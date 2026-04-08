"""
Binance exchange integration.
"""

from decimal import Decimal
from typing import Optional, Dict, Any, List
import asyncio

import ccxt.async_support as ccxt

from zyx_ai.exchanges.base import BaseExchange, Ticker, Balance, Order
from zyx_ai.core.config import settings
from zyx_ai.core.logging import logger


class BinanceClient(BaseExchange):
    """Binance exchange client using CCXT."""
    
    def __init__(self):
        """Initialize Binance client."""
        super().__init__(
            api_key=settings.binance_api_key,
            secret=settings.binance_secret,
            testnet=settings.binance_testnet
        )
        self.name = "Binance"
        self.client = None
    
    async def connect(self) -> bool:
        """Connect to Binance API."""
        try:
            config = {
                'apiKey': self.api_key,
                'secret': self.secret,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future',  # Use futures for leverage
                }
            }
            
            if self.testnet:
                config['sandbox'] = True
            
            self.client = ccxt.binance(config)
            
            # Test connection
            await self.client.load_markets()
            
            logger.info(f"Connected to Binance ({'testnet' if self.testnet else 'live'})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Binance: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from exchange."""
        if self.client:
            await self.client.close()
            logger.info("Disconnected from Binance")
    
    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Get current price ticker."""
        try:
            # Normalize symbol format
            symbol = symbol.replace("/", "")
            
            ticker_data = await self.client.fetch_ticker(symbol)
            
            return Ticker(
                symbol=symbol,
                bid=Decimal(str(ticker_data['bid'])),
                ask=Decimal(str(ticker_data['ask'])),
                last=Decimal(str(ticker_data['last'])),
                volume=Decimal(str(ticker_data['baseVolume'])),
                timestamp=ticker_data['timestamp']
            )
            
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            return None
    
    async def get_balance(self, asset: str = None) -> List[Balance]:
        """Get account balance."""
        try:
            balance_data = await self.client.fetch_balance()
            
            balances = []
            for asset_code, data in balance_data.items():
                if isinstance(data, dict) and 'total' in data:
                    if asset and asset_code != asset:
                        continue
                    
                    balances.append(Balance(
                        asset=asset_code,
                        free=Decimal(str(data.get('free', 0))),
                        used=Decimal(str(data.get('used', 0))),
                        total=Decimal(str(data.get('total', 0)))
                    ))
            
            return balances
            
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            return []
    
    async def place_order(
        self,
        symbol: str,
        side: str,
        type: str,
        amount: Decimal,
        price: Decimal = None
    ) -> Optional[Order]:
        """Place a new order."""
        try:
            symbol = symbol.replace("/", "")
            
            params = {}
            if type == "limit" and price:
                params['price'] = float(price)
            
            order_data = await self.client.create_order(
                symbol=symbol,
                type=type,
                side=side,
                amount=float(amount),
                **params
            )
            
            return Order(
                id=order_data['id'],
                symbol=symbol,
                side=side,
                type=type,
                price=Decimal(str(order_data.get('price', 0))),
                amount=Decimal(str(order_data['amount'])),
                filled=Decimal(str(order_data.get('filled', 0))),
                remaining=Decimal(str(order_data.get('remaining', 0))),
                status=order_data['status'],
                timestamp=order_data['timestamp']
            )
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an existing order."""
        try:
            symbol = symbol.replace("/", "")
            await self.client.cancel_order(order_id, symbol)
            logger.info(f"Cancelled order {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False
    
    async def get_order(self, order_id: str, symbol: str) -> Optional[Order]:
        """Get order details."""
        try:
            symbol = symbol.replace("/", "")
            order_data = await self.client.fetch_order(order_id, symbol)
            
            return Order(
                id=order_data['id'],
                symbol=symbol,
                side=order_data['side'],
                type=order_data['type'],
                price=Decimal(str(order_data.get('price', 0))),
                amount=Decimal(str(order_data['amount'])),
                filled=Decimal(str(order_data.get('filled', 0))),
                remaining=Decimal(str(order_data.get('remaining', 0))),
                status=order_data['status'],
                timestamp=order_data['timestamp']
            )
            
        except Exception as e:
            logger.error(f"Error fetching order: {e}")
            return None
    
    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get OHLCV data."""
        try:
            symbol = symbol.replace("/", "")
            
            ohlcv = await self.client.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            # Convert to list of dicts
            candles = []
            for candle in ohlcv:
                candles.append({
                    'timestamp': candle[0],
                    'open': Decimal(str(candle[1])),
                    'high': Decimal(str(candle[2])),
                    'low': Decimal(str(candle[3])),
                    'close': Decimal(str(candle[4])),
                    'volume': Decimal(str(candle[5]))
                })
            
            return candles
            
        except Exception as e:
            logger.error(f"Error fetching OHLCV: {e}")
            return []
