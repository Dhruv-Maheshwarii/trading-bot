import ccxt
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import pickle
import warnings
warnings.filterwarnings('ignore')

# ── Step 1: Fetch lots of historical data ──
print("📥 Fetching historical data...")
exchange = ccxt.kucoin()
ohlcv    = exchange.fetch_ohlcv('BTC/USDT', '1d', limit=1000)
df       = pd.DataFrame(ohlcv, columns=['timestamp','open','high','low','close','volume'])
df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
print(f"✅ Got {len(df)} days of data")

# ── Step 2: Calculate indicators (features) ──
print("🔧 Calculating indicators...")

# Moving averages
df['MA7']  = df['close'].rolling(7).mean()
df['MA21'] = df['close'].rolling(21).mean()
df['MA50'] = df['close'].rolling(50).mean()
df['MA200']= df['close'].rolling(200).mean()

# RSI
delta     = df['close'].diff()
gain      = delta.where(delta > 0, 0).rolling(14).mean()
loss      = -delta.where(delta < 0, 0).rolling(14).mean()
df['RSI'] = 100 - (100 / (1 + gain / loss))

# MACD
exp12          = df['close'].ewm(span=12).mean()
exp26          = df['close'].ewm(span=26).mean()
df['MACD']     = exp12 - exp26
df['MACD_sig'] = df['MACD'].ewm(span=9).mean()
df['MACD_hist']= df['MACD'] - df['MACD_sig']

# ATR
df['TR']  = pd.concat([
    df['high'] - df['low'],
    (df['high'] - df['close'].shift()).abs(),
    (df['low']  - df['close'].shift()).abs()
], axis=1).max(axis=1)
df['ATR']     = df['TR'].rolling(14).mean()
df['ATR_pct'] = df['ATR'] / df['close'] * 100

# Bollinger Bands
df['BB_mid']   = df['close'].rolling(20).mean()
df['BB_std']   = df['close'].rolling(20).std()
df['BB_upper'] = df['BB_mid'] + 2 * df['BB_std']
df['BB_lower'] = df['BB_mid'] - 2 * df['BB_std']
df['BB_pct']   = (df['close'] - df['BB_lower']) / (df['BB_upper'] - df['BB_lower'])

# Price momentum
df['momentum_3']  = df['close'].pct_change(3)  * 100
df['momentum_7']  = df['close'].pct_change(7)  * 100
df['momentum_14'] = df['close'].pct_change(14) * 100

# Volume momentum
df['vol_ma7']  = df['volume'].rolling(7).mean()
df['vol_ratio']= df['volume'] / df['vol_ma7']

# MA ratios
df['ma7_21_ratio']  = df['MA7']  / df['MA21']
df['ma21_50_ratio'] = df['MA21'] / df['MA50']
df['price_ma50']    = df['close'] / df['MA50']

print("✅ Indicators calculated")

# ── Step 3: Create labels (what we want ML to predict) ──
print("🏷️  Creating labels...")

# Look 7 days into future — did price go up more than 3%?
df['future_return'] = df['close'].shift(-7) / df['close'] - 1

def label(ret):
    if ret > 0.03:   return 1   # BUY  — price went up 3%+
    elif ret < -0.03: return -1  # SELL — price went down 3%+
    else:             return 0   # HOLD — price stayed flat

df['label'] = df['future_return'].apply(label)

# ── Step 4: Prepare features ──
features = [
    'RSI', 'MACD', 'MACD_sig', 'MACD_hist',
    'ATR_pct', 'BB_pct',
    'momentum_3', 'momentum_7', 'momentum_14',
    'vol_ratio', 'ma7_21_ratio', 'ma21_50_ratio', 'price_ma50'
]

df = df.dropna()
X  = df[features]
y  = df['label']

print(f"✅ Dataset: {len(X)} samples")
print(f"   BUY signals  : {(y==1).sum()} ({(y==1).sum()/len(y)*100:.1f}%)")
print(f"   SELL signals : {(y==-1).sum()} ({(y==-1).sum()/len(y)*100:.1f}%)")
print(f"   HOLD signals : {(y==0).sum()} ({(y==0).sum()/len(y)*100:.1f}%)")

# ── Step 5: Train model ──
print("\n🧠 Training Random Forest model...")
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, shuffle=False
)

model = RandomForestClassifier(
    n_estimators=200,
    max_depth=10,
    min_samples_split=20,
    random_state=42,
    class_weight='balanced'
)
model.fit(X_train, y_train)

# ── Step 6: Evaluate ──
print("📊 Evaluating model...")
y_pred    = model.predict(X_test)
accuracy  = accuracy_score(y_test, y_pred)

print(f"\n🎯 MODEL RESULTS")
print("=" * 45)
print(f"Accuracy        : {accuracy*100:.1f}%")
print(f"Training samples: {len(X_train)}")
print(f"Testing samples : {len(X_test)}")
print(f"\n📋 Detailed Report:")
print(classification_report(y_test, y_pred, target_names=['SELL','HOLD','BUY']))

# ── Step 7: Feature importance ──
print("🔍 Most important features:")
importance = pd.DataFrame({
    'feature':    features,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

for _, row in importance.iterrows():
    bar = '█' * int(row['importance'] * 100)
    print(f"   {row['feature']:<20} {bar} {row['importance']*100:.1f}%")

# ── Step 8: Test on latest data ──
print(f"\n📡 Current market prediction:")
latest_features = X.iloc[-1][features].values.reshape(1, -1)
prediction      = model.predict(latest_features)[0]
probability     = model.predict_proba(latest_features)[0]
classes         = model.classes_

pred_label = {1: '🟢 BUY', -1: '🔴 SELL', 0: '⚪ HOLD'}
print(f"   Signal     : {pred_label[prediction]}")
for cls, prob in zip(classes, probability):
    print(f"   {pred_label[cls]:<12} confidence: {prob*100:.1f}%")

# ── Step 9: Save model ──
with open('model.pkl', 'wb') as f:
    pickle.dump(model, f)
with open('features.pkl', 'wb') as f:
    pickle.dump(features, f)

print(f"\n✅ Model saved as model.pkl")
print(f"✅ Ready to plug into trading bot!")