"""
Machine learning features for strategy enhancement.
Feature engineering and model inference.
"""

from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler


class FeatureEngineer:
    """Engineer features from market data for ML models."""
    
    def __init__(self):
        self.scaler = StandardScaler()
    
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create technical features from OHLCV data.
        
        Args:
            df: DataFrame with OHLCV columns
            
        Returns:
            DataFrame with added feature columns
        """
        data = df.copy()
        
        # Price-based features
        data['returns'] = data['close'].pct_change()
        data['log_returns'] = np.log(data['close'] / data['close'].shift(1))
        
        # Volatility
        data['volatility_5'] = data['returns'].rolling(window=5).std()
        data['volatility_20'] = data['returns'].rolling(window=20).std()
        
        # Moving averages
        for window in [5, 10, 20, 50]:
            data[f'ma_{window}'] = data['close'].rolling(window=window).mean()
            data[f'ma_ratio_{window}'] = data['close'] / data[f'ma_{window}']
        
        # Price channels
        data['high_20'] = data['high'].rolling(window=20).max()
        data['low_20'] = data['low'].rolling(window=20).min()
        data['channel_position'] = (data['close'] - data['low_20']) / (data['high_20'] - data['low_20'])
        
        # Volume features
        data['volume_ma'] = data['volume'].rolling(window=20).mean()
        data['volume_ratio'] = data['volume'] / data['volume_ma']
        
        # Candlestick features
        data['body'] = (data['close'] - data['open']) / data['open']
        data['upper_shadow'] = (data['high'] - data[['open', 'close']].max(axis=1)) / data['open']
        data['lower_shadow'] = (data[['open', 'close']].min(axis=1) - data['low']) / data['open']
        
        # Momentum
        data['momentum_10'] = data['close'] / data['close'].shift(10) - 1
        data['momentum_30'] = data['close'] / data['close'].shift(30) - 1
        
        return data.dropna()
    
    def select_features(self, df: pd.DataFrame, target_col: str = 'returns') -> pd.DataFrame:
        """Select most relevant features using correlation.
        
        Args:
            df: DataFrame with features
            target_col: Target variable column
            
        Returns:
            DataFrame with selected features
        """
        # Calculate correlations with target
        correlations = df.corr()[target_col].abs().sort_values(ascending=False)
        
        # Select top features (excluding target itself)
        top_features = correlations[1:21].index.tolist()
        
        return df[top_features + [target_col]]


class SignalEnsemble:
    """Ensemble multiple strategies for robust signals."""
    
    def __init__(self, strategies: List[Any], weights: Optional[List[float]] = None):
        """Initialize ensemble.
        
        Args:
            strategies: List of strategy objects
            weights: Optional weights for each strategy
        """
        self.strategies = strategies
        self.weights = weights or [1.0 / len(strategies)] * len(strategies)
    
    def generate_composite_signal(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Generate composite signal from all strategies.
        
        Args:
            data: Market data
            
        Returns:
            Dictionary with composite signal and metadata
        """
        signals = []
        
        for strategy, weight in zip(self.strategies, self.weights):
            signal = strategy.generate_signal(data)
            if signal:
                signals.append({
                    'direction': 1 if signal.direction == 'buy' else -1 if signal.direction == 'sell' else 0,
                    'strength': signal.strength * weight,
                    'strategy': strategy.name
                })
        
        if not signals:
            return {'direction': 'hold', 'strength': 0.0, 'components': []}
        
        # Weighted average
        avg_direction = sum(s['direction'] * s['strength'] for s in signals) / sum(s['strength'] for s in signals)
        avg_strength = sum(s['strength'] for s in signals)
        
        # Determine composite direction
        if avg_direction > 0.3:
            direction = 'buy'
        elif avg_direction < -0.3:
            direction = 'sell'
        else:
            direction = 'hold'
        
        return {
            'direction': direction,
            'strength': min(avg_strength, 1.0),
            'components': signals,
            'consensus': avg_direction
        }
