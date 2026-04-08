"""
Performance monitoring and circuit breakers.
Prevents runaway strategies and monitors system health.
"""

import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import deque

from zyx_ai.core.logging import logger


@dataclass
class PerformanceMetrics:
    """Real-time performance metrics."""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    latency_ms: float
    throughput: float  # trades per second
    error_rate: float
    queue_depth: int


class CircuitBreaker:
    """Circuit breaker pattern for fault tolerance.
    
    Prevents cascading failures by stopping trading when
    errors exceed threshold.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 3
    ):
        """Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening
            recovery_timeout: Seconds before attempting recovery
            half_open_max_calls: Max calls in half-open state
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.state = "closed"  # closed, open, half-open
        self.failure_count = 0
        self.last_failure_time = None
        self.success_count = 0
        self.half_open_calls = 0
    
    def can_execute(self) -> bool:
        """Check if operation can execute."""
        if self.state == "closed":
            return True
        
        if self.state == "open":
            # Check if recovery timeout has passed
            if self.last_failure_time:
                elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
                if elapsed >= self.recovery_timeout:
                    logger.info("Circuit breaker entering half-open state")
                    self.state = "half-open"
                    self.half_open_calls = 0
                    return True
            return False
        
        if self.state == "half-open":
            if self.half_open_calls < self.half_open_max_calls:
                self.half_open_calls += 1
                return True
            return False
        
        return True
    
    def record_success(self):
        """Record successful operation."""
        if self.state == "half-open":
            self.success_count += 1
            if self.success_count >= self.half_open_max_calls:
                logger.info("Circuit breaker closing - recovery successful")
                self._reset()
        else:
            self.failure_count = max(0, self.failure_count - 1)
    
    def record_failure(self):
        """Record failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == "half-open":
            logger.warning("Circuit breaker opening - recovery failed")
            self.state = "open"
        elif self.failure_count >= self.failure_threshold:
            logger.error(f"Circuit breaker opening after {self.failure_count} failures")
            self.state = "open"
    
    def _reset(self):
        """Reset circuit breaker to closed state."""
        self.state = "closed"
        self.failure_count = 0
        self.success_count = 0
        self.half_open_calls = 0
        self.last_failure_time = None


class PerformanceMonitor:
    """Monitor system performance and trading metrics."""
    
    def __init__(self, window_size: int = 1000):
        """Initialize monitor.
        
        Args:
            window_size: Number of data points to keep
        """
        self.window_size = window_size
        self.metrics_history: deque = deque(maxlen=window_size)
        self.trade_times: deque = deque(maxlen=window_size)
        self.error_times: deque = deque(maxlen=window_size)
        self.latencies: deque = deque(maxlen=window_size)
        
        self.total_trades = 0
        self.total_errors = 0
        self.start_time = datetime.utcnow()
    
    def record_trade(self, latency_ms: float):
        """Record trade execution."""
        self.total_trades += 1
        self.trade_times.append(datetime.utcnow())
        self.latencies.append(latency_ms)
    
    def record_error(self):
        """Record error."""
        self.total_errors += 1
        self.error_times.append(datetime.utcnow())
    
    def record_latency(self, latency_ms: float):
        """Record operation latency."""
        self.latencies.append(latency_ms)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        now = datetime.utcnow()
        
        # Calculate rates over last minute
        one_minute_ago = now - timedelta(minutes=1)
        
        recent_trades = sum(1 for t in self.trade_times if t > one_minute_ago)
        recent_errors = sum(1 for t in self.error_times if t > one_minute_ago)
        
        # Latency statistics
        if self.latencies:
            latencies_list = list(self.latencies)
            avg_latency = sum(latencies_list) / len(latencies_list)
            p95_latency = sorted(latencies_list)[int(len(latencies_list) * 0.95)]
            p99_latency = sorted(latencies_list)[int(len(latencies_list) * 0.99)]
        else:
            avg_latency = p95_latency = p99_latency = 0
        
        # Error rate
        total_recent = recent_trades + recent_errors
        error_rate = recent_errors / total_recent if total_recent > 0 else 0
        
        # Uptime
        uptime_seconds = (now - self.start_time).total_seconds()
        
        return {
            "timestamp": now.isoformat(),
            "uptime_seconds": uptime_seconds,
            "total_trades": self.total_trades,
            "total_errors": self.total_errors,
            "trades_per_minute": recent_trades,
            "errors_per_minute": recent_errors,
            "error_rate": error_rate,
            "avg_latency_ms": avg_latency,
            "p95_latency_ms": p95_latency,
            "p99_latency_ms": p99_latency,
        }
    
    def check_health(self) -> Dict[str, Any]:
        """Check system health."""
        metrics = self.get_metrics()
        
        issues = []
        
        # Check error rate
        if metrics["error_rate"] > 0.1:  # 10% errors
            issues.append("high_error_rate")
        
        # Check latency
        if metrics["p95_latency_ms"] > 1000:  # 1 second
            issues.append("high_latency")
        
        # Check if trading
        if metrics["trades_per_minute"] == 0 and self.total_trades > 0:
            issues.append("trading_stalled")
        
        return {
            "healthy": len(issues) == 0,
            "issues": issues,
            "metrics": metrics
        }


class TradingRateLimiter:
    """Rate limiter for trading operations."""
    
    def __init__(self, max_trades_per_minute: int = 60, max_trades_per_hour: int = 500):
        """Initialize rate limiter.
        
        Args:
            max_trades_per_minute: Maximum trades allowed per minute
            max_trades_per_hour: Maximum trades allowed per hour
        """
        self.max_per_minute = max_trades_per_minute
        self.max_per_hour = max_trades_per_hour
        self.trade_times: deque = deque()
    
    def can_trade(self) -> bool:
        """Check if trading is allowed."""
        now = datetime.utcnow()
        
        # Clean old entries
        one_hour_ago = now - timedelta(hours=1)
        while self.trade_times and self.trade_times[0] < one_hour_ago:
            self.trade_times.popleft()
        
        # Check hourly limit
        if len(self.trade_times) >= self.max_per_hour:
            return False
        
        # Check minute limit
        one_minute_ago = now - timedelta(minutes=1)
        recent_trades = sum(1 for t in self.trade_times if t > one_minute_ago)
        
        if recent_trades >= self.max_per_minute:
            return False
        
        return True
    
    def record_trade(self):
        """Record a trade."""
        self.trade_times.append(datetime.utcnow())
    
    def get_status(self) -> Dict[str, int]:
        """Get current rate limit status."""
        now = datetime.utcnow()
        
        one_hour_ago = now - timedelta(hours=1)
        one_minute_ago = now - timedelta(minutes=1)
        
        hour_count = sum(1 for t in self.trade_times if t > one_hour_ago)
        minute_count = sum(1 for t in self.trade_times if t > one_minute_ago)
        
        return {
            "trades_last_hour": hour_count,
            "trades_last_minute": minute_count,
            "hourly_limit": self.max_per_hour,
            "minute_limit": self.max_per_minute,
            "hourly_remaining": self.max_per_hour - hour_count,
            "minute_remaining": self.max_per_minute - minute_count,
        }
