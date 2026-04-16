import ccxt
import pandas as pd
import smtplib
import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pickle
import numpy as np

# Load ML model
def load_ml_model():
    try:
        with open('model.pkl', 'rb') as f:
            model = pickle.load(f)
        with open('features.pkl', 'rb') as f:
            features = pickle.load(f)
        return model, features
    except:
        print("⚠️ ML model not found — running without ML filter")
        return None, None

def get_ml_signal(model, features, data):
    if model is None:
        return True, 0.5
    try:
        X = pd.DataFrame([[
            data['rsi'],
            data['macd'],
            data['macd_sig'],
            data['macd_hist'],
            data['atr_pct'],
            data['bb_pct'],
            data['momentum_3'],
            data['momentum_7'],
            data['momentum_14'],
            data['vol_ratio'],
            data['ma7_21_ratio'],
            data['ma21_50_ratio'],
            data['price_ma50'],
            data['prev_day_1'],
            data['prev_day_2'],
            data['prev_day_3'],
            data['hl_range'],
            data['close_pos'],
            data['vol_spike']
        ]], columns=features)
        prediction  = model.predict(X)[0]
        probability = model.predict_proba(X)[0]
        up_conf     = probability[1]
        return prediction == 1, up_conf
    except Exception as e:
        print(f"⚠️ ML error: {e}")
        return True, 0.5

load_dotenv()
EMAIL_SENDER   = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

# ── Paper trading wallet ──
STARTING_CAPITAL = 10000
TAKE_PROFIT      = 1.08
STOP_LOSS        = 0.95

# ── Load or create portfolio ──
PORTFOLIO_FILE = 'portfolio.json'

def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, 'r') as f:
            return json.load(f)
    return {
        'cash':       STARTING_CAPITAL,
        'btc':        0,
        'buy_price':  0,
        'trades':     [],
        'started_at': datetime.now().strftime('%Y-%m-%d %H:%M')
    }

def save_portfolio(portfolio):
    with open(PORTFOLIO_FILE, 'w') as f:
        json.dump(portfolio, f, indent=2, default=str)

# ── Email alert ──
def send_email(subject, body):
    try:
        msg = MIMEMultipart()
        msg['From']    = EMAIL_SENDER
        msg['To']      = EMAIL_RECEIVER
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        server.quit()
        print("   📧 Email alert sent!")
    except Exception as e:
        print(f"   ❌ Email failed: {e}")

# ── Fetch data + calculate indicators ──
def get_signal():
    exchange = ccxt.bybit()
    ohlcv    = exchange.fetch_ohlcv('BTC/USDT', '1d', limit=100)
    df       = pd.DataFrame(ohlcv, columns=['timestamp','open','high','low','close','volume'])
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')

    # Indicators
    df['MA7']  = df['close'].rolling(7).mean()
    df['MA21'] = df['close'].rolling(21).mean()
    df['MA50'] = df['close'].rolling(50).mean()
    delta      = df['close'].diff()
    gain       = delta.where(delta > 0, 0).rolling(14).mean()
    loss       = -delta.where(delta < 0, 0).rolling(14).mean()
    df['RSI']  = 100 - (100 / (1 + gain / loss))
    exp12      = df['close'].ewm(span=12).mean()
    exp26      = df['close'].ewm(span=26).mean()
    df['MACD']        = exp12 - exp26
    df['MACD_signal'] = df['MACD'].ewm(span=9).mean()
    df['TR']    = pd.concat([
        df['high'] - df['low'],
        (df['high'] - df['close'].shift()).abs(),
        (df['low']  - df['close'].shift()).abs()
    ], axis=1).max(axis=1)
    df['ATR']     = df['TR'].rolling(14).mean()
    df['ATR_pct'] = df['ATR'] / df['close'] * 100

    latest = df.iloc[-1]
    prev   = df.iloc[-2]

    # Conditions
    ma_buy         = latest['MA7'] > latest['MA21'] and prev['MA7'] <= prev['MA21']
    ma_sell        = latest['MA7'] < latest['MA21'] and prev['MA7'] >= prev['MA21']
    rsi_ok_buy     = latest['RSI'] < 60
    rsi_ok_sell    = latest['RSI'] > 30
    macd_buy       = latest['MACD'] > latest['MACD_signal']
    macd_sell      = latest['MACD'] < latest['MACD_signal']
    macd_positive  = latest['MACD'] > 0
    above_ma50     = latest['close'] > latest['MA50'] * 1.02
    low_volatility = latest['ATR_pct'] < 4
    ma21_rising    = latest['MA21'] > df.iloc[-4]['MA21']

    buy_signal  = ma_buy and rsi_ok_buy and macd_buy and macd_positive and above_ma50 and low_volatility and ma21_rising
    sell_signal = ma_sell and rsi_ok_sell and macd_sell

    # Extra features for ML
    latest2 = df.iloc[-2]
    latest3 = df.iloc[-3]
    latest4 = df.iloc[-4]

    return {
        'signal':        'BUY'  if buy_signal else 'SELL' if sell_signal else 'HOLD',
        'price':         latest['close'],
        'rsi':           latest['RSI'],
        'macd':          latest['MACD'],
        'macd_sig':      latest['MACD_signal'],
        'macd_hist':     latest['MACD'] - latest['MACD_signal'],
        'atr_pct':       latest['ATR_pct'],
        'bb_pct':        (latest['close'] - (latest['close'] - 2*df['close'].rolling(20).std().iloc[-1])) /
                         (4 * df['close'].rolling(20).std().iloc[-1]) if df['close'].rolling(20).std().iloc[-1] != 0 else 0.5,
        'momentum_3':    df['close'].pct_change(3).iloc[-1]  * 100,
        'momentum_7':    df['close'].pct_change(7).iloc[-1]  * 100,
        'momentum_14':   df['close'].pct_change(14).iloc[-1] * 100,
        'vol_ratio':     latest['volume'] / df['volume'].rolling(7).mean().iloc[-1],
        'ma7_21_ratio':  latest['MA7']  / latest['MA21'],
        'ma21_50_ratio': latest['MA21'] / latest['MA50'],
        'price_ma50':    latest['close'] / latest['MA50'],
        'prev_day_1':    df['close'].pct_change(1).iloc[-1] * 100,
        'prev_day_2':    df['close'].pct_change(2).iloc[-1] * 100,
        'prev_day_3':    df['close'].pct_change(3).iloc[-1] * 100,
        'hl_range':      (latest['high'] - latest['low']) / latest['close'] * 100,
        'close_pos':     (latest['close'] - latest['low']) / (latest['high'] - latest['low']) if latest['high'] != latest['low'] else 0.5,
        'vol_spike':     latest['volume'] / df['volume'].rolling(30).mean().iloc[-1],
        'ma7':           latest['MA7'],
        'ma21':          latest['MA21'],
        'ma50':          latest['MA50'],
        'timestamp':     datetime.now().strftime('%Y-%m-%d %H:%M')
    }

# ── Execute paper trade ──
def execute_trade(portfolio, data):
    signal    = data['signal']
    price     = data['price']
    timestamp = data['timestamp']

    # Take profit check
    if portfolio['btc'] > 0 and price > portfolio['buy_price'] * TAKE_PROFIT:
        cash = portfolio['btc'] * price
        profit = cash - STARTING_CAPITAL
        portfolio['cash'] = cash
        portfolio['btc']  = 0
        trade = {'date': timestamp, 'type': 'TAKE PROFIT', 'price': price, 'portfolio': cash}
        portfolio['trades'].append(trade)
        save_portfolio(portfolio)
        print(f"   💰 TAKE PROFIT at ${price:,.2f} | Portfolio: ${cash:,.2f}")
        send_email(
            "💰 AlgoTrade — TAKE PROFIT Hit!",
            f"""
            <h2 style='color:gold'>💰 Take Profit Triggered!</h2>
            <p><b>Price:</b> ${price:,.2f}</p>
            <p><b>Portfolio Value:</b> ${cash:,.2f}</p>
            <p><b>Time:</b> {timestamp}</p>
            <p><b>RSI:</b> {data['rsi']:.1f}</p>
            """
        )
        return portfolio

    # Stop loss check
    if portfolio['btc'] > 0 and price < portfolio['buy_price'] * STOP_LOSS:
        cash = portfolio['btc'] * price
        portfolio['cash'] = cash
        portfolio['btc']  = 0
        trade = {'date': timestamp, 'type': 'STOP LOSS', 'price': price, 'portfolio': cash}
        portfolio['trades'].append(trade)
        save_portfolio(portfolio)
        print(f"   ⛔ STOP LOSS at ${price:,.2f} | Portfolio: ${cash:,.2f}")
        send_email(
            "⛔ AlgoTrade — STOP LOSS Hit!",
            f"""
            <h2 style='color:orange'>⛔ Stop Loss Triggered!</h2>
            <p><b>Price:</b> ${price:,.2f}</p>
            <p><b>Portfolio Value:</b> ${cash:,.2f}</p>
            <p><b>Time:</b> {timestamp}</p>
            """
        )
        return portfolio

    # Buy signal
    if signal == 'BUY' and portfolio['cash'] > 0 and portfolio['btc'] == 0:
        btc = portfolio['cash'] / price
        portfolio['btc']       = btc
        portfolio['buy_price'] = price
        portfolio['cash']      = 0
        trade = {'date': timestamp, 'type': 'BUY', 'price': price, 'portfolio': btc * price}
        portfolio['trades'].append(trade)
        save_portfolio(portfolio)
        print(f"   🟢 BUY at ${price:,.2f} | BTC held: {btc:.6f}")
        send_email(
            "🟢 AlgoTrade — BUY Signal!",
            f"""
            <h2 style='color:lime'>🟢 BUY Signal Detected!</h2>
            <p><b>Price:</b> ${price:,.2f}</p>
            <p><b>BTC Bought:</b> {btc:.6f}</p>
            <p><b>Time:</b> {timestamp}</p>
            <p><b>RSI:</b> {data['rsi']:.1f}</p>
            <p><b>MACD:</b> {data['macd']:.2f}</p>
            <p><b>ATR%:</b> {data['atr_pct']:.2f}%</p>
            """
        )
        return portfolio

    # Sell signal
    if signal == 'SELL' and portfolio['btc'] > 0:
        cash = portfolio['btc'] * price
        portfolio['cash'] = cash
        portfolio['btc']  = 0
        trade = {'date': timestamp, 'type': 'SELL', 'price': price, 'portfolio': cash}
        portfolio['trades'].append(trade)
        save_portfolio(portfolio)
        print(f"   🔴 SELL at ${price:,.2f} | Portfolio: ${cash:,.2f}")
        send_email(
            "🔴 AlgoTrade — SELL Signal!",
            f"""
            <h2 style='color:red'>🔴 SELL Signal Detected!</h2>
            <p><b>Price:</b> ${price:,.2f}</p>
            <p><b>Portfolio Value:</b> ${cash:,.2f}</p>
            <p><b>Time:</b> {timestamp}</p>
            <p><b>RSI:</b> {data['rsi']:.1f}</p>
            """
        )
        return portfolio

    return portfolio

# ── Main loop ──
def run_bot():
    print("🤖 AlgoTrade Paper Trading Bot Started!")
    print("=" * 45)
    print("Strategy  : MA + RSI + MACD + ATR + ML")
    print("Pair      : BTC/USDT")
    print("Interval  : Every 1 hour")
    print("=" * 45)

    # Load ML model
    model, features = load_ml_model()
    if model:
        print("🧠 ML Model loaded successfully!")
    
    portfolio = load_portfolio()
    save_portfolio(portfolio)
    print(f"💰 Portfolio: ${portfolio['cash']:,.2f} cash | {portfolio['btc']:.6f} BTC")
    print("Press Ctrl+C to stop\n")

    while True:
        try:
            now  = datetime.now().strftime('%Y-%m-%d %H:%M')
            print(f"⏰ [{now}] Checking market...")

            data = get_signal()
            ml_up, ml_conf = get_ml_signal(model, features, data)

            print(f"   Price : ${data['price']:,.2f}")
            print(f"   RSI   : {data['rsi']:.1f}")
            print(f"   Signal: {data['signal']}")
            print(f"   ML    : {'🟢 UP' if ml_up else '🔴 DOWN'} ({ml_conf*100:.1f}% confidence)")

            # Only execute BUY if ML also confirms UP with 55%+ confidence
            if data['signal'] == 'BUY' and not (ml_up and ml_conf > 0.55):
                print(f"   ⚠️ ML filtered out BUY signal — not confident enough")
                data['signal'] = 'HOLD'

            portfolio = execute_trade(portfolio, data)

            if portfolio['btc'] > 0:
                current_value = portfolio['btc'] * data['price']
                pnl = ((current_value - portfolio['buy_price'] * portfolio['btc']) /
                       (portfolio['buy_price'] * portfolio['btc'])) * 100
                print(f"   📊 Holding BTC | Value: ${current_value:,.2f} | P&L: {pnl:.2f}%")
            else:
                print(f"   📊 Holding CASH | ${portfolio['cash']:,.2f}")

            print(f"   💤 Sleeping 1 hour...\n")
            time.sleep(3600)

        except KeyboardInterrupt:
            print("\n🛑 Bot stopped by user")
            break
        except Exception as e:
            print(f"   ❌ Error: {e}")
            print(f"   Retrying in 5 minutes...")
            time.sleep(300)

if __name__ == "__main__":
    run_bot()