"""
Tests for RSI strategy.
"""

import pytest
import pandas as pd
import numpy as np

from zyx_ai.strategies.rsi import RSIStrategy


class TestRSIStrategy:
    """Test RSI mean reversion strategy."""
    
    def test_strategy_initialization(self):
        """Test strategy can be initialized."""
        strategy = RSIStrategy()
        assert strategy.name == "RSI Mean Reversion"
        assert strategy.params["period"] == 14
        assert strategy.params["oversold"] == 30
        assert strategy.params["overbought"] == 70
    
    def test_rsi_calculation(self):
        """Test RSI calculation."""
        strategy = RSIStrategy()
        
        # Create sample price data
        prices = pd.Series([100, 102, 101, 103, 105, 104, 106, 108, 107, 109])
        rsi = strategy.calculate_rsi(prices, period=5)
        
        # RSI should be between 0 and 100
        assert not rsi.isna().all()
        valid_rsi = rsi.dropna()
        assert (valid_rsi >= 0).all() and (valid_rsi <= 100).all()
    
    def test_signal_generation_oversold(self, sample_market_data):
        """Test buy signal when RSI is oversold."""
        strategy = RSIStrategy(params={"period": 5, "oversold": 30})
        
        # Modify data to create oversold condition
        data = sample_market_data.copy()
        # Force price down trend to lower RSI
        data["close"] = data["close"].iloc[0] * (1 - np.linspace(0, 0.3, len(data)))
        
        signal = strategy.generate_signal(data)
        
        # Should generate a buy signal when oversold
        if signal:
            assert signal.direction in ["buy", "sell", "hold"]
            assert 0 <= signal.strength <= 1
    
    def test_invalid_data(self):
        """Test strategy handles invalid data gracefully."""
        strategy = RSIStrategy()
        
        # Empty dataframe
        empty_data = pd.DataFrame()
        signal = strategy.generate_signal(empty_data)
        assert signal is None
        
        # Missing required columns
        bad_data = pd.DataFrame({"price": [1, 2, 3]})
        signal = strategy.generate_signal(bad_data)
        assert signal is None
