"""
DCE-Enabled Trading Agent
Extends BaseAgent with Dynamic Context Extraction for token optimization
"""

import os
import asyncio
from typing import Optional, Dict, Any
from pathlib import Path

import sys
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from agent.base_agent.base_agent import BaseAgent
from prompts.agent_prompt_dce import get_agent_system_prompt_dce, STOP_SIGNAL
from agent.context_extractor.dce import DCEMetrics
from langchain.agents import create_agent


class DCEAgent(BaseAgent):
    """
    DCE-optimized trading agent

    Extends BaseAgent with:
    - Dynamic Context Extraction for reduced token usage
    - Metrics tracking for DCE performance
    - Optimized prompt generation
    """

    def __init__(
        self,
        signature: str,
        basemodel: str,
        max_symbols: int = 30,  # DCE parameter
        **kwargs
    ):
        """
        Initialize DCE Agent

        Args:
            signature: Agent signature/name
            basemodel: Base model name
            max_symbols: Maximum symbols to include in context (DCE optimization)
            **kwargs: Additional BaseAgent parameters
        """
        super().__init__(signature, basemodel, **kwargs)

        # DCE-specific configuration
        self.max_symbols = max_symbols
        self.dce_metrics = DCEMetrics()

        # Add DCE suffix to signature for tracking
        self.dce_signature = f"{signature}-dce"

        # Update data paths to use DCE signature
        self.data_path = os.path.join(self.base_log_path, self.dce_signature)
        self.position_file = os.path.join(self.data_path, "position", "position.jsonl")

    async def run_trading_session(self, today_date: str) -> None:
        """
        Run single day trading session with DCE optimization

        Overrides BaseAgent.run_trading_session to use DCE prompt

        Args:
            today_date: Trading date
        """
        print(f"📈 [DCE] Starting trading session: {today_date}")

        # Set up logging
        log_file = self._setup_logging(today_date)

        # Generate DCE-optimized system prompt
        system_prompt, dce_stats = get_agent_system_prompt_dce(
            today_date,
            self.signature,  # Use original signature for data access
            max_symbols=self.max_symbols,
            metrics=self.dce_metrics
        )

        # Log DCE stats
        print(f"[DCE Stats] Tokens: {dce_stats['original_tokens']} → {dce_stats['optimized_tokens']}")
        print(f"[DCE Stats] Reduction: {dce_stats['reduction_pct']:.1f}%")
        print(f"[DCE Stats] Symbols: {dce_stats['symbols_before']} → {dce_stats['symbols_after']}")

        # Create agent with optimized prompt
        self.agent = create_agent(
            self.model,
            tools=self.tools,
            system_prompt=system_prompt,
        )

        # Initial user query
        user_query = [{"role": "user", "content": f"Please analyze and update today's ({today_date}) positions."}]
        message = user_query.copy()

        # Log initial message
        self._log_message(log_file, user_query)

        # Trading loop (same as BaseAgent)
        current_step = 0
        while current_step < self.max_steps:
            current_step += 1
            print(f"🔄 Step {current_step}/{self.max_steps}")

            try:
                # Call agent
                response = await self._ainvoke_with_retry(message)

                # Extract agent response
                from tools.general_tools import extract_conversation, extract_tool_messages
                agent_response = extract_conversation(response, "final")

                # Check stop signal
                if STOP_SIGNAL in agent_response:
                    print("✅ Received stop signal, trading session ended")
                    print(agent_response)
                    self._log_message(log_file, [{"role": "assistant", "content": agent_response}])
                    break

                # Extract tool messages
                tool_msgs = extract_tool_messages(response)
                tool_response = '\n'.join([msg.content for msg in tool_msgs])

                # Prepare new messages
                new_messages = [
                    {"role": "assistant", "content": agent_response},
                    {"role": "user", "content": f'Tool results: {tool_response}'}
                ]

                # Add new messages
                message.extend(new_messages)

                # Log messages
                self._log_message(log_file, new_messages[0])
                self._log_message(log_file, new_messages[1])

            except Exception as e:
                print(f"❌ Trading session error: {str(e)}")
                print(f"Error details: {e}")
                raise

        # Handle trading results
        await self._handle_trading_result(today_date)

    async def run_date_range(self, init_date: str, end_date: str) -> None:
        """
        Run all trading days in date range with DCE

        Overrides BaseAgent.run_date_range to save DCE metrics

        Args:
            init_date: Start date
            end_date: End date
        """
        print(f"📅 [DCE] Running date range: {init_date} to {end_date}")

        # Call parent implementation
        await super().run_date_range(init_date, end_date)

        # Save DCE metrics
        metrics_file = os.path.join(self.data_path, "dce_metrics.json")
        self.dce_metrics.save_to_file(metrics_file)
        print(f"💾 [DCE] Metrics saved to: {metrics_file}")

        # Print summary
        summary = self.dce_metrics.get_summary()
        if summary:
            print("\n" + "="*60)
            print("DCE PERFORMANCE SUMMARY")
            print("="*60)
            print(f"Total days: {summary['total_days']}")
            print(f"Total tokens saved: {summary['total_tokens_saved']:,}")
            print(f"Average reduction: {summary['avg_reduction_pct']:.1f}%")
            print(f"Original tokens: {summary['total_original_tokens']:,}")
            print(f"Optimized tokens: {summary['total_optimized_tokens']:,}")
            print("="*60)

    def get_dce_metrics_summary(self) -> Dict[str, Any]:
        """
        Get DCE metrics summary

        Returns:
            Dictionary with DCE performance metrics
        """
        return self.dce_metrics.get_summary()

    def __str__(self) -> str:
        return f"DCEAgent(signature='{self.dce_signature}', basemodel='{self.basemodel}', max_symbols={self.max_symbols})"


if __name__ == "__main__":
    # Quick test
    print("Testing DCE Agent initialization...")

    agent = DCEAgent(
        signature="test-dce",
        basemodel="anthropic/claude-3.7-sonnet",
        max_symbols=30,
        initial_cash=10000.0
    )

    print(agent)
    print(f"Data path: {agent.data_path}")
    print(f"Max symbols: {agent.max_symbols}")
    print("✅ DCE Agent initialization successful")
