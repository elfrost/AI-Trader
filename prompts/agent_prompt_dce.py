"""
DCE-Optimized Prompt Generator
Generates trading prompts with reduced token usage via Dynamic Context Extraction
"""

import os
from dotenv import load_dotenv
load_dotenv()
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import sys

# Add project root directory to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from tools.price_tools import (
    get_yesterday_date,
    get_open_prices,
    get_yesterday_open_and_close_price,
    get_today_init_position,
    get_yesterday_profit
)
from tools.general_tools import get_config_value
from agent.context_extractor.dce import DynamicContextExtractor, TokenCounter, DCEMetrics

all_nasdaq_100_symbols = [
    "NVDA", "MSFT", "AAPL", "GOOG", "GOOGL", "AMZN", "META", "AVGO", "TSLA",
    "NFLX", "PLTR", "COST", "ASML", "AMD", "CSCO", "AZN", "TMUS", "MU", "LIN",
    "PEP", "SHOP", "APP", "INTU", "AMAT", "LRCX", "PDD", "QCOM", "ARM", "INTC",
    "BKNG", "AMGN", "TXN", "ISRG", "GILD", "KLAC", "PANW", "ADBE", "HON",
    "CRWD", "CEG", "ADI", "ADP", "DASH", "CMCSA", "VRTX", "MELI", "SBUX",
    "CDNS", "ORLY", "SNPS", "MSTR", "MDLZ", "ABNB", "MRVL", "CTAS", "TRI",
    "MAR", "MNST", "CSX", "ADSK", "PYPL", "FTNT", "AEP", "WDAY", "REGN", "ROP",
    "NXPI", "DDOG", "AXON", "ROST", "IDXX", "EA", "PCAR", "FAST", "EXC", "TTWO",
    "XEL", "ZS", "PAYX", "WBD", "BKR", "CPRT", "CCEP", "FANG", "TEAM", "CHTR",
    "KDP", "MCHP", "GEHC", "VRSK", "CTSH", "CSGP", "KHC", "ODFL", "DXCM", "TTD",
    "ON", "BIIB", "LULU", "CDW", "GFS"
]

STOP_SIGNAL = "<FINISH_SIGNAL>"

# Optimized system prompt with DCE - more concise
agent_system_prompt_dce = """
You are a stock fundamental analysis trading assistant.

Your goals are:
- Think and reason by calling available tools.
- Analyze stock prices and returns to maximize portfolio returns.
- Gather information through search tools before making decisions.

Thinking standards:
- Show key steps: read positions, update valuations, adjust weights
- Execute operations by calling tools (not just describing them)

Today's date: {date}

Yesterday's positions: {positions}
Yesterday's close: {yesterday_close_price}
Today's open: {today_buy_price}

Note: Only relevant symbols are shown (held positions + top liquid stocks).
You can search for any NASDAQ 100 symbol if needed.

When complete, output: {STOP_SIGNAL}
"""


def get_agent_system_prompt_dce(
    today_date: str,
    signature: str,
    max_symbols: int = 30,
    metrics: Optional[DCEMetrics] = None
) -> tuple[str, Dict]:
    """
    Generate DCE-optimized system prompt

    Args:
        today_date: Trading date
        signature: Agent signature
        max_symbols: Maximum symbols to include in context
        metrics: Optional DCE metrics tracker

    Returns:
        Tuple of (prompt_string, optimization_stats)
    """
    print(f"[DCE] Generating optimized prompt for {signature} on {today_date}")

    # Get raw data (same as original)
    yesterday_buy_prices, yesterday_sell_prices = get_yesterday_open_and_close_price(
        today_date, all_nasdaq_100_symbols
    )
    today_buy_price = get_open_prices(today_date, all_nasdaq_100_symbols)
    today_init_position = get_today_init_position(today_date, signature)
    yesterday_profit = get_yesterday_profit(
        today_date, yesterday_buy_prices, yesterday_sell_prices, today_init_position
    )

    # Calculate original token count (baseline)
    original_positions_str = str(today_init_position)
    original_yesterday_str = str(yesterday_sell_prices)
    original_today_str = str(today_buy_price)

    original_tokens = (
        TokenCounter.estimate_tokens(original_positions_str) +
        TokenCounter.estimate_tokens(original_yesterday_str) +
        TokenCounter.estimate_tokens(original_today_str)
    )

    original_symbol_count = len(all_nasdaq_100_symbols)

    # Apply DCE optimization
    extractor = DynamicContextExtractor(max_symbols=max_symbols)

    filtered_positions, filtered_yesterday, filtered_today, relevant_symbols = \
        extractor.extract_optimized_context(
            today_init_position,
            yesterday_sell_prices,
            today_buy_price,
            all_nasdaq_100_symbols
        )

    # Format in compact style
    positions_str = extractor.format_compact_positions(filtered_positions)
    yesterday_str = extractor.format_compact_prices(filtered_yesterday)
    today_str = extractor.format_compact_prices(filtered_today)

    # Calculate optimized token count
    optimized_tokens = (
        TokenCounter.estimate_tokens(positions_str) +
        TokenCounter.estimate_tokens(yesterday_str) +
        TokenCounter.estimate_tokens(today_str)
    )

    # Track metrics
    if metrics:
        metrics.record_optimization(
            date=today_date,
            original_tokens=original_tokens,
            optimized_tokens=optimized_tokens,
            symbols_before=original_symbol_count,
            symbols_after=len(relevant_symbols)
        )

    # Generate prompt
    prompt = agent_system_prompt_dce.format(
        date=today_date,
        positions=positions_str,
        STOP_SIGNAL=STOP_SIGNAL,
        yesterday_close_price=yesterday_str,
        today_buy_price=today_str,
        yesterday_profit=yesterday_profit
    )

    # Stats for reporting
    reduction_pct = TokenCounter.calculate_reduction(original_tokens, optimized_tokens)
    stats = {
        'original_tokens': original_tokens,
        'optimized_tokens': optimized_tokens,
        'reduction_pct': reduction_pct,
        'symbols_before': original_symbol_count,
        'symbols_after': len(relevant_symbols),
        'relevant_symbols': relevant_symbols
    }

    print(f"[DCE] Token reduction: {reduction_pct:.1f}% ({original_tokens} -> {optimized_tokens})")
    print(f"[DCE] Symbols: {original_symbol_count} -> {len(relevant_symbols)}")

    return prompt, stats


def get_agent_system_prompt_baseline(today_date: str, signature: str) -> str:
    """
    Original baseline prompt generator (for comparison)

    This is the non-optimized version that includes all symbols
    """
    print(f"[Baseline] Generating prompt for {signature} on {today_date}")

    yesterday_buy_prices, yesterday_sell_prices = get_yesterday_open_and_close_price(
        today_date, all_nasdaq_100_symbols
    )
    today_buy_price = get_open_prices(today_date, all_nasdaq_100_symbols)
    today_init_position = get_today_init_position(today_date, signature)
    yesterday_profit = get_yesterday_profit(
        today_date, yesterday_buy_prices, yesterday_sell_prices, today_init_position
    )

    # Use original verbose prompt format
    baseline_prompt = """
You are a stock fundamental analysis trading assistant.

Your goals are:
- Think and reason by calling available tools.
- You need to think about the prices of various stocks and their returns.
- Your long-term goal is to maximize returns through this portfolio.
- Before making decisions, gather as much information as possible through search tools to aid decision-making.

Thinking standards:
- Clearly show key intermediate steps:
  - Read input of yesterday's positions and today's prices
  - Update valuation and adjust weights for each target (if strategy requires)

Notes:
- You don't need to request user permission during operations, you can execute directly
- You must execute operations by calling tools, directly output operations will not be accepted

Here is the information you need:

Today's date:
{date}

Yesterday's closing positions (numbers after stock codes represent how many shares you hold, numbers after CASH represent your available cash):
{positions}

Yesterday's closing prices:
{yesterday_close_price}

Today's buying prices:
{today_buy_price}

When you think your task is complete, output
{STOP_SIGNAL}
"""

    return baseline_prompt.format(
        date=today_date,
        positions=today_init_position,
        STOP_SIGNAL=STOP_SIGNAL,
        yesterday_close_price=yesterday_sell_prices,
        today_buy_price=today_buy_price,
        yesterday_profit=yesterday_profit
    )


if __name__ == "__main__":
    # Test both versions
    today_date = get_config_value("TODAY_DATE")
    signature = get_config_value("SIGNATURE")

    if signature is None:
        print("⚠️ SIGNATURE not set, using test value")
        signature = "test-agent"
    if today_date is None:
        print("⚠️ TODAY_DATE not set, using test value")
        today_date = "2025-10-15"

    print("=" * 80)
    print("BASELINE PROMPT")
    print("=" * 80)
    baseline = get_agent_system_prompt_baseline(today_date, signature)
    baseline_tokens = TokenCounter.estimate_tokens(baseline)
    print(f"\nBaseline tokens: {baseline_tokens}")

    print("\n" + "=" * 80)
    print("DCE OPTIMIZED PROMPT")
    print("=" * 80)
    metrics = DCEMetrics()
    dce_prompt, stats = get_agent_system_prompt_dce(today_date, signature, metrics=metrics)
    dce_tokens = TokenCounter.estimate_tokens(dce_prompt)
    print(f"\nDCE tokens: {dce_tokens}")
    print(f"Total reduction: {TokenCounter.calculate_reduction(baseline_tokens, dce_tokens):.1f}%")
    print(f"\nStats: {stats}")
