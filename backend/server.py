"""HFT Signal Generator - Main Server

Full-featured backend for high-frequency trading signal generation.
Supports Rithmic (XAUUSD), Binance (Crypto), and OpenRouter AI integration.
"""
from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

# Load environment
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Import local modules
from models import (
    Settings, RithmicCredentials, BinanceSettings, OpenRouterSettings,
    SignalWeights, DataSource, Trade, OrderBook, TradingSignal, SignalType
)
from analytics_engine import AnalyticsEngine
from data_feeds import BinanceFeed, RithmicFeed, SimulatedFeed
from openrouter_client import OpenRouterClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'hft_signals')]

# Create FastAPI app
app = FastAPI(title="HFT Signal Generator API", version="1.0.0")

# Create router with /api prefix
api_router = APIRouter(prefix="/api")

# Global instances
analytics_engine = AnalyticsEngine()
binance_feed = BinanceFeed()
rithmic_feed = RithmicFeed()
simulated_feed = SimulatedFeed()
openrouter_client = OpenRouterClient()

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections[:]:
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

# Current state
current_settings: Optional[Settings] = None
current_signal: Optional[TradingSignal] = None
is_streaming = False
stream_task: Optional[asyncio.Task] = None

# ==================== SETTINGS ENDPOINTS ====================

@api_router.get("/settings")
async def get_settings():
    """Get current settings."""
    global current_settings
    
    settings_doc = await db.settings.find_one({"_id": "main"})
    
    if settings_doc:
        settings_doc.pop('_id', None)
        current_settings = Settings(**settings_doc)
    else:
        current_settings = Settings()
    
    return current_settings.dict()

@api_router.post("/settings")
async def save_settings(settings: Settings):
    """Save settings to database."""
    global current_settings
    
    settings.updated_at = datetime.utcnow()
    current_settings = settings
    
    await db.settings.update_one(
        {"_id": "main"},
        {"$set": settings.dict()},
        upsert=True
    )
    
    analytics_engine.update_weights(settings.signal_weights)
    
    return {"status": "success", "message": "Settings saved"}

@api_router.post("/settings/rithmic")
async def update_rithmic_settings(credentials: RithmicCredentials):
    """Update Rithmic credentials."""
    global current_settings
    
    if not current_settings:
        current_settings = Settings()
    
    current_settings.rithmic = credentials
    current_settings.updated_at = datetime.utcnow()
    
    await db.settings.update_one(
        {"_id": "main"},
        {"$set": {"rithmic": credentials.dict(), "updated_at": current_settings.updated_at}},
        upsert=True
    )
    
    return {"status": "success", "message": "Rithmic credentials updated"}

@api_router.post("/settings/binance")
async def update_binance_settings(settings: BinanceSettings):
    """Update Binance settings."""
    global current_settings
    
    if not current_settings:
        current_settings = Settings()
    
    current_settings.binance = settings
    current_settings.updated_at = datetime.utcnow()
    
    await db.settings.update_one(
        {"_id": "main"},
        {"$set": {"binance": settings.dict(), "updated_at": current_settings.updated_at}},
        upsert=True
    )
    
    return {"status": "success", "message": "Binance settings updated"}

@api_router.post("/settings/openrouter")
async def update_openrouter_settings(settings: OpenRouterSettings):
    """Update OpenRouter API settings."""
    global current_settings
    
    if not current_settings:
        current_settings = Settings()
    
    current_settings.openrouter = settings
    current_settings.updated_at = datetime.utcnow()
    
    openrouter_client.set_api_key(settings.api_key)
    openrouter_client.set_model(settings.selected_model)
    
    await db.settings.update_one(
        {"_id": "main"},
        {"$set": {"openrouter": settings.dict(), "updated_at": current_settings.updated_at}},
        upsert=True
    )
    
    return {"status": "success", "message": "OpenRouter settings updated"}

@api_router.post("/settings/weights")
async def update_signal_weights(weights: SignalWeights):
    """Update signal generation weights."""
    global current_settings
    
    if not current_settings:
        current_settings = Settings()
    
    current_settings.signal_weights = weights
    analytics_engine.update_weights(weights)
    
    await db.settings.update_one(
        {"_id": "main"},
        {"$set": {"signal_weights": weights.dict()}},
        upsert=True
    )
    
    return {"status": "success", "message": "Signal weights updated"}

# ==================== DATA SOURCE ENDPOINTS ====================

@api_router.get("/binance/symbols")
async def get_binance_symbols():
    """Get available Binance trading pairs."""
    symbols = await BinanceFeed.get_exchange_info()
    return {"symbols": symbols}

@api_router.post("/data-source/connect")
async def connect_data_source(source: str, symbol: str = "BTCUSDT"):
    """Connect to a data source."""
    global is_streaming, stream_task, current_settings
    
    await stop_streaming()
    
    if source == "binance":
        binance_feed.on_trade = on_trade_received
        binance_feed.on_order_book = on_order_book_received
        binance_feed.on_connection_change = on_connection_change
        stream_task = asyncio.create_task(binance_feed.connect(symbol.lower()))
        is_streaming = True
        
    elif source == "rithmic":
        if not current_settings or not current_settings.rithmic.username:
            raise HTTPException(status_code=400, detail="Rithmic credentials not configured")
        
        rithmic_feed.on_trade = on_trade_received
        rithmic_feed.on_order_book = on_order_book_received
        rithmic_feed.on_connection_change = on_connection_change
        stream_task = asyncio.create_task(
            rithmic_feed.connect(
                current_settings.rithmic.username,
                current_settings.rithmic.password,
                current_settings.rithmic.server,
                current_settings.rithmic.gateway
            )
        )
        is_streaming = True
        
    elif source == "simulated":
        simulated_feed.on_trade = on_trade_received
        simulated_feed.on_order_book = on_order_book_received
        simulated_feed.on_connection_change = on_connection_change
        stream_task = asyncio.create_task(simulated_feed.connect(symbol, 100.0))
        is_streaming = True
    
    else:
        raise HTTPException(status_code=400, detail=f"Unknown data source: {source}")
    
    if current_settings:
        current_settings.active_data_source = DataSource(source)
        current_settings.active_symbol = symbol
        await db.settings.update_one(
            {"_id": "main"},
            {"$set": {"active_data_source": source, "active_symbol": symbol}},
            upsert=True
        )
    
    return {"status": "success", "message": f"Connecting to {source} for {symbol}"}

@api_router.post("/data-source/disconnect")
async def disconnect_data_source():
    """Disconnect from current data source."""
    await stop_streaming()
    return {"status": "success", "message": "Disconnected"}

@api_router.get("/data-source/status")
async def get_data_source_status():
    """Get current data source connection status."""
    return {
        "is_streaming": is_streaming,
        "binance_connected": binance_feed.is_connected,
        "rithmic_connected": rithmic_feed.is_connected,
        "simulated_connected": simulated_feed.is_connected,
        "active_symbol": current_settings.active_symbol if current_settings else None,
        "active_source": current_settings.active_data_source.value if current_settings else None
    }

async def stop_streaming():
    """Stop all data streams."""
    global is_streaming, stream_task
    
    is_streaming = False
    
    if binance_feed.is_connected:
        await binance_feed.disconnect()
    if rithmic_feed.is_connected:
        await rithmic_feed.disconnect()
    if simulated_feed.is_connected:
        await simulated_feed.disconnect()
    
    if stream_task:
        stream_task.cancel()
        try:
            await stream_task
        except asyncio.CancelledError:
            pass
        stream_task = None

# ==================== DATA CALLBACKS ====================

async def on_trade_received(trade: Trade):
    """Handle incoming trade data."""
    global current_signal
    
    analytics_engine.add_trade(trade)
    
    if len(analytics_engine.trades) % 10 == 0:
        symbol = current_settings.active_symbol if current_settings else trade.symbol
        current_signal = analytics_engine.generate_signal(symbol)
        
        await db.signals.insert_one(current_signal.dict())
    
    await manager.broadcast({
        "type": "trade",
        "data": {
            "symbol": trade.symbol,
            "price": trade.price,
            "quantity": trade.quantity,
            "timestamp": trade.timestamp.isoformat(),
            "side": "sell" if trade.is_buyer_maker else "buy"
        }
    })

async def on_order_book_received(order_book: OrderBook):
    """Handle incoming order book update."""
    analytics_engine.add_order_book(order_book)
    
    await manager.broadcast({
        "type": "orderbook",
        "data": {
            "symbol": order_book.symbol,
            "best_bid": order_book.best_bid,
            "best_ask": order_book.best_ask,
            "spread": order_book.spread,
            "mid_price": order_book.mid_price,
            "bids": [{"price": b.price, "quantity": b.quantity} for b in order_book.bids[:10]],
            "asks": [{"price": a.price, "quantity": a.quantity} for a in order_book.asks[:10]],
            "timestamp": order_book.timestamp.isoformat()
        }
    })

async def on_connection_change(connected: bool, symbol: str):
    """Handle connection status changes."""
    await manager.broadcast({
        "type": "connection",
        "data": {
            "connected": connected,
            "symbol": symbol,
            "timestamp": datetime.utcnow().isoformat()
        }
    })

# ==================== OPENROUTER ENDPOINTS ====================

@api_router.get("/openrouter/models")
async def get_openrouter_models(refresh: bool = False):
    """Get available OpenRouter models."""
    if not openrouter_client.api_key and current_settings:
        openrouter_client.set_api_key(current_settings.openrouter.api_key)
    
    models = await openrouter_client.fetch_models(force_refresh=refresh)
    return {
        "models": [m.dict() for m in models],
        "is_connected": openrouter_client.is_connected,
        "selected_model": openrouter_client.selected_model
    }

@api_router.post("/openrouter/set-model")
async def set_openrouter_model(model_id: str):
    """Set the active OpenRouter model."""
    openrouter_client.set_model(model_id)
    
    if current_settings:
        current_settings.openrouter.selected_model = model_id
        await db.settings.update_one(
            {"_id": "main"},
            {"$set": {"openrouter.selected_model": model_id}},
            upsert=True
        )
    
    return {"status": "success", "model": model_id}

@api_router.post("/ai/analyze")
async def ai_analyze_market():
    """Get AI analysis of current market conditions."""
    if not openrouter_client.api_key:
        raise HTTPException(status_code=400, detail="OpenRouter API key not configured")
    
    metrics = analytics_engine.get_all_metrics()
    symbol = current_settings.active_symbol if current_settings else "UNKNOWN"
    
    context = f"Analyzing {symbol} order flow at {datetime.utcnow().isoformat()}"
    
    response = await openrouter_client.analyze_order_flow(
        context=context,
        metrics=metrics,
        signal=current_signal
    )
    
    return response.dict()

@api_router.get("/ai/summary")
async def ai_quick_summary():
    """Get quick AI summary of market state."""
    metrics = analytics_engine.get_all_metrics()
    summary = await openrouter_client.get_quick_summary(metrics)
    return {"summary": summary}

# ==================== SIGNAL ENDPOINTS ====================

@api_router.get("/signals/current")
async def get_current_signal():
    """Get the current trading signal."""
    if current_signal:
        return current_signal.dict()
    return {"signal_type": "no_trade", "message": "No signal generated yet"}

@api_router.get("/signals/history")
async def get_signal_history(
    limit: int = Query(100, ge=1, le=1000),
    signal_type: Optional[str] = None
):
    """Get historical signals."""
    query = {}
    if signal_type:
        query["signal_type"] = signal_type
    
    signals = await db.signals.find(query).sort("timestamp", -1).limit(limit).to_list(limit)
    
    for s in signals:
        s['_id'] = str(s['_id'])
    
    return {"signals": signals}

@api_router.get("/metrics")
async def get_current_metrics():
    """Get current analytics metrics."""
    return analytics_engine.get_all_metrics()

# ==================== WEBSOCKET ENDPOINT ====================

@api_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time data streaming."""
    await manager.connect(websocket)
    
    try:
        await websocket.send_json({
            "type": "init",
            "data": {
                "is_streaming": is_streaming,
                "active_symbol": current_settings.active_symbol if current_settings else None,
                "metrics": analytics_engine.get_all_metrics()
            }
        })
        
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                message = json.loads(data)
                
                if message.get("type") == "get_signal":
                    if current_signal:
                        await websocket.send_json({
                            "type": "signal",
                            "data": current_signal.dict()
                        })
                
                elif message.get("type") == "get_metrics":
                    await websocket.send_json({
                        "type": "metrics",
                        "data": analytics_engine.get_all_metrics()
                    })
                    
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "heartbeat"})
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# ==================== HEALTH ENDPOINTS ====================

@api_router.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "HFT Signal Generator API",
        "version": "1.0.0",
        "status": "running"
    }

@api_router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "connections": {
            "mongodb": "connected",
            "binance": binance_feed.is_connected,
            "rithmic": rithmic_feed.is_connected,
            "openrouter": openrouter_client.is_connected
        }
    }

# Include router
app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    global current_settings
    
    settings_doc = await db.settings.find_one({"_id": "main"})
    if settings_doc:
        settings_doc.pop('_id', None)
        current_settings = Settings(**settings_doc)
        
        if current_settings.openrouter.api_key:
            openrouter_client.set_api_key(current_settings.openrouter.api_key)
            openrouter_client.set_model(current_settings.openrouter.selected_model)
        
        analytics_engine.update_weights(current_settings.signal_weights)
    
    logger.info("HFT Signal Generator started")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    await stop_streaming()
    client.close()
    logger.info("HFT Signal Generator stopped")
