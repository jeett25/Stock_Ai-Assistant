from typing import Dict, Optional, List, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SignalGenerator:
    # Signal weights for confidence calculation
    SIGNAL_WEIGHTS = {
        'rsi': 0.20,
        'macd': 0.25,
        'ma_cross': 0.20,
        'bollinger': 0.15,
        'trend': 0.20
    }
    
    def generate_signal(self, indicators: Dict) -> Dict:
        """
        Generate trading signal from technical indicators.
        
        Args:
            indicators: Dict of calculated technical indicators
            
        Returns:
            Dict with signal, confidence, and reasoning
        """
        if not indicators:
            return self._create_signal('HOLD', 0.0, ['Insufficient data'])
        
        # Check each indicator
        rsi_signal = self._analyze_rsi(indicators)
        macd_signal = self._analyze_macd(indicators)
        ma_signal = self._analyze_moving_averages(indicators)
        bb_signal = self._analyze_bollinger_bands(indicators)
        trend_signal = self._analyze_trend(indicators)
        
        # Aggregate signals
        all_signals = [rsi_signal, macd_signal, ma_signal, bb_signal, trend_signal]
        
        # Calculate weighted score (-1 to +1)
        score = self._calculate_weighted_score(all_signals)
        
        # Determine final signal
        if score >= 0.6:
            signal = 'STRONG_BUY'
        elif score >= 0.2:
            signal = 'BUY'
        elif score <= -0.6:
            signal = 'STRONG_SELL'
        elif score <= -0.2:
            signal = 'SELL'
        else:
            signal = 'HOLD'
        
        # Calculate confidence (0-1)
        confidence = min(abs(score), 1.0)
        
        # Collect reasons
        reasons = self._collect_reasons(all_signals)
        
        return self._create_signal(signal, confidence, reasons, indicators)
    
    def _analyze_rsi(self, indicators: Dict) -> Tuple[str, float, str]:
        """
        Analyze RSI indicator.
        
        Returns:
            (signal, score, reason)
        """
        rsi = indicators.get('rsi')
        
        if rsi is None:
            return ('NEUTRAL', 0.0, 'RSI: No data')
        
        if rsi < 30:
            return ('BUY', 0.8, f'RSI oversold ({rsi:.1f})')
        elif rsi < 40:
            return ('BUY', 0.4, f'RSI slightly oversold ({rsi:.1f})')
        elif rsi > 70:
            return ('SELL', -0.8, f'RSI overbought ({rsi:.1f})')
        elif rsi > 60:
            return ('SELL', -0.4, f'RSI slightly overbought ({rsi:.1f})')
        else:
            return ('NEUTRAL', 0.0, f'RSI neutral ({rsi:.1f})')
    
    def _analyze_macd(self, indicators: Dict) -> Tuple[str, float, str]:
        """
        Analyze MACD indicator.
        """
        macd = indicators.get('macd_value')
        signal = indicators.get('macd_signal')
        histogram = indicators.get('macd_histogram')
        
        if macd is None or signal is None or histogram is None:
            return ('NEUTRAL', 0.0, 'MACD: No data')
        
        # MACD crossover
        if macd > signal and histogram > 0:
            strength = min(abs(histogram) * 10, 0.8)  # Scale histogram
            return ('BUY', strength, f'MACD bullish crossover (hist: {histogram:.3f})')
        elif macd < signal and histogram < 0:
            strength = min(abs(histogram) * 10, 0.8)
            return ('SELL', -strength, f'MACD bearish crossover (hist: {histogram:.3f})')
        else:
            return ('NEUTRAL', 0.0, 'MACD neutral')
    
    def _analyze_moving_averages(self, indicators: Dict) -> Tuple[str, float, str]:
        """
        Analyze moving average trends and crossovers.
        """
        price = indicators.get('close_price')
        sma_20 = indicators.get('sma_20')
        sma_50 = indicators.get('sma_50')
        sma_200 = indicators.get('sma_200')
        
        if not all([price, sma_20, sma_50]):
            return ('NEUTRAL', 0.0, 'MA: Insufficient data')
        
        reasons = []
        score = 0.0
        
        # Price vs moving averages
        if price > sma_20:
            score += 0.3
            reasons.append('above 20-day MA')
        else:
            score -= 0.3
            reasons.append('below 20-day MA')
        
        if sma_200 and price > sma_200:
            score += 0.3
            reasons.append('above 200-day MA (long-term bullish)')
        elif sma_200 and price < sma_200:
            score -= 0.3
            reasons.append('below 200-day MA (long-term bearish)')
        
        # Golden cross / Death cross
        if sma_50 and sma_200:
            if sma_50 > sma_200:
                score += 0.4
                reasons.append('golden cross (50>200)')
            elif sma_50 < sma_200:
                score -= 0.4
                reasons.append('death cross (50<200)')
        
        reason_text = f"MA: Price {', '.join(reasons)}"
        
        if score > 0:
            return ('BUY', min(score, 1.0), reason_text)
        elif score < 0:
            return ('SELL', max(score, -1.0), reason_text)
        else:
            return ('NEUTRAL', 0.0, reason_text)
    
    def _analyze_bollinger_bands(self, indicators: Dict) -> Tuple[str, float, str]:
        """
        Analyze Bollinger Bands position.
        """
        price = indicators.get('close_price')
        bb_upper = indicators.get('bb_upper')
        bb_middle = indicators.get('bb_middle')
        bb_lower = indicators.get('bb_lower')
        
        if not all([price, bb_upper, bb_middle, bb_lower]):
            return ('NEUTRAL', 0.0, 'BB: No data')
        
        band_width = bb_upper - bb_lower
        position = (price - bb_lower) / band_width if band_width > 0 else 0.5
        
        if position < 0.2:
            return ('BUY', 0.6, f'BB: Near lower band (oversold)')
        elif position > 0.8:
            return ('SELL', -0.6, f'BB: Near upper band (overbought)')
        else:
            return ('NEUTRAL', 0.0, f'BB: Middle range')
    
    def _analyze_trend(self, indicators: Dict) -> Tuple[str, float, str]:
        """
        Analyze overall price trend.
        """
        sma_20 = indicators.get('sma_20')
        sma_50 = indicators.get('sma_50')
        volatility = indicators.get('volatility')
        
        if not all([sma_20, sma_50]):
            return ('NEUTRAL', 0.0, 'Trend: No data')
        
        # Trend direction
        if sma_20 > sma_50:
            trend_score = 0.5
            trend_text = 'uptrend'
        elif sma_20 < sma_50:
            trend_score = -0.5
            trend_text = 'downtrend'
        else:
            trend_score = 0.0
            trend_text = 'sideways'
        
        # Adjust for volatility
        if volatility and volatility > 3.0:
            # High volatility = lower confidence
            trend_score *= 0.7
            trend_text += ' (high volatility)'
        
        reason = f'Trend: {trend_text}'
        
        if trend_score > 0:
            return ('BUY', trend_score, reason)
        elif trend_score < 0:
            return ('SELL', trend_score, reason)
        else:
            return ('NEUTRAL', 0.0, reason)
    
    def _calculate_weighted_score(
        self,
        signals: List[Tuple[str, float, str]]
    ) -> float:
        """
        Calculate weighted average of all signal scores.
        """
        weights = list(self.SIGNAL_WEIGHTS.values())
        scores = [sig[1] for sig in signals]
        
        weighted_sum = sum(w * s for w, s in zip(weights, scores))
        return weighted_sum
    
    def _collect_reasons(
        self,
        signals: List[Tuple[str, float, str]]
    ) -> List[str]:
        """
        Collect all non-neutral reasons.
        """
        reasons = []
        for sig_type, score, reason in signals:
            if sig_type != 'NEUTRAL' and abs(score) > 0.1:
                reasons.append(reason)
        
        return reasons if reasons else ['No strong signals']
    
    def _create_signal(
        self,
        signal: str,
        confidence: float,
        reasons: List[str],
        indicators: Optional[Dict] = None
    ) -> Dict:
        """
        Create standardized signal response.
        """
        return {
            'signal': signal,
            'confidence': round(confidence, 2),
            'reasons': reasons,
            'timestamp': datetime.utcnow().isoformat(),
            'indicators_used': indicators
        }