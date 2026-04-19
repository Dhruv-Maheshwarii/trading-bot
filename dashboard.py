import streamlit as st
import ccxt, pandas as pd, matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import json, os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(page_title="AlgoTrade", page_icon="", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    font-family: 'Inter', sans-serif !important;
    background: #111318 !important;
    color: #e8eaed !important;
}
[data-testid="stSidebar"] {
    background: #0e0f13 !important;
    border-right: 1px solid #1f2128 !important;
}
[data-testid="stSidebar"] * { font-family: 'Inter', sans-serif !important; }
[data-testid="stSidebar"] > div { margin-top: 0 !important; padding-top: 0 !important; }
[data-testid="stSidebar"] > div > div { margin-top: 0 !important; padding-top: 0 !important; }
[data-testid="stSidebar"] > div > div > div { padding-top: 0 !important; }
[data-testid="stSidebarNav"] { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
#MainMenu, footer, header { visibility: hidden; }
section[data-testid="stSidebar"] > div:first-child { padding: 0 !important; margin-top: 0 !important; }

[data-testid="stSlider"] label p {
    font-size: 11px !important; font-weight: 600 !important;
    color: #94a3b8 !important; letter-spacing: 0.04em !important;
    text-transform: uppercase !important;
    font-family: 'Inter', sans-serif !important;
}
[data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"] {
    background: #00d4aa !important; border-color: #00d4aa !important;
    width: 14px !important; height: 14px !important;
}
[data-testid="stSlider"] [data-baseweb="slider"] > div > div:nth-child(3) {
    background: #00d4aa !important;
}
[data-testid="stSlider"] [data-baseweb="slider"] > div > div:first-child {
    background: #252830 !important; height: 3px !important;
}
[data-testid="stSlider"] div[data-testid="stThumbValue"] {
    font-family: 'Inter', sans-serif !important;
    font-size: 12px !important; font-weight: 700 !important;
    color: #00d4aa !important; background: transparent !important;
}
[data-testid="stSlider"] [data-testid="stTickBarMin"],
[data-testid="stSlider"] [data-testid="stTickBarMax"] {
    color: #64748b !important; font-size: 11px !important;
}
.stSelectbox label p {
    font-size: 11px !important; font-weight: 600 !important;
    color: #94a3b8 !important; text-transform: uppercase !important;
    letter-spacing: 0.04em !important;
}
.stSelectbox [data-baseweb="select"] {
    background: #1a1d24 !important; border: 1px solid #252830 !important;
}
.stSelectbox [data-baseweb="select"] * {
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important; color: #e8eaed !important;
    background: #1a1d24 !important;
}
.stButton button {
    font-family: 'Inter', sans-serif !important;
    font-size: 12px !important; font-weight: 700 !important;
    letter-spacing: 0.06em !important; text-transform: uppercase !important;
    background: #00d4aa !important; color: #0e0f13 !important;
    border: none !important; padding: 10px 0 !important;
    border-radius: 6px !important; transition: all 0.15s !important;
}
.stButton button:hover { background: #00b894 !important; }

.topbar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 24px; height: 52px; background: #0e0f13;
    border-bottom: 1px solid #1f2128;
}
.brand { font-size: 16px; font-weight: 700; color: #fff; letter-spacing: -0.02em; }
.brand span { color: #00d4aa; }
.nav-tags { display: flex; gap: 4px; }
.ntag {
    font-size: 11px; font-weight: 600; color: #94a3b8;
    padding: 4px 10px; border-radius: 4px; border: 1px solid #1f2128;
}
.ntag-active {
    font-size: 11px; font-weight: 700; color: #00d4aa;
    padding: 4px 10px; border-radius: 4px;
    background: rgba(0,212,170,0.08); border: 1px solid rgba(0,212,170,0.25);
}
.live-badge {
    display: flex; align-items: center; gap: 6px;
    font-size: 11px; font-weight: 700; color: #00d4aa;
    padding: 4px 10px; border-radius: 4px;
    background: rgba(0,212,170,0.08); border: 1px solid rgba(0,212,170,0.2);
}
.dot { width: 6px; height: 6px; border-radius: 50%; background: #00d4aa;
    animation: pulse 1.6s ease-in-out infinite; }
@keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.3;transform:scale(0.7)} }
.topbar-right { display: flex; align-items: center; gap: 12px; }
.ts { font-size: 12px; font-weight: 600; color: #94a3b8; font-variant-numeric: tabular-nums; }

.stats-row {
    display: grid; grid-template-columns: repeat(7, 1fr);
    border-bottom: 1px solid #1f2128; background: #0e0f13;
}
.sc { padding: 12px 16px; border-right: 1px solid #1f2128; }
.sc:last-child { border-right: none; }
.sc-label { font-size: 10px; font-weight: 700; color: #64748b;
    text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 5px; }
.sc-val { font-size: 16px; font-weight: 700; color: #ffffff; letter-spacing: -0.01em; }
.sc-sub { font-size: 12px; font-weight: 600; margin-top: 3px; }
.g { color: #00d4aa; } .r { color: #ff6b6b; } .b { color: #60a5fa; } .m { color: #94a3b8; }

.kpi-row {
    display: grid; grid-template-columns: repeat(5,1fr);
    gap: 1px; background: #1f2128; margin: 0;
}
.kpi { background: #111318; padding: 18px 20px; position: relative; overflow: hidden; }
.kpi::after {
    content: ''; position: absolute;
    bottom: 0; left: 0; right: 0; height: 2px; background: #00d4aa;
}
.kpi-label { font-size: 11px; font-weight: 700; color: #64748b;
    text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 8px; }
.kpi-val { font-size: 28px; font-weight: 700; color: #ffffff;
    letter-spacing: -0.02em; line-height: 1; }
.kpi-sub { font-size: 13px; font-weight: 600; margin-top: 6px; }

.sig-card { padding: 18px 16px; border-bottom: 1px solid #1f2128; }
.sig-pill {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 5px 16px; border-radius: 20px;
    font-size: 12px; font-weight: 700; letter-spacing: 0.1em; margin-bottom: 14px;
}
.sp-hold { background: #1a1d24; color: #94a3b8; }
.sp-buy  { background: rgba(0,212,170,0.12); color: #00d4aa; border: 1px solid rgba(0,212,170,0.3); }
.sp-sell { background: rgba(255,107,107,0.12); color: #ff6b6b; border: 1px solid rgba(255,107,107,0.3); }
.price-hero { font-size: 32px; font-weight: 700; color: #ffffff;
    letter-spacing: -0.03em; line-height: 1; margin-bottom: 4px; }
.pair-meta { font-size: 11px; font-weight: 600; color: #64748b;
    text-transform: uppercase; letter-spacing: 0.06em; }

.ind-card { padding: 14px 16px; border-bottom: 1px solid #1f2128; }
.ind-title { font-size: 10px; font-weight: 700; color: #64748b;
    text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 12px; }
.ir { display: flex; justify-content: space-between; align-items: center;
    padding: 6px 0; border-bottom: 1px solid #1a1d24; }
.ir:last-child { border-bottom: none; }
.ik { font-size: 12px; font-weight: 600; color: #cbd5e1; }
.iv { font-size: 13px; font-weight: 700; color: #ffffff; }
.bar-wrap { height: 2px; background: #1f2128; margin-top: 4px; border-radius: 1px; }
.bar-fill { height: 2px; border-radius: 1px; }

.pf-card { padding: 14px 16px; }
.pr { display: flex; justify-content: space-between; align-items: center;
    padding: 6px 0; border-bottom: 1px solid #1a1d24; }
.pr:last-child { border-bottom: none; }
.pk { font-size: 12px; font-weight: 600; color: #cbd5e1; }
.pv { font-size: 13px; font-weight: 700; color: #ffffff; }

.tlog { padding: 14px 20px 18px; background: #0e0f13; border-top: 1px solid #1f2128; }
.tlog-title { font-size: 11px; font-weight: 700; color: #64748b;
    text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 10px; }
.th { display: grid; grid-template-columns: 110px 130px 120px 120px 100px;
    gap: 0; border-bottom: 1px solid #252830; padding-bottom: 8px; margin-bottom: 4px; }
.thc { font-size: 10px; font-weight: 700; color: #4b5563;
    text-transform: uppercase; letter-spacing: 0.1em; padding: 0 8px; }
.tr-row { display: grid; grid-template-columns: 110px 130px 120px 120px 100px;
    gap: 0; padding: 6px 0; border-bottom: 1px solid #1a1d24; }
.tr-row:last-child { border-bottom: none; }
.trc { font-size: 13px; font-weight: 500; padding: 0 8px; color: #94a3b8; }
.trc.bright { color: #ffffff; font-weight: 600; }
.trc.g { color: #00d4aa; font-weight: 700; }
.trc.r { color: #ff6b6b; font-weight: 700; }
.trc.a { color: #34d399; font-weight: 700; }
.trc.m { color: #94a3b8; }

.sb-brand { padding: 18px 16px 16px; border-bottom: 1px solid #1f2128; background: #0e0f13; }
.sb-brand-name { font-size: 16px; font-weight: 700; color: #fff; letter-spacing: -0.01em; }
.sb-brand-name span { color: #00d4aa; }
.sb-brand-sub { font-size: 10px; font-weight: 600; color: #4b5563;
    text-transform: uppercase; letter-spacing: 0.08em; margin-top: 4px; line-height: 1.6; }
.sb-section-hdr { font-size: 10px; font-weight: 700; color: #64748b;
    text-transform: uppercase; letter-spacing: 0.12em; padding: 16px 16px 8px; }
.rule-list { padding: 4px 16px 12px; }
.rl-item { display: flex; align-items: center; gap: 10px;
    padding: 6px 0; border-bottom: 1px solid #1a1d24; }
.rl-item:last-child { border-bottom: none; }
.rl-dot { width: 5px; height: 5px; border-radius: 50%; background: #00d4aa; flex-shrink: 0; }
.rl-text { font-size: 12px; font-weight: 500; color: #cbd5e1; }
.risk-grid { display: grid; grid-template-columns: 1fr 1fr;
    gap: 1px; background: #1f2128; margin: 4px 16px 16px;
    border-radius: 6px; overflow: hidden; }
.rg-cell { background: #151720; padding: 12px 14px; }
.rg-label { font-size: 10px; font-weight: 700; color: #64748b;
    text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 4px; }
.rg-val { font-size: 16px; font-weight: 700; color: #00d4aa; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──
with st.sidebar:
    st.markdown("""
<div class='sb-brand'>
  <div class='sb-brand-name'>Algo<span>Trade</span></div>
  <div class='sb-brand-sub'>Autonomous Trading System<br>Paper Mode · ML Powered</div>
</div>
""", unsafe_allow_html=True)
    st.markdown("<div class='sb-section-hdr'>Configuration</div>", unsafe_allow_html=True)
    coin       = st.selectbox("Pair",                ["BTC/USDT","ETH/USDT"])
    limit      = st.slider("Days of history",         100, 500, 500, step=50)
    rsi_thresh = st.slider("RSI entry threshold",      40,  70,  60, step=5)
    tp_pct     = st.slider("Take profit %",             3,  20,   8, step=1) / 100
    sl_pct     = st.slider("Stop loss %",               2,  15,   5, step=1) / 100
    atr_thresh = st.slider("Max ATR volatility %",      1,  10,   4, step=1)
    st.markdown("<br>", unsafe_allow_html=True)
    st.button("Run Backtest", use_container_width=True)

    st.markdown("<div class='sb-section-hdr'>Active Strategy Rules</div>", unsafe_allow_html=True)
    rules = [
        "MA7 × MA21 crossover",
        "RSI below threshold",
        "MACD positive + signal",
        "Price 2% above MA50",
        "ATR below volatility cap",
        "ML confidence > 55%",
        "MA21 rising 3-day slope",
    ]
    rl = "".join([f"<div class='rl-item'><div class='rl-dot'></div><span class='rl-text'>{r}</span></div>" for r in rules])
    st.markdown(f"<div class='rule-list'>{rl}</div>", unsafe_allow_html=True)

    st.markdown("<div class='sb-section-hdr'>Risk Parameters</div>", unsafe_allow_html=True)
    st.markdown(f"""
<div class='risk-grid'>
  <div class='rg-cell'><div class='rg-label'>Take Profit</div><div class='rg-val'>{int(tp_pct*100)}%</div></div>
  <div class='rg-cell'><div class='rg-label'>Stop Loss</div><div class='rg-val'>{int(sl_pct*100)}%</div></div>
  <div class='rg-cell'><div class='rg-label'>RSI Max</div><div class='rg-val'>{rsi_thresh}</div></div>
  <div class='rg-cell'><div class='rg-label'>ATR Cap</div><div class='rg-val'>{atr_thresh}%</div></div>
</div>
""", unsafe_allow_html=True)

# ── Data ──
@st.cache_data(ttl=300)
def fetch_and_run(coin, limit, rsi_thresh, tp_pct, sl_pct, atr_thresh):
    ex  = ccxt.bybit()
    raw = ex.fetch_ohlcv(coin, '1d', limit=limit)
    df  = pd.DataFrame(raw, columns=['timestamp','open','high','low','close','volume'])
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['MA7']  = df['close'].rolling(7).mean()
    df['MA21'] = df['close'].rolling(21).mean()
    df['MA50'] = df['close'].rolling(50).mean()
    d=df['close'].diff(); g=d.where(d>0,0).rolling(14).mean(); l=-d.where(d<0,0).rolling(14).mean()
    df['RSI']=100-(100/(1+g/l))
    e12=df['close'].ewm(span=12).mean(); e26=df['close'].ewm(span=26).mean()
    df['MACD']=e12-e26; df['MACDs']=df['MACD'].ewm(span=9).mean()
    df['TR']=pd.concat([
        df['high']-df['low'],
        (df['high']-df['close'].shift()).abs(),
        (df['low']-df['close'].shift()).abs()
    ],axis=1).max(axis=1)
    df['ATR']=df['TR'].rolling(14).mean(); df['ATRp']=df['ATR']/df['close']*100
    df['sig']=''
    for i in range(1,len(df)):
        mb=df['MA7'].iloc[i]>df['MA21'].iloc[i] and df['MA7'].iloc[i-1]<=df['MA21'].iloc[i-1]
        ms=df['MA7'].iloc[i]<df['MA21'].iloc[i] and df['MA7'].iloc[i-1]>=df['MA21'].iloc[i-1]
        if mb and df['RSI'].iloc[i]<rsi_thresh and df['MACD'].iloc[i]>df['MACDs'].iloc[i]:
            df.loc[df.index[i],'sig']='BUY'
        elif ms and df['RSI'].iloc[i]>30 and df['MACD'].iloc[i]<df['MACDs'].iloc[i]:
            df.loc[df.index[i],'sig']='SELL'
    cash=10000; btc=0; bp=0; trades=[]
    for i,row in df.iterrows():
        if btc>0 and row['close']>bp*(1+tp_pct):
            cash=btc*row['close']
            trades.append({'date':row['date'],'type':'TAKE PROFIT','price':row['close'],'portfolio':cash,'pnl':cash-10000})
            btc=0; bp=0; continue
        if btc>0 and row['close']<bp*(1-sl_pct):
            cash=btc*row['close']
            trades.append({'date':row['date'],'type':'STOP LOSS','price':row['close'],'portfolio':cash,'pnl':cash-10000})
            btc=0; bp=0; continue
        mr=i>=3 and df['MA21'].iloc[i]>df['MA21'].iloc[i-3]
        am=row['close']>df['MA50'].iloc[i]*1.02
        lv=df['ATRp'].iloc[i]<atr_thresh; mp=df['MACD'].iloc[i]>0
        if row['sig']=='BUY' and cash>0 and btc==0 and mr and am and lv and mp:
            btc=cash/row['close']; bp=row['close']; cash=0
            trades.append({'date':row['date'],'type':'BUY','price':bp,'portfolio':btc*bp,'pnl':0})
        elif row['sig']=='SELL' and btc>0:
            cash=btc*row['close']
            trades.append({'date':row['date'],'type':'SELL','price':row['close'],'portfolio':cash,'pnl':cash-10000})
            btc=0; bp=0
    fv=cash if btc==0 else btc*df['close'].iloc[-1]
    bh=(df['close'].iloc[-1]/df['close'].iloc[0])*10000
    return df,trades,fv,bh

def load_pf():
    if os.path.exists('portfolio.json'):
        with open('portfolio.json') as f: return json.load(f)
    return {'cash':10000,'btc':0,'buy_price':0,'trades':[]}

def fmt(v):
    return (f"+${v:,.0f}" if v>=0 else f"-${abs(v):,.0f}")

def fmtp(v):
    return (f"+{v:.2f}%" if v>=0 else f"{v:.2f}%")

with st.spinner(""):
    df,trades,fv,bh = fetch_and_run(coin,limit,rsi_thresh,tp_pct,sl_pct,atr_thresh)

pf   = load_pf()
lat  = df.iloc[-1]
pnl  = fv-10000; pnlp=(pnl/10000)*100
beat = fv-bh;    bhp=(bh/10000-1)*100
wins = sum(1 for t in trades if t.get('pnl',0)>0)
wr   = int(wins/max(len(trades),1)*100)
rsi  = lat['RSI']; macd=lat['MACD']; atrp=lat['ATRp']
sig  = 'BUY' if (rsi<rsi_thresh and macd>0) else 'SELL' if rsi>70 else 'HOLD'
pbv  = pf.get('cash',10000) if pf.get('btc',0)==0 else pf.get('btc',0)*lat['close']
ppnl = pbv-10000; pbp=pf.get('buy_price',0)
opnl = (lat['close']-pbp)/pbp*100 if pf.get('btc',0)>0 and pbp>0 else 0
now  = datetime.now().strftime('%Y-%m-%d  %H:%M:%S')
chg24= ((lat['close']-df.iloc[-2]['close'])/df.iloc[-2]['close'])*100
vol24= lat['volume']*lat['close']

# ── Topbar ──
st.markdown(f"""
<div class='topbar'>
  <div style='display:flex;align-items:center;gap:16px'>
    <span class='brand'>Algo<span>Trade</span></span>
    <div class='nav-tags'>
      <span class='ntag-active'>{coin}</span>
      <span class='ntag'>1D</span>
      <span class='ntag'>Bybit</span>
      <span class='ntag'>MA · RSI · MACD · ATR</span>
      <span class='ntag'>ML Model</span>
    </div>
  </div>
  <div class='topbar-right'>
    <span class='live-badge'><span class='dot'></span>Live Paper</span>
    <span class='ts'>{now}</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Stats strip ──
chg_c = "g" if chg24>=0 else "r"
st.markdown(f"""
<div class='stats-row'>
  <div class='sc'>
    <div class='sc-label'>Price</div>
    <div class='sc-val'>${lat['close']:,.2f}</div>
    <div class='sc-sub {chg_c}'>{chg24:+.2f}% 24h</div>
  </div>
  <div class='sc'>
    <div class='sc-label'>Volume 24h</div>
    <div class='sc-val'>${vol24/1e6:.1f}M</div>
    <div class='sc-sub m'>daily</div>
  </div>
  <div class='sc'>
    <div class='sc-label'>RSI(14)</div>
    <div class='sc-val {"r" if rsi>70 else "g" if rsi<30 else "b"}'>{rsi:.1f}</div>
    <div class='sc-sub m'>{"Overbought" if rsi>70 else "Oversold" if rsi<30 else "Neutral"}</div>
  </div>
  <div class='sc'>
    <div class='sc-label'>MACD</div>
    <div class='sc-val {"g" if macd>0 else "r"}'>{macd:,.0f}</div>
    <div class='sc-sub m'>{"Bullish" if macd>0 else "Bearish"}</div>
  </div>
  <div class='sc'>
    <div class='sc-label'>ATR %</div>
    <div class='sc-val {"r" if atrp>4 else "m"}'>{atrp:.2f}%</div>
    <div class='sc-sub m'>{"High vol" if atrp>4 else "Low vol"}</div>
  </div>
  <div class='sc'>
    <div class='sc-label'>MA50</div>
    <div class='sc-val'>${lat['MA50']:,.0f}</div>
    <div class='sc-sub {"g" if lat["close"]>lat["MA50"] else "r"}'>Price {"above" if lat["close"]>lat["MA50"] else "below"}</div>
  </div>
  <div class='sc'>
    <div class='sc-label'>Signal</div>
    <div class='sc-val {"g" if sig=="BUY" else "r" if sig=="SELL" else "m"}'>{sig}</div>
    <div class='sc-sub m'>Current</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── KPI row ──
pcl = "g" if pnl>=0 else "r"
bcl = "g" if beat>=0 else "r"
ppc = "g" if ppnl>=0 else "r"
bhcl= "g" if bhp>=0 else "r"

st.markdown(f"""
<div class='kpi-row'>
  <div class='kpi'>
    <div class='kpi-label'>Final Value</div>
    <div class='kpi-val'>${fv:,.0f}</div>
    <div class='kpi-sub {pcl}'>{fmtp(pnlp)} &nbsp;·&nbsp; {fmt(pnl)}</div>
  </div>
  <div class='kpi'>
    <div class='kpi-label'>Buy &amp; Hold</div>
    <div class='kpi-val'>${bh:,.0f}</div>
    <div class='kpi-sub {bhcl}'>{fmtp(bhp)} baseline</div>
  </div>
  <div class='kpi'>
    <div class='kpi-label'>Alpha</div>
    <div class='kpi-val {bcl}'>{fmt(beat)}</div>
    <div class='kpi-sub {bcl}'>{'Outperformed' if beat>=0 else 'Underperformed'}</div>
  </div>
  <div class='kpi'>
    <div class='kpi-label'>Executions</div>
    <div class='kpi-val'>{len(trades)}</div>
    <div class='kpi-sub m'>{wr}% win rate · {wins} wins</div>
  </div>
  <div class='kpi'>
    <div class='kpi-label'>Paper P&amp;L</div>
    <div class='kpi-val {ppc}'>{fmt(ppnl)}</div>
    <div class='kpi-sub m'>{"Holding BTC" if pf.get("btc",0)>0 else "In cash"}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Chart + right panel ──
col_c, col_s = st.columns([4, 1])

with col_c:
    fig = plt.figure(figsize=(13, 7.5), facecolor='#111318')
    gs  = gridspec.GridSpec(3,1,figure=fig,hspace=0.04,height_ratios=[3,1,1])
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    ax3 = fig.add_subplot(gs[2], sharex=ax1)

    ax1.plot(df['date'],df['close'], color='#e8eaed', lw=1.4, zorder=3)
    ax1.plot(df['date'],df['MA7'],   color='#00d4aa', lw=1.0, alpha=0.8, zorder=2)
    ax1.plot(df['date'],df['MA21'],  color='#60a5fa', lw=1.0, alpha=0.7, zorder=2, dashes=[5,3])
    ax1.plot(df['date'],df['MA50'],  color='#c084fc', lw=1.0, alpha=0.7, zorder=2, dashes=[2,3])
    ax1.fill_between(df['date'],df['close'],df['close'].min(),alpha=0.03,color='#00d4aa')

    tc_map={'BUY':'#00d4aa','SELL':'#ff6b6b','TAKE PROFIT':'#34d399','STOP LOSS':'#ff6b6b'}
    for t in trades:
        c=tc_map.get(t['type'],'#94a3b8')
        mk='^' if t['type']=='BUY' else 'v'
        ax1.scatter(t['date'],t['price'],color=c,marker=mk,s=100,zorder=6,linewidths=0)

    for ax in [ax1,ax2,ax3]:
        ax.set_facecolor('#0e0f13')
        ax.tick_params(colors='#4b5563',labelsize=9,length=3,width=0.5)
        ax.grid(True,alpha=0.04,color='#ffffff',linewidth=0.5)
        for s in ax.spines.values(): s.set_color('#1f2128'); s.set_linewidth(0.5)

    ax2.plot(df['date'],df['RSI'],color='#a78bfa',lw=1)
    ax2.axhline(70,color='#ff6b6b',ls='--',lw=0.7,alpha=0.6)
    ax2.axhline(30,color='#00d4aa',ls='--',lw=0.7,alpha=0.6)
    ax2.axhline(rsi_thresh,color='#60a5fa',ls=':',lw=0.7,alpha=0.5)
    ax2.fill_between(df['date'],df['RSI'],70,where=(df['RSI']>=70),color='#ff6b6b',alpha=0.07)
    ax2.fill_between(df['date'],df['RSI'],30,where=(df['RSI']<=30),color='#00d4aa',alpha=0.07)
    ax2.set_ylim(0,100); ax2.set_yticks([30,50,70])

    hist=df['MACD']-df['MACDs']
    ax3.bar(df['date'],hist,color=['#00d4aa' if x>=0 else '#ff6b6b' for x in hist],alpha=0.65,width=0.8)
    ax3.plot(df['date'],df['MACD'], color='#60a5fa',lw=0.9)
    ax3.plot(df['date'],df['MACDs'],color='#f472b6',lw=0.9,dashes=[4,2])
    ax3.axhline(0,color='#4b5563',lw=0.5)

    ax1.set_ylabel('Price (USD)',color='#64748b',fontsize=9,labelpad=8)
    ax2.set_ylabel('RSI',        color='#64748b',fontsize=9,labelpad=8)
    ax3.set_ylabel('MACD',       color='#64748b',fontsize=9,labelpad=8)
    plt.setp(ax1.get_xticklabels(),visible=False)
    plt.setp(ax2.get_xticklabels(),visible=False)
    ax3.tick_params(axis='x',labelsize=9,colors='#64748b')
    fig.patch.set_facecolor('#111318')
    plt.tight_layout(pad=0.8)
    st.pyplot(fig, use_container_width=True)

with col_s:
    sc   = {'BUY':'sp-buy','SELL':'sp-sell','HOLD':'sp-hold'}[sig]
    rc   = 'g' if rsi<30 else 'r' if rsi>70 else 'b'
    mc   = 'g' if macd>0 else 'r'
    pfst = 'Holding BTC' if pf.get('btc',0)>0 else 'In Cash'
    ppc2 = 'g' if ppnl>=0 else 'r'
    opc  = 'g' if opnl>=0 else 'r'
    rsi_w= min(100,max(0,rsi))
    rsi_bc='#ff6b6b' if rsi>70 else '#00d4aa' if rsi<30 else '#60a5fa'

    st.markdown(f"""
<div class='sig-card'>
  <div class='sig-pill {sc}'>{sig}</div>
  <div class='price-hero'>${lat['close']:,.0f}</div>
  <div class='pair-meta'>{coin} · Bybit · Daily</div>
</div>

<div class='ind-card'>
  <div class='ind-title'>Indicators</div>
  <div class='ir'><span class='ik'>RSI(14)</span><span class='iv {rc}'>{rsi:.1f}</span></div>
  <div class='bar-wrap'><div class='bar-fill' style='width:{rsi_w:.0f}%;background:{rsi_bc}'></div></div>
  <div class='ir'><span class='ik'>MACD</span><span class='iv {mc}'>{macd:,.0f}</span></div>
  <div class='ir'><span class='ik'>Signal line</span><span class='iv m'>{lat['MACDs']:,.0f}</span></div>
  <div class='ir'><span class='ik'>ATR %</span><span class='iv {"r" if atrp>4 else "m"}'>{atrp:.2f}%</span></div>
  <div class='ir'><span class='ik'>MA7</span><span class='iv g'>${lat['MA7']:,.0f}</span></div>
  <div class='ir'><span class='ik'>MA21</span><span class='iv b'>${lat['MA21']:,.0f}</span></div>
  <div class='ir'><span class='ik'>MA50</span><span class='iv m'>${lat['MA50']:,.0f}</span></div>
</div>

<div class='pf-card'>
  <div class='ind-title'>Paper Portfolio</div>
  <div class='pr'><span class='pk'>Value</span><span class='pv'>${pbv:,.0f}</span></div>
  <div class='pr'><span class='pk'>P&amp;L</span><span class='pv {ppc2}'>{fmt(ppnl)}</span></div>
  <div class='pr'><span class='pk'>Status</span><span class='pv {"g" if pf.get("btc",0)>0 else "m"}'>{pfst}</span></div>
  <div class='pr'><span class='pk'>Entry</span><span class='pv'>${pbp:,.0f}</span></div>
  <div class='pr'><span class='pk'>Open P&amp;L</span><span class='pv {opc}'>{fmtp(opnl)}</span></div>
  <div class='pr'><span class='pk'>Trades</span><span class='pv'>{len(pf.get("trades",[]))}</span></div>
</div>
""", unsafe_allow_html=True)

# ── Trade log ──
tc_map2 = {'BUY':'g','SELL':'r','TAKE PROFIT':'a','STOP LOSS':'r'}
rows = ""
for t in reversed(trades[-8:]):
    ds  = t['date'].strftime('%Y-%m-%d') if hasattr(t['date'],'strftime') else str(t['date'])[:10]
    tc_ = tc_map2.get(t['type'],'m')
    pv  = t.get('pnl',0)
    pc_ = 'g' if pv>0 else 'r' if pv<0 else 'm'
    ps  = (f"+${pv:,.0f}" if pv>=0 else f"-${abs(pv):,.0f}") if t['type']!='BUY' else '--'
    rows += f"""
<div class='tr-row'>
  <div class='trc'>{ds}</div>
  <div class='trc {tc_}'>{t['type']}</div>
  <div class='trc bright'>${t['price']:,.2f}</div>
  <div class='trc bright'>${t['portfolio']:,.2f}</div>
  <div class='trc {pc_}'>{ps}</div>
</div>"""

st.markdown(f"""
<div class='tlog'>
  <div class='tlog-title'>Execution Log</div>
  <div class='th'>
    <div class='thc'>Date</div>
    <div class='thc'>Type</div>
    <div class='thc'>Price</div>
    <div class='thc'>Portfolio</div>
    <div class='thc'>P&amp;L</div>
  </div>
  {rows}
</div>
""", unsafe_allow_html=True)