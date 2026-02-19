import shutil
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import MetaTrader5 as mt5
import os
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import MetaTrader5 as mt5
import os
from pathlib import Path
from datetime import datetime
from matplotlib.patches import Rectangle

DOWNLOADS_FOLDER = str(Path.home() / "OneDrive - University of Ghana")
PLOTS_FOLDER = os.path.join(DOWNLOADS_FOLDER, "MT5_SupplyDemand_Zones")
        

if not os.path.exists(PLOTS_FOLDER):
    os.makedirs(PLOTS_FOLDER)
class SupplyDemandAnalyzer:
    def __init__(self, data, lookback_period=20, min_touch_points=2):
        """
        Initialize the analyzer
        
        Parameters:
        - data: DataFrame with OHLC data
        - lookback_period: Period to look for swing highs/lows
        - min_touch_points: Minimum touches to validate a zone
        """
        self.data = data.copy()
        self.lookback = lookback_period
        self.min_touches = min_touch_points
        
    def find_swing_points(self):
        """Identify swing highs and lows"""
        data = self.data
        
        # Initialize columns
        data['swing_high'] = np.nan
        data['swing_low'] = np.nan
        data['is_swing_high'] = False
        data['is_swing_low'] = False
        
        for i in range(self.lookback, len(data) - self.lookback):
            # Check for swing high
            if (data['high'].iloc[i] == data['high'].iloc[i-self.lookback:i+self.lookback+1].max() and
                data['high'].iloc[i] > data['high'].iloc[i-1] and
                data['high'].iloc[i] > data['high'].iloc[i+1]):
                data.loc[data.index[i], 'swing_high'] = data['high'].iloc[i]
                data.loc[data.index[i], 'is_swing_high'] = True
            
            # Check for swing low
            if (data['low'].iloc[i] == data['low'].iloc[i-self.lookback:i+self.lookback+1].min() and
                data['low'].iloc[i] < data['low'].iloc[i-1] and
                data['low'].iloc[i] < data['low'].iloc[i+1]):
                data.loc[data.index[i], 'swing_low'] = data['low'].iloc[i]
                data.loc[data.index[i], 'is_swing_low'] = True
        
        return data
    
    def identify_zones(self):
        """Identify supply and demand zones"""
        data = self.find_swing_points()
        
        supply_zones = []
        demand_zones = []
        
        swing_highs = data[data['is_swing_high']].copy()
        swing_lows = data[data['is_swing_low']].copy()
        
        # Find supply zones (resistance)
        for i in range(len(swing_highs)):
            current_high = swing_highs.iloc[i]
            zone_price = current_high['high']
            
            # Count touches to this level
            touches = self.count_touches(data, zone_price, zone_type='supply')
            
            if touches >= self.min_touches and touches <= 20:
                # Check if supply zone is broken (5 consecutive candles close above without touching)
                is_broken = self.is_zone_broken(data, zone_price, zone_type='supply')
                
                supply_zones.append({
                    'price': zone_price,
                    'date': current_high.name,
                    'touches': touches,
                    'strength': touches,
                    'is_broken': is_broken
                })
        
        # Find demand zones (support)
        for i in range(len(swing_lows)):
            current_low = swing_lows.iloc[i]
            zone_price = current_low['low']
            
            # Count touches to this level
            touches = self.count_touches(data, zone_price, zone_type='demand')
            
            if touches >= self.min_touches and touches <= 20:
                # Check if demand zone is broken (5 consecutive candles close below without touching)
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
        """
        Check if a zone has been broken by consecutive candles crossing without touching back
        
        Parameters:
        - consecutive_candles: Number of consecutive candles required to confirm break
        - tolerance: Price tolerance for considering a touch
        """
        price_tolerance = zone_price * tolerance
        
        # Find the index where the zone was formed
        if zone_type == 'supply':
            zone_formation_idx = data[data['is_swing_high'] & (abs(data['high'] - zone_price) <= price_tolerance)].index
        else:  # demand zone
            zone_formation_idx = data[data['is_swing_low'] & (abs(data['low'] - zone_price) <= price_tolerance)].index
        
        if len(zone_formation_idx) == 0:
            return False
            
        zone_idx = data.index.get_loc(zone_formation_idx[-1])
        
        # Look at data after the zone was formed
        subsequent_data = data.iloc[zone_idx+1:]
        
        if len(subsequent_data) < consecutive_candles:
            return False
        
        consecutive_count = 0
        max_consecutive = 0
        
        for i in range(len(subsequent_data)):
            current_candle = subsequent_data.iloc[i]
            
            if zone_type == 'supply':
                # For supply zone: broken if candle closes above zone
                if current_candle['close'] > zone_price + price_tolerance:
                    consecutive_count += 1
                    max_consecutive = max(max_consecutive, consecutive_count)
                else:
                    # Check if price touched the zone (came back to test it)
                    if (current_candle['high'] >= zone_price - price_tolerance and 
                        current_candle['low'] <= zone_price + price_tolerance):
                        consecutive_count = 0  # Reset if price touches the zone
                    else:
                        consecutive_count = 0  # Reset if candle doesn't cross
            else:  # demand zone
                # For demand zone: broken if candle closes below zone
                if current_candle['close'] < zone_price - price_tolerance:
                    consecutive_count += 1
                    max_consecutive = max(max_consecutive, consecutive_count)
                else:
                    # Check if price touched the zone (came back to test it)
                    if (current_candle['high'] >= zone_price - price_tolerance and 
                        current_candle['low'] <= zone_price + price_tolerance):
                        consecutive_count = 0  # Reset if price touches the zone
                    else:
                        consecutive_count = 0  # Reset if candle doesn't cross
            
            # If we reach the required consecutive candles, zone is broken
            if consecutive_count >= consecutive_candles:
                return True
        
        return False
    
    def count_touches(self, data, zone_price, zone_type, tolerance=0.001):
        """Count how many times price touched the zone"""
        touches = 0
        price_tolerance = zone_price * tolerance
        
        for i in range(len(data)):
            if zone_type == 'supply':
                # For supply zones, count when price approaches from below
                if (abs(data['high'].iloc[i] - zone_price) <= price_tolerance or
                    (data['high'].iloc[i] >= zone_price and 
                     data['low'].iloc[i] <= zone_price)):
                    touches += 1
            else:  # demand zones
                # For demand zones, count when price approaches from above
                if (abs(data['low'].iloc[i] - zone_price) <= price_tolerance or
                    (data['high'].iloc[i] >= zone_price and 
                     data['low'].iloc[i] <= zone_price)):
                    touches += 1
        
        return touches
    
    def plot_candlestick(self, ax, data, width=0.6):
        """Plot candlestick chart"""
        for i, (idx, row) in enumerate(data.iterrows()):
            open_price = row['open']
            high_price = row['high']
            low_price = row['low']
            close_price = row['close']
            
            # Determine color
            if close_price >= open_price:
                color = 'green'
                body_bottom = open_price
                body_top = close_price
            else:
                color = 'red'
                body_bottom = close_price
                body_top = open_price
            
            # Plot high-low line
            ax.plot([i, i], [low_price, high_price], color='black', linewidth=0.8)
            
            # Plot body
            body_height = body_top - body_bottom
            if body_height > 0:
                rect = Rectangle((i - width/2, body_bottom), width, body_height, 
                               facecolor=color, alpha=0.7, edgecolor='black')
                ax.add_patch(rect)
    
    def plot_zones(self, symbol, timeframe_str, recent_bars=100):
            """Plot candlestick chart with supply and demand zones"""
            supply_zones, demand_zones = self.identify_zones()
            
            # Get recent data
            recent_data = self.data.tail(recent_bars)
            
            fig, ax = plt.subplots(figsize=(15, 8))
            
            # Plot candlestick chart
            self.plot_candlestick(ax, recent_data)
            
            # Plot supply zones
            for zone in supply_zones:
                if zone['date'] in recent_data.index:
                    # Determine line style and label based on whether zone is broken
                    if zone['is_broken']:
                        linestyle = ':'  # Dotted line for broken zones
                        label_suffix = " (possible support)"
                        color = 'orange'  # Different color for broken supply zones
                    else:
                        linestyle = '--'  # Dashed line for intact zones
                        label_suffix = ""
                        color = 'red'
                    
                    ax.axhline(y=zone['price'], color=color, linestyle=linestyle, 
                            alpha=0.7, linewidth=2, label='Supply Zone' + label_suffix if zone == supply_zones[0] else "")
                    
                    # Add price label on the right side
                    ax.text(len(recent_data)-1, zone['price'], 
                            f'{zone["price"]:.5f}', 
                            color=color, va='center', ha='right', backgroundcolor='white',
                            fontweight='bold', fontsize=9)
                    
                    # Add zone label on the left side
                    ax.text(0, zone['price'], 
                            f'Supply ({zone["touches"]} touches){label_suffix}', 
                            color=color, va='center', ha='left', backgroundcolor='white',
                            transform=ax.get_yaxis_transform())
            
            # Plot demand zones
            for zone in demand_zones:
                if zone['date'] in recent_data.index:
                    # Determine line style and label based on whether zone is broken
                    if zone['is_broken']:
                        linestyle = ':'  # Dotted line for broken zones
                        label_suffix = " (possible resistance)"
                        color = 'purple'  # Different color for broken demand zones
                    else:
                        linestyle = '--'  # Dashed line for intact zones
                        label_suffix = ""
                        color = 'green'
                    
                    ax.axhline(y=zone['price'], color=color, linestyle=linestyle, 
                            alpha=0.7, linewidth=2, label='Demand Zone' + label_suffix if zone == demand_zones[0] else "")
                    
                    # Add price label on the right side
                    ax.text(len(recent_data)-1, zone['price'], 
                            f'{zone["price"]:.5f}', 
                            color=color, va='center', ha='right', backgroundcolor='white',
                            fontweight='bold', fontsize=9)
                    
                    # Add zone label on the left side
                    ax.text(0, zone['price'], 
                            f'Demand ({zone["touches"]} touches){label_suffix}', 
                            color=color, va='center', ha='left', backgroundcolor='white',
                            transform=ax.get_yaxis_transform())
            
            # Set x-axis labels
            ax.set_xticks(range(0, len(recent_data), max(1, len(recent_data)//10)))
            ax.set_xticklabels([date.strftime('%Y-%m-%d %H:%M') for date in recent_data.index[::max(1, len(recent_data)//10)]])
            
            ax.set_title(f'Supply and Demand Zones - {symbol} ({timeframe_str})')
            ax.set_xlabel('Date')
            ax.set_ylabel('Price')
            ax.legend()
            ax.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            plt.tight_layout()
            
                
            plot_filename = os.path.join(PLOTS_FOLDER, f"{symbol}_{timeframe_str}_supply_demand.png")
            plt.savefig(plot_filename, dpi=150, bbox_inches='tight')
            plt.close()
            
            print(f"✅ Plot saved: {plot_filename}")
            
            return supply_zones, demand_zones

def clear_output_folder():
    """Delete all files and subfolders inside OUTPUT_FOLDER, but keep the folder itself."""
    if os.path.exists(PLOTS_FOLDER):
        for item in os.listdir(PLOTS_FOLDER):
            item_path = os.path.join(PLOTS_FOLDER, item)
            try:
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    os.unlink(item_path)        # delete file or link
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)    # delete folder and everything inside
                print(f"Deleted: {item_path}")
            except Exception as e:
                print(f"Warning: Failed to delete {item_path}: {e}")
        print(f"Output folder cleared: {PLOTS_FOLDER}")
    else:
        os.makedirs(PLOTS_FOLDER, exist_ok=True)
        print(f"Output folder created: {PLOTS_FOLDER}")

def initialize_mt5():
    """Initialize MT5 connection"""
    MT5_PATH = "C:\\Program Files\\MetaTrader 5\\terminal64.exe"
    if not mt5.initialize(path=MT5_PATH):
        print("❌ Failed to connect to MetaTrader 5", mt5.last_error())
        return False
    else:
        print("✅ Successfully connected to MT5!")
        return True

def timeframe_to_str(timeframe):
    """Convert MT5 timeframe constant to human-readable string"""
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

def get_candles(symbol, timeframe, num_bars):
    """Fetch candle data from MT5"""
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, num_bars)
    if rates is None or len(rates) == 0:
        print(f"❌ No data received for {symbol} on timeframe {timeframe}")
        return pd.DataFrame()
    
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    return df

def analyze_symbols():
    """Analyze multiple symbols and timeframes for supply/demand zones"""
    
    # Define symbols and timeframes to analyze (same as test.py)
    FOREX_PAIRS = ["EURUSD.0", "GBPUSD.0", "USDJPY.0", "CHFJPY.0",  "USDCHF.0","EURJPY.0"]
    XAUUSD = "XAUUSD.0"
    BTCUSD="BTCUSD.0"
    MAJORS = [ "EURCHF.0", "CADCHF.0","GBPCAD.0","USDCAD.0"]
    V100 = "Volatility 100 Index.0"
    BnC = ["Boom 900 Index.0","Boom 300 Index.0"]
    Jump = ["Jump 25 Index.0"]
    vol = ["Volatility 50 Index.0","Volatility 25 Index.0","Volatility 10 Index.0"]
    SYNTHETICS = ["Step Index.0"]
    US =["US Tech 100.0","Wall Street 30.0"]
    v=["Volatility 75 Index.0"]
    J=["Jump 75 Index.0"]
    C=["Crash 900 Index.0","Crash 300 Index.0"]
    
    # Combine all symbols
    all_symbols = list(set(FOREX_PAIRS + [XAUUSD, BTCUSD] + MAJORS + [V100] + BnC + C + Jump + J + vol + v  + SYNTHETICS + US))
    
    # Timeframes to analyze
    #timeframes = [mt5.TIMEFRAME_H1, mt5.TIMEFRAME_M15, mt5.TIMEFRAME_M5]
    timeframes = [mt5.TIMEFRAME_M15,mt5.TIMEFRAME_H1]
    
    results = {}
    
    for symbol in all_symbols:
        for timeframe in timeframes:
            try:
                print(f"🔍 Analyzing {symbol} on {timeframe_to_str(timeframe)}...")
                
                # Get candle data (more bars for better zone detection)
                df = get_candles(symbol, timeframe, 200)
                
                if df.empty:
                    print(f"⚠️ No data for {symbol} on {timeframe_to_str(timeframe)}")
                    continue
                
                # Create analyzer and find zones
                analyzer = SupplyDemandAnalyzer(df, lookback_period=15, min_touch_points=2)
                supply_zones, demand_zones = analyzer.plot_zones(symbol, timeframe_to_str(timeframe), recent_bars=100)
                
                # Store results
                key = f"{symbol}_{timeframe_to_str(timeframe)}"
                results[key] = {
                    'supply_zones': supply_zones,
                    'demand_zones': demand_zones,
                    'symbol': symbol,
                    'timeframe': timeframe_to_str(timeframe)
                }
                
                print(f"✅ Found {len(supply_zones)} supply zones and {len(demand_zones)} demand zones for {symbol}")
                
            except Exception as e:
                print(f"❌ Error analyzing {symbol} on {timeframe_to_str(timeframe)}: {str(e)}")
    
    return results

def main():
    """Main function to run supply/demand analysis"""
    
    # Initialize MT5 connection
    if not initialize_mt5():
        return
    
    try:
        clear_output_folder()
        print("🚀 Starting Supply/Demand Analysis...")
        
        # Analyze all symbols
        results = analyze_symbols()
        
        # Print summary
        print("\n" + "="*50)
        print("📊 SUPPLY/DEMAND ANALYSIS SUMMARY")
        print("="*50)
        
        for key, result in results.items():
            print(f"\n{key}:")
            print(f"  Supply Zones: {len(result['supply_zones'])}")
            for zone in result['supply_zones'][:3]:  # Show top 3
                status = " (broken - possible support)" if zone['is_broken'] else ""
                print(f"    - {zone['price']:.5f} ({zone['touches']} touches){status}")
            
            print(f"  Demand Zones: {len(result['demand_zones'])}")
            for zone in result['demand_zones'][:3]:  # Show top 3
                status = " (broken - possible resistance)" if zone['is_broken'] else ""
                print(f"    - {zone['price']:.5f} ({zone['touches']} touches){status}")
        
        print(f"\n✅ Analysis completed! Check the plots folder for charts.")
        
    except Exception as e:
        print(f"❌ Error in main analysis: {str(e)}")
    
    finally:
        # Shutdown MT5 connection
        mt5.shutdown()
        print("🔚 MT5 connection closed.")

# Run the analysis
if __name__ == "__main__":
    main()