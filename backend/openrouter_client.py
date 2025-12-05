"""OpenRouter API Client for AI Model Integration"""
import httpx
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from models import AIModel, AIAnalysisRequest, AIAnalysisResponse, TradingSignal

logger = logging.getLogger(__name__)


class OpenRouterClient:
    """Client for OpenRouter API to access various AI models."""
    
    BASE_URL = "https://openrouter.ai/api/v1"
    
    def __init__(self):
        self.api_key: str = ""
        self.selected_model: str = ""
        self.models_cache: List[AIModel] = []
        self.cache_timestamp: Optional[datetime] = None
        self.cache_duration = timedelta(hours=1)
        self.is_connected = False
    
    def set_api_key(self, api_key: str):
        """Set the OpenRouter API key."""
        self.api_key = api_key
        self.is_connected = bool(api_key)
    
    def set_model(self, model_id: str):
        """Set the selected AI model."""
        self.selected_model = model_id
    
    async def fetch_models(self, force_refresh: bool = False) -> List[AIModel]:
        """Fetch available models from OpenRouter."""
        # Return cached if valid
        if not force_refresh and self.models_cache and self.cache_timestamp:
            if datetime.utcnow() - self.cache_timestamp < self.cache_duration:
                return self.models_cache
        
        if not self.api_key:
            logger.warning("No API key set for OpenRouter")
            return []
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/models",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    models = []
                    
                    for model_data in data.get('data', []):
                        model = AIModel(
                            id=model_data.get('id', ''),
                            name=model_data.get('name', model_data.get('id', '')),
                            context_length=model_data.get('context_length', 0),
                            pricing_prompt=model_data.get('pricing', {}).get('prompt', 0),
                            pricing_completion=model_data.get('pricing', {}).get('completion', 0),
                            description=model_data.get('description', '')
                        )
                        models.append(model)
                    
                    self.models_cache = models
                    self.cache_timestamp = datetime.utcnow()
                    self.is_connected = True
                    
                    logger.info(f"Fetched {len(models)} models from OpenRouter")
                    return models
                else:
                    logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
                    self.is_connected = False
                    return []
                    
        except Exception as e:
            logger.error(f"Error fetching OpenRouter models: {e}")
            self.is_connected = False
            return []
    
    async def analyze_order_flow(
        self,
        context: str,
        metrics: Dict[str, Any],
        signal: Optional[TradingSignal] = None
    ) -> AIAnalysisResponse:
        """Use AI to analyze order flow and provide insights.
        
        Includes safety checks to validate AI outputs against quantitative data.
        """
        if not self.api_key or not self.selected_model:
            return AIAnalysisResponse(
                analysis="AI analysis unavailable - API key or model not configured",
                validated=False
            )
        
        # Build prompt
        prompt = self._build_analysis_prompt(context, metrics, signal)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://hft-signal-generator.app",
                        "X-Title": "HFT Signal Generator"
                    },
                    json={
                        "model": self.selected_model,
                        "messages": [
                            {
                                "role": "system",
                                "content": """You are an expert high-frequency trading analyst specializing in order flow analysis, market microstructure, and quantitative trading signals. 
                                
Your task is to:
1. Interpret the provided order flow metrics and market data
2. Identify potential anomalies or significant patterns
3. Provide actionable trading insights
4. Explain what large institutional players might be doing

Be concise, specific, and data-driven. Focus on actionable insights.
Always ground your analysis in the quantitative metrics provided."""
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "max_tokens": 500,
                        "temperature": 0.3  # Lower temperature for more consistent analysis
                    },
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    ai_response = data['choices'][0]['message']['content']
                    
                    # Validate AI response against quantitative data
                    validated, confidence_adjustment = self._validate_ai_response(
                        ai_response, metrics, signal
                    )
                    
                    # Extract anomalies and insights
                    anomalies = self._extract_anomalies(ai_response)
                    insight = self._extract_trading_insight(ai_response)
                    
                    return AIAnalysisResponse(
                        analysis=ai_response,
                        anomalies_detected=anomalies,
                        trading_insight=insight,
                        confidence_adjustment=confidence_adjustment,
                        validated=validated
                    )
                else:
                    logger.error(f"OpenRouter completion error: {response.status_code}")
                    return AIAnalysisResponse(
                        analysis=f"AI analysis failed: {response.status_code}",
                        validated=False
                    )
                    
        except Exception as e:
            logger.error(f"Error in AI analysis: {e}")
            return AIAnalysisResponse(
                analysis=f"AI analysis error: {str(e)}",
                validated=False
            )
    
    def _build_analysis_prompt(self, context: str, metrics: Dict[str, Any], signal: Optional[TradingSignal]) -> str:
        """Build the analysis prompt for the AI model."""
        prompt_parts = [
            f"## Market Context\n{context}\n",
            "## Order Flow Metrics\n"
        ]
        
        # Add metrics
        if 'delta' in metrics:
            delta = metrics['delta']
            prompt_parts.append(f"- Raw Delta: {delta.get('raw_delta', 0):.2f}")
            prompt_parts.append(f"- Normalized Delta: {delta.get('normalized_delta', 0):.4f}")
            prompt_parts.append(f"- Cumulative Delta: {delta.get('cumulative_delta', 0):.2f}")
        
        if 'absorption' in metrics:
            absorption = metrics['absorption']
            prompt_parts.append(f"- Absorption Score: {absorption.get('score', 0):.4f}")
            prompt_parts.append(f"- Bid Absorption: {absorption.get('bid_absorption', 0):.4f}")
            prompt_parts.append(f"- Ask Absorption: {absorption.get('ask_absorption', 0):.4f}")
        
        if 'iceberg' in metrics:
            iceberg = metrics['iceberg']
            prompt_parts.append(f"- Iceberg Probability: {iceberg.get('probability', 0):.4f}")
            prompt_parts.append(f"- Fill-to-Display Ratio: {iceberg.get('fill_to_display_ratio', 0):.4f}")
        
        if 'momentum' in metrics:
            momentum = metrics['momentum']
            prompt_parts.append(f"- OFMBI: {momentum.get('ofmbi', 0):.4f}")
            prompt_parts.append(f"- Tape Speed: {momentum.get('tape_speed', 0):.2f} trades/sec")
        
        if 'structure' in metrics:
            structure = metrics['structure']
            prompt_parts.append(f"- Market Regime: {structure.get('regime', 'unknown')}")
            prompt_parts.append(f"- Trend Direction: {structure.get('trend_direction', 'neutral')}")
            prompt_parts.append(f"- BOS Detected: {structure.get('bos_detected', False)}")
            prompt_parts.append(f"- CHOCH Detected: {structure.get('choch_detected', False)}")
        
        if signal:
            prompt_parts.append(f"\n## Current Signal")
            prompt_parts.append(f"- Signal Type: {signal.signal_type.value}")
            prompt_parts.append(f"- HFSS Score: {signal.hfss_score:.4f}")
            prompt_parts.append(f"- Confidence: {signal.confidence:.2%}")
            prompt_parts.append(f"- P(Buy): {signal.probability_buy:.2%}")
            prompt_parts.append(f"- P(Sell): {signal.probability_sell:.2%}")
        
        prompt_parts.append("\n## Analysis Request")
        prompt_parts.append("1. What is the current order flow telling us about institutional activity?")
        prompt_parts.append("2. Are there any anomalies in the data?")
        prompt_parts.append("3. What is the likely short-term direction based on microstructure?")
        prompt_parts.append("4. Any hidden liquidity or iceberg orders detected?")
        
        return "\n".join(prompt_parts)
    
    def _validate_ai_response(
        self,
        ai_response: str,
        metrics: Dict[str, Any],
        signal: Optional[TradingSignal]
    ) -> tuple[bool, float]:
        """Validate AI response against quantitative data.
        
        Returns (is_valid, confidence_adjustment)
        """
        confidence_adjustment = 0.0
        
        # Check for directional consistency
        ai_bullish = any(word in ai_response.lower() for word in ['bullish', 'buying', 'long', 'upward'])
        ai_bearish = any(word in ai_response.lower() for word in ['bearish', 'selling', 'short', 'downward'])
        
        if signal:
            quant_bullish = signal.probability_buy > signal.probability_sell
            quant_bearish = signal.probability_sell > signal.probability_buy
            
            # Check consistency
            if (ai_bullish and quant_bearish) or (ai_bearish and quant_bullish):
                # AI contradicts quantitative signal - downgrade confidence
                confidence_adjustment = -0.2
                logger.warning("AI analysis contradicts quantitative signal")
            elif (ai_bullish and quant_bullish) or (ai_bearish and quant_bearish):
                # AI confirms quantitative signal - slight boost
                confidence_adjustment = 0.05
        
        # Check for hallucination indicators
        hallucination_indicators = [
            'certainly', 'definitely', 'guaranteed', 'will absolutely',
            '100%', 'impossible', 'never fail'
        ]
        
        has_hallucination = any(indicator in ai_response.lower() for indicator in hallucination_indicators)
        if has_hallucination:
            confidence_adjustment -= 0.1
        
        # Validated if no major issues
        is_valid = confidence_adjustment >= -0.1
        
        return is_valid, confidence_adjustment
    
    def _extract_anomalies(self, ai_response: str) -> List[str]:
        """Extract detected anomalies from AI response."""
        anomalies = []
        
        anomaly_keywords = ['anomaly', 'unusual', 'abnormal', 'spike', 'irregular', 'divergence']
        
        lines = ai_response.split('\n')
        for line in lines:
            if any(keyword in line.lower() for keyword in anomaly_keywords):
                anomalies.append(line.strip())
        
        return anomalies[:5]  # Limit to 5 anomalies
    
    def _extract_trading_insight(self, ai_response: str) -> str:
        """Extract main trading insight from AI response."""
        # Look for conclusion or recommendation
        lines = ai_response.split('\n')
        
        for i, line in enumerate(lines):
            if any(word in line.lower() for word in ['conclusion', 'recommendation', 'suggest', 'likely']):
                # Return this line and the next if available
                insight = line.strip()
                if i + 1 < len(lines):
                    insight += " " + lines[i + 1].strip()
                return insight[:300]  # Limit length
        
        # If no specific conclusion, return last non-empty line
        for line in reversed(lines):
            if line.strip():
                return line.strip()[:300]
        
        return "No specific insight extracted"
    
    async def get_quick_summary(self, metrics: Dict[str, Any]) -> str:
        """Get a quick one-liner summary of current market state."""
        if not self.api_key or not self.selected_model:
            return "AI summary unavailable"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.selected_model,
                        "messages": [
                            {
                                "role": "user",
                                "content": f"""In one sentence (max 100 chars), summarize this market state:
Delta: {metrics.get('delta', {}).get('normalized_delta', 0):.3f}
Absorption: {metrics.get('absorption', {}).get('score', 0):.3f}
Regime: {metrics.get('structure', {}).get('regime', 'unknown')}
Trend: {metrics.get('structure', {}).get('trend_direction', 'neutral')}"""
                            }
                        ],
                        "max_tokens": 50,
                        "temperature": 0.5
                    },
                    timeout=15.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data['choices'][0]['message']['content'].strip()
                    
        except Exception as e:
            logger.error(f"Error getting quick summary: {e}")
        
        return "AI summary unavailable"
