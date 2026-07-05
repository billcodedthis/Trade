>BOT BUGS AND LOGIC PROBLEMS

`To the actual bot:`

* ✅If it enters in 15 minute  and wants to place the same order in a higher timeframe and it has crossed tp1 already just extend the full tp of the 15min setup  to that of the higher timeframe setup

* ✅ If same symbol two different timeframes but identifying different slopes delete lower timeframe

* ✅For every candle above or below the breakout candle whose open is above or below the channel depending on the slope if the candles exceed the number of bars for the channel  delete the Chanel

* ✅If between entry and tp 1 (or tp2 think about it )and an engulfing(maybe filter out some of the engulfing by making sure it comes after 3 consecutive candle that are opposite to the engulfing  candle ) happens ( followed by a candle closing lower or higher depending on the trend )break even  the trade(if in lowest lot size ) else  breakeven and move SL to entry . IF at anytime it  happens again and trade is in lowest lot size and already applied breakeven close the trade

* ✅ If price  hit tp1 delete pending

* ✅Store breakeven applied trades id  so that it keeps checking if that trade is still active .if it leaves to history it checks if sl or tp hit and sends a message to telegram

* ✅It shouldn’t look for channels that already have trades active

* ✅If the bot starts running it should still look for engulfing in  trades that don’t have saved channels from its entry time it should get all candles to the most recent candle and handle the engulfing

*  ✅Add something about supply and demand on higher timeframes  to make sure to be picking good trades and to filter out highly risky ones

*  ✅And if a trade is in a certain direction it shouldn’t look for any trade again that isn’t looking for that direction

* ✅Add something about locking profit after a particular time window
* ✅add a check tp1 after engulfing function that moves sl to secure more profit
* ✅add that if last touch is found within the first 10 candles of a channel the channel should be deleted(for safety reasons)
* ✅Fix the volatility 75 closing half issue
* 💭Fix the  Not halfing profit  when engulfing is detected before tp1 problem --⚡since you've 
fixed the bot's problem of closing engulfing's in loss profits would be secured before tp1 is reached and it will be okay if the bot doesn't half profit again
* ✅check why engulfing are being closed when in loss
* ✅the candle immediately before the entry_candle_idx should notbe an opposite type
* ✅even if slippage happened let trade be recorded as hit breakeven
* ✅Add something  about using account balance to weigh whether to enter trades and the lot size 
* ( add monthly drawdowns,weekly drawdowns and other account-focused risk management scheme  if deemed necessary ) 
* Add M30 trades with supply/demand zones on H1 and M15 trades should have their supply/demad zones on M30 in visuals.py and test.py
* remove all code which is focusing on features of the swing candle ( it its wick is longer than the candle between it and breakout_idx or the candle formed after it )
* the swing point should be at a turning point (it should show rejection or the candles immediately  before and after it should show rejection(pin bars preferrably) )
* fix problem where if symbol  present in sell and buy but diferent type of orders it enters pending because thats checked first

`To the analysis bot:`
* ✅ even if slippage happened let trade be recorded as hit breakeven
* Check if placed trades would have been better at pending
*  Add net pips too


`lessons from John to be implemented:`

* check if swing point is an order block as filter
before a pending order is opened, make sure there is a liquidity sweep before the the swing point(order block) is taken out,after that the candle stick confirmation on a lower timeframe .


