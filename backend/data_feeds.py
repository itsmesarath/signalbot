"""Data Feed Managers for Rithmic, Binance, and Simulated Data"""
import asyncio
import json
import random
import math
from datetime import datetime
from typing import Optional, Callable, Dict, List, Any
import logging
import websockets
import httpx
from models import Trade, OrderBook, OrderBookLevel, DataSource

logger = logging.getLogger(__name__)


class BinanceFeed:
    """Binance WebSocket feed for cryptocurrency data."""
    
    WEBSOCKET_URL = "wss://stream.binance.com:9443/ws"
    REST_URL = "https://api.binance.com/api/v3"
    
    def __init__(self):
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected = False
        self.symbol = "btcusdt"
        self.on_trade: Optional[Callable] = None
        self.on_order_book: Optional[Callable] = None
        self.on_connection_change: Optional[Callable] = None
        self._running = False
        self._reconnect_delay = 1
        self._max_reconnect_delay = 60
    
    async def connect(self, symbol: str = "btcusdt"):
        """Connect to Binance WebSocket streams."""
        self.symbol = symbol.lower()
        self._running = True
        
        while self._running:
            try:
                # Subscribe to trade and depth streams
                stream_url = f"{self.WEBSOCKET_URL}/{self.symbol}@aggTrade/{self.symbol}@depth20@100ms"
                
                async with websockets.connect(stream_url) as ws:
                    self.ws = ws
                    self.is_connected = True
                    self._reconnect_delay = 1
                    
                    if self.on_connection_change:
                        await self.on_connection_change(True, self.symbol.upper())
                    
                    logger.info(f"Connected to Binance stream for {self.symbol.upper()}")
                    
                    async for message in ws:
                        if not self._running:
                            break
                        await self._handle_message(json.loads(message))
                        
            except websockets.exceptions.ConnectionClosed:
                logger.warning("Binance connection closed, reconnecting...")
            except Exception as e:
                logger.error(f"Binance connection error: {e}")
            finally:
                self.is_connected = False
                if self.on_connection_change:
                    await self.on_connection_change(False, self.symbol.upper())
            
            if self._running:
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(self._reconnect_delay * 2, self._max_reconnect_delay)
    
    async def _handle_message(self, data: Dict):
        """Handle incoming WebSocket message."""
        try:
            if 'e' in data:
                event_type = data['e']
                
                if event_type == 'aggTrade':
                    # Aggregate trade
                    trade = Trade(
                        symbol=data['s'],
                        price=float(data['p']),
                        quantity=float(data['q']),
                        timestamp=datetime.fromtimestamp(data['T'] / 1000),
                        is_buyer_maker=data['m'],  # True = sell aggressor
                        trade_id=str(data['a'])
                    )
                    if self.on_trade:
                        await self.on_trade(trade)
                
                elif event_type == 'depthUpdate':
                    # Order book update
                    bids = [OrderBookLevel(price=float(b[0]), quantity=float(b[1])) for b in data['b']]
                    asks = [OrderBookLevel(price=float(a[0]), quantity=float(a[1])) for a in data['a']]
                    
                    if bids and asks:
                        order_book = OrderBook(
                            symbol=data['s'],
                            timestamp=datetime.fromtimestamp(data['E'] / 1000),
                            bids=sorted(bids, key=lambda x: x.price, reverse=True),
                            asks=sorted(asks, key=lambda x: x.price),
                            best_bid=bids[0].price if bids else 0,
                            best_ask=asks[0].price if asks else 0,
                            spread=asks[0].price - bids[0].price if bids and asks else 0,
                            mid_price=(bids[0].price + asks[0].price) / 2 if bids and asks else 0
                        )
                        if self.on_order_book:
                            await self.on_order_book(order_book)
            
            # Handle depth snapshot format
            elif 'bids' in data and 'asks' in data:
                bids = [OrderBookLevel(price=float(b[0]), quantity=float(b[1])) for b in data['bids'][:20]]
                asks = [OrderBookLevel(price=float(a[0]), quantity=float(a[1])) for a in data['asks'][:20]]
                
                if bids and asks:
                    order_book = OrderBook(
                        symbol=self.symbol.upper(),
                        timestamp=datetime.utcnow(),
                        bids=sorted(bids, key=lambda x: x.price, reverse=True),
                        asks=sorted(asks, key=lambda x: x.price),
                        best_bid=bids[0].price if bids else 0,
                        best_ask=asks[0].price if asks else 0,
                        spread=asks[0].price - bids[0].price if bids and asks else 0,
                        mid_price=(bids[0].price + asks[0].price) / 2 if bids and asks else 0
                    )
                    if self.on_order_book:
                        await self.on_order_book(order_book)
                        
        except Exception as e:
            logger.error(f"Error handling Binance message: {e}")
    
    async def change_symbol(self, new_symbol: str):
        """Change the trading symbol."""
        if self.ws:
            await self.disconnect()
        await self.connect(new_symbol)
    
    async def disconnect(self):
        """Disconnect from Binance."""
        self._running = False
        if self.ws:
            await self.ws.close()
            self.ws = None
        self.is_connected = False
    
    @staticmethod
    async def get_exchange_info() -> List[str]:
        """Get list of available trading pairs."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{BinanceFeed.REST_URL}/exchangeInfo")
                data = response.json()
                symbols = [s['symbol'] for s in data['symbols'] 
                          if s['status'] == 'TRADING' and s['quoteAsset'] == 'USDT']
                return sorted(symbols)[:50]  # Return top 50 USDT pairs
        except Exception as e:
            logger.error(f"Error fetching exchange info: {e}")
            return ["BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "SOLUSDT"]


class RithmicFeed:
    """Rithmic connection manager (placeholder for real implementation).
    
    Note: Real Rithmic integration requires their proprietary API and credentials.
    This class provides the interface and simulated behavior for development.
    """
    
    def __init__(self):
        self.is_connected = False
        self.username = ""
        self.password = ""
        self.server = "Rithmic Paper Trading"
        self.gateway = "Chicago"
        self.on_trade: Optional[Callable] = None
        self.on_order_book: Optional[Callable] = None
        self.on_connection_change: Optional[Callable] = None
        self._running = False
    
    async def connect(self, username: str, password: str, server: str = "Rithmic Paper Trading", gateway: str = "Chicago"):
        """Attempt to connect to Rithmic.
        
        Note: This is a placeholder. Real implementation would use Rithmic's API.
        """
        self.username = username
        self.password = password
        self.server = server
        self.gateway = gateway
        
        # Validate credentials (placeholder logic)
        if not username or not password:
            raise ValueError("Rithmic credentials required")
        
        # In a real implementation, this would connect to Rithmic's servers
        # For now, we'll simulate the connection
        self._running = True
        self.is_connected = True
        
        if self.on_connection_change:
            await self.on_connection_change(True, "XAUUSD")
        
        logger.info(f"Connected to Rithmic ({server}) - Simulated")
        
        # Start simulated data feed for XAUUSD
        asyncio.create_task(self._simulate_xauusd_feed())
    
    async def _simulate_xauusd_feed(self):
        """Simulate XAUUSD tick data for development/testing."""
        base_price = 2350.0  # Base gold price
        volatility = 0.5
        
        while self._running:
            try:
                # Generate realistic price movement
                change = random.gauss(0, volatility)
                base_price += change
                
                # Generate trade
                trade = Trade(
                    symbol="XAUUSD",
                    price=round(base_price + random.uniform(-0.1, 0.1), 2),
                    quantity=round(random.uniform(0.1, 10.0), 2),
                    timestamp=datetime.utcnow(),
                    is_buyer_maker=random.random() > 0.5,
                    trade_id=str(random.randint(100000, 999999))
                )
                
                if self.on_trade:
                    await self.on_trade(trade)
                
                # Generate order book
                spread = random.uniform(0.1, 0.3)
                best_bid = round(base_price - spread / 2, 2)
                best_ask = round(base_price + spread / 2, 2)
                
                bids = []
                asks = []
                for i in range(20):
                    bids.append(OrderBookLevel(
                        price=round(best_bid - i * 0.1, 2),
                        quantity=round(random.uniform(1, 50), 2)
                    ))
                    asks.append(OrderBookLevel(
                        price=round(best_ask + i * 0.1, 2),
                        quantity=round(random.uniform(1, 50), 2)
                    ))
                
                order_book = OrderBook(
                    symbol="XAUUSD",
                    timestamp=datetime.utcnow(),
                    bids=bids,
                    asks=asks,
                    best_bid=best_bid,
                    best_ask=best_ask,
                    spread=spread,
                    mid_price=round((best_bid + best_ask) / 2, 2)
                )
                
                if self.on_order_book:
                    await self.on_order_book(order_book)
                
                await asyncio.sleep(random.uniform(0.05, 0.2))  # 50-200ms intervals
                
            except Exception as e:
                logger.error(f"Error in Rithmic simulation: {e}")
                await asyncio.sleep(1)
    
    async def disconnect(self):
        """Disconnect from Rithmic."""
        self._running = False
        self.is_connected = False
        if self.on_connection_change:
            await self.on_connection_change(False, "XAUUSD")


class SimulatedFeed:
    """Simulated market data feed for testing without external connections."""
    
    def __init__(self):
        self.is_connected = False
        self.symbol = "SIMULATED"
        self.on_trade: Optional[Callable] = None
        self.on_order_book: Optional[Callable] = None
        self.on_connection_change: Optional[Callable] = None
        self._running = False
        self._base_price = 100.0
    
    async def connect(self, symbol: str = "SIMULATED", base_price: float = 100.0):
        """Start simulated feed."""
        self.symbol = symbol
        self._base_price = base_price
        self._running = True
        self.is_connected = True
        
        if self.on_connection_change:
            await self.on_connection_change(True, symbol)
        
        asyncio.create_task(self._generate_data())
    
    async def _generate_data(self):
        """Generate simulated market data with realistic patterns."""
        trend = 0
        trend_duration = 0
        
        while self._running:
            try:
                # Change trend periodically
                trend_duration += 1
                if trend_duration > random.randint(50, 200):
                    trend = random.choice([-1, 0, 1]) * random.uniform(0.01, 0.05)
                    trend_duration = 0
                
                # Price movement
                noise = random.gauss(0, 0.1)
                self._base_price += trend + noise
                self._base_price = max(self._base_price, 1)  # Prevent negative prices
                
                # Generate trade with realistic volume distribution
                volume = random.paretovariate(1.5)  # Fat-tailed distribution
                is_buyer = random.random() > 0.5 + (trend * 2)  # Trend influences direction
                
                trade = Trade(
                    symbol=self.symbol,
                    price=round(self._base_price, 4),
                    quantity=round(min(volume, 100), 4),
                    timestamp=datetime.utcnow(),
                    is_buyer_maker=not is_buyer,
                    trade_id=str(random.randint(1, 1000000))
                )
                
                if self.on_trade:
                    await self.on_trade(trade)
                
                # Generate order book every few trades
                if random.random() > 0.7:
                    spread = random.uniform(0.01, 0.05) * self._base_price / 100
                    mid = self._base_price
                    
                    bids = []
                    asks = []
                    for i in range(20):
                        bid_price = mid - spread / 2 - i * spread * 0.5
                        ask_price = mid + spread / 2 + i * spread * 0.5
                        
                        # Volume decreases with distance from mid
                        bid_vol = random.uniform(10, 100) / (i + 1)
                        ask_vol = random.uniform(10, 100) / (i + 1)
                        
                        bids.append(OrderBookLevel(price=round(bid_price, 4), quantity=round(bid_vol, 4)))
                        asks.append(OrderBookLevel(price=round(ask_price, 4), quantity=round(ask_vol, 4)))
                    
                    order_book = OrderBook(
                        symbol=self.symbol,
                        timestamp=datetime.utcnow(),
                        bids=bids,
                        asks=asks,
                        best_bid=bids[0].price,
                        best_ask=asks[0].price,
                        spread=round(asks[0].price - bids[0].price, 4),
                        mid_price=round(mid, 4)
                    )
                    
                    if self.on_order_book:
                        await self.on_order_book(order_book)
                
                await asyncio.sleep(random.uniform(0.02, 0.1))
                
            except Exception as e:
                logger.error(f"Error in simulated feed: {e}")
                await asyncio.sleep(1)
    
    async def disconnect(self):
        """Stop simulated feed."""
        self._running = False
        self.is_connected = False
        if self.on_connection_change:
            await self.on_connection_change(False, self.symbol)
