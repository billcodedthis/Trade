import pandas as pd
import numpy as np
import MetaTrader5 as mt5
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta
import os
from pathlib import Path
import warnings
import signal
import sys
warnings.filterwarnings('ignore')

# ==================== MT5 CONNECTION ====================

MT5_PATH = "C:\\Program Files\\MetaTrader 5 Terminal\\terminal64.exe"
if not mt5.initialize(path=MT5_PATH):
    print("❌ Failed to connect to MetaTrader 5", mt5.last_error())
    quit()
else:
    print("✅ Successfully connected to MT5!")

# ==================== CONFIGURATION ====================

# Define symbols and timeframes (same as original)
Basket_Indices = ['AUD Basket', 'EUR Basket', 'GBP Basket', 'Gold Basket', 'USD Basket']
Crash_Boom_Indices = ['Boom 1000 Index', 'Boom 150 Index', 'Boom 300 Index', 'Boom 500 Index', 
                      'Boom 600 Index', 'Boom 900 Index', 'Crash 1000 Index', 'Crash 150 Index', 
                      'Crash 300 Index', 'Crash 500 Index', 'Crash 600 Index', 'Crash 900 Index']
Crypto = ['ADAUSD', 'ALGUSD', 'AVAUSD', 'BATUSD', 'BCHUSD', 'BNBUSD', 'BTCETH', 'BTCLTC', 
          'BTCUSD', 'DOGUSD', 'DOTUSD', 'DSHUSD', 'ETCUSD', 'ETHUSD', 'IOTUSD', 'LNKUSD', 
          'LTCUSD', 'SOLUSD', 'UNIUSD', 'XLMUSD', 'XRPUSD', 'ZECUSD']
DEX_Indices = ['DEX 1500 DOWN Index', 'DEX 1500 UP Index', 'DEX 600 DOWN Index', 
               'DEX 600 UP Index', 'DEX 900 DOWN Index', 'DEX 900 UP Index']
Energies = ['UK Brent Oil', 'US Oil']
Forex_Major = ['AUDJPY', 'AUDUSD', 'EURAUD', 'EURCAD', 'EURCHF', 'EURGBP', 'EURJPY', 
               'EURUSD', 'GBPAUD', 'GBPJPY', 'GBPUSD', 'USDCAD', 'USDCHF', 'USDJPY']
Forex_Minor = ['AUDCAD', 'AUDCHF', 'AUDNZD', 'CADCHF', 'CADJPY', 'CHFJPY', 'EURNOK', 
               'EURNZD', 'EURPLN', 'EURSEK', 'GBPCAD', 'GBPCHF', 'GBPNOK', 'GBPNZD', 
               'GBPSEK', 'NZDCAD', 'NZDJPY', 'NZDUSD', 'USDCNH', 'USDMXN', 'USDNOK', 
               'USDPLN', 'USDSEK', 'USDZAR']
Jump_Indices = ['Jump 10 Index', 'Jump 100 Index', 'Jump 25 Index', 'Jump 50 Index', 'Jump 75 Index']
Metals = ['XAGEUR', 'XAGUSD', 'XAUEUR', 'XAUUSD', 'XPDUSD', 'XPTUSD']
Multi_Step_Indices = ['Multi Step 2 Index', 'Multi Step 3 Index', 'Multi Step 4 Index']
Range_Break = ['Range Break 100 Index', 'Range Break 200 Index']
Skewed_Step = ['Skew Step Index 4 Down', 'Skew Step Index 4 Up', 
               'Skew Step Index 5 Down', 'Skew Step Index 5 Up']
Step_Indices = ['Step Index 200', 'Step Index 300', 'Step Index 400', 'Step Index 500', 'Step Index']
Stock_Indices = ['Australia 200', 'China H Shares', 'Europe 50', 'France 40', 'Germany 40', 
                 'Hong Kong 50', 'Japan 225', 'Netherlands 25', 'Spain 35', 'Swiss 20', 
                 'UK 100', 'US Mid Cap 400', 'US SP 500', 'US Small Cap 2000', 'US Tech 100', 
                 'Wall Street 30']
Volatility_Indices = ['Volatility 10 (1s) Index', 'Volatility 10 Index', 'Volatility 100 (1s) Index', 
                      'Volatility 100 Index', 'Volatility 15 (1s) Index', 'Volatility 150 (1s) Index', 
                      'Volatility 25 (1s) Index', 'Volatility 25 Index', 'Volatility 30 (1s) Index', 
                      'Volatility 50 (1s) Index', 'Volatility 50 Index', 'Volatility 75 (1s) Index', 
                      'Volatility 75 Index', 'Volatility 90 (1s) Index']

# Combine all symbols
ALL_SYMBOLS = list(set(Basket_Indices + Crash_Boom_Indices + Crypto + DEX_Indices + Energies + 
                       Forex_Major + Forex_Minor + Jump_Indices + Metals + Multi_Step_Indices + 
                       Range_Break + Skewed_Step + Step_Indices + Stock_Indices + Volatility_Indices))

# Symbol categorization (exactly as in visuals.py)
TIMEFRAME_H1 = ALL_SYMBOLS
TIMEFRAME_M15 = ALL_SYMBOLS
TIMEFRAME_M5 = ALL_SYMBOLS

H1_B = []  # Buy only
H1_S = []  # Sell only
H1_BS = ALL_SYMBOLS  # Both sides
H1_pen = ALL_SYMBOLS  # Pending orders
H1_pl = []  # Market orders

M15_B = []
M15_S = []
M15_BS = ALL_SYMBOLS
M15_pen = ALL_SYMBOLS
M15_pl = []

M5_B = []
M5_S = []
M5_BS = ALL_SYMBOLS
M5_pen = ALL_SYMBOLS
M5_pl = []

# Zone reload configuration (exactly as in visuals.py)
ZONE_RELOAD_CONFIG = {
    mt5.TIMEFRAME_M5: timedelta(hours=12),    # M5 zones reload every 12 hours
    mt5.TIMEFRAME_M15: timedelta(days=1),      # M15 zones reload daily
    mt5.TIMEFRAME_H1: timedelta(days=5),       # H1 zones reload every 5 days
    mt5.TIMEFRAME_H4: timedelta(days=7),       # H4 zones reload weekly
}

# ==================== BACKTESTING DATA STRUCTURES ====================

class BacktestState:
    def __init__(self):
        self.active_channels = {}  # (symbol, timeframe) -> channel data
        self.levels = {}  # (symbol, timeframe) -> Fibonacci levels
        self.old_engulfs = {}  # Track engulfing for trades not in levels
        self.breakeven_trades = {}  # Trades moved to breakeven
        self.active_trades = {}  # Currently open trades
        self.cooldown = {}  # Cooldown periods
        self.profit_tracking = {}  # Track profit duration
        self.supply_demand_zones = {}  # Store zones for each symbol
        self.zone_last_loaded = {}
        self.to_be_reloaded = []
        
        # Backtest specific
        self.current_time = None
        self.trade_history = []
        self.missed_trades = []
        self.equity_curve = []
        self.initial_capital = 10000
        self.current_capital = 10000
        
        # Statistics
        self.total_signals = 0
        self.executed_trades = 0
        self.missed_trades_count = 0

# ==================== HELPER FUNCTIONS ====================

def decimal_places(n):
    return len(str(n).rstrip('0').split('.')[-1]) if '.' in str(n) else 0

def timeframe_to_str(timeframe):
    """Convert MT5 timeframe constant to human-readable string (exactly as in visuals.py)"""
    if timeframe == mt5.TIMEFRAME_M1: return "M1"
    elif timeframe == mt5.TIMEFRAME_M5: return "M5"
    elif timeframe == mt5.TIMEFRAME_M15: return "M15"
    elif timeframe == mt5.TIMEFRAME_M30: return "M30"
    elif timeframe in (mt5.TIMEFRAME_H1, 16385): return "H1"
    elif timeframe == mt5.TIMEFRAME_H4: return "H4"
    elif timeframe == mt5.TIMEFRAME_D1: return "D1"
    elif timeframe == mt5.TIMEFRAME_W1: return "W1"
    elif timeframe == mt5.TIMEFRAME_MN1: return "MN1"
    else: return str(timeframe)

def get_min_lot_size(symbol):
    """Get minimum lot size from MT5"""
    info = mt5.symbol_info(symbol)
    if info:
        return info.volume_min
    else:
        return 0.01

def lot_size(symbol):
    """Calculate position size (exactly as in visuals.py)"""
    return 4 * get_min_lot_size(symbol)

# ==================== MT5 DATA FETCHING ====================

def fetch_historical_data(symbol, timeframe, start_date, end_date):
    """
    Fetch historical data from MT5 for a given symbol and timeframe
    """
    try:
        # Convert datetime to MT5-compatible format
        utc_from = datetime(start_date.year, start_date.month, start_date.day)
        utc_to = datetime(end_date.year, end_date.month, end_date.day)
        
        # Fetch rates
        rates = mt5.copy_rates_range(symbol, timeframe, utc_from, utc_to)
        
        if rates is None or len(rates) == 0:
            print(f"⚠️ No data for {symbol} {timeframe_to_str(timeframe)}")
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        # Rename columns if needed
        if 'tick_volume' in df.columns:
            df['volume'] = df['tick_volume']
        else:
            df['volume'] = 0
            
        # Ensure required columns exist in the right format
        required_cols = ['open', 'high', 'low', 'close', 'time']
        for col in required_cols:
            if col not in df.columns:
                print(f"⚠️ Missing column {col} in {symbol} data")
                return pd.DataFrame()
        
        print(f"✅ Fetched {len(df)} candles for {symbol} {timeframe_to_str(timeframe)}")
        return df
        
    except Exception as e:
        print(f"❌ Error fetching data for {symbol}: {e}")
        return pd.DataFrame()

def load_all_historical_data(symbols, timeframes, start_date, end_date):
    """
    Load historical data for all symbols and timeframes
    """
    historical_data = {}
    
    total_symbols = len(symbols)
    for i, symbol in enumerate(symbols):
        print(f"Loading data for {symbol} ({i+1}/{total_symbols})...")
        historical_data[symbol] = {}
        
        for tf in timeframes:
            df = fetch_historical_data(symbol, tf, start_date, end_date)
            if not df.empty:
                historical_data[symbol][tf] = df
            else:
                historical_data[symbol][tf] = pd.DataFrame()
    
    return historical_data

# ==================== SUPPLY/DEMAND ANALYZER (EXACTLY AS IN VISUALS.PY) ====================

class SupplyDemandAnalyzer:
    def __init__(self, data, lookback_period=20, min_touch_points=2):
        self.data = data.copy()
        self.lookback = lookback_period
        self.min_touches = min_touch_points
        
    def find_swing_points(self):
        data = self.data
        
        data['swing_high'] = np.nan
        data['swing_low'] = np.nan
        data['is_swing_high'] = False
        data['is_swing_low'] = False
        
        for i in range(self.lookback, len(data) - self.lookback):
            if (data['high'].iloc[i] == data['high'].iloc[i-self.lookback:i+self.lookback+1].max() and
                data['high'].iloc[i] > data['high'].iloc[i-1] and
                data['high'].iloc[i] > data['high'].iloc[i+1]):
                data.loc[data.index[i], 'swing_high'] = data['high'].iloc[i]
                data.loc[data.index[i], 'is_swing_high'] = True
            
            if (data['low'].iloc[i] == data['low'].iloc[i-self.lookback:i+self.lookback+1].min() and
                data['low'].iloc[i] < data['low'].iloc[i-1] and
                data['low'].iloc[i] < data['low'].iloc[i+1]):
                data.loc[data.index[i], 'swing_low'] = data['low'].iloc[i]
                data.loc[data.index[i], 'is_swing_low'] = True
        
        return data
    
    def identify_zones(self):
        data = self.find_swing_points()
        
        supply_zones = []
        demand_zones = []
        
        swing_highs = data[data['is_swing_high']].copy()
        swing_lows = data[data['is_swing_low']].copy()
        
        for i in range(len(swing_highs)):
            current_high = swing_highs.iloc[i]
            zone_price = current_high['high']
            
            touches = self.count_touches(data, zone_price, zone_type='supply')
            
            if touches >= self.min_touches and touches <= 20:
                is_broken = self.is_zone_broken(data, zone_price, zone_type='supply')
                
                supply_zones.append({
                    'price': zone_price,
                    'date': current_high.name,
                    'touches': touches,
                    'strength': touches,
                    'is_broken': is_broken
                })
        
        for i in range(len(swing_lows)):
            current_low = swing_lows.iloc[i]
            zone_price = current_low['low']
            
            touches = self.count_touches(data, zone_price, zone_type='demand')
            
            if touches >= self.min_touches and touches <= 20:
                is_broken = self.is_zone_broken(data, zone_price, zone_type='demand')
                
                demand_zones.append({
                    'price': zone_price,
                    'date': current_low.name,
                    'touches': touches,
                    'strength': touches,
                    'is_broken': is_broken
                })
        
        return supply_zones, demand_zones
    
    def is_zone_broken(self, data, zone_price, zone_type, consecutive_candles=3, tolerance=0.001):
        price_tolerance = zone_price * tolerance
        
        if zone_type == 'supply':
            zone_formation_idx = data[data['is_swing_high'] & (abs(data['high'] - zone_price) <= price_tolerance)].index
        else:
            zone_formation_idx = data[data['is_swing_low'] & (abs(data['low'] - zone_price) <= price_tolerance)].index
        
        if len(zone_formation_idx) == 0:
            return False
            
        zone_idx = data.index.get_loc(zone_formation_idx[-1])
        subsequent_data = data.iloc[zone_idx+1:]
        
        if len(subsequent_data) < consecutive_candles:
            return False
        
        consecutive_count = 0
        max_consecutive = 0
        
        for i in range(len(subsequent_data)):
            current_candle = subsequent_data.iloc[i]
            
            if zone_type == 'supply':
                if current_candle['close'] > zone_price + price_tolerance:
                    consecutive_count += 1
                    max_consecutive = max(max_consecutive, consecutive_count)
                else:
                    if (current_candle['high'] >= zone_price - price_tolerance and 
                        current_candle['low'] <= zone_price + price_tolerance):
                        consecutive_count = 0
                    else:
                        consecutive_count = 0
            else:
                if current_candle['close'] < zone_price - price_tolerance:
                    consecutive_count += 1
                    max_consecutive = max(max_consecutive, consecutive_count)
                else:
                    if (current_candle['high'] >= zone_price - price_tolerance and 
                        current_candle['low'] <= zone_price + price_tolerance):
                        consecutive_count = 0
                    else:
                        consecutive_count = 0
            
            if consecutive_count >= consecutive_candles:
                return True
        
        return False
    
    def count_touches(self, data, zone_price, zone_type, tolerance=0.001):
        touches = 0
        price_tolerance = zone_price * tolerance
        
        for i in range(len(data)):
            if zone_type == 'supply':
                if (abs(data['high'].iloc[i] - zone_price) <= price_tolerance or
                    (data['high'].iloc[i] >= zone_price and 
                     data['low'].iloc[i] <= zone_price)):
                    touches += 1
            else:
                if (abs(data['low'].iloc[i] - zone_price) <= price_tolerance or
                    (data['high'].iloc[i] >= zone_price and 
                     data['low'].iloc[i] <= zone_price)):
                    touches += 1
        
        return touches

# ==================== CHANNEL DETECTION FUNCTIONS (EXACTLY AS IN VISUALS.PY) ====================

def get_candles(symbol, timeframe, num_bars, historical_data, current_idx):
    """
    Get candles up to current index - exactly as live would get current candles
    """
    if symbol in historical_data and timeframe in historical_data[symbol]:
        df = historical_data[symbol][timeframe].iloc[:current_idx+1].copy()
        if len(df) >= num_bars:
            return df.iloc[-num_bars:].reset_index(drop=True)
    return pd.DataFrame()

def detect_regression_channel(df, symbol, timeframe, state, current_time):
    """
    Detect regression channel from candle data - EXACTLY as in visuals.py
    Returns: (validated, full_df, a_plus_setup)
    """
    # Split data - exclude last 5 candles for analysis but keep full data for plotting
    analysis_df = df.iloc[:-10].copy()
    full_df = df.copy()
    
    if len(analysis_df) < 20:  # Need enough data
        return False, full_df, False
    
    # Original channel calculation (using analysis portion only)
    X = np.arange(len(analysis_df)).reshape(-1, 1)
    y = analysis_df['close'].values
    model = LinearRegression().fit(X, y)
    trend_line = model.predict(X)
    residuals = y - trend_line
    std_dev = np.std(residuals)
    upper = trend_line + 2 * std_dev
    lower = trend_line - 3 * std_dev
    
    # Extend to full dataset for plotting
    X_full = np.arange(len(full_df)).reshape(-1, 1)
    trend_line_full = model.predict(X_full)
    upper_full = trend_line_full + 2 * std_dev
    lower_full = trend_line_full - 3 * std_dev
    
    # Store extended lines in full dataframe
    full_df['upper'] = upper_full
    full_df['lower'] = lower_full
    full_df['trend'] = trend_line_full

    # Original validation logic exactly as in visuals.py
    upper_touch_count = 0
    lower_touch_count = 0
    breakout = None
    validated = False
    upper_touch_indices = []
    lower_touch_indices = []
    
    for i in range(1, len(analysis_df)):
        # Check if there was a touch in the last 5 candles
        recent_upper_touch = any((i - idx) <= 5 for idx in upper_touch_indices)
        recent_lower_touch = any((i - idx) <= 5 for idx in lower_touch_indices)

        # Original touch counting logic
        if analysis_df['high'].iloc[i] > upper[i]:
            extreme_price = analysis_df['high'].iloc[i]
            new_upper_adjustment = extreme_price - upper[i]
            upper += new_upper_adjustment
            upper_full += new_upper_adjustment
            full_df['upper'] = upper_full
            
        if analysis_df['high'].iloc[i] == upper[i] and not recent_upper_touch:
            upper_touch_count += 1
            upper_touch_indices.append(i)
            
        if analysis_df['low'].iloc[i] < lower[i]:
            extreme_price = analysis_df['low'].iloc[i]
            new_lower_adjustment = extreme_price - lower[i]
            lower += new_lower_adjustment
            lower_full += new_lower_adjustment
            full_df['lower'] = lower_full
            
        if analysis_df['low'].iloc[i] == lower[i] and not recent_lower_touch:
            lower_touch_count += 1
            lower_touch_indices.append(i)

        # Original breakout logic
        if analysis_df['close'].iloc[i-1] <= upper[i-1] and analysis_df['close'].iloc[i] > upper[i-1]:
            breakout = i
            direction = 'upper'
        elif analysis_df['close'].iloc[i-1] >= lower[i-1] and analysis_df['close'].iloc[i] < lower[i-1]:
            breakout = i
            direction = 'lower'

        # Original breakout validation
        if breakout is not None:
            valid_breakout = True
            for j in range(breakout, min(breakout + 3, len(analysis_df))):
                if (direction == 'upper' and analysis_df['close'].iloc[j] <= upper[j]) or \
                   (direction == 'lower' and analysis_df['close'].iloc[j] >= lower[j]):
                    valid_breakout = False
                    break
            
            if not valid_breakout:
                if direction == 'upper':
                    extreme_price = max(analysis_df['high'].iloc[breakout:min(breakout + 3, len(analysis_df))])
                    new_upper_adjustment = extreme_price - upper[breakout]
                    upper += new_upper_adjustment
                    upper_full += new_upper_adjustment
                    full_df['upper'] = upper_full
                else:
                    extreme_price = min(analysis_df['low'].iloc[breakout:min(breakout + 3, len(analysis_df))])
                    new_lower_adjustment = extreme_price - lower[breakout]
                    lower += new_lower_adjustment
                    lower_full += new_lower_adjustment
                    full_df['lower'] = lower_full
                
                breakout = None
                upper_touch_count = 0
                lower_touch_count = 0
                
                for m in range(1, len(analysis_df)):
                    if analysis_df['high'].iloc[m] == upper[m]:
                        upper_touch_count += 1
                    if analysis_df['low'].iloc[m] == lower[m]:
                        lower_touch_count += 1
        
        # Original validation condition
        if (upper_touch_count >= 2 and lower_touch_count >= 1) or (upper_touch_count >= 1 and lower_touch_count >= 2):
            validated = True
            break
    
    # Check for touch imbalance and adjust boundaries if needed (exactly as in visuals.py)
    if not validated:
        if upper_touch_count >= 2 and lower_touch_count == 0:
            # Adjust lower boundary to be closer to trend line
            lower = trend_line - 2 * std_dev
            lower_full = trend_line_full - 2 * std_dev
            full_df['lower'] = lower_full
            
            # Re-count touches with new boundaries
            lower_touch_count = 0
            lower_touch_indices = []
            breakout = None
            for k in range(1, len(analysis_df)):
                recent_lower_touch = any((k - idx) <= 5 for idx in lower_touch_indices)
                if analysis_df['low'].iloc[k] < lower[k]:
                    extreme_price = analysis_df['low'].iloc[k]
                    new_lower_adjustment = extreme_price - lower[k]
                    lower += new_lower_adjustment
                    lower_full += new_lower_adjustment
                    full_df['lower'] = lower_full
                    
                if analysis_df['low'].iloc[k] == lower[k] and not recent_lower_touch:
                    lower_touch_count += 1
                    lower_touch_indices.append(k)
                
                if analysis_df['close'].iloc[k-1] <= upper[k-1] and analysis_df['close'].iloc[k] > upper[k-1]:
                    breakout = k
                    direction = 'upper'
                elif analysis_df['close'].iloc[k-1] >= lower[k-1] and analysis_df['close'].iloc[k] < lower[k-1]:
                    breakout = k
                    direction = 'lower'

                if breakout is not None:
                    valid_breakout = True
                    for j in range(breakout, min(breakout + 3, len(analysis_df))):
                        if (direction == 'upper' and analysis_df['close'].iloc[j] <= upper[j]) or \
                        (direction == 'lower' and analysis_df['close'].iloc[j] >= lower[j]):
                            valid_breakout = False
                            break
                    
                    if not valid_breakout:
                        if direction == 'upper':
                            extreme_price = max(analysis_df['high'].iloc[breakout:min(breakout + 3, len(analysis_df))])
                            new_upper_adjustment = extreme_price - upper[breakout]
                            upper += new_upper_adjustment
                            upper_full += new_upper_adjustment
                            full_df['upper'] = upper_full
                        else:
                            extreme_price = min(analysis_df['low'].iloc[breakout:min(breakout + 3, len(analysis_df))])
                            new_lower_adjustment = extreme_price - lower[breakout]
                            lower += new_lower_adjustment
                            lower_full += new_lower_adjustment
                            full_df['lower'] = lower_full
                        
                        breakout = None
                        upper_touch_count = 0
                        lower_touch_count = 0
                        
                        for m in range(1, len(analysis_df)):
                            if analysis_df['high'].iloc[m] == upper[m]:
                                upper_touch_count += 1
                            if analysis_df['low'].iloc[m] == lower[m]:
                                lower_touch_count += 1
            if (upper_touch_count >= 2 and lower_touch_count >= 1) or (upper_touch_count >= 1 and lower_touch_count >= 2):
                validated = True
                
        elif lower_touch_count >= 2 and upper_touch_count == 0:
            # Adjust upper boundary to be closer to trend line
            upper = trend_line + std_dev
            upper_full = trend_line_full + std_dev
            full_df['upper'] = upper_full
            
            # Re-count touches with new boundaries
            upper_touch_count = 0
            upper_touch_indices = []
            breakout = None
            for k in range(1, len(analysis_df)):
                recent_upper_touch = any((k - idx) <= 5 for idx in upper_touch_indices)
                if analysis_df['high'].iloc[k] > upper[k]:
                    extreme_price = analysis_df['high'].iloc[k]
                    new_upper_adjustment = extreme_price - upper[k]
                    upper += new_upper_adjustment
                    upper_full += new_upper_adjustment
                    full_df['upper'] = upper_full
                    
                if analysis_df['high'].iloc[k] == upper[k] and not recent_upper_touch:
                    upper_touch_count += 1
                    upper_touch_indices.append(k)
                
                if analysis_df['close'].iloc[k-1] <= upper[k-1] and analysis_df['close'].iloc[k] > upper[k-1]:
                    breakout = k
                    direction = 'upper'
                elif analysis_df['close'].iloc[k-1] >= lower[k-1] and analysis_df['close'].iloc[k] < lower[k-1]:
                    breakout = k
                    direction = 'lower'

                if breakout is not None:
                    valid_breakout = True
                    for j in range(breakout, min(breakout + 3, len(analysis_df))):
                        if (direction == 'upper' and analysis_df['close'].iloc[j] <= upper[j]) or \
                        (direction == 'lower' and analysis_df['close'].iloc[j] >= lower[j]):
                            valid_breakout = False
                            break
                    
                    if not valid_breakout:
                        if direction == 'upper':
                            extreme_price = max(analysis_df['high'].iloc[breakout:min(breakout + 3, len(analysis_df))])
                            new_upper_adjustment = extreme_price - upper[breakout]
                            upper += new_upper_adjustment
                            upper_full += new_upper_adjustment
                            full_df['upper'] = upper_full
                        else:
                            extreme_price = min(analysis_df['low'].iloc[breakout:min(breakout + 3, len(analysis_df))])
                            new_lower_adjustment = extreme_price - lower[breakout]
                            lower += new_lower_adjustment
                            lower_full += new_lower_adjustment
                            full_df['lower'] = lower_full
                        
                        breakout = None
                        upper_touch_count = 0
                        lower_touch_count = 0
                        
                        for m in range(1, len(analysis_df)):
                            if analysis_df['high'].iloc[m] == upper[m]:
                                upper_touch_count += 1
                            if analysis_df['low'].iloc[m] == lower[m]:
                                lower_touch_count += 1
            if (upper_touch_count >= 2 and lower_touch_count >= 1) or (upper_touch_count >= 1 and lower_touch_count >= 2):
                validated = True

    # Check A+ setup using supply/demand zones (exactly as in visuals.py)
    a_plus_setup = False
    if validated:
        trend_slope = full_df['trend'].iloc[-1] - full_df['trend'].iloc[0]
        a_plus_setup = check_a_plus_setup(symbol, full_df, trend_slope, timeframe, state, current_time)

    return validated, full_df, a_plus_setup

def update_channel_data(symbol, timeframe, state, current_idx, all_data, current_time):
    """
    Update channel data with new candle - EXACTLY as in visuals.py update_channel_data
    """
    key = (symbol, timeframe)
    if key not in state.active_channels:
        return False

    channel_data = state.active_channels[key]
    timeframe_val = channel_data["timeframe"]
    last_time = channel_data["last_time"]
    num_bars = channel_data["num_bars"]
    
    # Get new candles since last update
    df = all_data[symbol][timeframe].iloc[:current_idx+1].copy()
    
    if last_time is not None:
        new_data = df[df['time'] > last_time].copy()
    else:
        new_data = pd.DataFrame()
    
    if new_data.empty:
        return False

    # Add channel columns to new data
    for col in ['upper', 'lower', 'trend']:
        if col not in new_data.columns:
            new_data[col] = np.nan

    # Get existing df
    existing_df = channel_data["df"]
    
    # Calculate slope (price change per bar) - exactly as in visuals.py
    if len(existing_df) >= 3:
        trend_vector = (existing_df['trend'].iloc[-1] - existing_df['trend'].iloc[-3]) / 2
        upper_vector = (existing_df['upper'].iloc[-1] - existing_df['upper'].iloc[-3]) / 2
        lower_vector = (existing_df['lower'].iloc[-1] - existing_df['lower'].iloc[-3]) / 2
    else:
        trend_vector = 0
        upper_vector = 0
        lower_vector = 0

    # Extend new candles organically
    for i in range(len(new_data)):
        if key in state.levels:
            break
        bars_from_end = i + 1
        new_data.at[new_data.index[i], 'trend'] = existing_df['trend'].iloc[-2] + (trend_vector * bars_from_end) if len(existing_df) >= 2 else existing_df['trend'].iloc[-1]
        new_data.at[new_data.index[i], 'upper'] = existing_df['upper'].iloc[-2] + (upper_vector * bars_from_end) if len(existing_df) >= 2 else existing_df['upper'].iloc[-1]
        new_data.at[new_data.index[i], 'lower'] = existing_df['lower'].iloc[-2] + (lower_vector * bars_from_end) if len(existing_df) >= 2 else existing_df['lower'].iloc[-1]

    # Concatenate with existing data
    updated_df = pd.concat([existing_df, new_data], ignore_index=True)
    updated_df = updated_df.drop_duplicates(subset='time', keep='last').reset_index(drop=True)

    # Update the channel data
    state.active_channels[key]["df"] = updated_df
    state.active_channels[key]["last_time"] = updated_df['time'].iloc[-2] if len(updated_df) >= 2 else updated_df['time'].iloc[-1]

    # Check for breakout in the direction of trend (exactly as in visuals.py)
    if key not in state.levels:
        df_latest = state.active_channels[key]["df"]
        last_n = df_latest.iloc[-num_bars:] if len(df_latest) >= num_bars else df_latest
        upper_line = df_latest['upper'].iloc[-1]
        lower_line = df_latest['lower'].iloc[-1]
        last_trend = df_latest['trend']
        trend_slope = last_trend.iloc[-1] - last_trend.iloc[0]
        
        for i in range(len(last_n)):
            candle = last_n.iloc[i]
            broke_above = candle['high'] > upper_line
            broke_below = candle['low'] < lower_line

            # Apply symbol-specific filters exactly as in visuals.py
            if timeframe == mt5.TIMEFRAME_H1:
                if symbol in H1_B:
                    if (trend_slope > 0) or (trend_slope < 0 and broke_below):
                        del state.active_channels[key]
                        break
                elif symbol in H1_BS:
                    if (trend_slope > 0 and broke_above) or (trend_slope < 0 and broke_below):
                        del state.active_channels[key]
                        break
                elif symbol in H1_S:
                    if (trend_slope > 0 and broke_above) or (trend_slope < 0):
                        del state.active_channels[key]
                        break
            
            elif timeframe == mt5.TIMEFRAME_M15:
                if symbol in M15_B:
                    if (trend_slope > 0) or (trend_slope < 0 and broke_below):
                        del state.active_channels[key]
                        break
                elif symbol in M15_BS:
                    if (trend_slope > 0 and broke_above) or (trend_slope < 0 and broke_below):
                        del state.active_channels[key]
                        break
                elif symbol in M15_S:
                    if (trend_slope > 0 and broke_above) or (trend_slope < 0):
                        del state.active_channels[key]
                        break

            elif timeframe == mt5.TIMEFRAME_M5:
                if symbol in M5_B:
                    if (trend_slope > 0) or (trend_slope < 0 and broke_below):
                        del state.active_channels[key]
                        break
                elif symbol in M5_BS:
                    if (trend_slope > 0 and broke_above) or (trend_slope < 0 and broke_below):
                        del state.active_channels[key]
                        break
                elif symbol in M5_S:
                    if (trend_slope > 0 and broke_above) or (trend_slope < 0):
                        del state.active_channels[key]
                        break

    return True

def detect_break(df, symbol, timeframe, state):
    """
    Detect breakout from channel - EXACTLY as in visuals.py
    """
    key = (symbol, timeframe)
    if key not in state.active_channels:
        return
    
    channel_data = state.active_channels[key]
    data = channel_data["df"]
    
    # Use the most recent data
    if 'trend' not in data.columns or 'upper' not in data.columns or 'lower' not in data.columns:
        return
    
    breakout = None
    trend_slope = data['trend'].iloc[-1] - data['trend'].iloc[0]
    last_touch_found = False
    
    for i in range(1, len(data)):
        if data['close'].iloc[i-1] <= data['upper'].iloc[i-1] and data['close'].iloc[i] > data['upper'].iloc[i]:
            if trend_slope < 0:
                breakout = i
                state.active_channels[key]["breakout_idx"] = breakout
                # Find last touch before breakout
                for j in range(breakout - 10, 10, -1):
                    if j < 0 or j >= len(data):
                        continue
                    if data['high'].iloc[j] >= data['upper'].iloc[j]:
                        if data['close'].iloc[j] < data['open'].iloc[j] and data['open'].iloc[j] > data['upper'].iloc[breakout]:
                            state.active_channels[key]["last_touch_price"] = data['open'].iloc[j]
                            state.active_channels[key]["last_touch_idx"] = j
                            last_touch_found = True
                            break
                        elif data['close'].iloc[j] > data['open'].iloc[j] and data['close'].iloc[j] > data['upper'].iloc[breakout]:
                            state.active_channels[key]["last_touch_price"] = data['close'].iloc[j]
                            state.active_channels[key]["last_touch_idx"] = j
                            last_touch_found = True
                            break
                break

        elif data['close'].iloc[i-1] >= data['lower'].iloc[i-1] and data['close'].iloc[i] < data['lower'].iloc[i]:
            if trend_slope > 0:
                breakout = i
                state.active_channels[key]["breakout_idx"] = breakout
                # Find last touch before breakout
                for j in range(breakout - 10, 10, -1):
                    if j < 0 or j >= len(data):
                        continue
                    if data['low'].iloc[j] <= data['lower'].iloc[j]:
                        if data['close'].iloc[j] > data['open'].iloc[j] and data['open'].iloc[j] < data['lower'].iloc[breakout]:
                            state.active_channels[key]["last_touch_price"] = data['open'].iloc[j]
                            state.active_channels[key]["last_touch_idx"] = j
                            last_touch_found = True
                            break
                        elif data['close'].iloc[j] < data['open'].iloc[j] and data['close'].iloc[j] < data['lower'].iloc[breakout]:
                            state.active_channels[key]["last_touch_price"] = data['close'].iloc[j]
                            state.active_channels[key]["last_touch_idx"] = j
                            last_touch_found = True
                            break
                break
    
    if breakout is not None and not last_touch_found:
        if key in state.active_channels:
            del state.active_channels[key]
        if key in state.levels:
            del state.levels[key]

def find_valid_entry(df, breakout_idx, last_touch_idx, symbol, timeframe, state):
    """
    Find valid entry after breakout - EXACTLY as in visuals.py
    """
    if last_touch_idx is None or breakout_idx is None:
        return None
        
    key = (symbol, timeframe)
    if key not in state.active_channels:
        return None
        
    channel_data = state.active_channels[key]
    last_touch_price = channel_data.get("last_touch_price")
    if last_touch_price is None:
        return None
    
    entry_candle_idx = None
    count = 0
    
    for i in range(breakout_idx, len(df)):
        if df['open'].iloc[i] > df['upper'].iloc[i] or df['open'].iloc[i] < df['lower'].iloc[i]:
            count += 1
        if df['open'].iloc[i] > last_touch_price and df['high'].iloc[i] > df['upper'].iloc[i] and last_touch_price>df['upper'].iloc[i]:
            entry_candle_idx = i-1
            break
        elif df['open'].iloc[i] < last_touch_price and df['low'].iloc[i] < df['lower'].iloc[i] and last_touch_price<df['lower'].iloc[i]:
            entry_candle_idx = i-1
            break
        
    if count >= channel_data.get("num_bars", 50) and entry_candle_idx is None:
        if key in state.active_channels:
            del state.active_channels[key]
        if key in state.levels:
            del state.levels[key]
        return None
    
    if entry_candle_idx is None or entry_candle_idx < 0:
        return None
    
    last_trend = df["trend"]
    trend_slope = last_trend.iloc[-1] - last_trend.iloc[0]

    count = 0
    for j in range(entry_candle_idx + 1, min(entry_candle_idx + 6, len(df))):
        if j >= len(df):
            break
        if trend_slope < 0 and (df['close'].iloc[j] > df['close'].iloc[entry_candle_idx] and df['low'].iloc[j] > df['low'].iloc[entry_candle_idx]):
            count += 1
        elif trend_slope > 0 and (df['close'].iloc[j] < df['close'].iloc[entry_candle_idx] and df['high'].iloc[j] < df['high'].iloc[entry_candle_idx]):
            count += 1
        
        if count >= 3:
            if key in state.active_channels:
                del state.active_channels[key]
            if key in state.levels:
                del state.levels[key]
            return None
    
    return entry_candle_idx

def apply_fibonacci_levels(symbol, entry_idx, df, timeframe, state):
    """
    Calculate Fibonacci levels for trade - EXACTLY as in visuals.py
    """
    if entry_idx is None or entry_idx < 0 or entry_idx >= len(df):
        return None
        
    key = (symbol, timeframe)
    entry_price = df['close'].iloc[entry_idx]
    last_opposite_idx = None
    
    # Find the last opposite-colored candle before entry
    for i in range(entry_idx, 0, -1):
        if i-1 < 0:
            continue
        if (df['close'].iloc[entry_idx] > df['open'].iloc[entry_idx] and df['close'].iloc[i] < df['open'].iloc[i]) or \
           (df['close'].iloc[entry_idx] < df['open'].iloc[entry_idx] and df['close'].iloc[i] > df['open'].iloc[i]):
            last_opposite_idx = i
            break
    
    if last_opposite_idx is None:
        return None
    
    # Get the swing point (low for buys, high for sells)
    is_buy = df['close'].iloc[entry_idx] > df['open'].iloc[entry_idx]
    swing_point = df['low'].iloc[last_opposite_idx] if is_buy else df['high'].iloc[last_opposite_idx]
    
    # Calculate risk (distance from entry to swing point)
    risk = abs(entry_price - swing_point)
    
    if risk == 0:
        return None
    
    if is_buy:
        fib_levels = {
            "sl": swing_point - (0.9 * risk),
            "tp1": swing_point + (1.8 * risk),
            "tp2": swing_point + (2.8 * risk),
            "tp3": entry_price + (3.5 * risk),
            "sniper": swing_point + (0.3 * risk),
            "sl1": swing_point - (0.2 * risk),
            "direction": "BUY",
            "entry_time": df['time'].iloc[entry_idx],
            "engulf_count": 0,
            "last_engulf_time": None,
            "entry": entry_price
        }
    else:
        fib_levels = {
            "sl": swing_point + (0.9 * risk),
            "tp1": swing_point - (1.8 * risk),
            "tp2": swing_point - (2.8 * risk),
            "tp3": entry_price - (3.5 * risk),
            "sniper": swing_point - (0.3 * risk),
            "sl1": swing_point + (0.2 * risk),
            "direction": "SELL",
            "entry_time": df['time'].iloc[entry_idx],
            "engulf_count": 0,
            "last_engulf_time": None,
            "entry": entry_price
        }
    
    state.levels[key] = fib_levels
    return fib_levels

# ==================== A+ SETUP FUNCTION (EXACTLY AS IN VISUALS.PY) ====================

def check_a_plus_setup(symbol, df, trend_slope, current_timeframe, state, current_time):
    """
    Check if channel qualifies for A+ setup based on supply/demand zones
    EXACTLY as in visuals.py
    """
    key = (symbol, current_timeframe)
    
    # Check if zones need to be reloaded
    should_reload_zones(state, current_time)
    
    # Get or calculate supply/demand zones for this symbol
    if key not in state.supply_demand_zones:
        timeframe_map = {
            mt5.TIMEFRAME_M5: [mt5.TIMEFRAME_M15],
            mt5.TIMEFRAME_M15: [mt5.TIMEFRAME_H1],
            mt5.TIMEFRAME_H1: [mt5.TIMEFRAME_H4]
        }
        
        higher_timeframes = timeframe_map.get(current_timeframe, [mt5.TIMEFRAME_H1])
        
        state.supply_demand_zones[key] = {'supply_zones': [], 'demand_zones': []}
        
        for ht in higher_timeframes:
            try:
                # Need to get historical data up to current_time only
                # This is a limitation - we need to pass the actual data
                # For now, we'll skip A+ setup in backtest or implement properly
                pass
            except Exception as e:
                continue
    
    if key not in state.supply_demand_zones:
        return False
        
    zones = state.supply_demand_zones[key]
    
    # For downward channel (negative slope), check demand zones (support)
    if trend_slope < 0:
        for zone in zones.get('demand_zones', []):
            zone_price = zone['price']
            # Check if any candle in the dataframe touches this demand zone
            for i in range(len(df)):
                candle_low = df['low'].iloc[i]
                candle_high = df['high'].iloc[i]
                
                # Check if zone price falls within candle's range
                if candle_low <= zone_price <= candle_high:
                    return True
        
        # Also check broken supply zones (now acting as support)
        for zone in zones.get('supply_zones', []):
            if zone.get('is_broken', False):
                zone_price = zone['price']
                for i in range(len(df)):
                    candle_low = df['low'].iloc[i]
                    candle_high = df['high'].iloc[i]
                    
                    if candle_low <= zone_price <= candle_high:
                        return True
    
    # For upward channel (positive slope), check supply zones (resistance)
    elif trend_slope > 0:
        for zone in zones.get('supply_zones', []):
            zone_price = zone['price']
            # Check if any candle in the dataframe touches this supply zone
            for i in range(len(df)):
                candle_low = df['low'].iloc[i]
                candle_high = df['high'].iloc[i]
                
                # Check if zone price falls within candle's range
                if candle_low <= zone_price <= candle_high:
                    return True
        
        # Also check broken demand zones (now acting as resistance)
        for zone in zones.get('demand_zones', []):
            if zone.get('is_broken', False):
                zone_price = zone['price']
                for i in range(len(df)):
                    candle_low = df['low'].iloc[i]
                    candle_high = df['high'].iloc[i]
                    
                    if candle_low <= zone_price <= candle_high:
                        return True
    
    return False

def preload_supply_demand_zones(state, historical_data, current_time):
    """
    Preload supply/demand zones for all active symbols using appropriate higher timeframes
    EXACTLY as in visuals.py
    """
    # Get all symbols from active channels
    all_symbols = set()
    for (symbol, _) in state.active_channels.keys():
        all_symbols.add(symbol)
    
    # Define which higher timeframe to use for each trading timeframe
    timeframe_map = {
        mt5.TIMEFRAME_M5: [mt5.TIMEFRAME_M15],
        mt5.TIMEFRAME_M15: [mt5.TIMEFRAME_H1],
        mt5.TIMEFRAME_H1: [mt5.TIMEFRAME_H4]
    }
    
    # Trading timeframes we actually use
    trading_timeframes = [mt5.TIMEFRAME_M5, mt5.TIMEFRAME_M15, mt5.TIMEFRAME_H1]
    
    for symbol in all_symbols:
        for trading_tf in trading_timeframes:
            key = (symbol, trading_tf)
            
            # Initialize zones for this symbol/trading timeframe pair
            if key not in state.supply_demand_zones:
                state.supply_demand_zones[key] = {
                    'supply_zones': [],
                    'demand_zones': []
                }
            
            # Get the higher timeframe(s) to analyze
            higher_timeframes = timeframe_map.get(trading_tf, [mt5.TIMEFRAME_H1])
            
            for ht in higher_timeframes:
                try:
                    # Get data up to current_time only
                    if symbol in historical_data and ht in historical_data[symbol]:
                        df = historical_data[symbol][ht]
                        df_up_to = df[df['time'] <= current_time].copy()
                        
                        if df_up_to.empty:
                            continue
                        
                        # Analyze zones for this higher timeframe
                        analyzer = SupplyDemandAnalyzer(df_up_to, lookback_period=15, min_touch_points=2)
                        ht_supply_zones, ht_demand_zones = analyzer.identify_zones()
                        
                        # Add zones to the appropriate key
                        state.supply_demand_zones[key]['supply_zones'].extend(ht_supply_zones)
                        state.supply_demand_zones[key]['demand_zones'].extend(ht_demand_zones)
                        
                except Exception as e:
                    continue
    
            # Update last loaded time for this key
            state.zone_last_loaded[key] = current_time

def should_reload_zones(state, current_time):
    """
    Check if zones should be reloaded based on the timeframe-specific schedule
    EXACTLY as in visuals.py
    """
    timeframe_map = {
        mt5.TIMEFRAME_M5: [mt5.TIMEFRAME_M15],
        mt5.TIMEFRAME_M15: [mt5.TIMEFRAME_H1],
        mt5.TIMEFRAME_H1: [mt5.TIMEFRAME_H4]
    }
    
    # Clear to_be_reloaded list before checking
    state.to_be_reloaded = []
    
    # Check all zone_last_loaded keys
    for key in list(state.zone_last_loaded.keys()):
        symbol, timeframe = key
        time_since_last_load = current_time - state.zone_last_loaded[key]
        
        # Get reload period for this timeframe
        reload_period = ZONE_RELOAD_CONFIG.get(timeframe, timedelta(days=5))
        
        if time_since_last_load >= reload_period:
            state.to_be_reloaded.append(key)
            if key in state.supply_demand_zones:
                del state.supply_demand_zones[key]
    
    # Return whether any zones need reloading
    return len(state.to_be_reloaded) > 0

# ==================== BACKTEST TRADE FUNCTIONS (EXACTLY AS IN VISUALS.PY) ====================

def pending(symbol, direction, entry_price, sl, tp, sniper, timeframe, state, candle_time):
    """
    Simulate pending order placement in backtest - EXACTLY as in visuals.py pending()
    """
    if abs(sl - sniper) >= abs(tp - sniper):
        return
    
    key = (symbol, timeframe)
    
    # Check if already have position/order
    if any(trade['symbol'] == symbol and trade['timeframe'] == timeframe and trade['status'] in ['pending', 'open'] 
           for trade in state.trade_history):
        return
    
    # Calculate position size
    pos_size = lot_size(symbol)
    
    state.total_signals += 1
    
    trade = {
        'symbol': symbol,
        'timeframe': timeframe,
        'direction': direction,
        'entry_price': sniper,
        'sl': sl,
        'tp1': state.levels[key]["tp1"] if key in state.levels else None,
        'tp2': state.levels[key]["tp2"] if key in state.levels else None,
        'tp3': tp,
        'sniper': sniper,
        'size': pos_size,
        'entry_time': candle_time,
        'status': 'pending',
        'type': 'pending',
        'exit_time': None,
        'exit_price': None,
        'pnl': 0,
        'pnl_pct': 0,
        'ticket': len(state.trade_history) + 1,
        'signal_time': candle_time
    }
    
    state.trade_history.append(trade)
    state.levels[key]['is_pending'] = True
    state.levels[key]['pending_order_ticket'] = trade['ticket']
    state.levels[key]['entry'] = entry_price

def place_trade(symbol, direction, entry_price, sl1, tp, timeframe, state, candle_time):
    """
    Simulate market order placement in backtest - EXACTLY as in visuals.py place_trade()
    """
    if abs(sl1 - entry_price) >= abs(tp - entry_price):
        return
    
    key = (symbol, timeframe)
    
    # Check if already have position/order
    if any(trade['symbol'] == symbol and trade['timeframe'] == timeframe and trade['status'] in ['open'] 
           for trade in state.trade_history):
        return
    
    # Calculate position size
    pos_size = lot_size(symbol)
    
    state.total_signals += 1
    state.executed_trades += 1
    
    trade = {
        'symbol': symbol,
        'timeframe': timeframe,
        'direction': direction,
        'entry_price': entry_price,
        'sl': sl1,
        'tp1': state.levels[key]["tp1"] if key in state.levels else None,
        'tp2': state.levels[key]["tp2"] if key in state.levels else None,
        'tp3': tp,
        'size': pos_size,
        'entry_time': candle_time,
        'status': 'open',
        'type': 'market',
        'exit_time': None,
        'exit_price': None,
        'pnl': 0,
        'pnl_pct': 0,
        'ticket': len(state.trade_history) + 1,
        'signal_time': candle_time
    }
    
    state.trade_history.append(trade)
    state.active_trades[trade['ticket']] = {'symbol': symbol, 'timeframe': timeframe}
    state.levels[key]['entry'] = entry_price

def modify_trade_to_breakeven(symbol, order_ticket, entry_price, state, current_time):
    """
    Simulate moving SL to breakeven - EXACTLY as in visuals.py modify_trade_to_breakeven()
    """
    # Find the trade
    for trade in state.trade_history:
        if trade.get('ticket') == order_ticket and trade['status'] == 'open':
            if trade['sl'] == entry_price:
                return
            trade['sl'] = entry_price
            state.breakeven_trades[order_ticket] = {'symbol': symbol, 'timeframe': trade['timeframe']}
            break

def close_pending(symbol, state, current_time, all_data):
    """
    Check and close pending orders if TP2 (the old TP1) is hit - EXACTLY as in visuals.py close_pending()
    """
    key = None
    for k in list(state.levels.keys()):
        if k[0] == symbol:
            key = k
            break
    
    if key is None:
        return
    
    timeframe = key[1]
    
    if key not in state.levels or not state.levels[key].get('is_pending', False):
        return
    
    L = state.levels[key]
    tp2 = L["tp2"]
    direction = L["direction"]
    entry_time = L["entry_time"]
    
    # Get data since entry
    df = all_data[symbol][timeframe]
    df_after = df[df['time'] > entry_time]
    
    if len(df_after) == 0:
        return
    
    crossed_tp2 = False
    tp2_hit_time = None
    if direction == "BUY":
        tp2_hits = df_after[df_after['high'] >= tp2]
        if len(tp2_hits) > 0:
            crossed_tp2 = True
            tp2_hit_time = tp2_hits.iloc[0]['time']
    elif direction == "SELL":
        tp2_hits = df_after[df_after['low'] <= tp2]
        if len(tp2_hits) > 0:
            crossed_tp2 = True
            tp2_hit_time = tp2_hits.iloc[0]['time']
    
    if crossed_tp2:
        # Find the pending order
        for trade in state.trade_history:
            if trade['symbol'] == symbol and trade['timeframe'] == timeframe and trade['status'] == 'pending':
                trade['status'] = 'cancelled'
                trade['exit_time'] = tp2_hit_time
                trade['exit_reason'] = 'TP2_hit_before_entry'
                
                # Track as missed trade
                missed_trade = trade.copy()
                missed_trade['tp2_hit_time'] = tp2_hit_time
                missed_trade['tp2_price'] = tp2
                state.missed_trades.append(missed_trade)
                state.missed_trades_count += 1
                
                break
        
        if key in state.active_channels:
            del state.active_channels[key]
        if key in state.levels:
            del state.levels[key]

def check_tp1_and_manage_trades(symbol, tp1_value, timeframe, state, current_time, all_data):
    """
    Check if TP1 (new, 1.8x risk) is hit and manage position - EXACTLY as in visuals.py
    check_tp1_and_manage_trades() (simplified for backtest: flags the event and applies
    breakeven rather than simulating the actual ~1/3 partial close).
    """
    if tp1_value is None:
        return
    
    if isinstance(tp1_value, str):
        if tp1_value == '':
            return
        try:
            Tp1 = float(tp1_value)
        except:
            return
    else:
        Tp1 = tp1_value
    
    # Find open trades for this symbol/timeframe
    for trade in state.trade_history:
        if trade['symbol'] == symbol and trade['timeframe'] == timeframe and trade['status'] == 'open':
            entry_price = trade['entry_price']
            direction = trade['direction']
            entry_time = trade['entry_time']
            
            # Get data since entry
            df = all_data[symbol][timeframe]
            df_after = df[df['time'] > entry_time]
            
            if len(df_after) == 0:
                continue
            
            crossed_tp1 = False
            if direction == "BUY":
                if (df_after['high'] >= Tp1).any():
                    crossed_tp1 = True
            elif direction == "SELL":
                if (df_after['low'] <= Tp1).any():
                    crossed_tp1 = True
            
            if crossed_tp1:
                # Apply breakeven
                modify_trade_to_breakeven(symbol, trade['ticket'], entry_price, state, current_time)
                
                # Cut-to-~2/3 logic (simplified for backtest: just flags the event)
                if 'tp1_hit' not in trade:
                    trade['tp1_hit'] = True
                    trade['tp1_hit_time'] = current_time

def check_tp2_and_manage_trades(symbol, tp2_value, timeframe, state, current_time, all_data):
    """
    Check if TP2 (the old TP1, 2.8x risk) is hit and manage position - simplified
    backtest companion to check_tp1_and_manage_trades(). Breakeven should already be
    applied from TP1; this checks defensively rather than assuming it.
    """
    if tp2_value is None:
        return
    
    if isinstance(tp2_value, str):
        if tp2_value == '':
            return
        try:
            Tp2 = float(tp2_value)
        except:
            return
    else:
        Tp2 = tp2_value
    
    for trade in state.trade_history:
        if trade['symbol'] == symbol and trade['timeframe'] == timeframe and trade['status'] == 'open':
            entry_price = trade['entry_price']
            direction = trade['direction']
            entry_time = trade['entry_time']
            
            df = all_data[symbol][timeframe]
            df_after = df[df['time'] > entry_time]
            
            if len(df_after) == 0:
                continue
            
            crossed_tp2 = False
            if direction == "BUY":
                if (df_after['high'] >= Tp2).any():
                    crossed_tp2 = True
            elif direction == "SELL":
                if (df_after['low'] <= Tp2).any():
                    crossed_tp2 = True
            
            if crossed_tp2:
                # Defensive breakeven check - normally already applied at TP1
                modify_trade_to_breakeven(symbol, trade['ticket'], entry_price, state, current_time)
                
                if 'tp2_hit' not in trade:
                    trade['tp2_hit'] = True
                    trade['tp2_hit_time'] = current_time

def del_completed(state, current_time, all_data):
    """
    Check for trades hitting SL or TP3 - EXACTLY as in visuals.py del_completed()
    """
    for key in list(state.levels.keys()):
        symbol, timeframe = key
        L = state.levels[key]
        direction = L.get("direction")
        entry_time = L["entry_time"]
        sl = L["sl"]
        sl1 = L["sl1"]
        tp3 = L["tp3"]
        
        if not direction:
            continue
        
        # Get data since entry
        df = all_data[symbol][timeframe]
        df_after = df[df['time'] > entry_time].reset_index(drop=True)
        
        if len(df_after) == 0:
            continue
        
        crossed_tp3 = False
        crossed_sl1 = False
        crossed_sl = False
        
        if direction == "BUY":
            crossed_tp3 = (df_after['high'] >= tp3).any()
            crossed_sl1 = (df_after['low'] <= sl1).any()
            crossed_sl = (df_after['low'] <= sl).any()
        elif direction == "SELL":
            crossed_tp3 = (df_after['low'] <= tp3).any()
            crossed_sl1 = (df_after['high'] >= sl1).any()
            crossed_sl = (df_after['high'] >= sl).any()
        
        # Find the trade
        trade = None
        for t in state.trade_history:
            if t['symbol'] == symbol and t['timeframe'] == timeframe and t['status'] == 'open':
                trade = t
                break
        
        if not trade:
            continue
        
        # Apply timeframe-specific SL logic (exactly as in visuals.py)
        if timeframe == mt5.TIMEFRAME_M5:
            if symbol in M5_pen:
                if (direction == "BUY" and crossed_sl) or (direction == "SELL" and crossed_sl):
                    # Hit SL
                    exit_idx = None
                    if direction == "BUY":
                        sl_hits = df_after[df_after['low'] <= sl].index
                        if len(sl_hits) > 0:
                            exit_idx = sl_hits[0]
                    else:
                        sl_hits = df_after[df_after['high'] >= sl].index
                        if len(sl_hits) > 0:
                            exit_idx = sl_hits[0]
                    
                    if exit_idx is not None:
                        exit_price = df_after.iloc[exit_idx]['close']
                        exit_time = df_after.iloc[exit_idx]['time']
                        
                        pnl = (exit_price - trade['entry_price']) * trade['size'] if direction == "BUY" else (trade['entry_price'] - exit_price) * trade['size']
                        pnl_pct = pnl / (trade['entry_price'] * trade['size']) * 100
                        
                        trade['status'] = 'closed'
                        trade['exit_time'] = exit_time
                        trade['exit_price'] = exit_price
                        trade['pnl'] = pnl
                        trade['pnl_pct'] = pnl_pct
                        trade['exit_reason'] = 'SL'
                        
                        state.current_capital += pnl
                        state.equity_curve.append({'time': exit_time, 'equity': state.current_capital})
                        
                        if key in state.active_channels:
                            del state.active_channels[key]
                        if key in state.levels:
                            del state.levels[key]
                        if trade['ticket'] in state.active_trades:
                            del state.active_trades[trade['ticket']]
                        
                        start_cooldown(symbol, timeframe, state, current_time)
                        continue
                        
            elif symbol in M5_pl:
                if (direction == "BUY" and crossed_sl1) or (direction == "SELL" and crossed_sl1):
                    # Hit SL
                    exit_idx = None
                    if direction == "BUY":
                        sl_hits = df_after[df_after['low'] <= sl1].index
                        if len(sl_hits) > 0:
                            exit_idx = sl_hits[0]
                    else:
                        sl_hits = df_after[df_after['high'] >= sl1].index
                        if len(sl_hits) > 0:
                            exit_idx = sl_hits[0]
                    
                    if exit_idx is not None:
                        exit_price = df_after.iloc[exit_idx]['close']
                        exit_time = df_after.iloc[exit_idx]['time']
                        
                        pnl = (exit_price - trade['entry_price']) * trade['size'] if direction == "BUY" else (trade['entry_price'] - exit_price) * trade['size']
                        pnl_pct = pnl / (trade['entry_price'] * trade['size']) * 100
                        
                        trade['status'] = 'closed'
                        trade['exit_time'] = exit_time
                        trade['exit_price'] = exit_price
                        trade['pnl'] = pnl
                        trade['pnl_pct'] = pnl_pct
                        trade['exit_reason'] = 'SL'
                        
                        state.current_capital += pnl
                        state.equity_curve.append({'time': exit_time, 'equity': state.current_capital})
                        
                        if key in state.active_channels:
                            del state.active_channels[key]
                        if key in state.levels:
                            del state.levels[key]
                        if trade['ticket'] in state.active_trades:
                            del state.active_trades[trade['ticket']]
                        
                        start_cooldown(symbol, timeframe, state, current_time)
                        continue
        
        elif timeframe == mt5.TIMEFRAME_M15:
            if symbol in M15_pen:
                if (direction == "BUY" and crossed_sl) or (direction == "SELL" and crossed_sl):
                    # Hit SL
                    exit_idx = None
                    if direction == "BUY":
                        sl_hits = df_after[df_after['low'] <= sl].index
                        if len(sl_hits) > 0:
                            exit_idx = sl_hits[0]
                    else:
                        sl_hits = df_after[df_after['high'] >= sl].index
                        if len(sl_hits) > 0:
                            exit_idx = sl_hits[0]
                    
                    if exit_idx is not None:
                        exit_price = df_after.iloc[exit_idx]['close']
                        exit_time = df_after.iloc[exit_idx]['time']
                        
                        pnl = (exit_price - trade['entry_price']) * trade['size'] if direction == "BUY" else (trade['entry_price'] - exit_price) * trade['size']
                        pnl_pct = pnl / (trade['entry_price'] * trade['size']) * 100
                        
                        trade['status'] = 'closed'
                        trade['exit_time'] = exit_time
                        trade['exit_price'] = exit_price
                        trade['pnl'] = pnl
                        trade['pnl_pct'] = pnl_pct
                        trade['exit_reason'] = 'SL'
                        
                        state.current_capital += pnl
                        state.equity_curve.append({'time': exit_time, 'equity': state.current_capital})
                        
                        if key in state.active_channels:
                            del state.active_channels[key]
                        if key in state.levels:
                            del state.levels[key]
                        if trade['ticket'] in state.active_trades:
                            del state.active_trades[trade['ticket']]
                        
                        start_cooldown(symbol, timeframe, state, current_time)
                        continue
                        
            elif symbol in M15_pl:
                if (direction == "BUY" and crossed_sl1) or (direction == "SELL" and crossed_sl1):
                    # Hit SL
                    exit_idx = None
                    if direction == "BUY":
                        sl_hits = df_after[df_after['low'] <= sl1].index
                        if len(sl_hits) > 0:
                            exit_idx = sl_hits[0]
                    else:
                        sl_hits = df_after[df_after['high'] >= sl1].index
                        if len(sl_hits) > 0:
                            exit_idx = sl_hits[0]
                    
                    if exit_idx is not None:
                        exit_price = df_after.iloc[exit_idx]['close']
                        exit_time = df_after.iloc[exit_idx]['time']
                        
                        pnl = (exit_price - trade['entry_price']) * trade['size'] if direction == "BUY" else (trade['entry_price'] - exit_price) * trade['size']
                        pnl_pct = pnl / (trade['entry_price'] * trade['size']) * 100
                        
                        trade['status'] = 'closed'
                        trade['exit_time'] = exit_time
                        trade['exit_price'] = exit_price
                        trade['pnl'] = pnl
                        trade['pnl_pct'] = pnl_pct
                        trade['exit_reason'] = 'SL'
                        
                        state.current_capital += pnl
                        state.equity_curve.append({'time': exit_time, 'equity': state.current_capital})
                        
                        if key in state.active_channels:
                            del state.active_channels[key]
                        if key in state.levels:
                            del state.levels[key]
                        if trade['ticket'] in state.active_trades:
                            del state.active_trades[trade['ticket']]
                        
                        start_cooldown(symbol, timeframe, state, current_time)
                        continue
        
        elif timeframe == mt5.TIMEFRAME_H1:
            if symbol in H1_pen:
                if (direction == "BUY" and crossed_sl) or (direction == "SELL" and crossed_sl):
                    # Hit SL
                    exit_idx = None
                    if direction == "BUY":
                        sl_hits = df_after[df_after['low'] <= sl].index
                        if len(sl_hits) > 0:
                            exit_idx = sl_hits[0]
                    else:
                        sl_hits = df_after[df_after['high'] >= sl].index
                        if len(sl_hits) > 0:
                            exit_idx = sl_hits[0]
                    
                    if exit_idx is not None:
                        exit_price = df_after.iloc[exit_idx]['close']
                        exit_time = df_after.iloc[exit_idx]['time']
                        
                        pnl = (exit_price - trade['entry_price']) * trade['size'] if direction == "BUY" else (trade['entry_price'] - exit_price) * trade['size']
                        pnl_pct = pnl / (trade['entry_price'] * trade['size']) * 100
                        
                        trade['status'] = 'closed'
                        trade['exit_time'] = exit_time
                        trade['exit_price'] = exit_price
                        trade['pnl'] = pnl
                        trade['pnl_pct'] = pnl_pct
                        trade['exit_reason'] = 'SL'
                        
                        state.current_capital += pnl
                        state.equity_curve.append({'time': exit_time, 'equity': state.current_capital})
                        
                        if key in state.active_channels:
                            del state.active_channels[key]
                        if key in state.levels:
                            del state.levels[key]
                        if trade['ticket'] in state.active_trades:
                            del state.active_trades[trade['ticket']]
                        
                        start_cooldown(symbol, timeframe, state, current_time)
                        continue
                        
            elif symbol in H1_pl:
                if (direction == "BUY" and crossed_sl1) or (direction == "SELL" and crossed_sl1):
                    # Hit SL
                    exit_idx = None
                    if direction == "BUY":
                        sl_hits = df_after[df_after['low'] <= sl1].index
                        if len(sl_hits) > 0:
                            exit_idx = sl_hits[0]
                    else:
                        sl_hits = df_after[df_after['high'] >= sl1].index
                        if len(sl_hits) > 0:
                            exit_idx = sl_hits[0]
                    
                    if exit_idx is not None:
                        exit_price = df_after.iloc[exit_idx]['close']
                        exit_time = df_after.iloc[exit_idx]['time']
                        
                        pnl = (exit_price - trade['entry_price']) * trade['size'] if direction == "BUY" else (trade['entry_price'] - exit_price) * trade['size']
                        pnl_pct = pnl / (trade['entry_price'] * trade['size']) * 100
                        
                        trade['status'] = 'closed'
                        trade['exit_time'] = exit_time
                        trade['exit_price'] = exit_price
                        trade['pnl'] = pnl
                        trade['pnl_pct'] = pnl_pct
                        trade['exit_reason'] = 'SL'
                        
                        state.current_capital += pnl
                        state.equity_curve.append({'time': exit_time, 'equity': state.current_capital})
                        
                        if key in state.active_channels:
                            del state.active_channels[key]
                        if key in state.levels:
                            del state.levels[key]
                        if trade['ticket'] in state.active_trades:
                            del state.active_trades[trade['ticket']]
                        
                        start_cooldown(symbol, timeframe, state, current_time)
                        continue
        
        # Check TP3 (final target)
        if (direction == "BUY" and crossed_tp3) or (direction == "SELL" and crossed_tp3):
            # Hit TP3
            exit_idx = None
            if direction == "BUY":
                tp3_hits = df_after[df_after['high'] >= tp3].index
                if len(tp3_hits) > 0:
                    exit_idx = tp3_hits[0]
            else:
                tp3_hits = df_after[df_after['low'] <= tp3].index
                if len(tp3_hits) > 0:
                    exit_idx = tp3_hits[0]
            
            if exit_idx is not None:
                exit_price = df_after.iloc[exit_idx]['close']
                exit_time = df_after.iloc[exit_idx]['time']
                
                pnl = (exit_price - trade['entry_price']) * trade['size'] if direction == "BUY" else (trade['entry_price'] - exit_price) * trade['size']
                pnl_pct = pnl / (trade['entry_price'] * trade['size']) * 100
                
                trade['status'] = 'closed'
                trade['exit_time'] = exit_time
                trade['exit_price'] = exit_price
                trade['pnl'] = pnl
                trade['pnl_pct'] = pnl_pct
                trade['exit_reason'] = 'TP3'
                
                state.current_capital += pnl
                state.equity_curve.append({'time': exit_time, 'equity': state.current_capital})
                
                if key in state.active_channels:
                    del state.active_channels[key]
                if key in state.levels:
                    del state.levels[key]
                if trade['ticket'] in state.active_trades:
                    del state.active_trades[trade['ticket']]

def update_pending_order_status(state, current_time, all_data):
    """
    Update status of pending orders (check if triggered) - EXACTLY as in visuals.py update_pending_order_status()
    """
    for key in list(state.levels.keys()):
        if state.levels[key].get('is_pending', False):
            symbol, timeframe = key
            order_ticket = state.levels[key].get('pending_order_ticket')
            if not order_ticket:
                continue
            
            # Find the pending order
            pending_order = None
            for trade in state.trade_history:
                if trade.get('ticket') == order_ticket and trade['status'] == 'pending':
                    pending_order = trade
                    break
            
            if not pending_order:
                continue
            
            # Check if price has reached entry
            df = all_data[symbol][timeframe]
            entry_time = state.levels[key]['entry_time']
            df_after = df[df['time'] > entry_time]
            
            if len(df_after) == 0:
                continue
            
            triggered = False
            trigger_time = None
            trigger_price = None
            
            if pending_order['direction'] == "BUY":
                buy_triggers = df_after[df_after['low'] <= pending_order['entry_price']]
                if len(buy_triggers) > 0:
                    triggered = True
                    trigger_idx = buy_triggers.index[0]
                    trigger_time = buy_triggers.iloc[0]['time']
                    trigger_price = pending_order['entry_price']
            else:  # SELL
                sell_triggers = df_after[df_after['high'] >= pending_order['entry_price']]
                if len(sell_triggers) > 0:
                    triggered = True
                    trigger_idx = sell_triggers.index[0]
                    trigger_time = sell_triggers.iloc[0]['time']
                    trigger_price = pending_order['entry_price']
            
            if triggered:
                # Convert pending to open
                pending_order['status'] = 'open'
                pending_order['entry_time'] = trigger_time
                pending_order['entry_price'] = trigger_price
                state.active_trades[pending_order['ticket']] = {'symbol': symbol, 'timeframe': timeframe}
                state.levels[key]['is_pending'] = False
                state.levels[key]['pending_order_ticket'] = None
                state.levels[key]['entry_time'] = trigger_time
                state.levels[key]['entry'] = trigger_price
                
                state.executed_trades += 1

def detect_opposite_engulfing(df, direction, symbol, timeframe, state):
    """
    Detect opposite engulfing pattern - EXACTLY as in visuals.py detect_opposite_engulfing()
    """
    entry_price = None
    
    # Find the trade
    for trade in state.trade_history:
        if trade['symbol'] == symbol and trade['timeframe'] == timeframe and trade['status'] == 'open':
            entry_price = trade['entry_price']
            break
    
    if entry_price is None:
        return None
    
    for i in range(4, len(df) - 1):  # Need confirmation candle
        if direction == "BUY":  # Bearish engulfing after 3 bulls
            bulls = all(df['close'].iloc[j] > df['open'].iloc[j] for j in range(i-3, i))
            if not bulls: continue
            # Bearish engulfing
            if df['close'].iloc[i] >= df['open'].iloc[i]: continue
            if df['open'].iloc[i] <= df['close'].iloc[i-1]: continue
            if df['close'].iloc[i] >= df['open'].iloc[i-1]: continue
            # Check if engulfing candle's open is higher than entry price
            if df['open'].iloc[i] <= entry_price: continue
            if max(df['high'].iloc[i-3:i]) <= entry_price: continue
            # Confirmed by next candle closing lower
            if df['close'].iloc[i+1] >= df['close'].iloc[i]: continue
            return i
        elif direction == "SELL":  # Bullish engulfing after 3 bears
            bears = all(df['close'].iloc[j] < df['open'].iloc[j] for j in range(i-3, i))
            if not bears: continue
            # Bullish engulfing
            if df['close'].iloc[i] <= df['open'].iloc[i]: continue
            if df['open'].iloc[i] >= df['close'].iloc[i-1]: continue
            if df['close'].iloc[i] <= df['open'].iloc[i-1]: continue
            # Check if engulfing candle's open is lower than entry price
            if df['open'].iloc[i] >= entry_price: continue
            if min(df['low'].iloc[i-3:i]) >= entry_price: continue
            # Confirmed by next candle closing higher
            if df['close'].iloc[i+1] <= df['close'].iloc[i]: continue
            return i
    return None

def handle_engulfing_patterns(state, current_time, all_data):
    """
    Handle engulfing patterns for trade management - EXACTLY as in visuals.py handle_engulfing_patterns()
    """
    for key in list(state.levels.keys()):
        symbol, timeframe = key
        L = state.levels[key]
        if 'entry_time' not in L:
            continue
        entry_time = L['entry_time']
        if L.get('is_pending', False):
            continue
        
        df = all_data[symbol][timeframe]
        recent = df[df['time'] > entry_time].reset_index(drop=True)
        if len(recent) < 5:
            continue
            
        eng_i = detect_opposite_engulfing(recent, L['direction'], symbol, timeframe, state)
        if eng_i is not None:
            eng_time = recent['time'].iloc[eng_i]
            if 'last_engulf_time' not in L or L['last_engulf_time'] is None or eng_time > L['last_engulf_time']:
                L['last_engulf_time'] = eng_time
                L['engulf_count'] += 1
                
                # Find the trade
                trade = None
                for t in state.trade_history:
                    if t['symbol'] == symbol and t['timeframe'] == timeframe and t['status'] == 'open':
                        trade = t
                        break
                
                if not trade:
                    continue
                
                count = L['engulf_count']
                if count == 1:
                    # Move to breakeven
                    modify_trade_to_breakeven(symbol, trade['ticket'], trade['entry_price'], state, current_time)
                elif count >= 2:
                    # Close half (simplified)
                    if 'half_closed' not in trade:
                        trade['half_closed'] = True
                    else:
                        # Close full position
                        current_price = recent.iloc[-1]['close']
                        pnl = (current_price - trade['entry_price']) * trade['size'] if L['direction'] == "BUY" else (trade['entry_price'] - current_price) * trade['size']
                        
                        trade['status'] = 'closed'
                        trade['exit_time'] = current_time
                        trade['exit_price'] = current_price
                        trade['pnl'] = pnl
                        trade['exit_reason'] = 'engulfing'
                        
                        state.current_capital += pnl
                        state.equity_curve.append({'time': current_time, 'equity': state.current_capital})
                        
                        if key in state.active_channels:
                            del state.active_channels[key]
                        if key in state.levels:
                            del state.levels[key]
                        if trade['ticket'] in state.active_trades:
                            del state.active_trades[trade['ticket']]

def check_conflicting_slopes(state):
    """
    Check for conflicting slopes across timeframes - EXACTLY as in visuals.py check_conflicting_slopes()
    """
    timeframe_combinations = [
        (mt5.TIMEFRAME_M5, mt5.TIMEFRAME_M15),
        (mt5.TIMEFRAME_M5, mt5.TIMEFRAME_H1),
        (mt5.TIMEFRAME_M15, mt5.TIMEFRAME_H1)
    ]
    
    for tf1, tf2 in timeframe_combinations:
        symbols_tf1 = {symbol for symbol, timeframe in state.active_channels.keys() if timeframe == tf1}
        symbols_tf2 = {symbol for symbol, timeframe in state.active_channels.keys() if timeframe == tf2}
        overlaps = symbols_tf1 & symbols_tf2
        
        for symbol in overlaps:
            key1 = (symbol, tf1)
            key2 = (symbol, tf2)
            
            if key1 in state.active_channels and key2 in state.active_channels:
                df1 = state.active_channels[key1]['df']
                df2 = state.active_channels[key2]['df']
                slope1 = df1['trend'].iloc[-1] - df1['trend'].iloc[0]
                slope2 = df2['trend'].iloc[-1] - df2['trend'].iloc[0]
                
                if (slope1 > 0 and slope2 < 0) or (slope1 < 0 and slope2 > 0):
                    if tf1 < tf2:
                        del state.active_channels[key1]
                        if key1 in state.levels:
                            del state.levels[key1]
                    else:
                        del state.active_channels[key2]
                        if key2 in state.levels:
                            del state.levels[key2]

def check_conflicting_trades(state):
    """
    Remove channels that conflict with existing trades - EXACTLY as in visuals.py check_conflicting_trades()
    """
    # Get open trades
    open_trades = [t for t in state.trade_history if t['status'] == 'open']
    
    for trade in open_trades:
        symbol = trade['symbol']
        trade_direction = trade['direction']
        
        for key in list(state.active_channels.keys()):
            channel_symbol, channel_timeframe = key
            if channel_symbol != symbol:
                continue
            
            # Get channel direction
            df = state.active_channels[key]['df']
            if 'trend' not in df.columns or len(df) < 2:
                continue
            trend_slope = df['trend'].iloc[-1] - df['trend'].iloc[0]
            channel_direction = "BUY" if trend_slope < 0 else "SELL"
            
            if channel_direction != trade_direction:
                del state.active_channels[key]
                if key in state.levels:
                    del state.levels[key]

def start_cooldown(symbol, timeframe, state, current_time):
    """
    Start cooldown period - EXACTLY as in visuals.py start_cooldown()
    """
    end_time = current_time + timedelta(hours=1)
    state.cooldown[(symbol, timeframe)] = end_time

def is_cooldown_active(symbol, timeframe, state, current_time):
    """
    Check if cooldown is active - EXACTLY as in visuals.py is_cooldown_active()
    """
    key = (symbol, timeframe)
    if key not in state.cooldown:
        return False
    if current_time >= state.cooldown[key]:
        del state.cooldown[key]
        return False
    return True

# ==================== BACKTEST ENGINE ====================

def run_backtest(historical_data, symbols, timeframes, start_date=None, end_date=None):
    """
    Run backtest on historical data - EXACTLY simulating the live bot
    """
    state = BacktestState()
    
    # Determine all timestamps across all symbols/timeframes
    all_dates = []
    for symbol in symbols:
        for tf in timeframes:
            df = historical_data[symbol].get(tf, pd.DataFrame())
            if not df.empty:
                all_dates.extend(df['time'].tolist())
    
    if not all_dates:
        print("No data available")
        return state
    
    all_dates = sorted(set(all_dates))
    
    if start_date:
        all_dates = [d for d in all_dates if d >= start_date]
    if end_date:
        all_dates = [d for d in all_dates if d <= end_date]
    
    print(f"Running backtest from {all_dates[0]} to {all_dates[-1]}")
    print(f"Total candles: {len(all_dates)}")
    
    # Preload supply/demand zones at the beginning
    print("Preloading supply/demand zones...")
    preload_supply_demand_zones(state, historical_data, all_dates[0])
    
    # Process each timestamp sequentially (exactly like live bot processes each moment)
    for i, current_time in enumerate(all_dates):
        if i % 1000 == 0:
            print(f"Processing {i}/{len(all_dates)}...")
        
        state.current_time = current_time
        
        # Check if zones need reloading
        if should_reload_zones(state, current_time):
            for key in state.to_be_reloaded:
                symbol, timeframe = key
                # Reload zones for this key
                if key in state.supply_demand_zones:
                    del state.supply_demand_zones[key]
                preload_supply_demand_zones(state, historical_data, current_time)
        
        # Process each symbol and timeframe (exactly as in live bot's loops)
        for symbol in symbols:
            for timeframe in timeframes:
                df = historical_data[symbol].get(timeframe, pd.DataFrame())
                if df.empty:
                    continue
                
                # Find current index
                current_idx = df[df['time'] <= current_time].index[-1] if len(df[df['time'] <= current_time]) > 0 else -1
                if current_idx < 0:
                    continue
                
                key = (symbol, timeframe)
                
                # NEW CHANNEL DETECTION - exactly as in live bot
                if key not in state.active_channels and not is_cooldown_active(symbol, timeframe, state, current_time):
                    # Try different bar counts (exactly as in visuals.py)
                    num_bars_list = [30, 40, 50, 60, 70, 80]
                    if timeframe == mt5.TIMEFRAME_H1:
                        num_bars_list = [40, 50, 60, 70, 80, 100]
                    elif timeframe == mt5.TIMEFRAME_M15:
                        num_bars_list = [40, 50, 60, 70, 80]
                    elif timeframe == mt5.TIMEFRAME_M5:
                        num_bars_list = [30, 40, 50, 60, 70, 80]
                    
                    for num_bars in num_bars_list:
                        if current_idx + 1 < num_bars:
                            continue
                        
                        # Get candles up to current time
                        candles = df.iloc[current_idx - num_bars + 1:current_idx + 1].copy()
                        if len(candles) < num_bars:
                            continue
                        
                        # Detect channel
                        channel = detect_regression_channel(candles, symbol, timeframe, state, current_time)
                        
                        if channel is not None and channel[0] == True and channel[2] == True:
                            # Save channel
                            state.active_channels[key] = {
                                "df": channel[1].copy(),
                                "breakout_idx": None,
                                "last_touch_idx": None,
                                "last_touch_price": None,
                                "num_bars": num_bars,
                                "timeframe": timeframe,
                                "last_time": channel[1]['time'].iloc[-2] if len(channel[1]) >= 2 else None,
                                "a_plus_setup": channel[2]
                            }
                            
                            # Check initial breakout condition (exactly as in live bot)
                            df_channel = state.active_channels[key]["df"]
                            last = df_channel.iloc[-10:] if len(df_channel) >= 10 else df_channel
                            upper = df_channel['upper'].iloc[-1]
                            lower = df_channel['lower'].iloc[-1]
                            last_trend = df_channel['trend']
                            trend_slope = last_trend.iloc[-1] - last_trend.iloc[0]
                            
                            for j in range(len(last)):
                                candle = last.iloc[j]
                                broke_above = candle['high'] > upper
                                broke_below = candle['low'] < lower
                                
                                # Apply symbol-specific filters
                                if timeframe == mt5.TIMEFRAME_H1:
                                    if symbol in H1_B and (trend_slope > 0 or (trend_slope < 0 and broke_below)):
                                        del state.active_channels[key]
                                        break
                                    elif symbol in H1_S and ((trend_slope > 0 and broke_above) or trend_slope < 0):
                                        del state.active_channels[key]
                                        break
                                    elif symbol in H1_BS and ((trend_slope > 0 and broke_above) or (trend_slope < 0 and broke_below)):
                                        del state.active_channels[key]
                                        break
                                
                                elif timeframe == mt5.TIMEFRAME_M15:
                                    if symbol in M15_B and (trend_slope > 0 or (trend_slope < 0 and broke_below)):
                                        del state.active_channels[key]
                                        break
                                    elif symbol in M15_S and ((trend_slope > 0 and broke_above) or trend_slope < 0):
                                        del state.active_channels[key]
                                        break
                                    elif symbol in M15_BS and ((trend_slope > 0 and broke_above) or (trend_slope < 0 and broke_below)):
                                        del state.active_channels[key]
                                        break
                                
                                elif timeframe == mt5.TIMEFRAME_M5:
                                    if symbol in M5_B and (trend_slope > 0 or (trend_slope < 0 and broke_below)):
                                        del state.active_channels[key]
                                        break
                                    elif symbol in M5_S and ((trend_slope > 0 and broke_above) or trend_slope < 0):
                                        del state.active_channels[key]
                                        break
                                    elif symbol in M5_BS and ((trend_slope > 0 and broke_above) or (trend_slope < 0 and broke_below)):
                                        del state.active_channels[key]
                                        break
                            
                            break  # Stop trying different num_bars if channel found
                
                # UPDATE EXISTING CHANNELS - exactly as in live bot
                elif key in state.active_channels:
                    # Update channel data
                    update_channel_data(symbol, timeframe, state, current_idx, historical_data, current_time)
                    
                    if key not in state.active_channels:
                        continue
                    
                    # Detect breakout
                    candles = state.active_channels[key]["df"]
                    detect_break(candles, symbol, timeframe, state)
                    
                    if key not in state.active_channels:
                        continue
                    
                    # Find entry if breakout exists
                    breakout_idx = state.active_channels[key].get('breakout_idx')
                    last_touch_idx = state.active_channels[key].get('last_touch_idx')
                    entry_idx = find_valid_entry(candles, breakout_idx, last_touch_idx, symbol, timeframe, state)
                    
                    if key not in state.active_channels:
                        continue
                    
                    if entry_idx is not None:
                        fib_levels = apply_fibonacci_levels(symbol, entry_idx, candles, timeframe, state)
                        if fib_levels:
                            direction = "BUY" if candles['close'].iloc[entry_idx] > candles['upper'].iloc[entry_idx] else "SELL"
                            
                            # Place trade based on symbol category (exactly as in live bot)
                            if timeframe == mt5.TIMEFRAME_H1:
                                if symbol in H1_pen:
                                    pending(symbol, direction, candles['close'].iloc[entry_idx], 
                                           fib_levels['sl'], fib_levels['tp3'], fib_levels['sniper'], 
                                           timeframe, state, current_time)
                                elif symbol in H1_pl:
                                    place_trade(symbol, direction, candles['close'].iloc[entry_idx], 
                                               fib_levels['sl1'], fib_levels['tp3'], 
                                               timeframe, state, current_time)
                            
                            elif timeframe == mt5.TIMEFRAME_M15:
                                if symbol in M15_pen:
                                    pending(symbol, direction, candles['close'].iloc[entry_idx], 
                                           fib_levels['sl'], fib_levels['tp3'], fib_levels['sniper'], 
                                           timeframe, state, current_time)
                                elif symbol in M15_pl:
                                    place_trade(symbol, direction, candles['close'].iloc[entry_idx], 
                                               fib_levels['sl1'], fib_levels['tp3'], 
                                               timeframe, state, current_time)
                            
                            elif timeframe == mt5.TIMEFRAME_M5:
                                if symbol in M5_pen:
                                    pending(symbol, direction, candles['close'].iloc[entry_idx], 
                                           fib_levels['sl'], fib_levels['tp3'], fib_levels['sniper'], 
                                           timeframe, state, current_time)
                                elif symbol in M5_pl:
                                    place_trade(symbol, direction, candles['close'].iloc[entry_idx], 
                                               fib_levels['sl1'], fib_levels['tp3'], 
                                               timeframe, state, current_time)
                
                # Check TP1/TP2 for existing levels
                if key in state.levels:
                    L = state.levels[key]
                    check_tp1_and_manage_trades(symbol, L.get("tp1"), timeframe, state, current_time, historical_data)
                    check_tp2_and_manage_trades(symbol, L.get("tp2"), timeframe, state, current_time, historical_data)
                
                # Close pending orders if TP2 (old TP1) hit
                close_pending(symbol, state, current_time, historical_data)
        
        # Global management functions (run at each timestamp exactly as in live bot)
        update_pending_order_status(state, current_time, historical_data)
        handle_engulfing_patterns(state, current_time, historical_data)
        del_completed(state, current_time, historical_data)
        check_conflicting_slopes(state)
        check_conflicting_trades(state)
    
    return state

# ==================== RESULTS ANALYSIS ====================

def analyze_results(state):
    """
    Analyze backtest results including missed trades
    """
    trades = [t for t in state.trade_history if t['status'] in ['closed', 'open']]
    closed_trades = [t for t in trades if t['status'] == 'closed']
    
    if not closed_trades and state.missed_trades_count == 0:
        print("No trades or missed trades")
        return
    
    # Basic statistics
    total_trades = len(closed_trades)
    winning_trades = [t for t in closed_trades if t['pnl'] > 0]
    losing_trades = [t for t in closed_trades if t['pnl'] < 0]
    win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
    
    total_pnl = sum(t['pnl'] for t in closed_trades)
    avg_win = sum(t['pnl'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
    avg_loss = sum(t['pnl'] for t in losing_trades) / len(losing_trades) if losing_trades else 0
    
    profit_factor = abs(sum(t['pnl'] for t in winning_trades) / sum(t['pnl'] for t in losing_trades)) if losing_trades and sum(t['pnl'] for t in losing_trades) != 0 else float('inf')
    
    # Trade distribution by timeframe
    trades_by_tf = {}
    for t in closed_trades:
        tf_str = timeframe_to_str(t['timeframe'])
        if tf_str not in trades_by_tf:
            trades_by_tf[tf_str] = []
        trades_by_tf[tf_str].append(t)
    
    # Missed trades by timeframe
    missed_by_tf = {}
    for t in state.missed_trades:
        tf_str = timeframe_to_str(t['timeframe'])
        if tf_str not in missed_by_tf:
            missed_by_tf[tf_str] = []
        missed_by_tf[tf_str].append(t)
    
    print("\n" + "="*60)
    print("BACKTEST RESULTS")
    print("="*60)
    print(f"Initial Capital: ${state.initial_capital:.2f}")
    print(f"Final Capital: ${state.current_capital:.2f}")
    print(f"Total P&L: ${total_pnl:.2f}")
    print(f"Return: {(state.current_capital/state.initial_capital - 1)*100:.2f}%")
    print("\n" + "-"*30)
    print("TRADE STATISTICS:")
    print(f"Total Signals Generated: {state.total_signals}")
    print(f"Executed Trades: {state.executed_trades}")
    print(f"Missed Trades (TP1 hit before entry): {state.missed_trades_count}")
    print(f"Execution Rate: {(state.executed_trades/state.total_signals*100):.2f}%" if state.total_signals > 0 else "Execution Rate: N/A")
    print(f"Missed Trade Rate: {(state.missed_trades_count/state.total_signals*100):.2f}%" if state.total_signals > 0 else "Missed Trade Rate: N/A")
    
    print("\n" + "-"*30)
    print("CLOSED TRADES STATISTICS:")
    print(f"Total Closed Trades: {total_trades}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Avg Win: ${avg_win:.2f}")
    print(f"Avg Loss: ${avg_loss:.2f}")
    print(f"Profit Factor: {profit_factor:.2f}")
    
    print("\n" + "-"*30)
    print("TRADES BY TIMEFRAME:")
    for tf, tf_trades in trades_by_tf.items():
        tf_wins = len([t for t in tf_trades if t['pnl'] > 0])
        tf_pnl = sum(t['pnl'] for t in tf_trades)
        print(f"{tf}: {len(tf_trades)} trades, {tf_wins/len(tf_trades)*100:.1f}% win, P&L: ${tf_pnl:.2f}")
    
    print("\n" + "-"*30)
    print("MISSED TRADES BY TIMEFRAME:")
    for tf, tf_missed in missed_by_tf.items():
        print(f"{tf}: {len(tf_missed)} missed trades")
    
    # Recent trades
    print("\n" + "-"*30)
    print("LAST 10 TRADES:")
    recent = sorted(closed_trades, key=lambda x: x['exit_time'])[-10:]
    for t in recent:
        print(f"{t['exit_time']} | {t['symbol']} {t['direction']} | P&L: ${t['pnl']:.2f} ({t['pnl_pct']:.2f}%) | {t.get('exit_reason', 'UNKNOWN')}")
    
    # Recent missed trades
    if state.missed_trades:
        print("\n" + "-"*30)
        print("LAST 5 MISSED TRADES (TP2 hit before entry):")
        recent_missed = sorted(state.missed_trades, key=lambda x: x['exit_time'])[-5:]
        for t in recent_missed:
            print(f"{t['exit_time']} | {t['symbol']} {t['direction']} | TP2: {t['tp2_price']:.4f} | Entry would have been: {t['entry_price']:.4f}")
    
    return {
        'total_signals': state.total_signals,
        'executed_trades': state.executed_trades,
        'missed_trades': state.missed_trades_count,
        'total_trades': total_trades,
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'profit_factor': profit_factor,
        'final_capital': state.current_capital
    }

def plot_equity_curve(state):
    """
    Plot equity curve
    """
    if not state.equity_curve:
        print("No equity data to plot")
        return
    
    df_equity = pd.DataFrame(state.equity_curve)
    
    plt.figure(figsize=(12, 6))
    plt.plot(df_equity['time'], df_equity['equity'], linewidth=1, label='Equity')
    plt.axhline(y=state.initial_capital, color='r', linestyle='--', label='Initial Capital')
    
    # Add annotation for missed trades
    plt.title(f'Equity Curve (Missed Trades: {state.missed_trades_count})')
    plt.xlabel('Date')
    plt.ylabel('Equity ($)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()

def save_results(state, filename='backtest_results.csv'):
    """
    Save trade history and missed trades to CSV
    """
    # Save all trades
    trades_df = pd.DataFrame(state.trade_history)
    if not trades_df.empty:
        trades_df.to_csv(filename, index=False)
        print(f"Trade history saved to {filename}")
    
    # Save missed trades separately
    if state.missed_trades:
        missed_df = pd.DataFrame(state.missed_trades)
        missed_filename = filename.replace('.csv', '_missed.csv')
        missed_df.to_csv(missed_filename, index=False)
        print(f"Missed trades saved to {missed_filename}")
    
    # Save summary statistics
    summary = {
        'Metric': ['Total Signals', 'Executed Trades', 'Missed Trades', 'Execution Rate (%)', 
                  'Total P&L', 'Win Rate (%)', 'Profit Factor', 'Final Capital'],
        'Value': [
            state.total_signals,
            state.executed_trades,
            state.missed_trades_count,
            (state.executed_trades/state.total_signals*100) if state.total_signals > 0 else 0,
            sum(t['pnl'] for t in state.trade_history if t['status'] == 'closed'),
            (len([t for t in state.trade_history if t['status'] == 'closed' and t['pnl'] > 0]) / 
             len([t for t in state.trade_history if t['status'] == 'closed']) * 100) if len([t for t in state.trade_history if t['status'] == 'closed']) > 0 else 0,
            abs(sum(t['pnl'] for t in state.trade_history if t['status'] == 'closed' and t['pnl'] > 0) / 
                sum(t['pnl'] for t in state.trade_history if t['status'] == 'closed' and t['pnl'] < 0)) if sum(t['pnl'] for t in state.trade_history if t['status'] == 'closed' and t['pnl'] < 0) != 0 else float('inf'),
            state.current_capital
        ]
    }
    
    summary_df = pd.DataFrame(summary)
    summary_filename = filename.replace('.csv', '_summary.csv')
    summary_df.to_csv(summary_filename, index=False)
    print(f"Summary statistics saved to {summary_filename}")

def signal_handler(sig, frame):
    """Handle interrupt signals"""
    print("\n🛑 Script interrupted - shutting down MT5...")
    mt5.shutdown()
    sys.exit(0)

# ==================== MAIN BACKTEST ====================

if __name__ == "__main__":
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("="*60)
    print("DERIV TRADING BOT - BACKTEST (MT5 DATA)")
    print("="*60)
    
    # Configuration
    TIMEFRAMES_TO_TEST = [
        mt5.TIMEFRAME_M5,
        mt5.TIMEFRAME_M15,
        mt5.TIMEFRAME_H1
    ]
    
    # Symbols to test (limit for testing - you can adjust)
    TEST_SYMBOLS = ALL_SYMBOLS[:1]  # Test first 5 symbols to start
    
    # Date range
    START_DATE = datetime(2026, 1, 1)
    END_DATE = datetime(2026, 2, 1)
    
    print(f"\nTest Configuration:")
    print(f"- Symbols: {len(TEST_SYMBOLS)} symbols (first 5)")
    print(f"- Timeframes: M5, M15, H1")
    print(f"- Date Range: {START_DATE.date()} to {END_DATE.date()}")
    print(f"- Initial Capital: $10,000")
    
    # Fetch historical data from MT5
    print("\n" + "="*60)
    print("FETCHING HISTORICAL DATA FROM MT5")
    print("="*60)
    
    historical_data = load_all_historical_data(TEST_SYMBOLS, TIMEFRAMES_TO_TEST, START_DATE, END_DATE)
    
    # Check if we have data
    has_data = False
    for symbol in TEST_SYMBOLS:
        for tf in TIMEFRAMES_TO_TEST:
            if not historical_data[symbol].get(tf, pd.DataFrame()).empty:
                has_data = True
                break
        if has_data:
            break
    
    if not has_data:
        print("\n❌ No data available for any symbol. Please check MT5 connection and symbol availability.")
        mt5.shutdown()
        sys.exit(1)
    
    # Run backtest
    print("\n" + "="*60)
    print("RUNNING BACKTEST")
    print("="*60)
    
    state = run_backtest(historical_data, TEST_SYMBOLS, TIMEFRAMES_TO_TEST, START_DATE, END_DATE)
    
    # Analyze results
    print("\n" + "="*60)
    print("BACKTEST RESULTS")
    print("="*60)
    
    analyze_results(state)
    
    # Plot equity curve
    plot_equity_curve(state)
    
    # Save results
    save_results(state)
    
    print("\nBacktest complete!")
    
    # Shutdown MT5
    mt5.shutdown()