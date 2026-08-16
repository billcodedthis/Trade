import pandas as pd
import numpy as np
import MetaTrader5 as mt5
import time
import mplfinance as mpf
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os
from pathlib import Path
import signal
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

MT5_PATH = "C:\\Program Files\\MetaTrader 5\\terminal64.exe"
if not mt5.initialize(path=MT5_PATH):
    print("❌ Failed to connect to MetaTrader 5", mt5.last_error())
    quit()
else:
    print("✅ Successfully connected to MT5!")

'''
# Login to your Deriv MT5 account
account_number = 40719643  # Replace with your Deriv MT5 account number
password = input(f"Enter password for {account_number}: ")  # Replace with your actual password
server = "Deriv-Demo"  # Change to "Deriv-Real" if using a real account


login_status = mt5.login(account_number, password, server)

if login_status:
    print("✅ Successfully connected to MT5!")
else:
    print("❌ Login failed. Check your credentials.")
    quit()
'''
# Define symbols and timeframes
FOREX_PAIRS = ["CHFJPY.0","USDCHF.0"]
XAUUSD = "XAUUSD.0"
BTCUSD="BTCUSD.0"
MAJORS = [ ]
V100 = "Volatility 100 Index.0"
BnC = ["Boom 900 Index.0"]
C=["Crash 900 Index.0"]
Jump = ["Jump 25 Index.0"]
J=["Jump 75 Index.0"]
vol = ["Volatility 10 Index.0","Volatility 50 Index.0"]
v=["Volatility 75 Index.0"]
SYNTHETICS = ["Step Index.0"]
US =["US Tech 100.0","Wall Street 30.0"]

TIMEFRAME_H1 = BnC+MAJORS+[XAUUSD,BTCUSD]+US+SYNTHETICS+Jump+J
H1_B= [XAUUSD,BTCUSD]+BnC+US+SYNTHETICS
H1_S=Jump+J
H1_BS=MAJORS
H1_pen= MAJORS+Jump+[BTCUSD]+J 
H1_pl= [XAUUSD]+US+SYNTHETICS+BnC

TIMEFRAME_M15= FOREX_PAIRS+vol+[XAUUSD,V100]+Jump+J
M15_B= [XAUUSD,V100]+FOREX_PAIRS+vol
M15_S=Jump+J
M15_BS=[]
M15_pen= Jump+FOREX_PAIRS+vol+[XAUUSD,V100]
M15_pl= J

active_channels = {}
levels={}

DOWNLOADS_FOLDER = str(Path.home() / "OneDrive - University of Ghana")
PLOTS_FOLDER = os.path.join(DOWNLOADS_FOLDER, "MT5_Regression_Channels_real_deriv")

# Create the folder if it doesn't exist
if not os.path.exists(PLOTS_FOLDER):
    os.makedirs(PLOTS_FOLDER)

def is_connected():
    try:
        MT5_PATH = "C:\\Program Files\\MetaTrader 5\\terminal64.exe"
        if not mt5.initialize(path=MT5_PATH):
            return False
        return True
    except:
        return False



def send_telegram_image(image_path, caption=""):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    channel_id = os.getenv("TELEGRAM_CHANNEL_ID_REAL_DERIV", "")
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"

    with open(image_path, "rb") as image_file:
        payload = {
            "chat_id": channel_id,
            "caption": caption,
            "parse_mode": "HTML"
        }
        files = {
            "photo": image_file
        }
        try:
            response = requests.post(url, data=payload, files=files)
            if response.status_code != 200:
                print(f"❌ Failed to send image to Telegram: {response.text}")
        except Exception as e:
            print(f"❌ Telegram image error: {e}")

def send_telegram_message(text):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    channel_id = os.getenv("TELEGRAM_CHANNEL_ID_REAL_DERIV", "")
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    payload = {
        "chat_id": channel_id,
        "text": text,
        "parse_mode": "HTML"
    }

    try:
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            print(f"❌ Failed to send message to Telegram: {response.text}")
    except Exception as e:
        print(f"❌ Telegram error: {e}")

def timeframe_to_str(timeframe):
    """Convert MT5 timeframe constant to human-readable string"""
    if timeframe == mt5.TIMEFRAME_M1: return "M1"
    elif timeframe == mt5.TIMEFRAME_M5: return "M5"
    elif timeframe == mt5.TIMEFRAME_M15: return "M15"
    elif timeframe == mt5.TIMEFRAME_M30: return "M30"
    elif timeframe in (mt5.TIMEFRAME_H1, 16385): return "H1"  # Handle both representations
    elif timeframe == mt5.TIMEFRAME_H4: return "H4"
    elif timeframe == mt5.TIMEFRAME_D1: return "D1"
    elif timeframe == mt5.TIMEFRAME_W1: return "W1"
    elif timeframe == mt5.TIMEFRAME_MN1: return "MN1"
    else: return str(timeframe)

def cleanup_old_plots(current_active_symbols):
    """Remove plot files for symbols that are no longer active"""
    current_files = {f for f in os.listdir(PLOTS_FOLDER) if f.endswith('.png')}
    active_files = {f"{symbol}_{timeframe_to_str(timeframe)}_channel.png" for symbol,timeframe in current_active_symbols}
    
    for file in current_files:
        if file not in active_files:
            try:
                os.remove(os.path.join(PLOTS_FOLDER, file))
                print(f"🗑️ Deleted old plot: {file}")
            except Exception as e:
                print(f"❌ Failed to delete {file}: {str(e)}")

def clean_manual_deleted():
    """Check for manually deleted plot files and remove corresponding channel data"""
    try:
        current_files = {f for f in os.listdir(PLOTS_FOLDER) if f.endswith('.png')}
        channels_to_remove = []
        
        # Find channels without corresponding plot files
        for symbol,timeframe in list(active_channels.keys()):
            expected_file = f"{symbol}_{timeframe_to_str(timeframe)}_channel.png"
            if expected_file not in current_files:
                channels_to_remove.append((symbol,timeframe))
        
        # Remove the channel data
        for symbol,timeframe in channels_to_remove:
            print(f"🚨 Plot file for {symbol}_{timeframe_to_str(timeframe)} was manually deleted - removing channel data")
            if (symbol, timeframe) in active_channels:
                del active_channels[(symbol,timeframe)]
            if (symbol, timeframe) in levels:
                del levels[(symbol,timeframe)]
                
    except Exception as e:
        print(f"⚠️ Error in clean_manual_deleted(): {str(e)}")

def plot_active_channels():
    current_active = set(active_channels.keys())

    for symbol,timeframe in current_active:
        try:
            channel_data = active_channels[(symbol,timeframe)]
            df = channel_data["df"].copy()

            if df.empty:
                print(f"⚠️ No candle data for {symbol}")
                continue

            original_length = channel_data["num_bars"]
            df_plot = df.copy()
            df_plot.set_index('time', inplace=True)

            upper_line = df_plot['upper']  # Already extended with slope
            lower_line = df_plot['lower']
            trend_line = df_plot['trend']

            apds = [
                mpf.make_addplot(upper_line, color='blue', width=1.2, linestyle='-', label='Upper Channel'),
                mpf.make_addplot(lower_line, color='blue', width=1.2, linestyle='-', label='Lower Channel'),
                mpf.make_addplot(trend_line, color='orange', width=1.5, linestyle='-', label='Trend Line'),
            ]

            breakout_idx = channel_data.get('breakout_idx')
            if breakout_idx is not None and breakout_idx < len(df_plot):
                scatter_breakouts = pd.Series(index=df_plot.index, dtype='float64')
                scatter_breakouts.iloc[breakout_idx] = df_plot['close'].iloc[breakout_idx]
                apds.append(mpf.make_addplot(scatter_breakouts, type='scatter', markersize=200,
                                              marker='^', color='green', label='Breakout'))

            last_touch_price = channel_data.get('last_touch_price')
            if last_touch_price is not None and isinstance(last_touch_price, float):
                last_touch_line = pd.Series(last_touch_price, index=df_plot.index)
                apds.append(mpf.make_addplot(last_touch_line, color='red', width=1.5,
                                             linestyle='--', label='Last Touch Price'))

            if (symbol, timeframe) in levels and levels[(symbol,timeframe)].get("tp1") is not None:
                fib_levels = levels[(symbol,timeframe)]
                fib_colors = {
                    'sl': ('darkred', ':', 'Stop Loss'),
                    'sl1': ('red', ':', 'Secondary SL'),
                    'tp1': ('darkgreen', ':', 'Take Profit 1'),
                    'tp2': ('limegreen', ':', 'Take Profit 2'),
                    'tp3': ('lime', ':', 'Take Profit 3'),
                    'sniper': ('purple', ':', 'Sniper Entry')
                }

                for level in ['sl', 'sl1', 'tp1', 'tp2', 'tp3', 'sniper']:
                    if level in fib_levels:
                        color, linestyle, label = fib_colors[level]
                        level_line = pd.Series(fib_levels[level], index=df_plot.index)
                        price_label = f"{label} ({fib_levels[level]:.5f})"
                        apds.append(mpf.make_addplot(
                            level_line,
                            color=color,
                            width=1.5,
                            linestyle=linestyle,
                            label=price_label
                        ))

            fig, axes = mpf.plot(
                df_plot,
                type='candle',
                style='yahoo',
                title=f"{symbol} Regression Channel ({timeframe_to_str(channel_data['timeframe'])})",
                ylabel='Price',
                addplot=apds,
                volume=False,
                figsize=(14, 10),
                returnfig=True,
                scale_width_adjustment=dict(lines=0.5)
            )

            if axes:
                axes[0].legend(
                    loc='upper left',
                    bbox_to_anchor=(0.02, 0.98),
                    framealpha=0.7,
                    fontsize='small'
                )

                # In the plot_active_channels function, update this section:
                channel_text = f"Channel Bars: {original_length}\n"
                channel_text += f"Extended Bars: {len(df_plot) - original_length}"  # Calculate extended bars
                axes[0].text(
                    0.90, 0.98, channel_text,
                    transform=axes[0].transAxes,
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.8),
                    fontsize=9
                )

                if (symbol, timeframe) in levels:
                    fib_text = "Fibonacci Levels:\n"
                    for level in ['sniper', 'sl', 'sl1', 'tp1', 'tp2', 'tp3']:
                        if level in levels[(symbol,timeframe)]:
                            fib_text += f"{level.upper()}: {levels[(symbol,timeframe)][level]:.5f}\n"

                    axes[0].text(
                        0.02, 0.02, fib_text,
                        transform=axes[0].transAxes,
                        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8),
                        fontsize=9
                    )

            plot_filename = os.path.join(PLOTS_FOLDER, f"{symbol}_{timeframe_to_str(timeframe)}_channel.png")
            fig.savefig(plot_filename, dpi=150, bbox_inches='tight')
            plt.close(fig)
            

        except Exception as e:
            print(f"❌ Error plotting channel for {symbol,timeframe}: {str(e)}")
            continue

    cleanup_old_plots(current_active)

def clear_plots_folder():
    """Clear all plot files from the folder"""
    if os.path.exists(PLOTS_FOLDER):
        for filename in os.listdir(PLOTS_FOLDER):
            file_path = os.path.join(PLOTS_FOLDER, filename)
            try:
                if os.path.isfile(file_path) and filename.endswith('.png'):
                    os.unlink(file_path)
                    #print(f"🗑️ Deleted plot file: {filename}")
            except Exception as e:
                print(f"❌ Failed to delete {file_path}: {e}")

def signal_handler(sig, frame):
    """Handle interrupt signals"""
    send_telegram_message("Deriv Bot stopped")
    print("\n🛑 Script interrupted - cleaning up...")
    clear_plots_folder()
    mt5.shutdown()
    sys.exit(0)

def get_min_lot_size(symbol):
    info = mt5.symbol_info(symbol)
    if info:
        return info.volume_min
    else:
        return None

def get_candles(symbol, timeframe, num_bars):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, num_bars)
    if rates is None or len(rates) == 0:
        print(f"❌ No data received for {symbol} on timeframe {timeframe}")
        return pd.DataFrame()
    df = pd.DataFrame(rates)
    if 'tick_volume' in df.columns:
        df['volume'] = df['tick_volume']
    else:
        df['volume'] = 0  # Fallback
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df

def update_channel_data(symbol,timeframe):
    """Fetch new candles and append to existing channel data without extending original channel lines"""
    if (symbol, timeframe) not in active_channels:
        return False

    channel_data = active_channels[(symbol,timeframe)]
    timeframe = channel_data["timeframe"]
    last_time = channel_data["last_time"]
    num_bars = channel_data["num_bars"]
    
    # Fetch last 30 candles to ensure we get all new data
    new_candles = get_candles(symbol, timeframe, num_bars)
    
    new_data = new_candles[new_candles['time'] > last_time].copy()
    
    
    if new_data.empty:
        return False

    for col in ['upper', 'lower', 'trend']:
        if col not in new_data.columns:
            new_data[col] = np.nan

    df = channel_data["df"]
    
    # Calculate slope (price change per bar)
    trend_vector = (df['trend'].iloc[-1] - df['trend'].iloc[-3]) / 2  # Last 2 bars' movement
    upper_vector = (df['upper'].iloc[-1] - df['upper'].iloc[-3]) / 2
    lower_vector = (df['lower'].iloc[-1] - df['lower'].iloc[-3]) / 2

    # Extend new candles organically
    for i in range(len(new_data)):
        if (symbol, timeframe) in levels:
            break
        bars_from_end = i + 1
        new_data.at[new_data.index[i], 'trend'] = df['trend'].iloc[-2] + (trend_vector * bars_from_end)
        new_data.at[new_data.index[i], 'upper'] = df['upper'].iloc[-2] + (upper_vector * bars_from_end)
        new_data.at[new_data.index[i], 'lower'] = df['lower'].iloc[-2] + (lower_vector * bars_from_end)

        
    # Concatenate with existing data
    updated_df = pd.concat([channel_data["df"], new_data], ignore_index=True)
    updated_df = updated_df.drop_duplicates(subset='time', keep='last').reset_index(drop=True)


    # Update the channel data
    active_channels[(symbol,timeframe)]["df"] = updated_df
    active_channels[(symbol,timeframe)]["last_time"] = updated_df['time'].iloc[-2]

    if (symbol, timeframe) in levels :
        return True
    else:
        df = active_channels[(symbol,timeframe)]["df"]
        last = df.iloc[-10:]
        upper = df['upper'].iloc[-1]       # Access upper line from DataFrame
        lower = df['lower'].iloc[-1]       # Access lower line from DataFrame
        last_trend = df['trend']     
        trend_slope = last_trend.iloc[-1] - last_trend.iloc[0]
        for i in range(len(last)):
            candle = last.iloc[i]
            broke_above = candle['high'] > upper
            broke_below = candle['low'] < lower

            # Breakout matches trend direction? Then delete
            if symbol in H1_B+M15_B:
                if (trend_slope > 0 ) or (trend_slope < 0 and broke_below):
                        print(f"🚨 {symbol}_{timeframe_to_str(timeframe)} broke out in the direction of the trend — clearing it.")
                        del active_channels[(symbol,timeframe)]
                        break# Skip further processing this round
            elif symbol in H1_BS+M15_BS:
                if (trend_slope > 0  and broke_above) or (trend_slope < 0 and broke_below):
                        print(f"🚨 {symbol}_{timeframe_to_str(timeframe)} broke out in the direction of the trend — clearing it.")
                        del active_channels[(symbol,timeframe)]
                        break# Skip further processing this round
            elif symbol in H1_S+M15_S:
                    if (trend_slope > 0  and broke_above) or (trend_slope < 0 ):
                        print(f"🚨 {symbol}_{timeframe_to_str(timeframe)} broke out in the direction of the trend — clearing it.")
                        del active_channels[(symbol,timeframe)]
                        break# Skip further processing this round

    return True

def detect_regression_channel(df):
    # Split data - exclude last 5 candles for analysis but keep full data for plotting
    analysis_df = df.iloc[:-10].copy()
    full_df = df.copy()
    
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

    # YOUR ORIGINAL VALIDATION LOGIC EXACTLY AS WAS (but using analysis_df)
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

        # Original touch counting logic (unchanged)
        if analysis_df['high'].iloc[i] > upper[i]:
            extreme_price = analysis_df['high'].iloc[i]
            new_upper_adjustment = extreme_price - upper[i]
            upper += new_upper_adjustment
            upper_full += new_upper_adjustment  # Mirror adjustment in full data
            full_df['upper'] = upper_full
            
        if analysis_df['high'].iloc[i] == upper[i] and not recent_upper_touch:
            upper_touch_count += 1
            upper_touch_indices.append(i)
            
        if analysis_df['low'].iloc[i] < lower[i]:
            extreme_price = analysis_df['low'].iloc[i]
            new_lower_adjustment = extreme_price - lower[i]
            lower += new_lower_adjustment
            lower_full += new_lower_adjustment  # Mirror adjustment in full data
            full_df['lower'] = lower_full
            
        if analysis_df['low'].iloc[i] == lower[i] and not recent_lower_touch:
            lower_touch_count += 1
            lower_touch_indices.append(i)

        # Original breakout logic (unchanged)
        if analysis_df['close'].iloc[i-1] <= upper[i-1] and analysis_df['close'].iloc[i] > upper[i-1]:
            breakout = i
            direction = 'upper'
        elif analysis_df['close'].iloc[i-1] >= lower[i-1] and analysis_df['close'].iloc[i] < lower[i-1]:
            breakout = i
            direction = 'lower'

        # Original breakout validation (unchanged)
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
                
                for k in range(1, len(analysis_df)):
                    if analysis_df['high'].iloc[k] >= upper[k]:
                        upper_touch_count += 1
                    if analysis_df['low'].iloc[k] <= lower[k]:
                        lower_touch_count += 1
        
        # Check for touch imbalance and adjust boundaries if needed
        if upper_touch_count >= 2 and lower_touch_count == 0:
            # Adjust lower boundary to be closer to trend line
            lower = trend_line - 2 * std_dev  # Was -3, increase
            lower_full = trend_line_full - 2 * std_dev
            full_df['lower'] = lower_full
            
            # Re-count touches with new boundaries
            for k in range(1, len(analysis_df)):
                recent_lower_touch = any((i - idx) <= 5 for idx in lower_touch_indices)
                if analysis_df['low'].iloc[i] < lower[i]:
                    extreme_price = analysis_df['low'].iloc[i]
                    new_lower_adjustment = extreme_price - lower[i]
                    lower += new_lower_adjustment
                    lower_full += new_lower_adjustment  # Mirror adjustment in full data
                    full_df['lower'] = lower_full
                    
                if analysis_df['low'].iloc[i] == lower[i] and not recent_lower_touch:
                    lower_touch_count += 1
                    lower_touch_indices.append(i)
                
                if analysis_df['close'].iloc[i-1] <= upper[i-1] and analysis_df['close'].iloc[i] > upper[i-1]:
                    breakout = i
                    direction = 'upper'
                elif analysis_df['close'].iloc[i-1] >= lower[i-1] and analysis_df['close'].iloc[i] < lower[i-1]:
                    breakout = i
                    direction = 'lower'

                # Original breakout validation (unchanged)
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
                            if analysis_df['high'].iloc[m] >= upper[m]:
                                upper_touch_count += 1
                            if analysis_df['low'].iloc[m] <= lower[m]:
                                lower_touch_count += 1
                    
        elif lower_touch_count >= 2 and upper_touch_count == 0:
            # Adjust upper boundary to be closer to trend line
            upper = trend_line + std_dev  # Was +2, decrease
            upper_full = trend_line_full + std_dev
            full_df['upper'] = upper_full
            
            # Re-count touches with new boundaries
            for k in range(1, len(analysis_df)):
                recent_upper_touch = any((i - idx) <= 5 for idx in upper_touch_indices)
                if analysis_df['high'].iloc[i] > upper[i]:
                    extreme_price = analysis_df['high'].iloc[i]
                    new_upper_adjustment = extreme_price - upper[i]
                    upper += new_upper_adjustment
                    upper_full += new_upper_adjustment  # Mirror adjustment in full data
                    full_df['upper'] = upper_full
                    
                if analysis_df['high'].iloc[i] == upper[i] and not recent_upper_touch:
                    upper_touch_count += 1
                    upper_touch_indices.append(i)
                
                if analysis_df['close'].iloc[i-1] <= upper[i-1] and analysis_df['close'].iloc[i] > upper[i-1]:
                    breakout = i
                    direction = 'upper'
                elif analysis_df['close'].iloc[i-1] >= lower[i-1] and analysis_df['close'].iloc[i] < lower[i-1]:
                    breakout = i
                    direction = 'lower'

                # Original breakout validation (unchanged)
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
                            if analysis_df['high'].iloc[m] >= upper[m]:
                                upper_touch_count += 1
                            if analysis_df['low'].iloc[m] <= lower[m]:
                                lower_touch_count += 1
                

        # Original validation condition (unchanged)
        if (upper_touch_count >= 2 and lower_touch_count >= 1) or (upper_touch_count >= 1 and lower_touch_count >= 2):
            validated = True
            break
    
    return validated, full_df

def find_valid_entry(df, breakout_idx, last_touch_idx,symbol,timeframe):
    if last_touch_idx is None or breakout_idx is None:
        return None
        
    # Get the price from active_channels instead of using the index directly
    channel_data = active_channels[(symbol,timeframe)]
    last_touch_price = channel_data["last_touch_price"]
    if last_touch_price is None:
        return None
        
    entry_candle_idx = None
    
    for i in range(breakout_idx+1, len(df)):
        if df['open'].iloc[i] > last_touch_price and df['low'].iloc[i] > df['upper'].iloc[i]: 
            entry_candle_idx = i-1
            break
        elif df['open'].iloc[i] < last_touch_price and df['high'].iloc[i] < df['lower'].iloc[i]: 
            entry_candle_idx = i-1
            break
    
    if entry_candle_idx is None:
        return None
    
    last_trend = df["trend"]
    trend_slope = last_trend.iloc[-1] - last_trend.iloc[0]

    count = 0
    for j in range(entry_candle_idx + 1, min(entry_candle_idx + 6, len(df))):
        if trend_slope<0 and (df['close'].iloc[j] > df['close'].iloc[entry_candle_idx] and df['low'].iloc[j] > df['low'].iloc[entry_candle_idx]) :
            count+=1
        elif trend_slope>0 and (df['close'].iloc[j] < df['close'].iloc[entry_candle_idx] and df['high'].iloc[j] < df['high'].iloc[entry_candle_idx] ):
            count += 1
        
        if count >= 3:
            if (symbol, timeframe) in active_channels:
                del active_channels[(symbol,timeframe)]
            if (symbol, timeframe) in levels:
                del levels[(symbol,timeframe)]
            return None
    
    return entry_candle_idx

def detect_break(df, symbol,timeframe):
    channel_data = active_channels[(symbol,timeframe)]
    data = channel_data["df"] 
    df['trend'] = data["trend"]
    df['upper'] = data["upper"]
    df['lower'] = data["lower"]
    breakout = None
    trend_slope = df['trend'].iloc[-1] - df['trend'].iloc[0]
    last_touch_found = False
    
    for i in range(1,len(df)):
        if df['close'].iloc[i-1] <= df['upper'][i-1] and df['close'].iloc[i] > df['upper'][i-1]:
            if trend_slope < 0:
                breakout = i
                active_channels[(symbol,timeframe)]["breakout_idx"] = breakout
                # Find last touch before breakout
                for j in range(breakout - 10, 0, -1):
                    if df['high'].iloc[j] >= df['upper'].iloc[j]:
                        if df['close'].iloc[j] < df['open'].iloc[j] and df['open'].iloc[j] > df['upper'].iloc[breakout]:
                                active_channels[(symbol,timeframe)]["last_touch_price"] = df['open'].iloc[j]
                                active_channels[(symbol,timeframe)]["last_touch_idx"] = j
                                last_touch_found = True
                                break
                        elif df['close'].iloc[j] > df['open'].iloc[j] and df['close'].iloc[j] > df['upper'].iloc[breakout]:
                                active_channels[(symbol,timeframe)]["last_touch_price"] = df['close'].iloc[j]
                                active_channels[(symbol,timeframe)]["last_touch_idx"] = j
                                last_touch_found = True
                                break
                break

        elif df['close'].iloc[i-1] >= df['lower'][i-1] and df['close'].iloc[i] < df['lower'][i-1]:
            if trend_slope > 0:
                breakout = i
                active_channels[(symbol,timeframe)]["breakout_idx"] = breakout
                # Find last touch before breakout
                for j in range(breakout - 10, 0, -1):
                    if df['low'].iloc[j] <= df['lower'].iloc[j]:
                        if df['close'].iloc[j] > df['open'].iloc[j] and df['open'].iloc[j] < df['lower'].iloc[breakout]:
                                active_channels[(symbol,timeframe)]["last_touch_price"] = df['open'].iloc[j]
                                active_channels[(symbol,timeframe)]["last_touch_idx"] = j
                                last_touch_found = True
                                break
                        elif df['close'].iloc[j] < df['open'].iloc[j] and df['close'].iloc[j] < df['lower'].iloc[breakout]:
                                active_channels[(symbol,timeframe)]["last_touch_price"] = df['close'].iloc[j]
                                active_channels[(symbol,timeframe)]["last_touch_idx"] = j
                                last_touch_found = True
                                break
                break
    if breakout is not None and not last_touch_found:
        print(f"🚨 No last touch found for {symbol} - deleting channel.")
        if (symbol, timeframe) in active_channels:
            del active_channels[(symbol,timeframe)]
        if (symbol, timeframe) in levels:
            del levels[(symbol,timeframe)]

def apply_fibonacci_levels(symbol, entry_idx, df,timeframe):
    if entry_idx is None:
        return None
    entry_price = df['close'].iloc[entry_idx]
    last_opposite_idx = None
    
    # Find the last opposite-colored candle before entry
    for i in range(entry_idx , 0, -1):
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
    
    if is_buy:
        levels[(symbol,timeframe)] = {
            "sl": swing_point - (0.9 * risk),
            "tp1": swing_point + (1.8 * risk),
            "tp2": swing_point + (2.8 * risk),
            "tp3": entry_price + (3.5 * risk),
            "sniper": swing_point + (0.3 * risk), 
            "sl1": swing_point - (0.2 * risk),
            "direction": "BUY"   
        }
    else:
        levels[(symbol,timeframe)] = {
            "sl": swing_point + (0.9 * risk),
            "tp1": swing_point - (1.8 * risk),
            "tp2": swing_point - (2.8 * risk),
            "tp3": entry_price - (3.5 * risk),
            "sniper": swing_point - (0.3 * risk), 
            "sl1": swing_point   + (0.2 * risk),
            "direction": "SELL"
        }
    
    return levels[(symbol,timeframe)]

def format_tp_comment(tp1, tp2):
    """Encode tp1 and tp2 into the compact pipe-delimited order/position comment."""
    return f"{tp1}|{tp2}"

def extract_tp_levels_from_comment(comment):
    """Decode the pipe-delimited comment back into (tp1, tp2). Returns (None, None) on failure."""
    if not comment or pd.isna(comment) if hasattr(pd, "isna") else not comment:
        return None, None
    try:
        parts = str(comment).split("|")
        if len(parts) < 2:
            return None, None
        return float(parts[0]), float(parts[1])
    except (ValueError, TypeError):
        return None, None
    
def pending(symbol, direction, entry_price, sl, tp,sniper,timeframe):
    if abs(sl - sniper) >= abs(tp - sniper):
        print(f"🚫 pending Trade not placed: SL is greater than TP for {symbol}.")
        return
    orders = mt5.orders_get(symbol=symbol)
    for order in orders:
        if timeframe == order.magic:
            print(f"🚫 pending Trade not placed: An order already exists for {symbol}.")
            return
    positions = mt5.positions_get(symbol=symbol)
    if positions is not None:
        for position in positions:
            if timeframe == position.magic:
                print(f"🚫 pending Trade not placed: An open position already exists for {symbol}.")
                return
    request1 = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "volume": get_min_lot_size(symbol) *2 ,
            "type": mt5.ORDER_TYPE_BUY_LIMIT if direction == "BUY" else mt5.ORDER_TYPE_SELL_LIMIT,
            "price": sniper,
            "sl": sl,
            "tp": tp,
            "deviation": 10,
            "magic": timeframe,
            "comment": format_tp_comment(levels[(symbol,timeframe)]["tp1"], levels[(symbol,timeframe)]["tp2"]),
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
    order = mt5.order_send(request1)
    if order.retcode == mt5.TRADE_RETCODE_DONE:
        plot_filename = os.path.join(PLOTS_FOLDER, f"{symbol}_{timeframe_to_str(timeframe)}_channel.png")
        send_telegram_image(plot_filename,f"📥 <b>Deriv Pending Trade</b>\nSymbol: {symbol}\nDirection: {direction}\nEntry: {sniper:.4f}\nSL: {sl:.4f}\nTP1: {levels[(symbol,timeframe)]["tp1"]:.4f}\nTP2: {levels[(symbol,timeframe)]["tp2"]:.4f}\nTP3: {tp:.4f}")
        print(f"Pending Trade placed: {direction} {symbol} @ {sniper}")
    else:
        print(f"{symbol}, pending {direction}@{entry_price} sl:{sl},tp:{tp} failed: {order.comment}")

def place_trade(symbol, direction, entry_price, sl1, tp,timeframe):
    if abs(sl1 - entry_price) >= abs(tp - entry_price):
        print(f"🚫 Trade not placed: SL is greater than TP for {symbol}.")
        return
    positions = mt5.positions_get(symbol=symbol)
    if positions is not None:
        for position in positions:
            if timeframe==position.magic:
                print(f"🚫 Trade not placed: An open position already exists for {symbol}.")
                return
    request = {
        "action": mt5.TRADE_ACTION_DEAL ,
        "symbol": symbol,
        "volume": get_min_lot_size(symbol) * 2  ,
        "type": mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL,
        "price": entry_price,
        "sl": sl1,
        "tp": tp,
        "deviation": 10,
        "magic": timeframe,
        "comment": format_tp_comment(levels[(symbol,timeframe)]["tp1"], levels[(symbol,timeframe)]["tp2"]),
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }
    order = mt5.order_send(request)
    if order.retcode == mt5.TRADE_RETCODE_DONE:
        plot_filename = os.path.join(PLOTS_FOLDER, f"{symbol}_{timeframe_to_str(timeframe)}_channel.png")
        send_telegram_image(plot_filename,f"🚀 <b>Deriv Market Trade</b>\nSymbol: {symbol}\nDirection: {direction}\nEntry: {entry_price:.4f}\nSL: {sl1:.4f}\nTP1: {levels[(symbol,timeframe)]["tp1"]:.4f}\nTP2: {levels[(symbol,timeframe)]["tp2"]:.4f}\nTP3: {tp:.4f}")
        print(f"Trade placed: {direction} {symbol} @ {entry_price}")
    else:
        print(f"{symbol},{direction}@{entry_price} sl:{sl1},tp:{tp} failed: {order.comment}")

def modify_trade_to_breakeven(symbol, order_ticket, entry_price):
    position = mt5.positions_get(ticket=order_ticket)
    if position[0].sl == entry_price:
        print(f"Breakeven already applied on {symbol}")
        return
    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": order_ticket,
        "sl": entry_price,  # Move SL to break-even
        "tp":position[0].tp,
        "comment":position[0].comment,
        "magic":position[0].magic
    }
    result = mt5.order_send(request)
    
    if result is None:
        print(f"❌ Failed to modify trade {order_ticket}: No response from server.")
    else:
        print(f"📝 Modify Trade Response: {result}")
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"✅ SL moved to break-even for trade {order_ticket} on {symbol}.")
        else:
            print(f"❌ Failed to move SL: {result.comment} (Error Code: {result.retcode})")

def close_pending(symbol):
    orders = mt5.orders_get(symbol=symbol)
    if orders is None or len(orders) == 0:
        return  # No active trades

    for order in orders:
        tp= order.tp
        price = mt5.symbol_info_tick(symbol).bid if order.type == mt5.ORDER_TYPE_SELL_LIMIT else mt5.symbol_info_tick(symbol).ask
        if (order.type == mt5.ORDER_TYPE_BUY_LIMIT and price >= tp) or (order.type == mt5.ORDER_TYPE_SELL_LIMIT and price <= tp):
            request = {
                    "action": mt5.TRADE_ACTION_REMOVE,
                    "order": order.ticket,
                }
            result = mt5.order_send(request)
                
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                send_telegram_message(f"Delete deriv pending order for {symbol}.")
                print(f"✅ Deleted pending order {order.ticket} for {symbol}.")
            else:
                print(f"❌ Failed to delete order {order.ticket} for {symbol}: {result.comment}")
        else:
            print(f"Order still valid for {symbol} ")

def _cut_lot(volume, symbol):
    """Same fractional cut used by the engulfing-halving logic: closes ~1/3 of `volume`
    (volume - volume/1.5), applied fresh to whatever the current volume is."""
    return round(volume - (volume / 1.5), 2)

def check_tp1_and_manage_trades(symbol, tp1, timeframe):
    """Fires at (new) TP1: apply breakeven and close ~1/3 of the current position."""
    if isinstance(tp1, str):
        if tp1 == '':
            return
        Tp1, _tp2_unused = extract_tp_levels_from_comment(tp1)
        if Tp1 is None:
            return
        positions = mt5.positions_get(symbol=symbol)
    else:
        Tp1 = tp1
        positions = mt5.positions_get(symbol=symbol, magic=timeframe)

    if positions is not None:
        for position in positions:
            if position.magic != timeframe:
                continue
            entry_price = position.price_open
            current_price = mt5.symbol_info_tick(symbol).bid if position.type == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(symbol).ask

            # TP1 logic: breakeven + close ~1/3 of current position
            if (position.type == mt5.ORDER_TYPE_BUY and current_price >= Tp1) or \
            (position.type == mt5.ORDER_TYPE_SELL and current_price <= Tp1):
                if position.volume == get_min_lot_size(symbol):
                    modify_trade_to_breakeven(symbol, position.ticket, entry_price)
                    continue
                if position.sl == position.price_open:
                    print(f"✅ Position {position.ticket} for {symbol} already processed at TP1 (breakeven already applied).")
                    continue
                cut_lot = _cut_lot(position.volume, symbol)
                close_request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": cut_lot,
                    "type": mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
                    "position": position.ticket,
                    "price": current_price,
                    "comment": position.comment,
                    "deviation": 10,
                    "magic": position.magic,
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_FOK,
                }
                close_result = mt5.order_send(close_request)
                if close_result.retcode == mt5.TRADE_RETCODE_DONE:
                    send_telegram_message(f"TP1 hit. Apply breakeven and close ~1/3 of deriv positions for {symbol} trade.✅")
                    print(f"✅ Closed ~1/3 of position {position.ticket} for {symbol} at TP1.")
                    modify_trade_to_breakeven(symbol, position.ticket, entry_price)
                elif close_result.comment == "Invalid volume":
                    send_telegram_message(f"TP1 hit. Apply breakeven for deriv {symbol} trade (volume too small to cut).✅")
                    print(f"{symbol} cannot be cut, but SL has been moved to breakeven.")
                    modify_trade_to_breakeven(symbol, position.ticket, entry_price)
                else:
                    print(f"❌ Failed to close portion of {symbol}: {close_result.comment}")

def check_tp2_and_manage_trades(symbol, tp2, timeframe):
    """Fires at TP2 (the old TP1): close ~1/3 of whatever volume currently remains.
    Breakeven should already be applied from TP1, but this checks defensively rather
    than assuming it, to handle the edge case where TP1 was skipped/slipped past."""
    if isinstance(tp2, str):
        if tp2 == '':
            return
        _tp1_unused, Tp2 = extract_tp_levels_from_comment(tp2)
        if Tp2 is None:
            return
        positions = mt5.positions_get(symbol=symbol)
    else:
        Tp2 = tp2
        positions = mt5.positions_get(symbol=symbol, magic=timeframe)

    if positions is not None:
        for position in positions:
            if position.magic != timeframe:
                continue
            entry_price = position.price_open
            current_price = mt5.symbol_info_tick(symbol).bid if position.type == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(symbol).ask

            if (position.type == mt5.ORDER_TYPE_BUY and current_price >= Tp2) or \
            (position.type == mt5.ORDER_TYPE_SELL and current_price <= Tp2):
                # Defensive breakeven check - normally already applied at TP1, but don't assume it
                if position.sl != position.price_open:
                    modify_trade_to_breakeven(symbol, position.ticket, entry_price)
                if position.volume == get_min_lot_size(symbol):
                    continue
                cut_lot = _cut_lot(position.volume, symbol)
                close_request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": cut_lot,
                    "type": mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
                    "position": position.ticket,
                    "price": current_price,
                    "comment": position.comment,
                    "deviation": 10,
                    "magic": position.magic,
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_FOK,
                }
                close_result = mt5.order_send(close_request)
                if close_result.retcode == mt5.TRADE_RETCODE_DONE:
                    send_telegram_message(f"TP2 hit. Closed further portion of deriv position for {symbol} trade.✅")
                    print(f"✅ Closed further portion of position {position.ticket} for {symbol} at TP2.")
                elif close_result.comment == "Invalid volume":
                    print(f"{symbol} cannot be cut further at TP2 (volume too small).")
                else:
                    print(f"❌ Failed to close portion of {symbol} at TP2: {close_result.comment}")
 
def del_completed():
    if levels:
        for (symbol,timeframe) in list(levels.keys()):  # Use list to avoid runtime modification issues
            L = levels[(symbol,timeframe)]
            direction = L.get("direction")
            if not direction:
                continue

            # Get current price
            current_price = mt5.symbol_info_tick(symbol).bid  # Use current market price

            # Check SL
            if (direction == "BUY" and current_price <= L["sl"]) or (direction == "SELL" and current_price >= L["sl"]):
                # Hit SL - delete channel and levels
                if (symbol, timeframe) in active_channels:
                    send_telegram_message(f"🚨 {symbol} hit Deriv SL on {timeframe_to_str(timeframe)}")
                    del active_channels[(symbol,timeframe)]
                if (symbol, timeframe) in levels:
                    del levels[(symbol,timeframe)]
                print(f"🚨 {symbol} hit SL - channel removed.")
                continue  # Skip TP check since we already hit SL

            # Check TP3 (final target)
            if (direction == "BUY" and current_price >= L["tp3"]) or (direction == "SELL" and current_price <= L["tp3"]):
                # Hit TP3 - delete channel and levels
                if (symbol, timeframe) in active_channels:
                    plot_filename = os.path.join(PLOTS_FOLDER, f"{symbol}_{timeframe_to_str(timeframe)}_channel.png")
                    send_telegram_image(plot_filename, f"✅ {symbol} hit Deriv TP3 on {timeframe_to_str(timeframe)}")
                    del active_channels[(symbol,timeframe)]
                if (symbol, timeframe) in levels:
                    del levels[(symbol,timeframe)]
                print(f"✅ {symbol} hit TP3 - channel removed.")  
        
            

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

clear_plots_folder()

send_telegram_message("Deriv Bot running")
while True:
    try:
        if not is_connected():
            print("🚫 Network or MT5 disconnected.")
            clear_plots_folder()
            mt5.shutdown()
            sys.exit("❌ Terminating script due to disconnection.")

        clean_manual_deleted()
        del_completed()
        active=[]
        for symbol in TIMEFRAME_H1 :
                timeframe = mt5.TIMEFRAME_H1
                if (symbol, timeframe) not in active_channels:
                    num_bars = [40,50,60,70,80,100]
                    for i in num_bars:
                        candles = get_candles(symbol, timeframe, i)
                        if candles.empty:
                            continue
                        channel  = detect_regression_channel(candles)
                        if channel[0] == True:
                            # Save channel and breakout info
                            active_channels[(symbol,timeframe)] = {
                                    "df": channel[1].copy(),
                                    "breakout_idx": None,
                                    "last_touch_idx": None,
                                    "last_touch_price":None,
                                    "num_bars":i,
                                    "timeframe":timeframe,
                                    "last_time" :channel[1]['time'].iloc[-2]
                            }
                            df = active_channels[(symbol,timeframe)]["df"]
                            last = df.iloc[-10:]
                            upper = df['upper'].iloc[-1]       # Access upper line from DataFrame
                            lower = df['lower'].iloc[-1]       # Access lower line from DataFrame
                            last_trend = df['trend']     
                            trend_slope = last_trend.iloc[-1] - last_trend.iloc[0]
                            for i in range(len(last)):
                                candle = last.iloc[i]
                                broke_above = candle['high'] > upper
                                broke_below = candle['low'] < lower

                                # Breakout matches trend direction? Then delete
                                if symbol in H1_B:
                                    if (trend_slope > 0 ) or (trend_slope < 0 and broke_below):
                                            print(f"🚨 {symbol}_{timeframe_to_str(timeframe)} broke out in the direction of the trend — clearing it.")
                                            del active_channels[(symbol,timeframe)]
                                            break# Skip further processing this round
                                elif symbol in H1_BS:
                                    if (trend_slope > 0  and broke_above) or (trend_slope < 0 and broke_below):
                                            print(f"🚨 {symbol}_{timeframe_to_str(timeframe)} broke out in the direction of the trend — clearing it.")
                                            del active_channels[(symbol,timeframe)]
                                            break# Skip further processing this round
                                elif symbol in H1_S:
                                    if (trend_slope > 0  and broke_above) or (trend_slope < 0 ):
                                            print(f"🚨 {symbol}_{timeframe_to_str(timeframe)} broke out in the direction of the trend — clearing it.")
                                            del active_channels[(symbol,timeframe)]
                                            break# Skip further processing this round
                            break
                
                else:
                        update_channel_data(symbol,timeframe)
                        if (symbol, timeframe) not in active_channels:
                            continue
                        candles = active_channels[(symbol,timeframe)]["df"]
                        detect_break(candles, symbol,timeframe)
                        if (symbol, timeframe) not in active_channels:
                            continue
                        breakout_idx = active_channels[(symbol,timeframe)]['breakout_idx']
                        last_touch_idx = active_channels[(symbol,timeframe)]['last_touch_idx']
                        entry_idx = find_valid_entry(candles, breakout_idx, last_touch_idx,symbol,timeframe)
                        if (symbol, timeframe) not in active_channels:
                            continue
                        if entry_idx:
                            fib_levels = apply_fibonacci_levels(symbol,entry_idx, candles,timeframe)
                            if fib_levels:
                                    direction = "BUY" if candles['close'].iloc[entry_idx] > candles['upper'].iloc[entry_idx] else "SELL"
                                    if symbol in H1_pen :
                                        pending(symbol, direction, candles['close'].iloc[entry_idx], fib_levels['sl'], fib_levels['tp3'],fib_levels['sniper'],timeframe)
                                    elif symbol in H1_pl:
                                        place_trade(symbol, direction, candles['close'].iloc[entry_idx], fib_levels['sl1'], fib_levels['tp3'],timeframe)
                if (symbol, timeframe) in levels :
                    L =levels[(symbol,timeframe)]
                    check_tp1_and_manage_trades(symbol, L["tp1"], timeframe)
                    check_tp2_and_manage_trades(symbol, L["tp2"], timeframe)
                else:
                    positions = mt5.positions_get(symbol=symbol)
                    if positions is not None:
                        for position in positions:
                            check_tp1_and_manage_trades(symbol, position.comment, timeframe)
                            check_tp2_and_manage_trades(symbol, position.comment, timeframe)
                close_pending(symbol)
 
        for symbol in TIMEFRAME_M15 :
                timeframe = mt5.TIMEFRAME_M15
                if (symbol, timeframe) not in active_channels:
                    num_bars = [40,50,60,70,80]
                    for i in num_bars:
                        candles = get_candles(symbol, timeframe, i)
                        if candles.empty:
                            continue
                        channel  = detect_regression_channel(candles)
                        if channel[0] == True:
                            # Save channel and breakout info
                            active_channels[(symbol,timeframe)] = {
                                    "df": channel[1].copy(),
                                    "breakout_idx": None,
                                    "last_touch_idx": None,
                                    "last_touch_price":None,
                                    "num_bars":i,
                                    "timeframe":timeframe,
                                    "last_time" :channel[1]['time'].iloc[-2]
                            }
                            df = active_channels[(symbol,timeframe)]["df"]
                            last = df.iloc[-10:]
                            upper = df['upper'].iloc[-1]       # Access upper line from DataFrame
                            lower = df['lower'].iloc[-1]       # Access lower line from DataFrame
                            last_trend = df['trend']     
                            trend_slope = last_trend.iloc[-1] - last_trend.iloc[0]
                            for i in range(len(last)):
                                candle = last.iloc[i]
                                broke_above = candle['high'] > upper
                                broke_below = candle['low'] < lower

                                # Breakout matches trend direction? Then delete
                                if symbol in M15_B:
                                    if (trend_slope > 0 ) or (trend_slope < 0 and broke_below):
                                            print(f"🚨 {symbol}_{timeframe_to_str(timeframe)} broke out in the direction of the trend — clearing it.")
                                            del active_channels[(symbol,timeframe)]
                                            break# Skip further processing this round
                                elif symbol in M15_BS:
                                    if (trend_slope > 0  and broke_above) or (trend_slope < 0 and broke_below):
                                            print(f"🚨 {symbol}_{timeframe_to_str(timeframe)} broke out in the direction of the trend — clearing it.")
                                            del active_channels[(symbol,timeframe)]
                                            break# Skip further processing this round
                                elif symbol in M15_S:
                                    if (trend_slope > 0  and broke_above) or (trend_slope < 0 ):
                                            print(f"🚨 {symbol}_{timeframe_to_str(timeframe)} broke out in the direction of the trend — clearing it.")
                                            del active_channels[(symbol,timeframe)]
                                            break# Skip further processing this round
                            break
                
                else:
                        update_channel_data(symbol,timeframe)
                        if (symbol, timeframe) not in active_channels:
                            continue
                        candles = active_channels[(symbol,timeframe)]["df"]
                        detect_break(candles, symbol,timeframe)
                        if (symbol, timeframe) not in active_channels:
                            continue
                        breakout_idx = active_channels[(symbol,timeframe)]['breakout_idx']
                        last_touch_idx = active_channels[(symbol,timeframe)]['last_touch_idx']
                        entry_idx = find_valid_entry(candles, breakout_idx, last_touch_idx,symbol,timeframe)
                        if (symbol, timeframe) not in active_channels:
                            continue
                        if entry_idx:
                            fib_levels = apply_fibonacci_levels(symbol,entry_idx, candles,timeframe)
                            if fib_levels:
                                    direction = "BUY" if candles['close'].iloc[entry_idx] > candles['upper'].iloc[entry_idx] else "SELL"
                                    if symbol in M15_pen :
                                        pending(symbol, direction, candles['close'].iloc[entry_idx], fib_levels['sl'], fib_levels['tp3'],fib_levels['sniper'],timeframe)
                                    elif symbol in M15_pl:
                                        place_trade(symbol, direction, candles['close'].iloc[entry_idx], fib_levels['sl1'], fib_levels['tp3'],timeframe)
                if (symbol, timeframe) in levels :
                    L =levels[(symbol,timeframe)]
                    check_tp1_and_manage_trades(symbol, L["tp1"], timeframe)
                    check_tp2_and_manage_trades(symbol, L["tp2"], timeframe)
                else:
                    positions = mt5.positions_get(symbol=symbol)
                    if positions is not None:
                        for position in positions:
                            check_tp1_and_manage_trades(symbol, position.comment,timeframe)
                            check_tp2_and_manage_trades(symbol, position.comment,timeframe)
                close_pending(symbol)

        for (symbol,timeframe) in active_channels:
            active.append(f'{symbol}_{timeframe_to_str(timeframe)}')

        plot_active_channels()
        print(f"{active} have validated channels.")
        next_check_time = datetime.now() + timedelta(minutes=5)
        print(f"\033[92m Waiting for next trading opportunity at {next_check_time.strftime("%H:%M:%S")}...\033[0m")
        time.sleep(300)
    except Exception as e:
        send_telegram_message("Deriv Bot stopped")
        print(f"⚠️ Unexpected error: {e}")
        clear_plots_folder()
        raise