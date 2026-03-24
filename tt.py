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


import MetaTrader5 as mt5

MT5_PATH = "C:\\Program Files\\MetaTrader 5 EXNESS\\terminal64.exe"
if not mt5.initialize(path=MT5_PATH):
    print("❌ Failed to connect to MetaTrader 5", mt5.last_error())
    quit()
else:
    print("✅ Successfully connected to MT5!")


symbol = "BTCUSDm"  # Change to your desired symbol
TRADE_TYPE = "BUY"   

def get_lot_step(symbol):
    info = mt5.symbol_info(symbol)
    if info:
        return info.volume_step
    else:
        return None

def get_min_lot_size(symbol):
    info = mt5.symbol_info(symbol)
    if info:
        return info.volume_min
    else:
        return None

def lot_size(symbol):
    lot = 4 * get_min_lot_size(symbol)
    return lot


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


def place_buy_order():
    # Get current market price
    symbol_info = mt5.symbol_info_tick(symbol)
    if symbol_info is None:
        print(f"❌ Failed to retrieve price data for {symbol}")
        mt5.shutdown()
        quit()

    current_price = symbol_info.ask if TRADE_TYPE == "BUY" else symbol_info.bid

    # Define Stop Loss (SL) and Take Profit (TP) levels
    SL_PIPS = 23000 # Adjust SL in pips
    TP_PIPS = 300000  # Adjust TP in pips

    point = mt5.symbol_info(symbol).point
    sl = current_price - (SL_PIPS * point) if TRADE_TYPE == "BUY" else current_price + (SL_PIPS * point)
    tp = current_price + (TP_PIPS * point) if TRADE_TYPE == "BUY" else current_price - (TP_PIPS * point)
    
    initial_lot = lot_size(symbol)
    adjusted_volume = adjust_lot_for_risk(symbol, TRADE_TYPE, current_price, sl, initial_lot)
    if adjusted_volume is None:
        print(f"🚫 Skipping market trade for {symbol}: Risk exceeds 2-5% even at min lot.")
        return


    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": adjusted_volume,
        "type": mt5.ORDER_TYPE_BUY ,
        "price": current_price,
        "sl": sl,
        "tp": tp,
        "deviation": 10,
        "magic": 123456,
        "comment": "Placing market order",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,  # Automatically detected filling mode
    }

    # Send trade request
    order_result = mt5.order_send(request)

    # Check if order was placed successfully
    if order_result.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"✅ Trade placed: {TRADE_TYPE} {symbol} @ {current_price}")
        print(f"🎯 SL: {sl}, TP: {tp}")
    else:
        print(f"❌ Trade failed: {order_result.comment}")


place_buy_order()

t=2
positions = mt5.positions_get(symbol=symbol)
for pos in positions:
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
        print(half)

        