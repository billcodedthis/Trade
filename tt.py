# Adjust lot size for risk
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