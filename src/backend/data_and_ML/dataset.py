"""
Agentic AI Trade Validator - Improved Synthetic Trade Dataset Generator
- Fraud rate capped at 2–5%
- Safer/robust market lookup
- Reproducible
- Additional features
- Prevents negative balances (optional)
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from tqdm import tqdm
import warnings
warnings.filterwarnings("ignore")

# ========== CONFIG ==========
TOKENS = ['AAPL', 'GOOGL', 'TSLA', 'AMZN', 'MSFT']
NUM_TRADES = 100000
NUM_WALLETS = 2000
DATE_START = '2024-01-01'
DATE_END = '2024-12-31'

SEED = 42
np.random.seed(SEED)

# Fraud simulation params
FRAUD_RATE = 0.02  # random anomaly
PRICE_DEV_ATTEMPT_P = 0.15  # attempted manipulation probability
MAX_MANIP_PCT = 0.15
NORMAL_SIGMA = 0.02

PRICE_DEV_THRESHOLD_STD_MULT = 3   # z-score multiplier
PRICE_DEV_ABS_CAP_PCT = 5.0       # absolute pct as minimum threshold guard

BALANCE_RATIO_THRESHOLD = 0.40
FREQUENCY_THRESHOLD = 10  # trades in past hour

OUTPUT_CSV = "synthetic_trades.csv"
OUTPUT_PARQUET = "synthetic_trades.parquet"

USE_YFINANCE = True
ENFORCE_POSITIVE_BALANCE = True
# ===========================

print("🚀 Initializing Agentic Trade Dataset Generator (improved)...")

# ========= Market data fetch ==========
market_data = {}
date_index = pd.date_range(DATE_START, DATE_END, freq='B')  # business days
if USE_YFINANCE:
    try:
        import yfinance as yf
        print("📈 Downloading market data from Yahoo Finance (batch)...")
        all_hist = yf.download(TOKENS, start=DATE_START, end=DATE_END, progress=False, threads=True)
        for token in TOKENS:
            try:
                close = all_hist[('Close', token)].dropna()
                vol = all_hist[('Volume', token)].dropna()
                df = pd.DataFrame({'Close': close, 'Volume': vol})
                df = df.sort_index().reindex(pd.to_datetime(df.index)).ffill().bfill()
                market_data[token] = df
            except Exception:
                market_data[token] = None
    except Exception as e:
        print("⚠️ yfinance batch download failed, falling back to synthetic. Error:", e)
        market_data = {t: None for t in TOKENS}

# fallback to synthetic if needed
for token in TOKENS:
    if market_data.get(token) is None or len(market_data[token]) == 0:
        print(f"⚠️  No real data for {token}, generating synthetic series.")
        dates = pd.date_range(DATE_START, DATE_END, freq='B')
        price = 100 + np.cumsum(np.random.normal(0, 1, len(dates)))
        market_data[token] = pd.DataFrame({
            'Close': np.abs(price) + 50,
            'Volume': np.random.uniform(1e6, 1e8, len(dates))
        }, index=dates)

# ========= Compute indicators =========
print("\n🧮 Computing technical indicators...")
for token, df in market_data.items():
    df = df.sort_index()
    df['returns'] = df['Close'].pct_change()
    df['rolling_volatility'] = df['returns'].rolling(window=10, min_periods=1).std() * (252 ** 0.5)
    df['SMA_20'] = df['Close'].rolling(window=20, min_periods=1).mean()
    df['SMA_50'] = df['Close'].rolling(window=50, min_periods=1).mean()
    df['market_trend'] = ((df['SMA_20'] > df['SMA_50']).astype(int) * 2 - 1)
    df.fillna(method='bfill', inplace=True)
    df.fillna(0, inplace=True)
    market_data[token] = df

# ========= Initialize wallets =========
print(f"\n👛 Initializing {NUM_WALLETS} wallet agents...")
wallets = {}
for i in range(NUM_WALLETS):
    addr = f"0x{i:040x}"
    wallets[addr] = {
        'balance': float(np.random.uniform(10_000, 1_000_000)),
        'trade_history': [],
        'counterparty_counts': {}
    }
wallet_addresses = list(wallets.keys())

# ========= Helper: nearest market row =========
def get_market_row(token_df, ts: pd.Timestamp):
    ts = pd.to_datetime(ts)
    idxer = token_df.index.get_indexer([ts], method='nearest')[0]
    return token_df.iloc[idxer]

# ========= Generate trades =========
print(f"\n🔨 Generating {NUM_TRADES} synthetic trades...")
trades = []

start_dt = pd.to_datetime(DATE_START)
end_dt = pd.to_datetime(DATE_END) + pd.Timedelta(days=1)

while len(trades) < NUM_TRADES:
    day = pd.Timestamp(np.random.choice(pd.date_range(start_dt, end_dt, freq='B')))
    hour = np.random.randint(9, 16)
    minute = np.random.randint(0, 60)
    second = np.random.randint(0, 60)
    timestamp = pd.Timestamp(year=day.year, month=day.month, day=day.day,
                             hour=int(hour), minute=int(minute), second=int(second))

    token = np.random.choice(TOKENS)
    buyer_id = np.random.choice(wallet_addresses)
    seller_id = np.random.choice([w for w in wallet_addresses if w != buyer_id])

    token_df = market_data[token]
    market_row = get_market_row(token_df, timestamp)
    market_price = float(market_row['Close'])
    rolling_volatility = float(market_row.get('rolling_volatility', 0.0))
    market_trend = int(market_row.get('market_trend', 0))

    trade_size = int(np.random.randint(1, 1000))
    if np.random.random() < PRICE_DEV_ATTEMPT_P:
        price_deviation = float(np.random.uniform(-MAX_MANIP_PCT, MAX_MANIP_PCT))
        attempted_manip = True
    else:
        price_deviation = float(np.random.normal(0, NORMAL_SIGMA))
        attempted_manip = False

    trade_price = market_price * (1 + price_deviation)
    trade_value = trade_size * trade_price

    buyer_balance = wallets[buyer_id]['balance']
    seller_balance = wallets[seller_id]['balance']
    buyer_balance_ratio = trade_value / buyer_balance if buyer_balance > 0 else np.inf
    seller_balance_ratio = trade_value / seller_balance if seller_balance > 0 else np.inf

    hour_ago = timestamp - pd.Timedelta(hours=1)
    buyer_recent = [t for t in wallets[buyer_id]['trade_history'] if t > hour_ago]
    trade_frequency = len(buyer_recent)

    if ENFORCE_POSITIVE_BALANCE and (trade_value > buyer_balance):
        continue

    wallets[buyer_id]['trade_history'].append(timestamp)
    wallets[seller_id]['trade_history'].append(timestamp)
    wallets[buyer_id]['counterparty_counts'][seller_id] = wallets[buyer_id]['counterparty_counts'].get(seller_id,0)+1
    wallets[seller_id]['counterparty_counts'][buyer_id] = wallets[seller_id]['counterparty_counts'].get(buyer_id,0)+1

    wallets[buyer_id]['balance'] -= trade_value
    wallets[seller_id]['balance'] += trade_value

    price_deviation_pct = (trade_price - market_price) / market_price * 100

    trade = {
        'timestamp': timestamp,
        'token': token,
        'buyer_id': buyer_id,
        'seller_id': seller_id,
        'trade_size': trade_size,
        'trade_price': round(trade_price, 2),
        'trade_value': round(trade_value, 2),
        'market_price': round(market_price, 2),
        'price_deviation_pct': round(price_deviation_pct, 4),
        'rolling_volatility': round(rolling_volatility, 6),
        'market_trend': market_trend,
        'buyer_balance_ratio': round(buyer_balance_ratio, 6),
        'seller_balance_ratio': round(seller_balance_ratio, 6),
        'trade_frequency': trade_frequency,
        'attempted_manip': int(attempted_manip)
    }
    trades.append(trade)

# ========= Build DataFrame =========
df = pd.DataFrame(trades)
df.sort_values('timestamp', inplace=True)
df.reset_index(drop=True, inplace=True)

# time features
df['hour'] = df['timestamp'].dt.hour
df['weekday'] = df['timestamp'].dt.weekday

pair_counts = {}
pair_repeat = []
for idx, row in df.iterrows():
    pair = (row['buyer_id'], row['seller_id'])
    c = pair_counts.get(pair, 0)
    pair_repeat.append(c)
    pair_counts[pair] = c + 1
df['counterparty_repeat'] = pair_repeat

# ========= Controlled Fraud Labeling =========
df['is_fraudulent'] = 0

# 1️⃣ Price manipulation attempts → always fraud
df.loc[df['attempted_manip'] == 1, 'is_fraudulent'] = 1

# 2️⃣ Large balance ratio / high frequency → sample 15% to limit overall fraud
suspect_mask = (df['buyer_balance_ratio'] > BALANCE_RATIO_THRESHOLD) | \
               (df['seller_balance_ratio'] > BALANCE_RATIO_THRESHOLD) | \
               (df['trade_frequency'] > FREQUENCY_THRESHOLD)
suspect_indices = df[suspect_mask & (df['is_fraudulent'] == 0)].index
sample_frac = 0.15
sample_indices = np.random.choice(suspect_indices, size=int(len(suspect_indices)*sample_frac), replace=False)
df.loc[sample_indices, 'is_fraudulent'] = 1

# 3️⃣ Random anomalies
rand_mask = np.random.random(len(df)) < FRAUD_RATE
df.loc[rand_mask, 'is_fraudulent'] = 1

# 4️⃣ Cap fraud rate at ~5%
max_fraud = int(len(df) * 0.05)
current_fraud = df['is_fraudulent'].sum()
if current_fraud > max_fraud:
    fraud_indices = df[df['is_fraudulent']==1].index
    disable_count = current_fraud - max_fraud
    disable_indices = np.random.choice(fraud_indices, size=disable_count, replace=False)
    df.loc[disable_indices, 'is_fraudulent'] = 0

# ========= Export =========
df.to_csv(OUTPUT_CSV, index=False)
df.to_parquet(OUTPUT_PARQUET, index=False)

# ========= Summary =========
print("\n" + "="*60)
print("✅ DATASET GENERATION COMPLETE")
print("="*60)
total = len(df)
fraud_count = int(df['is_fraudulent'].sum())
print(f"Output files: {OUTPUT_CSV}, {OUTPUT_PARQUET}")
print(f"Total trades: {total:,}")
print(f"Fraudulent: {fraud_count:,} ({fraud_count/total*100:.2f}%)")
print("\nToken distribution:")
print(df['token'].value_counts())
print("\nSample:")
print(df.head(8).to_string(index=False))
