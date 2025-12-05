"""MongoDB Models for HFT Signal Generator"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


class DataSource(str, Enum):
    RITHMIC = "rithmic"
    BINANCE = "binance"
    SIMULATED = "simulated"


class SignalType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    NO_TRADE = "no_trade"


class MarketRegime(str, Enum):
    TREND = "trend"
    RANGE = "range"
    SPIKE = "spike"
    MEAN_REVERT = "mean_revert"


# Settings Models
class RithmicCredentials(BaseModel):
    username: str = ""
    password: str = ""
    server: str = "Rithmic Paper Trading"
    gateway: str = "Chicago"
    is_connected: bool = False


class BinanceSettings(BaseModel):
    enabled: bool = True
    selected_symbol: str = "BTCUSDT"
    available_symbols: List[str] = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "SOLUSDT", "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "MATICUSDT"]
    is_connected: bool = False


class OpenRouterSettings(BaseModel):
    api_key: str = ""
    selected_model: str = ""
    is_connected: bool = False


class SignalWeights(BaseModel):
    delta_weight: float = 0.25
    absorption_weight: float = 0.20
    iceberg_weight: float = 0.15
    ofmbi_weight: float = 0.20
    structure_weight: float = 0.10
    spread_penalty_weight: float = 0.10


class Settings(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    rithmic: RithmicCredentials = Field(default_factory=RithmicCredentials)
    binance: BinanceSettings = Field(default_factory=BinanceSettings)
    openrouter: OpenRouterSettings = Field(default_factory=OpenRouterSettings)
    signal_weights: SignalWeights = Field(default_factory=SignalWeights)
    active_data_source: DataSource = DataSource.BINANCE
    active_symbol: str = "BTCUSDT"
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# Market Data Models
class OrderBookLevel(BaseModel):
    price: float
    quantity: float
    orders_count: int = 1


class OrderBook(BaseModel):
    symbol: str
    timestamp: datetime
    bids: List[OrderBookLevel]  # Buy orders (descending by price)
    asks: List[OrderBookLevel]  # Sell orders (ascending by price)
    best_bid: float = 0.0
    best_ask: float = 0.0
    spread: float = 0.0
    mid_price: float = 0.0


class Trade(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str
    price: float
    quantity: float
    timestamp: datetime
    is_buyer_maker: bool  # True = sell aggressor, False = buy aggressor
    trade_id: str = ""


class Tick(BaseModel):
    symbol: str
    price: float
    quantity: float
    timestamp: datetime
    side: str  # "buy" or "sell"
    bid: float = 0.0
    ask: float = 0.0


# Analytics Models
class DeltaMetrics(BaseModel):
    raw_delta: float = 0.0  # V_buy - V_sell
    normalized_delta: float = 0.0  # (V_buy - V_sell) / (V_buy + V_sell + epsilon)
    depth_aware_delta: float = 0.0  # (V_buy - V_sell) / (D_bid + D_ask + epsilon)
    cumulative_delta: float = 0.0


class AbsorptionMetrics(BaseModel):
    score: float = 0.0  # V_hit / (V_hit + L_vis + epsilon)
    strength: float = 0.0  # (V_hit + L_res) / (V_hit + L_vis + L_res + epsilon)
    bid_absorption: float = 0.0
    ask_absorption: float = 0.0
    absorption_levels: List[Dict[str, float]] = []


class IcebergMetrics(BaseModel):
    probability: float = 0.0
    fill_to_display_ratio: float = 0.0
    refill_intensity: float = 0.0
    persistence_score: float = 0.0
    detected_levels: List[Dict[str, Any]] = []


class MomentumMetrics(BaseModel):
    ofmbi: float = 0.0  # Order Flow Momentum Burst Index
    ofmbi_vol_normalized: float = 0.0
    tape_speed: float = 0.0  # trades per second
    volume_velocity: float = 0.0


class StructureMetrics(BaseModel):
    regime: MarketRegime = MarketRegime.RANGE
    trend_direction: str = "neutral"  # "up", "down", "neutral"
    swing_highs: List[float] = []
    swing_lows: List[float] = []
    support_levels: List[float] = []
    resistance_levels: List[float] = []
    bos_detected: bool = False  # Break of Structure
    choch_detected: bool = False  # Change of Character
    trendline_rejection_probability: float = 0.0


class LiquidityMetrics(BaseModel):
    liquidity_zones: List[Dict[str, Any]] = []
    order_blocks: List[Dict[str, Any]] = []
    volume_profile: List[Dict[str, float]] = []
    vwap: float = 0.0
    premium_zone: bool = False
    discount_zone: bool = False


# Signal Models
class SignalBreakdown(BaseModel):
    delta_contribution: float = 0.0
    absorption_contribution: float = 0.0
    iceberg_contribution: float = 0.0
    momentum_contribution: float = 0.0
    structure_contribution: float = 0.0
    spread_penalty: float = 0.0


class TradingSignal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    signal_type: SignalType
    hfss_score: float = 0.0  # High Frequency Signal Score
    probability_buy: float = 0.0
    probability_sell: float = 0.0
    probability_no_trade: float = 0.0
    confidence: float = 0.0
    breakdown: SignalBreakdown = Field(default_factory=SignalBreakdown)
    reason: str = ""
    price_at_signal: float = 0.0
    ai_analysis: str = ""
    ai_validated: bool = False


# AI Models
class AIModel(BaseModel):
    id: str
    name: str
    context_length: int = 0
    pricing_prompt: float = 0.0
    pricing_completion: float = 0.0
    description: str = ""


class AIAnalysisRequest(BaseModel):
    context: str
    metrics: Dict[str, Any]
    signal: Optional[TradingSignal] = None


class AIAnalysisResponse(BaseModel):
    analysis: str
    anomalies_detected: List[str] = []
    trading_insight: str = ""
    confidence_adjustment: float = 0.0
    validated: bool = True
