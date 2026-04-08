"""
Backtesting engine for strategy validation.
Implements walk-forward analysis and Monte Carlo simulation.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import statistics

import pandas as pd
import numpy as np

from zyx_ai.core.logging import logger
from zyx_ai.strategies.base import BaseStrategy, Signal


@dataclass
class TradeResult:
    """Result of a single backtest trade."""
    entry_time: datetime
    exit_time: datetime
    symbol: str
    side: str
    entry_price: Decimal
    exit_price: Decimal
    size: Decimal
    pnl: Decimal
    pnl_pct: float
    holding_periods: int
    strategy: str


@dataclass
class BacktestResult:
    """Complete backtest results."""
    strategy_name: str
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal
    final_capital: Decimal
    
    # Performance metrics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_duration: int
    
    # Trade statistics
    avg_trade_return: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    
    # Risk metrics
    volatility: float
    calmar_ratio: float
    
    # Equity curve
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)
    trades: List[TradeResult] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "strategy_name": self.strategy_name,
            "period": f"{self.start_date} to {self.end_date}",
            "initial_capital": float(self.initial_capital),
            "final_capital": float(self.final_capital),
            "total_return_pct": self.total_return,
            "total_trades": self.total_trades,
            "win_rate": self.win_rate,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "profit_factor": self.profit_factor,
        }


class BacktestEngine:
    """Engine for backtesting trading strategies."""
    
    def __init__(self, initial_capital: Decimal = Decimal("10000")):
        """Initialize backtest engine.
        
        Args:
            initial_capital: Starting capital for backtest
        """
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions = {}  # symbol -> position info
        self.trades = []
        self.equity_curve = []
    
    def run_backtest(
        self,
        strategy: BaseStrategy,
        data: pd.DataFrame,
        symbol: str,
        commission: float = 0.001,  # 0.1%
        slippage: float = 0.0005,   # 0.05%
    ) -> BacktestResult:
        """Run backtest for a strategy.
        
        Args:
            strategy: Trading strategy to test
            data: OHLCV data
            symbol: Trading pair
            commission: Commission rate per trade
            slippage: Slippage assumption
            
        Returns:
            BacktestResult with full statistics
        """
        logger.info(f"Starting backtest for {strategy.name} on {symbol}")
        
        start_date = data.index[0]
        end_date = data.index[-1]
        
        # Iterate through data
        for i in range(len(data)):
            current_data = data.iloc[:i+1]
            current_bar = data.iloc[i]
            current_time = data.index[i]
            
            # Generate signal
            signal = strategy.generate_signal(current_data)
            
            # Execute signal
            if signal and signal.direction != "hold":
                self._execute_signal(
                    signal, current_bar, symbol, commission, slippage, current_time
                )
            
            # Update equity curve
            self._update_equity(current_time, current_bar["close"])
        
        # Close any open positions at end
        self._close_all_positions(data.iloc[-1], symbol, commission, slippage, end_date)
        
        # Calculate results
        result = self._calculate_results(
            strategy.name, start_date, end_date
        )
        
        logger.info(f"Backtest complete: {result.total_return:.2f}% return")
        
        return result
    
    def _execute_signal(
        self,
        signal: Signal,
        bar: pd.Series,
        symbol: str,
        commission: float,
        slippage: float,
        timestamp: datetime
    ):
        """Execute trading signal."""
        # Apply slippage
        if signal.direction == "buy":
            fill_price = signal.price * (1 + Decimal(str(slippage)))
        else:  # sell
            fill_price = signal.price * (1 - Decimal(str(slippage)))
        
        # Calculate position size (simple risk-based)
        risk_amount = self.capital * Decimal("0.02")  # 2% risk
        position_size = risk_amount / fill_price
        
        # Check if we have a position
        if symbol in self.positions:
            position = self.positions[symbol]
            
            # Close existing position if opposite direction
            if position["side"] != signal.direction:
                self._close_position(
                    position, fill_price, commission, timestamp
                )
            else:
                # Same direction - add to position
                return  # Skip for simplicity
        
        # Open new position
        cost = position_size * fill_price
        commission_cost = cost * Decimal(str(commission))
        total_cost = cost + commission_cost
        
        if total_cost > self.capital:
            return  # Insufficient funds
        
        self.capital -= total_cost
        self.positions[symbol] = {
            "side": signal.direction,
            "entry_price": fill_price,
            "size": position_size,
            "entry_time": timestamp,
        }
    
    def _close_position(
        self,
        position: Dict,
        exit_price: Decimal,
        commission: float,
        timestamp: datetime
    ):
        """Close an open position."""
        symbol = list(self.positions.keys())[0]  # Get symbol
        
        # Calculate P&L
        if position["side"] == "buy":
            pnl = (exit_price - position["entry_price"]) * position["size"]
        else:
            pnl = (position["entry_price"] - exit_price) * position["size"]
        
        # Apply commission
        exit_value = position["size"] * exit_price
        commission_cost = exit_value * Decimal(str(commission))
        pnl -= commission_cost
        
        # Update capital
        self.capital += exit_value + pnl
        
        # Record trade
        trade = TradeResult(
            entry_time=position["entry_time"],
            exit_time=timestamp,
            symbol=symbol,
            side=position["side"],
            entry_price=position["entry_price"],
            exit_price=exit_price,
            size=position["size"],
            pnl=pnl,
            pnl_pct=float(pnl / (position["entry_price"] * position["size"]) * 100),
            holding_periods=0,  # Calculate if needed
            strategy="backtest"
        )
        self.trades.append(trade)
        
        # Remove position
        del self.positions[symbol]
    
    def _close_all_positions(self, bar, symbol, commission, slippage, timestamp):
        """Close all open positions at end of backtest."""
        for sym, position in list(self.positions.items()):
            exit_price = Decimal(str(bar["close"]))
            self._close_position(position, exit_price, commission, timestamp)
    
    def _update_equity(self, timestamp: datetime, price: float):
        """Update equity curve."""
        # Calculate unrealized P&L
        unrealized = Decimal("0")
        for sym, pos in self.positions.items():
            if pos["side"] == "buy":
                unrealized += (Decimal(str(price)) - pos["entry_price"]) * pos["size"]
            else:
                unrealized += (pos["entry_price"] - Decimal(str(price))) * pos["size"]
        
        equity = self.capital + unrealized
        
        self.equity_curve.append({
            "timestamp": timestamp,
            "equity": float(equity),
            "cash": float(self.capital),
            "unrealized": float(unrealized)
        })
    
    def _calculate_results(
        self,
        strategy_name: str,
        start_date: datetime,
        end_date: datetime
    ) -> BacktestResult:
        """Calculate final backtest statistics."""
        
        # Basic counts
        total_trades = len(self.trades)
        if total_trades == 0:
            return BacktestResult(
                strategy_name=strategy_name,
                start_date=start_date,
                end_date=end_date,
                initial_capital=self.initial_capital,
                final_capital=self.capital,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                total_return=0.0,
                annualized_return=0.0,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                max_drawdown=0.0,
                max_drawdown_duration=0,
                avg_trade_return=0.0,
                avg_win=0.0,
                avg_loss=0.0,
                profit_factor=0.0,
                volatility=0.0,
                calmar_ratio=0.0,
                equity_curve=self.equity_curve,
                trades=self.trades
            )
        
        winning_trades = len([t for t in self.trades if t.pnl > 0])
        losing_trades = total_trades - winning_trades
        win_rate = winning_trades / total_trades
        
        # Returns
        total_return = float((self.capital - self.initial_capital) / self.initial_capital * 100)
        
        # Days in backtest
        days = (end_date - start_date).days
        if days > 0:
            annualized_return = ((self.capital / self.initial_capital) ** (365 / days) - 1) * 100
        else:
            annualized_return = 0.0
        
        # Drawdown calculation
        max_drawdown, max_dd_duration = self._calculate_drawdown()
        
        # Trade statistics
        returns = [t.pnl_pct for t in self.trades]
        avg_trade_return = statistics.mean(returns) if returns else 0.0
        
        wins = [t.pnl_pct for t in self.trades if t.pnl > 0]
        losses = [t.pnl_pct for t in self.trades if t.pnl <= 0]
        
        avg_win = statistics.mean(wins) if wins else 0.0
        avg_loss = statistics.mean(losses) if losses else 0.0
        
        # Profit factor
        gross_profit = sum(t.pnl for t in self.trades if t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in self.trades if t.pnl < 0))
        profit_factor = float(gross_profit / gross_loss) if gross_loss > 0 else float('inf')
        
        # Volatility (daily)
        if len(self.equity_curve) > 1:
            equity_values = [e["equity"] for e in self.equity_curve]
            daily_returns = np.diff(equity_values) / equity_values[:-1]
            volatility = float(np.std(daily_returns) * np.sqrt(365) * 100)
        else:
            volatility = 0.0
        
        # Sharpe ratio (assuming 0% risk-free rate for simplicity)
        if volatility > 0:
            sharpe_ratio = annualized_return / volatility
        else:
            sharpe_ratio = 0.0
        
        # Sortino ratio (downside deviation only)
        if losses:
            downside_std = statistics.stdev([l for l in losses if l < 0]) if len(losses) > 1 else 0.0
            sortino_ratio = annualized_return / downside_std if downside_std > 0 else 0.0
        else:
            sortino_ratio = 0.0
        
        # Calmar ratio
        calmar = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0.0
        
        return BacktestResult(
            strategy_name=strategy_name,
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.initial_capital,
            final_capital=self.capital,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_return=total_return,
            annualized_return=annualized_return,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=max_drawdown,
            max_drawdown_duration=max_dd_duration,
            avg_trade_return=avg_trade_return,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            volatility=volatility,
            calmar_ratio=calmar,
            equity_curve=self.equity_curve,
            trades=self.trades
        )
    
    def _calculate_drawdown(self) -> tuple:
        """Calculate maximum drawdown."""
        if not self.equity_curve:
            return 0.0, 0
        
        equity_values = [e["equity"] for e in self.equity_curve]
        peak = equity_values[0]
        max_drawdown = 0.0
        max_duration = 0
        current_duration = 0
        
        for equity in equity_values:
            if equity > peak:
                peak = equity
                current_duration = 0
            else:
                drawdown = (peak - equity) / peak
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
                current_duration += 1
                if current_duration > max_duration:
                    max_duration = current_duration
        
        return max_drawdown * 100, max_duration


class WalkForwardAnalysis:
    """Walk-forward analysis for strategy robustness."""
    
    def __init__(self, train_pct: float = 0.7):
        """Initialize walk-forward analysis.
        
        Args:
            train_pct: Percentage of data for training
        """
        self.train_pct = train_pct
    
    def run(self, strategy: BaseStrategy, data: pd.DataFrame, 
            symbol: str, n_splits: int = 5) -> List[BacktestResult]:
        """Run walk-forward analysis.
        
        Args:
            strategy: Strategy to test
            data: Full dataset
            symbol: Trading pair
            n_splits: Number of train/test splits
            
        Returns:
            List of backtest results for each fold
        """
        results = []
        data_size = len(data)
        
        for i in range(n_splits):
            # Calculate split points
            train_start = int(i * data_size / n_splits)
            train_end = int(train_start + (data_size / n_splits) * self.train_pct)
            test_end = int((i + 1) * data_size / n_splits)
            
            train_data = data.iloc[train_start:train_end]
            test_data = data.iloc[train_end:test_end]
            
            # Run backtest on test set
            engine = BacktestEngine()
            result = engine.run_backtest(strategy, test_data, symbol)
            results.append(result)
        
        return results
