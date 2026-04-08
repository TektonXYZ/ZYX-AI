"""
MACD Trend Following Strategy.

Uses MACD line crossover with signal line for entry/exit.
"""

from decimal import Decimal
from typing import Optional, Dict, Any
from datetime import datetime

import pandas as pd
import numpy as np

from zyx_ai.strategies.base import BaseStrategy, Signal


class MACDStrategy(BaseStrategy):
    """MACD-based trend following strategy."""
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """Initialize MACD strategy.
        
        Args:
            params: Dictionary with keys:
                - fast_period: Fast EMA period (default: 12)
                - slow_period: Slow EMA period (default: 26)
                - signal_period: Signal EMA period (default: 9)
                - min_strength: Minimum signal strength (default: 0.7)
        """
        default_params = {
            "fast_period": 12,
            "slow_period": 26,
            "signal_period": 9,
            "min_strength": 0.7,
        }
        default_params.update(params or {})
        super().__init__("MACD Trend Following", default_params)
    
    def calculate_macd(self, prices: pd.Series) -> tuple:
        """Calculate MACD indicator.
        
        Args:
            prices: Price series
            
        Returns:
            Tuple of (macd_line, signal_line, histogram)
        """
        fast = self.params["fast_period"]
        slow = self.params["slow_period"]
        signal = self.params["signal_period"]
        
        # Calculate EMAs
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()
        
        # MACD line
        macd_line = ema_fast - ema_slow
        
        # Signal line
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        
        # Histogram
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate MACD and related indicators."""
        data = data.copy()
        
        # Calculate MACD
        macd, signal, hist = self.calculate_macd(data["close"])
        data["macd"] = macd
        data["macd_signal"] = signal
        data["macd_histogram"] = hist
        
        # Calculate trend strength
        data["trend_strength"] = abs(hist) / abs(macd) * 100
        
        return data
    
    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        """Generate signal based on MACD crossovers."""
        if not self.validate_data(data):
            return None
        
        min_periods = self.params["slow_period"] + self.params["signal_period"] + 10
        if len(data) < min_periods:
            return None
        
        # Calculate indicators
        data = self.calculate_indicators(data)
        
        # Get current and previous values
        macd_current = data["macd"].iloc[-1]
        signal_current = data["macd_signal"].iloc[-1]
        hist_current = data["macd_histogram"].iloc[-1]
        
        macd_prev = data["macd"].iloc[-2]
        signal_prev = data["macd_signal"].iloc[-2]
        
        current_price = Decimal(str(data["close"].iloc[-1]))
        
        # Check for valid values
        if pd.isna(macd_current) or pd.isna(signal_current):
            return None
        
        min_strength = self.params["min_strength"]
        signal = None
        
        # Bullish crossover: MACD crosses above signal line
        if macd_prev <= signal_prev and macd_current > signal_current:
            # Calculate strength based on histogram and trend
            strength = min(1.0, min_strength + abs(hist_current) / abs(macd_current) * 0.3)
            signal = Signal(
                symbol="UNKNOWN",
                direction="buy",
                strength=strength,
                price=current_price,
                timestamp=datetime.utcnow(),
                timeframe="1h",
                strategy=self.name,
                metadata={
                    "macd": float(macd_current),
                    "signal": float(signal_current),
                    "histogram": float(hist_current),
                    "condition": "bullish_crossover",
                }
            )
        
        # Bearish crossover: MACD crosses below signal line
        elif macd_prev >= signal_prev and macd_current < signal_current:
            strength = min(1.0, min_strength + abs(hist_current) / abs(macd_current) * 0.3)
            signal = Signal(
                symbol="UNKNOWN",
                direction="sell",
                strength=strength,
                price=current_price,
                timestamp=datetime.utcnow(),
                timeframe="1h",
                strategy=self.name,
                metadata={
                    "macd": float(macd_current),
                    "signal": float(signal_current),
                    "histogram": float(hist_current),
                    "condition": "bearish_crossover",
                }
            )
        
        return signal
