"""
Market Making Strategy - True HFT behavior.
Provides liquidity by placing bid/ask orders simultaneously.
"""

from decimal import Decimal
from typing import Optional, Dict, Any
from datetime import datetime

from zyx_ai.strategies.base import BaseStrategy, Signal
from zyx_ai.exchanges.orderbook import OrderBook
from zyx_ai.core.logging import logger


class MarketMakingStrategy(BaseStrategy):
    """Market making strategy with inventory management.
    
    Places simultaneous bid and ask orders to capture spread.
    Adjusts quotes based on inventory position.
    """
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """Initialize market maker.
        
        Args:
            params: Dictionary with keys:
                - spread_pct: Target spread percentage (default: 0.02)
                - order_size: Base order size (default: 0.01 BTC)
                - max_inventory: Maximum inventory exposure (default: 0.1 BTC)
                - inventory_skew: Adjust quotes based on inventory (default: True)
                - quote_duration: How long quotes stay active in seconds (default: 30)
        """
        default_params = {
            "spread_pct": 0.02,  # 0.02% spread
            "order_size": Decimal("0.01"),  # BTC
            "max_inventory": Decimal("0.1"),  # BTC
            "inventory_skew": True,
            "quote_duration": 30,
            "min_spread": Decimal("0.5"),  # Minimum absolute spread in quote currency
        }
        default_params.update(params or {})
        super().__init__("Market Maker", default_params)
        
        # Track inventory
        self.inventory = Decimal("0")
        self.cash = Decimal("10000")
        self.active_quotes = {}  # symbol -> {bid_id, ask_id, timestamp}
    
    def calculate_quotes(self, orderbook: OrderBook) -> Optional[Dict[str, Any]]:
        """Calculate bid and ask quotes based on order book.
        
        Args:
            orderbook: Current order book
            
        Returns:
            Dictionary with bid_price, ask_price, sizes
        """
        mid = orderbook.mid_price()
        if not mid:
            return None
        
        spread_pct = Decimal(str(self.params["spread_pct"])) / 100
        spread = mid * spread_pct
        
        # Ensure minimum spread
        min_spread = self.params["min_spread"]
        spread = max(spread, min_spread)
        
        # Base quotes
        bid_price = mid - spread / 2
        ask_price = mid + spread / 2
        
        # Inventory skew
        if self.params["inventory_skew"]:
            skew = self._calculate_inventory_skew()
            bid_price *= (1 - skew)
            ask_price *= (1 + skew)
        
        # Check if we can improve the market
        best_bid = orderbook.best_bid()
        best_ask = orderbook.best_ask()
        
        if best_bid and bid_price <= best_bid.price:
            bid_price = best_bid.price + Decimal("0.01")  # Penny jump
        
        if best_ask and ask_price >= best_ask.price:
            ask_price = best_ask.price - Decimal("0.01")  # Penny jump
        
        return {
            "bid_price": bid_price,
            "ask_price": ask_price,
            "bid_size": self.params["order_size"],
            "ask_size": self.params["order_size"],
            "spread": spread,
            "mid_price": mid
        }
    
    def _calculate_inventory_skew(self) -> Decimal:
        """Calculate inventory skew factor (-0.5 to 0.5).
        
        Positive inventory -> lower bids, higher asks (try to sell)
        Negative inventory -> higher bids, lower asks (try to buy)
        """
        max_inv = self.params["max_inventory"]
        if max_inv == 0:
            return Decimal("0")
        
        # Normalize inventory to -1 to 1
        normalized = self.inventory / max_inv
        normalized = max(min(normalized, Decimal("1")), Decimal("-1"))
        
        # Convert to skew factor (max 50% adjustment)
        return normalized * Decimal("0.5")
    
    def update_inventory(self, fill_side: str, size: Decimal, price: Decimal):
        """Update inventory after a fill.
        
        Args:
            fill_side: "buy" or "sell" (from our perspective)
            size: Filled quantity
            price: Fill price
        """
        if fill_side == "buy":
            self.inventory += size
            self.cash -= size * price
        else:  # sell
            self.inventory -= size
            self.cash += size * price
        
        logger.info(f"Inventory updated: {self.inventory} BTC, Cash: ${self.cash}")
    
    def should_requote(self, symbol: str, orderbook: OrderBook) -> bool:
        """Check if we should update our quotes.
        
        Requote if:
        - No active quotes
        - Quotes are stale
        - Market moved significantly
        """
        if symbol not in self.active_quotes:
            return True
        
        quote_info = self.active_quotes[symbol]
        age = (datetime.utcnow() - quote_info["timestamp"]).total_seconds()
        
        if age > self.params["quote_duration"]:
            return True
        
        # Check if market moved
        mid = orderbook.mid_price()
        if mid:
            last_mid = quote_info.get("mid_price")
            if last_mid and abs(mid - last_mid) / last_mid > Decimal("0.0005"):
                return True  # Market moved > 0.05%
        
        return False
    
    def generate_signal(self, data: Any) -> Optional[Signal]:
        """Market maker doesn't generate directional signals."""
        # Market maker operates differently - it manages quotes
        return None
    
    def get_pnl(self, current_price: Decimal) -> Dict[str, Decimal]:
        """Calculate current P&L.
        
        Args:
            current_price: Current market price
            
        Returns:
            Dictionary with P&L breakdown
        """
        inventory_value = self.inventory * current_price
        total_value = self.cash + inventory_value
        
        # Assuming we started with $10000 cash and 0 BTC
        starting_value = Decimal("10000")
        pnl = total_value - starting_value
        
        return {
            "cash": self.cash,
            "inventory": self.inventory,
            "inventory_value": inventory_value,
            "total_value": total_value,
            "pnl": pnl,
            "pnl_pct": pnl / starting_value * 100
        }


class StatisticalArbitrageStrategy(BaseStrategy):
    """Statistical arbitrage between correlated assets.
    
    Monitors correlation between pairs and trades mean reversion.
    """
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        default_params = {
            "lookback": 100,  # Periods for correlation calc
            "entry_zscore": 2.0,  # Z-score threshold for entry
            "exit_zscore": 0.5,  # Z-score threshold for exit
            "pairs": [("BTCUSDT", "ETHUSDT")],  # Correlated pairs
        }
        default_params.update(params or {})
        super().__init__("Statistical Arbitrage", default_params)
        
        self.price_history = {}
        self.spread_history = {}
    
    def update_prices(self, symbol: str, price: Decimal):
        """Update price history."""
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        
        self.price_history[symbol].append({
            "price": price,
            "timestamp": datetime.utcnow()
        })
        
        # Keep only lookback period
        lookback = self.params["lookback"]
        if len(self.price_history[symbol]) > lookback * 2:
            self.price_history[symbol] = self.price_history[symbol][-lookback * 2:]
    
    def calculate_correlation(self, pair: tuple) -> Optional[float]:
        """Calculate correlation between pair."""
        sym1, sym2 = pair
        
        if sym1 not in self.price_history or sym2 not in self.price_history:
            return None
        
        prices1 = [p["price"] for p in self.price_history[sym1][-self.params["lookback"]:]]
        prices2 = [p["price"] for p in self.price_history[sym2][-self.params["lookback"]:]]
        
        if len(prices1) < 10 or len(prices2) < 10:
            return None
        
        # Simple correlation calculation
        import numpy as np
        
        try:
            corr = np.corrcoef([float(p) for p in prices1], [float(p) for p in prices2])[0, 1]
            return corr
        except:
            return None
    
    def calculate_zscore(self, pair: tuple) -> Optional[float]:
        """Calculate z-score of the spread."""
        # TODO: Implement proper cointegration test
        return None


class LatencyArbitrageStrategy(BaseStrategy):
    """Latency arbitrage between exchanges.
    
    Exploits price discrepancies between fast and slow exchanges.
    """
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        default_params = {
            "min_discrepancy": 0.1,  # 0.1% minimum price difference
            "fast_exchange": "binance",
            "slow_exchange": "bybit",
            "max_hold_time": 5,  # Seconds to hold position
        }
        default_params.update(params or {})
        super().__init__("Latency Arbitrage", default_params)
        
        self.prices = {}  # exchange -> symbol -> price
        self.latency = {}  # exchange -> avg latency in ms
    
    def update_price(self, exchange: str, symbol: str, price: Decimal, timestamp: datetime):
        """Update price from exchange."""
        if exchange not in self.prices:
            self.prices[exchange] = {}
        
        self.prices[exchange][symbol] = {
            "price": price,
            "timestamp": timestamp
        }
    
    def check_arbitrage(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Check for arbitrage opportunity."""
        fast_ex = self.params["fast_exchange"]
        slow_ex = self.params["slow_exchange"]
        
        if fast_ex not in self.prices or slow_ex not in self.prices:
            return None
        
        if symbol not in self.prices[fast_ex] or symbol not in self.prices[slow_ex]:
            return None
        
        fast_price = self.prices[fast_ex][symbol]["price"]
        slow_price = self.prices[slow_ex][symbol]["price"]
        
        diff_pct = abs(fast_price - slow_price) / fast_price * 100
        
        if diff_pct < self.params["min_discrepancy"]:
            return None
        
        # Determine direction
        if fast_price > slow_price:
            # Fast exchange is higher - sell there, buy on slow
            return {
                "action": "sell_fast_buy_slow",
                "fast_exchange": fast_ex,
                "slow_exchange": slow_ex,
                "fast_price": float(fast_price),
                "slow_price": float(slow_price),
                "diff_pct": float(diff_pct),
                "symbol": symbol
            }
        else:
            return {
                "action": "buy_fast_sell_slow",
                "fast_exchange": fast_ex,
                "slow_exchange": slow_ex,
                "fast_price": float(fast_price),
                "slow_price": float(slow_price),
                "diff_pct": float(diff_pct),
                "symbol": symbol
            }
