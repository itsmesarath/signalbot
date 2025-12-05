"""Advanced Order-Flow Analytics Engine

Implements all the quantitative formulas for HFT signal generation:
- Delta & Imbalance Model
- Absorption Strength
- Iceberg Probability
- Order-Flow Momentum Burst Index
- Trendline Rejection Probability
- Composite High-Frequency Signal Score
"""
import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import deque
from datetime import datetime, timedelta
import math
from models import (
    Trade, OrderBook, Tick, DeltaMetrics, AbsorptionMetrics,
    IcebergMetrics, MomentumMetrics, StructureMetrics, LiquidityMetrics,
    TradingSignal, SignalType, SignalBreakdown, MarketRegime, SignalWeights
)


class AnalyticsEngine:
    """Core analytics engine for order flow analysis and signal generation."""
    
    EPSILON = 1e-10  # Small constant to avoid division by zero
    
    def __init__(self, window_size: int = 100, micro_bar_ms: int = 500):
        self.window_size = window_size
        self.micro_bar_ms = micro_bar_ms
        
        # Rolling data structures
        self.trades: deque = deque(maxlen=10000)
        self.ticks: deque = deque(maxlen=10000)
        self.order_books: deque = deque(maxlen=1000)
        self.prices: deque = deque(maxlen=5000)
        self.volumes: deque = deque(maxlen=5000)
        
        # Cumulative metrics
        self.cumulative_delta = 0.0
        self.total_buy_volume = 0.0
        self.total_sell_volume = 0.0
        
        # Level tracking for absorption/iceberg detection
        self.level_hits: Dict[float, Dict] = {}  # price -> {hits, volume, timestamps}
        self.level_depth_history: Dict[float, List[float]] = {}  # price -> [depth snapshots]
        
        # ATR calculation
        self.atr_period = 14
        self.atr_values: deque = deque(maxlen=100)
        self.high_prices: deque = deque(maxlen=100)
        self.low_prices: deque = deque(maxlen=100)
        self.close_prices: deque = deque(maxlen=100)
        
        # Median values for normalization
        self.median_spread = 0.0
        self.median_atr = 0.0
        self.spreads: deque = deque(maxlen=1000)
        
        # Structure detection
        self.swing_highs: List[Tuple[datetime, float]] = []
        self.swing_lows: List[Tuple[datetime, float]] = []
        
        # Signal weights (configurable)
        self.weights = SignalWeights()
        
        # Iceberg model coefficients
        self.iceberg_coeffs = {
            'a0': -2.0,  # bias
            'a1': 1.5,   # FDR weight
            'a2': 1.0,   # refill weight  
            'a3': 0.5    # persistence weight
        }
        
        # TRP coefficients
        self.trp_coeffs = {
            'b0': 0.0,
            'b1': 2.0,
            'lambda': 2.0  # distance sensitivity
        }
    
    def update_weights(self, weights: SignalWeights):
        """Update signal weights."""
        self.weights = weights
    
    def add_trade(self, trade: Trade):
        """Process a new trade."""
        self.trades.append(trade)
        self.prices.append(trade.price)
        self.volumes.append(trade.quantity)
        
        # Update cumulative delta
        if not trade.is_buyer_maker:  # Buy aggressor
            self.cumulative_delta += trade.quantity
            self.total_buy_volume += trade.quantity
        else:  # Sell aggressor
            self.cumulative_delta -= trade.quantity
            self.total_sell_volume += trade.quantity
        
        # Track level hits for absorption detection
        price_level = round(trade.price, 2)
        if price_level not in self.level_hits:
            self.level_hits[price_level] = {'hits': 0, 'volume': 0.0, 'timestamps': []}
        self.level_hits[price_level]['hits'] += 1
        self.level_hits[price_level]['volume'] += trade.quantity
        self.level_hits[price_level]['timestamps'].append(trade.timestamp)
        
        # Clean old level data
        self._clean_old_level_data()
    
    def add_order_book(self, order_book: OrderBook):
        """Process order book update."""
        self.order_books.append(order_book)
        self.spreads.append(order_book.spread)
        
        # Update median spread
        if len(self.spreads) > 10:
            self.median_spread = np.median(list(self.spreads))
        
        # Track depth at each level for iceberg detection
        for level in order_book.bids + order_book.asks:
            price = round(level.price, 2)
            if price not in self.level_depth_history:
                self.level_depth_history[price] = []
            self.level_depth_history[price].append(level.quantity)
            # Keep only recent depth history
            if len(self.level_depth_history[price]) > 100:
                self.level_depth_history[price] = self.level_depth_history[price][-100:]
    
    def add_candle(self, high: float, low: float, close: float):
        """Add candle data for ATR calculation."""
        self.high_prices.append(high)
        self.low_prices.append(low)
        self.close_prices.append(close)
        self._calculate_atr()
    
    def _clean_old_level_data(self, max_age_seconds: int = 60):
        """Clean old level tracking data."""
        cutoff = datetime.utcnow() - timedelta(seconds=max_age_seconds)
        levels_to_remove = []
        for price, data in self.level_hits.items():
            data['timestamps'] = [t for t in data['timestamps'] if t > cutoff]
            if not data['timestamps']:
                levels_to_remove.append(price)
        for price in levels_to_remove:
            del self.level_hits[price]
    
    def _calculate_atr(self):
        """Calculate Average True Range."""
        if len(self.high_prices) < 2:
            return
        
        high = list(self.high_prices)
        low = list(self.low_prices)
        close = list(self.close_prices)
        
        tr_values = []
        for i in range(1, len(high)):
            tr = max(
                high[i] - low[i],
                abs(high[i] - close[i-1]),
                abs(low[i] - close[i-1])
            )
            tr_values.append(tr)
        
        if tr_values:
            atr = np.mean(tr_values[-self.atr_period:])
            self.atr_values.append(atr)
            if len(self.atr_values) > 10:
                self.median_atr = np.median(list(self.atr_values))
    
    def get_current_atr(self) -> float:
        """Get current ATR value."""
        if self.atr_values:
            return self.atr_values[-1]
        return 0.01  # Default small value
    
    # ==================== DELTA & IMBALANCE MODEL ====================
    
    def calculate_delta_metrics(self, window_ms: int = 1000) -> DeltaMetrics:
        """Calculate delta and imbalance metrics.
        
        Formulas:
        - Raw Delta: Δ_raw(t) = V_buy(t) - V_sell(t)
        - Normalized: Δ_norm(t) = (V_buy - V_sell) / (V_buy + V_sell + ε)
        - Depth-aware: Δ_depth(t) = (V_buy - V_sell) / (D_bid + D_ask + ε)
        """
        cutoff = datetime.utcnow() - timedelta(milliseconds=window_ms)
        recent_trades = [t for t in self.trades if t.timestamp > cutoff]
        
        v_buy = sum(t.quantity for t in recent_trades if not t.is_buyer_maker)
        v_sell = sum(t.quantity for t in recent_trades if t.is_buyer_maker)
        
        # Get current depth
        d_bid, d_ask = 0.0, 0.0
        if self.order_books:
            ob = self.order_books[-1]
            d_bid = sum(l.quantity for l in ob.bids[:5])  # Top 5 levels
            d_ask = sum(l.quantity for l in ob.asks[:5])
        
        raw_delta = v_buy - v_sell
        normalized_delta = raw_delta / (v_buy + v_sell + self.EPSILON)
        depth_aware_delta = raw_delta / (d_bid + d_ask + self.EPSILON)
        
        return DeltaMetrics(
            raw_delta=raw_delta,
            normalized_delta=normalized_delta,
            depth_aware_delta=depth_aware_delta,
            cumulative_delta=self.cumulative_delta
        )
    
    # ==================== ABSORPTION DETECTION ====================
    
    def calculate_absorption_metrics(self, window_ms: int = 5000) -> AbsorptionMetrics:
        """Calculate absorption strength at key levels.
        
        Formulas:
        - AbsorptionScore(p,t) = V_hit(p,t) / (V_hit(p,t) + L_vis(p,t) + ε)
        - AbsorptionStrength(p,t) = (V_hit + L_res) / (V_hit + L_vis + L_res + ε)
        """
        if not self.order_books:
            return AbsorptionMetrics()
        
        ob = self.order_books[-1]
        absorption_levels = []
        max_bid_absorption = 0.0
        max_ask_absorption = 0.0
        
        # Check bid levels (support)
        for level in ob.bids[:10]:
            price = round(level.price, 2)
            if price in self.level_hits:
                v_hit = self.level_hits[price]['volume']
                l_vis = level.quantity
                l_res = self._estimate_hidden_liquidity(price)
                
                score = v_hit / (v_hit + l_vis + self.EPSILON)
                strength = (v_hit + l_res) / (v_hit + l_vis + l_res + self.EPSILON)
                
                if score > 0.3:  # Threshold for significant absorption
                    absorption_levels.append({
                        'price': price,
                        'side': 'bid',
                        'score': score,
                        'strength': strength,
                        'volume_hit': v_hit
                    })
                    max_bid_absorption = max(max_bid_absorption, strength)
        
        # Check ask levels (resistance)
        for level in ob.asks[:10]:
            price = round(level.price, 2)
            if price in self.level_hits:
                v_hit = self.level_hits[price]['volume']
                l_vis = level.quantity
                l_res = self._estimate_hidden_liquidity(price)
                
                score = v_hit / (v_hit + l_vis + self.EPSILON)
                strength = (v_hit + l_res) / (v_hit + l_vis + l_res + self.EPSILON)
                
                if score > 0.3:
                    absorption_levels.append({
                        'price': price,
                        'side': 'ask',
                        'score': score,
                        'strength': strength,
                        'volume_hit': v_hit
                    })
                    max_ask_absorption = max(max_ask_absorption, strength)
        
        # Overall absorption score
        overall_score = 0.0
        overall_strength = 0.0
        if absorption_levels:
            overall_score = np.mean([l['score'] for l in absorption_levels])
            overall_strength = np.mean([l['strength'] for l in absorption_levels])
        
        return AbsorptionMetrics(
            score=overall_score,
            strength=overall_strength,
            bid_absorption=max_bid_absorption,
            ask_absorption=max_ask_absorption,
            absorption_levels=absorption_levels
        )
    
    def _estimate_hidden_liquidity(self, price: float) -> float:
        """Estimate hidden/iceberg liquidity at a price level."""
        if price not in self.level_depth_history:
            return 0.0
        
        depths = self.level_depth_history[price]
        if len(depths) < 3:
            return 0.0
        
        # Look for refill patterns (depth decreases then increases)
        refills = 0
        for i in range(2, len(depths)):
            if depths[i-1] < depths[i-2] and depths[i] > depths[i-1]:
                refills += 1
        
        # Estimate hidden liquidity based on refill frequency
        if price in self.level_hits:
            v_hit = self.level_hits[price]['volume']
            return v_hit * (refills / max(len(depths) - 2, 1))
        return 0.0
    
    # ==================== ICEBERG DETECTION ====================
    
    def calculate_iceberg_metrics(self) -> IcebergMetrics:
        """Calculate iceberg probability using refined model.
        
        Formula:
        IP(p,t) = σ(a0 + a1*FDR(p,t) + a2*R_refill(p,t) + a3*T_persist(p,t))
        where σ is logistic function
        """
        if not self.order_books:
            return IcebergMetrics()
        
        ob = self.order_books[-1]
        detected_icebergs = []
        max_probability = 0.0
        
        all_levels = [(l, 'bid') for l in ob.bids[:10]] + [(l, 'ask') for l in ob.asks[:10]]
        
        for level, side in all_levels:
            price = round(level.price, 2)
            
            # Calculate FDR (Fill-to-Display Ratio)
            v_exec = self.level_hits.get(price, {}).get('volume', 0)
            l_disp = level.quantity
            fdr = v_exec / (l_disp + self.EPSILON)
            
            # Calculate refill intensity
            r_refill = self._calculate_refill_intensity(price)
            
            # Calculate persistence
            t_persist = self._calculate_persistence(price)
            
            # Logistic model for iceberg probability
            z = (self.iceberg_coeffs['a0'] + 
                 self.iceberg_coeffs['a1'] * fdr +
                 self.iceberg_coeffs['a2'] * r_refill +
                 self.iceberg_coeffs['a3'] * t_persist)
            
            probability = 1 / (1 + math.exp(-z))  # Sigmoid
            
            if probability > 0.5:  # Threshold for iceberg detection
                detected_icebergs.append({
                    'price': price,
                    'side': side,
                    'probability': probability,
                    'fdr': fdr,
                    'estimated_hidden': v_exec - l_disp if v_exec > l_disp else 0
                })
                max_probability = max(max_probability, probability)
        
        # Simple IP calculation
        v_exec_total = sum(self.level_hits.get(round(l.price, 2), {}).get('volume', 0) 
                          for l in ob.bids[:5] + ob.asks[:5])
        v_visible_total = sum(l.quantity for l in ob.bids[:5] + ob.asks[:5])
        ip_simple = (v_exec_total - v_visible_total) / (v_exec_total + self.EPSILON) if v_exec_total > v_visible_total else 0
        
        return IcebergMetrics(
            probability=max_probability,
            fill_to_display_ratio=fdr if detected_icebergs else 0,
            refill_intensity=np.mean([self._calculate_refill_intensity(round(l.price, 2)) for l in ob.bids[:5] + ob.asks[:5]]),
            persistence_score=np.mean([self._calculate_persistence(round(l.price, 2)) for l in ob.bids[:5] + ob.asks[:5]]),
            detected_levels=detected_icebergs
        )
    
    def _calculate_refill_intensity(self, price: float) -> float:
        """Calculate normalized refill intensity at a price level."""
        if price not in self.level_depth_history:
            return 0.0
        
        depths = self.level_depth_history[price]
        if len(depths) < 3:
            return 0.0
        
        refill_magnitude = 0.0
        consume_magnitude = 0.0
        
        for i in range(1, len(depths)):
            diff = depths[i] - depths[i-1]
            if diff > 0:
                refill_magnitude += diff
            else:
                consume_magnitude += abs(diff)
        
        return refill_magnitude / (consume_magnitude + self.EPSILON)
    
    def _calculate_persistence(self, price: float) -> float:
        """Calculate how long a price level persists while being hit."""
        if price not in self.level_hits:
            return 0.0
        
        timestamps = self.level_hits[price]['timestamps']
        if len(timestamps) < 2:
            return 0.0
        
        # Duration the level has been present while being traded
        duration = (timestamps[-1] - timestamps[0]).total_seconds()
        hits = len(timestamps)
        
        # Normalize: high persistence = long duration with many hits
        return min(1.0, (duration * hits) / 60.0)  # Normalize to 60 seconds
    
    # ==================== MOMENTUM BURST INDEX ====================
    
    def calculate_momentum_metrics(self, window_ms: int = 1000) -> MomentumMetrics:
        """Calculate Order-Flow Momentum Burst Index.
        
        Formula:
        OFMBI(t) = Δ_norm(t) * TS(t) / (S(t) + ε)
        OFMBI_vol(t) = Δ_norm(t) * TS(t) / (S(t) * ATR_k(t) + ε)
        """
        delta_metrics = self.calculate_delta_metrics(window_ms)
        
        # Calculate tape speed (trades per second)
        cutoff = datetime.utcnow() - timedelta(milliseconds=window_ms)
        recent_trades = [t for t in self.trades if t.timestamp > cutoff]
        tape_speed = len(recent_trades) / (window_ms / 1000.0) if window_ms > 0 else 0
        
        # Volume velocity
        volume_velocity = sum(t.quantity for t in recent_trades) / (window_ms / 1000.0) if recent_trades else 0
        
        # Get current spread
        spread = self.median_spread if self.median_spread > 0 else 0.01
        if self.order_books:
            spread = self.order_books[-1].spread
        
        # Calculate OFMBI
        ofmbi = (delta_metrics.normalized_delta * tape_speed) / (spread + self.EPSILON)
        
        # Volatility-normalized OFMBI
        atr = self.get_current_atr()
        ofmbi_vol = (delta_metrics.normalized_delta * tape_speed) / (spread * atr + self.EPSILON)
        
        return MomentumMetrics(
            ofmbi=ofmbi,
            ofmbi_vol_normalized=ofmbi_vol,
            tape_speed=tape_speed,
            volume_velocity=volume_velocity
        )
    
    # ==================== STRUCTURE & REGIME DETECTION ====================
    
    def calculate_structure_metrics(self) -> StructureMetrics:
        """Detect market structure, regime, and trendline rejection."""
        if len(self.prices) < 20:
            return StructureMetrics()
        
        prices = list(self.prices)
        
        # Detect swing points
        swing_highs = self._detect_swing_highs(prices)
        swing_lows = self._detect_swing_lows(prices)
        
        # Determine trend direction
        trend = self._determine_trend(swing_highs, swing_lows)
        
        # Detect regime
        regime = self._detect_regime(prices)
        
        # Detect BOS/CHOCH
        bos, choch = self._detect_structure_breaks(swing_highs, swing_lows, trend)
        
        # Calculate TRP
        trp = self._calculate_trendline_rejection(prices, swing_highs, swing_lows)
        
        return StructureMetrics(
            regime=regime,
            trend_direction=trend,
            swing_highs=swing_highs[-5:] if swing_highs else [],
            swing_lows=swing_lows[-5:] if swing_lows else [],
            support_levels=swing_lows[-3:] if swing_lows else [],
            resistance_levels=swing_highs[-3:] if swing_highs else [],
            bos_detected=bos,
            choch_detected=choch,
            trendline_rejection_probability=trp
        )
    
    def _detect_swing_highs(self, prices: List[float], lookback: int = 5) -> List[float]:
        """Detect swing high points."""
        swing_highs = []
        for i in range(lookback, len(prices) - lookback):
            if prices[i] == max(prices[i-lookback:i+lookback+1]):
                swing_highs.append(prices[i])
        return swing_highs
    
    def _detect_swing_lows(self, prices: List[float], lookback: int = 5) -> List[float]:
        """Detect swing low points."""
        swing_lows = []
        for i in range(lookback, len(prices) - lookback):
            if prices[i] == min(prices[i-lookback:i+lookback+1]):
                swing_lows.append(prices[i])
        return swing_lows
    
    def _determine_trend(self, highs: List[float], lows: List[float]) -> str:
        """Determine trend based on higher highs/lows vs lower highs/lows."""
        if len(highs) < 2 or len(lows) < 2:
            return "neutral"
        
        # Check for higher highs and higher lows (uptrend)
        hh = highs[-1] > highs[-2] if len(highs) >= 2 else False
        hl = lows[-1] > lows[-2] if len(lows) >= 2 else False
        
        # Check for lower highs and lower lows (downtrend)
        lh = highs[-1] < highs[-2] if len(highs) >= 2 else False
        ll = lows[-1] < lows[-2] if len(lows) >= 2 else False
        
        if hh and hl:
            return "up"
        elif lh and ll:
            return "down"
        return "neutral"
    
    def _detect_regime(self, prices: List[float]) -> MarketRegime:
        """Detect market regime using volatility and directional persistence."""
        if len(prices) < 20:
            return MarketRegime.RANGE
        
        returns = np.diff(prices) / np.array(prices[:-1])
        volatility = np.std(returns)
        
        # Directional persistence (autocorrelation of returns)
        if len(returns) > 1:
            persistence = np.corrcoef(returns[:-1], returns[1:])[0, 1]
        else:
            persistence = 0
        
        # High volatility spike
        if volatility > np.mean(np.abs(returns)) * 3:
            return MarketRegime.SPIKE
        
        # Trending (high persistence)
        if abs(persistence) > 0.3:
            return MarketRegime.TREND
        
        # Mean reverting (negative persistence)
        if persistence < -0.2:
            return MarketRegime.MEAN_REVERT
        
        return MarketRegime.RANGE
    
    def _detect_structure_breaks(self, highs: List[float], lows: List[float], trend: str) -> Tuple[bool, bool]:
        """Detect Break of Structure (BOS) and Change of Character (CHOCH)."""
        bos = False
        choch = False
        
        if len(self.prices) < 3:
            return bos, choch
        
        current_price = self.prices[-1]
        
        # BOS: Price breaks recent structure in trend direction
        if trend == "up" and highs:
            if current_price > max(highs[-3:]) if len(highs) >= 3 else highs[-1]:
                bos = True
        elif trend == "down" and lows:
            if current_price < min(lows[-3:]) if len(lows) >= 3 else lows[-1]:
                bos = True
        
        # CHOCH: Price breaks structure against trend
        if trend == "up" and lows:
            if current_price < min(lows[-2:]) if len(lows) >= 2 else lows[-1]:
                choch = True
        elif trend == "down" and highs:
            if current_price > max(highs[-2:]) if len(highs) >= 2 else highs[-1]:
                choch = True
        
        return bos, choch
    
    def _calculate_trendline_rejection(self, prices: List[float], highs: List[float], lows: List[float]) -> float:
        """Calculate Trendline Rejection Probability.
        
        Formula:
        TRP_dist(t) = 1 - min(1, |Price(t) - T(t)| / (λ * ATR_k(t) + ε))
        TRP(t) = TRP_dist(t) * σ(b0 + b1 * RejFlow(t))
        """
        if not prices:
            return 0.0
        
        current_price = prices[-1]
        atr = self.get_current_atr()
        lambda_param = self.trp_coeffs['lambda']
        
        # Find nearest trendline level
        trendline_level = None
        min_distance = float('inf')
        
        for level in highs[-3:] + lows[-3:]:
            distance = abs(current_price - level)
            if distance < min_distance:
                min_distance = distance
                trendline_level = level
        
        if trendline_level is None:
            return 0.0
        
        # Calculate TRP_dist
        distance_normalized = min_distance / (lambda_param * atr + self.EPSILON)
        trp_dist = 1 - min(1, distance_normalized)
        
        # Get rejection flow (delta against breakout direction)
        delta = self.calculate_delta_metrics().normalized_delta
        rej_flow = -delta if current_price > trendline_level else delta
        
        # Apply logistic transform
        z = self.trp_coeffs['b0'] + self.trp_coeffs['b1'] * rej_flow
        rej_factor = 1 / (1 + math.exp(-z))
        
        return trp_dist * rej_factor
    
    # ==================== LIQUIDITY ANALYSIS ====================
    
    def calculate_liquidity_metrics(self) -> LiquidityMetrics:
        """Analyze liquidity structure and key zones."""
        if not self.order_books or not self.prices:
            return LiquidityMetrics()
        
        ob = self.order_books[-1]
        prices = list(self.prices)
        volumes = list(self.volumes)
        
        # Calculate VWAP
        if volumes:
            vwap = sum(p * v for p, v in zip(prices[-100:], volumes[-100:])) / (sum(volumes[-100:]) + self.EPSILON)
        else:
            vwap = prices[-1] if prices else 0
        
        # Identify liquidity zones (high depth areas)
        liquidity_zones = []
        for level in ob.bids[:20] + ob.asks[:20]:
            if level.quantity > np.mean([l.quantity for l in ob.bids[:10] + ob.asks[:10]]) * 1.5:
                liquidity_zones.append({
                    'price': level.price,
                    'quantity': level.quantity,
                    'type': 'support' if level in ob.bids else 'resistance'
                })
        
        # Volume profile (simplified)
        volume_profile = []
        if prices and volumes:
            price_bins = np.linspace(min(prices[-500:]), max(prices[-500:]), 20)
            for i in range(len(price_bins) - 1):
                vol_at_level = sum(v for p, v in zip(prices[-500:], volumes[-500:]) 
                                  if price_bins[i] <= p < price_bins[i+1])
                volume_profile.append({
                    'price': (price_bins[i] + price_bins[i+1]) / 2,
                    'volume': vol_at_level
                })
        
        # Premium/Discount zones
        current_price = prices[-1] if prices else 0
        premium_zone = current_price > vwap * 1.002
        discount_zone = current_price < vwap * 0.998
        
        return LiquidityMetrics(
            liquidity_zones=liquidity_zones,
            volume_profile=volume_profile,
            vwap=vwap,
            premium_zone=premium_zone,
            discount_zone=discount_zone
        )
    
    # ==================== COMPOSITE SIGNAL GENERATION ====================
    
    def generate_signal(self, symbol: str) -> TradingSignal:
        """Generate composite high-frequency trading signal.
        
        HFSS(t) = w1*Δ̃(t) + w2*AS̃(t) + w3*IP̃(t) + w4*OFMBĨ(t) + w5*Structurẽ(t) - w6*SpreadPeñ(t)
        """
        # Calculate all metrics
        delta = self.calculate_delta_metrics()
        absorption = self.calculate_absorption_metrics()
        iceberg = self.calculate_iceberg_metrics()
        momentum = self.calculate_momentum_metrics()
        structure = self.calculate_structure_metrics()
        liquidity = self.calculate_liquidity_metrics()
        
        # Normalize components to [-1, 1] or [0, 1]
        delta_normalized = np.clip(delta.normalized_delta, -1, 1)
        
        # Absorption: positive for bid absorption (bullish), negative for ask absorption (bearish)
        absorption_normalized = np.clip(absorption.bid_absorption - absorption.ask_absorption, -1, 1)
        
        # Iceberg: directional based on where icebergs detected
        iceberg_normalized = iceberg.probability * 0.5  # Scale down
        
        # OFMBI: already directional
        ofmbi_normalized = np.clip(momentum.ofmbi / 100, -1, 1)  # Scale
        
        # Structure factor
        structure_factor = 0.0
        if structure.trend_direction == "up":
            structure_factor = 0.5
            if structure.bos_detected:
                structure_factor = 0.8
        elif structure.trend_direction == "down":
            structure_factor = -0.5
            if structure.bos_detected:
                structure_factor = -0.8
        if structure.choch_detected:
            structure_factor *= -0.5  # Reduce confidence on CHOCH
        
        # Spread penalty
        spread_penalty = 0.0
        if self.order_books and self.median_spread > 0:
            current_spread = self.order_books[-1].spread
            atr = self.get_current_atr()
            spread_penalty = (current_spread / self.median_spread) * (atr / (self.median_atr + self.EPSILON))
            spread_penalty = min(spread_penalty, 1.0)
        
        # Calculate HFSS
        hfss = (
            self.weights.delta_weight * delta_normalized +
            self.weights.absorption_weight * absorption_normalized +
            self.weights.iceberg_weight * iceberg_normalized +
            self.weights.ofmbi_weight * ofmbi_normalized +
            self.weights.structure_weight * structure_factor -
            self.weights.spread_penalty_weight * spread_penalty
        )
        
        # Convert to probabilities using softmax
        # Scale HFSS to reasonable range for softmax
        scaled_hfss = hfss * 3  # Scale factor
        
        exp_buy = math.exp(scaled_hfss)
        exp_sell = math.exp(-scaled_hfss)
        exp_none = math.exp(0)  # Neutral
        
        total = exp_buy + exp_sell + exp_none
        p_buy = exp_buy / total
        p_sell = exp_sell / total
        p_none = exp_none / total
        
        # Determine signal
        if p_buy > 0.45 and p_buy > p_sell:
            signal_type = SignalType.BUY
            confidence = p_buy
        elif p_sell > 0.45 and p_sell > p_buy:
            signal_type = SignalType.SELL
            confidence = p_sell
        else:
            signal_type = SignalType.NO_TRADE
            confidence = p_none
        
        # Build reason breakdown
        reasons = []
        if abs(delta_normalized) > 0.3:
            reasons.append(f"Delta: {'Bullish' if delta_normalized > 0 else 'Bearish'} ({delta_normalized:.2f})")
        if absorption.strength > 0.3:
            reasons.append(f"Absorption: {'Bid' if absorption_normalized > 0 else 'Ask'} wall detected")
        if iceberg.probability > 0.5:
            reasons.append(f"Iceberg: Hidden liquidity detected ({iceberg.probability:.1%})")
        if abs(momentum.ofmbi) > 10:
            reasons.append(f"Momentum: {'Burst up' if momentum.ofmbi > 0 else 'Burst down'}")
        if structure.bos_detected:
            reasons.append("Structure: Break of structure")
        if structure.choch_detected:
            reasons.append("Structure: Change of character")
        
        current_price = self.prices[-1] if self.prices else 0
        
        return TradingSignal(
            symbol=symbol,
            signal_type=signal_type,
            hfss_score=hfss,
            probability_buy=p_buy,
            probability_sell=p_sell,
            probability_no_trade=p_none,
            confidence=confidence,
            breakdown=SignalBreakdown(
                delta_contribution=self.weights.delta_weight * delta_normalized,
                absorption_contribution=self.weights.absorption_weight * absorption_normalized,
                iceberg_contribution=self.weights.iceberg_weight * iceberg_normalized,
                momentum_contribution=self.weights.ofmbi_weight * ofmbi_normalized,
                structure_contribution=self.weights.structure_weight * structure_factor,
                spread_penalty=self.weights.spread_penalty_weight * spread_penalty
            ),
            reason=" | ".join(reasons) if reasons else "No significant signals",
            price_at_signal=current_price
        )
    
    def get_all_metrics(self) -> Dict:
        """Get all current metrics for display."""
        return {
            'delta': self.calculate_delta_metrics().dict(),
            'absorption': self.calculate_absorption_metrics().dict(),
            'iceberg': self.calculate_iceberg_metrics().dict(),
            'momentum': self.calculate_momentum_metrics().dict(),
            'structure': self.calculate_structure_metrics().dict(),
            'liquidity': self.calculate_liquidity_metrics().dict()
        }
