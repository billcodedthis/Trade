# comprehensive_deriv_analysis.py - FIXED VERSION
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
import re
from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import PieChart, BarChart, Reference
import matplotlib.font_manager as fm
from typing import List, Dict, Any, Tuple
import shutil

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


# Trading configuration from visuals.py
def get_trading_config():
    XAUUSD = "XAUUSD.0"
    BTCUSD="BTCUSD.0"
    MAJORS = ["EURCHF.0"]
    Jump = ["Jump 25 Index.0"]
    J=["Jump 75 Index.0"]
    v=["Volatility 75 Index.0"]
    US =["Wall Street 30.0"]
    
    return {
        "H1_PENDING": Jump+J ,
        "H1_INSTANT": [XAUUSD]+US,
        "M15_PENDING": Jump+[XAUUSD]+v,
        "M15_INSTANT": J,
        "M5_PENDING": [BTCUSD],
        "M5_INSTANT": MAJORS+J
    }

def get_all_deals():
    from_date = datetime(2026, 1, 13)
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
    from_date = datetime(2026, 1, 13)
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

        if order_type == "UNKNOWN":
            continue

        records.append({
            "Symbol": symbol,
            "Timeframe": tf_str,
            "Direction": direction,
            "Order Type": order_type,
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
        
        sl = safe_float_conversion(entry.get('sl', 0))
        tp = safe_float_conversion(entry.get('tp', 0))
        
        comment = str(entry.get('comment', '')).strip()
        tp1 = extract_tp1_from_comment(comment)
        
        net_profit = group['profit'].sum() + group['swap'].sum() + group['commission'].sum()
        net_profit = round(float(net_profit), 2)
        
        # Outcome & Reason
        if net_profit > 0:
            outcome = "WINNER"
            reason = "TP Hit"
        elif net_profit < 0:
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
        
        print(f"Total Profit: ${total_profit:.2f}")
        print(f"Win Rate: {win_rate:.1f}%")
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
    
    mt5.shutdown()
    print(f"\n✅ Comprehensive analysis completed successfully!")
    print(f"📁 Results saved to: {OUTPUT_FOLDER}")

if __name__ == "__main__":
    main()