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

# === CONFIGURATION ===
MT5_PATH = r"C:\Program Files\MetaTrader 5 Terminal\terminal64.exe"
OUTPUT_FOLDER = str(Path.home() / "OneDrive - University of Ghana" / "visuals_Comprehensive_Analysis")
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
CANDLE_CONTEXT_LOOKBACK = 100        # candles to pull before (and including) the entry candle
CANDLE_INDICATOR_WARMUP = 20        # extra candles fetched purely to warm up rolling indicators
CANDLE_CONTEXT_MAX_CHARTS = 100      # cap on highlighted candle charts generated (set to None for no cap)
ENABLE_CANDLE_CONTEXT_ANALYSIS = True

STD_DEV_WINDOW = 20   # rolling window for std-dev / volume / body / range z-scores
ATR_WINDOW = 14
RSI_WINDOW = 14
EMA_FAST = 9
EMA_SLOW = 21

TF_TO_MT5 = {
    "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4, "D1": mt5.TIMEFRAME_D1
}
TF_MINUTES = {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440}


# Trading configuration from visuals.py
def get_trading_config():
    Basket_Indices= ['AUD Basket', 'EUR Basket', 'GBP Basket', 'Gold Basket', 'USD Basket']
    Crash_Boom_Indices= ['Boom 1000 Index', 'Boom 150 Index', 'Boom 300 Index', 'Boom 500 Index', 'Boom 600 Index', 'Boom 900 Index', 'Crash 1000 Index', 'Crash 150 Index', 'Crash 300 Index', 'Crash 500 Index', 'Crash 600 Index', 'Crash 900 Index']
    Crypto= ['ADAUSD', 'ALGUSD', 'AVAUSD', 'BATUSD', 'BCHUSD', 'BNBUSD', 'BTCETH', 'BTCLTC', 'BTCUSD', 'DOGUSD', 'DOTUSD', 'DSHUSD', 'ETCUSD', 'ETHUSD', 'IOTUSD', 'LNKUSD', 'LTCUSD', 'SOLUSD', 'UNIUSD', 'XLMUSD', 'XRPUSD', 'ZECUSD']
    DEX_Indices= ['DEX 1500 DOWN Index', 'DEX 1500 UP Index', 'DEX 600 DOWN Index', 'DEX 600 UP Index', 'DEX 900 DOWN Index', 'DEX 900 UP Index']
    Energies= ['UK Brent Oil', 'US Oil']
    Forex_Major= ['AUDJPY', 'AUDUSD', 'EURAUD', 'EURCAD', 'EURCHF', 'EURGBP', 'EURJPY', 'EURUSD', 'GBPAUD', 'GBPJPY', 'GBPUSD', 'USDCAD', 'USDCHF', 'USDJPY']
    Forex_Minor= ['AUDCAD', 'AUDCHF', 'AUDNZD', 'CADCHF', 'CADJPY', 'CHFJPY', 'EURNOK', 'EURNZD', 'EURPLN', 'EURSEK', 'GBPCAD', 'GBPCHF', 'GBPNOK', 'GBPNZD', 'GBPSEK', 'NZDCAD', 'NZDJPY', 'NZDUSD', 'USDCNH', 'USDMXN', 'USDNOK', 'USDPLN', 'USDSEK', 'USDZAR']
    Jump_Indices= ['Jump 10 Index', 'Jump 100 Index', 'Jump 25 Index', 'Jump 50 Index', 'Jump 75 Index']
    Metals= ['XAGEUR', 'XAGUSD', 'XAUEUR', 'XAUUSD', 'XPDUSD', 'XPTUSD']
    Multi_Step_Indices= ['Multi Step 2 Index', 'Multi Step 3 Index', 'Multi Step 4 Index']
    Range_Break= ['Range Break 100 Index', 'Range Break 200 Index']
    Skewed_Step= ['Skew Step Index 4 Down', 'Skew Step Index 4 Up', 'Skew Step Index 5 Down', 'Skew Step Index 5 Up']
    Step_Indices= ['Step Index 200', 'Step Index 300', 'Step Index 400', 'Step Index 500', 'Step Index']
    Stock_Indices= ['Australia 200', 'China H Shares', 'Europe 50', 'France 40', 'Germany 40', 'Hong Kong 50', 'Japan 225', 'Netherlands 25', 'Spain 35', 'Swiss 20', 'UK 100', 'US Mid Cap 400', 'US SP 500', 'US Small Cap 2000', 'US Tech 100', 'Wall Street 30']
    Volatility_Indices= ['Volatility 10 (1s) Index', 'Volatility 10 Index', 'Volatility 100 (1s) Index', 'Volatility 100 Index', 'Volatility 15 (1s) Index', 'Volatility 150 (1s) Index', 'Volatility 25 (1s) Index', 'Volatility 25 Index', 'Volatility 30 (1s) Index', 'Volatility 50 (1s) Index', 'Volatility 50 Index', 'Volatility 75 (1s) Index', 'Volatility 75 Index', 'Volatility 90 (1s) Index']

    return {
        "H1_PENDING": Basket_Indices+Crash_Boom_Indices+Crypto+DEX_Indices+Energies+Forex_Major+Forex_Minor+Jump_Indices+Metals+Multi_Step_Indices+Range_Break+Skewed_Step+Step_Indices+Stock_Indices+Volatility_Indices,
        "H1_INSTANT": [],
        "M15_PENDING": Basket_Indices+Crash_Boom_Indices+Crypto+DEX_Indices+Energies+Forex_Major+Forex_Minor+Jump_Indices+Metals+Multi_Step_Indices+Range_Break+Skewed_Step+Step_Indices+Stock_Indices+Volatility_Indices,
        "M15_INSTANT": [],
        "M5_PENDING": Basket_Indices+Crash_Boom_Indices+Crypto+DEX_Indices+Energies+Forex_Major+Forex_Minor+Jump_Indices+Metals+Multi_Step_Indices+Range_Break+Skewed_Step+Step_Indices+Stock_Indices+Volatility_Indices,
        "M5_INSTANT": [],
        "M1_PENDING": Basket_Indices+Crash_Boom_Indices+Crypto+DEX_Indices+Energies+Jump_Indices+Metals+Multi_Step_Indices+Range_Break+Skewed_Step+Step_Indices+Stock_Indices+Volatility_Indices,
        "M1_INSTANT": []
    }

def get_all_deals():
    from_date = datetime(2026, 8, 16)
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
    from_date = datetime(2026, 8, 16)
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

def extract_tp_levels_from_comment(comment):
    """Decode the pipe-delimited 'tp1|tp2' comment written by the live bot into (tp1, tp2).
    Used for OUR OWN order/entry-deal comments, which always carry this format."""
    if not comment or pd.isna(comment):
        return None, None
    try:
        parts = str(comment).split("|")
        if len(parts) < 2:
            return None, None
        return float(parts[0]), float(parts[1])
    except (ValueError, TypeError):
        return None, None

def extract_first_float_from_comment(comment):
    """Generic fallback: pulls the first float-looking substring from a comment field,
    regardless of format. Used for broker-generated exit-deal comments, which may not
    carry our own tp1|tp2 format (e.g. this is how `last_sl` is recovered below)."""
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

def simulate_price_hits_with_ticks(symbol, direction, entry_price, target_price, sl_price, start_time, end_time):
    """
    Simulate price hits using tick-by-tick data for maximum accuracy.
    `target_price` is whichever level the caller wants to check hits against (for the
    pending-order "missed opportunity" analysis this is TP2 - the old TP1 - since that's
    the level close_pending() actually watches in the live bot).
    
    Returns: tuple of (target_hit, sl_hit, entry_hit, target_time, sl_time, entry_time, first_touch_time)
    """
    # Get tick data
    ticks_df = get_ticks_for_simulation(symbol, start_time, end_time)
    
    if ticks_df.empty:
        print(f"⚠️ No tick data for {symbol} between {start_time} and {end_time}")
        return False, False, False, None, None, None, None
    
    # Initialize tracking variables
    target_hit = sl_hit = entry_hit = False
    target_time = sl_time = entry_time = first_touch_time = None
    
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
        
        # Check target hit
        if not target_hit:
            if direction == "BUY" and bid >= target_price:
                target_hit = True
                target_time = tick_time
            elif direction == "SELL" and ask <= target_price:
                target_hit = True
                target_time = tick_time
        
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
                if bid >= target_price or ask <= sl_price or ask <= entry_price:
                    touched = True
            elif direction == "SELL":
                if ask <= target_price or bid >= sl_price or bid >= entry_price:
                    touched = True
            
            if touched:
                first_touch_time = tick_time
        
        # Early exit if all levels hit
        if target_hit and sl_hit and entry_hit:
            break
    
    return target_hit, sl_hit, entry_hit, target_time, sl_time, entry_time, first_touch_time

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
        if tf_str == "M1":
            # M1 trading is deactivated in visuals.py - exclude any M1 history from reports
            processed_count += 1
            continue
        direction = "BUY" if order['type'] in [2, 4] else "SELL"
        
        # Safe conversion
        entry = safe_float_conversion(order['price_open'])
        sl = safe_float_conversion(order['sl'])
        tp3 = safe_float_conversion(order['tp'])  # broker-side final target
        comment = str(order.get('comment', ''))
        tp1, tp2 = extract_tp_levels_from_comment(comment)

        # TP2 (the old TP1) is what close_pending() in the live bot actually watches to
        # cancel a resting order, so it's the level this simulation checks against.
        if tp2 is None or sl == 0.0 or entry == 0.0:
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
        
        # Use tick-based simulation, checking hits against TP2 (the missed-opportunity trigger)
        target_hit, sl_hit, entry_hit, target_time, sl_time, entry_time, first_touch_time = \
            simulate_price_hits_with_ticks(symbol, direction, entry, tp2, sl, start, end)
        
        # Enhanced outcome determination
        missed_opportunity = target_hit and not entry_hit
        won_trade = False
        lost_trade = False
        
        if entry_hit:
            if target_hit and (not sl_hit or (sl_time and target_time and target_time < sl_time)):
                won_trade = True
            elif sl_hit and (not target_hit or (target_time and sl_time and sl_time < target_time)):
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
            "TP3": tp3,
            "TP2 Hit": target_hit,
            "SL Hit": sl_hit,
            "Entry Filled": entry_hit,
            "Missed Opportunity": missed_opportunity,
            "Won Trade": won_trade,
            "Lost Trade": lost_trade,
            "TP2 Time": target_time,
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
        if timeframe_str == "M1":
            # M1 trading is deactivated in visuals.py - exclude any M1 history from reports
            continue
        
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
        tp3 = safe_float_conversion(entry.get('tp', 0))  # broker-side final target
        
        comment = str(entry.get('comment', '')).strip()
        tp1, tp2 = extract_tp_levels_from_comment(comment)
        
        net_profit = group['profit'].sum() + group['swap'].sum() + group['commission'].sum()
        net_profit = round(float(net_profit), 2)
        
        exit_deals = group[group['entry'] == 1]
        if exit_deals.empty:
            continue
        exit = exit_deals.iloc[-1]
        last_sl = extract_first_float_from_comment(exit.get('comment', 0))
        
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
            "TP3": tp3 if tp3 != 0 else None,
            "TP1": tp1,
            "TP2": tp2,
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
    for col in ['Outcome', 'Reason', 'Volume', 'Position ID', 'Profit']:
        if col not in df_pending.columns:
            df_pending[col] = pd.NA
        if col not in df_completed.columns:
            df_completed[col] = pd.NA
    
    # Now safe concat
    df = pd.concat([df_pending, df_completed], ignore_index=True)
    
    # Type fixing
    numeric_columns = ['Entry Price', 'TP1', 'SL', 'TP2', 'TP3', 'Profit', 'Volume']
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    bool_columns = ['TP2 Hit', 'SL Hit', 'Entry Filled', 'Missed Opportunity', 'Won Trade']
    for col in bool_columns:
        if col in df.columns:
            df[col] = df[col].astype('boolean')
    
    print(f"Final combined dataset: {len(df)} rows ({len(df_pending)} pending + {len(df_completed)} completed)")
    return df
# ======================================================================================
# === SHADOW-MODE ENGULF ANALYSIS (pending-order alternate-entry edge) ===
# Retroactively simulates: instead of a resting pending order filling at `sniper`, wait
# for price to touch sniper, then require a raw body-engulf candle (opposite color, body
# fully containing the prior candle's body, in the trade's direction — no 3-prior-candle
# filter, no confirmation candle, unlike the bot's own detect_opposite_engulfing()) on the
# confirmation timeframe before entering. The valid-entry zone is symmetric around sniper:
# sniper +/- 20% of the original entry->SL risk. If price closes beyond the SL-side
# boundary before a qualifying engulf appears, the setup is abandoned (dodged a loss). If
# price closes beyond the TP-side boundary first, the setup also gets no entry, but for the
# opposite reason -- the move ran favorably without ever giving the pullback/engulf entry
# (a missed win, not a dodge). Confirmation timeframe is M3 first; if no qualifying engulf
# is found anywhere in the valid window on M3, M5 is scanned over that same window as a
# fallback (an M5 candle can show a clean engulf that's noisy/split across M3 candles).
# Entry price/time = the engulfing candle's own close, since this is closed historical data
# (no need to wait an extra candle for confirmation the way live data would require).
# ======================================================================================

SHADOW_ENGULF_TIMEFRAME_PRIMARY = mt5.TIMEFRAME_M3    # checked first
SHADOW_ENGULF_TIMEFRAME_FALLBACK = mt5.TIMEFRAME_M5   # checked only if primary finds no engulf
SHADOW_ZONE_RISK_FRACTION = 0.20                      # symmetric zone: sniper +/- 20% of risk

def detect_raw_body_engulf(df, direction, i):
    """
    True if candle i is a raw body-engulf of candle i-1 in the trade direction: opposite
    color from the prior candle, and its body (open/close) fully contains the prior
    candle's body. No other conditions -- deliberately simpler than the live bot's own
    detect_opposite_engulfing(), which is a different, more filtered pattern.
    """
    if i < 1 or i >= len(df):
        return False
    prev_open, prev_close = df['open'].iloc[i-1], df['close'].iloc[i-1]
    cur_open, cur_close = df['open'].iloc[i], df['close'].iloc[i]
    prev_bullish = prev_close > prev_open
    cur_bullish = cur_close > cur_open

    if direction == "BUY":
        if not (cur_bullish and not prev_bullish):
            return False
        return cur_open <= prev_close and cur_close >= prev_open
    elif direction == "SELL":
        if not (not cur_bullish and prev_bullish):
            return False
        return cur_open >= prev_close and cur_close <= prev_open
    return False


def fetch_shadow_confirmation_candles(symbol, start_time, end_time, timeframe):
    """Fetch confirmation-timeframe candles from start_time to end_time for the shadow logic."""
    if pd.isna(start_time) or pd.isna(end_time) or end_time <= start_time:
        return pd.DataFrame()
    try:
        rates = mt5.copy_rates_range(symbol, timeframe, start_time, end_time)
    except Exception as e:
        print(f"⚠️ copy_rates_range failed for {symbol} shadow analysis: {e}")
        return pd.DataFrame()
    if rates is None or len(rates) == 0:
        return pd.DataFrame()
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df.sort_values('time').reset_index(drop=True)


def _scan_window_for_shadow_engulf(candles, direction, sniper, sl_side_boundary, tp_side_boundary):
    """
    Scans one candle series for touch -> valid-zone engulf. The valid zone is symmetric:
    [sl_side_boundary, tp_side_boundary] around sniper (sniper +/- 20% of risk). Once
    touched, if a candle CLOSES beyond either boundary before a qualifying engulf appears,
    the window ends there (abandon_side records which boundary: 'SL' or 'TP').
    Returns a dict: touched, touch_time, entered, entry_price, entry_time,
    abandon_side, abandon_time.
    """
    result = {
        "touched": False, "touch_time": None,
        "entered": False, "entry_price": None, "entry_time": None,
        "abandon_side": None, "abandon_time": None,
    }
    if candles.empty:
        return result

    for i in range(len(candles)):
        if not result["touched"]:
            if direction == "BUY" and candles['low'].iloc[i] <= sniper:
                result["touched"] = True
                result["touch_time"] = candles['time'].iloc[i]
            elif direction == "SELL" and candles['high'].iloc[i] >= sniper:
                result["touched"] = True
                result["touch_time"] = candles['time'].iloc[i]
            continue

        close_price = candles['close'].iloc[i]
        if direction == "BUY":
            if close_price < sl_side_boundary:
                result["abandon_side"] = "SL"
                result["abandon_time"] = candles['time'].iloc[i]
                break
            if close_price > tp_side_boundary:
                result["abandon_side"] = "TP"
                result["abandon_time"] = candles['time'].iloc[i]
                break
        else:  # SELL
            if close_price > sl_side_boundary:
                result["abandon_side"] = "SL"
                result["abandon_time"] = candles['time'].iloc[i]
                break
            if close_price < tp_side_boundary:
                result["abandon_side"] = "TP"
                result["abandon_time"] = candles['time'].iloc[i]
                break

        if i >= 1 and detect_raw_body_engulf(candles, direction, i):
            result["entered"] = True
            result["entry_price"] = candles['close'].iloc[i]
            result["entry_time"] = candles['time'].iloc[i]
            break

    return result


def simulate_shadow_outcome_with_ticks(symbol, direction, sl, tp2, start_time, end_time):
    """
    Given a shadow entry has already happened at start_time, scans ticks forward to see
    whether SL or TP2 (the same gating level used to score the real order's Won/Lost
    Trade fields, so the comparison is apples-to-apples) is hit first.
    Returns (outcome, hit_time) where outcome is 'WON', 'LOST', or 'NO_DATA'.
    """
    ticks_df = get_ticks_for_simulation(symbol, start_time, end_time)
    if ticks_df.empty:
        return 'NO_DATA', None

    for _, tick in ticks_df.iterrows():
        tick_time = tick['time']
        bid = safe_float_conversion(tick.get('bid', 0))
        ask = safe_float_conversion(tick.get('ask', 0))
        if bid == 0 and ask == 0:
            last_price = safe_float_conversion(tick.get('last', 0))
            if last_price == 0:
                continue
            bid = ask = last_price

        if direction == "BUY":
            if bid >= tp2:
                return 'WON', tick_time
            if ask <= sl:
                return 'LOST', tick_time
        elif direction == "SELL":
            if ask <= tp2:
                return 'WON', tick_time
            if bid >= sl:
                return 'LOST', tick_time

    return 'NO_DATA', None


def analyze_shadow_engulf_pending_orders(pending_records):
    """
    Retroactively simulates the touch -> wait-for-engulf -> enter (or abandon) edge for
    every historical PENDING order, and compares it against what the order actually did.
    `pending_records` is the list of dicts returned by analyze_pending_orders_enhanced().
    Returns a list of dicts (one per PENDING order) with the shadow simulation results.
    """
    print("🕯️ Running shadow-mode engulf analysis on historical pending orders...")
    shadow_records = []

    pending_only = [r for r in pending_records if r.get("Order Type") == "PENDING"]
    total = len(pending_only)

    for idx, rec in enumerate(pending_only):
        symbol = rec["Symbol"]
        direction = rec["Direction"]
        sniper = rec["Entry Price"]
        sl = rec["SL"]
        tp2 = rec["TP2"]
        signal_time = rec["Signal Time"]

        if sniper is None or sl is None or tp2 is None or sniper == 0 or sl == 0:
            continue

        # risk = abs(entry_price - swing_point) originally; recovered here purely from
        # sniper and sl since sniper - sl = 1.2*risk in both directions (from the fib
        # multipliers: sniper = swing +/- 0.3*risk, sl = swing -/+ 0.9*risk).
        risk = abs(sniper - sl) / 1.2
        if risk <= 0:
            continue

        if direction == "BUY":
            sl_side_boundary = sniper - (SHADOW_ZONE_RISK_FRACTION * risk)
            tp_side_boundary = sniper + (SHADOW_ZONE_RISK_FRACTION * risk)
        else:
            sl_side_boundary = sniper + (SHADOW_ZONE_RISK_FRACTION * risk)
            tp_side_boundary = sniper - (SHADOW_ZONE_RISK_FRACTION * risk)

        # Window: from signal time to whenever the real order's analysis window ended
        window_end = rec.get("Entry Time") or rec.get("SL Time") or rec.get("TP2 Time") or \
            rec.get("First Touch Time") or datetime.now()
        if pd.isna(window_end):
            window_end = datetime.now()

        # Primary pass: M3 across the full window
        primary_candles = fetch_shadow_confirmation_candles(
            symbol, signal_time, window_end, SHADOW_ENGULF_TIMEFRAME_PRIMARY)
        scan = _scan_window_for_shadow_engulf(
            primary_candles, direction, sniper, sl_side_boundary, tp_side_boundary)
        used_timeframe = "M3" if scan["touched"] else None
        has_any_data = not primary_candles.empty

        # Fallback pass: M5, only if M3 didn't find a qualifying engulf. Restricted to the
        # same window (touch -> wherever the window ended for the M3 pass).
        if not scan["entered"] and SHADOW_ENGULF_TIMEFRAME_FALLBACK != SHADOW_ENGULF_TIMEFRAME_PRIMARY:
            fallback_end = scan["abandon_time"] if scan["abandon_time"] else window_end
            fallback_candles = fetch_shadow_confirmation_candles(
                symbol, signal_time, fallback_end, SHADOW_ENGULF_TIMEFRAME_FALLBACK)
            has_any_data = has_any_data or not fallback_candles.empty
            fb_scan = _scan_window_for_shadow_engulf(
                fallback_candles, direction, sniper, sl_side_boundary, tp_side_boundary)
            if fb_scan["entered"]:
                scan = fb_scan
                used_timeframe = "M5"
            elif not scan["touched"] and fb_scan["touched"]:
                # M3 had no data / never registered touch, but M5 did
                scan = fb_scan
                used_timeframe = "M5"

        if not has_any_data:
            shadow_records.append({
                "Symbol": symbol, "Timeframe": rec["Timeframe"], "Direction": direction,
                "Signal Time": signal_time, "Shadow Touched": False,
                "Shadow Entry Timeframe": None, "Shadow Entered": False,
                "Shadow Abandon Side": None, "Shadow Abandon Time": None,
                "Shadow Entry Price": None, "Shadow Entry Time": None,
                "Shadow Outcome": "NO_DATA", "Shadow Outcome Time": None,
                "Real Missed Opportunity": rec.get("Missed Opportunity"),
                "Real Won Trade": rec.get("Won Trade"), "Real Lost Trade": rec.get("Lost Trade"),
                "Real Entry Filled": rec.get("Entry Filled"),
            })
            continue

        shadow_outcome = "NO_ENTRY"
        shadow_outcome_time = None
        if scan["entered"]:
            outcome_end = window_end if window_end > scan["entry_time"] else scan["entry_time"] + timedelta(days=5)
            shadow_outcome, shadow_outcome_time = simulate_shadow_outcome_with_ticks(
                symbol, direction, sl, tp2, scan["entry_time"], outcome_end)

        shadow_records.append({
            "Symbol": symbol,
            "Timeframe": rec["Timeframe"],
            "Direction": direction,
            "Signal Time": signal_time,
            "Shadow Touched": scan["touched"],
            "Shadow Entry Timeframe": used_timeframe if scan["entered"] else None,
            "Shadow Entered": scan["entered"],
            "Shadow Abandon Side": scan["abandon_side"],
            "Shadow Abandon Time": scan["abandon_time"],
            "Shadow Entry Price": scan["entry_price"],
            "Shadow Entry Time": scan["entry_time"],
            "Shadow Outcome": shadow_outcome,
            "Shadow Outcome Time": shadow_outcome_time,
            "Real Missed Opportunity": rec.get("Missed Opportunity"),
            "Real Won Trade": rec.get("Won Trade"),
            "Real Lost Trade": rec.get("Lost Trade"),
            "Real Entry Filled": rec.get("Entry Filled"),
        })

        if (idx + 1) % 10 == 0:
            print(f"  Shadow-analyzed {idx + 1}/{total} pending orders...")

    print(f"Shadow-mode engulf analysis complete: {len(shadow_records)} pending orders processed")
    return shadow_records


def build_shadow_vs_actual_comparison(shadow_df):
    """
    Classifies each shadow-analyzed order into a comparison category against what the
    real resting order actually did, and returns the per-trade comparison plus an
    aggregated win-rate comparison (real vs shadow) by Symbol and by Symbol+Timeframe.
    """
    if shadow_df.empty:
        return shadow_df, pd.DataFrame(), pd.DataFrame()

    def classify(row):
        real_won = bool(row.get("Real Won Trade"))
        real_lost = bool(row.get("Real Lost Trade"))
        shadow_entered = bool(row.get("Shadow Entered"))
        shadow_won = row.get("Shadow Outcome") == "WON"
        shadow_lost = row.get("Shadow Outcome") == "LOST"

        if not shadow_entered:
            if real_lost:
                return "Dodged Loss"
            elif real_won:
                return "Missed Win"
            else:
                return "No Real Fill / No Shadow Entry"
        else:
            if real_won and shadow_won:
                return "Agree - Both Won"
            elif real_lost and shadow_lost:
                return "Agree - Both Lost"
            elif real_won and shadow_lost:
                return "Disagree - Real Won, Shadow Lost"
            elif real_lost and shadow_won:
                return "Disagree - Real Lost, Shadow Won"
            else:
                return "Other / Incomplete Data"

    shadow_df = shadow_df.copy()
    shadow_df["Comparison"] = shadow_df.apply(classify, axis=1)

    def win_rate_summary(group_cols):
        rows = []
        for keys, group in shadow_df.groupby(group_cols):
            total = len(group)
            real_wins = group["Real Won Trade"].fillna(False).astype(bool).sum()
            real_losses = group["Real Lost Trade"].fillna(False).astype(bool).sum()
            real_decided = real_wins + real_losses
            real_wr = (real_wins / real_decided * 100) if real_decided > 0 else None

            shadow_entered = group["Shadow Entered"].fillna(False).astype(bool)
            shadow_wins = (group["Shadow Outcome"] == "WON").sum()
            shadow_losses = (group["Shadow Outcome"] == "LOST").sum()
            shadow_decided = shadow_wins + shadow_losses
            shadow_wr = (shadow_wins / shadow_decided * 100) if shadow_decided > 0 else None

            row = {}
            if isinstance(keys, tuple):
                for col, val in zip(group_cols, keys):
                    row[col] = val
            else:
                row[group_cols[0]] = keys
            row.update({
                "Total Orders": total,
                "Real Wins": int(real_wins), "Real Losses": int(real_losses),
                "Real Win Rate %": round(real_wr, 1) if real_wr is not None else None,
                "Shadow Entries": int(shadow_entered.sum()),
                "Shadow Wins": int(shadow_wins), "Shadow Losses": int(shadow_losses),
                "Shadow Win Rate %": round(shadow_wr, 1) if shadow_wr is not None else None,
                "Dodged Losses": int((group["Comparison"] == "Dodged Loss").sum()),
                "Missed Wins": int((group["Comparison"] == "Missed Win").sum()),
            })
            rows.append(row)
        return pd.DataFrame(rows)

    by_symbol = win_rate_summary(["Symbol"])
    by_symbol_tf = win_rate_summary(["Symbol", "Timeframe"])

    return shadow_df, by_symbol, by_symbol_tf


def save_shadow_engulf_excel_report(shadow_df, by_symbol, by_symbol_tf):
    """Writes the per-trade shadow-vs-actual comparison and the aggregated win-rate
    comparison (real vs shadow) to their own workbook."""
    if shadow_df.empty:
        print("No shadow-mode engulf data to save")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = os.path.join(OUTPUT_FOLDER, f"Shadow_Engulf_Analysis_{timestamp}.xlsx")

    try:
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            shadow_df.to_excel(writer, sheet_name="Shadow_vs_Actual", index=False)
            if not by_symbol.empty:
                by_symbol.to_excel(writer, sheet_name="WinRate_By_Symbol", index=False)
            if not by_symbol_tf.empty:
                by_symbol_tf.to_excel(writer, sheet_name="WinRate_By_Symbol_TF", index=False)

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

        print(f"Shadow-mode engulf analysis report saved: {filename}")
    except Exception as e:
        print(f"Error saving shadow-mode Excel report: {e}")
        import traceback
        traceback.print_exc()


def run_shadow_engulf_analysis():
    """Orchestrates the shadow-mode engulf edge analysis: re-derives the pending order
    records, simulates the touch->engulf->enter/abandon logic, compares it against what
    the real resting orders actually did, and saves results to their own workbook."""
    pending_data = analyze_pending_orders_enhanced()
    if not pending_data:
        print("⚠️ No pending order data available for shadow-mode analysis")
        return
    shadow_records = analyze_shadow_engulf_pending_orders(pending_data)
    if not shadow_records:
        print("⚠️ No shadow-mode results generated")
        return
    shadow_df = pd.DataFrame(shadow_records)
    shadow_df, by_symbol, by_symbol_tf = build_shadow_vs_actual_comparison(shadow_df)
    save_shadow_engulf_excel_report(shadow_df, by_symbol, by_symbol_tf)

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
    Used to add volume, standard-deviation, ATR, RSI, EMA and z-score style indicator columns to a
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


CANDLE_SNAPSHOT_COLS = [
    'open', 'high', 'low', 'close', 'volume', 'body', 'body_abs', 'range',
    'upper_wick', 'lower_wick', 'body_pct_of_range', 'is_bullish'
]


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

        for i, candle in window.iterrows():
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
                'time': candle['time'],
                'Is_Entry_Candle': (i == entry_idx),
                'Is_Trigger_Candle': (i == trigger_idx),
                'Is_Between_Entry_And_Trigger': (entry_idx < i < trigger_idx),
                'Is_Swing_Candle': (swing_idx is not None and i == swing_idx),
            }
            for col in CANDLE_SNAPSHOT_COLS:
                row[col] = candle.get(col)
            rows.append(row)

        if keep_windows_for_charts is None or len(chart_windows) < keep_windows_for_charts:
            chart_windows[trade_id] = {
                'window': window, 'entry_idx': entry_idx, 'trigger_idx': trigger_idx,
                'swing_idx': swing_idx, 'symbol': symbol, 'tf_str': tf_str,
                'outcome': trade.get('Outcome')
            }

        if (trade_id + 1) % 25 == 0:
            print(f"  Candle-context processed {trade_id + 1}/{total} trades...")

    context_df = pd.DataFrame(rows)
    n_trades = context_df['Trade_ID'].nunique() if not context_df.empty else 0
    print(f"Candle-context dataset built: {len(context_df)} candle rows across {n_trades} trades")
    return context_df, chart_windows


def build_entry_swing_summary(context_df: pd.DataFrame) -> pd.DataFrame:
    """Collapses the long-format candle context into one row per trade: entry-candle snapshot,
    trigger-candle snapshot, swing-candle snapshot, and aggregate stats over every candle that
    sat between entry and trigger (the gap that only exists for PENDING orders -- for INSTANT
    trades this gap is empty since trigger_idx == entry_idx + 1)."""
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

    return pd.DataFrame(summaries)




def plot_trade_candle_highlight(window_df, entry_idx, trigger_idx, swing_idx, symbol, tf_str,
                                 trade_id, outcome, save_path):
    """Renders the candle window with the entry/signal candle (▲), the trigger/fill candle (●),
    and the swing candle (▼) highlighted."""
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

        outcome_label = outcome if outcome else 'UNKNOWN'
        fig, axes = mpf.plot(
            plot_df, type='candle', style='yahoo',
            title=f"{symbol} {tf_str} | Trade #{trade_id} | {outcome_label}\n"
                  f"(▲ entry/signal candle   ● trigger/fill candle   ▼ swing candle)",
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
                                        trade_id, info['outcome'], save_path):
            saved += 1

    print(f"Saved {saved} candle-context highlight charts to {charts_folder}")


def save_candle_context_excel_report(context_df: pd.DataFrame, entry_swing_df: pd.DataFrame):
    """Writes the per-candle dataset, the per-trade entry/swing snapshot, and the winner-vs-loser
    indicator comparison to their own workbook."""
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
    """Orchestrates the full candle-context workflow: build dataset -> summarise -> compare
    winners vs losers -> save Excel report -> save highlighted charts."""
    if not ENABLE_CANDLE_CONTEXT_ANALYSIS:
        return

    print("\n🔬 Running candle-context analysis on completed trades...")
    context_df, chart_windows = build_candle_context_dataset(
        df, lookback=CANDLE_CONTEXT_LOOKBACK, keep_windows_for_charts=CANDLE_CONTEXT_MAX_CHARTS
    )
    if context_df.empty:
        print("⚠️ No candle-context data generated (no MT5 history available for trade entry times?)")
        return

    entry_swing_df = build_entry_swing_summary(context_df)

    save_candle_context_excel_report(context_df, entry_swing_df)
    #generate_candle_context_charts(chart_windows, OUTPUT_FOLDER)

   



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
        
        print(f"📈 Missed Opportunities (TP2 hit but no entry): {len(missed_opps)}")
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
        report_lines.append(f"📈 Missed Opportunities (TP2 hit but no entry): {len(missed_opps)}")
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
                line = f"   📍 {symbol} on {timeframe}: {count} missed TP2 hits"
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

            ax.set_title('TOP 15 MISSED OPPORTUNITIES\n(TP2 Hit Before Entry)', 
                        fontsize=24, fontweight='bold', pad=40)
            ax.set_xlabel('Number of Times TP2 Was Hit Without Entry', fontsize=13, fontweight='bold')

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
    run_shadow_engulf_analysis()
    
    mt5.shutdown()
    print(f"\n✅ Comprehensive analysis completed successfully!")
    print(f"📁 Results saved to: {OUTPUT_FOLDER}")

if __name__ == "__main__":
    main()