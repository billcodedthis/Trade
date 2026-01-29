
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
                

                # Original TP1 logic (half position & move SL to breakeven)
                if (position.type == mt5.ORDER_TYPE_BUY and current_price >= Tp1) or \
                (position.type == mt5.ORDER_TYPE_SELL and current_price <= Tp1):
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
                        half_lot = round(position.volume / 2, 2)
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
                            send_telegram_message(f"TP1 hit. Apply breakeven and close half of deriv {direction}  positions for {symbol} on {timeframe_to_str(timeframe)}  trade.✅")
                            print(f"✅ Closed half of position {position.ticket} for {symbol} at TP1.")
                            modify_trade_to_breakeven(symbol, position.ticket, entry_price)
                        elif close_result.comment == "Invalid volume":
                            send_telegram_message(f"TP1 hit. Apply breakeven and close half of deriv {direction}  positions for {symbol} on {timeframe_to_str(timeframe)}  trade.✅")
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
                

                # Original TP1 logic (half position & move SL to breakeven)
                if timeframe == magic:
                    if (position.type == mt5.ORDER_TYPE_BUY and current_price >= tp1 ) or \
                    (position.type == mt5.ORDER_TYPE_SELL and current_price <= tp1 ):
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
                            half_lot = round(position.volume / 2, 2)
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
                                send_telegram_message(f"TP1 hit. Apply breakeven and close half of deriv {direction}  positions for {symbol} on {timeframe_to_str(timeframe)}  trade.✅")
                                print(f"✅ Closed half of position {position.ticket} for {symbol} at TP1.")
                                modify_trade_to_breakeven(symbol, position.ticket, entry_price)
                            elif close_result.comment == "Invalid volume":
                                send_telegram_message(f"TP1 hit. Apply breakeven and close half of deriv {direction}  positions for {symbol} on {timeframe_to_str(timeframe)}  trade.✅")
                                print(f"{symbol} cannot be halved, but SL has been moved to breakeven.")
                                modify_trade_to_breakeven(symbol, position.ticket, entry_price)
                            else:
                                print(f"❌ Failed to close half of position: {close_result.comment}")
 
'''

'''
def del_completed():
    if levels:
        for (symbol,timeframe) in list(levels.keys()):  # Use list to avoid runtime modification issues
            L = levels[(symbol,timeframe)]
            direction = L.get("direction")
            if not direction:
                continue

            # Get current price
            current_price = mt5.symbol_info_tick(symbol).bid if direction =="SELL" else mt5.symbol_info_tick(symbol).ask
                 # Use current market price

            if timeframe== mt5.TIMEFRAME_M5:
                if symbol in M5_pen :
                    if (direction == "BUY" and current_price <= L["sl"]) or (direction == "SELL" and current_price >= L["sl"]):
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
                    if (direction == "BUY" and current_price <= L["sl1"]) or (direction == "SELL" and current_price >= L["sl1"]):
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
                    if (direction == "BUY" and current_price <= L["sl"]) or (direction == "SELL" and current_price >= L["sl"]):
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
                    if (direction == "BUY" and current_price <= L["sl1"]) or (direction == "SELL" and current_price >= L["sl1"]):
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
                    if (direction == "BUY" and current_price <= L["sl"]) or (direction == "SELL" and current_price >= L["sl"]):
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
                    if (direction == "BUY" and current_price <= L["sl1"]) or (direction == "SELL" and current_price >= L["sl1"]):
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
            if (direction == "BUY" and current_price >= L["tp2"]) or (direction == "SELL" and current_price <= L["tp2"]):
                # Hit TP2 - delete channel and levels
                if (symbol, timeframe) in active_channels:
                    plot_filename = os.path.join(PLOTS_FOLDER, f"{symbol}_{timeframe_to_str(timeframe)}_channel.png")
                    send_telegram_image(plot_filename, f"✅ {symbol} {direction} hit Deriv TP2 on {timeframe_to_str(timeframe)}")
                    del active_channels[(symbol,timeframe)]
                if (symbol, timeframe) in levels:
                    del levels[(symbol,timeframe)]
                print(f"✅ {symbol} {direction} hit TP2 - channel removed.")  
 
'''