"""
DCE POC Test Script
Compares baseline vs DCE-optimized agent performance

Usage:
    python dce_poc_test.py
"""

import os
import asyncio
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Add project root to path
import sys
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from agent.base_agent.base_agent import BaseAgent
from agent.dce_agent.dce_agent import DCEAgent
from tools.general_tools import write_config_value


async def test_dce_poc(
    model_name: str = "anthropic/claude-3.7-sonnet",
    init_date: str = "2025-10-13",
    end_date: str = "2025-10-17",  # 5 trading days for POC
    max_symbols: int = 30
):
    """
    Run DCE POC test comparing baseline vs DCE

    Args:
        model_name: Model to test
        init_date: Start date
        end_date: End date
        max_symbols: Max symbols for DCE
    """
    print("\n" + "="*80)
    print("DCE POC TEST")
    print("="*80)
    print(f"Model: {model_name}")
    print(f"Date range: {init_date} to {end_date}")
    print(f"DCE max symbols: {max_symbols}")
    print("="*80 + "\n")

    # Test configuration
    test_signature_baseline = "poc-baseline"
    test_signature_dce = "poc-dce"

    # MCP config
    mcp_config = {
        "math": {
            "transport": "streamable_http",
            "url": f"http://localhost:{os.getenv('MATH_HTTP_PORT', '8000')}/mcp",
        },
        "stock_local": {
            "transport": "streamable_http",
            "url": f"http://localhost:{os.getenv('GETPRICE_HTTP_PORT', '8003')}/mcp",
        },
        "search": {
            "transport": "streamable_http",
            "url": f"http://localhost:{os.getenv('SEARCH_HTTP_PORT', '8001')}/mcp",
        },
        "trade": {
            "transport": "streamable_http",
            "url": f"http://localhost:{os.getenv('TRADE_HTTP_PORT', '8002')}/mcp",
        },
    }

    # Common agent config
    agent_config = {
        "mcp_config": mcp_config,
        "log_path": "./data/agent_data",
        "max_steps": 30,
        "max_retries": 3,
        "base_delay": 1.0,
        "initial_cash": 10000.0,
        "init_date": init_date
    }

    # Create agents
    print("🤖 Creating baseline agent...")
    baseline_agent = BaseAgent(
        signature=test_signature_baseline,
        basemodel=model_name,
        **agent_config
    )

    print("🤖 Creating DCE agent...")
    dce_agent = DCEAgent(
        signature=test_signature_dce,
        basemodel=model_name,
        max_symbols=max_symbols,
        **agent_config
    )

    # Initialize agents
    print("\n📡 Initializing baseline agent...")
    await baseline_agent.initialize()

    print("📡 Initializing DCE agent...")
    await dce_agent.initialize()

    # Register agents (create initial positions)
    print("\n📝 Registering baseline agent...")
    baseline_agent.register_agent()

    print("📝 Registering DCE agent...")
    dce_agent.register_agent()

    # Run baseline
    print("\n" + "="*80)
    print("RUNNING BASELINE AGENT")
    print("="*80)
    try:
        await baseline_agent.run_date_range(init_date, end_date)
        print("✅ Baseline agent completed successfully")
    except Exception as e:
        print(f"❌ Baseline agent failed: {e}")

    # Run DCE
    print("\n" + "="*80)
    print("RUNNING DCE AGENT")
    print("="*80)
    try:
        await dce_agent.run_date_range(init_date, end_date)
        print("✅ DCE agent completed successfully")
    except Exception as e:
        print(f"❌ DCE agent failed: {e}")

    # Compare results
    print("\n" + "="*80)
    print("COMPARISON RESULTS")
    print("="*80)

    # DCE metrics
    dce_summary = dce_agent.get_dce_metrics_summary()
    if dce_summary:
        print("\n📊 DCE Performance:")
        print(f"  Total days: {dce_summary['total_days']}")
        print(f"  Total tokens saved: {dce_summary['total_tokens_saved']:,}")
        print(f"  Average reduction: {dce_summary['avg_reduction_pct']:.1f}%")
        print(f"  Original tokens: {dce_summary['total_original_tokens']:,}")
        print(f"  Optimized tokens: {dce_summary['total_optimized_tokens']:,}")

    # Position summaries
    print("\n💼 Final Positions:")
    baseline_pos = baseline_agent.get_position_summary()
    dce_pos = dce_agent.get_position_summary()

    print("\nBaseline:")
    print(f"  Latest date: {baseline_pos.get('latest_date', 'N/A')}")
    print(f"  Total records: {baseline_pos.get('total_records', 0)}")
    if 'positions' in baseline_pos:
        cash = baseline_pos['positions'].get('CASH', 0)
        print(f"  Cash: ${cash:.2f}")

    print("\nDCE:")
    print(f"  Latest date: {dce_pos.get('latest_date', 'N/A')}")
    print(f"  Total records: {dce_pos.get('total_records', 0)}")
    if 'positions' in dce_pos:
        cash = dce_pos['positions'].get('CASH', 0)
        print(f"  Cash: ${cash:.2f}")

    print("\n" + "="*80)
    print("POC TEST COMPLETE")
    print("="*80)

    # Save comparison report
    report = {
        'test_date': datetime.now().isoformat(),
        'model': model_name,
        'date_range': {'init': init_date, 'end': end_date},
        'dce_config': {'max_symbols': max_symbols},
        'baseline_summary': baseline_pos,
        'dce_summary': dce_pos,
        'dce_metrics': dce_summary
    }

    report_file = "./data/agent_data/dce_poc_report.json"
    os.makedirs(os.path.dirname(report_file), exist_ok=True)
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n📄 Full report saved to: {report_file}")


async def quick_prompt_test():
    """
    Quick test to compare prompt sizes without running full trading

    This is useful for rapid iteration on DCE optimization
    """
    print("\n" + "="*80)
    print("QUICK PROMPT SIZE COMPARISON")
    print("="*80)

    from prompts.agent_prompt import get_agent_system_prompt
    from prompts.agent_prompt_dce import get_agent_system_prompt_dce, TokenCounter
    from agent.context_extractor.dce import DCEMetrics

    # Test settings
    test_date = "2025-10-15"
    test_signature = "quick-test"

    # Setup config
    write_config_value("TODAY_DATE", test_date)
    write_config_value("SIGNATURE", test_signature)

    # Get baseline prompt
    print("\n🔍 Generating baseline prompt...")
    try:
        baseline_prompt = get_agent_system_prompt(test_date, test_signature)
        baseline_tokens = TokenCounter.estimate_tokens(baseline_prompt)
        print(f"✅ Baseline prompt: {baseline_tokens:,} tokens")
    except Exception as e:
        print(f"❌ Baseline failed: {e}")
        baseline_tokens = 0

    # Get DCE prompt
    print("\n🔍 Generating DCE prompt...")
    try:
        metrics = DCEMetrics()
        dce_prompt, stats = get_agent_system_prompt_dce(test_date, test_signature, metrics=metrics)
        dce_tokens = TokenCounter.estimate_tokens(dce_prompt)
        print(f"✅ DCE prompt: {dce_tokens:,} tokens")

        # Calculate reduction
        if baseline_tokens > 0:
            reduction = TokenCounter.calculate_reduction(baseline_tokens, dce_tokens)
            print(f"\n📊 Token reduction: {reduction:.1f}%")
            print(f"   Saved: {baseline_tokens - dce_tokens:,} tokens")
    except Exception as e:
        print(f"❌ DCE failed: {e}")

    print("\n" + "="*80)


def print_usage():
    """Print usage instructions"""
    print("""
DCE POC Test Script

Usage:
    python dce_poc_test.py [mode]

Modes:
    full        - Run full POC test (baseline + DCE agents)
    quick       - Quick prompt comparison only
    help        - Show this help message

Examples:
    python dce_poc_test.py full
    python dce_poc_test.py quick

Note: Requires MCP services to be running.
Start them with: cd agent_tools && python start_mcp_services.py
    """)


if __name__ == "__main__":
    import sys

    # Parse command line arguments
    mode = sys.argv[1] if len(sys.argv) > 1 else "quick"

    if mode == "help":
        print_usage()
    elif mode == "quick":
        # Quick test - just compare prompts
        asyncio.run(quick_prompt_test())
    elif mode == "full":
        # Full test - run both agents
        print("⚠️  Full test requires MCP services to be running!")
        print("    Start them with: cd agent_tools && python start_mcp_services.py\n")
        response = input("Continue? (y/n): ")
        if response.lower() == 'y':
            asyncio.run(test_dce_poc())
        else:
            print("Test cancelled.")
    else:
        print(f"Unknown mode: {mode}")
        print_usage()
