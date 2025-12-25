import pandas as pd
import numpy as np
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import logging

from app.models.stock import StockPrice

logger = logging.getLogger(__name__)


class TechnicalAnalyzer:
    """
    Calculate technical indicators from price data.
    All methods are static and deterministic.
    """
    
    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        # Calculate price changes
        delta = prices.diff()
        
        # Separate gains and losses
        gains = delta.where(delta > 0, 0.0)
        losses = -delta.where(delta < 0, 0.0)
        
        # Calculate average gains and losses
        avg_gains = gains.rolling(window=period, min_periods=period).mean()
        avg_losses = losses.rolling(window=period, min_periods=period).mean()
        
        # Calculate RS and RSI
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def calculate_macd(
        prices: pd.Series,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Dict[str, pd.Series]:
        # Calculate EMAs
        ema_fast = prices.ewm(span=fast_period, adjust=False).mean()
        ema_slow = prices.ewm(span=slow_period, adjust=False).mean()
        
        # Calculate MACD line
        macd_line = ema_fast - ema_slow
        
        # Calculate signal line
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        
        # Calculate histogram
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    @staticmethod
    def calculate_sma(prices: pd.Series, period: int) -> pd.Series:
        return prices.rolling(window=period, min_periods=period).mean()
    
    @staticmethod
    def calculate_ema(prices: pd.Series, period: int) -> pd.Series:
        """
        Calculate Exponential Moving Average (EMA).
        Gives more weight to recent prices.
        """
        return prices.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def calculate_bollinger_bands(
        prices: pd.Series,
        period: int = 20,
        std_dev: float = 2.0
    ) -> Dict[str, pd.Series]:
        """
        Calculate Bollinger Bands.
        
        Bands expand/contract with volatility:
        - Upper Band: SMA + (std_dev × standard deviation)
        - Middle Band: SMA
        - Lower Band: SMA - (std_dev × standard deviation)
        
        Signals:
        - Price near upper band: Overbought
        - Price near lower band: Oversold
        - Bands narrowing: Low volatility (breakout coming)
        - Bands widening: High volatility
        """
        sma = prices.rolling(window=period, min_periods=period).mean()
        std = prices.rolling(window=period, min_periods=period).std()
        
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        return {
            'upper': upper_band,
            'middle': sma,
            'lower': lower_band
        }
    
    @staticmethod
    def calculate_volatility(prices: pd.Series, period: int = 20) -> pd.Series:
        """
        Calculate historical volatility (standard deviation of returns).
        Higher values indicate more price movement.
        """
        returns = prices.pct_change()
        volatility = returns.rolling(window=period, min_periods=period).std()
        return volatility * 100  # Convert to percentage
    
    @staticmethod
    def calculate_support_resistance(
        prices: pd.DataFrame,
        lookback_period: int = 20
    ) -> Dict[str, float]:
        """
        Identify support and resistance levels.
        
        Support: Price level where buying pressure prevents further decline
        Resistance: Price level where selling pressure prevents further rise
        
        Simple method: Use recent highs/lows
        """
        recent_data = prices.tail(lookback_period)
        
        support = recent_data['low'].min()
        resistance = recent_data['high'].max()
        
        return {
            'support': float(support),
            'resistance': float(resistance),
            'range': float(resistance - support)
        }
    
    @staticmethod
    def prepare_dataframe(price_records: List[StockPrice]) -> pd.DataFrame:
        """
        Convert SQLAlchemy price records to pandas DataFrame.
        """
        if not price_records:
            return pd.DataFrame()
        
        data = {
            'date': [p.date for p in price_records],
            'open': [float(p.open) for p in price_records],
            'high': [float(p.high) for p in price_records],
            'low': [float(p.low) for p in price_records],
            'close': [float(p.close) for p in price_records],
            'volume': [p.volume for p in price_records]
        }
        
        df = pd.DataFrame(data)
        df.set_index('date', inplace=True)
        df.sort_index(inplace=True)
        
        return df


class IndicatorCalculator:
    """
    High-level interface for calculating all indicators at once.
    """
    
    def __init__(self):
        self.analyzer = TechnicalAnalyzer()
    
    def calculate_all_indicators(
        self,
        price_records: List[StockPrice],
        ticker: str
    ) -> Optional[Dict]:
        """
        Calculate all technical indicators for a ticker.
        
        Returns:
            Dict with all indicator values and metadata
        """
        if len(price_records) < 50:
            logger.warning(
                f"Insufficient data for {ticker}: {len(price_records)} records "
                "(need at least 50 for reliable indicators)"
            )
            return None
        
        try:
            # Prepare dataframe
            df = self.analyzer.prepare_dataframe(price_records)
            
            if df.empty:
                return None
            
            # Calculate indicators
            rsi = self.analyzer.calculate_rsi(df['close'])
            macd_data = self.analyzer.calculate_macd(df['close'])
            sma_20 = self.analyzer.calculate_sma(df['close'], 20)
            sma_50 = self.analyzer.calculate_sma(df['close'], 50)
            sma_200 = self.analyzer.calculate_sma(df['close'], 200)
            ema_12 = self.analyzer.calculate_ema(df['close'], 12)
            ema_26 = self.analyzer.calculate_ema(df['close'], 26)
            bb_data = self.analyzer.calculate_bollinger_bands(df['close'])
            volatility = self.analyzer.calculate_volatility(df['close'])
            support_resistance = self.analyzer.calculate_support_resistance(df)
            
            # Get latest values (most recent day)
            latest_date = df.index[-1]
            latest_close = float(df['close'].iloc[-1])
            
            indicators = {
                'ticker': ticker,
                'date': latest_date,
                'close_price': latest_close,
                
                # RSI
                'rsi': float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None,
                
                # MACD
                'macd_value': float(macd_data['macd'].iloc[-1]) if not pd.isna(macd_data['macd'].iloc[-1]) else None,
                'macd_signal': float(macd_data['signal'].iloc[-1]) if not pd.isna(macd_data['signal'].iloc[-1]) else None,
                'macd_histogram': float(macd_data['histogram'].iloc[-1]) if not pd.isna(macd_data['histogram'].iloc[-1]) else None,
                
                # Moving Averages
                'sma_20': float(sma_20.iloc[-1]) if not pd.isna(sma_20.iloc[-1]) else None,
                'sma_50': float(sma_50.iloc[-1]) if not pd.isna(sma_50.iloc[-1]) else None,
                'sma_200': float(sma_200.iloc[-1]) if not pd.isna(sma_200.iloc[-1]) else None,
                'ema_12': float(ema_12.iloc[-1]) if not pd.isna(ema_12.iloc[-1]) else None,
                'ema_26': float(ema_26.iloc[-1]) if not pd.isna(ema_26.iloc[-1]) else None,
                
                # Bollinger Bands
                'bb_upper': float(bb_data['upper'].iloc[-1]) if not pd.isna(bb_data['upper'].iloc[-1]) else None,
                'bb_middle': float(bb_data['middle'].iloc[-1]) if not pd.isna(bb_data['middle'].iloc[-1]) else None,
                'bb_lower': float(bb_data['lower'].iloc[-1]) if not pd.isna(bb_data['lower'].iloc[-1]) else None,
                
                # Volatility
                'volatility': float(volatility.iloc[-1]) if not pd.isna(volatility.iloc[-1]) else None,
                
                # Support/Resistance
                'support': support_resistance['support'],
                'resistance': support_resistance['resistance'],
                'price_range': support_resistance['range'],
            }
            
            logger.info(f"Calculated indicators for {ticker} on {latest_date}")
            return indicators
            
        except Exception as e:
            logger.error(f"Error calculating indicators for {ticker}: {e}")
            return None