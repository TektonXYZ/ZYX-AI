"""
WebSocket manager for real-time market data.
Handles multiple exchange connections with automatic reconnection.
"""

import asyncio
import json
from typing import Dict, Set, Callable, Any
from datetime import datetime
import websockets
from websockets.exceptions import ConnectionClosed

from zyx_ai.core.logging import logger
from zyx_ai.core.config import settings


class WebSocketManager:
    """Manages WebSocket connections for real-time data."""
    
    def __init__(self):
        self.connections: Dict[str, websockets.WebSocketClientProtocol] = {}
        self.subscribers: Dict[str, Set[Callable]] = {}
        self.running = False
        self.reconnect_delay = 1.0
        self.max_reconnect_delay = 60.0
        
    async def connect_exchange(self, exchange: str, url: str):
        """Connect to exchange WebSocket."""
        while self.running:
            try:
                logger.info(f"Connecting to {exchange} WebSocket...")
                async with websockets.connect(url) as ws:
                    self.connections[exchange] = ws
                    self.reconnect_delay = 1.0  # Reset on success
                    
                    # Subscribe to channels
                    await self._subscribe(exchange, ws)
                    
                    # Handle messages
                    async for message in ws:
                        await self._handle_message(exchange, message)
                        
            except ConnectionClosed:
                logger.warning(f"{exchange} WebSocket closed, reconnecting...")
            except Exception as e:
                logger.error(f"{exchange} WebSocket error: {e}")
            
            # Exponential backoff
            await asyncio.sleep(self.reconnect_delay)
            self.reconnect_delay = min(
                self.reconnect_delay * 2, 
                self.max_reconnect_delay
            )
    
    async def _subscribe(self, exchange: str, ws: websockets.WebSocketClientProtocol):
        """Subscribe to market data channels."""
        if exchange == "binance":
            # Subscribe to ticker streams
            subscribe_msg = {
                "method": "SUBSCRIBE",
                "params": ["btcusdt@ticker", "ethusdt@ticker"],
                "id": 1
            }
            await ws.send(json.dumps(subscribe_msg))
    
    async def _handle_message(self, exchange: str, message: str):
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(message)
            
            # Notify subscribers
            if exchange in self.subscribers:
                for callback in self.subscribers[exchange]:
                    try:
                        await callback(data)
                    except Exception as e:
                        logger.error(f"Subscriber error: {e}")
                        
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from {exchange}: {message[:100]}")
    
    def subscribe(self, exchange: str, callback: Callable[[Any], None]):
        """Subscribe to exchange updates."""
        if exchange not in self.subscribers:
            self.subscribers[exchange] = set()
        self.subscribers[exchange].add(callback)
        logger.info(f"New subscriber for {exchange}")
    
    def unsubscribe(self, exchange: str, callback: Callable[[Any], None]):
        """Unsubscribe from exchange updates."""
        if exchange in self.subscribers:
            self.subscribers[exchange].discard(callback)
    
    async def start(self):
        """Start all WebSocket connections."""
        self.running = True
        
        # Start connections to multiple exchanges
        tasks = [
            self.connect_exchange("binance", "wss://stream.binance.com:9443/ws"),
            # Add more exchanges here
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def stop(self):
        """Stop all connections."""
        self.running = False
        
        for exchange, ws in self.connections.items():
            try:
                await ws.close()
                logger.info(f"Closed {exchange} connection")
            except Exception as e:
                logger.error(f"Error closing {exchange}: {e}")


# Global WebSocket manager instance
ws_manager = WebSocketManager()
