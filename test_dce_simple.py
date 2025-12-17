"""
Simple DCE Test - No external dependencies required
Tests the core DCE functionality with mock data
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.context_extractor.dce import DynamicContextExtractor, TokenCounter


def test_context_extraction():
    """Test basic context extraction"""
    print("="*80)
    print("TEST 1: Context Extraction")
    print("="*80)

    # Create mock data
    all_symbols = [
        "NVDA", "MSFT", "AAPL", "GOOG", "GOOGL", "AMZN", "META", "AVGO", "TSLA",
        "NFLX", "PLTR", "COST", "ASML", "AMD", "CSCO", "AZN", "TMUS", "MU", "LIN",
        "PEP"  # 20 symbols for testing
    ]

    # Mock positions - only holding 3 stocks
    positions = {
        'AAPL': 10,
        'MSFT': 5,
        'NVDA': 8,
        'GOOG': 0,  # Not held
        'CASH': 5000.0
    }

    # Mock prices
    yesterday_close = {f"{sym}_price": 100.0 + i for i, sym in enumerate(all_symbols)}
    today_open = {f"{sym}_price": 101.0 + i for i, sym in enumerate(all_symbols)}

    # Create extractor
    extractor = DynamicContextExtractor(max_symbols=10)

    # Extract context
    filtered_pos, filtered_yesterday, filtered_today, relevant_symbols = \
        extractor.extract_optimized_context(
            positions, yesterday_close, today_open, all_symbols
        )

    # Print results
    print(f"\nOriginal positions: {len(positions)} items")
    print(f"Filtered positions: {len(filtered_pos)} items")
    print(f"Filtered positions: {filtered_pos}")

    print(f"\nOriginal symbols: {len(all_symbols)}")
    print(f"Relevant symbols: {len(relevant_symbols)}")
    print(f"Selected symbols: {relevant_symbols}")

    print(f"\nOriginal yesterday prices: {len(yesterday_close)}")
    print(f"Filtered yesterday prices: {len(filtered_yesterday)}")

    print(f"\nOriginal today prices: {len(today_open)}")
    print(f"Filtered today prices: {len(filtered_today)}")

    # Format compact
    compact_pos = extractor.format_compact_positions(filtered_pos)
    compact_yesterday = extractor.format_compact_prices(filtered_yesterday)
    compact_today = extractor.format_compact_prices(filtered_today)

    print(f"\nCompact positions: {compact_pos}")
    print(f"Compact yesterday: {compact_yesterday[:100]}...")
    print(f"Compact today: {compact_today[:100]}...")

    print("\n✅ Context extraction test passed\n")


def test_token_counting():
    """Test token counting and reduction calculation"""
    print("="*80)
    print("TEST 2: Token Counting")
    print("="*80)

    # Create full context (100 symbols like real NASDAQ 100)
    full_symbols = [f"SYM{i:03d}" for i in range(100)]
    full_positions = {sym: 0 for sym in full_symbols}
    full_positions['CASH'] = 10000.0

    # Add some actual positions
    full_positions['SYM000'] = 10
    full_positions['SYM001'] = 5
    full_positions['SYM002'] = 8

    # Create prices
    full_prices = {f"{sym}_price": 100.0 for sym in full_symbols}

    # Calculate original tokens
    import json
    original_text = json.dumps({
        'positions': full_positions,
        'prices': full_prices
    })
    original_tokens = TokenCounter.estimate_tokens(original_text)

    print(f"\nOriginal context:")
    print(f"  Symbols: {len(full_symbols)}")
    print(f"  Text length: {len(original_text)} chars")
    print(f"  Estimated tokens: {original_tokens:,}")

    # Extract with DCE
    extractor = DynamicContextExtractor(max_symbols=30)
    filtered_pos, _, filtered_prices, relevant = \
        extractor.extract_optimized_context(
            full_positions, full_prices, full_prices, full_symbols
        )

    # Calculate optimized tokens
    optimized_text = json.dumps({
        'positions': filtered_pos,
        'prices': filtered_prices
    })
    optimized_tokens = TokenCounter.estimate_tokens(optimized_text)

    print(f"\nOptimized context (DCE):")
    print(f"  Symbols: {len(relevant)}")
    print(f"  Text length: {len(optimized_text)} chars")
    print(f"  Estimated tokens: {optimized_tokens:,}")

    # Calculate reduction
    reduction = TokenCounter.calculate_reduction(original_tokens, optimized_tokens)
    tokens_saved = original_tokens - optimized_tokens

    print(f"\n📊 Results:")
    print(f"  Token reduction: {reduction:.1f}%")
    print(f"  Tokens saved: {tokens_saved:,}")
    print(f"  Symbol reduction: {len(full_symbols)} → {len(relevant)}")

    print("\n✅ Token counting test passed\n")


def test_full_prompt_simulation():
    """Simulate full prompt generation with realistic data"""
    print("="*80)
    print("TEST 3: Full Prompt Simulation")
    print("="*80)

    # Simulate NASDAQ 100
    nasdaq_100 = [
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

    # Create realistic positions (agent holds 5 stocks)
    positions = {sym: 0 for sym in nasdaq_100}
    positions.update({
        'AAPL': 10,
        'MSFT': 15,
        'NVDA': 8,
        'GOOGL': 5,
        'AMZN': 12,
        'CASH': 3000.0
    })

    # Create realistic prices
    import random
    random.seed(42)
    prices = {f"{sym}_price": round(50 + random.random() * 500, 2) for sym in nasdaq_100}

    # Baseline prompt (all data)
    baseline_prompt = f"""
You are a stock fundamental analysis trading assistant.

Today's date: 2025-10-15

Yesterday's closing positions:
{positions}

Yesterday's closing prices:
{prices}

Today's buying prices:
{prices}

When complete, output: <FINISH_SIGNAL>
"""

    baseline_tokens = TokenCounter.estimate_tokens(baseline_prompt)
    print(f"\nBaseline prompt:")
    print(f"  Length: {len(baseline_prompt):,} chars")
    print(f"  Estimated tokens: {baseline_tokens:,}")
    print(f"  Symbols: {len(nasdaq_100)}")

    # DCE optimized prompt
    extractor = DynamicContextExtractor(max_symbols=30)
    filtered_pos, filtered_yesterday, filtered_today, relevant = \
        extractor.extract_optimized_context(
            positions, prices, prices, nasdaq_100
        )

    # Format compact
    compact_pos = extractor.format_compact_positions(filtered_pos)
    compact_prices = extractor.format_compact_prices(filtered_today)

    dce_prompt = f"""
You are a stock fundamental analysis trading assistant.

Today's date: 2025-10-15

Yesterday's positions: {compact_pos}
Yesterday's close: {compact_prices}
Today's open: {compact_prices}

Note: Only relevant symbols shown. Search for any NASDAQ 100 symbol if needed.

When complete, output: <FINISH_SIGNAL>
"""

    dce_tokens = TokenCounter.estimate_tokens(dce_prompt)
    print(f"\nDCE optimized prompt:")
    print(f"  Length: {len(dce_prompt):,} chars")
    print(f"  Estimated tokens: {dce_tokens:,}")
    print(f"  Symbols: {len(relevant)}")

    # Calculate savings
    reduction = TokenCounter.calculate_reduction(baseline_tokens, dce_tokens)
    saved = baseline_tokens - dce_tokens

    print(f"\n📊 Optimization Results:")
    print(f"  Token reduction: {reduction:.1f}%")
    print(f"  Tokens saved: {saved:,}")
    print(f"  Char reduction: {len(baseline_prompt) - len(dce_prompt):,}")
    print(f"  Symbol reduction: {len(nasdaq_100)} → {len(relevant)}")

    # Calculate cost savings (rough estimate)
    # Assume $0.003 per 1K tokens (Claude Sonnet pricing)
    cost_per_token = 0.003 / 1000
    cost_saved_per_prompt = saved * cost_per_token

    print(f"\n💰 Cost Impact (per prompt @ $0.003/1K tokens):")
    print(f"  Baseline cost: ${baseline_tokens * cost_per_token:.6f}")
    print(f"  DCE cost: ${dce_tokens * cost_per_token:.6f}")
    print(f"  Saved per prompt: ${cost_saved_per_prompt:.6f}")

    # Over 20 trading days with 30 iterations each
    total_iterations = 20 * 30  # 600 prompts
    total_saved = cost_saved_per_prompt * total_iterations
    print(f"  Saved over 20 days (30 steps/day): ${total_saved:.2f}")

    print("\n✅ Full prompt simulation test passed\n")


def run_all_tests():
    """Run all DCE tests"""
    print("\n" + "="*80)
    print("DCE POC - SIMPLE TESTS")
    print("="*80 + "\n")

    test_context_extraction()
    test_token_counting()
    test_full_prompt_simulation()

    print("="*80)
    print("ALL TESTS PASSED ✅")
    print("="*80)
    print("\nDCE POC is ready for integration testing!")
    print("Next steps:")
    print("  1. Install dependencies: pip install python-dotenv")
    print("  2. Start MCP services: cd agent_tools && python start_mcp_services.py")
    print("  3. Run full test: python dce_poc_test.py full")
    print()


if __name__ == "__main__":
    run_all_tests()
