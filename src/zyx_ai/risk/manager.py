"""
Risk management module for position sizing and exposure control.
"""

from decimal import Decimal
from typing import Optional, Dict, Any
from dataclasses import dataclass

from zyx_ai.core.config import settings


@dataclass
class RiskAssessment:
    """Risk assessment for a potential trade."""
    can_trade: bool
    max_position_size: Decimal
    recommended_leverage: int
    stop_loss_price: Decimal
    take_profit_price: Decimal
    risk_amount: Decimal
    risk_percent: float
    warning_messages: list


class RiskManager:
    """Manages trading risk and position sizing."""
    
    def __init__(self):
        self.max_leverage = settings.max_leverage
        self.default_leverage = settings.default_leverage
        self.max_position_pct = Decimal(str(settings.max_position_pct))
        self.risk_per_trade = Decimal(str(settings.risk_per_trade))
        self.max_drawdown_pct = Decimal(str(settings.max_drawdown_pct))
    
    def calculate_position_size(
        self,
        portfolio_value: Decimal,
        entry_price: Decimal,
        signal_strength: float,
        leverage: int = None
    ) -> Decimal:
        """Calculate optimal position size using Kelly Criterion.
        
        Args:
            portfolio_value: Total portfolio value
            entry_price: Entry price per unit
            signal_strength: Signal confidence (0.0-1.0)
            leverage: Desired leverage (uses default if None)
            
        Returns:
            Position size in base currency
        """
        if leverage is None:
            leverage = self.default_leverage
        
        # Base risk amount (e.g., 2% of portfolio)
        base_risk = portfolio_value * self.risk_per_trade
        
        # Adjust by signal strength (stronger signals = larger positions)
        adjusted_risk = base_risk * (Decimal("0.5") + Decimal(str(signal_strength)))
        
        # Apply maximum position limit
        max_position = portfolio_value * self.max_position_pct
        
        # Calculate position size with leverage
        position_with_leverage = adjusted_risk * Decimal(leverage)
        
        # Take minimum of calculated size and max position
        position_size = min(position_with_leverage, max_position)
        
        return position_size
    
    def assess_trade_risk(
        self,
        symbol: str,
        side: str,
        entry_price: Decimal,
        portfolio_value: Decimal,
        portfolio_equity: Decimal,
        existing_positions: list,
        signal_strength: float = 0.5
    ) -> RiskAssessment:
        """Assess risk for a potential trade.
        
        Args:
            symbol: Trading pair
            side: "long" or "short"
            entry_price: Planned entry price
            portfolio_value: Total portfolio value
            portfolio_equity: Available equity
            existing_positions: List of current open positions
            signal_strength: Signal confidence level
            
        Returns:
            RiskAssessment with sizing and warnings
        """
        warnings = []
        can_trade = True
        
        # Check if we're already at max positions for symbol
        symbol_exposure = sum(
            p.size for p in existing_positions 
            if p.symbol == symbol
        )
        
        if symbol_exposure > portfolio_value * Decimal("0.2"):
            warnings.append(f"High exposure to {symbol}: {symbol_exposure}")
        
        # Calculate position size
        position_size = self.calculate_position_size(
            portfolio_value, entry_price, signal_strength
        )
        
        # Check if we have enough margin
        margin_required = position_size / Decimal(self.default_leverage)
        if margin_required > portfolio_equity * Decimal("0.5"):
            warnings.append("Position requires significant margin")
            can_trade = False
        
        # Calculate stop loss and take profit
        if side == "long":
            stop_loss = entry_price * (1 - Decimal(str(settings.default_stop_loss_pct)))
            take_profit = entry_price * (1 + Decimal(str(settings.default_take_profit_pct)))
        else:  # short
            stop_loss = entry_price * (1 + Decimal(str(settings.default_stop_loss_pct)))
            take_profit = entry_price * (1 - Decimal(str(settings.default_take_profit_pct)))
        
        # Calculate risk amount
        risk_amount = position_size * Decimal(str(settings.default_stop_loss_pct))
        risk_percent = float(risk_amount / portfolio_value * 100)
        
        # Check drawdown
        total_exposure = sum(p.size for p in existing_positions)
        total_exposure_pct = float(total_exposure / portfolio_value)
        
        if total_exposure_pct > 0.8:
            warnings.append("Portfolio highly leveraged")
        
        return RiskAssessment(
            can_trade=can_trade,
            max_position_size=position_size,
            recommended_leverage=self.default_leverage,
            stop_loss_price=stop_loss,
            take_profit_price=take_profit,
            risk_amount=risk_amount,
            risk_percent=risk_percent,
            warning_messages=warnings
        )
    
    def check_portfolio_health(
        self,
        portfolio_value: Decimal,
        portfolio_high: Decimal,
        open_positions: list
    ) -> Dict[str, Any]:
        """Check overall portfolio health.
        
        Args:
            portfolio_value: Current portfolio value
            portfolio_high: Highest portfolio value (for drawdown)
            open_positions: List of open positions
            
        Returns:
            Health metrics and warnings
        """
        warnings = []
        
        # Calculate drawdown
        if portfolio_high > 0:
            drawdown = (portfolio_high - portfolio_value) / portfolio_high
            drawdown_pct = float(drawdown * 100)
        else:
            drawdown_pct = 0.0
        
        # Check if drawdown exceeds limit
        if drawdown_pct > float(self.max_drawdown_pct * 100):
            warnings.append(f"Max drawdown exceeded: {drawdown_pct:.2f}%")
        
        # Calculate total exposure
        total_exposure = sum(p.size for p in open_positions)
        exposure_pct = float(total_exposure / portfolio_value * 100) if portfolio_value > 0 else 0
        
        # Calculate margin usage
        margin_used = sum(p.size / Decimal(p.leverage) for p in open_positions)
        margin_pct = float(margin_used / portfolio_value * 100) if portfolio_value > 0 else 0
        
        return {
            "healthy": len(warnings) == 0,
            "drawdown_pct": drawdown_pct,
            "max_drawdown_pct": float(self.max_drawdown_pct * 100),
            "exposure_pct": exposure_pct,
            "margin_pct": margin_pct,
            "warnings": warnings,
            "can_open_new_positions": len(warnings) == 0 and margin_pct < 80
        }
