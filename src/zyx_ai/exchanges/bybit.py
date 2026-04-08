"""
Bybit exchange integration.
"""

from decimal import Decimal
from typing import Optional, Dict, Any, List

import ccxt.async_support as ccxt

from zyx_ai.exchanges.base import BaseExchange, Ticker, Balance, Order
from zyx_ai.core.config import settings
from zyx_ai.core.logging import logger


class BybitClient(BaseExchange):
    """Bybit exchange client."""
    
    def __init__(self):
        """Initialize Bybit client."""
        super().__init__(
            api_key=settings.bybit_api_key,
            secret=settings.bybit_secret,
            testnet=settings.bybit_testnet
        )
        self.name = "Bybit"
        self.client = None
    
    async def connect(self) -> bool:
        """Connect to Bybit API."""
        try:
            config = {
                'apiKey': self.api_key,
                'secret': self.secret,
                'enableRateLimit': True,
            }
            
            if self.testnet:
                config['sandbox'] = True
            
            self.client = ccxt.bybit(config)
            
            await self.client.load_markets()
            
            logger.info(f"Connected to Bybit ({'testnet' if self.testnet else 'live'})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Bybit: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from exchange."""
        if self.client:
            await self.client.close()
            logger.info("Disconnected from Bybit")
    
    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Get current price ticker."""
        try:
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
            logger.error(f"Error fetching Bybit ticker: {e}")
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
            logger.error(f"Error fetching Bybit balance: {e}")
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
            logger.error(f"Error placing Bybit order: {e}")
            return None
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an order."""
        try:
            await self.client.cancel_order(order_id, symbol)
            return True
        except Exception as e:
            logger.error(f"Error cancelling Bybit order: {e}")
            return False
    
    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get OHLCV data."""
        try:
            ohlcv = await self.client.fetch_ohlcv(symbol, timeframe, limit=limit)
            
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
            logger.error(f"Error fetching Bybit OHLCV: {e}")
            return []
