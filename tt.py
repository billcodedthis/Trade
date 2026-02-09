'''
def place_trade(symbol, direction, entry_price, sl1, tp,timeframe):
    if abs(sl1 - entry_price) >= abs(tp - entry_price):
        print(f"🚫 Trade not placed: SL is greater than TP for {symbol}.")
        return
    positions = mt5.positions_get(symbol=symbol)
    if positions is not None:
        for position in positions:
            if timeframe == position.magic:
                print(f"🚫 Trade not placed: An open position already exists for {symbol}.")
                return
    account_info = mt5.account_info()
    if account_info is None:
        print(f"❌ Failed to get account info ")
        return
    balance = account_info.balance()
    if balance <= 0:
        print(f"❌ Insufficient or zero balance ")
        return
    min_lot = get_min_lot_size(symbol)
    if min_lot is None:
        print(f"❌ Could not get min lot size for {symbol}.")
        return
    volume = lot_size(symbol)
    order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
    t = decimal_places(min_lot)  # For rounding precision
    while volume >= min_lot:
        profit = mt5.order_calc_profit(order_type, symbol, volume, entry_price, sl1)
        if profit is None:
            print(f"❌ Failed to calculate profit for {symbol}.")
            return
        loss = abs(profit)  # Potential loss at SL
        risk_pct = (loss / balance) * 100
        if risk_pct <= 20:
            break  # Acceptable risk
        # Halve and retry
        volume = round(volume / 2, t)
    if volume < min_lot:
        print(f"{symbol},{direction}@{entry_price} sl:{sl1},tp:{tp} failed: Risk still above 20% even at minimum lot size.")
        return
    # Place the trade with adjusted volume
    request = {
        "action": mt5.TRADE_ACTION_DEAL ,
        "symbol": symbol,
        "volume": volume ,
        "type": order_type,
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


'''      

'''# Adjust lot size for risk
    initial_lot = lot_size(symbol)
    adjusted_volume = adjust_lot_for_risk(symbol, direction, sniper, sl, initial_lot)
    if adjusted_volume is None:
        print(f"🚫 Skipping pending trade for {symbol}: Risk exceeds 20% even at min lot.")
        return


# Adjust lot size for risk
    initial_lot = lot_size(symbol)
    adjusted_volume = adjust_lot_for_risk(symbol, direction, entry_price, sl1, initial_lot)
    if adjusted_volume is None:
        print(f"🚫 Skipping market trade for {symbol}: Risk exceeds 20% even at min lot.")
        return


def get_lot_step(symbol):
    info = mt5.symbol_info(symbol)
    if info:
        return info.volume_step
    else:
        return None

def adjust_lot_for_risk(symbol, direction, entry_price, sl, initial_volume):
    """Adjust lot size to ensure risk <= 20% of balance."""
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

    while volume >= min_lot:
        # Calculate hypothetical profit (negative for loss)
        profit = mt5.order_calc_profit(order_type, symbol, volume, entry_price, sl)
        if profit is None:
            print(f"❌ Failed to calculate profit for {symbol}.")
            return None

        loss = abs(profit)  # Loss is positive value
        risk_pct = (loss / balance) * 100

        if risk_pct <= 20:
            # Round down to nearest step
            volume = (volume // lot_step) * lot_step
            if volume < min_lot:
                volume = min_lot
            return volume

        # Halve and round down to step
        volume /= 2
        volume = max((volume // lot_step) * lot_step, min_lot)

    print(f"🚫 Risk still exceeds 20% at minimum lot size for {symbol}. Skipping trade.")
    return None
'''


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

'''
TIMEFRAME_PROFIT_BARS = 48  # Consistent across all (was implicit in your durations)

def update_profit_tracking():
    """Update profit tracking using candle-based bar counts for all active positions"""
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
                # Profitable if close > entry (simple) or low > entry (conservative)
                is_profitable = candle['close'] > entry_price  # Or use candle['low'] > entry_price
            else:  # SELL
                is_profitable = candle['close'] < entry_price  # Or candle['high'] < entry_price
            
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
            print(f"⏰ Position {ticket} has {consecutive_profit_bars} consecutive profitable bars - applying breakeven")
            send_telegram_message(f"⏰ {symbol} trade on {timeframe_to_str(timeframe)} has {consecutive_profit_bars} consecutive profitable bars - applying breakeven")

# Update cleanup_profit_tracking to handle the new structure (no changes needed, as it deletes by ticket)

# In monitor_breakeven_trades() and other places, check profit_tracking[ticket]['breakeven_applied'] as before
'''
