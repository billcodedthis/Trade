import pandas as pd
import numpy as np
import MetaTrader5 as mt5
import time
import mplfinance as mpf
import requests
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os
from pathlib import Path
import signal
import sys

MT5_PATH ="C:\\Program Files\\MetaTrader 5 Terminal\\terminal64.exe"
if not mt5.initialize(path=MT5_PATH):
    print("❌ Failed to connect to MetaTrader 5", mt5.last_error())
    quit()
else:
    print("✅ Successfully connected to MT5!")


# Define symbols and timeframes
Basket_Indices= ['AUD Basket', 'EUR Basket', 'GBP Basket', 'Gold Basket', 'USD Basket']
Conversions= ['BCHUSD.conv', 'BTCUSD.conv', 'ETHUSD.conv', 'EURUSD.conv', 'LTCUSD.conv', 'USDAED.conv', 'XAGUSD.conv', 'XAUUSD.conv']
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

TIMEFRAME_H1 = Basket_Indices+Conversions+Crash_Boom_Indices+Crypto+DEX_Indices+Energies+Forex_Major+Forex_Minor+Jump_Indices+Metals+Multi_Step_Indices+Range_Break+Skewed_Step+Step_Indices+Stock_Indices+Volatility_Indices
H1_B= []
H1_S=[]
H1_BS=Basket_Indices+Conversions+Crash_Boom_Indices+Crypto+DEX_Indices+Energies+Forex_Major+Forex_Minor+Jump_Indices+Metals+Multi_Step_Indices+Range_Break+Skewed_Step+Step_Indices+Stock_Indices+Volatility_Indices
H1_pen= Basket_Indices+Conversions+Crash_Boom_Indices+Crypto+DEX_Indices+Energies+Forex_Major+Forex_Minor+Jump_Indices+Metals+Multi_Step_Indices+Range_Break+Skewed_Step+Step_Indices+Stock_Indices+Volatility_Indices
H1_pl= []

TIMEFRAME_M15= Basket_Indices+Conversions+Crash_Boom_Indices+Crypto+DEX_Indices+Energies+Forex_Major+Forex_Minor+Jump_Indices+Metals+Multi_Step_Indices+Range_Break+Skewed_Step+Step_Indices+Stock_Indices+Volatility_Indices
M15_B= []
M15_S=[]
M15_BS=Basket_Indices+Conversions+Crash_Boom_Indices+Crypto+DEX_Indices+Energies+Forex_Major+Forex_Minor+Jump_Indices+Metals+Multi_Step_Indices+Range_Break+Skewed_Step+Step_Indices+Stock_Indices+Volatility_Indices
M15_pen= Basket_Indices+Conversions+Crash_Boom_Indices+Crypto+DEX_Indices+Energies+Forex_Major+Forex_Minor+Jump_Indices+Metals+Multi_Step_Indices+Range_Break+Skewed_Step+Step_Indices+Stock_Indices+Volatility_Indices
M15_pl= []

TIMEFRAME_M5= Basket_Indices+Conversions+Crash_Boom_Indices+Crypto+DEX_Indices+Energies+Forex_Major+Forex_Minor+Jump_Indices+Metals+Multi_Step_Indices+Range_Break+Skewed_Step+Step_Indices+Stock_Indices+Volatility_Indices
M5_S=[]
M5_B= []
M5_BS=Basket_Indices+Conversions+Crash_Boom_Indices+Crypto+DEX_Indices+Energies+Forex_Major+Forex_Minor+Jump_Indices+Metals+Multi_Step_Indices+Range_Break+Skewed_Step+Step_Indices+Stock_Indices+Volatility_Indices
M5_pen= Basket_Indices+Conversions+Crash_Boom_Indices+Crypto+DEX_Indices+Energies+Forex_Major+Forex_Minor+Jump_Indices+Metals+Multi_Step_Indices+Range_Break+Skewed_Step+Step_Indices+Stock_Indices+Volatility_Indices
M5_pl= []

active_channels = {}
levels={}
old_engulfs={}
breakeven_trades = {}
active_trades={}
cooldown = {}     


DOWNLOADS_FOLDER = str(Path.home() / "OneDrive - University of Ghana")
PLOTS_FOLDER = os.path.join(DOWNLOADS_FOLDER, "MT5_Regression_Channels_visuals")

# Create the folder if it doesn't exist
if not os.path.exists(PLOTS_FOLDER):
    os.makedirs(PLOTS_FOLDER)

supply_demand_zones = {}  # Store zones for each symbol
zone_last_loaded = None   # Track when zones were last loaded
ZONE_RELOAD_DAYS = 5   

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
            
            if touches >= self.min_touches:
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
            
            if touches >= self.min_touches:
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
        MT5_PATH = "C:\\Program Files\\MetaTrader 5 Terminal\\terminal64.exe"
        if not mt5.initialize(path=MT5_PATH):
            return False
        return True
    except:
        return False

def send_telegram_image(image_path, caption=""):
    bot_token = "7851945053:AAExF_JdIYTbCWytWNcAnIK9kFaHXZ1sWE8"
    channel_id = "-1001960135029"
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
    bot_token = "7851945053:AAExF_JdIYTbCWytWNcAnIK9kFaHXZ1sWE8"  # replace with your bot token
    channel_id = "-1001960135029"  # e.g., "-1001234567890"
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
                    'sniper': ('purple', ':', 'Sniper Entry')
                }

                for level in ['sl', 'sl1', 'tp1', 'tp2', 'sniper']:
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
                    for level in ['sniper', 'sl', 'sl1', 'tp1', 'tp2']:
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
        last = df.iloc[-num_bars:]
        upper = df['upper'].iloc[-1]       # Access upper line from DataFrame
        lower = df['lower'].iloc[-1]       # Access lower line from DataFrame
        last_trend = df['trend']     
        trend_slope = last_trend.iloc[-1] - last_trend.iloc[0]
        for i in range(len(last)):
            candle = last.iloc[i]
            broke_above = candle['high'] > upper
            broke_below = candle['low'] < lower

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

    return True

def detect_regression_channel(df,symbol,timeframe):
    positions = [pos for pos in mt5.positions_get(symbol=symbol) if pos.magic == timeframe]
    orders = [order for order in mt5.orders_get(symbol=symbol) if order.magic == timeframe]
    if positions or orders:
        return
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
                
                for m in range(1, len(analysis_df)):
                    if analysis_df['high'].iloc[m] == upper[m]:
                        upper_touch_count += 1
                    if analysis_df['low'].iloc[m] == lower[m]:
                        lower_touch_count += 1
        
        # Original validation condition (unchanged)
        if (upper_touch_count >= 2 and lower_touch_count >= 1) or (upper_touch_count >= 1 and lower_touch_count >= 2):
            validated = True
            break
    
    # Check for touch imbalance and adjust boundaries if needed
    if not validated:
        if upper_touch_count >= 2 and lower_touch_count == 0:
            # Adjust lower boundary to be closer to trend line
            lower = trend_line - 2 * std_dev  # Was -3, increase
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
                    lower_full += new_lower_adjustment  # Mirror adjustment in full data
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
                            if analysis_df['high'].iloc[m] == upper[m]:
                                upper_touch_count += 1
                            if analysis_df['low'].iloc[m] == lower[m]:
                                lower_touch_count += 1
            if (upper_touch_count >= 2 and lower_touch_count >= 1) or (upper_touch_count >= 1 and lower_touch_count >= 2):
                validated = True
                
        elif lower_touch_count >= 2 and upper_touch_count == 0:
            # Adjust upper boundary to be closer to trend line
            upper = trend_line + std_dev  # Was +2, decrease
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
                    upper_full += new_upper_adjustment  # Mirror adjustment in full data
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
                            if analysis_df['high'].iloc[m] == upper[m]:
                                upper_touch_count += 1
                            if analysis_df['low'].iloc[m] == lower[m]:
                                lower_touch_count += 1
            if (upper_touch_count >= 2 and lower_touch_count >= 1) or (upper_touch_count >= 1 and lower_touch_count >= 2):
                validated = True
                

    a_plus_setup = False
    if validated:
        # Calculate trend slope for A+ setup check
        trend_slope = full_df['trend'].iloc[-1] - full_df['trend'].iloc[0]
        a_plus_setup = check_a_plus_setup(symbol,full_df, trend_slope)

    return validated, full_df, a_plus_setup 

def find_valid_entry(df, breakout_idx, last_touch_idx,symbol,timeframe):
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
        if df['open'].iloc[i] > last_touch_price and df['high'].iloc[i] > df['upper'].iloc[i]: 
            entry_candle_idx = i-1
            break
        elif df['open'].iloc[i] < last_touch_price and df['low'].iloc[i] < df['lower'].iloc[i]: 
            entry_candle_idx = i-1
            break
        
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

        elif df['close'].iloc[i-1] >= df['lower'][i-1] and df['close'].iloc[i] < df['lower'][i]:
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
            "tp1": swing_point + (2.8 * risk),  
            "tp2": entry_price + (3.5 * risk), 
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
            "tp1": swing_point - (2.8 * risk),   
            "tp2": entry_price - (3.5 * risk), 
            "sniper": swing_point - (0.3 * risk), 
            "sl1": swing_point   + (0.2 * risk),
            "direction": "SELL",
            "entry_time": df['time'].iloc[entry_idx],
            "engulf_count": 0,
            "last_engulf_time": None,
            "entry":None
        }
    
    return levels[(symbol,timeframe)]
    
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
            "volume": lot_size(symbol) ,
            "type": mt5.ORDER_TYPE_BUY_LIMIT if direction == "BUY" else mt5.ORDER_TYPE_SELL_LIMIT,
            "price": sniper,
            "sl": sl,
            "tp": tp,
            "deviation": 10,
            "magic": timeframe,
            "comment": f"{levels[(symbol,timeframe)]["tp1"]}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
    order = mt5.order_send(request1)
    if order.retcode == mt5.TRADE_RETCODE_DONE:
        plot_filename = os.path.join(PLOTS_FOLDER, f"{symbol}_{timeframe_to_str(timeframe)}_channel.png")
        send_telegram_image(plot_filename,f"📥 <b>Deriv Pending Trade</b>\nSymbol: {symbol}\nDirection: {direction}\nEntry: {sniper:.4f}\nSL: {sl:.4f}\nTP1: {levels[(symbol,timeframe)]["tp1"]:.4f}\nTP2: {tp:.4f}")
        print(f"Pending Trade placed: {direction} {symbol} @ {sniper}")
        levels[(symbol, timeframe)]['is_pending'] = True
        levels[(symbol, timeframe)]['pending_order_ticket'] = order.order
        levels[(symbol, timeframe)]['entry'] = entry_price
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
        "volume": lot_size(symbol) ,
        "type": mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL,
        "price": entry_price,
        "sl": sl1,
        "tp": tp,
        "deviation": 10,
        "magic": timeframe,
        "comment": f"{levels[(symbol,timeframe)]["tp1"]}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }
    order = mt5.order_send(request)
    if order.retcode == mt5.TRADE_RETCODE_DONE:
        plot_filename = os.path.join(PLOTS_FOLDER, f"{symbol}_{timeframe_to_str(timeframe)}_channel.png")
        send_telegram_image(plot_filename,f"🚀 <b>Deriv Market Trade</b>\nSymbol: {symbol}\nDirection: {direction}\nEntry: {entry_price:.4f}\nSL: {sl1:.4f}\nTP1: {levels[(symbol,timeframe)]["tp1"]:.4f}\nTP2: {tp:.4f}")
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
    if (position.type == mt5.ORDER_TYPE_BUY and position.sl > position.price_open) or \
        (position.type == mt5.ORDER_TYPE_SELL and position.sl < position.price_open):
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
            tp1 = L["tp1"]   # ← Use the stored TP1 from levels, NOT order.comment
            direction = L["direction"]
            entry_time = L["entry_time"]  # This is the breakout candle time — CORRECT reference!
        else:
            # For old orders not in levels
            try:
                tp1 = float(order.comment)
            except ValueError:
                continue  # Skip if comment isn't a valid float
            direction = "SELL" if order.type == mt5.ORDER_TYPE_SELL_LIMIT else "BUY"
            entry_time = pd.to_datetime(order.time_setup, unit='s')  # Fixed: Use order setup time

        # Fetch candles since the SIGNAL (breakout), not since order placement
        rates = mt5.copy_rates_range(symbol, timeframe, entry_time, datetime.now())
        if rates is None or len(rates) == 0:
            continue
        recent_candles = pd.DataFrame(rates)
        recent_candles['time'] = pd.to_datetime(recent_candles['time'], unit='s')
        crossed_tp1 = False
        if direction == "BUY":
            if (recent_candles['high'] >= tp1).any():
                crossed_tp1 = True
        elif direction == "SELL":
            if (recent_candles['low'] <= tp1).any():
                crossed_tp1 = True
        if crossed_tp1:
            request = {
                    "action": mt5.TRADE_ACTION_REMOVE,
                    "order": order.ticket,
                }
            result = mt5.order_send(request)
                
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
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
                    
def check_tp1_and_manage_trades(symbol, tp1,timeframe):
    if isinstance(tp1,str):
        if tp1=='':
            return
        Tp1=float(tp1)
        positions = mt5.positions_get(symbol=symbol)
        if positions is not None:
            for position in positions:
                if position.magic != timeframe:
                    continue
                entry_price = position.price_open
                current_price = mt5.symbol_info_tick(symbol).bid if position.type == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(symbol).ask
                direction = "SELL" if position.type == mt5.ORDER_TYPE_SELL else "BUY"
                entry_time = pd.to_datetime(position.time, unit='s')
                

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

                # Original TP1 logic (half position & move SL to breakeven)
                if (position.type == mt5.ORDER_TYPE_BUY and crossed_tp1) or \
                (position.type == mt5.ORDER_TYPE_SELL and crossed_tp1):
                    if position.volume == get_min_lot_size(symbol):
                        modify_trade_to_breakeven(symbol, position.ticket, entry_price)
                        continue
                    if position.volume <= (lot_size(symbol)/ 2):
                        print(f"✅ Position {position.ticket} for {symbol} already halved at TP1.")
                        modify_trade_to_breakeven(symbol, position.ticket, entry_price)
                        continue
                    if position.sl == position.price_open:
                        print(f"✅ Position {position.ticket} for {symbol} SL has already been modified")
                    else:
                        t = decimal_places(get_min_lot_size(symbol))
                        half_lot = round(position.volume / 2, t)
                        close_request = {
                            "action": mt5.TRADE_ACTION_DEAL,
                            "symbol": symbol,
                            "volume": half_lot,
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
                            send_telegram_message(f"TP1 hit. Apply breakeven and close half of deriv {direction} positions for {symbol} on {timeframe_to_str(timeframe)} trade.✅")
                            print(f"✅ Closed half of position {position.ticket} for {symbol} at TP1.")
                            modify_trade_to_breakeven(symbol, position.ticket, entry_price)
                        elif close_result.comment == "Invalid volume":
                            send_telegram_message(f"TP1 hit. Apply breakeven and close half of deriv {direction} positions for {symbol} on {timeframe_to_str(timeframe)} trade.✅")
                            print(f"{symbol} cannot be halved, but SL has been moved to breakeven.")
                            modify_trade_to_breakeven(symbol, position.ticket, entry_price)
                        else:
                            print(f"❌ Failed to close half of  of {symbol}: {close_result.comment}")

    else:
        positions = mt5.positions_get(symbol=symbol)
        if positions is not None:
            for position in positions:
                if position.magic != timeframe:
                    continue
                entry_price = position.price_open
                current_price = mt5.symbol_info_tick(symbol).bid if position.type == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(symbol).ask
                magic =position.magic
                direction = "SELL" if position.type == mt5.ORDER_TYPE_SELL else "BUY"
                entry_time = pd.to_datetime(position.time, unit='s')
                

                rates = mt5.copy_rates_range(symbol, timeframe, entry_time, datetime.now())
                if rates is None or len(rates) == 0:
                    continue
                recent_candles = pd.DataFrame(rates)
                recent_candles['time'] = pd.to_datetime(recent_candles['time'], unit='s')
                crossed_tp1 = False
                if direction == "BUY":
                    if (recent_candles['high'] >= tp1).any():
                        crossed_tp1 = True
                elif direction == "SELL":
                    if (recent_candles['low'] <= tp1).any():
                        crossed_tp1 = True

                # Original TP1 logic (half position & move SL to breakeven)
                if timeframe == magic:
                    if (position.type == mt5.ORDER_TYPE_BUY and crossed_tp1 ) or \
                    (position.type == mt5.ORDER_TYPE_SELL and crossed_tp1 ):
                        if position.volume == get_min_lot_size(symbol):
                            modify_trade_to_breakeven(symbol, position.ticket, entry_price)
                            continue
                        if position.volume <= (lot_size(symbol)/ 2):
                            print(f"✅ Position {position.ticket} for {symbol} already halved at TP1.")
                            modify_trade_to_breakeven(symbol, position.ticket, entry_price)
                            continue
                        if position.sl == position.price_open:
                            print(f"✅ Position {position.ticket} for {symbol} SL has already been modified")
                        else:
                            t = decimal_places(get_min_lot_size(symbol))
                            half_lot = round(position.volume / 2, t)
                            close_request = {
                                "action": mt5.TRADE_ACTION_DEAL,
                                "symbol": symbol,
                                "volume": half_lot,
                                "type": mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
                                "position": position.ticket,
                                "price": current_price,
                                "deviation": 10,
                                "magic": magic,
                                "comment": position.comment,
                                "type_time": mt5.ORDER_TIME_GTC,
                                "type_filling": mt5.ORDER_FILLING_FOK,
                            }
                            close_result = mt5.order_send(close_request)
                            if close_result.retcode == mt5.TRADE_RETCODE_DONE:
                                send_telegram_message(f"TP1 hit. Apply breakeven and close half of deriv {direction} positions for {symbol} on {timeframe_to_str(timeframe)}  trade.✅")
                                print(f"✅ Closed half of position {position.ticket} for {symbol} at TP1.")
                                modify_trade_to_breakeven(symbol, position.ticket, entry_price)
                            elif close_result.comment == "Invalid volume":
                                send_telegram_message(f"TP1 hit. Apply breakeven and close half of deriv {direction} positions for {symbol} on {timeframe_to_str(timeframe)}  trade.✅")
                                print(f"{symbol} cannot be halved, but SL has been moved to breakeven.")
                                modify_trade_to_breakeven(symbol, position.ticket, entry_price)
                            else:
                                print(f"❌ Failed to close half of position: {close_result.comment}")
 
def del_completed():
    if levels:
        for (symbol,timeframe) in list(levels.keys()):  # Use list to avoid runtime modification issues
            L = levels[(symbol,timeframe)]
            direction = L.get("direction")
            entry_time = L["entry_time"] 
            sl = L["sl"]
            sl1 = L["sl1"]
            tp2 = L["tp2"]
            if not direction:
                continue

            rates = mt5.copy_rates_range(symbol, timeframe, entry_time, datetime.now())
            if rates is None or len(rates) == 0:
                continue
            recent_candles = pd.DataFrame(rates)
            recent_candles['time'] = pd.to_datetime(recent_candles['time'], unit='s')
            crossed_tp2 = False
            crossed_sl1 = False
            crossed_sl =  False
            if direction == "BUY":
                # For BUY positions: TP when price goes up, SL when price goes down
                crossed_tp2 = (recent_candles['high'] >= tp2).any()
                crossed_sl1 = (recent_candles['low'] <= sl1).any()
                crossed_sl = (recent_candles['low'] <= sl).any()
                
            elif direction == "SELL":
                # For SELL positions: TP when price goes down, SL when price goes up
                crossed_tp2 = (recent_candles['low'] <= tp2).any()
                crossed_sl1 = (recent_candles['high'] >= sl1).any()
                crossed_sl = (recent_candles['high'] >= sl).any()

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

            # Check TP2
            if (direction == "BUY" and crossed_tp2) or (direction == "SELL" and crossed_tp2):
                # Hit TP2 - delete channel and levels
                if (symbol, timeframe) in active_channels:
                    plot_filename = os.path.join(PLOTS_FOLDER, f"{symbol}_{timeframe_to_str(timeframe)}_channel.png")
                    send_telegram_image(plot_filename, f"✅ {symbol} {direction} hit Deriv TP2 on {timeframe_to_str(timeframe)}")
                    del active_channels[(symbol,timeframe)]
                if (symbol, timeframe) in levels:
                    del levels[(symbol,timeframe)]
                print(f"✅ {symbol} {direction} hit TP2 - channel removed.")  
 
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
        if hasattr(trade, 'type'):  # Position
            trade_direction = "BUY" if trade.type == mt5.ORDER_TYPE_BUY else "SELL"
        else:  # Order
            if trade.type in [mt5.ORDER_TYPE_BUY_LIMIT, mt5.ORDER_TYPE_BUY_STOP]:
                trade_direction = "BUY"
            elif trade.type in [mt5.ORDER_TYPE_SELL_LIMIT, mt5.ORDER_TYPE_SELL_STOP]:
                trade_direction = "SELL"
            else:
                continue  # Skip other order types
        
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
                                half = round(pos.volume / 2, t)
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
                                if result.retcode == mt5.TRADE_RETCODE_DONE:
                                    print(f"Closed half due to engulfing {symbol}")
                                    send_telegram_message(f"Engulfing detected, closed half and breakeven {symbol} { L['direction']} on {timeframe_to_str(timeframe)}")
                                    modify_trade_to_breakeven(symbol, pos.ticket, pos.price_open)
                            else:
                                modify_trade_to_breakeven(symbol, pos.ticket, pos.price_open)
                        elif count >= 2 :
                            if pos.volume > min_lot:
                                t = decimal_places(get_min_lot_size(symbol))
                                half = round(pos.volume / 2, t)
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
                            half = round(pos.volume / 2, t)
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
                            if result.retcode == mt5.TRADE_RETCODE_DONE:
                                print(f"Closed half due to engulfing {symbol}")
                                send_telegram_message(f"Engulfing detected, closed half and breakeven {symbol} { direction} on {timeframe_to_str(timeframe)}")
                                modify_trade_to_breakeven(symbol, pos.ticket, pos.price_open)
                        else:
                            modify_trade_to_breakeven(symbol, pos.ticket, pos.price_open)
                    elif count >= 2:
                        if pos.volume > min_lot:
                            t = decimal_places(get_min_lot_size(symbol))
                            half = round(pos.volume / 2, t)
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
                            if result.retcode == mt5.TRADE_RETCODE_DONE:
                                print(f"Closed due to too many engulfing {symbol}")
                                send_telegram_message(f"Too many  engulfing, closed trade {symbol} { direction} on {timeframe_to_str(timeframe)}")
                            del old_engulfs[key]
                            if key in active_channels: del active_channels[key]

def check_conflicting_slopes():
    """Check for conflicting slopes across all possible timeframe combinations"""
    # Get all active symbols across all timeframes
    all_symbols = set()
    timeframe_combinations = [
        (mt5.TIMEFRAME_M5, mt5.TIMEFRAME_M15),
        (mt5.TIMEFRAME_M5, mt5.TIMEFRAME_H1), 
        (mt5.TIMEFRAME_M15, mt5.TIMEFRAME_H1)
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
            tp1 = None
            try:
                if pos.comment and pos.comment.strip():
                    tp1 = float(pos.comment)
            except ValueError:
                pass
            return {
                'type': 'position',
                'ticket': pos.ticket,
                'direction': "BUY" if pos.type == 0 else "SELL",
                'sl': pos.sl,
                'tp': pos.tp,
                'tp1': tp1,
                'entry_price': pos.price_open,
            }
    orders = mt5.orders_get(symbol=symbol) or []
    for ord in orders:
        if ord.magic == tf:
            tp1 = None
            try:
                if ord.comment and ord.comment.strip():
                    tp1 = float(ord.comment)
            except ValueError:
                pass
            return {
                'type': 'order',
                'ticket': ord.ticket,
                'direction': "BUY" if ord.type == mt5.ORDER_TYPE_BUY_LIMIT else "SELL",
                'sl': ord.sl,
                'tp': ord.tp,
                'tp1': tp1,
                'entry_price': ord.price_open,
            }
    return None

def check_extend_active_tp_from_higher_tf(symbol, direction, timeframe):
    """Extend TP from higher timeframe for any symbol with multiple active timeframes"""
    current_tf = timeframe
    
    # Define higher timeframes for each current timeframe
    higher_timeframes = {
        mt5.TIMEFRAME_M5: [mt5.TIMEFRAME_M15, mt5.TIMEFRAME_H1],
        mt5.TIMEFRAME_M15: [mt5.TIMEFRAME_H1],
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
        tp1_higher = higher_info['tp1']
        tp2_lower = lower_info['tp']
        tp2_higher = higher_info['tp']
        
        if tp1_lower is None or tp1_higher is None:
            continue
        
        # First, check if TP was already extended (TPs are the same)
        tp_extended = (direction == 'BUY' and tp2_lower == tp2_higher) or \
                     (direction == 'SELL' and tp2_lower == tp2_higher)
        
        if tp_extended:
            # Check if lower timeframe has crossed higher timeframe's TP1
            crossed_higher_tp1 = False
            if direction == 'BUY':
                crossed_higher_tp1 = current_price >= tp1_higher
            else:  # SELL
                crossed_higher_tp1 = current_price <= tp1_higher
            
            if crossed_higher_tp1:
                # Move SL of lower timeframe to higher timeframe's TP1
                request = {
                    "action": mt5.TRADE_ACTION_SLTP if lower_info['type'] == 'position' else mt5.TRADE_ACTION_MODIFY,
                    "sl": tp1_lower,
                    "tp": tp2_lower,  # Keep the extended TP
                    "symbol": symbol,
                    "comment":str(tp1_lower),
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_FOK,
                }
                if lower_info['type'] == 'position':
                    request["position"] = lower_info['ticket']
                else:
                    request["order"] = lower_info['ticket']
                
                result = mt5.order_send(request)
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"🛡️ Moved SL for {symbol} {timeframe_to_str(current_tf)} to TP1: {tp1_higher:.5f}")
                    send_telegram_message(f"🛡️ Moved Deriv SL for {symbol} {timeframe_to_str(current_tf)} to TP1: {tp1_higher:.5f}")
                    modified = True
                else:
                    print(f"❌ Failed to move SL for {symbol}: {result.comment}")
        
        # Original TP extension logic - only execute if TP hasn't been extended yet
        elif not tp_extended:
            crossed_lower_tp1 = (direction == 'BUY' and current_price >= tp1_lower) or \
                               (direction == 'SELL' and current_price <= tp1_lower)
            
            if not crossed_lower_tp1:
                continue
            
            valid_extension = False
            if direction == 'BUY':
                valid_extension = tp2_higher > tp2_lower
            else:  # SELL
                valid_extension = tp2_higher < tp2_lower
            
            if not valid_extension:
                continue
            
            # Modify the lower trade to extend TP
            request = {
                "action": mt5.TRADE_ACTION_SLTP if lower_info['type'] == 'position' else mt5.TRADE_ACTION_MODIFY,
                "sl": lower_info['sl'],
                "tp": tp2_higher,
                "symbol": symbol,
                "comment":str(tp1_lower),
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_FOK,
            }
            if lower_info['type'] == 'position':
                request["position"] = lower_info['ticket']
            else:
                request["order"] = lower_info['ticket']
            
            result = mt5.order_send(request)
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"📈 Extended TP for {symbol} {timeframe_to_str(current_tf)} to {timeframe_to_str(higher_tf)} TP2: {tp2_higher:.5f}")
                send_telegram_message(f"📈 Extended Deriv TP for {symbol} {timeframe_to_str(current_tf)} to {timeframe_to_str(higher_tf)} TP2: {tp2_higher:.5f}")
                modified = True
            else:
                print(f"❌ Failed to extend TP for {symbol}: {result.comment}")
    
    return modified

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
            direction = "BUY" if first_deal.type == mt5.DEAL_TYPE_BUY else "SELL"
            total_profit = sum(d.profit for d in deals)
            if total_profit > 0:
                msg = "hit TP"
            elif total_profit < 0:
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
            direction = "BUY" if first_deal.type == mt5.DEAL_TYPE_BUY else "SELL"
            total_profit = sum(d.profit for d in deals)
            if total_profit > 0:
                msg = "hit TP"
            elif total_profit < 0:
                msg = "hit SL"
            symbol = active_trades[ticket]['symbol']
            timeframe = active_trades[ticket]['timeframe']
            if msg == "hit SL":
                start_cooldown(symbol, timeframe)
            send_telegram_message(f"{symbol} {direction} on {timeframe_to_str(timeframe)}  {msg}" )
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

def check_a_plus_setup(symbol,df, trend_slope):
    """
    Check if channel qualifies for A+ setup based on supply/demand zones
    Returns True if A+ setup is detected, False otherwise
    """
    global supply_demand_zones
    
    # Get or calculate supply/demand zones for this symbol
    if symbol not in supply_demand_zones:
        supply_demand_zones[symbol] = {
            'supply_zones': [],
            'demand_zones': []
        }
        
        # Define higher timeframes for zone detection
        higher_timeframes = [mt5.TIMEFRAME_H4, mt5.TIMEFRAME_H1]
        
        for ht in higher_timeframes:
            try:
                # Fetch historical data from higher timeframe
                historical_data = get_candles(symbol, ht, 200)  # More bars for better zone detection
                if historical_data.empty:
                    print(f"⚠️ No H1/H4 data for {symbol} on {timeframe_to_str(ht)}")
                    continue
                
                # Analyze zones for this higher timeframe
                analyzer = SupplyDemandAnalyzer(historical_data, lookback_period=15, min_touch_points=2)
                ht_supply_zones, ht_demand_zones = analyzer.identify_zones()
                
                # Add zones from this timeframe to the combined list
                supply_demand_zones[symbol]['supply_zones'].extend(ht_supply_zones)
                supply_demand_zones[symbol]['demand_zones'].extend(ht_demand_zones)
                
                print(f"✅ Found {len(ht_supply_zones)} supply zones and {len(ht_demand_zones)} demand zones for {symbol} on {timeframe_to_str(ht)}")
                
            except Exception as e:
                print(f"❌ Error analyzing {symbol} on {timeframe_to_str(ht)}: {str(e)}")
                continue
        
    zones = supply_demand_zones[symbol]
    # For downward channel (negative slope), check demand zones (support)
    if trend_slope < 0:
        for zone in zones['demand_zones']:
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
    Preload supply/demand zones for all active symbols from H1 and H4 timeframes
    """
    global supply_demand_zones
    
    # Get all symbols from your configuration
    all_symbols = set(TIMEFRAME_H1 + TIMEFRAME_M15 + TIMEFRAME_M5)
    
    print("🔄 Preloading H1/H4 supply-demand zones for all symbols...")
    
    for symbol in all_symbols:
        if symbol not in supply_demand_zones:
            # Initialize empty zones for this symbol
            supply_demand_zones[symbol] = {
                'supply_zones': [],
                'demand_zones': []
            }
            
            # Define higher timeframes for zone detection
            higher_timeframes = [mt5.TIMEFRAME_H4, mt5.TIMEFRAME_H1]
            
            for ht in higher_timeframes:
                try:
                    # Fetch historical data from higher timeframe
                    historical_data = get_candles(symbol, ht, 200)
                    if historical_data.empty:
                        continue
                    
                    # Analyze zones for this higher timeframe
                    analyzer = SupplyDemandAnalyzer(historical_data, lookback_period=15, min_touch_points=2)
                    ht_supply_zones, ht_demand_zones = analyzer.identify_zones()
                    
                    # Add zones from this timeframe to the combined list
                    supply_demand_zones[symbol]['supply_zones'].extend(ht_supply_zones)
                    supply_demand_zones[symbol]['demand_zones'].extend(ht_demand_zones)
                    
                except Exception as e:
                    print(f"❌ Error preloading zones for {symbol} on {timeframe_to_str(ht)}: {str(e)}")
                    continue
            print(f"✅ Preloaded zones for {symbol}: {len(supply_demand_zones[symbol]['supply_zones'])} supply, {len(supply_demand_zones[symbol]['demand_zones'])} demand zones")
            zone_last_loaded = datetime.now()
            print(f"📅 Zones preloaded at: {zone_last_loaded.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"🔄 Next zones reload in: {ZONE_RELOAD_DAYS} days")

def should_reload_zones():
    """
    Check if zones should be reloaded based on the 5-day schedule
    """
    global zone_last_loaded
    global supply_demand_zones
    
    if zone_last_loaded is None:
        return True
    
    time_since_last_load = datetime.now() - zone_last_loaded
    days_since_last_load = time_since_last_load.days
    
    if days_since_last_load >= ZONE_RELOAD_DAYS:
        print(f"🔄 Zones reload required: {days_since_last_load} days since last load")
        supply_demand_zones={}
        return True
    
    return False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

clear_plots_folder()



send_telegram_message("Deriv Bot running")
while True:
    try:
        if not is_connected():
            print("🚫 Network or MT5 disconnected.")
            mt5.shutdown()
            check_time = datetime.now() + timedelta(minutes=10)
            print(f"\033[92m Waiting for network reconnection at {check_time.strftime("%H:%M:%S")}...\033[0m")
            time.sleep(600)
            if is_connected():
                print("✅ Network or MT5 reconnected.")
                send_telegram_message("✅ Network or MT5 reconnected.")
            else:
                clear_plots_folder()
                sys.exit("❌ Terminating script due to disconnection.")
        if zone_last_loaded is None or should_reload_zones():
            print("🔄 Initializing supply/demand zones...")
            preload_supply_demand_zones()
        clean_manual_deleted()
        monitor_breakeven_trades()
        monitor_active_trades()
        del_completed()
        update_pending_order_status()
        handle_engulfing_patterns()
        active=[]

        active_symbols = set(TIMEFRAME_H1 + TIMEFRAME_M15 + TIMEFRAME_M5)
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
                                        pending(symbol, direction, candles['close'].iloc[entry_idx], fib_levels['sl'], fib_levels['tp2'],fib_levels['sniper'],timeframe)
                                    elif symbol in H1_pl:
                                        place_trade(symbol, direction, candles['close'].iloc[entry_idx], fib_levels['sl1'], fib_levels['tp2'],timeframe)
                if (symbol, timeframe) in levels :
                    L =levels[(symbol,timeframe)]
                    check_tp1_and_manage_trades(symbol, L["tp1"], timeframe)
                else:
                    positions = mt5.positions_get(symbol=symbol)
                    if positions is not None:
                        for position in positions:
                            if position.magic != timeframe:
                                continue
                            check_tp1_and_manage_trades(symbol, position.comment, timeframe)
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
                                        pending(symbol, direction, candles['close'].iloc[entry_idx], fib_levels['sl'], fib_levels['tp2'],fib_levels['sniper'],timeframe)
                                    elif symbol in M15_pl:
                                        place_trade(symbol, direction, candles['close'].iloc[entry_idx], fib_levels['sl1'], fib_levels['tp2'],timeframe)
                if (symbol, timeframe) in levels :
                    L =levels[(symbol,timeframe)]
                    check_tp1_and_manage_trades(symbol, L["tp1"], timeframe)
                else:
                    positions = mt5.positions_get(symbol=symbol)
                    if positions is not None:
                        for position in positions:
                            if position.magic != timeframe:
                                continue
                            check_tp1_and_manage_trades(symbol, position.comment, timeframe)
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
                            upper = df['upper'].iloc[-1]       # Access upper line from DataFrame
                            lower = df['lower'].iloc[-1]       # Access lower line from DataFrame
                            last_trend = df['trend']     
                            trend_slope = last_trend.iloc[-1] - last_trend.iloc[0]
                            for i in range(len(last)):
                                candle = last.iloc[i]
                                broke_above = candle['high'] > upper
                                broke_below = candle['low'] < lower

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
                            if fib_levels:
                                    direction = "BUY" if candles['close'].iloc[entry_idx] > candles['upper'].iloc[entry_idx] else "SELL"
                                    if symbol in M5_pen :
                                        pending(symbol, direction, candles['close'].iloc[entry_idx], fib_levels['sl'], fib_levels['tp2'],fib_levels['sniper'],timeframe)
                                    elif symbol in M5_pl:
                                        place_trade(symbol, direction, candles['close'].iloc[entry_idx], fib_levels['sl1'], fib_levels['tp2'],timeframe)
                if (symbol, timeframe) in levels :
                    L =levels[(symbol,timeframe)]
                    
                    check_tp1_and_manage_trades(symbol, L["tp1"], timeframe)
                else:
                    positions = mt5.positions_get(symbol=symbol)
                    if positions is not None:
                        for position in positions:
                            if position.magic != timeframe:
                                continue
                            check_tp1_and_manage_trades(symbol, position.comment, timeframe)
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