"""
Integration tests for trading system.
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, timedelta

import pandas as pd
import numpy as np

from zyx_ai.database.models import Trade, TradeSide, TradeStatus
from zyx_ai.strategies.rsi import RSIStrategy
from zyx_ai.strategies.macd import MACDStrategy
from zyx_ai.strategies.hft import MarketMakingStrategy
from zyx_ai.risk.manager import RiskManager
from zyx_ai.backtest.engine import BacktestEngine, WalkForwardAnalysis


class TestTradingIntegration:
    """Integration tests for complete trading flow."""
    
    @pytest.fixture
    def sample_market_data(self):
        """Generate realistic market data."""
        np.random.seed(42)
        dates = pd.date_range(start="2024-01-01", periods=500, freq="H")
        
        # Generate trending data with noise
        trend = np.linspace(30000, 35000, 500)
        noise = np.random.normal(0, 500, 500)
        prices = trend + noise
        
        data = pd.DataFrame({
            "open": prices + np.random.normal(0, 100, 500),
            "high": prices + np.abs(np.random.normal(200, 50, 500)),
            "low": prices - np.abs(np.random.normal(200, 50, 500)),
            "close": prices,
            "volume": np.random.uniform(100, 1000, 500),
        }, index=dates)
        
        return data
    
    def test_end_to_end_backtest(self, sample_market_data):
        """Test complete backtest flow."""
        strategy = RSIStrategy(params={"period": 14, "oversold": 30, "overbought": 70})
        engine = BacktestEngine(initial_capital=Decimal("10000"))
        
        result = engine.run_backtest(
            strategy=strategy,
            data=sample_market_data,
            symbol="BTCUSDT"
        )
        
        # Verify results structure
        assert result is not None
        assert result.total_trades >= 0
        assert result.win_rate >= 0 and result.win_rate <= 1
        assert result.total_return is not None
        assert len(result.equity_curve) > 0
        
        print(f"Backtest Results:")
        print(f"  Total Return: {result.total_return:.2f}%")
        print(f"  Win Rate: {result.win_rate:.2%}")
        print(f"  Sharpe Ratio: {result.sharpe_ratio:.2f}")
        print(f"  Max Drawdown: {result.max_drawdown:.2f}%")
    
    def test_walk_forward_analysis(self, sample_market_data):
        """Test walk-forward analysis."""
        strategy = MACDStrategy()
        wfa = WalkForwardAnalysis(train_pct=0.7)
        
        results = wfa.run(
            strategy=strategy,
            data=sample_market_data,
            symbol="BTCUSDT",
            n_splits=3
        )
        
        assert len(results) == 3
        
        # Check consistency across folds
        returns = [r.total_return for r in results]
        print(f"Walk-forward returns: {returns}")
        
        # All folds should complete without errors
        for result in results:
            assert result is not None
            assert result.total_trades >= 0
    
    def test_market_maker_inventory_management(self):
        """Test market maker inventory tracking."""
        mm = MarketMakingStrategy()
        
        # Simulate fills
        mm.update_inventory("buy", Decimal("0.01"), Decimal("35000"))
        assert mm.inventory == Decimal("0.01")
        
        mm.update_inventory("sell", Decimal("0.005"), Decimal("36000"))
        assert mm.inventory == Decimal("0.005")
        
        # Check P&L calculation
        pnl_data = mm.get_pnl(Decimal("37000"))
        assert "pnl" in pnl_data
        assert "inventory_value" in pnl_data
    
    def test_risk_manager_position_sizing(self):
        """Test risk management calculations."""
        risk_mgr = RiskManager()
        
        portfolio_value = Decimal("10000")
        entry_price = Decimal("35000")
        signal_strength = 0.8
        
        position_size = risk_mgr.calculate_position_size(
            portfolio_value=portfolio_value,
            entry_price=entry_price,
            signal_strength=signal_strength
        )
        
        # Position should be reasonable
        assert position_size > 0
        assert position_size <= portfolio_value * Decimal("10")  # Max 10x leverage
    
    def test_strategy_ensemble(self, sample_market_data):
        """Test signal ensemble from multiple strategies."""
        from zyx_ai.ml.features import SignalEnsemble
        
        strategies = [
            RSIStrategy(params={"period": 10}),
            MACDStrategy(),
        ]
        
        ensemble = SignalEnsemble(strategies, weights=[0.5, 0.5])
        
        # Get composite signal
        signal = ensemble.generate_composite_signal(sample_market_data)
        
        assert "direction" in signal
        assert "strength" in signal
        assert "components" in signal
        assert signal["direction"] in ["buy", "sell", "hold"]
        assert 0 <= signal["strength"] <= 1
    
    def test_feature_engineering(self, sample_market_data):
        """Test ML feature creation."""
        from zyx_ai.ml.features import FeatureEngineer
        
        engineer = FeatureEngineer()
        features = engineer.create_features(sample_market_data)
        
        # Should add many feature columns
        assert len(features.columns) > len(sample_market_data.columns)
        
        # Check for expected features
        expected_features = ["returns", "volatility_20", "ma_20", "volume_ratio"]
        for feat in expected_features:
            assert feat in features.columns


class TestStressTests:
    """Stress tests for system stability."""
    
    def test_high_frequency_signals(self):
        """Test system handles many signals quickly."""
        strategy = RSIStrategy()
        
        # Generate large dataset
        data = pd.DataFrame({
            "open": np.random.uniform(30000, 40000, 10000),
            "high": np.random.uniform(31000, 41000, 10000),
            "low": np.random.uniform(29000, 39000, 10000),
            "close": np.random.uniform(30000, 40000, 10000),
            "volume": np.random.uniform(100, 1000, 10000),
        })
        
        import time
        start = time.time()
        
        # Process many windows
        for i in range(1000, 10000, 100):
            window = data.iloc[i-100:i]
            signal = strategy.generate_signal(window)
        
        elapsed = time.time() - start
        print(f"Processed 9000 signals in {elapsed:.2f}s")
        
        # Should be reasonably fast (< 5 seconds)
        assert elapsed < 5.0
    
    def test_order_book_pressure(self):
        """Test order book with high update frequency."""
        from zyx_ai.exchanges.orderbook import OrderBookAnalyzer
        
        analyzer = OrderBookAnalyzer()
        
        # Simulate many order book updates
        for i in range(1000):
            bids = [(Decimal("35000") - Decimal(str(j)), Decimal("0.1")) for j in range(10)]
            asks = [(Decimal("35000") + Decimal(str(j)), Decimal("0.1")) for j in range(10)]
            
            analyzer.update("BTCUSDT", bids, asks)
        
        book = analyzer.order_books.get("BTCUSDT")
        assert book is not None
        assert len(analyzer.history["BTCUSDT"]) == 1000
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test system handles concurrent operations."""
        async def simulate_trading():
            strategy = RSIStrategy()
            data = pd.DataFrame({
                "open": np.random.uniform(30000, 40000, 100),
                "high": np.random.uniform(31000, 41000, 100),
                "low": np.random.uniform(29000, 39000, 100),
                "close": np.random.uniform(30000, 40000, 100),
                "volume": np.random.uniform(100, 1000, 100),
            })
            return strategy.generate_signal(data)
        
        # Run many concurrent operations
        tasks = [simulate_trading() for _ in range(100)]
        results = await asyncio.gather(*tasks)
        
        # All should complete without errors
        assert len(results) == 100


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_data(self):
        """Test handling of empty data."""
        strategy = RSIStrategy()
        empty_data = pd.DataFrame()
        
        signal = strategy.generate_signal(empty_data)
        assert signal is None
    
    def test_insufficient_data(self):
        """Test handling of insufficient data points."""
        strategy = RSIStrategy(params={"period": 50})
        
        small_data = pd.DataFrame({
            "open": [30000],
            "high": [31000],
            "low": [29000],
            "close": [30500],
            "volume": [100],
        })
        
        signal = strategy.generate_signal(small_data)
        assert signal is None
    
    def test_zero_prices(self):
        """Test handling of zero or negative prices."""
        strategy = RSIStrategy()
        
        bad_data = pd.DataFrame({
            "open": [0, 0, 0],
            "high": [0, 0, 0],
            "low": [0, 0, 0],
            "close": [0, 0, 0],
            "volume": [0, 0, 0],
        })
        
        # Should not crash
        signal = strategy.generate_signal(bad_data)
        # May return None or handle gracefully
    
    def test_extreme_leverage(self):
        """Test risk manager with extreme leverage values."""
        risk_mgr = RiskManager()
        
        # Very high leverage request
        position_size = risk_mgr.calculate_position_size(
            portfolio_value=Decimal("10000"),
            entry_price=Decimal("35000"),
            signal_strength=0.9,
            leverage=100  # Extreme
        )
        
        # Should be capped at max leverage
        max_position = Decimal("10000") * Decimal("10")  # 10x max
        assert position_size <= max_position
    
    def test_rapid_trades(self):
        """Test system with rapid-fire trade execution."""
        engine = BacktestEngine()
        
        # Create data with many signals
        data = pd.DataFrame({
            "open": np.random.uniform(30000, 40000, 100),
            "high": np.random.uniform(31000, 41000, 100),
            "low": np.random.uniform(29000, 39000, 100),
            "close": np.random.uniform(30000, 40000, 100),
            "volume": np.random.uniform(100, 1000, 100),
        })
        
        strategy = RSIStrategy(params={"period": 5, "oversold": 20, "overbought": 80})
        
        # Should handle many trades without error
        result = engine.run_backtest(strategy, data, "BTCUSDT")
        assert result is not None
