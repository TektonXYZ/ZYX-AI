"""
Order book analysis for high-frequency trading.
Implements Level 2 market data processing.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import heapq

from zyx_ai.core.logging import logger


@dataclass
class OrderBookLevel:
    """Single level in order book."""
    price: Decimal
    quantity: Decimal
    orders: int = 1
    
    def __lt__(self, other):
        """For heapq comparison."""
        return self.price < other.price


@dataclass
class OrderBook:
    """Full order book for a symbol."""
    symbol: str
    bids: List[OrderBookLevel] = field(default_factory=list)  # Max heap (negative prices)
    asks: List[OrderBookLevel] = field(default_factory=list)  # Min heap
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def best_bid(self) -> Optional[OrderBookLevel]:
        """Get best (highest) bid."""
        if self.bids:
            return self.bids[0]
        return None
    
    def best_ask(self) -> Optional[OrderBookLevel]:
        """Get best (lowest) ask."""
        if self.asks:
            return self.asks[0]
        return None
    
    def spread(self) -> Optional[Decimal]:
        """Calculate bid-ask spread."""
        bid = self.best_bid()
        ask = self.best_ask()
        if bid and ask:
            return ask.price - bid.price
        return None
    
    def spread_pct(self) -> Optional[float]:
        """Calculate spread as percentage."""
        spread = self.spread()
        bid = self.best_bid()
        if spread and bid:
            return float(spread / bid.price * 100)
        return None
    
    def mid_price(self) -> Optional[Decimal]:
        """Calculate mid price."""
        bid = self.best_bid()
        ask = self.best_ask()
        if bid and ask:
            return (bid.price + ask.price) / 2
        return None
    
    def weighted_mid_price(self) -> Optional[Decimal]:
        """Calculate volume-weighted mid price."""
        bid = self.best_bid()
        ask = self.best_ask()
        if bid and ask:
            total_qty = bid.quantity + ask.quantity
            if total_qty > 0:
                return (bid.price * ask.quantity + ask.price * bid.quantity) / total_qty
        return None
    
    def order_imbalance(self) -> Optional[float]:
        """Calculate order book imbalance (-1 to 1)."""
        if not self.bids or not self.asks:
            return None
        
        bid_volume = sum(level.quantity for level in self.bids[:5])
        ask_volume = sum(level.quantity for level in self.asks[:5])
        total = bid_volume + ask_volume
        
        if total > 0:
            return float((bid_volume - ask_volume) / total)
        return 0.0
    
    def depth(self, levels: int = 10) -> Tuple[Decimal, Decimal]:
        """Calculate total depth for bids and asks."""
        bid_depth = sum(level.quantity for level in self.bids[:levels])
        ask_depth = sum(level.quantity for level in self.asks[:levels])
        return bid_depth, ask_depth
    
    def get_vwap(self, side: str, quantity: Decimal) -> Optional[Decimal]:
        """Calculate VWAP for executing an order.
        
        Args:
            side: "buy" or "sell"
            quantity: Amount to trade
            
        Returns:
            Volume-weighted average price
        """
        remaining = quantity
        total_cost = Decimal("0")
        
        levels = self.asks if side == "buy" else self.bids
        
        for level in levels:
            if remaining <= 0:
                break
            
            take = min(remaining, level.quantity)
            total_cost += take * level.price
            remaining -= take
        
        if remaining > 0:
            logger.warning(f"Insufficient liquidity for {quantity} {self.symbol}")
            return None
        
        return total_cost / quantity


class OrderBookAnalyzer:
    """Analyzes order book for trading signals."""
    
    def __init__(self):
        self.order_books: Dict[str, OrderBook] = {}
        self.history: Dict[str, List[OrderBook]] = {}
        self.max_history = 1000
    
    def update(self, symbol: str, bids: List[Tuple[Decimal, Decimal]], 
               asks: List[Tuple[Decimal, Decimal]]):
        """Update order book with new data.
        
        Args:
            symbol: Trading pair
            bids: List of (price, quantity) tuples
            asks: List of (price, quantity) tuples
        """
        # Create order book levels
        bid_levels = [OrderBookLevel(price, qty) for price, qty in bids]
        ask_levels = [OrderBookLevel(price, qty) for price, qty in asks]
        
        # Sort: bids descending, asks ascending
        bid_levels.sort(key=lambda x: x.price, reverse=True)
        ask_levels.sort(key=lambda x: x.price)
        
        # Create order book
        book = OrderBook(
            symbol=symbol,
            bids=bid_levels,
            asks=ask_levels,
            timestamp=datetime.utcnow()
        )
        
        # Store
        self.order_books[symbol] = book
        
        # Add to history
        if symbol not in self.history:
            self.history[symbol] = []
        self.history[symbol].append(book)
        
        # Trim history
        if len(self.history[symbol]) > self.max_history:
            self.history[symbol] = self.history[symbol][-self.max_history:]
    
    def detect_large_orders(self, symbol: str, threshold: Decimal = Decimal("100000")) -> List[Dict]:
        """Detect large orders in the book.
        
        Args:
            symbol: Trading pair
            threshold: Minimum order value to flag
            
        Returns:
            List of large orders with metadata
        """
        book = self.order_books.get(symbol)
        if not book:
            return []
        
        large_orders = []
        
        for level in book.bids + book.asks:
            value = level.price * level.quantity
            if value >= threshold:
                large_orders.append({
                    "side": "bid" if level in book.bids else "ask",
                    "price": float(level.price),
                    "quantity": float(level.quantity),
                    "value": float(value),
                    "timestamp": book.timestamp.isoformat()
                })
        
        return large_orders
    
    def detect_iceberg_orders(self, symbol: str) -> List[Dict]:
        """Detect potential iceberg orders.
        
        Iceberg orders show as multiple small orders at same price level.
        
        Returns:
            List of suspected iceberg orders
        """
        book = self.order_books.get(symbol)
        if not book:
            return []
        
        icebergs = []
        
        for level in book.bids + book.asks:
            if level.orders > 5:  # Many small orders at same price
                icebergs.append({
                    "side": "bid" if level in book.bids else "ask",
                    "price": float(level.price),
                    "total_quantity": float(level.quantity),
                    "order_count": level.orders
                })
        
        return icebergs
    
    def calculate_slippage(self, symbol: str, side: str, 
                          quantity: Decimal) -> Optional[float]:
        """Calculate expected slippage for an order.
        
        Args:
            symbol: Trading pair
            side: "buy" or "sell"
            quantity: Order size
            
        Returns:
            Expected slippage as percentage
        """
        book = self.order_books.get(symbol)
        if not book:
            return None
        
        vwap = book.get_vwap(side, quantity)
        mid = book.mid_price()
        
        if vwap and mid:
            return float(abs(vwap - mid) / mid * 100)
        
        return None
    
    def get_support_resistance(self, symbol: str, 
                               levels: int = 5) -> Tuple[List[Decimal], List[Decimal]]:
        """Identify support and resistance levels from order book.
        
        Returns:
            Tuple of (support_levels, resistance_levels)
        """
        book = self.order_books.get(symbol)
        if not book:
            return [], []
        
        # Find price levels with high volume concentration
        bid_volumes = [(level.price, level.quantity) for level in book.bids[:20]]
        ask_volumes = [(level.price, level.quantity) for level in book.asks[:20]]
        
        # Sort by volume
        bid_volumes.sort(key=lambda x: x[1], reverse=True)
        ask_volumes.sort(key=lambda x: x[1], reverse=True)
        
        support = [price for price, _ in bid_volumes[:levels]]
        resistance = [price for price, _ in ask_volumes[:levels]]
        
        return support, resistance
