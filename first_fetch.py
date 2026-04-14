import ccxt
import pandas as pd

# Fetch data
exchange = ccxt.binance()
ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1d', limit=500)
df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df['date'] = pd.to_datetime(df['timestamp'], unit='ms')

# Indicators
df['MA7']  = df['close'].rolling(7).mean()
df['MA21'] = df['close'].rolling(21).mean()
df['MA50'] = df['close'].rolling(50).mean()
delta = df['close'].diff()
gain = delta.where(delta > 0, 0).rolling(14).mean()
loss = -delta.where(delta < 0, 0).rolling(14).mean()
df['RSI'] = 100 - (100 / (1 + gain / loss))
exp12 = df['close'].ewm(span=12).mean()
exp26 = df['close'].ewm(span=26).mean()
df['MACD'] = exp12 - exp26
df['MACD_signal'] = df['MACD'].ewm(span=9).mean()

# ATR volatility
df['TR'] = pd.concat([
    df['high'] - df['low'],
    (df['high'] - df['close'].shift()).abs(),
    (df['low']  - df['close'].shift()).abs()
], axis=1).max(axis=1)
df['ATR']     = df['TR'].rolling(14).mean()
df['ATR_pct'] = df['ATR'] / df['close'] * 100

# Signals
df['signal'] = ''
for i in range(1, len(df)):
    ma_buy      = df['MA7'].iloc[i] > df['MA21'].iloc[i] and df['MA7'].iloc[i-1] <= df['MA21'].iloc[i-1]
    ma_sell     = df['MA7'].iloc[i] < df['MA21'].iloc[i] and df['MA7'].iloc[i-1] >= df['MA21'].iloc[i-1]
    rsi_ok_buy  = df['RSI'].iloc[i] < 60
    rsi_ok_sell = df['RSI'].iloc[i] > 30
    macd_buy    = df['MACD'].iloc[i] > df['MACD_signal'].iloc[i]
    macd_sell   = df['MACD'].iloc[i] < df['MACD_signal'].iloc[i]
    if ma_buy and rsi_ok_buy and macd_buy:
        df.loc[df.index[i], 'signal'] = 'BUY'
    elif ma_sell and rsi_ok_sell and macd_sell:
        df.loc[df.index[i], 'signal'] = 'SELL'

# Backtest Engine
cash = 10000
btc = 0
buy_price = 0
trades = []

for i, row in df.iterrows():

    # Take profit at +8%
    if btc > 0 and row['close'] > buy_price * 1.08:
        cash = btc * row['close']
        trades.append({'date': row['date'], 'type': 'TAKE PROFIT', 'price': row['close'], 'portfolio': cash})
        btc = 0
        buy_price = 0
        continue

    # Stop loss at -5%
    if btc > 0 and row['close'] < buy_price * 0.95:
        cash = btc * row['close']
        trades.append({'date': row['date'], 'type': 'STOP LOSS', 'price': row['close'], 'portfolio': cash})
        btc = 0
        buy_price = 0
        continue

    # Buy conditions
    ma21_rising    = i >= 3 and df['MA21'].iloc[i] > df['MA21'].iloc[i-3]
    above_ma50     = row['close'] > df['MA50'].iloc[i] * 1.02
    low_volatility = df['ATR_pct'].iloc[i] < 4
    macd_positive  = df['MACD'].iloc[i] > 0

    if row['signal'] == 'BUY' and cash > 0 and btc == 0 and ma21_rising and above_ma50 and low_volatility and macd_positive:
        btc = cash / row['close']
        buy_price = row['close']
        cash = 0
        trades.append({'date': row['date'], 'type': 'BUY', 'price': buy_price, 'portfolio': btc * buy_price})

    # Sell signal
    elif row['signal'] == 'SELL' and btc > 0:
        cash = btc * row['close']
        trades.append({'date': row['date'], 'type': 'SELL', 'price': row['close'], 'portfolio': cash})
        btc = 0
        buy_price = 0

# Final value
final_value = cash if btc == 0 else btc * df['close'].iloc[-1]

# Results
print("\n📊 BACKTEST RESULTS")
print("=" * 55)
print(f"Starting Capital  : $10,000")
print(f"Final Value       : ${final_value:,.2f}")
print(f"Total Profit/Loss : ${final_value - 10000:,.2f}")
print(f"Return            : {((final_value - 10000) / 10000) * 100:.2f}%")
print(f"Total Trades      : {len(trades)}")

print("\n📋 TRADE HISTORY")
print("=" * 55)
for t in trades:
    emoji = "🟢" if t['type'] == 'BUY' else "🔴" if t['type'] == 'SELL' else "💰" if t['type'] == 'TAKE PROFIT' else "⛔"
    print(f"{emoji} {t['type']:<12} | {t['date'].strftime('%Y-%m-%d')} | Price: ${t['price']:,.2f} | Portfolio: ${t['portfolio']:,.2f}")

# Buy and hold comparison
buy_hold = (df['close'].iloc[-1] / df['close'].iloc[0]) * 10000
print(f"\n📈 Buy & Hold Comparison")
print("=" * 55)
print(f"If you just bought and held : ${buy_hold:,.2f}")
print(f"Our bot made                : ${final_value:,.2f}")
if final_value > buy_hold:
    print("✅ Bot BEAT buy and hold!")
else:
    print("❌ Bot UNDERPERFORMED buy and hold — strategy needs improvement")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# Create figure with 3 subplots
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
fig.suptitle('BTC/USDT Trading Bot Performance', fontsize=16, fontweight='bold')

# Plot 1 — Price + Moving Averages + Trade signals
ax1.plot(df['date'], df['close'], label='BTC Price', color='white', linewidth=1, alpha=0.8)
ax1.plot(df['date'], df['MA7'],   label='MA7',       color='cyan',  linewidth=1)
ax1.plot(df['date'], df['MA21'],  label='MA21',      color='orange',linewidth=1)
ax1.plot(df['date'], df['MA50'],  label='MA50',      color='red',   linewidth=1)

# Plot buy/sell points
for t in trades:
    if t['type'] == 'BUY':
        ax1.scatter(t['date'], t['price'], color='lime',   marker='^', s=150, zorder=5)
    elif t['type'] == 'SELL':
        ax1.scatter(t['date'], t['price'], color='red',    marker='v', s=150, zorder=5)
    elif t['type'] == 'TAKE PROFIT':
        ax1.scatter(t['date'], t['price'], color='gold',   marker='v', s=150, zorder=5)
    elif t['type'] == 'STOP LOSS':
        ax1.scatter(t['date'], t['price'], color='orange', marker='v', s=150, zorder=5)

ax1.set_facecolor('#1a1a2e')
ax1.set_ylabel('Price (USD)', color='white')
ax1.tick_params(colors='white')
ax1.legend(loc='upper left', fontsize=8)
ax1.grid(True, alpha=0.2)

# Plot 2 — RSI
ax2.plot(df['date'], df['RSI'], color='purple', linewidth=1)
ax2.axhline(y=70, color='red',   linestyle='--', alpha=0.7, label='Overbought 70')
ax2.axhline(y=30, color='green', linestyle='--', alpha=0.7, label='Oversold 30')
ax2.axhline(y=60, color='yellow',linestyle='--', alpha=0.5, label='Our threshold 60')
ax2.fill_between(df['date'], df['RSI'], 70, where=(df['RSI'] >= 70), color='red',   alpha=0.3)
ax2.fill_between(df['date'], df['RSI'], 30, where=(df['RSI'] <= 30), color='green', alpha=0.3)
ax2.set_facecolor('#1a1a2e')
ax2.set_ylabel('RSI', color='white')
ax2.tick_params(colors='white')
ax2.legend(loc='upper left', fontsize=8)
ax2.grid(True, alpha=0.2)
ax2.set_ylim(0, 100)

# Plot 3 — MACD
ax3.plot(df['date'], df['MACD'],        color='cyan',   linewidth=1, label='MACD')
ax3.plot(df['date'], df['MACD_signal'], color='orange', linewidth=1, label='Signal')
ax3.bar(df['date'], df['MACD'] - df['MACD_signal'],
        color=['lime' if x >= 0 else 'red' for x in df['MACD'] - df['MACD_signal']],
        alpha=0.5, label='Histogram')
ax3.axhline(y=0, color='white', linestyle='-', alpha=0.3)
ax3.set_facecolor('#1a1a2e')
ax3.set_ylabel('MACD', color='white')
ax3.tick_params(colors='white')
ax3.legend(loc='upper left', fontsize=8)
ax3.grid(True, alpha=0.2)

# Legend for trade markers
buy_patch   = mpatches.Patch(color='lime',   label='BUY')
sell_patch  = mpatches.Patch(color='red',    label='SELL')
tp_patch    = mpatches.Patch(color='gold',   label='TAKE PROFIT')
sl_patch    = mpatches.Patch(color='orange', label='STOP LOSS')
ax1.legend(handles=[buy_patch, sell_patch, tp_patch, sl_patch,
           *ax1.lines], loc='upper left', fontsize=7)

# Styling
fig.patch.set_facecolor('#0d0d1a')
for ax in [ax1, ax2, ax3]:
    ax.spines['bottom'].set_color('gray')
    ax.spines['top'].set_color('gray')
    ax.spines['left'].set_color('gray')
    ax.spines['right'].set_color('gray')

plt.tight_layout()
plt.savefig('trading_chart.png', dpi=150, bbox_inches='tight')
plt.show()
print("\n✅ Chart saved as trading_chart.png")