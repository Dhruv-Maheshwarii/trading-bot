import streamlit as st
import ccxt
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import time

# Page config
st.set_page_config(
    page_title="AlgoTrade Dashboard",
    page_icon="🤖",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main { background-color: #0d0d1a; color: white; }
    .metric-card {
        background: #1a1a2e;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        border: 1px solid #333;
    }
    .profit { color: #00ff88; }
    .loss   { color: #ff4444; }
</style>
""", unsafe_allow_html=True)

# Header
st.title("🤖 AlgoTrade — BTC/USDT Trading Bot")
st.caption("Automated trading using MA + RSI + MACD + ATR strategy")

# Sidebar controls
st.sidebar.title("⚙️ Bot Settings")
limit      = st.sidebar.slider("Days of data",        100, 500, 500)
rsi_thresh = st.sidebar.slider("RSI Buy Threshold",    40,  70,  60)
tp_pct     = st.sidebar.slider("Take Profit %",         3,  20,   8) / 100
sl_pct     = st.sidebar.slider("Stop Loss %",           2,  15,   5) / 100
atr_thresh = st.sidebar.slider("Max ATR Volatility %",  1,  10,   4)
coin       = st.sidebar.selectbox("Coin", ["BTC/USDT", "ETH/USDT"])

run_btn = st.sidebar.button("🚀 Run Backtest", use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.markdown("**📊 Strategy Rules**")
st.sidebar.markdown("- MA7 crosses above MA21")
st.sidebar.markdown("- RSI below threshold")
st.sidebar.markdown("- MACD positive & above signal")
st.sidebar.markdown("- Price 2% above MA50")
st.sidebar.markdown("- ATR below volatility limit")

# Main logic
@st.cache_data(ttl=300)
def fetch_and_run(coin, limit, rsi_thresh, tp_pct, sl_pct, atr_thresh):

    # Fetch data
    exchange = ccxt.kucoin()
    ohlcv = exchange.fetch_ohlcv(coin, '1d', limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp','open','high','low','close','volume'])
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')

    # Indicators
    df['MA7']  = df['close'].rolling(7).mean()
    df['MA21'] = df['close'].rolling(21).mean()
    df['MA50'] = df['close'].rolling(50).mean()
    delta = df['close'].diff()
    gain  = delta.where(delta > 0, 0).rolling(14).mean()
    loss  = -delta.where(delta < 0, 0).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + gain / loss))
    exp12 = df['close'].ewm(span=12).mean()
    exp26 = df['close'].ewm(span=26).mean()
    df['MACD']        = exp12 - exp26
    df['MACD_signal'] = df['MACD'].ewm(span=9).mean()
    df['TR']    = pd.concat([
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
        rsi_ok_buy  = df['RSI'].iloc[i] < rsi_thresh
        rsi_ok_sell = df['RSI'].iloc[i] > 30
        macd_buy    = df['MACD'].iloc[i] > df['MACD_signal'].iloc[i]
        macd_sell   = df['MACD'].iloc[i] < df['MACD_signal'].iloc[i]
        if ma_buy and rsi_ok_buy and macd_buy:
            df.loc[df.index[i], 'signal'] = 'BUY'
        elif ma_sell and rsi_ok_sell and macd_sell:
            df.loc[df.index[i], 'signal'] = 'SELL'

    # Backtest
    cash      = 10000
    btc       = 0
    buy_price = 0
    trades    = []

    for i, row in df.iterrows():
        if btc > 0 and row['close'] > buy_price * (1 + tp_pct):
            cash = btc * row['close']
            trades.append({'date': row['date'], 'type': 'TAKE PROFIT', 'price': row['close'], 'portfolio': cash})
            btc = 0; buy_price = 0
            continue
        if btc > 0 and row['close'] < buy_price * (1 - sl_pct):
            cash = btc * row['close']
            trades.append({'date': row['date'], 'type': 'STOP LOSS', 'price': row['close'], 'portfolio': cash})
            btc = 0; buy_price = 0
            continue
        ma21_rising    = i >= 3 and df['MA21'].iloc[i] > df['MA21'].iloc[i-3]
        above_ma50     = row['close'] > df['MA50'].iloc[i] * 1.02
        low_volatility = df['ATR_pct'].iloc[i] < atr_thresh
        macd_positive  = df['MACD'].iloc[i] > 0
        if row['signal'] == 'BUY' and cash > 0 and btc == 0 and ma21_rising and above_ma50 and low_volatility and macd_positive:
            btc = cash / row['close']
            buy_price = row['close']
            cash = 0
            trades.append({'date': row['date'], 'type': 'BUY', 'price': buy_price, 'portfolio': btc * buy_price})
        elif row['signal'] == 'SELL' and btc > 0:
            cash = btc * row['close']
            trades.append({'date': row['date'], 'type': 'SELL', 'price': row['close'], 'portfolio': cash})
            btc = 0; buy_price = 0

    final_value = cash if btc == 0 else btc * df['close'].iloc[-1]
    buy_hold    = (df['close'].iloc[-1] / df['close'].iloc[0]) * 10000
    return df, trades, final_value, buy_hold

# Run on button or first load
if run_btn or True:
    with st.spinner("Fetching live data and running backtest..."):
        df, trades, final_value, buy_hold = fetch_and_run(
            coin, limit, rsi_thresh, tp_pct, sl_pct, atr_thresh
        )

    # ── Metrics Row ──
    col1, col2, col3, col4, col5 = st.columns(5)
    pnl     = final_value - 10000
    pnl_pct = (pnl / 10000) * 100

    col1.metric("💰 Final Value",      f"${final_value:,.2f}")
    col2.metric("📈 Profit / Loss",    f"${pnl:,.2f}",        f"{pnl_pct:.2f}%")
    col3.metric("🔄 Total Trades",     len(trades))
    col4.metric("📊 Buy & Hold",       f"${buy_hold:,.2f}")
    col5.metric("🏆 Beat Market By",   f"${final_value - buy_hold:,.2f}")

    st.markdown("---")

    # ── Chart ──
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 9), sharex=True)
    fig.suptitle(f'{coin} Trading Bot Performance', fontsize=14, fontweight='bold', color='white')

    ax1.plot(df['date'], df['close'], color='white',  linewidth=1,   alpha=0.8, label='Price')
    ax1.plot(df['date'], df['MA7'],   color='cyan',   linewidth=1,   label='MA7')
    ax1.plot(df['date'], df['MA21'],  color='orange', linewidth=1,   label='MA21')
    ax1.plot(df['date'], df['MA50'],  color='red',    linewidth=1,   label='MA50')

    for t in trades:
        if t['type'] == 'BUY':
            ax1.scatter(t['date'], t['price'], color='lime',   marker='^', s=150, zorder=5)
        elif t['type'] == 'SELL':
            ax1.scatter(t['date'], t['price'], color='red',    marker='v', s=150, zorder=5)
        elif t['type'] == 'TAKE PROFIT':
            ax1.scatter(t['date'], t['price'], color='gold',   marker='v', s=150, zorder=5)
        elif t['type'] == 'STOP LOSS':
            ax1.scatter(t['date'], t['price'], color='orange', marker='v', s=150, zorder=5)

    ax2.plot(df['date'], df['RSI'], color='purple', linewidth=1)
    ax2.axhline(y=70,         color='red',    linestyle='--', alpha=0.7)
    ax2.axhline(y=30,         color='green',  linestyle='--', alpha=0.7)
    ax2.axhline(y=rsi_thresh, color='yellow', linestyle='--', alpha=0.5)
    ax2.fill_between(df['date'], df['RSI'], 70, where=(df['RSI'] >= 70), color='red',   alpha=0.3)
    ax2.fill_between(df['date'], df['RSI'], 30, where=(df['RSI'] <= 30), color='green', alpha=0.3)
    ax2.set_ylim(0, 100)

    ax3.plot(df['date'], df['MACD'],        color='cyan',   linewidth=1)
    ax3.plot(df['date'], df['MACD_signal'], color='orange', linewidth=1)
    ax3.bar(df['date'], df['MACD'] - df['MACD_signal'],
            color=['lime' if x >= 0 else 'red' for x in df['MACD'] - df['MACD_signal']],
            alpha=0.5)
    ax3.axhline(y=0, color='white', linestyle='-', alpha=0.3)

    for ax in [ax1, ax2, ax3]:
        ax.set_facecolor('#1a1a2e')
        ax.tick_params(colors='white')
        ax.grid(True, alpha=0.2)
        for spine in ax.spines.values():
            spine.set_color('gray')

    ax1.set_ylabel('Price (USD)', color='white')
    ax2.set_ylabel('RSI',         color='white')
    ax3.set_ylabel('MACD',        color='white')
    ax1.legend(loc='upper left', fontsize=7)
    fig.patch.set_facecolor('#0d0d1a')
    plt.tight_layout()
    st.pyplot(fig)

    st.markdown("---")

    # ── Trade History Table ──
    st.subheader("📋 Trade History")
    if trades:
        trade_df = pd.DataFrame(trades)
        trade_df['date']      = trade_df['date'].dt.strftime('%Y-%m-%d')
        trade_df['price']     = trade_df['price'].apply(lambda x: f"${x:,.2f}")
        trade_df['portfolio'] = trade_df['portfolio'].apply(lambda x: f"${x:,.2f}")

        def color_type(val):
            colors = {
                'BUY':         'background-color: #1a4a1a; color: lime',
                'SELL':        'background-color: #4a1a1a; color: red',
                'TAKE PROFIT': 'background-color: #4a4a1a; color: gold',
                'STOP LOSS':   'background-color: #4a2a1a; color: orange'
            }
            return colors.get(val, '')

        st.dataframe(
            trade_df[['date','type','price','portfolio']].style.map(color_type, subset=['type']),
            use_container_width=True
        )
    else:
        st.info("No trades found with current settings")

    # ── Current Market Status ──
    st.markdown("---")
    st.subheader("📡 Current Market Status")

    latest = df.iloc[-1]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Current Price", f"${latest['close']:,.2f}")
    c2.metric("RSI",           f"{latest['RSI']:.1f}")
    c3.metric("MACD",          f"{latest['MACD']:.1f}")
    c4.metric("ATR %",         f"{latest['ATR_pct']:.2f}%")

    # Signal status
    if latest['RSI'] < rsi_thresh and latest['MACD'] > 0:
        st.success("🟢 Market conditions look FAVORABLE for buying")
    elif latest['RSI'] > 70:
        st.warning("🔴 Market OVERBOUGHT — bot would not buy here")
    else:
        st.info("⚪ Market NEUTRAL — waiting for signal")