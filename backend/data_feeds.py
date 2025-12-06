"""Data Feed Managers for Rithmic, Binance, and Simulated Data

Rithmic: Uses async_rithmic library for real market data
Binance: Uses public WebSocket API with testnet fallback
Simulated: Generates realistic test data
"""
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

# Try to import async_rithmic
try:
    from async_rithmic import RithmicClient, DataType, LastTradePresenceBits, BestBidOfferPresenceBits
    RITHMIC_AVAILABLE = True
except ImportError:
    RITHMIC_AVAILABLE = False
    logger.warning("async_rithmic not installed. Rithmic feed will use simulation mode.")


class BinanceFeed:
    """Binance WebSocket feed for cryptocurrency data.
    
    Supports both mainnet and testnet endpoints.
    Falls back to testnet if mainnet returns 451 (geographic restriction).
    """
    
    # Mainnet endpoints
    WEBSOCKET_URL = "wss://stream.binance.com:9443/ws"
    REST_URL = "https://api.binance.com/api/v3"
    
    # Testnet endpoints (no geographic restrictions)
    TESTNET_WEBSOCKET_URL = "wss://testnet.binance.vision/ws"
    TESTNET_REST_URL = "https://testnet.binance.vision/api/v3"
    
    # Default symbols when API fails
    DEFAULT_SYMBOLS = [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "SOLUSDT",
        "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "MATICUSDT",
        "LINKUSDT", "LTCUSDT", "UNIUSDT", "ATOMUSDT", "XLMUSDT"
    ]
    
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
        self._use_testnet = False
    
    async def connect(self, symbol: str = "btcusdt"):
        """Connect to Binance WebSocket streams."""
        self.symbol = symbol.lower()
        self._running = True
        
        while self._running:
            try:
                # Choose endpoint based on testnet flag
                base_url = self.TESTNET_WEBSOCKET_URL if self._use_testnet else self.WEBSOCKET_URL
                stream_url = f"{base_url}/{self.symbol}@aggTrade/{self.symbol}@depth20@100ms"
                
                logger.info(f"Connecting to Binance {'testnet' if self._use_testnet else 'mainnet'} for {self.symbol.upper()}")
                
                async with websockets.connect(stream_url, ping_interval=20, ping_timeout=10) as ws:
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
                        
            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"Binance connection closed: {e}")
            except Exception as e:
                error_str = str(e)
                logger.error(f"Binance connection error: {e}")
                
                # Check for geographic restriction (451 error)
                if "451" in error_str or "restricted" in error_str.lower():
                    if not self._use_testnet:
                        logger.info("Switching to Binance testnet due to geographic restriction")
                        self._use_testnet = True
                        continue
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
                    trade = Trade(
                        symbol=data['s'],
                        price=float(data['p']),
                        quantity=float(data['q']),
                        timestamp=datetime.fromtimestamp(data['T'] / 1000),
                        is_buyer_maker=data['m'],
                        trade_id=str(data['a'])
                    )
                    if self.on_trade:
                        await self.on_trade(trade)
                
                elif event_type == 'depthUpdate':
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
        # Try mainnet first, then testnet
        urls = [
            f"{BinanceFeed.REST_URL}/exchangeInfo",
            f"{BinanceFeed.TESTNET_REST_URL}/exchangeInfo"
        ]
        
        for url in urls:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(url)
                    
                    if response.status_code == 451:
                        logger.warning(f"Geographic restriction on {url}, trying next...")
                        continue
                    
                    if response.status_code == 200:
                        data = response.json()
                        symbols = [s['symbol'] for s in data['symbols'] 
                                  if s['status'] == 'TRADING' and s['quoteAsset'] == 'USDT']
                        return sorted(symbols)[:50]
                        
            except Exception as e:
                logger.error(f"Error fetching from {url}: {e}")
                continue
        
        # Return default symbols if all APIs fail
        logger.warning("Using default symbol list")
        return BinanceFeed.DEFAULT_SYMBOLS


class RithmicFeed:
    """Rithmic connection manager using async_rithmic library.
    
    Requires valid Rithmic credentials and conformance testing for production.
    """
    
    # Known Rithmic gateway URLs
    GATEWAYS = {
        "TEST": "rituz00100.rithmic.com:443",
        "PAPER": "rituz00100.rithmic.com:443",  # Paper trading (same as test for conformance)
        "CHICAGO": "rituz00100.rithmic.com:443",  # Production requires conformance
    }
    
    def __init__(self):
        self.is_connected = False
        self.username = ""
        self.password = ""
        self.server = "Rithmic Paper Trading"
        self.gateway = "TEST"
        self.gateway_url = ""
        self.on_trade: Optional[Callable] = None
        self.on_order_book: Optional[Callable] = None
        self.on_connection_change: Optional[Callable] = None
        self._running = False
        self._client = None
        self._symbol = "GC"  # Gold futures
        self._exchange = "COMEX"
    
    async def connect(
        self, 
        username: str, 
        password: str, 
        server: str = "Rithmic Paper Trading",
        gateway: str = "TEST",
        gateway_url: str = ""
    ):
        """Connect to Rithmic using async_rithmic library.
        
        Args:
            username: Rithmic username
            password: Rithmic password
            server: System name (e.g., "Rithmic Paper Trading", "Rithmic Test")
            gateway: Gateway name (TEST, PAPER, CHICAGO)
            gateway_url: Custom gateway URL (optional, uses GATEWAYS dict if not provided)
        """
        self.username = username
        self.password = password
        self.server = server
        self.gateway = gateway
        self.gateway_url = gateway_url or self.GATEWAYS.get(gateway.upper(), self.GATEWAYS["TEST"])
        
        if not username or not password:
            raise ValueError("Rithmic credentials required")
        
        self._running = True
        
        if not RITHMIC_AVAILABLE:
            logger.warning("async_rithmic not available, using simulation mode for XAUUSD")
            await self._simulate_xauusd_feed()
            return
        
        try:
            logger.info(f"Connecting to Rithmic: {self.server} via {self.gateway_url}")
            
            # Create Rithmic client
            self._client = RithmicClient(
                user=username,
                password=password,
                system_name=server,
                app_name="HFT_Signal_Generator",
                app_version="1.0",
                url=self.gateway_url
            )
            
            # Connect
            await self._client.connect()
            self.is_connected = True
            
            if self.on_connection_change:
                await self.on_connection_change(True, "XAUUSD")
            
            logger.info(f"Connected to Rithmic ({server})")
            
            # Get front month gold contract
            try:
                security_code = await self._client.get_front_month_contract(self._symbol, self._exchange)
                logger.info(f"Streaming data for {security_code}")
            except Exception as e:
                logger.warning(f"Could not get front month contract: {e}. Using GCZ5")
                security_code = "GCZ5"  # Fallback
            
            # Set up callbacks
            self._client.on_tick += self._on_tick_received
            self._client.on_order_book += self._on_order_book_received
            
            # Subscribe to market data
            data_type = DataType.LAST_TRADE | DataType.BBO
            await self._client.subscribe_to_market_data(security_code, self._exchange, data_type)
            
            # Also subscribe to order book if available
            try:
                await self._client.subscribe_to_market_data(security_code, self._exchange, DataType.ORDER_BOOK)
            except Exception as e:
                logger.warning(f"Order book subscription failed: {e}")
            
            # Keep connection alive
            while self._running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Rithmic connection error: {e}")
            logger.info("Falling back to simulation mode for XAUUSD")
            
            # Fall back to simulation
            if self.on_connection_change:
                await self.on_connection_change(True, "XAUUSD (Simulated)")
            await self._simulate_xauusd_feed()
    
    async def _on_tick_received(self, data: dict):
        """Handle incoming tick data from Rithmic."""
        try:
            if data.get("data_type") == DataType.LAST_TRADE:
                if data.get("presence_bits", 0) & LastTradePresenceBits.LAST_TRADE:
                    trade = Trade(
                        symbol="XAUUSD",
                        price=float(data.get("trade_price", 0)),
                        quantity=float(data.get("trade_size", 1)),
                        timestamp=datetime.utcnow(),
                        is_buyer_maker=data.get("aggressor_side", "") == "S",
                        trade_id=str(data.get("ssboe", ""))
                    )
                    if self.on_trade:
                        await self.on_trade(trade)
            
            elif data.get("data_type") == DataType.BBO:
                # Best bid/offer update - create order book with just top level
                presence = data.get("presence_bits", 0)
                
                if presence & (BestBidOfferPresenceBits.BID | BestBidOfferPresenceBits.ASK):
                    best_bid = float(data.get("bid_price", 0))
                    best_ask = float(data.get("ask_price", 0))
                    bid_size = float(data.get("bid_size", 0))
                    ask_size = float(data.get("ask_size", 0))
                    
                    if best_bid > 0 and best_ask > 0:
                        order_book = OrderBook(
                            symbol="XAUUSD",
                            timestamp=datetime.utcnow(),
                            bids=[OrderBookLevel(price=best_bid, quantity=bid_size)],
                            asks=[OrderBookLevel(price=best_ask, quantity=ask_size)],
                            best_bid=best_bid,
                            best_ask=best_ask,
                            spread=round(best_ask - best_bid, 2),
                            mid_price=round((best_bid + best_ask) / 2, 2)
                        )
                        if self.on_order_book:
                            await self.on_order_book(order_book)
                            
        except Exception as e:
            logger.error(f"Error handling Rithmic tick: {e}")
    
    async def _on_order_book_received(self, data: dict):
        """Handle order book updates from Rithmic."""
        try:
            # Parse order book data
            bids = []
            asks = []
            
            for level in data.get("levels", []):
                level_data = OrderBookLevel(
                    price=float(level.get("price", 0)),
                    quantity=float(level.get("size", 0))
                )
                if level.get("side") == "B":
                    bids.append(level_data)
                else:
                    asks.append(level_data)
            
            if bids or asks:
                bids = sorted(bids, key=lambda x: x.price, reverse=True)
                asks = sorted(asks, key=lambda x: x.price)
                
                best_bid = bids[0].price if bids else 0
                best_ask = asks[0].price if asks else 0
                
                order_book = OrderBook(
                    symbol="XAUUSD",
                    timestamp=datetime.utcnow(),
                    bids=bids,
                    asks=asks,
                    best_bid=best_bid,
                    best_ask=best_ask,
                    spread=round(best_ask - best_bid, 2) if best_bid and best_ask else 0,
                    mid_price=round((best_bid + best_ask) / 2, 2) if best_bid and best_ask else 0
                )
                if self.on_order_book:
                    await self.on_order_book(order_book)
                    
        except Exception as e:
            logger.error(f"Error handling Rithmic order book: {e}")
    
    async def _simulate_xauusd_feed(self):
        """Simulate XAUUSD tick data when Rithmic is unavailable."""
        base_price = 2350.0  # Base gold price
        volatility = 0.5
        
        self.is_connected = True
        
        while self._running:
            try:
                # Generate realistic price movement
                change = random.gauss(0, volatility)
                base_price += change
                base_price = max(base_price, 1800)  # Realistic gold floor
                base_price = min(base_price, 2800)  # Realistic gold ceiling
                
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
                
                await asyncio.sleep(random.uniform(0.05, 0.2))
                
            except Exception as e:
                logger.error(f"Error in XAUUSD simulation: {e}")
                await asyncio.sleep(1)
    
    async def disconnect(self):
        """Disconnect from Rithmic."""
        self._running = False
        
        if self._client and RITHMIC_AVAILABLE:
            try:
                await self._client.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting from Rithmic: {e}")
        
        self._client = None
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
                self._base_price = max(self._base_price, 1)
                
                # Generate trade
                volume = random.paretovariate(1.5)
                is_buyer = random.random() > 0.5 + (trend * 2)
                
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
