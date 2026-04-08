"""
RSI Mean Reversion Strategy.

Buys when RSI is oversold (< 30), sells when overbought (> 70).
"""

from decimal import Decimal
from typing import Optional, Dict, Any
from datetime import datetime

import pandas as pd
import numpy as np

from zyx_ai.strategies.base import BaseStrategy, Signal


class RSIStrategy(BaseStrategy):
    """RSI-based mean reversion strategy."""
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """Initialize RSI strategy.
        
        Args:
            params: Dictionary with keys:
                - period: RSI lookback period (default: 14)
                - oversold: Oversold threshold (default: 30)
                - overbought: Overbought threshold (default: 70)
                - min_strength: Minimum signal strength (default: 0.6)
        """
        default_params = {
            "period": 14,
            "oversold": 30,
            "overbought": 70,
            "min_strength": 0.6,
        }
        default_params.update(params or {})
        super().__init__("RSI Mean Reversion", default_params)
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator.
        
        Args:
            prices: Price series (typically close prices)
            period: RSI lookback period
            
        Returns:
            RSI values
        """
        delta = prices.diff()
        
        # Separate gains and losses
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        # Calculate RS and RSI
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate RSI and related indicators."""
        data = data.copy()
        period = self.params["period"]
        
        # Calculate RSI
        data["rsi"] = self.calculate_rsi(data["close"], period)
        
        # Calculate RSI moving average
        data["rsi_ma"] = data["rsi"].rolling(window=period).mean()
        
        # Calculate price momentum
        data["momentum"] = data["close"].pct_change(period)
        
        return data
    
    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        """Generate signal based on RSI levels."""
        if not self.validate_data(data):
            return None
        
        if len(data) < self.params["period"] + 10:
            return None
        
        # Calculate indicators
        data = self.calculate_indicators(data)
        
        # Get current values
        current_rsi = data["rsi"].iloc[-1]
        current_price = Decimal(str(data["close"].iloc[-1]))
        prev_rsi = data["rsi"].iloc[-2] if len(data) > 1 else current_rsi
        
        # Check for valid RSI value
        if pd.isna(current_rsi):
            return None
        
        oversold = self.params["oversold"]
        overbought = self.params["overbought"]
        min_strength = self.params["min_strength"]
        
        signal = None
        
        # Check for oversold (buy signal)
        if current_rsi < oversold and prev_rsi >= oversold:
            # RSI crossed below oversold level - mean reversion buy
            strength = min(1.0, (oversold - current_rsi) / oversold + min_strength)
            signal = Signal(
                symbol="UNKNOWN",  # Should be set by caller
                direction="buy",
                strength=strength,
                price=current_price,
                timestamp=datetime.utcnow(),
                timeframe="1h",
                strategy=self.name,
                metadata={
                    "rsi": float(current_rsi),
                    "rsi_prev": float(prev_rsi),
                    "threshold": oversold,
                    "condition": "oversold_cross",
                }
            )
        
        # Check for overbought (sell signal)
        elif current_rsi > overbought and prev_rsi <= overbought:
            # RSI crossed above overbought level - mean reversion sell
            strength = min(1.0, (current_rsi - overbought) / (100 - overbought) + min_strength)
            signal = Signal(
                symbol="UNKNOWN",
                direction="sell",
                strength=strength,
                price=current_price,
                timestamp=datetime.utcnow(),
                timeframe="1h",
                strategy=self.name,
                metadata={
                    "rsi": float(current_rsi),
                    "rsi_prev": float(prev_rsi),
                    "threshold": overbought,
                    "condition": "overbought_cross",
                }
            )
        
        return signal
