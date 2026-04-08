"""
Base exchange client interface.
"""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Ticker:
    """Price ticker data."""
    symbol: str
    bid: Decimal
    ask: Decimal
    last: Decimal
    volume: Decimal
    timestamp: datetime


@dataclass
class Balance:
    """Account balance."""
    asset: str
    free: Decimal
    used: Decimal
    total: Decimal


@dataclass
class Order:
    """Order details."""
    id: str
    symbol: str
    side: str
    type: str
    price: Decimal
    amount: Decimal
    filled: Decimal
    remaining: Decimal
    status: str
    timestamp: datetime


class BaseExchange(ABC):
    """Base class for exchange integrations."""
    
    def __init__(self, api_key: str = None, secret: str = None, testnet: bool = True):
        """Initialize exchange client.
        
        Args:
            api_key: Exchange API key
            secret: Exchange API secret
            testnet: Use testnet/sandbox mode
        """
        self.api_key = api_key
        self.secret = secret
        self.testnet = testnet
        self.name = "BaseExchange"
    
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to exchange."""
        pass
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Get current price ticker.
        
        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            
        Returns:
            Ticker data or None if error
        """
        pass
    
    @abstractmethod
    async def get_balance(self, asset: str = None) -> List[Balance]:
        """Get account balance.
        
        Args:
            asset: Specific asset or all if None
            
        Returns:
            List of balances
        """
        pass
    
    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        side: str,
        type: str,
        amount: Decimal,
        price: Decimal = None
    ) -> Optional[Order]:
        """Place a new order.
        
        Args:
            symbol: Trading pair
            side: "buy" or "sell"
            type: "market" or "limit"
            amount: Order size
            price: Limit price (required for limit orders)
            
        Returns:
            Order details or None if error
        """
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an existing order.
        
        Args:
            order_id: Order ID to cancel
            symbol: Trading pair
            
        Returns:
            True if cancelled successfully
        """
        pass
    
    @abstractmethod
    async def get_order(self, order_id: str, symbol: str) -> Optional[Order]:
        """Get order details.
        
        Args:
            order_id: Order ID
            symbol: Trading pair
            
        Returns:
            Order details or None
        """
        pass
    
    @abstractmethod
    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get OHLCV candlestick data.
        
        Args:
            symbol: Trading pair
            timeframe: Candle timeframe (1m, 5m, 1h, 1d, etc.)
            limit: Number of candles
            
        Returns:
            List of OHLCV data
        """
        pass
