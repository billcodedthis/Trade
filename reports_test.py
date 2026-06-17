# comprehensive_deriv_analysis.py - FIXED VERSION
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
import mplfinance as mpf
import re
from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import PieChart, BarChart, Reference
import matplotlib.font_manager as fm
from typing import List, Dict, Any, Tuple
import shutil
from sklearn.linear_model import LinearRegression

# === CONFIGURATION ===
MT5_PATH = r"C:\Program Files\MetaTrader 5\terminal64.exe"
OUTPUT_FOLDER = str(Path.home() / "OneDrive - University of Ghana" / "test_Comprehensive_Analysis")
os.makedirs(OUTPUT_FOLDER, exist_ok=True)



def clear_output_folder():
    """Delete all files and subfolders inside OUTPUT_FOLDER, but keep the folder itself."""
    if os.path.exists(OUTPUT_FOLDER):
        for item in os.listdir(OUTPUT_FOLDER):
            item_path = os.path.join(OUTPUT_FOLDER, item)
            try:
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    os.unlink(item_path)        # delete file or link
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)    # delete folder and everything inside
                print(f"Deleted: {item_path}")
            except Exception as e:
                print(f"Warning: Failed to delete {item_path}: {e}")
        print(f"Output folder cleared: {OUTPUT_FOLDER}")
    else:
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)
        print(f"Output folder created: {OUTPUT_FOLDER}")

plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10

# Connect to MT5
if not mt5.initialize(path=MT5_PATH):
    print("❌ Failed to connect to MT5")
    quit()
print("✅ Connected to MT5")

# Timeframe mapping
TIMEFRAMES = {
    1: "M1", 5: "M5", 15: "M15", 30: "M30",
    16385: "H1", 16388: "H4", 16408: "D1"
}

# === CANDLE-CONTEXT ANALYSIS CONFIG ===
# For every COMPLETED trade we pull the candles leading up to entry, tag the entry candle and the
# swing candle (the last opposite-coloured candle before entry, same rule the bot itself uses), and
# compute a set of indicators on each candle so we can compare winners vs losers.
CANDLE_CONTEXT_LOOKBACK = 30        # candles to pull before (and including) the entry candle
CANDLE_INDICATOR_WARMUP = 50        # extra candles fetched purely to warm up rolling indicators
CANDLE_CONTEXT_MAX_CHARTS = 40      # cap on highlighted candle charts generated (set to None for no cap)
ENABLE_CANDLE_CONTEXT_ANALYSIS = True

STD_DEV_WINDOW = 20   # rolling window for std-dev / volume / body / range z-scores
ATR_WINDOW = 14
RSI_WINDOW = 14
EMA_FAST = 9
EMA_SLOW = 21

# === REGRESSION CHANNEL RECONSTRUCTION CONFIG ===
# visuals.py never logs which num_bars window or creation point produced the regression
# channel for a given trade, so we re-derive it: walk backward from the now-known
# entry_candle_idx to find the structural swing/BOS point (mirrors detect_break's
# last_touch logic but anchored on price action, no channel needed), then search over the
# bot's actual num_bars candidates + a range of channel-creation offsets for the regression
# fit whose band lands exactly on that swing point. Best (lowest price error) match wins;
# flagged 'approximate' in the output if the error exceeds CHANNEL_MATCH_TOLERANCE.
CHANNEL_NUM_BARS_BY_TF = {
    "H1": [40, 50, 60, 70, 80, 100],
    "M15": [40, 50, 60, 70, 80],
    "M5": [30, 40, 50, 60, 70, 80],
    "M1": [40, 50, 60, 70, 80, 100],
}
CHANNEL_UPPER_STD_MULT = 2.0   # mirrors detect_regression_channel: upper = trend + 2*std
CHANNEL_LOWER_STD_MULT = 3.0   # mirrors detect_regression_channel: lower = trend - 3*std
CHANNEL_SWING_LOOKBACK = 3            # bars each side used to confirm a local swing high/low
CHANNEL_MAX_SCAN_BACK = 12            # how far before entry_idx to search for the swing/BOS point
CHANNEL_CREATION_OFFSET_RANGE = 20    # how far before/after the swing point to try as the
                                       # channel's analysis-window end point (creation_end)
CHANNEL_MATCH_TOLERANCE_ATR_FRAC = 0.05   # error vs 5% of ATR at the swing point = "exact"
ENABLE_CHANNEL_RECONSTRUCTION = True

TF_TO_MT5 = {
    "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4, "D1": mt5.TIMEFRAME_D1
}
TF_MINUTES = {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440}
# Trading configuration from visuals.py
def get_trading_config():
    XAUUSD = "XAUUSD.0"
    BTCUSD="BTCUSD.0"
    Jump = ["Jump 25 Index.0"]
    J=["Jump 75 Index.0"]
    v=["Volatility 75 Index.0"]
    US =["Wall Street 30.0"]
    H1_S_I = ["CADCHF.0","EURGBP.0"]
    M5_S_P = ["Volatility 30 (1s) Index.0","Volatility 25 (1s) Index.0","Volatility 75 (1s) Index.0","Volatility 30 (1s) Index.0","Gold Basket.0"]
    M5_B_P=["Boom 300 Index.0","Hong Kong 50.0"]
    M15_B_P = ["Volatility 100 (1s) Index.0"]
    M15_S_P = []
    
    return {
        "H1_PENDING": Jump ,
        "H1_INSTANT": [XAUUSD]+US+H1_S_I,
        "M15_PENDING": [XAUUSD]+M15_B_P+M15_S_P,
        "M15_INSTANT": [],
        "M5_PENDING": [XAUUSD]+M5_S_P+v+M5_B_P,
        "M5_INSTANT": [],
        "M1_PENDING": [],
        "M1_INSTANT": []
    }

def get_all_deals():
    from_date = datetime(2026, 4, 5)
    to_date = datetime.now()
    deals = mt5.history_deals_get(from_date, to_date)
    print(f"Looking for deals from {from_date.date()} to {to_date.date()}")
    if deals is None:
        print("history_deals_get returned None")
    else:
        print(f"Found {len(deals)} total deals in history")
        if len(deals) > 0:
            print(f"Most recent deal time: {pd.to_datetime(deals[-1].time, unit='s')}")
    if deals is None or len(deals) == 0:
        print("⚠️ No deals found")
        return pd.DataFrame()
    df = pd.DataFrame(list(deals), columns=deals[0]._asdict().keys())
    if 'time' in df.columns:
        df['time'] = pd.to_datetime(df['time'], unit='s')
    return df

def get_all_orders():
    from_date = datetime(2026, 4, 5)
    to_date = datetime.now()
    orders = mt5.history_orders_get(from_date, to_date)
    if orders is None or len(orders) == 0:
        print("⚠️ No orders found")
        return pd.DataFrame()
    df = pd.DataFrame(list(orders), columns=orders[0]._asdict().keys())
    if 'time_setup' in df.columns:
        df['time_setup'] = pd.to_datetime(df['time_setup'], unit='s')
    if 'time_done' in df.columns:
        df['time_done'] = pd.to_datetime(df['time_done'], unit='s')
    return df

def extract_tp1_from_comment(comment: str):
    """Extract TP1 from comment field"""
    if not comment or pd.isna(comment):
        return None
    try:
        numbers = re.findall(r"[-+]?\d*\.\d+|\d+", str(comment))
        if numbers:
            return float(numbers[0])
    except (ValueError, TypeError):
        pass
    return None

def safe_float_conversion(value, default=0.0):
    """Safely convert value to float"""
    try:
        return float(value) if value is not None and value != "" else default
    except (ValueError, TypeError):
        return default

def get_ticks_for_simulation(symbol, start_time, end_time, max_ticks=1000000):
    """
    Get tick data for simulation with proper error handling
    Returns: DataFrame with columns ['time', 'bid', 'ask', 'last', 'volume', 'flags']
    """
    try:
        # Convert datetime to timestamp
        from_timestamp = int(start_time.timestamp())
        to_timestamp = int(end_time.timestamp())
        
        # Get ticks
        ticks = mt5.copy_ticks_range(symbol, from_timestamp, to_timestamp, mt5.COPY_TICKS_ALL)
        
        if ticks is None or len(ticks) == 0:
            # Try with ticks info (last 1000 ticks as fallback)
            ticks_info = mt5.symbol_info_tick(symbol)
            if ticks_info is None:
                print(f"⚠️ No tick data available for {symbol}")
                return pd.DataFrame()
            
            # Create minimal tick data from current price
            return pd.DataFrame([{
                'time': start_time,
                'bid': ticks_info.bid,
                'ask': ticks_info.ask,
                'last': ticks_info.last,
                'volume': 0,
                'flags': 0
            }])
        
        # Convert to DataFrame
        ticks_df = pd.DataFrame(ticks)
        ticks_df['time'] = pd.to_datetime(ticks_df['time'], unit='s')
        
        # Limit number of ticks if too many
        if len(ticks_df) > max_ticks:
            print(f"📊 Downsampling {len(ticks_df)} ticks to {max_ticks} for {symbol}")
            ticks_df = ticks_df.iloc[::len(ticks_df)//max_ticks + 1]
        
        return ticks_df
        
    except Exception as e:
        print(f"⚠️ Error getting ticks for {symbol}: {e}")
        return pd.DataFrame()

def simulate_price_hits_with_ticks(symbol, direction, entry_price, tp1_price, sl_price, start_time, end_time):
    """
    Simulate price hits using tick-by-tick data for maximum accuracy
    
    Returns: tuple of (tp1_hit, sl_hit, entry_hit, tp1_time, sl_time, entry_time, first_touch_time)
    """
    # Get tick data
    ticks_df = get_ticks_for_simulation(symbol, start_time, end_time)
    
    if ticks_df.empty:
        print(f"⚠️ No tick data for {symbol} between {start_time} and {end_time}")
        return False, False, False, None, None, None, None
    
    # Initialize tracking variables
    tp1_hit = sl_hit = entry_hit = False
    tp1_time = sl_time = entry_time = first_touch_time = None
    
    # For buy orders, we use ask price for entry check and bid price for TP/SL check
    # For sell orders, we use bid price for entry check and ask price for TP/SL check
    # In practice, we'll check both bid and ask for hits
    
    for _, tick in ticks_df.iterrows():
        tick_time = tick['time']
        bid = safe_float_conversion(tick.get('bid', 0))
        ask = safe_float_conversion(tick.get('ask', 0))
        
        # If no bid/ask, use last price
        if bid == 0 and ask == 0:
            last_price = safe_float_conversion(tick.get('last', 0))
            if last_price == 0:
                continue
            bid = ask = last_price
        
        # Check TP1 hit
        if not tp1_hit:
            if direction == "BUY" and bid >= tp1_price:
                tp1_hit = True
                tp1_time = tick_time
            elif direction == "SELL" and ask <= tp1_price:
                tp1_hit = True
                tp1_time = tick_time
        
        # Check SL hit
        if not sl_hit and sl_price > 0:
            if direction == "BUY" and ask <= sl_price:
                sl_hit = True
                sl_time = tick_time
            elif direction == "SELL" and bid >= sl_price:
                sl_hit = True
                sl_time = tick_time
        
        # Check Entry hit (for pending orders)
        if not entry_hit:
            if direction == "BUY" and ask <= entry_price:
                entry_hit = True
                entry_time = tick_time
            elif direction == "SELL" and bid >= entry_price:
                entry_hit = True
                entry_time = tick_time
        
        # Track first touch of any level
        if not first_touch_time:
            touched = False
            if direction == "BUY":
                if bid >= tp1_price or ask <= sl_price or ask <= entry_price:
                    touched = True
            elif direction == "SELL":
                if ask <= tp1_price or bid >= sl_price or bid >= entry_price:
                    touched = True
            
            if touched:
                first_touch_time = tick_time
        
        # Early exit if all levels hit
        if tp1_hit and sl_hit and entry_hit:
            break
    
    return tp1_hit, sl_hit, entry_hit, tp1_time, sl_time, entry_time, first_touch_time

def analyze_pending_orders_enhanced():
    """Enhanced pending order analysis with TICK-BASED simulations"""
    print("🔍 Enhanced Pending Order Analysis with TICK simulations...")
    orders_df = get_all_orders()
    if orders_df.empty:
        print("No historical orders found.")
        return []

    # Filter pending orders
    pending = orders_df[orders_df['type'].isin([2, 3, 4, 5])].copy()
    print(f"Found {len(pending)} pending orders to analyze")

    records = []
    config = get_trading_config()

    # Simple counter approach
    total_orders = len(pending)
    processed_count = 0
    
    for _, order in pending.iterrows():
        symbol = order['symbol']
        magic = order['magic']
        tf_str = TIMEFRAMES.get(magic, f"TF{magic}")
        direction = "BUY" if order['type'] in [2, 4] else "SELL"
        
        # Safe conversion
        entry = safe_float_conversion(order['price_open'])
        sl = safe_float_conversion(order['sl'])
        tp2 = safe_float_conversion(order['tp'])
        comment = str(order.get('comment', ''))
        tp1 = extract_tp1_from_comment(comment)

        if tp1 is None or sl == 0.0 or entry == 0.0:
            processed_count += 1
            continue

        start = order['time_setup']
        end = order['time_done'] if pd.notna(order['time_done']) else datetime.now()
        
        # More realistic end time calculation
        if pd.notna(order['time_done']):
            # Order was completed/cancelled
            position_id = order.get('position_id', 0)
            if position_id != 0:
                # This became a position, use position logic
                deals = mt5.history_deals_get(position=position_id)
                if deals and len(deals) > 1:
                    # Use the actual exit time
                    exit_time = max(pd.to_datetime(deal.time, unit='s') for deal in deals)
                    end = exit_time
            # If cancelled without becoming position, keep the cancellation time
        else:
            # Still pending, analyze up to current time
            end = datetime.now()
        
        # Use tick-based simulation
        tp1_hit, sl_hit, entry_hit, tp1_time, sl_time, entry_time, first_touch_time = \
            simulate_price_hits_with_ticks(symbol, direction, entry, tp1, sl, start, end)
        
        # Enhanced outcome determination
        missed_opportunity = tp1_hit and not entry_hit
        won_trade = False
        lost_trade = False
        
        if entry_hit:
            if tp1_hit and (not sl_hit or (sl_time and tp1_time and tp1_time < sl_time)):
                won_trade = True
            elif sl_hit and (not tp1_hit or (tp1_time and sl_time and sl_time < tp1_time)):
                lost_trade = True

        # Determine order type from config
        order_type = "UNKNOWN"
        if tf_str == "H1":
            if symbol in config["H1_PENDING"]: order_type = "PENDING"
            elif symbol in config["H1_INSTANT"]: order_type = "INSTANT"
        elif tf_str == "M15":
            if symbol in config["M15_PENDING"]: order_type = "PENDING"
            elif symbol in config["M15_INSTANT"]: order_type = "INSTANT"
        elif tf_str == "M5":
            if symbol in config["M5_PENDING"]: order_type = "PENDING"
            elif symbol in config["M5_INSTANT"]: order_type = "INSTANT"
        elif tf_str == "M1":
            if symbol in config["M1_PENDING"]: order_type = "PENDING"
            elif symbol in config["M1_INSTANT"]: order_type = "INSTANT"

        if order_type == "UNKNOWN":
            continue

        records.append({
            "Symbol": symbol,
            "Timeframe": tf_str,
            "Direction": direction,
            "Order Type": order_type,
            "Signal Time": start,
            "Setup Time": start,
            "Entry Price": entry,
            "TP1": tp1,
            "SL": sl,
            "TP2": tp2,
            "TP1 Hit": tp1_hit,
            "SL Hit": sl_hit,
            "Entry Filled": entry_hit,
            "Missed Opportunity": missed_opportunity,
            "Won Trade": won_trade,
            "Lost Trade": lost_trade,
            "TP1 Time": tp1_time,
            "SL Time": sl_time,
            "Entry Time": entry_time,
            "First Touch Time": first_touch_time,
            "Analysis Period": f"{(end - start).days} days",
            "Trade Type": "PENDING_ORDER",
            "Simulation Method": "TICKS"
        })
        
        processed_count += 1
        
        # Progress update - FIXED
        if processed_count % 10 == 0:
            print(f"  Processed {processed_count}/{total_orders} orders...")

    print(f"Enhanced tick-based pending order analysis complete: {len(records)} orders processed")
    return records

def analyze_completed_trades():
    """Analyze completed trades from deals history - ROBUST VERSION"""
    print("Analyzing completed trades...")
    deals = get_all_deals()
    records = []
    
    if deals.empty:
        print("No deals found")
        return records
    
    # Build ticket -> time_setup lookup so we can recover the ORDER PLACEMENT time for
    # every entry deal (deal['order'] is the ticket of the order that generated it).
    # For INSTANT trades this placement time equals the fill time (market order). For
    # PENDING trades this is the time the resting limit order was actually placed —
    # i.e. the candle immediately AFTER the bot's signal/breakout candle
    # (visuals.py: pending()/place_trade() are called right after entry_candle_idx closes).
    orders_lookup = get_all_orders()
    ticket_to_setup = {}
    if not orders_lookup.empty and 'ticket' in orders_lookup.columns:
        ticket_to_setup = dict(zip(orders_lookup['ticket'], orders_lookup['time_setup']))

    # Group by position_id
    for pos_id, group in deals.groupby('position_id'):
        if pos_id == 0:
            continue
        
        # Find real entry deal (type 0 or 1, entry=0)
        entry_deals = group[group['entry'] == 0]
        if entry_deals.empty:
            continue
            
        entry = entry_deals.iloc[0]
        
        # === SAFELY extract fields (this is the fix) ===
        symbol = entry.get('symbol', 'Unknown')
        magic = int(entry.get('magic', 0)) if entry.get('magic') is not None else 0
        timeframe_str = TIMEFRAMES.get(magic, f"Unknown({magic})")
        
        direction = "BUY" if entry['type'] == 0 else "SELL"
        volume = safe_float_conversion(entry.get('volume', 0))
        entry_price = safe_float_conversion(entry.get('price', 0))
        entry_time = pd.to_datetime(entry['time'], unit='s')

        # Order placement time = when pending()/place_trade() was actually called in
        # visuals.py, i.e. the candle right after entry_candle_idx. Falls back to the
        # deal's own fill time if the originating order can't be found (shouldn't
        # happen for INSTANT trades, where placement == fill anyway).
        order_ticket = entry.get('order', None)
        placement_time = ticket_to_setup.get(order_ticket, entry_time) if order_ticket is not None else entry_time
        if pd.isna(placement_time):
            placement_time = entry_time
                
        sl = safe_float_conversion(entry.get('sl', 0))
        tp = safe_float_conversion(entry.get('tp', 0))
        
        comment = str(entry.get('comment', '')).strip()
        tp1 = extract_tp1_from_comment(comment)
        
        net_profit = group['profit'].sum() + group['swap'].sum() + group['commission'].sum()
        net_profit = round(float(net_profit), 2)

        exit_deals = group[group['entry'] == 1]
        if exit_deals.empty:
            continue
        exit = exit_deals.iloc[-1]
        last_sl = extract_tp1_from_comment(exit.get('comment', 0))
        
        # Outcome & Reason
        if net_profit > 0:
            outcome = "WINNER"
            reason = "TP Hit"
        elif net_profit < 0 and (entry_price != last_sl):
            outcome = "LOSER"
            reason = "SL Hit"
        else:
            outcome = "BREAKEVEN"
            reason = "Manual/BE"
        
        # Order type detection
        config = get_trading_config()
        order_type = "UNKNOWN"
        tf_key = None
        if magic == 16385 or timeframe_str == "H1":
            tf_key = "H1"
        elif magic == mt5.TIMEFRAME_M15 or timeframe_str == "M15":
            tf_key = "M15"
        elif magic == mt5.TIMEFRAME_M5 or timeframe_str == "M5":
            tf_key = "M5"
        elif magic == mt5.TIMEFRAME_M1 or timeframe_str == "M1":
            tf_key = "M1"
            
        if tf_key:
            if symbol in config.get(f"{tf_key}_PENDING", []) or symbol in config.get(f"{tf_key}_INSTANT", []):
                order_type = "PENDING" if symbol in config.get(f"{tf_key}_PENDING", []) else "INSTANT"

        if order_type == "UNKNOWN":
            continue

        records.append({
            "Symbol": symbol,
            "Timeframe": timeframe_str,
            "Direction": direction,
            "Order Type": order_type,
            "Signal Time": placement_time,
            "Entry Time": entry_time,
            "Profit": net_profit,
            "Outcome": outcome,
            "Reason": reason,
            "Trade Type": "COMPLETED",
            "Entry Price": entry_price,
            "SL": sl if sl != 0 else None,
            "TP": tp if tp != 0 else None,
            "TP1": tp1,
            "Volume": volume,
            "Position ID": pos_id,
            "Simulation Method": "ACTUAL"  # Track that this is actual trade, not simulation
        })

    print(f"Completed trades analysis: {len(records)} trades processed")
    return records

def analyze_strategy_performance():
    """Comprehensive analysis combining pending orders and completed trades"""
    print("Running comprehensive strategy analysis...")
    
    pending_data = analyze_pending_orders_enhanced()
    completed_data = analyze_completed_trades()
    
    # Convert separately first so columns are preserved
    df_pending   = pd.DataFrame(pending_data)
    df_completed = pd.DataFrame(completed_data)
    
    # Add missing columns with correct type so they survive the concat
    for col in ['Outcome', 'Reason', 'TP', 'Volume', 'Position ID', 'Profit']:
        if col not in df_pending.columns:
            df_pending[col] = pd.NA
        if col not in df_completed.columns:
            df_completed[col] = pd.NA
    
    # Now safe concat
    df = pd.concat([df_pending, df_completed], ignore_index=True)
    
    # Type fixing
    numeric_columns = ['Entry Price', 'TP1', 'SL', 'TP2', 'Profit', 'Volume', 'TP']
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    bool_columns = ['TP1 Hit', 'SL Hit', 'Entry Filled', 'Missed Opportunity', 'Won Trade']
    for col in bool_columns:
        if col in df.columns:
            df[col] = df[col].astype('boolean')
    
    print(f"Final combined dataset: {len(df)} rows ({len(df_pending)} pending + {len(df_completed)} completed)")
    return df

# ======================================================================================
# === CANDLE-CONTEXT ANALYSIS ===
# Pulls the candles leading into every completed trade, tags the entry candle (the candle
# right before the trade's actual fill) and the swing candle (the last opposite-coloured
# candle before entry — the same rule apply_fibonacci_levels() uses in the live bot), computes
# volume/std-dev/ATR/RSI/EMA style indicators on each candle, and looks for indicator patterns
# that distinguish winning trades from losing ones.
# ======================================================================================

def compute_candle_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds volume, standard-deviation, ATR, RSI, EMA and z-score style indicator columns to a
    candle dataframe. Expects columns: time, open, high, low, close, volume (or tick_volume),
    sorted ascending by time.
    """
    d = df.copy().reset_index(drop=True)
    if 'volume' not in d.columns:
        d['volume'] = d.get('tick_volume', 0)

    d['body'] = d['close'] - d['open']
    d['body_abs'] = d['body'].abs()
    d['range'] = (d['high'] - d['low']).replace(0, np.nan)
    d['upper_wick'] = d['high'] - d[['open', 'close']].max(axis=1)
    d['lower_wick'] = d[['open', 'close']].min(axis=1) - d['low']
    d['body_pct_of_range'] = (d['body_abs'] / d['range'] * 100).fillna(0)
    d['is_bullish'] = d['close'] > d['open']

    # Rolling standard deviation of closing price (volatility context around the candle)
    d['std_dev_20'] = d['close'].rolling(window=STD_DEV_WINDOW, min_periods=max(3, STD_DEV_WINDOW // 2)).std()

    # ATR (Wilder's smoothing)
    prev_close = d['close'].shift(1)
    true_range = pd.concat([
        d['high'] - d['low'],
        (d['high'] - prev_close).abs(),
        (d['low'] - prev_close).abs()
    ], axis=1).max(axis=1)
    d['true_range'] = true_range
    d['atr_14'] = true_range.ewm(alpha=1 / ATR_WINDOW, min_periods=max(3, ATR_WINDOW // 2), adjust=False).mean()

    # RSI (Wilder's smoothing)
    delta = d['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / RSI_WINDOW, min_periods=max(3, RSI_WINDOW // 2), adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / RSI_WINDOW, min_periods=max(3, RSI_WINDOW // 2), adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    d['rsi_14'] = (100 - (100 / (1 + rs))).fillna(50)

    # EMAs and distance from price
    d['ema_fast'] = d['close'].ewm(span=EMA_FAST, adjust=False).mean()
    d['ema_slow'] = d['close'].ewm(span=EMA_SLOW, adjust=False).mean()
    d['dist_from_ema_fast_pct'] = (d['close'] - d['ema_fast']) / d['ema_fast'] * 100
    d['dist_from_ema_slow_pct'] = (d['close'] - d['ema_slow']) / d['ema_slow'] * 100
    d['ema_fast_slope'] = d['ema_fast'].diff()

    # Volume behaviour relative to its own recent history
    vol_sma = d['volume'].rolling(window=STD_DEV_WINDOW, min_periods=max(3, STD_DEV_WINDOW // 2)).mean()
    vol_std = d['volume'].rolling(window=STD_DEV_WINDOW, min_periods=max(3, STD_DEV_WINDOW // 2)).std()
    d['volume_zscore_20'] = ((d['volume'] - vol_sma) / vol_std.replace(0, np.nan)).fillna(0)

    # Body / range z-scores (flags abnormally large or small candles vs recent history)
    body_sma = d['body_abs'].rolling(STD_DEV_WINDOW, min_periods=3).mean()
    body_std = d['body_abs'].rolling(STD_DEV_WINDOW, min_periods=3).std()
    d['body_zscore_20'] = ((d['body_abs'] - body_sma) / body_std.replace(0, np.nan)).fillna(0)

    range_sma = d['range'].rolling(STD_DEV_WINDOW, min_periods=3).mean()
    range_std = d['range'].rolling(STD_DEV_WINDOW, min_periods=3).std()
    d['range_zscore_20'] = ((d['range'] - range_sma) / range_std.replace(0, np.nan)).fillna(0)

    return d


def fetch_candle_window(symbol, tf_str, window_end_time, lookback=CANDLE_CONTEXT_LOOKBACK,
                         warmup=CANDLE_INDICATOR_WARMUP, extra_forward=0):
    """
    Fetch candles ending with the candle that closed right before `window_end_time`
    (plus `extra_forward` candles beyond it, needed when the trigger candle for a
    PENDING order falls after the signal candle), plus extra warm-up candles so rolling
    indicators aren't full of NaNs.
    Returns a DataFrame sorted ascending by time (empty if MT5 has no data for that period).
    """
    mt5_tf = TF_TO_MT5.get(tf_str)
    if mt5_tf is None:
        return pd.DataFrame()

    minutes = TF_MINUTES.get(tf_str, 1)
    bars_needed = lookback + warmup + extra_forward + 5
    # Generous calendar-day buffer so weekends/holidays don't starve the request of bars
    calendar_days = max(5, (minutes * bars_needed / (60 * 24)) * 3 + 5)
    date_from = window_end_time - timedelta(days=calendar_days)
    # Include enough forward bars to cover a trigger candle that lands after window_end_time
    date_to = window_end_time + timedelta(minutes=minutes * (extra_forward + 1)) - timedelta(seconds=1)

    try:
        rates = mt5.copy_rates_range(symbol, mt5_tf, date_from, date_to)
    except Exception as e:
        print(f"⚠️ copy_rates_range failed for {symbol} {tf_str}: {e}")
        return pd.DataFrame()

    if rates is None or len(rates) == 0:
        return pd.DataFrame()

    win = pd.DataFrame(rates)
    win['time'] = pd.to_datetime(win['time'], unit='s')
    win['volume'] = win['tick_volume'] if 'tick_volume' in win.columns else 0
    win = win.sort_values('time').reset_index(drop=True)

    total_needed = lookback + warmup + extra_forward + 1
    return win.tail(total_needed).reset_index(drop=True)


def _locate_candle_idx(window: pd.DataFrame, target_time, tf_minutes: int):
    """
    Returns the index of the candle whose [time, time + tf_minutes) bucket contains
    `target_time`. If target_time falls after the last candle's bucket (e.g. trigger
    hasn't closed yet), returns the last index. Returns None if target_time is before
    the first candle in the window.
    """
    if pd.isna(target_time) or window.empty:
        return None
    times = window['time']
    if target_time < times.iloc[0]:
        return None
    candle_end = times + pd.to_timedelta(tf_minutes, unit='m')
    mask = (times <= target_time) & (target_time < candle_end)
    matches = window.index[mask]
    if len(matches) > 0:
        return int(matches[-1])
    # Fallback: target_time is after the bucket of the last available candle
    # (still-forming candle, or trigger landed exactly on a gap) -> clamp to last row
    if target_time >= times.iloc[-1]:
        return len(window) - 1
    # target_time falls in a gap between candles (e.g. market closed) -> nearest prior candle
    prior = window.index[times <= target_time]
    return int(prior[-1]) if len(prior) > 0 else None


def get_trade_candle_context(symbol, tf_str, signal_time, trigger_time, lookback=CANDLE_CONTEXT_LOOKBACK):
    """
    Builds the indicator-enriched candle window for one trade and tags:
      - entry_idx:   the candle right before the candle that was open when the bot
                     placed the order/trade (visuals.py calls pending()/place_trade()
                     immediately after entry_candle_idx closes, i.e. during the NEXT
                     candle) -> this is entry_candle_idx from visuals.py, recovered
                     purely from `signal_time` (the order placement / instant-trade
                     timestamp), no price matching needed.
      - trigger_idx: the candle that actually contains the fill (`trigger_time`).
                     For INSTANT trades this is the same candle as entry_idx+1.
                     For PENDING trades this can be many candles later -- it's the
                     candle that hit the resting order's entry price.
      - swing_idx:   last opposite-coloured candle before entry_idx (mirrors
                     apply_fibonacci_levels()).
    Every candle strictly between entry_idx and trigger_idx is the "candles the
    pending order sat through before triggering" window you asked to evaluate.

    Returns (window_df, entry_idx, trigger_idx, swing_idx);
    (None, None, None, None) if there isn't enough data.
    """
    if pd.isna(signal_time):
        return None, None, None, None
    if pd.isna(trigger_time):
        trigger_time = signal_time

    tf_minutes = TF_MINUTES.get(tf_str, 1)

    # How many candles ahead of signal_time we might need to reach trigger_time
    gap_minutes = max((trigger_time - signal_time).total_seconds() / 60.0, 0)
    extra_forward = int(gap_minutes // tf_minutes) + 3  # small buffer for boundary rounding

    raw = fetch_candle_window(symbol, tf_str, signal_time, lookback=lookback,
                               extra_forward=extra_forward)
    if raw.empty or len(raw) < 3:
        return None, None, None, None

    enriched = compute_candle_indicators(raw)

    # Candle open at signal_time (i.e. the placement candle = entry_candle_idx + 1)
    placement_idx = _locate_candle_idx(enriched, signal_time, tf_minutes)
    if placement_idx is None or placement_idx < 1:
        return None, None, None, None
    entry_idx = placement_idx - 1

    trigger_idx = _locate_candle_idx(enriched, trigger_time, tf_minutes)
    if trigger_idx is None:
        trigger_idx = entry_idx
    trigger_idx = max(trigger_idx, entry_idx)  # trigger can't precede the signal candle

    # Trim to `lookback` candles of history before entry_idx, keep everything through trigger_idx
    start_pos = max(0, entry_idx - lookback)
    window = enriched.iloc[start_pos: trigger_idx + 1].reset_index(drop=True)
    entry_idx -= start_pos
    trigger_idx -= start_pos

    entry_bullish = bool(window['is_bullish'].iloc[entry_idx])
    swing_idx = None
    for i in range(entry_idx, 0, -1):
        candle_bullish = bool(window['is_bullish'].iloc[i])
        if entry_bullish and not candle_bullish:
            swing_idx = i
            break
        if (not entry_bullish) and candle_bullish:
            swing_idx = i
            break

    return window, entry_idx, trigger_idx, swing_idx


def get_channel_reconstruction_window(symbol, tf_str, signal_time):
    """
    The display window built by get_trade_candle_context() is intentionally short
    (CANDLE_CONTEXT_LOOKBACK candles) -- enough for indicator snapshots, but not enough history
    to fit a regression channel that may have used up to 100 bars (see CHANNEL_NUM_BARS_BY_TF)
    plus up to CHANNEL_CREATION_OFFSET_RANGE bars of slack around the swing point. This fetches
    a separate, wider window purely for channel reconstruction, and returns the entry_idx
    re-expressed relative to THIS wider window (channel reconstruction needs its own index
    space; the display window's entry_idx doesn't directly apply here).

    Returns (channel_window, channel_entry_idx) or (None, None) if data is unavailable.
    """
    max_num_bars = max(CHANNEL_NUM_BARS_BY_TF.get(tf_str, [80]))
    needed_lookback = max_num_bars + CHANNEL_CREATION_OFFSET_RANGE + CHANNEL_MAX_SCAN_BACK + 15

    raw = fetch_candle_window(symbol, tf_str, signal_time, lookback=needed_lookback, extra_forward=0)
    if raw.empty or len(raw) < 20:
        return None, None

    enriched = compute_candle_indicators(raw)
    tf_minutes = TF_MINUTES.get(tf_str, 1)
    placement_idx = _locate_candle_idx(enriched, signal_time, tf_minutes)
    if placement_idx is None or placement_idx < 1:
        return None, None
    channel_entry_idx = placement_idx - 1
    return enriched, channel_entry_idx


CANDLE_SNAPSHOT_COLS = [
    'open', 'high', 'low', 'close', 'volume', 'body', 'body_abs', 'range',
    'upper_wick', 'lower_wick', 'body_pct_of_range', 'std_dev_20', 'atr_14',
    'rsi_14', 'ema_fast', 'ema_slow', 'dist_from_ema_fast_pct',
    'dist_from_ema_slow_pct', 'ema_fast_slope', 'volume_zscore_20',
    'body_zscore_20', 'range_zscore_20'
]


# =====================================================================================
# REGRESSION CHANNEL RECONSTRUCTION
# =====================================================================================
# visuals.py never logs which num_bars window or which bar the channel was created on, and
# the channel is fit once then linearly extrapolated forward (not refit every bar), so it
# can't be looked up -- it has to be re-derived. The approach:
#
#   1. Find the structural swing/BOS point (last_touch_idx / last_touch_price) purely from
#      price action, anchored on the already-known entry_idx. This mirrors detect_break()'s
#      definition (the most recent candle whose wick is a local extreme, using its OPEN or
#      CLOSE -- whichever is the body's outer edge -- as the touch price) without needing the
#      channel's upper/lower arrays at all.
#   2. Search over the bot's real num_bars candidates for that timeframe, and a range of
#      possible channel-creation end-points, for the regression fit whose extrapolated band
#      lands exactly on that swing point at that index. Lowest price error wins.
#   3. Cross-check with the touch-count rule detect_regression_channel itself requires
#      ((upper>=2 and lower>=1) or (upper>=1 and lower>=2)) as a plausibility signal.
#
# This is reconstruction, not log replay: ties are possible, and the result is only ever as
# good as "the channel most consistent with the known facts." Each result is tagged with a
# Match_Quality flag so 'approximate' matches can be filtered out of the highest-confidence
# analyses if desired, without throwing the trade away entirely.

def find_swing_candidates(window: pd.DataFrame, entry_idx: int, direction: str,
                           max_scan_back=CHANNEL_MAX_SCAN_BACK,
                           swing_lookback=CHANNEL_SWING_LOOKBACK):
    """
    Generates EVERY local-extreme candidate in the scan-back range as a possible
    last_touch_idx/last_touch_price -- not just the nearest one. The actual swing point isn't a
    fixed-lookback rule; it's whatever the regression channel's band happened to sit on, which is
    purely market-determined. So this function only proposes candidates (any local high/low,
    however minor); reconstruct_regression_channel() is what actually validates each one by
    checking whether a real channel fit lands its band on that exact wick. The candidate whose
    channel-fit error is lowest is the one most likely to be the genuine touch point.

    direction: "SELL" -> upper break (swing HIGH, entry candle closes UP through touch price)
               "BUY"  -> lower break (swing LOW,  entry candle closes DOWN through touch price)

    Returns a list of (swing_idx, touch_price) tuples, nearest-to-entry first.
    """
    lo = max(swing_lookback, entry_idx - max_scan_back)
    candidates = []
    for j in range(entry_idx - 1, lo - 1, -1):
        left = window.iloc[max(0, j - swing_lookback): j]
        right = window.iloc[j + 1: j + 1 + swing_lookback]
        if len(left) == 0 or len(right) == 0:
            continue
        if direction == "SELL":
            is_swing = (window['high'].iloc[j] >= left['high'].max()
                        and window['high'].iloc[j] >= right['high'].max())
            if is_swing:
                bullish = window['close'].iloc[j] > window['open'].iloc[j]
                touch_price = window['close'].iloc[j] if bullish else window['open'].iloc[j]
                candidates.append((j, float(touch_price)))
        else:  # BUY
            is_swing = (window['low'].iloc[j] <= left['low'].min()
                        and window['low'].iloc[j] <= right['low'].min())
            if is_swing:
                bearish = window['close'].iloc[j] < window['open'].iloc[j]
                touch_price = window['close'].iloc[j] if bearish else window['open'].iloc[j]
                candidates.append((j, float(touch_price)))
    return candidates


def _fit_regression(closes: np.ndarray):
    """Linear regression on close price, returns (model, residual_std)."""
    X = np.arange(len(closes)).reshape(-1, 1)
    model = LinearRegression().fit(X, closes)
    resid = closes - model.predict(X)
    return model, float(np.std(resid))


def reconstruct_regression_channel(window: pd.DataFrame, swing_idx: int, swing_price: float,
                                    direction: str, tf_str: str,
                                    creation_offset_range=CHANNEL_CREATION_OFFSET_RANGE,
                                    upper_mult=CHANNEL_UPPER_STD_MULT,
                                    lower_mult=CHANNEL_LOWER_STD_MULT):
    """
    Searches over num_bars candidates (the bot's real per-timeframe list) and channel-creation
    end-points for the regression fit whose extrapolated band lands on `swing_price` at
    `swing_idx`. Returns the best match as a dict, or None if no valid window could be fit.

    The 'creation_end' is the bar index (within `window`) where detect_regression_channel's
    analysis_df would have ended (analysis_df = df.iloc[:-10] of whatever slice was fetched at
    creation time) -- i.e. analysis spans [creation_end - num_bars, creation_end - 10], with the
    full channel then extrapolated forward through creation_end and beyond via update_channel_data.
    Since we don't know exactly when the channel was created relative to the swing point, we try
    every creation_end within `creation_offset_range` bars either side of swing_idx.
    """
    num_bars_candidates = CHANNEL_NUM_BARS_BY_TF.get(tf_str, [40, 50, 60, 70, 80])
    target_band = "upper" if direction == "SELL" else "lower"
    band_key = "high" if direction == "SELL" else "low"

    lo_bound = max(0, swing_idx - creation_offset_range)
    hi_bound = min(len(window) - 1, swing_idx + creation_offset_range)

    best = None
    for num_bars in num_bars_candidates:
        for creation_end in range(hi_bound, lo_bound - 1, -1):
            analysis_end = creation_end - 10
            start = analysis_end - num_bars
            if start < 0 or analysis_end <= start + 10:
                continue

            analysis_closes = window['close'].iloc[start:analysis_end].values
            if len(analysis_closes) < 10:
                continue
            model, std = _fit_regression(analysis_closes)

            full_len = creation_end - start
            if full_len <= 0 or start + full_len > len(window):
                continue
            X_full = np.arange(full_len).reshape(-1, 1)
            trend_full = model.predict(X_full)
            upper_full = trend_full + upper_mult * std
            lower_full = trend_full - lower_mult * std

            touch_pos = swing_idx - start
            if touch_pos < 0 or touch_pos >= full_len:
                continue

            band_val = upper_full[touch_pos] if target_band == "upper" else lower_full[touch_pos]
            actual_wick = window[band_key].iloc[swing_idx]
            error = abs(actual_wick - band_val)

            candidate = {
                'num_bars': num_bars, 'start': start, 'analysis_end': analysis_end,
                'creation_end': creation_end, 'model': model, 'std': std, 'error': error,
            }
            if best is None or error < best['error']:
                best = candidate

    if best is None:
        return None

    # Build full trend/upper/lower arrays spanning the whole `window` (clipped to what the
    # fit can legitimately cover: from the analysis start onward) for feature extraction
    # and charting.
    start = best['start']
    span = len(window) - start
    X_span = np.arange(span).reshape(-1, 1)
    trend_span = best['model'].predict(X_span)
    upper_span = trend_span + upper_mult * best['std']
    lower_span = trend_span - lower_mult * best['std']

    trend_full = np.full(len(window), np.nan)
    upper_full = np.full(len(window), np.nan)
    lower_full = np.full(len(window), np.nan)
    trend_full[start:] = trend_span
    upper_full[start:] = upper_span
    lower_full[start:] = lower_span

    analysis_window = window.iloc[start: best['analysis_end']]
    upper_touch_count = int((analysis_window['high'].values >=
                              upper_full[start: best['analysis_end']]).sum())
    lower_touch_count = int((analysis_window['low'].values <=
                              lower_full[start: best['analysis_end']]).sum())
    touch_rule_passes = (upper_touch_count >= 2 and lower_touch_count >= 1) or \
                         (upper_touch_count >= 1 and lower_touch_count >= 2)

    return {
        'num_bars': best['num_bars'],
        'creation_end': best['creation_end'],
        'analysis_start': start,
        'analysis_end': best['analysis_end'],
        'slope': float(best['model'].coef_[0]),
        'std': best['std'],
        'match_error': float(best['error']),
        'upper_touch_count': upper_touch_count,
        'lower_touch_count': lower_touch_count,
        'touch_rule_passes': touch_rule_passes,
        'trend': trend_full,
        'upper': upper_full,
        'lower': lower_full,
    }


def get_channel_match_quality(channel: dict, window: pd.DataFrame, swing_idx: int) -> str:
    """Flags a reconstructed channel as 'exact', 'approximate', or 'unreliable' based on how
    close the band match was relative to local ATR, and whether the touch-count rule passes."""
    if channel is None:
        return 'failed'
    atr_at_swing = window['atr_14'].iloc[swing_idx] if 'atr_14' in window.columns else np.nan
    if pd.isna(atr_at_swing) or atr_at_swing == 0:
        tolerance = 1e-6
    else:
        tolerance = atr_at_swing * CHANNEL_MATCH_TOLERANCE_ATR_FRAC

    if channel['match_error'] <= tolerance and channel['touch_rule_passes']:
        return 'exact'
    elif channel['match_error'] <= tolerance * 4:
        return 'approximate'
    else:
        return 'unreliable'


def reconstruct_channel_for_trade(window: pd.DataFrame, entry_idx: int, direction: str, tf_str: str):
    """
    Full pipeline for one trade: generate every plausible swing/touch candidate near entry,
    search for the best-fitting regression channel for EACH, and keep whichever
    (candidate, channel) pair has the lowest price-match error overall. The swing point is
    market-determined (not a fixed lookback), so the channel-fit quality is what actually
    decides which candidate was the real touch point -- a genuine touch should let some
    num_bars/creation-point combination land the band almost exactly on the wick; a stray
    minor peak generally won't, across every combination tried.

    Returns a flat dict of channel-derived features ready to merge into the entry/swing
    summary, or None if no swing candidates were found at all.
    """
    candidates = find_swing_candidates(window, entry_idx, direction)
    if not candidates:
        return None

    best_swing_idx = None
    best_swing_price = None
    best_channel = None
    best_score = np.inf

    for swing_idx, swing_price in candidates:
        channel = reconstruct_regression_channel(window, swing_idx, swing_price, direction, tf_str)
        if channel is None:
            continue
        atr_at_swing = window['atr_14'].iloc[swing_idx] if 'atr_14' in window.columns else np.nan
        tolerance = atr_at_swing if pd.notna(atr_at_swing) and atr_at_swing > 0 else 1e-6
        score = channel['match_error'] / tolerance  # normalized so candidates are comparable
        if score < best_score:
            best_score = score
            best_swing_idx = swing_idx
            best_swing_price = swing_price
            best_channel = channel

    if best_channel is None:
        return {'Channel_Match_Quality': 'failed', 'Channel_Swing_Idx': None, 'Channel_Swing_Price': None}

    swing_idx, swing_price, channel = best_swing_idx, best_swing_price, best_channel
    quality = get_channel_match_quality(channel, window, swing_idx)

    entry_trend = channel['trend'][entry_idx] if entry_idx < len(channel['trend']) else np.nan
    entry_upper = channel['upper'][entry_idx] if entry_idx < len(channel['upper']) else np.nan
    entry_lower = channel['lower'][entry_idx] if entry_idx < len(channel['lower']) else np.nan
    band_width = entry_upper - entry_lower if pd.notna(entry_upper) and pd.notna(entry_lower) else np.nan
    entry_close = window['close'].iloc[entry_idx]
    # Where entry sits inside the band: 0 = on lower band, 1 = on upper band
    entry_pos_in_band = ((entry_close - entry_lower) / band_width) if band_width and not np.isnan(band_width) and band_width != 0 else np.nan

    return {
        'Channel_Match_Quality': quality,
        'Channel_Match_Error': channel['match_error'],
        'Channel_Candidates_Evaluated': len(candidates),
        'Channel_Num_Bars': channel['num_bars'],
        'Channel_Swing_Idx': swing_idx,
        'Channel_Swing_Price': swing_price,
        'Channel_Slope': channel['slope'],
        'Channel_Std_Dev': channel['std'],
        'Channel_Upper_Touch_Count': channel['upper_touch_count'],
        'Channel_Lower_Touch_Count': channel['lower_touch_count'],
        'Channel_Touch_Rule_Passes': channel['touch_rule_passes'],
        'Channel_Trend_At_Entry': entry_trend,
        'Channel_Upper_At_Entry': entry_upper,
        'Channel_Lower_At_Entry': entry_lower,
        'Channel_Band_Width_At_Entry': band_width,
        'Channel_Entry_Position_In_Band': entry_pos_in_band,  # 0=lower band, 1=upper band
        'Channel_Upper_Deviation': channel['std'] * CHANNEL_UPPER_STD_MULT,
        'Channel_Lower_Deviation': channel['std'] * CHANNEL_LOWER_STD_MULT,
        '_channel_trend_arr': channel['trend'],
        '_channel_upper_arr': channel['upper'],
        '_channel_lower_arr': channel['lower'],
    }


def build_candle_context_dataset(df: pd.DataFrame, lookback=CANDLE_CONTEXT_LOOKBACK,
                                  keep_windows_for_charts=CANDLE_CONTEXT_MAX_CHARTS):
    """
    For every completed trade, pulls its candle window, tags the entry candle (bot's signal/
    breakout candle), the trigger candle (the candle that actually filled the trade -- same as
    entry+1 for INSTANT, possibly much later for PENDING), every candle in between, and the swing
    candle, then stacks everything into one long-format dataframe (one row per candle per trade).
    Also returns a dict of the raw per-trade windows (capped at `keep_windows_for_charts`) for
    chart generation.
    """
    completed = df[df['Trade Type'] == 'COMPLETED'].copy().reset_index(drop=True)
    if completed.empty:
        print("No completed trades available for candle-context analysis")
        return pd.DataFrame(), {}

    rows = []
    channel_records = []
    chart_windows = {}
    total = len(completed)

    for trade_id, trade in completed.iterrows():
        symbol = trade['Symbol']
        tf_str = trade['Timeframe']
        signal_time = trade.get('Signal Time')
        trigger_time = trade['Entry Time']
        if pd.isna(signal_time) or pd.isna(trigger_time):
            continue

        window, entry_idx, trigger_idx, swing_idx = get_trade_candle_context(
            symbol, tf_str, signal_time, trigger_time, lookback=lookback)
        if window is None:
            continue

        # Channel reconstruction needs its OWN, much wider window (a regression channel can be
        # fit on up to 100 bars of history -- far more than the CANDLE_CONTEXT_LOOKBACK display
        # window holds), so it's fetched separately and aligned back to `window` by timestamp.
        channel_feats = None
        if ENABLE_CHANNEL_RECONSTRUCTION:
            try:
                channel_window, channel_entry_idx = get_channel_reconstruction_window(symbol, tf_str, signal_time)
                if channel_window is not None and channel_entry_idx is not None and channel_entry_idx >= 1:
                    channel_feats = reconstruct_channel_for_trade(
                        channel_window, channel_entry_idx, trade.get('Direction'), tf_str)
                    if channel_feats is not None:
                        # Re-express the swing index as a TIMESTAMP so it can be matched into
                        # `window` (a differently-offset/sized index space) further down.
                        c_swing_idx = channel_feats.get('Channel_Swing_Idx')
                        channel_feats['Channel_Swing_Time'] = (
                            channel_window['time'].iloc[c_swing_idx] if c_swing_idx is not None else None
                        )
                        channel_feats['_channel_window_times'] = channel_window['time'].values
            except Exception as e:
                print(f"⚠️ Channel reconstruction failed for trade {trade_id}: {e}")
                channel_feats = None
        if channel_feats is not None:
            record = {'Trade_ID': trade_id}
            record.update({k: v for k, v in channel_feats.items() if not k.startswith('_')})
            channel_records.append(record)

        # Build a time -> array-position lookup for the channel window (if reconstruction
        # succeeded) so each display-window candle can pull its corresponding channel band
        # value by matching timestamps, regardless of the two windows' differing offsets.
        channel_time_to_pos = {}
        if channel_feats is not None and channel_feats.get('_channel_window_times') is not None:
            channel_time_to_pos = {t: pos for pos, t in enumerate(channel_feats['_channel_window_times'])}

        for i, candle in window.iterrows():
            candle_time = candle['time']
            is_channel_swing = (channel_feats is not None
                                 and channel_feats.get('Channel_Swing_Time') is not None
                                 and candle_time == channel_feats['Channel_Swing_Time'])
            row = {
                'Trade_ID': trade_id,
                'Position_ID': trade.get('Position ID'),
                'Symbol': symbol,
                'Timeframe': tf_str,
                'Direction': trade.get('Direction'),
                'Order_Type': trade.get('Order Type'),
                'Outcome': trade.get('Outcome'),
                'Profit': trade.get('Profit'),
                'Candle_Offset': i - entry_idx,
                'time': candle_time,
                'Is_Entry_Candle': (i == entry_idx),
                'Is_Trigger_Candle': (i == trigger_idx),
                'Is_Between_Entry_And_Trigger': (entry_idx < i < trigger_idx),
                'Is_Swing_Candle': (swing_idx is not None and i == swing_idx),
                'Is_Channel_Swing_Candle': is_channel_swing,
            }
            for col in CANDLE_SNAPSHOT_COLS:
                row[col] = candle.get(col)
            if channel_feats is not None:
                upper_arr = channel_feats.get('_channel_upper_arr')
                lower_arr = channel_feats.get('_channel_lower_arr')
                trend_arr = channel_feats.get('_channel_trend_arr')
                pos = channel_time_to_pos.get(candle_time)
                row['Channel_Upper'] = upper_arr[pos] if (upper_arr is not None and pos is not None and pos < len(upper_arr)) else np.nan
                row['Channel_Lower'] = lower_arr[pos] if (lower_arr is not None and pos is not None and pos < len(lower_arr)) else np.nan
                row['Channel_Trend'] = trend_arr[pos] if (trend_arr is not None and pos is not None and pos < len(trend_arr)) else np.nan
            rows.append(row)

        if keep_windows_for_charts is None or len(chart_windows) < keep_windows_for_charts:
            # For charting we align the channel arrays onto `window`'s own index space (same
            # timestamp-matching approach) so the chart function can plot them directly
            # alongside the display window's candles without needing the wider channel window.
            chart_channel_upper = chart_channel_lower = chart_channel_trend = None
            chart_channel_swing_idx = None
            if channel_feats is not None and channel_time_to_pos:
                upper_arr = channel_feats.get('_channel_upper_arr')
                lower_arr = channel_feats.get('_channel_lower_arr')
                trend_arr = channel_feats.get('_channel_trend_arr')
                chart_channel_upper = np.full(len(window), np.nan)
                chart_channel_lower = np.full(len(window), np.nan)
                chart_channel_trend = np.full(len(window), np.nan)
                for wi, t in enumerate(window['time'].values):
                    pos = channel_time_to_pos.get(t)
                    if pos is not None:
                        if upper_arr is not None and pos < len(upper_arr):
                            chart_channel_upper[wi] = upper_arr[pos]
                        if lower_arr is not None and pos < len(lower_arr):
                            chart_channel_lower[wi] = lower_arr[pos]
                        if trend_arr is not None and pos < len(trend_arr):
                            chart_channel_trend[wi] = trend_arr[pos]
                swing_time = channel_feats.get('Channel_Swing_Time')
                if swing_time is not None:
                    swing_matches = np.where(window['time'].values == swing_time)[0]
                    chart_channel_swing_idx = int(swing_matches[0]) if len(swing_matches) else None

            chart_windows[trade_id] = {
                'window': window, 'entry_idx': entry_idx, 'trigger_idx': trigger_idx,
                'swing_idx': swing_idx, 'symbol': symbol, 'tf_str': tf_str,
                'outcome': trade.get('Outcome'),
                'channel_swing_idx': chart_channel_swing_idx,
                'channel_upper_arr': chart_channel_upper,
                'channel_lower_arr': chart_channel_lower,
                'channel_trend_arr': chart_channel_trend,
                'channel_match_quality': channel_feats.get('Channel_Match_Quality') if channel_feats else None,
            }

        if (trade_id + 1) % 25 == 0:
            print(f"  Candle-context processed {trade_id + 1}/{total} trades...")

    context_df = pd.DataFrame(rows)
    channel_df = pd.DataFrame(channel_records)
    n_trades = context_df['Trade_ID'].nunique() if not context_df.empty else 0
    print(f"Candle-context dataset built: {len(context_df)} candle rows across {n_trades} trades")
    if not channel_df.empty:
        quality_counts = channel_df['Channel_Match_Quality'].value_counts().to_dict()
        print(f"Channel reconstruction quality breakdown: {quality_counts}")
    return context_df, chart_windows, channel_df


def build_entry_swing_summary(context_df: pd.DataFrame, channel_df: pd.DataFrame = None) -> pd.DataFrame:
    """Collapses the long-format candle context into one row per trade: entry-candle snapshot,
    trigger-candle snapshot, swing-candle snapshot, aggregate stats over every candle that sat
    between entry and trigger (the gap that only exists for PENDING orders -- for INSTANT trades
    this gap is empty since trigger_idx == entry_idx + 1), and the reconstructed regression
    channel's features at entry (slope, band width, touch counts, deviations, match quality)."""
    if context_df.empty:
        return pd.DataFrame()

    summaries = []
    for trade_id, group in context_df.groupby('Trade_ID'):
        entry_rows = group[group['Is_Entry_Candle']]
        if entry_rows.empty:
            continue
        entry_row = entry_rows.iloc[0]
        base = group.iloc[0]

        record = {
            'Trade_ID': trade_id,
            'Symbol': base['Symbol'],
            'Timeframe': base['Timeframe'],
            'Direction': base['Direction'],
            'Order_Type': base['Order_Type'],
            'Outcome': base['Outcome'],
            'Profit': base['Profit'],
        }
        for col in CANDLE_SNAPSHOT_COLS:
            record[f'Entry_{col}'] = entry_row.get(col)

        trigger_rows = group[group['Is_Trigger_Candle']]
        if not trigger_rows.empty:
            trigger_row = trigger_rows.iloc[0]
            for col in CANDLE_SNAPSHOT_COLS:
                record[f'Trigger_{col}'] = trigger_row.get(col)
            record['Candles_Between_Entry_And_Trigger'] = trigger_row['Candle_Offset']
        else:
            for col in CANDLE_SNAPSHOT_COLS:
                record[f'Trigger_{col}'] = None
            record['Candles_Between_Entry_And_Trigger'] = None

        # Aggregate indicator stats over the candles strictly between entry and trigger
        # (e.g. a PENDING order resting for several bars before it's hit). Empty for
        # INSTANT trades, where there is no gap.
        between_rows = group[group['Is_Between_Entry_And_Trigger']]
        record['N_Candles_Between_Entry_And_Trigger'] = len(between_rows)
        for col in CANDLE_SNAPSHOT_COLS:
            vals = pd.to_numeric(between_rows[col], errors='coerce').dropna()
            record[f'Between_{col}_Mean'] = vals.mean() if len(vals) else None
            record[f'Between_{col}_Max'] = vals.max() if len(vals) else None
            record[f'Between_{col}_Min'] = vals.min() if len(vals) else None

        swing_rows = group[group['Is_Swing_Candle']]
        if not swing_rows.empty:
            swing_row = swing_rows.iloc[0]
            for col in CANDLE_SNAPSHOT_COLS:
                record[f'Swing_{col}'] = swing_row.get(col)
            record['Candles_Between_Swing_And_Entry'] = abs(swing_row['Candle_Offset'])
        else:
            for col in CANDLE_SNAPSHOT_COLS:
                record[f'Swing_{col}'] = None
            record['Candles_Between_Swing_And_Entry'] = None

        summaries.append(record)

    summary_df = pd.DataFrame(summaries)

    if channel_df is not None and not channel_df.empty and not summary_df.empty:
        summary_df = summary_df.merge(channel_df, on='Trade_ID', how='left')

    return summary_df


def find_winner_indicator_patterns(entry_swing_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compares entry/swing-candle indicator values between WINNER and LOSER trades to surface which
    indicators differ most consistently for winners (Cohen's d) and how tightly winners cluster
    together on each one (lower coefficient-of-variation = more similar/repeatable behaviour).
    """
    if entry_swing_df.empty:
        return pd.DataFrame()

    feature_cols = [c for c in entry_swing_df.columns
                    if c.startswith('Entry_') or c.startswith('Swing_')
                    or c.startswith('Trigger_') or c.startswith('Between_')
                    or c.startswith('Channel_')]
    for extra_col in ('Candles_Between_Swing_And_Entry', 'Candles_Between_Entry_And_Trigger',
                      'N_Candles_Between_Entry_And_Trigger'):
        if extra_col in entry_swing_df.columns:
            feature_cols.append(extra_col)

    # Channel_Match_Quality is categorical and Channel_Touch_Rule_Passes is boolean -- exclude
    # the former from numeric comparison (it's surfaced separately, see below) and coerce the
    # latter to 0/1 so it can still be compared like the other numeric features.
    feature_cols = [c for c in feature_cols if c != 'Channel_Match_Quality']
    if 'Channel_Touch_Rule_Passes' in entry_swing_df.columns:
        entry_swing_df = entry_swing_df.copy()
        entry_swing_df['Channel_Touch_Rule_Passes'] = entry_swing_df['Channel_Touch_Rule_Passes'].astype(float)

    winners = entry_swing_df[entry_swing_df['Outcome'] == 'WINNER']
    losers = entry_swing_df[entry_swing_df['Outcome'] == 'LOSER']
    breakeven = entry_swing_df[entry_swing_df['Outcome'] == 'BREAKEVEN']

    records = []
    for col in feature_cols:
        w = pd.to_numeric(winners[col], errors='coerce').dropna()
        l = pd.to_numeric(losers[col], errors='coerce').dropna()
        b = pd.to_numeric(breakeven[col], errors='coerce').dropna() if not breakeven.empty else pd.Series(dtype=float)

        if len(w) < 3 or len(l) < 3:
            continue

        w_mean, w_std = w.mean(), w.std()
        l_mean, l_std = l.mean(), l.std()

        dof = len(w) + len(l) - 2
        pooled_std = np.sqrt(((len(w) - 1) * w_std ** 2 + (len(l) - 1) * l_std ** 2) / dof) if dof > 0 else np.nan
        cohens_d = (w_mean - l_mean) / pooled_std if pooled_std and pooled_std > 0 else np.nan
        winner_cv = (w_std / abs(w_mean)) if w_mean not in (0, None) and not pd.isna(w_mean) else np.nan

        records.append({
            'Indicator': col,
            'Winners_N': len(w),
            'Winners_Mean': round(w_mean, 4),
            'Winners_Std': round(w_std, 4),
            'Losers_N': len(l),
            'Losers_Mean': round(l_mean, 4),
            'Losers_Std': round(l_std, 4),
            'Breakeven_Mean': round(b.mean(), 4) if len(b) else None,
            'Mean_Difference': round(w_mean - l_mean, 4),
            'Effect_Size_CohensD': round(cohens_d, 3) if pd.notna(cohens_d) else None,
            'Winner_Consistency_CV': round(winner_cv, 3) if pd.notna(winner_cv) else None,
            'Higher_In': 'Winners' if w_mean > l_mean else 'Losers',
        })

    patterns_df = pd.DataFrame(records)
    if not patterns_df.empty:
        patterns_df['Abs_Effect_Size'] = patterns_df['Effect_Size_CohensD'].abs()
        patterns_df = patterns_df.sort_values('Abs_Effect_Size', ascending=False) \
                                  .drop(columns='Abs_Effect_Size').reset_index(drop=True)
    return patterns_df


def build_channel_match_quality_breakdown(entry_swing_df: pd.DataFrame) -> pd.DataFrame:
    """Cross-tab of reconstructed-channel match quality ('exact' / 'approximate' / 'unreliable'
    / 'failed') against trade outcome -- a sanity check on how trustworthy the channel features
    are, and whether reconstruction confidence itself correlates with winning."""
    if entry_swing_df.empty or 'Channel_Match_Quality' not in entry_swing_df.columns:
        return pd.DataFrame()

    tab = pd.crosstab(entry_swing_df['Channel_Match_Quality'], entry_swing_df['Outcome'])
    tab['Total'] = tab.sum(axis=1)
    tab['Pct_of_All_Trades'] = (tab['Total'] / tab['Total'].sum() * 100).round(1)
    return tab.reset_index()


def plot_trade_candle_highlight(window_df, entry_idx, trigger_idx, swing_idx, symbol, tf_str,
                                 trade_id, outcome, save_path, channel_upper_arr=None,
                                 channel_lower_arr=None, channel_trend_arr=None,
                                 channel_swing_idx=None, channel_match_quality=None):
    """Renders the candle window with the entry/signal candle (▲), the trigger/fill candle (●),
    the swing candle (▼), and -- when available -- the reconstructed regression channel
    (upper/lower bands + trend line, dashed if the match was only 'approximate')."""
    try:
        plot_df = window_df.copy().set_index('time')[['open', 'high', 'low', 'close', 'volume']]

        apds = []
        entry_marker = pd.Series(index=plot_df.index, dtype='float64')
        entry_marker.iloc[entry_idx] = plot_df['low'].iloc[entry_idx] * 0.999
        apds.append(mpf.make_addplot(entry_marker, type='scatter', markersize=140, marker='^', color='lime'))

        if trigger_idx is not None and trigger_idx != entry_idx:
            trigger_marker = pd.Series(index=plot_df.index, dtype='float64')
            trigger_marker.iloc[trigger_idx] = plot_df['low'].iloc[trigger_idx] * 0.999
            apds.append(mpf.make_addplot(trigger_marker, type='scatter', markersize=140, marker='o', color='blue'))

        if swing_idx is not None:
            swing_marker = pd.Series(index=plot_df.index, dtype='float64')
            swing_marker.iloc[swing_idx] = plot_df['high'].iloc[swing_idx] * 1.001
            apds.append(mpf.make_addplot(swing_marker, type='scatter', markersize=140, marker='v', color='magenta'))

        channel_note = ""
        if channel_upper_arr is not None and channel_lower_arr is not None:
            n = len(plot_df)
            linestyle = '--' if channel_match_quality == 'approximate' else '-'
            upper_series = pd.Series(channel_upper_arr[:n], index=plot_df.index[:len(channel_upper_arr[:n])])
            lower_series = pd.Series(channel_lower_arr[:n], index=plot_df.index[:len(channel_lower_arr[:n])])
            apds.append(mpf.make_addplot(upper_series, color='orange', linestyle=linestyle, width=1.2))
            apds.append(mpf.make_addplot(lower_series, color='orange', linestyle=linestyle, width=1.2))
            if channel_trend_arr is not None:
                trend_series = pd.Series(channel_trend_arr[:n], index=plot_df.index[:len(channel_trend_arr[:n])])
                apds.append(mpf.make_addplot(trend_series, color='gray', linestyle=':', width=0.8))
            if channel_swing_idx is not None:
                cs_marker = pd.Series(index=plot_df.index, dtype='float64')
                cs_marker.iloc[channel_swing_idx] = plot_df['high'].iloc[channel_swing_idx] * 1.002
                apds.append(mpf.make_addplot(cs_marker, type='scatter', markersize=100, marker='*', color='orange'))
            quality_label = channel_match_quality or 'unknown'
            channel_note = f"   ◆ channel band (orange, {quality_label} match"

        outcome_label = outcome if outcome else 'UNKNOWN'
        fig, axes = mpf.plot(
            plot_df, type='candle', style='yahoo',
            title=f"{symbol} {tf_str} | Trade #{trade_id} | {outcome_label}\n"
                  f"(▲ entry/signal candle   ● trigger/fill candle   ▼ swing candle{channel_note})",
            ylabel='Price', addplot=apds, volume=True, figsize=(12, 8), returnfig=True
        )
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        return True
    except Exception as e:
        print(f"⚠️ Could not plot candle highlight for trade {trade_id}: {e}")
        return False


def generate_candle_context_charts(chart_windows: dict, output_folder: str):
    """Saves a highlighted candlestick chart for each trade kept in `chart_windows`."""
    if not chart_windows:
        return
    charts_folder = os.path.join(output_folder, "visualizations", "candle_context")
    os.makedirs(charts_folder, exist_ok=True)

    saved = 0
    for trade_id, info in chart_windows.items():
        safe_symbol = str(info['symbol']).replace(' ', '_').replace('/', '_')
        filename = f"trade_{trade_id}_{safe_symbol}_{info['tf_str']}_{info['outcome']}.png"
        save_path = os.path.join(charts_folder, filename)
        if plot_trade_candle_highlight(info['window'], info['entry_idx'], info['trigger_idx'],
                                        info['swing_idx'], info['symbol'], info['tf_str'],
                                        trade_id, info['outcome'], save_path,
                                        channel_upper_arr=info.get('channel_upper_arr'),
                                        channel_lower_arr=info.get('channel_lower_arr'),
                                        channel_trend_arr=info.get('channel_trend_arr'),
                                        channel_swing_idx=info.get('channel_swing_idx'),
                                        channel_match_quality=info.get('channel_match_quality')):
            saved += 1

    print(f"Saved {saved} candle-context highlight charts to {charts_folder}")


def save_candle_context_excel_report(context_df: pd.DataFrame, entry_swing_df: pd.DataFrame,
                                      patterns_df: pd.DataFrame, channel_quality_df: pd.DataFrame = None):
    """Writes the per-candle dataset, the per-trade entry/swing snapshot, the winner-vs-loser
    indicator comparison (including reconstructed regression-channel features), and the channel
    match-quality breakdown to their own workbook."""
    if context_df.empty:
        print("No candle-context data to save")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = os.path.join(OUTPUT_FOLDER, f"Candle_Context_Analysis_{timestamp}.xlsx")

    try:
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            context_df.to_excel(writer, sheet_name="Trade_Candle_Context", index=False)
            if not entry_swing_df.empty:
                entry_swing_df.to_excel(writer, sheet_name="Entry_Swing_Indicators", index=False)
            if not patterns_df.empty:
                patterns_df.to_excel(writer, sheet_name="Winner_Indicator_Patterns", index=False)
            if channel_quality_df is not None and not channel_quality_df.empty:
                channel_quality_df.to_excel(writer, sheet_name="Channel_Match_Quality", index=False)
            if not entry_swing_df.empty:
                channel_cols = ['Trade_ID', 'Symbol', 'Timeframe', 'Direction', 'Outcome', 'Profit'] + \
                                [c for c in entry_swing_df.columns if c.startswith('Channel_')]
                channel_cols = [c for c in channel_cols if c in entry_swing_df.columns]
                if len(channel_cols) > 6:
                    entry_swing_df[channel_cols].to_excel(writer, sheet_name="Channel_Reconstruction", index=False)

            header_font = Font(bold=True, color="FFFFFF", size=12)
            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            thin_border = Border(left=Side(style='thin'), right=Side(style='thin'),
                                  top=Side(style='thin'), bottom=Side(style='thin'))

            for sheet_name in writer.sheets:
                ws = writer.sheets[sheet_name]
                for cell in ws[1]:
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.alignment = Alignment(horizontal="center", vertical="center")

                for col in ws.columns:
                    max_length = 0
                    column = col[0].column_letter
                    for cell in col:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except Exception:
                            pass
                    ws.column_dimensions[column].width = min(max_length + 2, 50)

                for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
                    for cell in row:
                        cell.border = thin_border

        print(f"Candle-context analysis report saved: {filename}")
    except Exception as e:
        print(f"Error saving candle-context Excel report: {e}")
        import traceback
        traceback.print_exc()


def run_candle_context_analysis(df: pd.DataFrame):
    """Orchestrates the full candle-context workflow: build dataset (incl. regression-channel
    reconstruction) -> summarise -> compare winners vs losers -> save Excel report -> save
    highlighted charts."""
    if not ENABLE_CANDLE_CONTEXT_ANALYSIS:
        return

    print("\n🔬 Running candle-context analysis on completed trades...")
    context_df, chart_windows, channel_df = build_candle_context_dataset(
        df, lookback=CANDLE_CONTEXT_LOOKBACK, keep_windows_for_charts=CANDLE_CONTEXT_MAX_CHARTS
    )
    if context_df.empty:
        print("⚠️ No candle-context data generated (no MT5 history available for trade entry times?)")
        return

    entry_swing_df = build_entry_swing_summary(context_df, channel_df)
    patterns_df = find_winner_indicator_patterns(entry_swing_df)
    channel_quality_df = build_channel_match_quality_breakdown(entry_swing_df)

    save_candle_context_excel_report(context_df, entry_swing_df, patterns_df, channel_quality_df)
    generate_candle_context_charts(chart_windows, OUTPUT_FOLDER)

    if not patterns_df.empty:
        print("\n🏆 Indicators most associated with WINNING trades (top 10 by effect size):")
        for _, row in patterns_df.head(10).iterrows():
            print(f"   {row['Indicator']}: Winners={row['Winners_Mean']} vs Losers={row['Losers_Mean']} "
                  f"(Cohen's d={row['Effect_Size_CohensD']}, stronger in {row['Higher_In']})")

    if not channel_quality_df.empty:
        print("\n📐 Regression channel reconstruction quality breakdown:")
        for _, row in channel_quality_df.iterrows():
            print(f"   {row['Channel_Match_Quality']}: {row['Total']} trades ({row['Pct_of_All_Trades']}%)")

def build_outcome_eval_sheet(completed_trades: pd.DataFrame, group_cols: list) -> pd.DataFrame:
    """
    Builds a Winners / Losers / Breakeven / win-rate evaluation table grouped by `group_cols`
    (e.g. ['Symbol'], ['Symbol', 'Timeframe'], ['Symbol', 'Direction']).
    """
    def eval_stats(group):
        winners = (group['Outcome'] == 'WINNER').sum()
        losers = (group['Outcome'] == 'LOSER').sum()
        breakeven = (group['Outcome'] == 'BREAKEVEN').sum()
        total = len(group)
        total_excl_be = winners + losers
        win_pct_incl_be = (winners / total * 100) if total > 0 else 0
        win_pct_excl_be = (winners / total_excl_be * 100) if total_excl_be > 0 else 0

        return pd.Series({
            'Winners': int(winners),
            'Losers': int(losers),
            'Breakeven': int(breakeven),
            'Total_Trades': int(total),
            'Win_Rate_Incl_BE_%': round(win_pct_incl_be, 1),
            'Win_Rate_Excl_BE_%': round(win_pct_excl_be, 1),
        })

    result = completed_trades.groupby(group_cols, as_index=False).apply(eval_stats, include_groups=False)
    sort_ascending = [True] * len(group_cols) + [False]
    result = result.sort_values(by=group_cols + ['Winners'], ascending=sort_ascending).reset_index(drop=True)
    return result


def generate_comprehensive_report(df: pd.DataFrame):
    """Generate comprehensive analysis report and save to TXT file"""
    if df.empty:
        print("No data for report generation")
        return
    
    # Separate data by type
    pending_orders = df[df['Trade Type'] == 'PENDING_ORDER']
    completed_trades = df[df['Trade Type'] == 'COMPLETED']
    
    print(f"\n{'='*80}")
    print("🎯 COMPREHENSIVE TRADING BOT ANALYSIS REPORT")
    print(f"{'='*80}")
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_lines = []
    report_lines.append("="*80)
    report_lines.append("🎯 COMPREHENSIVE TRADING BOT ANALYSIS REPORT")
    report_lines.append(f"Generated on: {timestamp}")
    report_lines.append("="*80)
    report_lines.append("")
    
    # 1. PENDING ORDER ANALYSIS
    if not pending_orders.empty:
        print(f"\n📊 PENDING ORDER ANALYSIS ({len(pending_orders)} orders)")
        print(f"{'-'*60}")
        
        report_lines.append(f"📊 PENDING ORDER ANALYSIS ({len(pending_orders)} orders)")
        report_lines.append("-"*60)
        
        missed_opps = pending_orders[pending_orders['Missed Opportunity'] == True]
        missed_by_symbol_tf = missed_opps.groupby(['Symbol', 'Timeframe']).size().reset_index(name='Missed Count')
        missed_by_symbol_tf = missed_by_symbol_tf.sort_values('Missed Count', ascending=False)
        
        print(f"📈 Missed Opportunities (TP1 hit but no entry): {len(missed_opps)}")
        if not missed_opps.empty:
            print("\nTop missed opportunities:")
            for _, row in missed_by_symbol_tf.head(10).iterrows():
                print(f"   {row['Symbol']} - {row['Timeframe']}: {row['Missed Count']} missed")
        
        exec_stats = pending_orders.groupby(['Symbol', 'Timeframe']).agg({
            'Entry Filled': ['count', 'sum']
        }).reset_index()
        exec_stats.columns = ['Symbol', 'Timeframe', 'Total_Orders', 'Executed_Orders']
        exec_stats['Total_Orders'] = pd.to_numeric(exec_stats['Total_Orders'], errors='coerce')
        exec_stats['Executed_Orders'] = pd.to_numeric(exec_stats['Executed_Orders'], errors='coerce')
        exec_stats['Execution_Rate_%'] = (exec_stats['Executed_Orders'] / exec_stats['Total_Orders'] * 100).round(1)
        exec_stats = exec_stats.sort_values('Execution_Rate_%')
        
        print(f"\n📉 Lowest Execution Rates:")
        for _, row in exec_stats.head(5).iterrows():
            print(f"   {row['Symbol']} - {row['Timeframe']}: {row['Execution_Rate_%']}% ({row['Executed_Orders']:.0f}/{row['Total_Orders']:.0f})")
        
        # Add to report_lines
        report_lines.append(f"📈 Missed Opportunities (TP1 hit but no entry): {len(missed_opps)}")
        if not missed_opps.empty:
            report_lines.append("")
            report_lines.append("Top missed opportunities:")
            for _, row in missed_by_symbol_tf.head(10).iterrows():
                report_lines.append(f"   {row['Symbol']} - {row['Timeframe']}: {row['Missed Count']} missed")
        
        report_lines.append("")
        report_lines.append("📉 Lowest Execution Rates:")
        for _, row in exec_stats.head(5).iterrows():
            report_lines.append(f"   {row['Symbol']} - {row['Timeframe']}: {row['Execution_Rate_%']}% ({row['Executed_Orders']:.0f}/{row['Total_Orders']:.0f})")
    
    # 2. COMPLETED TRADES ANALYSIS
    if not completed_trades.empty:
        print(f"\n💰 COMPLETED TRADES ANALYSIS ({len(completed_trades)} trades)")
        print(f"{'-'*60}")
        
        total_profit = pd.to_numeric(completed_trades['Profit'], errors='coerce').sum()
        win_rate = (completed_trades['Outcome'] == 'WINNER').mean() * 100
        avg_profit = pd.to_numeric(completed_trades['Profit'], errors='coerce').mean()

        trades_without_be = completed_trades[completed_trades['Outcome'] != 'BREAKEVEN']
        win_rate_excluding_be = (trades_without_be['Outcome'] == 'WINNER').mean() * 100 if len(trades_without_be) > 0 else win_rate
        be_count = (completed_trades['Outcome'] == 'BREAKEVEN').sum()
        
        print(f"Total Profit: ${total_profit:.2f}")
        print(f"Win Rate: {win_rate:.1f}%")
        print(f"Win Rate (excluding BE): {win_rate_excluding_be:.1f}%")
        print(f"Breakeven Trades: {be_count}")
        print(f"Average Profit per Trade: ${avg_profit:.2f}")
        
        stfd_performance = completed_trades.groupby(['Symbol', 'Timeframe', 'Direction']).agg({
            'Profit': ['count', 'sum', 'mean'],
        }).round(2)
        
        if not stfd_performance.empty:
            stfd_performance.columns = ['Trade_Count', 'Total_Profit', 'Avg_Profit']
            win_rates = completed_trades.groupby(['Symbol', 'Timeframe', 'Direction'])['Outcome'].apply(
                lambda x: (x == 'WINNER').mean() * 100
            ).round(1)
            stfd_performance['Win_Rate_%'] = win_rates
            stfd_performance = stfd_performance.sort_values('Total_Profit', ascending=False)
            
            print(f"\n🏆 TOP PERFORMING COMBINATIONS:")
            top_combinations = stfd_performance.head(5)
            for idx, stats in top_combinations.iterrows():
                symbol, tf, direction = idx
                print(f"   ✅ {symbol} + {tf} + {direction}: {stats['Win_Rate_%']}% WR, ${stats['Total_Profit']:.2f} profit")
            
            sufficient_trades = stfd_performance[stfd_performance['Trade_Count'] >= 3]
            if not sufficient_trades.empty:
                print(f"\n📉 WORST PERFORMING COMBINATIONS (min 3 trades):")
                worst_combinations = sufficient_trades.tail(5)
                for idx, stats in worst_combinations.iterrows():
                    symbol, tf, direction = idx
                    print(f"   ❌ {symbol} + {tf} + {direction}: {stats['Win_Rate_%']}% WR, ${stats['Total_Profit']:.2f} profit")
        
        # Add to report_lines
        report_lines.append("")
        report_lines.append(f"💰 COMPLETED TRADES ANALYSIS ({len(completed_trades)} trades)")
        report_lines.append("-"*60)
        report_lines.append(f"Total Profit: ${total_profit:.2f}")
        report_lines.append(f"Win Rate: {win_rate:.1f}%")
        report_lines.append(f"Average Profit per Trade: ${avg_profit:.2f}")
        
        if not stfd_performance.empty:
            report_lines.append("")
            report_lines.append("🏆 TOP PERFORMING COMBINATIONS:")
            for idx, stats in top_combinations.iterrows():
                symbol, tf, direction = idx
                report_lines.append(f"   ✅ {symbol} + {tf} + {direction}: {stats['Win_Rate_%']}% WR, ${stats['Total_Profit']:.2f} profit")
            
            if not sufficient_trades.empty:
                report_lines.append("")
                report_lines.append("📉 WORST PERFORMING COMBINATIONS (min 3 trades):")
                for idx, stats in worst_combinations.iterrows():
                    symbol, tf, direction = idx
                    report_lines.append(f"   ❌ {symbol} + {tf} + {direction}: {stats['Win_Rate_%']}% WR, ${stats['Total_Profit']:.2f} profit")
    
    # 3. STRATEGY RECOMMENDATIONS
    print(f"\n🎯 STRATEGY OPTIMIZATION RECOMMENDATIONS")
    print(f"{'-'*60}")
    
    report_lines.append("")
    report_lines.append("🎯 STRATEGY OPTIMIZATION RECOMMENDATIONS")
    report_lines.append("-"*60)
    
    if not pending_orders.empty:
        high_missed = pending_orders[pending_orders['Missed Opportunity'] == True]
        high_missed_grouped = high_missed.groupby(['Symbol', 'Timeframe']).size()
        high_missed_grouped = high_missed_grouped[high_missed_grouped >= 3]
        
        if not high_missed_grouped.empty:
            print("🔔 CONSIDER SWITCHING TO INSTANT ORDERS:")
            report_lines.append("🔔 CONSIDER SWITCHING TO INSTANT ORDERS:")
            for (symbol, timeframe), count in high_missed_grouped.items():
                line = f"   📍 {symbol} on {timeframe}: {count} missed TP1 hits"
                print(line)
                report_lines.append(line)
    
    if not completed_trades.empty:
        losing_trades = completed_trades[completed_trades['Profit'] < 0]
        if not losing_trades.empty:
            avg_loss = pd.to_numeric(losing_trades['Profit'], errors='coerce').mean()
            max_loss = pd.to_numeric(losing_trades['Profit'], errors='coerce').min()
            print(f"📉 Risk Management:")
            print(f"   Average Loss: ${avg_loss:.2f}")
            print(f"   Maximum Loss: ${max_loss:.2f}")
            if max_loss < -100:
                print(f"   ⚠️  Consider tighter SL for large losses")
            
            report_lines.append("")
            report_lines.append("📉 Risk Management:")
            report_lines.append(f"   Average Loss: ${avg_loss:.2f}")
            report_lines.append(f"   Maximum Loss: ${max_loss:.2f}")
            if max_loss < -100:
                report_lines.append(f"   ⚠️  Consider tighter SL for large losses")
    
    # Save the report to TXT file
    txt_filename = os.path.join(OUTPUT_FOLDER, f"Comprehensive_Analysis_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt")
    with open(txt_filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    print(f"\nComprehensive text report saved: {txt_filename}")
    
def create_enhanced_visualizations(df: pd.DataFrame):
    """PREMIUM VISUALIZATIONS v3 – Exactly what you want (Nov 2025 Edition)"""
    if df.empty:
        print("No data for visualizations")
        return
    
    viz_folder = os.path.join(OUTPUT_FOLDER, "visualizations")
    os.makedirs(viz_folder, exist_ok=True)

    # === PREMIUM DARK THEME ===
    COLORS = {
        'buy': '#00F2DE',      # Electric Cyan
        'sell': '#FF3B5C',     # Vivid Coral
        'bg': '#0D0D2B',       # Deep Space Blue
        'text': '#FFFFFF',
        'grid': '#1E1E3F'
    }

    plt.rcParams.update({
        'figure.facecolor': COLORS['bg'],
        'axes.facecolor': COLORS['bg'],
        'axes.edgecolor': 'white',
        'axes.labelcolor': 'white',
        'axes.titlecolor': 'white',
        'xtick.color': 'white',
        'ytick.color': 'white',
        'text.color': 'white',
        'grid.color': COLORS['grid'],
        'grid.alpha': 0.4,
        'font.size': 11,
        'font.family': 'Segoe UI',
        'savefig.facecolor': COLORS['bg'],
        'savefig.dpi': 320,
        'savefig.bbox': 'tight'
    })

    pending_orders = df[df['Trade Type'] == 'PENDING_ORDER']
    completed_trades = df[df['Trade Type'] == 'COMPLETED']

    # ================================================
    # 1. MISSED OPPORTUNITIES – HORIZONTAL BAR (KEEP – IT'S GOLD)
    # ================================================
    if not pending_orders.empty:
        missed = pending_orders[pending_orders['Missed Opportunity'] == True]
        if not missed.empty:
            top15 = (missed.groupby(['Symbol', 'Timeframe', 'Direction'])
                    .size()
                    .reset_index(name='Missed_Count')
                    .sort_values('Missed_Count', ascending=True)
                    .tail(15))

            fig, ax = plt.subplots(figsize=(14, 10))
            bars = ax.barh([f"{r.Symbol} • {r.Timeframe} • {r.Direction}" for _, r in top15.iterrows()],
                          top15['Missed_Count'],
                          color=[COLORS['buy'] if d == 'BUY' else COLORS['sell'] for d in top15['Direction']],
                          edgecolor='white', linewidth=1.5, alpha=0.92)

            ax.set_title('TOP 15 MISSED OPPORTUNITIES\n(TP1 Hit Before Entry)', 
                        fontsize=24, fontweight='bold', pad=40)
            ax.set_xlabel('Number of Times TP1 Was Hit Without Entry', fontsize=13, fontweight='bold')

            for bar, count in zip(bars, top15['Missed_Count']):
                ax.text(count + 0.3, bar.get_y() + bar.get_height()/2,
                       f'{int(count)}', fontsize=13, va='center', fontweight='bold', color='white')

            ax.invert_yaxis()
            ax.grid(axis='x', alpha=0.5)
            ax.spines[['top', 'right']].set_visible(False)

            # Legend
            from matplotlib.patches import Patch
            ax.legend(handles=[
                Patch(facecolor=COLORS['buy'], label='BUY Signals Missed'),
                Patch(facecolor=COLORS['sell'], label='SELL Signals Missed')
            ], loc='lower right', fontsize=12)

            plt.tight_layout()
            plt.savefig(os.path.join(viz_folder, '01_Missed_Opportunities.png'))
            plt.close()
            print("Created: 01_Missed_Opportunities.png")

    # ================================================
    # 2. WIN RATE HEATMAP – NOW WITH DIRECTION (BUY/SELL SEPARATE)
    # ================================================
    if not completed_trades.empty:
        # Create multi-index pivot: Symbol × Timeframe × Direction
        heatmap_data = (completed_trades.groupby(['Symbol', 'Timeframe', 'Direction'])
                       .agg(Win_Rate=('Outcome', lambda x: (x == 'WINNER').mean() * 100),
                            Trades=('Outcome', 'count'))
                       .round(1))

        # Keep only combinations with at least 5 trades
        heatmap_data = heatmap_data[heatmap_data['Trades'] >= 10]

        if not heatmap_data.empty:
            # Unstack Direction to create columns: BUY and SELL
            pivot_wr = heatmap_data['Win_Rate'].unstack('Direction').fillna(0)

            fig, ax = plt.subplots(figsize=(16, 12))
            sns.heatmap(pivot_wr, annot=True, fmt=".0f", cmap="RdYlGn", center=60,
                       linewidths=2, linecolor='white', cbar_kws={'label': 'Win Rate %'},
                       annot_kws={'fontsize': 14, 'fontweight': 'bold'}, ax=ax, square=True)

            ax.set_title('WIN RATE HEATMAP BY SYMBOL × TIMEFRAME DIRECTION\n(Min. 10 Trades Required)', 
                        fontsize=26, fontweight='bold', pad=40)
            ax.set_xlabel('Trade Direction', fontsize=16, fontweight='bold')
            ax.set_ylabel('Symbol • Timeframe', fontsize=16, fontweight='bold')

            # Color bar label
            cbar = ax.collections[0].colorbar
            cbar.ax.tick_params(labelsize=12)
            cbar.set_label('Win Rate (%)', fontsize=14, fontweight='bold', color='white')

            plt.tight_layout()
            plt.savefig(os.path.join(viz_folder, '02_WinRate_Heatmap_With_Direction.png'))
            plt.close()
            print("Created: 02_WinRate_Heatmap_With_Direction.png")

    print(f"\nAll PREMIUM visuals saved (2 charts only – clean & focused):\n   {viz_folder}")    

def save_comprehensive_excel_report(df: pd.DataFrame):
    """Save comprehensive analysis to Excel with formatting — NOW INCLUDES DIRECTION"""
    if df.empty:
        print("No data to save")
        return
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = os.path.join(OUTPUT_FOLDER, f"Deriv_Comprehensive_Analysis_{timestamp}.xlsx")
    
    try:
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            # Main data sheet
            df.to_excel(writer, sheet_name="All_Data", index=False)
            
            # === 1. PENDING ORDERS SUMMARY (NOW WITH DIRECTION) ===
                        # === 1. PENDING ORDERS SUMMARY – NEW METRICS YOU ASKED FOR ===
                        # === 1. PENDING ORDERS SUMMARY – FIXED & CLEAN VERSION ===
            pending_orders = df[df['Trade Type'] == 'PENDING_ORDER']
            if not pending_orders.empty:
                def pending_stats(group):
                    total = len(group)
                    filled = group['Entry Filled'].sum()
                    missed = group['Missed Opportunity'].sum()
                    won_after_fill = group['Won Trade'].sum()

                    won_executed_pct = (won_after_fill / filled * 100) if filled > 0 else 0
                    missed_rate_pct = (missed / total * 100)

                    return pd.Series({
                        'Total_Orders': total,
                        'Filled_Orders': int(filled),
                        'Missed_Opportunities': int(missed),
                        'Won_After_Fill': int(won_after_fill),
                        'Won_Executed_%': round(won_executed_pct, 1),
                        'Lost_After_Fill': int(filled - won_after_fill),
                        'Missed_Opportunity_Rate_%': round(missed_rate_pct, 1)
                    })

                # Fix: explicitly include grouping columns + suppress warning
                pending_summary = (
                    pending_orders
                    .groupby(['Symbol', 'Timeframe', 'Direction', 'Order Type'], as_index=False)
                    .apply(pending_stats, include_groups=False)  # this removes the warning
                )

                pending_summary = pending_summary.sort_values(
                    by=['Symbol', 'Timeframe', 'Direction', 'Order Type', 'Missed_Opportunities'],
                    ascending=[True, True, True, True, False]
                ).reset_index(drop=True)
                pending_summary.to_excel(writer, sheet_name="Pending_Orders_Summary", index=False)

            # === 2. COMPLETED TRADES SUMMARY (NOW WITH DIRECTION) ===
                        # === 2. COMPLETED TRADES SUMMARY – NEW VERSION WITH WINNERS/LOSERS ===
                        # === 2. COMPLETED TRADES SUMMARY – FIXED & CLEAN VERSION ===
            completed_trades = df[df['Trade Type'] == 'COMPLETED']
            if not completed_trades.empty:
                def count_outcomes(group):
                    winners = (group['Outcome'] == 'WINNER').sum()
                    losers = (group['Outcome'] == 'LOSER').sum()
                    breakeven = (group['Outcome'] == 'BREAKEVEN').sum()
                    total = len(group)
                    win_rate = (winners / total * 100) if total > 0 else 0

                    return pd.Series({
                        'Trade_Count': total,
                        'Winners': int(winners),
                        'Losers': int(losers),
                        'Breakeven': int(breakeven),
                        'Win_Rate_%': round(win_rate, 1)
                    })

                # Fixed version – clean and no warning/error
                completed_summary = (
                    completed_trades
                    .groupby(['Symbol', 'Timeframe', 'Direction', 'Order Type'], as_index=False)
                    .apply(count_outcomes, include_groups=False)
                )

                completed_summary = completed_summary.sort_values(
                    by=['Symbol', 'Timeframe', 'Direction', 'Order Type', 'Trade_Count'],
                    ascending=[True, True, True, True, False]
                ).reset_index(drop=True)
                completed_summary.to_excel(writer, sheet_name="Completed_Trades_Summary", index=False)

                # Additional detailed breakdown: Symbol + Timeframe + Direction (regardless of order type)
                                # Symbol + Timeframe + Direction sheet
                            # === Symbol + Timeframe + Direction sheet (NO Total/Avg Profit) ===
            stfd_stats = completed_trades.groupby(['Symbol', 'Timeframe', 'Direction']).agg({
                'Profit': 'count',                     # only count of trades
                'Outcome': lambda x: (x == 'WINNER').mean() * 100
            }).round(2)
            stfd_stats.columns = ['Trade_Count', 'Win_Rate_%']
            stfd_stats = stfd_stats.reset_index()

            # Alphabetical order
            stfd_stats = stfd_stats.sort_values(
                by=['Symbol', 'Timeframe', 'Direction'],
                ascending=True
            ).reset_index(drop=True)

            stfd_stats.to_excel(writer, sheet_name="Symbol_Timeframe_Direction", index=False)
            
            # === 3. STRATEGY RECOMMENDATIONS (already includes Direction) ===
                        # === 3. STRATEGY RECOMMENDATIONS (without Total/Avg Profit) ===
            strategy_data = []
            if not completed_trades.empty:
                perf = completed_trades.groupby(['Symbol', 'Timeframe', 'Direction']).agg({
                    'Profit': 'count',
                    'Outcome': lambda x: (x == 'WINNER').mean() * 100
                }).round(2)
                perf.columns = ['Trade_Count', 'Win_Rate_%']
                perf = perf.reset_index()

                for _, row in perf.iterrows():
                    recommendation = "EXCELLENT" if (row['Win_Rate_%'] >= 60 and row['Trade_Count'] >= 5) \
                        else "GOOD" if (row['Win_Rate_%'] >= 55) \
                        else "NEEDS REVIEW" if (row['Win_Rate_%'] < 45) \
                        else "MONITOR"
                    
                    strategy_data.append({
                        'Symbol': row['Symbol'],
                        'Timeframe': row['Timeframe'],
                        'Direction': row['Direction'],
                        'Trade_Count': row['Trade_Count'],
                        'Win_Rate_%': row['Win_Rate_%'],
                        'Recommendation': recommendation
                    })
            
            strategy_df = pd.DataFrame(strategy_data)
            strategy_df = strategy_df.sort_values(
                by=['Recommendation', 'Symbol', 'Timeframe', 'Direction'],
                ascending=[False, True, True, True]
            ).reset_index(drop=True)

            strategy_df.to_excel(writer, sheet_name="Strategy_Recommendations", index=False)
            
            # === EVALUATION WORKSHEETS: WINNERS / LOSERS / BREAKEVEN (+ win % incl/excl BE) ===
            if not completed_trades.empty:
                eval_symbol = build_outcome_eval_sheet(completed_trades, ['Symbol'])
                eval_symbol.to_excel(writer, sheet_name="Eval_By_Symbol", index=False)

                eval_symbol_tf = build_outcome_eval_sheet(completed_trades, ['Symbol', 'Timeframe'])
                eval_symbol_tf.to_excel(writer, sheet_name="Eval_By_Symbol_Timeframe", index=False)

                eval_symbol_dir = build_outcome_eval_sheet(completed_trades, ['Symbol', 'Direction'])
                eval_symbol_dir.to_excel(writer, sheet_name="Eval_By_Symbol_Direction", index=False)
            
            # === Apply nice formatting ===
            workbook = writer.book
            header_font = Font(bold=True, color="FFFFFF", size=12)
            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            thin_border = Border(left=Side(style='thin'), right=Side(style='thin'),
                                 top=Side(style='thin'), bottom=Side(style='thin'))

            for sheet_name in writer.sheets:
                ws = writer.sheets[sheet_name]
                # Header styling
                for cell in ws[1]:
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                
                # Auto-adjust column widths
                for col in ws.columns:
                    max_length = 0
                    column = col[0].column_letter
                    for cell in col:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    ws.column_dimensions[column].width = adjusted_width
                
                # Add borders to all cells
                for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
                    for cell in row:
                        cell.border = thin_border

        print(f"Comprehensive report with DIRECTION analysis saved: {filename}")
        
    except Exception as e:
        print(f"Error saving Excel file: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main analysis function"""
    print("🚀 Starting Comprehensive Deriv Bot Analysis...")
    clear_output_folder()
    
    # Run comprehensive analysis
    df = analyze_strategy_performance()
    
    if df.empty:
        print("⚠️ No trading data found for analysis")
        mt5.shutdown()
        return
    
    # Generate reports and visualizations
    generate_comprehensive_report(df)
    create_enhanced_visualizations(df)
    save_comprehensive_excel_report(df)
    run_candle_context_analysis(df)
    
    mt5.shutdown()
    print(f"\n✅ Comprehensive analysis completed successfully!")
    print(f"📁 Results saved to: {OUTPUT_FOLDER}")

if __name__ == "__main__":
    main()