"""
Database models for XYZ Bot trading system.
Uses SQLAlchemy 2.0 with proper type annotations.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from enum import Enum

from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, ForeignKey, 
    Numeric, Enum as SQLEnum, Text, Index
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class TradeSide(str, Enum):
    """Trade direction."""
    LONG = "long"
    SHORT = "short"


class TradeStatus(str, Enum):
    """Trade status."""
    OPEN = "open"
    CLOSED = "closed"
    PENDING = "pending"
    CANCELLED = "cancelled"


class SignalDirection(str, Enum):
    """Signal direction."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class User(Base):
    """User account model."""
    
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
    is_superuser: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    # Relationships
    trades: Mapped[List["Trade"]] = relationship(back_populates="user")
    portfolio: Mapped[Optional["Portfolio"]] = relationship(back_populates="user")
    api_keys: Mapped[List["ApiKey"]] = relationship(back_populates="user")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username})>"


class Portfolio(Base):
    """Portfolio state for a user."""
    
    __tablename__ = "portfolios"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    
    # Balance
    balance: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("10000.0"))
    equity: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("10000.0"))
    margin_used: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0.0"))
    
    # Settings
    default_leverage: Mapped[int] = mapped_column(default=3)
    max_leverage: Mapped[int] = mapped_column(default=10)
    risk_per_trade: Mapped[float] = mapped_column(Float, default=0.02)
    
    # Statistics
    total_trades: Mapped[int] = mapped_column(default=0)
    winning_trades: Mapped[int] = mapped_column(default=0)
    total_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0.0"))
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="portfolio")
    
    def __repr__(self) -> str:
        return f"<Portfolio(id={self.id}, user_id={self.user_id}, equity={self.equity})>"
    
    @property
    def win_rate(self) -> float:
        """Calculate win rate."""
        if self.total_trades == 0:
            return 0.0
        return self.winning_trades / self.total_trades


class Trade(Base):
    """Trade execution record."""
    
    __tablename__ = "trades"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    
    # Trade details
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    side: Mapped[TradeSide] = mapped_column(SQLEnum(TradeSide))
    status: Mapped[TradeStatus] = mapped_column(
        SQLEnum(TradeStatus), default=TradeStatus.PENDING
    )
    
    # Position
    entry_price: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    exit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8), nullable=True)
    size: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    leverage: Mapped[int] = mapped_column(default=1)
    
    # Risk management
    stop_loss: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8), nullable=True)
    take_profit: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8), nullable=True)
    
    # P&L
    pnl: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8), nullable=True)
    pnl_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fees: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0.0"))
    
    # Exchange
    exchange: Mapped[str] = mapped_column(String(50), default="binance")
    exchange_order_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Timestamps
    opened_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Strategy
    strategy: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    signal_id: Mapped[Optional[int]] = mapped_column(ForeignKey("signals.id"), nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="trades")
    signal: Mapped[Optional["Signal"]] = relationship(back_populates="trade")
    
    # Indexes
    __table_args__ = (
        Index('ix_trades_symbol_status', 'symbol', 'status'),
        Index('ix_trades_user_opened', 'user_id', 'opened_at'),
    )
    
    def __repr__(self) -> str:
        return f"<Trade(id={self.id}, symbol={self.symbol}, side={self.side}, status={self.status})>"
    
    def calculate_pnl(self, current_price: Decimal) -> Decimal:
        """Calculate unrealized P&L."""
        if self.side == TradeSide.LONG:
            return (current_price - self.entry_price) / self.entry_price * self.size
        else:  # SHORT
            return (self.entry_price - current_price) / self.entry_price * self.size


class Signal(Base):
    """Trading signal generated by strategy."""
    
    __tablename__ = "signals"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Signal details
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    direction: Mapped[SignalDirection] = mapped_column(SQLEnum(SignalDirection))
    strength: Mapped[float] = mapped_column(Float)  # 0.0 to 1.0
    
    # Price data
    price: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    timeframe: Mapped[str] = mapped_column(String(10), default="1h")
    
    # Strategy
    strategy: Mapped[str] = mapped_column(String(50))
    strategy_version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    
    # Metadata (JSON)
    indicators: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Execution
    executed: Mapped[bool] = mapped_column(default=False)
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    trade: Mapped[Optional["Trade"]] = relationship(back_populates="signal")
    
    # Indexes
    __table_args__ = (
        Index('ix_signals_symbol_created', 'symbol', 'created_at'),
        Index('ix_signals_strategy_executed', 'strategy', 'executed'),
    )
    
    def __repr__(self) -> str:
        return f"<Signal(id={self.id}, symbol={self.symbol}, direction={self.direction}, strength={self.strength})>"


class ApiKey(Base):
    """API key for external integrations."""
    
    __tablename__ = "api_keys"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    
    key_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(100))
    scopes: Mapped[str] = mapped_column(String(255), default="read")  # comma-separated
    
    is_active: Mapped[bool] = mapped_column(default=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="api_keys")
    
    def __repr__(self) -> str:
        return f"<ApiKey(id={self.id}, name={self.name}, user_id={self.user_id})>"


class MarketData(Base):
    """Cached market data."""
    
    __tablename__ = "market_data"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    
    # OHLCV
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    open: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    high: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    low: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    close: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    volume: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    
    timeframe: Mapped[str] = mapped_column(String(10), default="1h")
    exchange: Mapped[str] = mapped_column(String(50), default="binance")
    
    # Indexes
    __table_args__ = (
        Index('ix_market_data_symbol_timeframe', 'symbol', 'timeframe'),
        Index('ix_market_data_timestamp', 'timestamp'),
    )
    
    def __repr__(self) -> str:
        return f"<MarketData(symbol={self.symbol}, timestamp={self.timestamp}, close={self.close})>"
