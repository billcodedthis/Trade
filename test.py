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
import re
from dotenv import load_dotenv

load_dotenv()

MT5_PATH = "C:\\Program Files\\MetaTrader 5\\terminal64.exe"
if not mt5.initialize(path=MT5_PATH):
    print("❌ Failed to connect to MetaTrader 5", mt5.last_error())
    quit()
else:
    print("✅ Successfully connected to MT5!")


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

TIMEFRAME_H1 = [XAUUSD]+US+Jump+H1_S_I
H1_B= [XAUUSD]+US
H1_S=Jump+H1_S_I
H1_BS=[]
H1_pen= Jump
H1_pl= [XAUUSD]+US+H1_S_I

TIMEFRAME_M15= [XAUUSD]+M15_B_P+M15_S_P
M15_B= M15_B_P
M15_S=M15_S_P
M15_BS=[XAUUSD]
M15_pen= [XAUUSD]+M15_B_P+M15_S_P
M15_pl= []

# NOTE: no M30 symbol set was specified for this bot, so it mirrors M15's
# symbols as a starting point. Adjust freely once you decide which symbols
# should actually trade on M30.
TIMEFRAME_M30= [XAUUSD]+M15_B_P+M15_S_P
M30_B= M15_B_P
M30_S= M15_S_P
M30_BS=[XAUUSD]
M30_pen= [XAUUSD]+M15_B_P+M15_S_P
M30_pl= []

TIMEFRAME_M5= [XAUUSD]+M5_S_P+v+M5_B_P
M5_S=M5_S_P+[XAUUSD]
M5_B= M5_B_P
M5_BS= v
M5_pen= [XAUUSD]+M5_S_P+v+M5_B_P
M5_pl= []

TIMEFRAME_M1 = []
M1_S =[]
M1_B= []
M1_BS = []
M1_pen = []
M1_pl = []

active_channels = {}
levels={}
old_engulfs={}
breakeven_trades = {}
active_trades={}
cooldown = {} 
profit_tracking = {}  

# ==================== DRAWDOWN PROTECTION ====================
WEEKLY_LOSS_LIMIT_PCT = 15.0   # Block new entries if account balance drops this % vs start of week
MONTHLY_LOSS_LIMIT_PCT = 30.0  # Block new entries if account balance drops this % vs start of month

risk_state = {
    'week_start_balance': None,
    'week_key': None,        # (ISO year, ISO week number)
    'month_start_balance': None,
    'month_key': None,       # (year, month)
    'weekly_blocked': False,
    'monthly_blocked': False,
}


DOWNLOADS_FOLDER = str(Path.home() / "OneDrive - University of Ghana")
PLOTS_FOLDER = os.path.join(DOWNLOADS_FOLDER, "MT5_Regression_Channels_test")

# Create the folder if it doesn't exist
if not os.path.exists(PLOTS_FOLDER):
    os.makedirs(PLOTS_FOLDER)

supply_demand_zones = {}  # Store zones for each symbol
to_be_reloaded=[]
zone_last_loaded ={}
ZONE_RELOAD_CONFIG = {
        mt5.TIMEFRAME_M1: timedelta(hours=12),    # M1 uses M5 zones which should reload every 12 hours
        mt5.TIMEFRAME_M5: timedelta(days=1),      # M5 uses M15 zones which should reload daily
        mt5.TIMEFRAME_M15: timedelta(days=3),       # M15 uses M30 zones which should reload every 3 days
        mt5.TIMEFRAME_M30: timedelta(days=5),       # M30 uses H1 zones which should reload every 5 days
        mt5.TIMEFRAME_H1: timedelta(days=7),       # H1 uses H4 zones which should  reload weekly
    }


WEEKEND_RESTRICTION_START = 12  # 12:00 PM Friday
WEEKEND_RESTRICTION_END = 12     # 12:00 PM Monday
Forex_Major= ['AUDJPY.0', 'AUDUSD.0', 'EURAUD.0', 'EURCAD.0', 'EURCHF.0', 'EURGBP.0', 'EURJPY.0', 'EURUSD.0', 'GBPAUD.0', 'GBPJPY.0', 'GBPUSD.0', 'USDCAD.0', 'USDCHF.0', 'USDJPY.0']
Forex_Minor= ['AUDCAD.0', 'AUDCHF.0', 'AUDNZD.0', 'CADCHF.0', 'CADJPY.0', 'CHFJPY.0', 'EURNOK.0', 'EURNZD.0', 'EURPLN.0', 'EURSEK.0', 'GBPCAD.0', 'GBPCHF.0', 'GBPNOK.0', 'GBPNZD.0', 'GBPSEK.0', 'NZDCAD.0', 'NZDJPY.0', 'NZDUSD.0', 'USDCNH.0', 'USDMXN.0', 'USDNOK.0', 'USDPLN.0', 'USDSEK.0', 'USDZAR.0']
Metals= ['XAGEUR.0', 'XAGUSD.0', 'XAUEUR.0', 'XAUUSD.0', 'XPDUSD.0', 'XPTUSD.0']
Energies= ['UK Brent Oil.0', 'US Oil.0']
Basket_Indices= ['AUD Basket.0', 'EUR Basket.0', 'GBP Basket.0', 'Gold Basket.0', 'USD Basket.0']
Stock_Indices= ['Australia 200', 'China H Shares', 'Europe 50', 'France 40', 'Germany 40', 'Hong Kong 50', 'Japan 225', 'Netherlands 25', 'Spain 35', 'Swiss 20', 'UK 100', 'US Mid Cap 400', 'US SP 500', 'US Small Cap 2000', 'US Tech 100', 'Wall Street 30']

def is_time_restricted(symbol):
    """
    Check if trading should be restricted for this symbol based on weekend rules
    Restricted: Friday 12:00 to Monday 06:00 for Forex, Metals, Energies, Basket Indices
    """
    # Get current time in local timezone
    now = datetime.now()
    
    # Check if it's weekend (Friday after 12 PM or Saturday/Sunday or Monday before 6 AM)
    if now.weekday() == 4:  # Friday
        if now.hour >= WEEKEND_RESTRICTION_START:
            # Check if symbol is in restricted categories
            if (symbol in Forex_Major + Forex_Minor or 
                symbol in Metals or 
                symbol in Energies or 
                symbol in Basket_Indices+Stock_Indices):
                print(f"⛔ Weekend restriction: {symbol} blocked from {now.strftime('%A %H:%M')} (Friday after {WEEKEND_RESTRICTION_START}:00)")
                return True
    elif now.weekday() == 6:  # Sunday
        if (symbol in Forex_Major + Forex_Minor or 
                symbol in Metals or 
                symbol in Energies or 
                symbol in Basket_Indices+Stock_Indices):
            print(f"⛔ Weekend restriction: {symbol} blocked until {WEEKEND_RESTRICTION_END}:00 Monday")
            return True
    elif now.weekday() == 0:  # Monday
        if now.hour < WEEKEND_RESTRICTION_END:
            if (symbol in Forex_Major + Forex_Minor or 
                symbol in Metals or 
                symbol in Energies or 
                symbol in Basket_Indices+Stock_Indices):
                print(f"⛔ Weekend restriction: {symbol} blocked until {WEEKEND_RESTRICTION_END}:00 Monday")
                return True
    
    return False

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
    channel_id = os.getenv("TELEGRAM_CHANNEL_ID_TEST", "")
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
    channel_id = os.getenv("TELEGRAM_CHANNEL_ID_TEST", "")
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

def decimal_places(n):
    return len(str(n).rstrip('0').split('.')[-1]) if '.' in str(n) else 0

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
                channel_text += f"Extended Bars: {len(df_plot) - original_length}\n"  # Calculate extended bars
                channel_text += f"A+ Setup: {'True' if channel_data.get('a_plus_setup', False) else 'False'}"
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

def lot_size(symbol):
    lot = 4 * get_min_lot_size(symbol)
    return lot

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
        last = df.iloc[-num_bars:]  # Keep this to check recent candles
        last_trend = df['trend']
        trend_slope = last_trend.iloc[-1] - last_trend.iloc[0]
        
        for i in range(len(last)):
            candle = last.iloc[i]
            # FIX: Use channel values at THIS candle's index, not the last one
            upper_at_i = last['upper'].iloc[i]
            lower_at_i = last['lower'].iloc[i]
            
            broke_above = candle['high'] > upper_at_i
            broke_below = candle['low'] < lower_at_i

            if timeframe == mt5.TIMEFRAME_H1:
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
            
            elif timeframe == mt5.TIMEFRAME_M15:
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

            elif timeframe == mt5.TIMEFRAME_M30:
                if symbol in M30_B:
                    if (trend_slope > 0 ) or (trend_slope < 0 and broke_below):
                            print(f"🚨 {symbol}_{timeframe_to_str(timeframe)} broke out in the direction of the trend — clearing it.")
                            del active_channels[(symbol,timeframe)]
                            break# Skip further processing this round
                elif symbol in M30_BS:
                    if (trend_slope > 0  and broke_above) or (trend_slope < 0 and broke_below):
                            print(f"🚨 {symbol}_{timeframe_to_str(timeframe)} broke out in the direction of the trend — clearing it.")
                            del active_channels[(symbol,timeframe)]
                            break# Skip further processing this round
                elif symbol in M30_S:
                        if (trend_slope > 0  and broke_above) or (trend_slope < 0 ):
                            print(f"🚨 {symbol}_{timeframe_to_str(timeframe)} broke out in the direction of the trend — clearing it.")
                            del active_channels[(symbol,timeframe)]
                            break# Skip further processing this round

            elif timeframe == mt5.TIMEFRAME_M5:
                if symbol in M5_B:
                    if (trend_slope > 0 ) or (trend_slope < 0 and broke_below):
                            print(f"🚨 {symbol}_{timeframe_to_str(timeframe)} broke out in the direction of the trend — clearing it.")
                            del active_channels[(symbol,timeframe)]
                            break# Skip further processing this round
                elif symbol in M5_BS:
                    if (trend_slope > 0  and broke_above) or (trend_slope < 0 and broke_below):
                            print(f"🚨 {symbol}_{timeframe_to_str(timeframe)} broke out in the direction of the trend — clearing it.")
                            del active_channels[(symbol,timeframe)]
                            break# Skip further processing this round
                elif symbol in M5_S:
                        if (trend_slope > 0  and broke_above) or (trend_slope < 0 ):
                            print(f"🚨 {symbol}_{timeframe_to_str(timeframe)} broke out in the direction of the trend — clearing it.")
                            del active_channels[(symbol,timeframe)]
                            break# Skip further processing this round

            elif timeframe == mt5.TIMEFRAME_M1:
                if symbol in M1_B:
                    if (trend_slope > 0 ) or (trend_slope < 0 and broke_below):
                            print(f"🚨 {symbol}_{timeframe_to_str(timeframe)} broke out in the direction of the trend — clearing it.")
                            del active_channels[(symbol,timeframe)]
                            break# Skip further processing this round
                elif symbol in M1_BS:
                    if (trend_slope > 0  and broke_above) or (trend_slope < 0 and broke_below):
                            print(f"🚨 {symbol}_{timeframe_to_str(timeframe)} broke out in the direction of the trend — clearing it.")
                            del active_channels[(symbol,timeframe)]
                            break# Skip further processing this round
                elif symbol in M1_S:
                        if (trend_slope > 0  and broke_above) or (trend_slope < 0 ):
                            print(f"🚨 {symbol}_{timeframe_to_str(timeframe)} broke out in the direction of the trend — clearing it.")
                            del active_channels[(symbol,timeframe)]
                            break# Skip further processing this round

    return True

def detect_regression_channel(df, symbol, timeframe):
    positions = [pos for pos in mt5.positions_get(symbol=symbol) if pos.magic == timeframe]
    orders = [order for order in mt5.orders_get(symbol=symbol) if order.magic == timeframe]
    if positions or orders:
        return

    # Split data - exclude last 10 candles for analysis but keep full data for plotting
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

    # ── helper: recount all touches with debounce after any refit ──────────────
    def recount_touches(upper, lower, upper_touch_indices, lower_touch_indices):
        """
        Re-scan analysis_df from scratch and recount upper/lower touches using
        the same 5-candle debounce as the main loop.  Returns updated counts and
        index lists so subsequent logic stays consistent.
        """
        u_count, l_count = 0, 0
        u_indices, l_indices = [], []
        for m in range(1, len(analysis_df)):
            recent_upper = any((m - idx) <= 5 for idx in u_indices)
            recent_lower = any((m - idx) <= 5 for idx in l_indices)
            if analysis_df['high'].iloc[m] == upper[m] and not recent_upper:
                u_count += 1
                u_indices.append(m)
            if analysis_df['low'].iloc[m] == lower[m] and not recent_lower:
                l_count += 1
                l_indices.append(m)
        return u_count, l_count, u_indices, l_indices
    # ───────────────────────────────────────────────────────────────────────────

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

        # Touch counting logic
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

        # Breakout detection
        if analysis_df['close'].iloc[i - 1] <= upper[i - 1] and analysis_df['close'].iloc[i] > upper[i - 1]:
            breakout = i
            direction = 'upper'
        elif analysis_df['close'].iloc[i - 1] >= lower[i - 1] and analysis_df['close'].iloc[i] < lower[i - 1]:
            breakout = i
            direction = 'lower'

        # Breakout validation + refit
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
                # FIX: use debounced recount instead of bare loop
                (upper_touch_count, lower_touch_count,
                 upper_touch_indices, lower_touch_indices) = recount_touches(
                    upper, lower, upper_touch_indices, lower_touch_indices)

        # Validation condition
        if (upper_touch_count >= 2 and lower_touch_count >= 1) or \
           (upper_touch_count >= 1 and lower_touch_count >= 2):
            validated = True
            break

    # ── Fallback: adjust boundary if one side has zero touches ─────────────────
    if not validated:
        if upper_touch_count >= 2 and lower_touch_count == 0:
            # Bring lower band in closer to the trend line
            lower = trend_line - 2 * std_dev
            lower_full = trend_line_full - 2 * std_dev
            full_df['lower'] = lower_full

            # Reset only the lower-side state; keep upper state intact
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

                if analysis_df['close'].iloc[k - 1] <= upper[k - 1] and analysis_df['close'].iloc[k] > upper[k - 1]:
                    breakout = k
                    direction = 'upper'
                elif analysis_df['close'].iloc[k - 1] >= lower[k - 1] and analysis_df['close'].iloc[k] < lower[k - 1]:
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
                        # FIX: use debounced recount instead of bare loop
                        (upper_touch_count, lower_touch_count,
                         upper_touch_indices, lower_touch_indices) = recount_touches(
                            upper, lower, upper_touch_indices, lower_touch_indices)

            if (upper_touch_count >= 2 and lower_touch_count >= 1) or \
               (upper_touch_count >= 1 and lower_touch_count >= 2):
                validated = True

        elif lower_touch_count >= 2 and upper_touch_count == 0:
            # Bring upper band in closer to the trend line
            upper = trend_line + std_dev
            upper_full = trend_line_full + std_dev
            full_df['upper'] = upper_full

            # Reset only the upper-side state; keep lower state intact
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

                if analysis_df['close'].iloc[k - 1] <= upper[k - 1] and analysis_df['close'].iloc[k] > upper[k - 1]:
                    breakout = k
                    direction = 'upper'
                elif analysis_df['close'].iloc[k - 1] >= lower[k - 1] and analysis_df['close'].iloc[k] < lower[k - 1]:
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
                        # FIX: use debounced recount instead of bare loop
                        (upper_touch_count, lower_touch_count,
                         upper_touch_indices, lower_touch_indices) = recount_touches(
                            upper, lower, upper_touch_indices, lower_touch_indices)

            if (upper_touch_count >= 2 and lower_touch_count >= 1) or \
               (upper_touch_count >= 1 and lower_touch_count >= 2):
                validated = True

    a_plus_setup = False
    if validated:
        trend_slope = full_df['trend'].iloc[-1] - full_df['trend'].iloc[0]
        a_plus_setup = check_a_plus_setup(symbol, full_df, trend_slope, timeframe)

    return validated, full_df, a_plus_setup

def find_valid_entry(df, breakout_idx, last_touch_idx,symbol,timeframe):
    not_valid_entry=False
    if last_touch_idx is None or breakout_idx is None:
        return None
        
    # Get the price from active_channels instead of using the index directly
    channel_data = active_channels[(symbol,timeframe)]
    last_touch_price = channel_data["last_touch_price"]
    if last_touch_price is None:
        return None
    
        
    entry_candle_idx = None
    count =0
    for i in range(breakout_idx, len(df)):
        if df['open'].iloc[i] > df['upper'].iloc[i] or df['open'].iloc[i] < df['lower'].iloc[i]: 
            count+=1
        if df['open'].iloc[i] > last_touch_price and df['high'].iloc[i] > df['upper'].iloc[i] and last_touch_price>df['upper'].iloc[i]:
            if df['close'].iloc[i-2]> df['open'].iloc[i-2]  and df['close'].iloc[i-1] > last_touch_price and df['open'].iloc[i-1] < last_touch_price:
                entry_candle_idx = i-1
                break
            else:
                not_valid_entry=True
        elif df['open'].iloc[i] < last_touch_price and df['low'].iloc[i] < df['lower'].iloc[i] and last_touch_price<df['lower'].iloc[i]: 
            if df['close'].iloc[i-2]< df['open'].iloc[i-2] and df['close'].iloc[i-1] < last_touch_price and df['open'].iloc[i-1] > last_touch_price:
                entry_candle_idx = i-1
                break
            else:
                not_valid_entry=True
        
    if not_valid_entry:
        print(f"{symbol} {timeframe}channel didn't meet the entry criteria")
        if (symbol, timeframe) in active_channels:
            del active_channels[(symbol,timeframe)]
        if (symbol, timeframe) in levels:
            del levels[(symbol,timeframe)]
        return None
    
    if count >= channel_data["num_bars"] and entry_candle_idx is None:
            print(f"{symbol} {timeframe}channel has kept too long after breakout.Deleting channel")
            if (symbol, timeframe) in active_channels:
                del active_channels[(symbol,timeframe)]
            if (symbol, timeframe) in levels:
                del levels[(symbol,timeframe)]
            return None
    
    
    if entry_candle_idx is None:
        return None
    
    last_trend = df["trend"]
    trend_slope = last_trend.iloc[-1] - last_trend.iloc[0]
    
    broken =0
    for i in range(breakout_idx, entry_candle_idx-1):
        if trend_slope<0 and df['high'].iloc[i] > last_touch_price:
            broken+=1
        elif trend_slope>0  and df['low'].iloc[i] < last_touch_price:
            broken+=1
    if broken >=1 :
        print(f"{symbol} {timeframe}channel didn't meet the entry criteria")
        if (symbol, timeframe) in active_channels:
            del active_channels[(symbol,timeframe)]
        if (symbol, timeframe) in levels:
            del levels[(symbol,timeframe)]
        return None
    
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
        if df['close'].iloc[i-1] <= df['upper'][i-1] and df['close'].iloc[i] > df['upper'][i]:
            if trend_slope < 0:
                breakout = i
                active_channels[(symbol,timeframe)]["breakout_idx"] = breakout
                # Find last touch before breakout
                for j in range(breakout - 10, 10, -1):
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

        elif df['close'].iloc[i-1] >= df['lower'][i-1] and df['close'].iloc[i] < df['lower'][i]:
            if trend_slope > 0:
                breakout = i
                active_channels[(symbol,timeframe)]["breakout_idx"] = breakout
                # Find last touch before breakout
                for j in range(breakout - 10, 10, -1):
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

def is_rejection_candle(df, idx, is_low):
    """
    Checks whether the candle at `idx` shows a pin-bar / rejection wick at its
    low (is_low=True, used for BUY swing points) or its high (is_low=False,
    used for SELL swing points). A rejection candle is one where the wick on
    the relevant side dominates the candle's range and dwarfs the body,
    signalling price was pushed to an extreme and rejected back.
    """
    if idx < 0 or idx >= len(df):
        return False
    o = df['open'].iloc[idx]
    c = df['close'].iloc[idx]
    h = df['high'].iloc[idx]
    l = df['low'].iloc[idx]
    candle_range = h - l
    if candle_range <= 0:
        return False
    body = abs(c - o)
    wick = (min(o, c) - l) if is_low else (h - max(o, c))
    # Pin-bar style rejection: wick makes up at least half the candle's range
    # and is clearly larger than the body itself.
    return wick >= candle_range * 0.5 and wick >= body * 1.5

def find_rejection_index(df, anchor_idx, is_low):
    """
    Given a candidate swing-anchor index (an opposite-colored candle),
    resolves which specific candle actually carries the rejection wick - the
    true pin bar. Checks the anchor candle itself first, then the candle
    immediately before it, then the candle immediately after it, and returns
    the index of whichever one qualifies (the pin bar can be a different
    candle than the anchor itself). Returns None if none of the three show
    a rejection.
    """
    if is_rejection_candle(df, anchor_idx, is_low):
        return anchor_idx
    if is_rejection_candle(df, anchor_idx - 1, is_low):
        return anchor_idx - 1
    if is_rejection_candle(df, anchor_idx + 1, is_low):
        return anchor_idx + 1
    return None

def swing_point_is_turning_point(df, swing_idx, entry_idx, is_buy):
    """
    True if the candidate swing anchor qualifies as a turning point - i.e.
    find_rejection_index finds a rejection wick at the anchor itself or
    either immediate neighbor.
    """
    return find_rejection_index(df, swing_idx, is_buy) is not None

def find_valid_swing_point(df, entry_idx, is_buy):
    """
    Searches backward from the candle immediately before entry for the
    nearest opposite-colored candle that qualifies as a turning-point anchor,
    then resolves that anchor to whichever candle actually carries the
    rejection wick (the pin bar) - which may be the anchor itself, or the
    candle immediately before/after it (see find_rejection_index). If the
    nearest anchor doesn't qualify, keeps searching further back rather than
    discarding the setup outright - candles that aren't opposite-colored are
    skipped over (never considered as an anchor), but the search continues
    all the way back to the first candle available in `df` (the same range
    the original nearest-opposite-candle search already covered - no new
    limit is introduced, it just no longer stops at the first failure).
    Returns the index of the pin bar candle - this is the actual swing point
    used for risk/SL/TP and for the run-up check to entry - or None if no
    qualifying anchor is found anywhere in range.
    """
    is_low = is_buy
    entry_bullish = df['close'].iloc[entry_idx] > df['open'].iloc[entry_idx]
    for i in range(entry_idx, 0, -1):
        candle_bullish = df['close'].iloc[i] > df['open'].iloc[i]
        is_opposite = (entry_bullish and not candle_bullish) or ((not entry_bullish) and candle_bullish)
        if not is_opposite:
            continue
        pin_bar_idx = find_rejection_index(df, i, is_low)
        if pin_bar_idx is not None:
            return pin_bar_idx
    return None

def apply_fibonacci_levels(symbol, entry_idx, df,timeframe):
    if entry_idx is None:
        return None
    entry_price = df['close'].iloc[entry_idx]

    # Get the swing point (low for buys, high for sells) - anchored to
    # whichever candle actually carries the rejection wick (the pin bar),
    # which may not be the same candle as the opposite-colored anchor that
    # was used to find it.
    is_buy = df['close'].iloc[entry_idx] > df['open'].iloc[entry_idx]
    pin_bar_idx = find_valid_swing_point(df, entry_idx, is_buy)

    if pin_bar_idx is None:
        print(f"{symbol} {timeframe}channel: no valid rejection swing point found - deleting channel")
        if (symbol, timeframe) in active_channels:
            del active_channels[(symbol,timeframe)]
        if (symbol, timeframe) in levels:
            del levels[(symbol,timeframe)]
        return None

    swing_point = df['low'].iloc[pin_bar_idx] if is_buy else df['high'].iloc[pin_bar_idx]

    # Between the pin bar and the entry candle, no candle may push its wick
    # past the pin bar's own wick in the relevant direction.
    for i in range(pin_bar_idx+1,entry_idx+1):
        if is_buy:
            if df['low'].iloc[i] < swing_point:
                print(f"{symbol} {timeframe}channel didn't meet the entry criteria")
                if (symbol, timeframe) in active_channels:
                    del active_channels[(symbol,timeframe)]
                if (symbol, timeframe) in levels:
                    del levels[(symbol,timeframe)]
                return None
        else:
            if df['high'].iloc[i] > swing_point:
                print(f"{symbol} {timeframe}channel didn't meet the entry criteria")
                if (symbol, timeframe) in active_channels:
                    del active_channels[(symbol,timeframe)]
                if (symbol, timeframe) in levels:
                    del levels[(symbol,timeframe)]
                return None 
    
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
            "direction": "BUY",
            "entry_time": df['time'].iloc[entry_idx],
            "engulf_count": 0,
            "last_engulf_time": None ,
            "entry": None
            
        }
    else:
        levels[(symbol,timeframe)] = {
            "sl": swing_point + (0.9 * risk),
            "tp1": swing_point - (1.8 * risk),
            "tp2": swing_point - (2.8 * risk),
            "tp3": entry_price - (3.5 * risk),
            "sniper": swing_point - (0.3 * risk), 
            "sl1": swing_point   + (0.2 * risk),
            "direction": "SELL",
            "entry_time": df['time'].iloc[entry_idx],
            "engulf_count": 0,
            "last_engulf_time": None,
            "entry":None
        }
    
    return levels[(symbol,timeframe)]

def format_tp_comment(tp1, tp2):
    """Encode tp1 and tp2 into the compact pipe-delimited order/position comment."""
    return f"{tp1}|{tp2}"

def extract_tp_levels_from_comment(comment):
    """Decode the pipe-delimited comment back into (tp1, tp2). Returns (None, None) on failure."""
    if not comment:
        return None, None
    try:
        parts = str(comment).split("|")
        if len(parts) < 2:
            return None, None
        return float(parts[0]), float(parts[1])
    except (ValueError, TypeError):
        return None, None

def get_lot_step(symbol):
    info = mt5.symbol_info(symbol)
    if info:
        return info.volume_step
    else:
        return None

def adjust_lot_for_risk(symbol, direction, entry_price, sl, initial_volume):
    """Adjust lot size to ensure risk <= 5% of balance."""
    balance = mt5.account_info().balance
    if balance <= 0:
        print(f"❌ Account balance is {balance}. Cannot place trade.")
        return None

    min_lot = get_min_lot_size(symbol)
    lot_step = get_lot_step(symbol)
    if min_lot is None or lot_step is None:
        print(f"❌ Could not get symbol info for {symbol}.")
        return None

    volume = initial_volume
    order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL

    while volume > min_lot:
        # Calculate hypothetical profit (negative for loss)
        profit = mt5.order_calc_profit(order_type, symbol, volume, entry_price, sl)
        if profit is None:
            print(f"❌ Failed to calculate profit for {symbol}.")
            return None

        loss = abs(profit)  # Loss is positive value
        risk_pct = (loss / balance) * 100
        

        if 2 <=risk_pct <= 5:
            # Round down to nearest step
            volume = (volume // lot_step) * lot_step
            if volume < min_lot:
                volume = min_lot
            return volume
        
        elif risk_pct < 2:
            volume *= 2
            volume = max((volume // lot_step) * lot_step, min_lot)

        elif risk_pct >5:
            volume /= 2
            volume = max((volume // lot_step) * lot_step, min_lot)

    if volume == min_lot:
        profit = mt5.order_calc_profit(order_type, symbol, volume, entry_price, sl)
        if profit is None:
            print(f"❌ Failed to calculate profit for {symbol}.")
            return None

        loss = abs(profit)  # Loss is positive value
        risk_pct = (loss / balance) * 100
        

        if 2 <=risk_pct <= 5:
            # Round down to nearest step
            volume = (volume // lot_step) * lot_step
            if volume < min_lot:
                volume = min_lot
            return volume

    print(f"🚫 Risk still exceeds 2-5% at minimum lot size for {symbol}. Skipping trade.")
    return None

def pending(symbol, direction, entry_price, sl, tp,sniper,timeframe):
    if is_trading_blocked():
        print(f"⛔ Drawdown protection active: not placing pending {direction} order for {symbol}")
        return
    if is_time_restricted(symbol):
        print(f"⛔ Weekend restriction: Not placing pending {direction} order for {symbol}")
        if (symbol, timeframe) in active_channels:
            del active_channels[(symbol,timeframe)]
        if (symbol, timeframe) in levels:
            del levels[(symbol,timeframe)]
        return
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
    initial_lot = lot_size(symbol)
    adjusted_volume = adjust_lot_for_risk(symbol, direction, sniper, sl, initial_lot)
    if adjusted_volume is None:
        print(f"🚫 Skipping pending trade for {symbol}: Risk exceeds 2-5% even at min lot.")
        return
    
    request1 = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "volume": adjusted_volume ,
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
    if order is None:
        print(f"❌ order_send returned None (no response from server): {mt5.last_error()}")
        return
    if order.retcode == mt5.TRADE_RETCODE_DONE:
        plot_filename = os.path.join(PLOTS_FOLDER, f"{symbol}_{timeframe_to_str(timeframe)}_channel.png")
        send_telegram_image(plot_filename,f"📥 <b>Deriv Pending Trade</b>\nSymbol: {symbol}\nDirection: {direction}\nEntry: {sniper:.4f}\nSL: {sl:.4f}\nTP1: {levels[(symbol,timeframe)]["tp1"]:.4f}\nTP2: {levels[(symbol,timeframe)]["tp2"]:.4f}\nTP3: {tp:.4f}")
        print(f"Pending Trade placed: {direction} {symbol} @ {sniper}")
        levels[(symbol, timeframe)]['is_pending'] = True
        levels[(symbol, timeframe)]['pending_order_ticket'] = order.order
        levels[(symbol, timeframe)]['entry'] = entry_price
    else:
        print(f"{symbol}, pending {direction}@{entry_price} sl:{sl},tp:{tp} failed: {order.comment}")

def place_trade(symbol, direction, entry_price, sl1, tp,timeframe):
    if is_trading_blocked():
        print(f"⛔ Drawdown protection active: not placing {direction} market trade for {symbol}")
        return
    if is_time_restricted(symbol):
        print(f"⛔ Weekend restriction: Not placing {direction} market trade for {symbol}")
        if (symbol, timeframe) in active_channels:
            del active_channels[(symbol,timeframe)]
        if (symbol, timeframe) in levels:
            del levels[(symbol,timeframe)]
        return
    if abs(sl1 - entry_price) >= abs(tp - entry_price):
        print(f"🚫 Trade not placed: SL is greater than TP for {symbol}.")
        return
    positions = mt5.positions_get(symbol=symbol)
    if positions is not None:
        for position in positions:
            if timeframe==position.magic:
                print(f"🚫 Trade not placed: An open position already exists for {symbol}.")
                return
    initial_lot = lot_size(symbol)
    adjusted_volume = adjust_lot_for_risk(symbol, direction, entry_price, sl1, initial_lot)
    if adjusted_volume is None:
        print(f"🚫 Skipping market trade for {symbol}: Risk exceeds 2-5% even at min lot.")
        return
    request = {
        "action": mt5.TRADE_ACTION_DEAL ,
        "symbol": symbol,
        "volume": adjusted_volume ,
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
    if order is None:
        print(f"❌ order_send returned None (no response from server): {mt5.last_error()}")
        return
    if order.retcode == mt5.TRADE_RETCODE_DONE:
        plot_filename = os.path.join(PLOTS_FOLDER, f"{symbol}_{timeframe_to_str(timeframe)}_channel.png")
        send_telegram_image(plot_filename,f"🚀 <b>Deriv Market Trade</b>\nSymbol: {symbol}\nDirection: {direction}\nEntry: {entry_price:.4f}\nSL: {sl1:.4f}\nTP1: {levels[(symbol,timeframe)]["tp1"]:.4f}\nTP2: {levels[(symbol,timeframe)]["tp2"]:.4f}\nTP3: {tp:.4f}")
        print(f"Trade placed: {direction} {symbol} @ {entry_price}")
        levels[(symbol, timeframe)]['entry'] = entry_price
    else:
        print(f"{symbol},{direction}@{entry_price} sl:{sl1},tp:{tp} failed: {order.comment}")

def modify_trade_to_breakeven(symbol, order_ticket, entry_price):
    position = mt5.positions_get(ticket=order_ticket)
    if position:
        position = position[0]
    else:
        return
    if position.sl == entry_price:
        print(f"Breakeven already applied on {symbol}")
        return
    if (position.type == mt5.ORDER_TYPE_BUY and position.sl > entry_price) or \
        (position.type == mt5.ORDER_TYPE_SELL and position.sl < entry_price):
            return
    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": order_ticket,
        "sl": entry_price,  # Move SL to break-even
        "tp":position.tp,
        "comment":position.comment,
        "magic":position.magic
    }
    result = mt5.order_send(request)
    
    if result is None:
        print(f"❌ Failed to modify trade {order_ticket}: No response from server.")
    else:
        print(f"📝 Modify Trade Response: {result}")
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"✅ SL moved to break-even for trade {order_ticket} on {symbol}.")
            if order_ticket not in list(breakeven_trades):
                breakeven_trades[order_ticket] = {'symbol': symbol, 'timeframe': position.magic}
        else:
            print(f"❌ Failed to move SL: {result.comment} (Error Code: {result.retcode})")

def close_pending(symbol):
    orders = mt5.orders_get(symbol=symbol)
    if orders is None or len(orders) == 0:
        return  # No active trades

    for order in orders:
        timeframe = order.magic
        key = (symbol, timeframe)
        if key in levels and levels[key].get('is_pending', False):
            L = levels[key]  # ← Define L here!
            tp2 = L["tp2"]   # ← Use the stored TP2 (old TP1) from levels, NOT order.comment
            direction = L["direction"]
            entry_time = L["entry_time"]  # This is the breakout candle time — CORRECT reference!
        else:
            # For old orders not in levels
            _tp1_unused, tp2 = extract_tp_levels_from_comment(order.comment)
            if tp2 is None:
                continue  # Skip if comment isn't in the expected tp1|tp2 format
            direction = "SELL" if order.type == mt5.ORDER_TYPE_SELL_LIMIT else "BUY"
            entry_time = pd.to_datetime(order.time_setup, unit='s')  # Fixed: Use order setup time

        # Fetch candles since the SIGNAL (breakout), not since order placement
        rates = mt5.copy_rates_range(symbol, timeframe, entry_time, datetime.now())
        if rates is None or len(rates) == 0:
            continue
        recent_candles = pd.DataFrame(rates)
        recent_candles['time'] = pd.to_datetime(recent_candles['time'], unit='s')
        crossed_tp2 = False
        if direction == "BUY":
            if (recent_candles['high'] >= tp2).any():
                crossed_tp2 = True
        elif direction == "SELL":
            if (recent_candles['low'] <= tp2).any():
                crossed_tp2 = True
        if crossed_tp2:
            request = {
                    "action": mt5.TRADE_ACTION_REMOVE,
                    "order": order.ticket,
                }
            result = mt5.order_send(request)
                
            if result is None:
                print(f"❌ order_send returned None (no response from server): {mt5.last_error()}")
                continue
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                send_telegram_message(f"Delete deriv pending {direction} order for {symbol} on {timeframe_to_str(timeframe)}.")
                print(f"✅ Deleted pending order {order.ticket} for {symbol}.")
                if (symbol, timeframe) in active_channels:
                    del active_channels[(symbol,timeframe)]
                if (symbol, timeframe) in levels:
                            del levels[(symbol,timeframe)]
            else:
                print(f"❌ Failed to delete order {order.ticket} for {symbol}: {result.comment}")
        else:
            print(f"Order still valid for {symbol} ")
            
# Fraction of the ORIGINAL volume remaining after each cascade cut. Each cut closes
# volume - (volume/1.5) of whatever is CURRENTLY open (~1/3 of current), same formula
# the engulfing-halving logic already uses. Applied twice in sequence:
#   100% -> ~66.7% (after TP1 cut) -> ~44.4% (after TP2 cut) -> rides to TP3
TP1_REMAINING_FRACTION = 2 / 3
TP2_REMAINING_FRACTION = (2 / 3) * (2 / 3)

def check_tp1_and_manage_trades(symbol, tp1,timeframe):
    """Fires at (new) TP1: apply breakeven and close ~1/3 of the current position."""
    if isinstance(tp1,str):
        if tp1=='':
            return
        Tp1, _tp2_unused = extract_tp_levels_from_comment(tp1)
        if Tp1 is None:
            return
    else:
        Tp1 = tp1

    positions = mt5.positions_get(symbol=symbol)
    if positions is not None:
        for position in positions:
            if position.magic != timeframe:
                continue
            entry_price = position.price_open
            current_price = mt5.symbol_info_tick(symbol).bid if position.type == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(symbol).ask
            direction = "SELL" if position.type == mt5.ORDER_TYPE_SELL else "BUY"
            entry_time = pd.to_datetime(position.time, unit='s')

            deals = mt5.history_deals_get(position=position.ticket)
            if not deals:
                continue

            # Find the opening deal (entry == 0)
            open_deals = [d for d in deals if d.entry == 0]
            if not open_deals:
                continue
            initial_volume = open_deals[0].volume

            rates = mt5.copy_rates_range(symbol, timeframe, entry_time, datetime.now())
            if rates is None or len(rates) == 0:
                continue
            recent_candles = pd.DataFrame(rates)
            recent_candles['time'] = pd.to_datetime(recent_candles['time'], unit='s')
            crossed_tp1 = False
            if direction == "BUY":
                if (recent_candles['high'] >= Tp1).any():
                    crossed_tp1 = True
            elif direction == "SELL":
                if (recent_candles['low'] <= Tp1).any():
                    crossed_tp1 = True

            # TP1 logic: breakeven + close ~1/3 of current position
            if (position.type == mt5.ORDER_TYPE_BUY and crossed_tp1) or \
            (position.type == mt5.ORDER_TYPE_SELL and crossed_tp1):
                if position.volume == get_min_lot_size(symbol):
                    modify_trade_to_breakeven(symbol, position.ticket, entry_price)
                    continue
                if position.volume <= (initial_volume * TP1_REMAINING_FRACTION) + 1e-9:
                    print(f"✅ Position {position.ticket} for {symbol} already cut at TP1.")
                    modify_trade_to_breakeven(symbol, position.ticket, entry_price)
                    continue
                if position.sl == position.price_open:
                    print(f"✅ Position {position.ticket} for {symbol} SL has already been modified")
                else:
                    t = decimal_places(get_min_lot_size(symbol))
                    cut_lot = round(position.volume - (position.volume / 1.5), t)
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
                    if close_result is None:
                        print(f"❌ order_send returned None (no response from server): {mt5.last_error()}")
                        continue
                    if close_result.retcode == mt5.TRADE_RETCODE_DONE:
                        send_telegram_message(f"TP1 hit. Apply breakeven and close ~1/3 of deriv {direction} positions for {symbol} on {timeframe_to_str(timeframe)} trade.✅")
                        print(f"✅ Closed ~1/3 of position {position.ticket} for {symbol} at TP1.")
                        modify_trade_to_breakeven(symbol, position.ticket, entry_price)
                    elif close_result.comment == "Invalid volume":
                        send_telegram_message(f"TP1 hit. Apply breakeven for deriv {direction} {symbol} on {timeframe_to_str(timeframe)} trade (volume too small to cut).✅")
                        print(f"{symbol} cannot be cut, but SL has been moved to breakeven.")
                        modify_trade_to_breakeven(symbol, position.ticket, entry_price)
                    else:
                        print(f"❌ Failed to close portion of {symbol}: {close_result.comment}")

def check_tp2_and_manage_trades(symbol, tp2, timeframe):
    """Fires at TP2 (the old TP1): closes ~1/3 of whatever volume currently remains
    (~4/9 of the original left after this). Breakeven should already be applied from
    TP1, but this checks defensively rather than assuming it, to handle the edge case
    where TP1 was skipped or slipped past."""
    if isinstance(tp2, str):
        if tp2 == '':
            return
        _tp1_unused, Tp2 = extract_tp_levels_from_comment(tp2)
        if Tp2 is None:
            return
    else:
        Tp2 = tp2

    positions = mt5.positions_get(symbol=symbol)
    if positions is not None:
        for position in positions:
            if position.magic != timeframe:
                continue
            entry_price = position.price_open
            current_price = mt5.symbol_info_tick(symbol).bid if position.type == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(symbol).ask
            direction = "SELL" if position.type == mt5.ORDER_TYPE_SELL else "BUY"
            entry_time = pd.to_datetime(position.time, unit='s')

            deals = mt5.history_deals_get(position=position.ticket)
            if not deals:
                continue
            open_deals = [d for d in deals if d.entry == 0]
            if not open_deals:
                continue
            initial_volume = open_deals[0].volume

            rates = mt5.copy_rates_range(symbol, timeframe, entry_time, datetime.now())
            if rates is None or len(rates) == 0:
                continue
            recent_candles = pd.DataFrame(rates)
            recent_candles['time'] = pd.to_datetime(recent_candles['time'], unit='s')
            crossed_tp2 = False
            if direction == "BUY":
                if (recent_candles['high'] >= Tp2).any():
                    crossed_tp2 = True
            elif direction == "SELL":
                if (recent_candles['low'] <= Tp2).any():
                    crossed_tp2 = True

            if crossed_tp2:
                # Defensive breakeven check - normally already applied at TP1, but don't assume it
                if position.sl != position.price_open:
                    modify_trade_to_breakeven(symbol, position.ticket, entry_price)
                if position.volume == get_min_lot_size(symbol):
                    continue
                if position.volume <= (initial_volume * TP2_REMAINING_FRACTION) + 1e-9:
                    print(f"✅ Position {position.ticket} for {symbol} already cut at TP2.")
                    continue
                t = decimal_places(get_min_lot_size(symbol))
                cut_lot = round(position.volume - (position.volume / 1.5), t)
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
                if close_result is None:
                    print(f"❌ order_send returned None (no response from server): {mt5.last_error()}")
                    continue
                if close_result.retcode == mt5.TRADE_RETCODE_DONE:
                    send_telegram_message(f"TP2 hit. Closed further portion of deriv {direction} position for {symbol} on {timeframe_to_str(timeframe)} trade.✅")
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
            entry_time = L["entry_time"] 
            sl = L["sl"]
            sl1 = L["sl1"]
            tp3 = L["tp3"]
            if not direction:
                continue

            rates = mt5.copy_rates_range(symbol, timeframe, entry_time, datetime.now())
            if rates is None or len(rates) == 0:
                continue
            recent_candles = pd.DataFrame(rates)
            recent_candles['time'] = pd.to_datetime(recent_candles['time'], unit='s')
            crossed_tp3 = False
            crossed_sl1 = False
            crossed_sl =  False
            if direction == "BUY":
                # For BUY positions: TP when price goes up, SL when price goes down
                crossed_tp3 = (recent_candles['high'] >= tp3).any()
                crossed_sl1 = (recent_candles['low'] <= sl1).any()
                crossed_sl = (recent_candles['low'] <= sl).any()
                
            elif direction == "SELL":
                # For SELL positions: TP when price goes down, SL when price goes up
                crossed_tp3 = (recent_candles['low'] <= tp3).any()
                crossed_sl1 = (recent_candles['high'] >= sl1).any()
                crossed_sl = (recent_candles['high'] >= sl).any()

            if timeframe== mt5.TIMEFRAME_M1:
                if symbol in M1_pen :
                    if (direction == "BUY" and crossed_sl) or (direction == "SELL" and crossed_sl):
                        start_cooldown(symbol, timeframe)
                        # Hit SL - delete channel and levels
                        if (symbol, timeframe) in active_channels:
                            send_telegram_message(f"🚨 {symbol} {direction}  hit Deriv SL on {timeframe_to_str(timeframe)}")
                            del active_channels[(symbol,timeframe)]
                        if (symbol, timeframe) in levels:
                            del levels[(symbol,timeframe)]
                        print(f"🚨 {symbol} {direction}  hit SL - channel removed.")
                        continue  # Skip TP check since we already hit SL
                elif symbol in M1_pl:
                    if (direction == "BUY" and crossed_sl1) or (direction == "SELL" and crossed_sl1):
                        start_cooldown(symbol, timeframe)
                        # Hit SL - delete channel and levels
                        if (symbol, timeframe) in active_channels:
                            send_telegram_message(f"🚨 {symbol} {direction}  hit Deriv SL on {timeframe_to_str(timeframe)}")
                            del active_channels[(symbol,timeframe)]
                        if (symbol, timeframe) in levels:
                            del levels[(symbol,timeframe)]
                        print(f"🚨 {symbol} {direction}  hit SL - channel removed.")
                        continue  # Skip TP check since we already hit SL

            if timeframe== mt5.TIMEFRAME_M5:
                if symbol in M5_pen :
                    if (direction == "BUY" and crossed_sl) or (direction == "SELL" and crossed_sl):
                        start_cooldown(symbol, timeframe)
                        # Hit SL - delete channel and levels
                        if (symbol, timeframe) in active_channels:
                            send_telegram_message(f"🚨 {symbol} {direction}  hit Deriv SL on {timeframe_to_str(timeframe)}")
                            del active_channels[(symbol,timeframe)]
                        if (symbol, timeframe) in levels:
                            del levels[(symbol,timeframe)]
                        print(f"🚨 {symbol} {direction}  hit SL - channel removed.")
                        continue  # Skip TP check since we already hit SL
                elif symbol in M5_pl:
                    if (direction == "BUY" and crossed_sl1) or (direction == "SELL" and crossed_sl1):
                        start_cooldown(symbol, timeframe)
                        # Hit SL - delete channel and levels
                        if (symbol, timeframe) in active_channels:
                            send_telegram_message(f"🚨 {symbol} {direction}  hit Deriv SL on {timeframe_to_str(timeframe)}")
                            del active_channels[(symbol,timeframe)]
                        if (symbol, timeframe) in levels:
                            del levels[(symbol,timeframe)]
                        print(f"🚨 {symbol} {direction}  hit SL - channel removed.")
                        continue  # Skip TP check since we already hit SL
            
            elif timeframe== mt5.TIMEFRAME_M15:
                if symbol in M15_pen :
                    if (direction == "BUY" and crossed_sl) or (direction == "SELL" and crossed_sl):
                        start_cooldown(symbol, timeframe)
                        # Hit SL - delete channel and levels
                        if (symbol, timeframe) in active_channels:
                            send_telegram_message(f"🚨 {symbol} {direction}  hit Deriv SL on {timeframe_to_str(timeframe)}")
                            del active_channels[(symbol,timeframe)]
                        if (symbol, timeframe) in levels:
                            del levels[(symbol,timeframe)]
                        print(f"🚨 {symbol} {direction}  hit SL - channel removed.")
                        continue  # Skip TP check since we already hit SL
                elif symbol in M15_pl:
                    if (direction == "BUY" and crossed_sl1) or (direction == "SELL" and crossed_sl1):
                        start_cooldown(symbol, timeframe)
                        # Hit SL - delete channel and levels
                        if (symbol, timeframe) in active_channels:
                            send_telegram_message(f"🚨 {symbol}  {direction} hit Deriv SL on {timeframe_to_str(timeframe)}")
                            del active_channels[(symbol,timeframe)]
                        if (symbol, timeframe) in levels:
                            del levels[(symbol,timeframe)]
                        print(f"🚨 {symbol} {direction}  hit SL - channel removed.")
                        continue  # Skip TP check since we already hit SL

            elif timeframe== mt5.TIMEFRAME_M30:
                if symbol in M30_pen :
                    if (direction == "BUY" and crossed_sl) or (direction == "SELL" and crossed_sl):
                        start_cooldown(symbol, timeframe)
                        # Hit SL - delete channel and levels
                        if (symbol, timeframe) in active_channels:
                            send_telegram_message(f"🚨 {symbol} {direction}  hit Deriv SL on {timeframe_to_str(timeframe)}")
                            del active_channels[(symbol,timeframe)]
                        if (symbol, timeframe) in levels:
                            del levels[(symbol,timeframe)]
                        print(f"🚨 {symbol} {direction}  hit SL - channel removed.")
                        continue  # Skip TP check since we already hit SL
                elif symbol in M30_pl:
                    if (direction == "BUY" and crossed_sl1) or (direction == "SELL" and crossed_sl1):
                        start_cooldown(symbol, timeframe)
                        # Hit SL - delete channel and levels
                        if (symbol, timeframe) in active_channels:
                            send_telegram_message(f"🚨 {symbol}  {direction} hit Deriv SL on {timeframe_to_str(timeframe)}")
                            del active_channels[(symbol,timeframe)]
                        if (symbol, timeframe) in levels:
                            del levels[(symbol,timeframe)]
                        print(f"🚨 {symbol} {direction}  hit SL - channel removed.")
                        continue  # Skip TP check since we already hit SL

            elif timeframe== mt5.TIMEFRAME_H1:
                if symbol in H1_pen :
                    if (direction == "BUY" and crossed_sl) or (direction == "SELL" and crossed_sl):
                        start_cooldown(symbol, timeframe)
                        # Hit SL - delete channel and levels
                        if (symbol, timeframe) in active_channels:
                            send_telegram_message(f"🚨 {symbol} {direction} hit Deriv SL on {timeframe_to_str(timeframe)}")
                            del active_channels[(symbol,timeframe)]
                        if (symbol, timeframe) in levels:
                            del levels[(symbol,timeframe)]
                        print(f"🚨 {symbol} {direction}  hit SL - channel removed.")
                        continue  # Skip TP check since we already hit SL
                elif symbol in H1_pl:
                    if (direction == "BUY" and crossed_sl1) or (direction == "SELL" and crossed_sl1):
                        start_cooldown(symbol, timeframe)
                        # Hit SL - delete channel and levels
                        if (symbol, timeframe) in active_channels:
                            send_telegram_message(f"🚨 {symbol}  {direction} hit Deriv SL on {timeframe_to_str(timeframe)}")
                            del active_channels[(symbol,timeframe)]
                        if (symbol, timeframe) in levels:
                            del levels[(symbol,timeframe)]
                        print(f"🚨 {symbol} {direction}  hit SL - channel removed.")
                        continue  # Skip TP check since we already hit SL

            # Check TP3 (final target)
            if (direction == "BUY" and crossed_tp3) or (direction == "SELL" and crossed_tp3):
                # Hit TP3 - delete channel and levels
                if (symbol, timeframe) in active_channels:
                    plot_filename = os.path.join(PLOTS_FOLDER, f"{symbol}_{timeframe_to_str(timeframe)}_channel.png")
                    send_telegram_image(plot_filename, f"✅ {symbol} {direction} hit Deriv TP3 on {timeframe_to_str(timeframe)}")
                    del active_channels[(symbol,timeframe)]
                if (symbol, timeframe) in levels:
                    del levels[(symbol,timeframe)]
                print(f"✅ {symbol} {direction} hit TP3 - channel removed.")  
 
def check_conflicting_trades():
    """Check for channels that conflict with existing trade directions and remove them"""
    # Get all open positions
    positions = mt5.positions_get()
    if positions is None:
        positions = []
    
    # Get all pending orders
    orders = mt5.orders_get()
    if orders is None:
        orders = []
    
    # Combine positions and orders
    all_trades = list(positions) + list(orders)
    
    for trade in all_trades:
        symbol = trade.symbol
        timeframe = trade.magic
        
        # Determine trade direction
        if trade.type in (mt5.ORDER_TYPE_BUY, mt5.ORDER_TYPE_BUY_LIMIT, mt5.ORDER_TYPE_BUY_STOP):
            trade_direction = "BUY"
        elif trade.type in (mt5.ORDER_TYPE_SELL, mt5.ORDER_TYPE_SELL_LIMIT, mt5.ORDER_TYPE_SELL_STOP):
            trade_direction = "SELL"
        else:
            continue
        
        # Check all active channels for this symbol (across all timeframes)
        for (channel_symbol, channel_timeframe) in list(active_channels.keys()):
            if channel_symbol != symbol:
                continue
                
            # Get channel direction from trend slope
            channel_data = active_channels[(channel_symbol, channel_timeframe)]
            df = channel_data["df"]
            trend_slope = df['trend'].iloc[-1] - df['trend'].iloc[0]
            channel_direction = "BUY" if trend_slope < 0 else "SELL"
            
            # If channel direction conflicts with existing trade direction, remove it
            if channel_direction != trade_direction:
                print(f"🗑️ Deleting {channel_symbol}_{timeframe_to_str(channel_timeframe)} - channel direction ({channel_direction}) conflicts with existing {trade_direction} trade on {timeframe_to_str(timeframe)}")
                
                # Remove from active_channels and levels
                if (channel_symbol, channel_timeframe) in active_channels:
                    del active_channels[(channel_symbol, channel_timeframe)]
                if (channel_symbol, channel_timeframe) in levels:
                    del levels[(channel_symbol, channel_timeframe)]

def update_pending_order_status():
    for (symbol, timeframe) in list(levels.keys()):
        if levels[(symbol, timeframe)].get('is_pending', False):
            order_ticket = levels[(symbol, timeframe)].get('pending_order_ticket')
            if not order_ticket:
                continue
            # Check if the order is still pending
            orders = mt5.orders_get(symbol=symbol)
            order_still_pending = any(order.ticket == order_ticket for order in orders) if orders else False
            if not order_still_pending:
                # Order is no longer pending; check if it became a position
                positions = mt5.positions_get(symbol=symbol)
                for pos in positions:
                    if pos.magic == timeframe:
                        # Order has been triggered; update entry_time
                        deals = mt5.history_deals_get(position=pos.ticket)
                        if deals:
                            open_time = deals[0].time  # Get the time the position was opened
                            levels[(symbol, timeframe)]['entry_time'] = pd.to_datetime(open_time, unit='s')
                            levels[(symbol, timeframe)]['is_pending'] = False
                            levels[(symbol, timeframe)]['pending_order_ticket'] = None
                            print(f"Pending order for {symbol} on {timeframe_to_str(timeframe)} triggered at {levels[(symbol, timeframe)]['entry_time']}")
                            break

def detect_opposite_engulfing(df, direction, symbol, timeframe):
    entry_price = levels.get((symbol, timeframe), {}).get('entry')
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

def handle_engulfing_patterns():
    for key in list(levels.keys()):
        symbol, timeframe = key
        L = levels[key]
        if 'entry_time' not in L:
            continue
        entry_time = L['entry_time']
        if L.get('is_pending', False):
            continue
        candles = get_candles(symbol, timeframe, 100)
        recent = candles[candles['time'] > entry_time].reset_index(drop=True)
        if len(recent) < 5: continue
        eng_i = detect_opposite_engulfing(recent, L['direction'], symbol, timeframe)
        if eng_i is not None:
            eng_time = recent['time'].iloc[eng_i]
            if 'last_engulf_time' not in L or L['last_engulf_time'] is None or eng_time > L['last_engulf_time']:
                L['last_engulf_time'] = eng_time
                L['engulf_count'] += 1
                print(f"Updated engulf_count to {L['engulf_count']} for {symbol}")
                positions = mt5.positions_get(symbol=symbol)
                for pos in positions:
                    if pos.magic == timeframe:
                        count = L['engulf_count']
                        min_lot = get_min_lot_size(symbol)
                        if count == 1:
                            if pos.volume > min_lot:
                                t = decimal_places(get_min_lot_size(symbol))
                                half = round(pos.volume-(pos.volume / 1.5), t)
                                current_price = mt5.symbol_info_tick(symbol).bid if pos.type == 1 else mt5.symbol_info_tick(symbol).ask
                                close_type = 1 if pos.type == 0 else 0
                                close_request = {
                                    "action": mt5.TRADE_ACTION_DEAL,
                                    "symbol": symbol,
                                    "volume": half,
                                    "type": close_type,
                                    "position": pos.ticket,
                                    "price": current_price,
                                    "deviation": 10,
                                    "magic": pos.magic,
                                    "comment": pos.comment,
                                    "type_time": mt5.ORDER_TIME_GTC,
                                    "type_filling": mt5.ORDER_FILLING_FOK,
                                }
                                result = mt5.order_send(close_request)
                                if result is None:
                                    print(f"❌ order_send returned None (no response from server): {mt5.last_error()}")
                                    continue
                                if result.retcode == mt5.TRADE_RETCODE_DONE:
                                    print(f"Closed half due to engulfing {symbol}")
                                    send_telegram_message(f"Engulfing detected, closed half and breakeven {symbol} { L['direction']} on {timeframe_to_str(timeframe)}")
                                    modify_trade_to_breakeven(symbol, pos.ticket, pos.price_open)
                            else:
                                modify_trade_to_breakeven(symbol, pos.ticket, pos.price_open)
                        elif count >= 2 :
                            if pos.volume > min_lot:
                                t = decimal_places(get_min_lot_size(symbol))
                                half = round(pos.volume-(pos.volume / 1.5), t)
                                current_price = mt5.symbol_info_tick(symbol).bid if pos.type == 1 else mt5.symbol_info_tick(symbol).ask
                                close_type = 1 if pos.type == 0 else 0
                                close_request = {
                                    "action": mt5.TRADE_ACTION_DEAL,
                                    "symbol": symbol,
                                    "volume": half,
                                    "type": close_type,
                                    "position": pos.ticket,
                                    "price": current_price,
                                    "deviation": 10,
                                    "magic": pos.magic,
                                    "comment": pos.comment,
                                    "type_time": mt5.ORDER_TIME_GTC,
                                    "type_filling": mt5.ORDER_FILLING_FOK,
                                }
                                result = mt5.order_send(close_request)
                                if result is None:
                                    print(f"❌ order_send returned None (no response from server): {mt5.last_error()}")
                                    continue
                                if result.retcode == mt5.TRADE_RETCODE_DONE:
                                    print(f"Closed half due to engulfing {symbol}")
                                    send_telegram_message(f"Engulfing detected, closed half and breakeven {symbol} { L['direction']} on {timeframe_to_str(timeframe)}")
                            elif pos.volume == min_lot:
                                current_price = mt5.symbol_info_tick(symbol).bid if pos.type == 1 else mt5.symbol_info_tick(symbol).ask
                                close_type = 1 if pos.type == 0 else 0
                                close_request = {
                                    "action": mt5.TRADE_ACTION_DEAL,
                                    "symbol": symbol,
                                    "volume": pos.volume,
                                    "type": close_type,
                                    "position": pos.ticket,
                                    "price": current_price,
                                    "deviation": 10,
                                    "magic": pos.magic,
                                    "comment": pos.comment,
                                    "type_time": mt5.ORDER_TIME_GTC,
                                    "type_filling": mt5.ORDER_FILLING_FOK,
                                }
                                result = mt5.order_send(close_request)
                                if result is None:
                                    print(f"❌ order_send returned None (no response from server): {mt5.last_error()}")
                                    continue
                                if result.retcode == mt5.TRADE_RETCODE_DONE:
                                    print(f"Closed due to too many engulfing {symbol}")
                                    send_telegram_message(f"Too many  engulfing, closed trade {symbol} { L['direction']} on {timeframe_to_str(timeframe)}")
                                del levels[key]
                                if key in active_channels: del active_channels[key]

    positions=mt5.positions_get()
    for pos in positions:
        key = (pos.symbol, pos.magic)
        if key not in levels:
            symbol = pos.symbol
            timeframe = pos.magic
            if key not in old_engulfs:
                old_engulfs[key] = {'engulf_count': 0, 'last_engulf_time': None}
            L = old_engulfs[key]
            deals = mt5.history_deals_get(position=pos.ticket)
            if deals:
                open_time = deals[0].time
                entry_time = pd.to_datetime(open_time, unit='s')
            else:
                continue  # Skip if no deals found
            candles = get_candles(symbol, timeframe, 100)
            recent = candles[candles['time'] > entry_time].reset_index(drop=True)
            if len(recent) < 5: continue
            direction = "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL"
            eng_i = detect_opposite_engulfing(recent, direction, symbol, timeframe)
            if eng_i is not None:
                eng_time = recent['time'].iloc[eng_i]
                if 'last_engulf_time' not in L or L['last_engulf_time'] is None or eng_time > L['last_engulf_time']:
                    L['last_engulf_time'] = eng_time
                    L['engulf_count'] += 1
                    print(f"Updated engulf_count to {L['engulf_count']} for {symbol}")
                    count = L['engulf_count']
                    min_lot = get_min_lot_size(symbol)
                    if count == 1:
                        if pos.volume > min_lot:
                            t = decimal_places(get_min_lot_size(symbol))
                            half = round(pos.volume-(pos.volume / 1.5), t)
                            current_price = mt5.symbol_info_tick(symbol).bid if pos.type == 1 else mt5.symbol_info_tick(symbol).ask
                            close_type = 1 if pos.type == 0 else 0
                            close_request = {
                                "action": mt5.TRADE_ACTION_DEAL,
                                "symbol": symbol,
                                "volume": half,
                                "type": close_type,
                                "position": pos.ticket,
                                "price": current_price,
                                "deviation": 10,
                                "magic": pos.magic,
                                "comment": pos.comment,
                                "type_time": mt5.ORDER_TIME_GTC,
                                "type_filling": mt5.ORDER_FILLING_FOK,
                            }
                            result = mt5.order_send(close_request)
                            if result is None:
                                print(f"❌ order_send returned None (no response from server): {mt5.last_error()}")
                                continue
                            if result.retcode == mt5.TRADE_RETCODE_DONE:
                                print(f"Closed half due to engulfing {symbol}")
                                send_telegram_message(f"Engulfing detected, closed half and breakeven {symbol} { direction} on {timeframe_to_str(timeframe)}")
                                modify_trade_to_breakeven(symbol, pos.ticket, pos.price_open)
                        else:
                            modify_trade_to_breakeven(symbol, pos.ticket, pos.price_open)
                    elif count >= 2:
                        if pos.volume > min_lot:
                            t = decimal_places(get_min_lot_size(symbol))
                            half = round(pos.volume-(pos.volume / 1.5), t)
                            current_price = mt5.symbol_info_tick(symbol).bid if pos.type == 1 else mt5.symbol_info_tick(symbol).ask
                            close_type = 1 if pos.type == 0 else 0
                            close_request = {
                                "action": mt5.TRADE_ACTION_DEAL,
                                "symbol": symbol,
                                "volume": half,
                                "type": close_type,
                                "position": pos.ticket,
                                "price": current_price,
                                "deviation": 10,
                                "magic": pos.magic,
                                "comment": pos.comment,
                                "type_time": mt5.ORDER_TIME_GTC,
                                "type_filling": mt5.ORDER_FILLING_FOK,
                            }
                            result = mt5.order_send(close_request)
                            if result is None:
                                print(f"❌ order_send returned None (no response from server): {mt5.last_error()}")
                                continue
                            if result.retcode == mt5.TRADE_RETCODE_DONE:
                                print(f"Closed half due to engulfing {symbol}")
                                send_telegram_message(f"Engulfing detected, closed half and breakeven {symbol} { direction} on {timeframe_to_str(timeframe)}")
                        elif pos.volume == min_lot:
                            current_price = mt5.symbol_info_tick(symbol).bid if pos.type == 1 else mt5.symbol_info_tick(symbol).ask
                            close_type = 1 if pos.type == 0 else 0
                            close_request = {
                                "action": mt5.TRADE_ACTION_DEAL,
                                "symbol": symbol,
                                "volume": pos.volume,
                                "type": close_type,
                                "position": pos.ticket,
                                "price": current_price,
                                "deviation": 10,
                                "magic": pos.magic,
                                "comment": pos.comment,
                                "type_time": mt5.ORDER_TIME_GTC,
                                "type_filling": mt5.ORDER_FILLING_FOK,
                            }
                            result = mt5.order_send(close_request)
                            if result is None:
                                print(f"❌ order_send returned None (no response from server): {mt5.last_error()}")
                                continue
                            if result.retcode == mt5.TRADE_RETCODE_DONE:
                                print(f"Closed due to too many engulfing {symbol}")
                                send_telegram_message(f"Too many  engulfing, closed trade {symbol} { direction} on {timeframe_to_str(timeframe)}")
                            del old_engulfs[key]
                            if key in active_channels: del active_channels[key]

def check_engulfing_before_tp2_for_breakeven_trades():
    """Check if engulfing patterns occurred before TP2 (the old TP1) was hit for breakeven trades"""
    for ticket in list(breakeven_trades):
        position = mt5.positions_get(ticket=ticket)
        if not position:
            continue
        
        position = position[0]
        symbol = position.symbol
        timeframe = position.magic
        trade_direction = "BUY" if position.type == mt5.ORDER_TYPE_BUY else "SELL"
        entry_price = position.price_open

        if position.sl != position.price_open :
            print(f"Skipping {symbol} ticket {ticket} — SL already adjusted from breakeven")
            continue
        
        # Get TP2 (old TP1) from position comment
        _tp1_unused, tp2 = extract_tp_levels_from_comment(position.comment)
        
        if not tp2:
            continue
        
        # Get trade entry time
        entry_time = pd.to_datetime(position.time, unit='s')
        
        # Check if engulfing happened before TP2
        key = (symbol, timeframe)
        engulf_time = None
        
        # Get engulf time from levels or old_engulfs
        if key in levels and 'last_engulf_time' in levels[key]:
            engulf_time = levels[key]['last_engulf_time']
        elif key in old_engulfs and 'last_engulf_time' in old_engulfs[key]:
            engulf_time = old_engulfs[key]['last_engulf_time']
        
        # Fetch candles from entry to now to check when TP2 was hit
        rates = mt5.copy_rates_range(symbol, timeframe, entry_time, datetime.now())
        if rates is None or len(rates) == 0:
            continue
        
        recent_candles = pd.DataFrame(rates)
        recent_candles['time'] = pd.to_datetime(recent_candles['time'], unit='s')
        
        # Find when TP2 was first hit
        tp2_hit_time = None
        for i in range(len(recent_candles)):
            if trade_direction == "BUY":
                if recent_candles['high'].iloc[i] >= tp2:
                    tp2_hit_time = recent_candles['time'].iloc[i]
                    break
            elif trade_direction == "SELL":
                if recent_candles['low'].iloc[i] <= tp2:
                    tp2_hit_time = recent_candles['time'].iloc[i]
                    break
        
        # If both engulfing and TP2 hit occurred, compare times
        if engulf_time and tp2_hit_time:
            if engulf_time < tp2_hit_time:
                print(f"⚠️ Engulfing detected at {engulf_time} (BEFORE TP2 hit at {tp2_hit_time}) for {symbol} "
                      f"on {timeframe_to_str(timeframe)}")
                
                if trade_direction == 'BUY':
                    distance_to_tp2 = tp2 - entry_price
                    new_sl = entry_price + (distance_to_tp2 * 0.3)  # 30% of the way to TP2
                else:  # SELL
                    distance_to_tp2 = entry_price - tp2
                    new_sl = entry_price - (distance_to_tp2 * 0.3)  # 30% of the way to TP2
                
                request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": ticket,
                    "sl": new_sl,
                    "tp": position.tp,  # Keep original TP
                    "symbol": symbol,
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_FOK,
                }
                
                result = mt5.order_send(request)
                if result is None:
                    print(f"❌ order_send returned None (no response from server): {mt5.last_error()}")
                    continue
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"✅ Tightened SL for breakeven trade {symbol}: New SL={new_sl:.5f}")
                    send_telegram_message(f"✅ Tightened SL for {symbol} {trade_direction} on {timeframe_to_str(timeframe)} due to pre-TP2 engulfing : New SL={new_sl:.5f}")
                else:
                    print(f"❌ Failed to tighten SL for {symbol}: {result.comment}")
            else:
                print(f"ℹ️ Engulfing happened AFTER TP2 hit for {symbol}, no SL adjustment needed")

def check_conflicting_slopes():
    """Check for conflicting slopes across all possible timeframe combinations"""
    # Get all active symbols across all timeframes
    all_symbols = set()
    timeframe_combinations = [
        (mt5.TIMEFRAME_M1, mt5.TIMEFRAME_M5),
        (mt5.TIMEFRAME_M1, mt5.TIMEFRAME_M15),
        (mt5.TIMEFRAME_M1, mt5.TIMEFRAME_M30),
        (mt5.TIMEFRAME_M1, mt5.TIMEFRAME_H1),
        (mt5.TIMEFRAME_M5, mt5.TIMEFRAME_M15),
        (mt5.TIMEFRAME_M5, mt5.TIMEFRAME_M30),
        (mt5.TIMEFRAME_M5, mt5.TIMEFRAME_H1), 
        (mt5.TIMEFRAME_M15, mt5.TIMEFRAME_M30),
        (mt5.TIMEFRAME_M15, mt5.TIMEFRAME_H1),
        (mt5.TIMEFRAME_M30, mt5.TIMEFRAME_H1)
    ]
    
    # Find symbols that exist in multiple timeframes
    for tf1, tf2 in timeframe_combinations:
        symbols_tf1 = {symbol for symbol, timeframe in active_channels.keys() if timeframe == tf1}
        symbols_tf2 = {symbol for symbol, timeframe in active_channels.keys() if timeframe == tf2}
        overlaps = symbols_tf1 & symbols_tf2
        
        for symbol in overlaps:
            key1 = (symbol, tf1)
            key2 = (symbol, tf2)
            
            if key1 in active_channels and key2 in active_channels:
                df1 = active_channels[key1]['df']
                df2 = active_channels[key2]['df']
                slope1 = df1['trend'].iloc[-1] - df1['trend'].iloc[0]
                slope2 = df2['trend'].iloc[-1] - df2['trend'].iloc[0]
                
                # Delete the lower timeframe if slopes conflict
                if (slope1 > 0 and slope2 < 0) or (slope1 < 0 and slope2 > 0):
                    # Always delete the lower timeframe
                    if tf1 < tf2:  # tf1 is lower timeframe
                        del active_channels[key1]
                        if key1 in levels: 
                            del levels[key1]
                        print(f"🗑️ Deleted {symbol}_{timeframe_to_str(tf1)} due to conflicting slope with {timeframe_to_str(tf2)}")
                    else:  # tf2 is lower timeframe
                        del active_channels[key2]
                        if key2 in levels: 
                            del levels[key2]
                        print(f"🗑️ Deleted {symbol}_{timeframe_to_str(tf2)} due to conflicting slope with {timeframe_to_str(tf1)}")

def get_trade_info(symbol, tf):
    positions = mt5.positions_get(symbol=symbol) or []
    for pos in positions:
        if pos.magic == tf:
            tp1, tp2 = extract_tp_levels_from_comment(pos.comment)
            return {
                'type': 'position',
                'ticket': pos.ticket,
                'direction': "BUY" if pos.type == 0 else "SELL",
                'sl': pos.sl,
                'tp': pos.tp,
                'tp1': tp1,
                'tp2': tp2,
                'entry_price': pos.price_open,
            }
    orders = mt5.orders_get(symbol=symbol) or []
    for ord in orders:
        if ord.magic == tf:
            tp1, tp2 = extract_tp_levels_from_comment(ord.comment)
            return {
                'type': 'order',
                'ticket': ord.ticket,
                'direction': "BUY" if ord.type == mt5.ORDER_TYPE_BUY_LIMIT else "SELL",
                'sl': ord.sl,
                'tp': ord.tp,
                'tp1': tp1,
                'tp2': tp2,
                'entry_price': ord.price_open,
            }
    return None

def check_extend_active_tp_from_higher_tf(symbol, direction, timeframe):
    """Extend TP3 from higher timeframe for any symbol with multiple active timeframes.
    Uses TP2 (the old TP1) as the gating checkpoint that decides when the extension
    kicks in, and TP3 (the old TP2 / broker-side final target) as the value that gets
    extended."""
    current_tf = timeframe
    
    # Define higher timeframes for each current timeframe
    higher_timeframes = {
        mt5.TIMEFRAME_M1: [mt5.TIMEFRAME_M5,mt5.TIMEFRAME_M15, mt5.TIMEFRAME_M30, mt5.TIMEFRAME_H1],
        mt5.TIMEFRAME_M5: [mt5.TIMEFRAME_M15, mt5.TIMEFRAME_M30, mt5.TIMEFRAME_H1],
        mt5.TIMEFRAME_M15: [mt5.TIMEFRAME_M30, mt5.TIMEFRAME_H1],
        mt5.TIMEFRAME_M30: [mt5.TIMEFRAME_H1],
        mt5.TIMEFRAME_H1: []  # No higher timeframe than H1
    }
    
    lower_info = get_trade_info(symbol, current_tf)
    if not lower_info:
        return False
    
    if lower_info['direction'] != direction:
        return False
    
    current_price = mt5.symbol_info_tick(symbol).ask if direction == 'BUY' else mt5.symbol_info_tick(symbol).bid
    modified = False
    
    for higher_tf in higher_timeframes.get(current_tf, []):
        higher_info = get_trade_info(symbol, higher_tf)
        if not higher_info:
            continue
        
        if lower_info['direction'] != higher_info['direction']:
            continue
        
        tp1_lower = lower_info['tp1']
        tp2_lower = lower_info['tp2']
        tp2_higher = higher_info['tp2']
        tp3_lower = lower_info['tp']
        tp3_higher = higher_info['tp']
        
        if tp1_lower is None or tp2_lower is None or tp2_higher is None:
            continue
        
        # First, check if TP3 was already extended (TP3s are the same)
        tp_extended = (direction == 'BUY' and tp3_lower == tp3_higher) or \
                     (direction == 'SELL' and tp3_lower == tp3_higher)
        
        if tp_extended:
            # Check if lower timeframe has crossed higher timeframe's TP2
            crossed_higher_tp2 = False
            if direction == 'BUY':
                crossed_higher_tp2 = current_price >= tp2_higher
            else:  # SELL
                crossed_higher_tp2 = current_price <= tp2_higher
            
            if crossed_higher_tp2:
                # Move SL of lower timeframe to higher timeframe's TP2
                request = {
                    "action": mt5.TRADE_ACTION_SLTP if lower_info['type'] == 'position' else mt5.TRADE_ACTION_MODIFY,
                    "sl": tp2_lower,
                    "tp": tp3_lower,  # Keep the extended TP3
                    "symbol": symbol,
                    "comment": format_tp_comment(tp1_lower, tp2_lower),
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_FOK,
                }
                if lower_info['type'] == 'position':
                    request["position"] = lower_info['ticket']
                else:
                    request["order"] = lower_info['ticket']
                
                result = mt5.order_send(request)
                if result is None:
                    print(f"❌ order_send returned None (no response from server): {mt5.last_error()}")
                    continue
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"🛡️ Moved SL for {symbol} {timeframe_to_str(current_tf)} to TP2: {tp2_higher:.5f}")
                    send_telegram_message(f"🛡️ Moved Deriv SL for {symbol} {timeframe_to_str(current_tf)} to TP2: {tp2_higher:.5f}")
                    modified = True
                else:
                    print(f"❌ Failed to move SL for {symbol}: {result.comment}")
        
        # Original TP extension logic - only execute if TP3 hasn't been extended yet
        elif not tp_extended:
            crossed_lower_tp2 = (direction == 'BUY' and current_price >= tp2_lower) or \
                               (direction == 'SELL' and current_price <= tp2_lower)
            
            if not crossed_lower_tp2:
                continue
            
            valid_extension = False
            if direction == 'BUY':
                valid_extension = tp3_higher > tp3_lower
            else:  # SELL
                valid_extension = tp3_higher < tp3_lower
            
            if not valid_extension:
                continue
            
            # Modify the lower trade to extend TP3
            request = {
                "action": mt5.TRADE_ACTION_SLTP if lower_info['type'] == 'position' else mt5.TRADE_ACTION_MODIFY,
                "sl": lower_info['sl'],
                "tp": tp3_higher,
                "symbol": symbol,
                "comment": format_tp_comment(tp1_lower, tp2_lower),
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_FOK,
            }
            if lower_info['type'] == 'position':
                request["position"] = lower_info['ticket']
            else:
                request["order"] = lower_info['ticket']
            
            result = mt5.order_send(request)
            if result is None:
                print(f"❌ order_send returned None (no response from server): {mt5.last_error()}")
                continue
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"📈 Extended TP3 for {symbol} {timeframe_to_str(current_tf)} to {timeframe_to_str(higher_tf)} TP3: {tp3_higher:.5f}")
                send_telegram_message(f"📈 Extended Deriv TP3 for {symbol} {timeframe_to_str(current_tf)} to {timeframe_to_str(higher_tf)} TP3: {tp3_higher:.5f}")
                modified = True
            else:
                print(f"❌ Failed to extend TP3 for {symbol}: {result.comment}")
    
    return modified

def update_profit_tracking():
    """Update profit tracking using candle-based bar counts for all active positions"""
    TIMEFRAME_PROFIT_BARS = 48
    TIMEFRAME_PROFIT_DURATIONS = {
        "M1": timedelta(minutes=48),
        "M5": timedelta(minutes=240),    
        "M15": timedelta(minutes=720),     
        "M30": timedelta(hours=24),
        "H1": timedelta(hours=48),     
    }
    DEFAULT_PROFIT_DURATION= timedelta(hours=48)
    
    positions = mt5.positions_get()
    if positions is None:
        return
    
    for position in positions:
        ticket = position.ticket
        symbol = position.symbol
        timeframe = position.magic  # Use the position's timeframe
        direction = "BUY" if position.type == mt5.ORDER_TYPE_BUY else "SELL"
        entry_price = position.price_open
        current_profit = position.profit

        if position.sl == entry_price:
            print(f"Position {ticket} has breakeven already applied")
            continue
        if (position.type == mt5.ORDER_TYPE_BUY and position.sl > position.price_open) or \
        (position.type == mt5.ORDER_TYPE_SELL and position.sl < position.price_open):
            print(f"Position {ticket} has its SL already applied")
            continue

        required_duration = TIMEFRAME_PROFIT_DURATIONS.get(timeframe_to_str(timeframe), DEFAULT_PROFIT_DURATION)
        
        # Skip if not currently in profit (real-time check as gatekeeper)
        if current_profit <= 0:
            if ticket in profit_tracking:
                del profit_tracking[ticket]  # Reset tracking if out of profit
            continue
        
        # Get entry time
        deals = mt5.history_deals_get(position=ticket)
        if not deals:
            continue
        entry_time = pd.to_datetime(deals[0].time, unit='s')
         
        # Fetch candles from entry time to now (buffer: 100 bars)
        rates = mt5.copy_rates_range(symbol, timeframe, entry_time, datetime.now())
        if rates is None or len(rates) == 0:
            continue
        candles = pd.DataFrame(rates)
        candles['time'] = pd.to_datetime(candles['time'], unit='s')
        
        # Count consecutive profitable bars from the end (current streak)
        consecutive_profit_bars = 0
        for i in range(len(candles) - 1, -1, -1):  # Start from latest bar backward
            candle = candles.iloc[i]
            is_profitable = False
            if direction == "BUY":
                is_profitable = candle['low'] > entry_price  
            else:  # SELL
                is_profitable = candle['high'] < entry_price 
            
            if is_profitable:
                consecutive_profit_bars += 1
            else:
                break  # Reset streak on non-profitable bar
        
        # Initialize or update tracking with bar count
        if ticket not in profit_tracking:
            profit_tracking[ticket] = {
                'consecutive_bars': 0,
                'breakeven_applied': False,
                'symbol': symbol,
                'timeframe': timeframe
            }
        
        profit_tracking[ticket]['consecutive_bars'] = consecutive_profit_bars
        
        # Apply breakeven if streak >= required bars and not already applied
        if (consecutive_profit_bars >= TIMEFRAME_PROFIT_BARS and 
            not profit_tracking[ticket]['breakeven_applied']):
            modify_trade_to_breakeven(symbol, ticket, entry_price)
            profit_tracking[ticket]['breakeven_applied'] = True
            hours = required_duration.total_seconds() / 3600
            print(f"⏰ Position {ticket} has been in profit for {hours:.1f} hours - applying breakeven")
            send_telegram_message(f"⏰ {symbol} {direction} trade on {timeframe_to_str(timeframe)} has been in profit for {hours:.1f} hours - applying breakeven")

def cleanup_profit_tracking():
    """Remove completed trades from profit tracking"""
    positions = mt5.positions_get()
    if positions is None:
        positions = []
    
    active_tickets = {pos.ticket for pos in positions}
    
    # Remove tracking for closed positions
    for ticket in list(profit_tracking.keys()):
        if ticket not in active_tickets:
            del profit_tracking[ticket]

def monitor_breakeven_trades():
    for ticket in list(breakeven_trades):
        if ticket in list(active_trades):
            del active_trades[ticket]
        pos = mt5.positions_get(ticket=ticket)
        if pos:
            continue
        deals = mt5.history_deals_get(position=ticket)
        if deals:
            first_deal = deals[0]
            entry_price = first_deal.price
            exit_deals = [d for d in deals if d.entry == 1]  # entry=1 means exit
            last_sl = 0.0
            if exit_deals:
                last_exit = exit_deals[-1]
                if last_exit.comment:
                    try:
                        last_sl = extract_price_from_comment(last_exit.comment)
                    except ValueError:
                        last_sl = 0.0
            direction = "BUY" if first_deal.type == mt5.DEAL_TYPE_BUY else "SELL"
            total_profit = sum(d.profit for d in deals)
            if total_profit > 0:
                msg = "hit TP"
            elif total_profit < 0 and (entry_price!=last_sl):
                msg = "hit SL"
            else:
                msg = "closed at breakeven"
            symbol = breakeven_trades[ticket]['symbol']
            timeframe = breakeven_trades[ticket]['timeframe']
            if msg == "hit SL":
                start_cooldown(symbol, timeframe)
            send_telegram_message(f"{symbol} {direction} on {timeframe_to_str(timeframe)}  {msg}")
            key = (symbol, timeframe)
            if key in levels:
                del levels[key]
            if key in active_channels:
                del active_channels[key]
            del breakeven_trades[ticket]

def monitor_active_trades():
    positions = mt5.positions_get() 
    for pos in positions:
        if pos.ticket not in list(active_trades) and pos.ticket not in list(breakeven_trades):
            active_trades[pos.ticket] = {'symbol':pos.symbol, 'timeframe': pos.magic}
        else:
            continue

    for ticket in list(active_trades):
        pos = mt5.positions_get(ticket=ticket)
        if pos:
            continue
        deals = mt5.history_deals_get(position=ticket)
        if deals:
            first_deal = deals[0]
            entry_price = first_deal.price
            exit_deals = [d for d in deals if d.entry == 1]  # entry=1 means exit
            last_sl = 0.0
            if exit_deals:
                last_exit = exit_deals[-1]
                if last_exit.comment:
                    try:
                        last_sl = extract_price_from_comment(last_exit.comment)
                    except ValueError:
                        last_sl = 0.0
            direction = "BUY" if first_deal.type == mt5.DEAL_TYPE_BUY else "SELL"
            total_profit = sum(d.profit for d in deals)
            if total_profit > 0:
                msg = "hit TP"
            elif total_profit < 0 and (entry_price!=last_sl):
                msg = "hit SL"
            else:
                msg = "closed at breakeven"
            symbol = active_trades[ticket]['symbol']
            timeframe = active_trades[ticket]['timeframe']
            if msg == "hit SL":
                start_cooldown(symbol, timeframe)
            send_telegram_message(f"{symbol} {direction} on {timeframe_to_str(timeframe)}   {msg}" )
            key = (symbol, timeframe)
            if key in levels:
                del levels[key]
            if key in active_channels:
                del active_channels[key]
            del active_trades[ticket]

def start_cooldown(symbol: str, timeframe: int):
    """Block this symbol+tf for 1 hour after SL."""
    end_time = datetime.now() + timedelta(hours=1)
    cooldown[(symbol, timeframe)] = end_time
    print(f"Cooldown started for {symbol} {timeframe_to_str(timeframe)} until {end_time.strftime('%H:%M:%S')}")

def is_cooldown_active(symbol: str, timeframe: int) -> bool:
    key = (symbol, timeframe)
    if key not in cooldown:
        return False
    if datetime.now() >= cooldown[key]:
        # time has elapsed → clean up
        del cooldown[key]
        print(f"Cooldown finished for {symbol} {timeframe_to_str(timeframe)}")
        return False
    return True

def _current_week_key(now):
    iso = now.isocalendar()
    return (iso[0], iso[1])  # (ISO year, ISO week number)

def _current_month_key(now):
    return (now.year, now.month)

def initialize_risk_tracking():
    """Sets the weekly/monthly reference balances used for drawdown tracking.
    Called once at startup, and again internally whenever a new week/month begins."""
    account = mt5.account_info()
    if account is None:
        print("⚠️ Could not read account info to initialize drawdown tracking.")
        return
    now = datetime.now()
    balance = account.balance
    risk_state['week_start_balance'] = balance
    risk_state['week_key'] = _current_week_key(now)
    risk_state['month_start_balance'] = balance
    risk_state['month_key'] = _current_month_key(now)
    risk_state['weekly_blocked'] = False
    risk_state['monthly_blocked'] = False
    print(f"📊 Drawdown tracking initialized. Balance: {balance:.2f}")

def is_trading_blocked():
    """True if either the weekly or monthly drawdown limit has been hit and not yet reset."""
    return risk_state.get('weekly_blocked', False) or risk_state.get('monthly_blocked', False)

def close_all_pending_orders(reason=""):
    """Closes every resting pending order across all symbols (used when a drawdown limit is hit)."""
    orders = mt5.orders_get()
    if not orders:
        return
    for order in orders:
        request = {
            "action": mt5.TRADE_ACTION_REMOVE,
            "order": order.ticket,
        }
        result = mt5.order_send(request)
        if result is None:
            print(f"❌ order_send returned None (no response from server): {mt5.last_error()}")
            continue
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"✅ Closed pending order {order.ticket} for {order.symbol} ({reason})")
            key = (order.symbol, order.magic)
            if key in active_channels:
                del active_channels[key]
            if key in levels:
                del levels[key]
        else:
            comment = result.comment if result else "no response"
            print(f"❌ Failed to close pending order {order.ticket} for {order.symbol}: {comment}")

def update_drawdown_protection():
    """
    Tracks weekly/monthly account loss against the balance recorded at the start
    of each period. If loss meets/exceeds the configured threshold, blocks new
    entries and closes all pending orders until the next period begins, at
    which point tracking resets and new entries are allowed again. A Telegram
    alert is sent both when a limit is hit and when the block resets.
    """
    account = mt5.account_info()
    if account is None:
        return
    now = datetime.now()
    balance = account.balance

    if risk_state['week_start_balance'] is None or risk_state['month_start_balance'] is None:
        initialize_risk_tracking()
        return

    # --- Weekly rollover ---
    week_key = _current_week_key(now)
    if week_key != risk_state['week_key']:
        if risk_state['weekly_blocked']:
            send_telegram_message("✅ <b>Weekly drawdown block reset</b>\nNew entries are allowed again.")
            print("✅ Weekly drawdown block reset - new entries allowed again.")
        risk_state['week_key'] = week_key
        risk_state['week_start_balance'] = balance
        risk_state['weekly_blocked'] = False
        print(f"📅 New week started - weekly drawdown reference reset to {balance:.2f}")

    # --- Monthly rollover ---
    month_key = _current_month_key(now)
    if month_key != risk_state['month_key']:
        if risk_state['monthly_blocked']:
            send_telegram_message("✅ <b>Monthly drawdown block reset</b>\nNew entries are allowed again.")
            print("✅ Monthly drawdown block reset - new entries allowed again.")
        risk_state['month_key'] = month_key
        risk_state['month_start_balance'] = balance
        risk_state['monthly_blocked'] = False
        print(f"📅 New month started - monthly drawdown reference reset to {balance:.2f}")

    # --- Weekly loss check ---
    week_start_balance = risk_state['week_start_balance']
    if week_start_balance and week_start_balance > 0:
        weekly_loss_pct = (week_start_balance - balance) / week_start_balance * 100
        if weekly_loss_pct >= WEEKLY_LOSS_LIMIT_PCT and not risk_state['weekly_blocked']:
            risk_state['weekly_blocked'] = True
            print(f"🛑 Weekly drawdown limit hit: -{weekly_loss_pct:.2f}%")
            send_telegram_message(
                f"🛑 <b>Weekly drawdown limit hit</b>\nLoss: -{weekly_loss_pct:.2f}% (limit {WEEKLY_LOSS_LIMIT_PCT}%)\n"
                f"Blocking new entries and closing all pending orders until next week."
            )
            close_all_pending_orders(reason="weekly drawdown limit")

    # --- Monthly loss check ---
    month_start_balance = risk_state['month_start_balance']
    if month_start_balance and month_start_balance > 0:
        monthly_loss_pct = (month_start_balance - balance) / month_start_balance * 100
        if monthly_loss_pct >= MONTHLY_LOSS_LIMIT_PCT and not risk_state['monthly_blocked']:
            risk_state['monthly_blocked'] = True
            print(f"🛑 Monthly drawdown limit hit: -{monthly_loss_pct:.2f}%")
            send_telegram_message(
                f"🛑 <b>Monthly drawdown limit hit</b>\nLoss: -{monthly_loss_pct:.2f}% (limit {MONTHLY_LOSS_LIMIT_PCT}%)\n"
                f"Blocking new entries and closing all pending orders until next month."
            )
            close_all_pending_orders(reason="monthly drawdown limit")

def check_a_plus_setup(symbol,df, trend_slope, current_timeframe):
    """
    Check if channel qualifies for A+ setup based on supply/demand zones
    Returns True if A+ setup is detected, False otherwise
    """
    global supply_demand_zones
    
    key= (symbol,current_timeframe)
    # Get or calculate supply/demand zones for this symbol
    if key not in supply_demand_zones:
        timeframe_map = {
            mt5.TIMEFRAME_M1: [mt5.TIMEFRAME_M5],
            mt5.TIMEFRAME_M5: [mt5.TIMEFRAME_M15],
            mt5.TIMEFRAME_M15: [mt5.TIMEFRAME_M30],
            mt5.TIMEFRAME_M30: [mt5.TIMEFRAME_H1],
            mt5.TIMEFRAME_H1: [mt5.TIMEFRAME_H4]
        }
        
        higher_timeframes = timeframe_map.get(current_timeframe, [mt5.TIMEFRAME_H1])
        
        supply_demand_zones[key] = {'supply_zones': [], 'demand_zones': []}
        
        for ht in higher_timeframes:
            try:
                # Fetch historical data from higher timeframe
                historical_data = get_candles(symbol, ht, 200)  # More bars for better zone detection
                if historical_data.empty:
                    continue
                
                # Analyze zones for this higher timeframe
                analyzer = SupplyDemandAnalyzer(historical_data, lookback_period=15, min_touch_points=2)
                ht_supply_zones, ht_demand_zones = analyzer.identify_zones()
                
                # Add zones from this timeframe to the combined list
                supply_demand_zones[key]['supply_zones'].extend(ht_supply_zones)
                supply_demand_zones[key]['demand_zones'].extend(ht_demand_zones)
                
                print(f"✅ Found {len(ht_supply_zones)} supply zones and {len(ht_demand_zones)} demand zones for {symbol} {timeframe_to_str(current_timeframe)} on {timeframe_to_str(ht)}")
                
            except Exception as e:
                print(f"❌ Error analyzing {symbol} on {timeframe_to_str(ht)}: {str(e)}")
                continue
        
    zones = supply_demand_zones[key]
    # For downward channel (negative slope), check demand zones (support)
    if trend_slope < 0:
        for zone in zones['demand_zones']:
            if not zone['is_broken']:
                zone_price = zone['price']
                # Check if any candle in the dataframe touches this demand zone
                for i in range(len(df)):
                    candle_low = df['low'].iloc[i]
                    candle_high = df['high'].iloc[i]
                    
                    # Check if zone price falls within candle's range
                    if candle_low <= zone_price <= candle_high:
                        print(f"✅ A+ Setup detected for {symbol}: Downward channel touches demand zone at {zone_price:.5f}")
                        return True
        
        # Also check broken supply zones (now acting as support)
        for zone in zones['supply_zones']:
            if zone['is_broken']:
                zone_price = zone['price']
                for i in range(len(df)):
                    candle_low = df['low'].iloc[i]
                    candle_high = df['high'].iloc[i]
                    
                    if candle_low <= zone_price <= candle_high:
                        print(f"✅ A+ Setup detected for {symbol}: Downward channel touches broken supply zone (now support) at {zone_price:.5f}")
                        return True
    
    # For upward channel (positive slope), check supply zones (resistance)
    elif trend_slope > 0:
        for zone in zones['supply_zones']:
            if not zone['is_broken']:
                zone_price = zone['price']
                # Check if any candle in the dataframe touches this supply zone
                for i in range(len(df)):
                    candle_low = df['low'].iloc[i]
                    candle_high = df['high'].iloc[i]
                    
                    # Check if zone price falls within candle's range
                    if candle_low <= zone_price <= candle_high:
                        print(f"✅ A+ Setup detected for {symbol}: Upward channel touches supply zone at {zone_price:.5f}")
                        return True
        
        # Also check broken demand zones (now acting as resistance)
        for zone in zones['demand_zones']:
            if zone['is_broken']:
                zone_price = zone['price']
                for i in range(len(df)):
                    candle_low = df['low'].iloc[i]
                    candle_high = df['high'].iloc[i]
                    
                    if candle_low <= zone_price <= candle_high:
                        print(f"✅ A+ Setup detected for {symbol}: Upward channel touches broken demand zone (now resistance) at {zone_price:.5f}")
                        return True
    
    return False

def preload_supply_demand_zones():
    """
    Preload supply/demand zones for all active symbols using appropriate higher timeframes
    """
    global supply_demand_zones, zone_last_loaded,ZONE_RELOAD_CONFIG
    
    # Get all symbols from your configuration
    all_symbols = set(TIMEFRAME_H1 + TIMEFRAME_M30 + TIMEFRAME_M15 + TIMEFRAME_M5+TIMEFRAME_M1)
    
    # Define which higher timeframe to use for each trading timeframe
    timeframe_map = {
        mt5.TIMEFRAME_M1: [mt5.TIMEFRAME_M5],
        mt5.TIMEFRAME_M5: [mt5.TIMEFRAME_M15],  # For M5 trades: Use M15 zones
        mt5.TIMEFRAME_M15: [mt5.TIMEFRAME_M30], # For M15 trades: Use M30 zones
        mt5.TIMEFRAME_M30: [mt5.TIMEFRAME_H1],  # For M30 trades: Use H1 zones
        mt5.TIMEFRAME_H1: [mt5.TIMEFRAME_H4]    # For H1 trades: Use H4 zones
    }
    
    # Trading timeframes we actually use
    trading_timeframes = [mt5.TIMEFRAME_M5, mt5.TIMEFRAME_M15, mt5.TIMEFRAME_M30, mt5.TIMEFRAME_H1]# M1 deactivated - no need to preload its zones
    
    print("🔄 Preloading supply-demand zones for all timeframe combinations...")
    
    for symbol in all_symbols:
        for trading_tf in trading_timeframes:
            key = (symbol, trading_tf)
            
            # Initialize zones for this symbol/trading timeframe pair
            if key not in supply_demand_zones:
                supply_demand_zones[key] = {
                    'supply_zones': [],
                    'demand_zones': []
                }
            
            # Get the higher timeframe(s) to analyze
            higher_timeframes = timeframe_map.get(trading_tf, [mt5.TIMEFRAME_H1])
            
            for ht in higher_timeframes:
                try:
                    # Fetch historical data from higher timeframe
                    historical_data = get_candles(symbol, ht, 200)
                    if historical_data.empty:
                        continue
                    
                    # Analyze zones for this higher timeframe
                    analyzer = SupplyDemandAnalyzer(historical_data, lookback_period=15, min_touch_points=2)
                    ht_supply_zones, ht_demand_zones = analyzer.identify_zones()
                    
                    # Add zones to the appropriate key
                    supply_demand_zones[key]['supply_zones'].extend(ht_supply_zones)
                    supply_demand_zones[key]['demand_zones'].extend(ht_demand_zones)
                    
                    print(f"✅ {symbol} ({timeframe_to_str(trading_tf)}): Found {len(ht_supply_zones)} supply, {len(ht_demand_zones)} demand zones on {timeframe_to_str(ht)}")
                    
                except Exception as e:
                    print(f"❌ Error preloading zones for {symbol} on {timeframe_to_str(ht)}: {str(e)}")
                    continue
    
            # Update last loaded time for this key
            zone_last_loaded[key] = datetime.now()
            reload_period = ZONE_RELOAD_CONFIG.get(trading_tf, timedelta(days=5))
            next_reload = zone_last_loaded[key] + reload_period
            print(f"📅 {symbol} {timeframe_to_str(trading_tf)} zones loaded at: {zone_last_loaded[key].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"🔄 Next zones reload at: {next_reload.strftime('%Y-%m-%d %H:%M:%S')}")
    
def should_reload_zones():
    """
    Check if zones should be reloaded based on the timeframe-specific schedule
    """
    global zone_last_loaded
    global to_be_reloaded
    global supply_demand_zones
    global ZONE_RELOAD_CONFIG

    timeframe_map = {
        mt5.TIMEFRAME_M1: [mt5.TIMEFRAME_M5],
        mt5.TIMEFRAME_M5: [mt5.TIMEFRAME_M15],  # For M5 trades: Use M15 zones
        mt5.TIMEFRAME_M15: [mt5.TIMEFRAME_M30], # For M15 trades: Use M30 zones
        mt5.TIMEFRAME_M30: [mt5.TIMEFRAME_H1],  # For M30 trades: Use H1 zones
        mt5.TIMEFRAME_H1: [mt5.TIMEFRAME_H4]    # For H1 trades: Use H4 zones
    }
    
    # Clear to_be_reloaded list before checking
    to_be_reloaded = []
    
    # Check all zone_last_loaded keys
    for key in list(zone_last_loaded.keys()):
        symbol, timeframe = key
        time_since_last_load = datetime.now() - zone_last_loaded[key]
        
        # Get reload period for this timeframe (default to 5 days if not specified)
        reload_period = ZONE_RELOAD_CONFIG.get(timeframe, timedelta(days=5))
        
        if time_since_last_load >= reload_period:
            to_be_reloaded.append(key)
            if key in supply_demand_zones:
                del supply_demand_zones[key]  # Clear existing zones
                print(f"🗑️ Cleared expired zones for {symbol} on {timeframe_to_str(timeframe)}")
    
    # Reload zones for all keys in to_be_reloaded
    for key in to_be_reloaded:
        symbol, timeframe = key
        
        # Re-initialize zones for this key
        if key not in supply_demand_zones:
            supply_demand_zones[key] = {
                'supply_zones': [],
                'demand_zones': []
            }
        
        # Get the higher timeframe(s) to analyze
        higher_timeframes = timeframe_map.get(timeframe, [mt5.TIMEFRAME_H1])
        
        for ht in higher_timeframes:
            try:
                # Fetch historical data from higher timeframe
                historical_data = get_candles(symbol, ht, 200)
                if historical_data.empty:
                    continue
                
                # Analyze zones for this higher timeframe
                analyzer = SupplyDemandAnalyzer(historical_data, lookback_period=15, min_touch_points=2)
                ht_supply_zones, ht_demand_zones = analyzer.identify_zones()
                
                # Add zones to the appropriate key
                supply_demand_zones[key]['supply_zones'].extend(ht_supply_zones)
                supply_demand_zones[key]['demand_zones'].extend(ht_demand_zones)
                
                print(f"✅ {symbol} ({timeframe_to_str(timeframe)}): Found {len(ht_supply_zones)} supply, {len(ht_demand_zones)} demand zones on {timeframe_to_str(ht)}")
                
            except Exception as e:
                print(f"❌ Error reloading zones for {symbol} on {timeframe_to_str(ht)}: {str(e)}")
                continue
        
        # Update last loaded time for this key after reload
        zone_last_loaded[key] = datetime.now()
        reload_period = ZONE_RELOAD_CONFIG.get(timeframe, timedelta(days=5))
        next_reload = zone_last_loaded[key] + reload_period
        print(f"📅 {symbol} {timeframe_to_str(timeframe)} zones reloaded at: {zone_last_loaded[key].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔄 Next zones reload at: {next_reload.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Clear the to_be_reloaded list after processing
    to_be_reloaded = []

def extract_price_from_comment(comment):
    """Extract price from comment field (TP1 or SL)"""
    if not comment:
        return None
    try:
        numbers = re.findall(r"[-+]?\d*\.\d+|\d+", str(comment))
        if numbers:
            return float(numbers[0])
    except (ValueError, TypeError):
        pass
    return None

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

clear_plots_folder()
initialize_risk_tracking()


send_telegram_message("Deriv Bot running")
while True:
    try:
        if not is_connected():
            print("🚫 Network or MT5 disconnected.")
            mt5.shutdown()
            reconnected=False
            max_attempts =3
            for i in range(0,max_attempts):
                check_time = datetime.now() + timedelta(minutes=10)
                print(f"\033[92m Waiting for network reconnection at {check_time.strftime("%H:%M:%S")}...\033[0m")
                time.sleep(600)
                if is_connected():
                    reconnected=True
                    print("✅ Network or MT5 reconnected.")
                    send_telegram_message("✅ Network or MT5 reconnected.")
                    break
            if not reconnected:
                clear_plots_folder()
                sys.exit("❌ Terminating script due to disconnection.")
        if len(supply_demand_zones)==0:
            print("🔄 Initializing supply/demand zones...")
            preload_supply_demand_zones()
        should_reload_zones()
        update_drawdown_protection()
        clean_manual_deleted()
        monitor_breakeven_trades()
        monitor_active_trades()
        update_profit_tracking()
        cleanup_profit_tracking()
        del_completed()
        update_pending_order_status()
        handle_engulfing_patterns()
        check_engulfing_before_tp2_for_breakeven_trades()
        active=[]

        active_symbols = set(TIMEFRAME_H1 + TIMEFRAME_M15 + TIMEFRAME_M30 + TIMEFRAME_M5 + TIMEFRAME_M1)
        for symbol in active_symbols:
            positions = mt5.positions_get(symbol=symbol) or []
            orders = mt5.orders_get(symbol=symbol) or []
            processed_tfs = set()
            for trade in list(positions) + list(orders):
                magic = trade.magic
                if magic in processed_tfs:
                    continue
                processed_tfs.add(magic)
                if hasattr(trade, 'identifier'):  # Position
                    direction = "BUY" if trade.type == 0 else "SELL"
                else:  # Order
                    if trade.type not in [mt5.ORDER_TYPE_BUY_LIMIT, mt5.ORDER_TYPE_SELL_LIMIT]:
                        continue
                    direction = "BUY" if trade.type == mt5.ORDER_TYPE_BUY_LIMIT else "SELL"
                check_extend_active_tp_from_higher_tf(symbol, direction, magic)

        for symbol in TIMEFRAME_H1 :
                timeframe = mt5.TIMEFRAME_H1
                if is_cooldown_active(symbol, timeframe):
                    continue
                if (symbol, timeframe) not in active_channels:
                    num_bars = [40,50,60,70,80,100]
                    for i in num_bars:
                        candles = get_candles(symbol, timeframe, i)
                        if candles.empty:
                            continue
                        channel  = detect_regression_channel(candles,symbol,timeframe)
                        if channel is not None and channel[0] == True and channel[2]==True:
                            # Save channel and breakout info
                            active_channels[(symbol,timeframe)] = {
                                    "df": channel[1].copy(),
                                    "breakout_idx": None,
                                    "last_touch_idx": None,
                                    "last_touch_price":None,
                                    "num_bars":i,
                                    "timeframe":timeframe,
                                    "last_time" :channel[1]['time'].iloc[-2],
                                    "a_plus_setup": channel[2]  # Add the A+ setup flag
                            }
                            df = active_channels[(symbol,timeframe)]["df"]
                            last = df.iloc[-10:]
                            last_trend = df['trend']     
                            trend_slope = last_trend.iloc[-1] - last_trend.iloc[0]
                            for i in range(len(last)):
                                candle = last.iloc[i]
                                upper_at_i = last['upper'].iloc[i]
                                lower_at_i = last['lower'].iloc[i]
                                
                                broke_above = candle['high'] > upper_at_i
                                broke_below = candle['low'] < lower_at_i

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
                            if (symbol, timeframe) not in active_channels:
                                continue
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
                            if position.magic != timeframe:
                                continue
                            check_tp1_and_manage_trades(symbol, position.comment, timeframe)
                            check_tp2_and_manage_trades(symbol, position.comment, timeframe)
                close_pending(symbol)
 
        for symbol in TIMEFRAME_M15 :
                timeframe = mt5.TIMEFRAME_M15
                if is_cooldown_active(symbol, timeframe):
                    continue
                if (symbol, timeframe) not in active_channels:
                    num_bars = [40,50,60,70,80]
                    for i in num_bars:
                        candles = get_candles(symbol, timeframe, i)
                        if candles.empty:
                            continue
                        channel  = detect_regression_channel(candles,symbol,timeframe)
                        if channel is not None and channel[0] == True and channel[2]==True:
                            # Save channel and breakout info
                            active_channels[(symbol,timeframe)] = {
                                    "df": channel[1].copy(),
                                    "breakout_idx": None,
                                    "last_touch_idx": None,
                                    "last_touch_price":None,
                                    "num_bars":i,
                                    "timeframe":timeframe,
                                    "last_time" :channel[1]['time'].iloc[-2],
                                    "a_plus_setup": channel[2]  # Add the A+ setup flag
                            }
                            df = active_channels[(symbol,timeframe)]["df"]
                            last = df.iloc[-10:]
                            last_trend = df['trend']     
                            trend_slope = last_trend.iloc[-1] - last_trend.iloc[0]
                            for i in range(len(last)):
                                candle = last.iloc[i]
                                upper_at_i = last['upper'].iloc[i]
                                lower_at_i = last['lower'].iloc[i]
                                
                                broke_above = candle['high'] > upper_at_i
                                broke_below = candle['low'] < lower_at_i

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
                            if (symbol, timeframe) not in active_channels:
                                continue
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
                            if position.magic != timeframe:
                                continue
                            check_tp1_and_manage_trades(symbol, position.comment, timeframe)
                            check_tp2_and_manage_trades(symbol, position.comment, timeframe)
                close_pending(symbol)

        for symbol in TIMEFRAME_M30 :
                timeframe = mt5.TIMEFRAME_M30
                if is_cooldown_active(symbol, timeframe):
                    continue
                if (symbol, timeframe) not in active_channels:
                    num_bars = [40,50,60,70,80]
                    for i in num_bars:
                        candles = get_candles(symbol, timeframe, i)
                        if candles.empty:
                            continue
                        channel  = detect_regression_channel(candles,symbol,timeframe)
                        if channel is not None and channel[0] == True and channel[2]==True:
                            # Save channel and breakout info
                            active_channels[(symbol,timeframe)] = {
                                    "df": channel[1].copy(),
                                    "breakout_idx": None,
                                    "last_touch_idx": None,
                                    "last_touch_price":None,
                                    "num_bars":i,
                                    "timeframe":timeframe,
                                    "last_time" :channel[1]['time'].iloc[-2],
                                    "a_plus_setup": channel[2]  # Add the A+ setup flag
                            }
                            df = active_channels[(symbol,timeframe)]["df"]
                            last = df.iloc[-10:]
                            last_trend = df['trend']     
                            trend_slope = last_trend.iloc[-1] - last_trend.iloc[0]
                            for i in range(len(last)):
                                candle = last.iloc[i]
                                upper_at_i = last['upper'].iloc[i]
                                lower_at_i = last['lower'].iloc[i]
                                
                                broke_above = candle['high'] > upper_at_i
                                broke_below = candle['low'] < lower_at_i

                                # Breakout matches trend direction? Then delete
                                if symbol in M30_B:
                                    if (trend_slope > 0 ) or (trend_slope < 0 and broke_below):
                                            print(f"🚨 {symbol}_{timeframe_to_str(timeframe)} broke out in the direction of the trend — clearing it.")
                                            del active_channels[(symbol,timeframe)]
                                            break# Skip further processing this round
                                elif symbol in M30_BS:
                                    if (trend_slope > 0  and broke_above) or (trend_slope < 0 and broke_below):
                                            print(f"🚨 {symbol}_{timeframe_to_str(timeframe)} broke out in the direction of the trend — clearing it.")
                                            del active_channels[(symbol,timeframe)]
                                            break# Skip further processing this round
                                elif symbol in M30_S:
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
                            if (symbol, timeframe) not in active_channels:
                                continue
                            if fib_levels:
                                    direction = "BUY" if candles['close'].iloc[entry_idx] > candles['upper'].iloc[entry_idx] else "SELL"
                                    if symbol in M30_pen :
                                        pending(symbol, direction, candles['close'].iloc[entry_idx], fib_levels['sl'], fib_levels['tp3'],fib_levels['sniper'],timeframe)
                                    elif symbol in M30_pl:
                                        place_trade(symbol, direction, candles['close'].iloc[entry_idx], fib_levels['sl1'], fib_levels['tp3'],timeframe)
                if (symbol, timeframe) in levels :
                    L =levels[(symbol,timeframe)]
                    
                    check_tp1_and_manage_trades(symbol, L["tp1"], timeframe)
                    check_tp2_and_manage_trades(symbol, L["tp2"], timeframe)
                else:
                    positions = mt5.positions_get(symbol=symbol)
                    if positions is not None:
                        for position in positions:
                            if position.magic != timeframe:
                                continue
                            check_tp1_and_manage_trades(symbol, position.comment, timeframe)
                            check_tp2_and_manage_trades(symbol, position.comment, timeframe)
                close_pending(symbol)

        for symbol in TIMEFRAME_M5 :
                timeframe = mt5.TIMEFRAME_M5
                if is_cooldown_active(symbol, timeframe):
                    continue
                if (symbol, timeframe) not in active_channels:
                    num_bars = [30,40,50,60,70,80]
                    for i in num_bars:
                        candles = get_candles(symbol, timeframe, i)
                        if candles.empty:
                            continue
                        channel  = detect_regression_channel(candles,symbol,timeframe)
                        if channel is not None and channel[0] == True and channel[2]==True:
                            # Save channel and breakout info
                            active_channels[(symbol,timeframe)] = {
                                    "df": channel[1].copy(),
                                    "breakout_idx": None,
                                    "last_touch_idx": None,
                                    "last_touch_price":None,
                                    "num_bars":i,
                                    "timeframe":timeframe,
                                    "last_time" :channel[1]['time'].iloc[-2],
                                    "a_plus_setup": channel[2]  # Add the A+ setup flag
                            }
                            df = active_channels[(symbol,timeframe)]["df"]
                            last = df.iloc[-10:]
                            last_trend = df['trend']     
                            trend_slope = last_trend.iloc[-1] - last_trend.iloc[0]
                            for i in range(len(last)):
                                candle = last.iloc[i]
                                upper_at_i = last['upper'].iloc[i]
                                lower_at_i = last['lower'].iloc[i]
                                
                                broke_above = candle['high'] > upper_at_i
                                broke_below = candle['low'] < lower_at_i

                                # Breakout matches trend direction? Then delete
                                if symbol in M5_B:
                                    if (trend_slope > 0 ) or (trend_slope < 0 and broke_below):
                                            print(f"🚨 {symbol}_{timeframe_to_str(timeframe)} broke out in the direction of the trend — clearing it.")
                                            del active_channels[(symbol,timeframe)]
                                            break# Skip further processing this round
                                elif symbol in M5_S:
                                    if (trend_slope > 0  and broke_above) or (trend_slope < 0 ):
                                            print(f"🚨 {symbol}_{timeframe_to_str(timeframe)} broke out in the direction of the trend — clearing it.")
                                            del active_channels[(symbol,timeframe)]
                                            break# Skip further processing this round
                                elif symbol in M5_BS:
                                    if (trend_slope > 0  and broke_above) or (trend_slope < 0 and broke_below):
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
                            if (symbol, timeframe) not in active_channels:
                                continue
                            if fib_levels:
                                    direction = "BUY" if candles['close'].iloc[entry_idx] > candles['upper'].iloc[entry_idx] else "SELL"
                                    if symbol in M5_pen :
                                        pending(symbol, direction, candles['close'].iloc[entry_idx], fib_levels['sl'], fib_levels['tp3'],fib_levels['sniper'],timeframe)
                                    elif symbol in M5_pl:
                                        place_trade(symbol, direction, candles['close'].iloc[entry_idx], fib_levels['sl1'], fib_levels['tp3'],timeframe)
                if (symbol, timeframe) in levels :
                    L =levels[(symbol,timeframe)]
                    
                    check_tp1_and_manage_trades(symbol, L["tp1"], timeframe)
                    check_tp2_and_manage_trades(symbol, L["tp2"], timeframe)
                else:
                    positions = mt5.positions_get(symbol=symbol)
                    if positions is not None:
                        for position in positions:
                            if position.magic != timeframe:
                                continue
                            check_tp1_and_manage_trades(symbol, position.comment, timeframe)
                            check_tp2_and_manage_trades(symbol, position.comment, timeframe)
                close_pending(symbol)

        for symbol in TIMEFRAME_M1 :
                timeframe = mt5.TIMEFRAME_M1
                if is_cooldown_active(symbol, timeframe):
                    continue
                if (symbol, timeframe) not in active_channels:
                    num_bars = [40,50,60,70,80,100]
                    for i in num_bars:
                        candles = get_candles(symbol, timeframe, i)
                        if candles.empty:
                            continue
                        channel  = detect_regression_channel(candles,symbol,timeframe)
                        if channel is not None and channel[0] == True and channel[2]==True:
                            # Save channel and breakout info
                            active_channels[(symbol,timeframe)] = {
                                    "df": channel[1].copy(),
                                    "breakout_idx": None,
                                    "last_touch_idx": None,
                                    "last_touch_price":None,
                                    "num_bars":i,
                                    "timeframe":timeframe,
                                    "last_time" :channel[1]['time'].iloc[-2],
                                    "a_plus_setup": channel[2]  # Add the A+ setup flag
                            }
                            df = active_channels[(symbol,timeframe)]["df"]
                            last = df.iloc[-10:]
                            last_trend = df['trend']     
                            trend_slope = last_trend.iloc[-1] - last_trend.iloc[0]
                            for i in range(len(last)):
                                candle = last.iloc[i]
                                upper_at_i = last['upper'].iloc[i]
                                lower_at_i = last['lower'].iloc[i]
                                
                                broke_above = candle['high'] > upper_at_i
                                broke_below = candle['low'] < lower_at_i

                                # Breakout matches trend direction? Then delete
                                if symbol in M1_B:
                                    if (trend_slope > 0 ) or (trend_slope < 0 and broke_below):
                                            print(f"🚨 {symbol}_{timeframe_to_str(timeframe)} broke out in the direction of the trend — clearing it.")
                                            del active_channels[(symbol,timeframe)]
                                            break# Skip further processing this round
                                elif symbol in M1_BS:
                                    if (trend_slope > 0  and broke_above) or (trend_slope < 0 and broke_below):
                                            print(f"🚨 {symbol}_{timeframe_to_str(timeframe)} broke out in the direction of the trend — clearing it.")
                                            del active_channels[(symbol,timeframe)]
                                            break# Skip further processing this round
                                elif symbol in M1_S:
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
                            if (symbol, timeframe) not in active_channels:
                                continue
                            if fib_levels:
                                    direction = "BUY" if candles['close'].iloc[entry_idx] > candles['upper'].iloc[entry_idx] else "SELL"
                                    if symbol in M1_pen :
                                        pending(symbol, direction, candles['close'].iloc[entry_idx], fib_levels['sl'], fib_levels['tp3'],fib_levels['sniper'],timeframe)
                                    elif symbol in M1_pl:
                                        place_trade(symbol, direction, candles['close'].iloc[entry_idx], fib_levels['sl1'], fib_levels['tp3'],timeframe)
                if (symbol, timeframe) in levels :
                    L =levels[(symbol,timeframe)]
                    
                    check_tp1_and_manage_trades(symbol, L["tp1"], timeframe)
                    check_tp2_and_manage_trades(symbol, L["tp2"], timeframe)
                else:
                    positions = mt5.positions_get(symbol=symbol)
                    if positions is not None:
                        for position in positions:
                            if position.magic != timeframe:
                                continue
                            check_tp1_and_manage_trades(symbol, position.comment, timeframe)
                            check_tp2_and_manage_trades(symbol, position.comment, timeframe)
                close_pending(symbol)


        check_conflicting_slopes()
        check_conflicting_trades()

        for (symbol,timeframe) in active_channels:
            active.append(f'{symbol}_{timeframe_to_str(timeframe)}')

        plot_active_channels()
        print(f"{active} have validated channels.")
        next_check_time = datetime.now() + timedelta(minutes=2.5)
        print(f"\033[92m Waiting for next trading opportunity at {next_check_time.strftime("%H:%M:%S")}...\033[0m")
        time.sleep(150)
    except Exception as e:
        send_telegram_message("Deriv Bot stopped")
        print(f"⚠️ Unexpected error: {e}")
        clear_plots_folder()
        raise