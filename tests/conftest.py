"""
Test configuration and fixtures.
"""

import pytest
from fastapi.testclient import TestClient

from zyx_ai.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def sample_market_data():
    """Sample OHLCV data for testing."""
    import pandas as pd
    import numpy as np
    
    dates = pd.date_range(start="2024-01-01", periods=100, freq="H")
    data = pd.DataFrame({
        "open": np.random.uniform(30000, 40000, 100),
        "high": np.random.uniform(31000, 41000, 100),
        "low": np.random.uniform(29000, 39000, 100),
        "close": np.random.uniform(30000, 40000, 100),
        "volume": np.random.uniform(100, 1000, 100),
    }, index=dates)
    
    return data
