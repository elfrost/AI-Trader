"""
Dynamic Context Extraction (DCE) - POC Module
Reduces token usage by intelligently filtering and compressing context
"""

import json
from typing import Dict, List, Optional, Tuple
from pathlib import Path


class DynamicContextExtractor:
    """
    Extracts and optimizes context for AI trading agents

    Core optimization strategies:
    1. Filter positions: Only include non-zero holdings
    2. Limit symbols: Show only relevant stocks (held + top movers)
    3. Compress prices: Use compact format
    """

    def __init__(
        self,
        max_symbols: int = 30,  # Reduced from 100
        min_position_threshold: float = 0.01  # Min % of portfolio
    ):
        self.max_symbols = max_symbols
        self.min_position_threshold = min_position_threshold

    def extract_relevant_positions(
        self,
        positions: Dict[str, float],
        prices: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Extract only non-zero positions that matter

        Args:
            positions: {symbol: shares, 'CASH': cash_amount}
            prices: {symbol_price: price_value}

        Returns:
            Filtered positions dict with only meaningful holdings
        """
        if not positions or 'CASH' not in positions:
            return positions

        # Always keep CASH
        filtered = {'CASH': positions['CASH']}

        # Calculate total portfolio value
        total_value = positions['CASH']
        for symbol, shares in positions.items():
            if symbol != 'CASH' and shares > 0:
                price_key = f"{symbol}_price"
                price = prices.get(price_key, 0)
                total_value += shares * price

        # Filter positions by threshold
        for symbol, shares in positions.items():
            if symbol == 'CASH':
                continue

            if shares <= 0:
                continue  # Skip zero or negative positions

            # Calculate position weight
            price_key = f"{symbol}_price"
            price = prices.get(price_key, 0)
            position_value = shares * price
            weight = position_value / total_value if total_value > 0 else 0

            # Keep if above threshold
            if weight >= self.min_position_threshold:
                filtered[symbol] = shares

        return filtered

    def select_relevant_symbols(
        self,
        positions: Dict[str, float],
        all_symbols: List[str],
        prices: Dict[str, float]
    ) -> List[str]:
        """
        Select most relevant symbols to include in context

        Priority:
        1. Symbols we currently hold
        2. Top liquid symbols (by proxy - first N in list)

        Args:
            positions: Current positions
            all_symbols: All available symbols
            prices: Current prices

        Returns:
            List of relevant symbols (max: self.max_symbols)
        """
        # Get held symbols
        held_symbols = [s for s in positions.keys() if s != 'CASH']

        # Add top liquid symbols up to max_symbols
        relevant = set(held_symbols)
        for symbol in all_symbols:
            if len(relevant) >= self.max_symbols:
                break
            relevant.add(symbol)

        return list(relevant)

    def compress_prices(
        self,
        prices: Dict[str, float],
        relevant_symbols: List[str]
    ) -> Dict[str, Optional[float]]:
        """
        Compress price dict to only include relevant symbols

        Args:
            prices: Full price dict {symbol_price: value}
            relevant_symbols: Symbols to keep

        Returns:
            Compressed price dict
        """
        compressed = {}
        for symbol in relevant_symbols:
            price_key = f"{symbol}_price"
            if price_key in prices:
                compressed[price_key] = prices[price_key]

        return compressed

    def format_compact_positions(self, positions: Dict[str, float]) -> str:
        """
        Format positions in compact readable format

        Args:
            positions: Position dict

        Returns:
            Compact string representation
        """
        parts = []
        for symbol, amount in positions.items():
            if symbol == 'CASH':
                parts.append(f"CASH: ${amount:.2f}")
            else:
                parts.append(f"{symbol}: {amount}")

        return " | ".join(parts)

    def format_compact_prices(self, prices: Dict[str, float]) -> str:
        """
        Format prices in compact readable format

        Args:
            prices: Price dict {symbol_price: value}

        Returns:
            Compact string representation
        """
        # Convert symbol_price keys to symbol: price format
        formatted = {}
        for key, value in prices.items():
            if key.endswith('_price'):
                symbol = key[:-6]  # Remove '_price' suffix
                formatted[symbol] = value

        parts = [f"{sym}: ${price:.2f}" for sym, price in sorted(formatted.items())]
        return " | ".join(parts)

    def extract_optimized_context(
        self,
        positions: Dict[str, float],
        yesterday_close: Dict[str, float],
        today_open: Dict[str, float],
        all_symbols: List[str]
    ) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, float], List[str]]:
        """
        Main extraction method: optimize full context

        Args:
            positions: Current positions
            yesterday_close: Yesterday's closing prices (all symbols)
            today_open: Today's opening prices (all symbols)
            all_symbols: All available symbols

        Returns:
            Tuple of (filtered_positions, filtered_yesterday, filtered_today, relevant_symbols)
        """
        # Step 1: Select relevant symbols
        relevant_symbols = self.select_relevant_symbols(
            positions, all_symbols, today_open
        )

        # Step 2: Filter positions
        filtered_positions = self.extract_relevant_positions(
            positions, today_open
        )

        # Step 3: Compress prices
        filtered_yesterday = self.compress_prices(yesterday_close, relevant_symbols)
        filtered_today = self.compress_prices(today_open, relevant_symbols)

        return (
            filtered_positions,
            filtered_yesterday,
            filtered_today,
            relevant_symbols
        )


class TokenCounter:
    """
    Simple token counter for measuring DCE impact
    Uses rough approximation: 1 token ≈ 4 characters
    """

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Estimate token count from text

        Args:
            text: Input text

        Returns:
            Estimated token count
        """
        # Rough approximation: 1 token ≈ 4 chars
        return len(text) // 4

    @staticmethod
    def count_dict_tokens(data: Dict) -> int:
        """
        Count tokens in dictionary representation

        Args:
            data: Dictionary to count

        Returns:
            Estimated token count
        """
        text = json.dumps(data)
        return TokenCounter.estimate_tokens(text)

    @staticmethod
    def calculate_reduction(original: int, optimized: int) -> float:
        """
        Calculate percentage reduction

        Args:
            original: Original token count
            optimized: Optimized token count

        Returns:
            Reduction percentage (0-100)
        """
        if original == 0:
            return 0.0
        return ((original - optimized) / original) * 100


class DCEMetrics:
    """Track and report DCE performance metrics"""

    def __init__(self):
        self.metrics = []

    def record_optimization(
        self,
        date: str,
        original_tokens: int,
        optimized_tokens: int,
        symbols_before: int,
        symbols_after: int
    ):
        """Record a single optimization event"""
        reduction = TokenCounter.calculate_reduction(original_tokens, optimized_tokens)

        self.metrics.append({
            'date': date,
            'original_tokens': original_tokens,
            'optimized_tokens': optimized_tokens,
            'reduction_pct': reduction,
            'symbols_before': symbols_before,
            'symbols_after': symbols_after
        })

    def get_summary(self) -> Dict:
        """Get summary statistics"""
        if not self.metrics:
            return {}

        total_original = sum(m['original_tokens'] for m in self.metrics)
        total_optimized = sum(m['optimized_tokens'] for m in self.metrics)
        avg_reduction = sum(m['reduction_pct'] for m in self.metrics) / len(self.metrics)

        return {
            'total_days': len(self.metrics),
            'total_tokens_saved': total_original - total_optimized,
            'avg_reduction_pct': avg_reduction,
            'total_original_tokens': total_original,
            'total_optimized_tokens': total_optimized
        }

    def save_to_file(self, filepath: str):
        """Save metrics to JSON file"""
        with open(filepath, 'w') as f:
            json.dump({
                'metrics': self.metrics,
                'summary': self.get_summary()
            }, f, indent=2)


if __name__ == "__main__":
    # Quick test
    extractor = DynamicContextExtractor(max_symbols=30)

    # Test data
    positions = {
        'AAPL': 10,
        'MSFT': 0,
        'NVDA': 5,
        'CASH': 5000.0
    }

    prices = {
        'AAPL_price': 150.0,
        'MSFT_price': 300.0,
        'NVDA_price': 800.0
    }

    # Extract relevant
    filtered = extractor.extract_relevant_positions(positions, prices)
    print("Filtered positions:", filtered)

    # Count tokens
    original_tokens = TokenCounter.count_dict_tokens(positions)
    filtered_tokens = TokenCounter.count_dict_tokens(filtered)
    reduction = TokenCounter.calculate_reduction(original_tokens, filtered_tokens)

    print(f"\nToken reduction: {reduction:.1f}%")
    print(f"Original: {original_tokens} tokens")
    print(f"Optimized: {filtered_tokens} tokens")
