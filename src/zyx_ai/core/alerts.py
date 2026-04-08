"""
Alert system for notifications.
Supports multiple channels: webhook, email, Discord, Telegram.
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

import aiohttp

from zyx_ai.core.config import settings
from zyx_ai.core.logging import logger


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Alert message."""
    severity: AlertSeverity
    title: str
    message: str
    timestamp: datetime
    metadata: Dict[str, Any]


class AlertManager:
    """Manages and routes alerts to configured channels."""
    
    def __init__(self):
        """Initialize alert manager."""
        self.webhook_url = getattr(settings, 'ALERT_WEBHOOK_URL', None)
        self.discord_webhook = getattr(settings, 'DISCORD_WEBHOOK_URL', None)
        self.telegram_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        self.telegram_chat_id = getattr(settings, 'TELEGRAM_CHAT_ID', None)
        
        self.alert_history: List[Alert] = []
        self.max_history = 1000
    
    async def send_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.INFO,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Send alert to all configured channels.
        
        Args:
            title: Alert title
            message: Alert message
            severity: Alert severity level
            metadata: Additional data
        """
        alert = Alert(
            severity=severity,
            title=title,
            message=message,
            timestamp=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        # Store in history
        self.alert_history.append(alert)
        if len(self.alert_history) > self.max_history:
            self.alert_history.pop(0)
        
        # Send to channels
        tasks = []
        
        if self.webhook_url:
            tasks.append(self._send_webhook(alert))
        
        if self.discord_webhook:
            tasks.append(self._send_discord(alert))
        
        if self.telegram_token and self.telegram_chat_id:
            tasks.append(self._send_telegram(alert))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Always log
        self._log_alert(alert)
    
    async def _send_webhook(self, alert: Alert):
        """Send alert to generic webhook."""
        if not self.webhook_url:
            return
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "severity": alert.severity.value,
                    "title": alert.title,
                    "message": alert.message,
                    "timestamp": alert.timestamp.isoformat(),
                    "metadata": alert.metadata
                }
                
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        logger.warning(f"Webhook alert failed: {response.status}")
                        
        except Exception as e:
            logger.error(f"Error sending webhook alert: {e}")
    
    async def _send_discord(self, alert: Alert):
        """Send alert to Discord webhook."""
        if not self.discord_webhook:
            return
        
        # Color based on severity
        colors = {
            AlertSeverity.INFO: 3447003,      # Blue
            AlertSeverity.WARNING: 15105570,  # Orange
            AlertSeverity.ERROR: 15158332,    # Red
            AlertSeverity.CRITICAL: 16711680  # Dark Red
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                embed = {
                    "title": alert.title,
                    "description": alert.message,
                    "color": colors.get(alert.severity, 3447003),
                    "timestamp": alert.timestamp.isoformat(),
                    "fields": [
                        {"name": "Severity", "value": alert.severity.value.upper(), "inline": True},
                        {"name": "Time", "value": alert.timestamp.strftime("%H:%M:%S"), "inline": True}
                    ]
                }
                
                # Add metadata fields
                for key, value in alert.metadata.items():
                    embed["fields"].append({
                        "name": key,
                        "value": str(value)[:1000],  # Discord limit
                        "inline": True
                    })
                
                payload = {"embeds": [embed]}
                
                async with session.post(
                    self.discord_webhook,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status not in [200, 204]:
                        logger.warning(f"Discord alert failed: {response.status}")
                        
        except Exception as e:
            logger.error(f"Error sending Discord alert: {e}")
    
    async def _send_telegram(self, alert: Alert):
        """Send alert to Telegram."""
        if not self.telegram_token or not self.telegram_chat_id:
            return
        
        try:
            # Emoji based on severity
            emojis = {
                AlertSeverity.INFO: "ℹ️",
                AlertSeverity.WARNING: "⚠️",
                AlertSeverity.ERROR: "❌",
                AlertSeverity.CRITICAL: "🚨"
            }
            
            emoji = emojis.get(alert.severity, "ℹ️")
            
            text = f"{emoji} <b>{alert.title}</b>\n\n"
            text += f"{alert.message}\n\n"
            text += f"Severity: {alert.severity.value.upper()}\n"
            text += f"Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
            
            if alert.metadata:
                text += "<b>Details:</b>\n"
                for key, value in alert.metadata.items():
                    text += f"• {key}: {value}\n"
            
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            
            async with aiohttp.ClientSession() as session:
                payload = {
                    "chat_id": self.telegram_chat_id,
                    "text": text,
                    "parse_mode": "HTML"
                }
                
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        logger.warning(f"Telegram alert failed: {response.status}")
                        
        except Exception as e:
            logger.error(f"Error sending Telegram alert: {e}")
    
    def _log_alert(self, alert: Alert):
        """Log alert to system logger."""
        msg = f"[{alert.severity.value.upper()}] {alert.title}: {alert.message}"
        
        if alert.severity == AlertSeverity.CRITICAL:
            logger.critical(msg)
        elif alert.severity == AlertSeverity.ERROR:
            logger.error(msg)
        elif alert.severity == AlertSeverity.WARNING:
            logger.warning(msg)
        else:
            logger.info(msg)
    
    async def notify_trade(self, trade_data: Dict[str, Any]):
        """Send trade notification."""
        side = trade_data.get('side', 'unknown')
        symbol = trade_data.get('symbol', 'unknown')
        pnl = trade_data.get('pnl', 0)
        
        emoji = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"
        
        await self.send_alert(
            title=f"Trade {side.upper()} - {symbol}",
            message=f"{emoji} {side.upper()} {symbol}\nP&L: ${pnl:.2f}",
            severity=AlertSeverity.INFO if pnl >= 0 else AlertSeverity.WARNING,
            metadata=trade_data
        )
    
    async def notify_error(self, error_message: str, details: Optional[Dict] = None):
        """Send error notification."""
        await self.send_alert(
            title="Trading Error",
            message=error_message,
            severity=AlertSeverity.ERROR,
            metadata=details or {}
        )
    
    async def notify_large_drawdown(self, drawdown_pct: float):
        """Notify when large drawdown occurs."""
        await self.send_alert(
            title="⚠️ Large Drawdown Detected",
            message=f"Portfolio drawdown: {drawdown_pct:.2f}%",
            severity=AlertSeverity.WARNING if drawdown_pct < 20 else AlertSeverity.CRITICAL,
            metadata={"drawdown_pct": drawdown_pct}
        )
    
    def get_alert_history(
        self,
        severity: Optional[AlertSeverity] = None,
        limit: int = 100
    ) -> List[Alert]:
        """Get historical alerts."""
        alerts = self.alert_history
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        return alerts[-limit:]


# Global alert manager instance
alert_manager = AlertManager()
