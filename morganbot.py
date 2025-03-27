import ccxt
import pandas as pd
import numpy as np
import ta
import plotly.graph_objects as go
from datetime import datetime
import time
import os
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from flask import Flask

# تنظیم Flask
app = Flask(__name__)

@app.route('/')
def health_check():
    return "OK", 200

# ---------- تنظیمات ----------
TELEGRAM_BOT_TOKEN = "8028923358:AAFDKzIahr5EEz9_9ax06gkswVQ-HrbntXc"
TELEGRAM_CHAT_ID = "255861039"

WINDOW = 3
MIN_DISTANCE = 3
INTERVAL = 10
LIMIT = 50
LIVE_WINDOW = 5
OUTPUT_DIR = "output"
TIMEFRAME = '1m'
HIGHER_TIMEFRAMES = ['30m', '1h']
IMBALANCE_THRESHOLD = 3.0
DELTA_THRESHOLD = 1000
ATR_MULTIPLIER = 2

reported_divergences = {}
reported_imbalances = {}

exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})

if not os.path.exists(OUTPUT_DIR):
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
    except OSError as e:
        print(f"خطا در ساخت پوشه {OUTPUT_DIR}: {e}")
        raise

FUTURES_SYMBOLS = list(dict.fromkeys([
    'BTCUSDT', 'ETHUSDT', '1INCHUSDT','AVAXUSDT',
    'AXSUSDT', 'BABYDOGEUSDT', 'BANUSDT', 'BBUSDT', 'BCHUSDT', 'BEAMXUSDT', 'BICOUSDT', 'BIGTIMEUSDT',
    'BIOUSDT', 'BITCOINUSDT', 'BLURUSDT', 'BNBUSDT', 'BOMEUSDT', 'BONKUSDT', 'BRETTUSDT', 'BTTUSDT',
    'CAKEUSDT', 'CATUSDT', 'CELRUSDT', 'CETUSUSDT', 'CFXUSDT', 'CHEEMSUSDT', 'CHRUSDT', 'CHZUSDT',
    'CKBUSDT', 'COMPUSDT', 'CROUSDT', 'CRVUSDT', 'CVXUSDT', 'DASHUSDT', 'DEGENUSDT', 'DOGUSDT',
    'DOGEUSDT', 'DOGSUSDT', 'DOTUSDT', 'DUSKUSDT', 'DYDXUSDT', 'DYMUSDT', 'EGLDUSDT', 'EIGENUSDT',
    'ENAUSDT', 'ENJUSDT', 'ENSUSDT', 'EOSUSDT', 'ETCUSDT', 'ETHFIUSDT', 'FARTCOINUSDT', 'FILUSDT',
    'FLOKIUSDT', 'FLOWUSDT', 'FXSUSDT', 'GALAUSDT', 'GASUSDT', 'GLMUSDT', 'GMTUSDT', 'GOATUSDT',
    'GRASSUSDT', 'GRIFFAINUSDT', 'GRTUSDT', 'HBARUSDT', 'HMSTRUSDT', 'HNTUSDT', 'HOTUSDT', 'ICPUSDT',
    'IDUSDT', 'IMXUSDT', 'INJUSDT', 'IOUSDT', 'IOTAUSDT', 'IOTXUSDT', 'IPUSDT', 'JASMYUSDT', 'JSTUSDT',
    'JTOUSDT', 'JUPUSDT', 'KAIAUSDT', 'KAITOUSDT', 'KASUSDT', 'KAVAUSDT', 'KDAUSDT', 'KSMUSDT',
    'LDOUSDT', 'LINKUSDT', 'LPTUSDT', 'LRCUSDT', 'LTCUSDT', 'LUNAUSDT', 'LUNCUSDT', 'MAGATRUMPUSDT',
    'MAGICUSDT', 'MANAUSDT', 'MANTAUSDT', 'MASKUSDT', 'MEUSDT', 'MELANIAUSDT', 'MEMEUSDT', 'MERLUSDT',
    'METISUSDT', 'MEWUSDT', 'MINAUSDT', 'MKRUSDT', 'MNTUSDT', 'MOGUSDT', 'MOVEUSDT', 'MUBARAKUSDT',
    'NEARUSDT', 'NEIROCTOUSDT', 'NEIROETHUSDT', 'NEOUSDT', 'NOTUSDT', 'OMUSDT', 'OMNIUSDT', 'ONDOUSDT',
    'ONEUSDT', 'OPUSDT', 'ORDIUSDT', 'PENDLEUSDT', 'PENGUUSDT', 'PEOPLEUSDT', 'PEPEUSDT', 'PNUTUSDT',
    'POLUSDT', 'POLYXUSDT', 'POPCATUSDT', 'PYTHUSDT', 'QNTUSDT', 'QTUMUSDT', 'RATSUSDT', 'RAYUSDT',
    'RENDERUSDT', 'RONUSDT', 'ROSEUSDT', 'RSRUSDT', 'RUNEUSDT', 'RVNUSDT', 'SUSDT', 'SAGAUSDT',
    'SANDUSDT', 'SATSUSDT', 'SCRUSDT', 'SEIUSDT', 'SHIBUSDT', 'SKLUSDT', 'SLPUSDT', 'SNXUSDT',
    'SOLUSDT', 'SOLVUSDT', 'SONICUSDT', 'SPXUSDT', 'SSVUSDT', 'STORJUSDT', 'STRKUSDT', 'STXUSDT',
    'SUIUSDT', 'SUPERUSDT', 'SUSHIUSDT', 'TAOUSDT', 'THETAUSDT', 'TIAUSDT', 'TNSRUSDT', 'TONUSDT',
    'TRBUSDT', 'TRUMPUSDT', 'TRXUSDT', 'TURBOUSDT', 'UMAUSDT', 'UNIUSDT', 'USTCUSDT', 'USUALUSDT',
    'UXLINKUSDT', 'VANAUSDT', 'VETUSDT', 'VIRTUALUSDT', 'WUSDT', 'WAVESUSDT', 'WIFUSDT', 'WLDUSDT',
    'WOOUSDT', 'XAIUSDT', 'XCHUSDT', 'XLMUSDT', 'XMRUSDT', 'XRPUSDT', 'XTZUSDT', 'YGGUSDT', 'ZECUSDT',
    'ZENUSDT', 'ZEREBROUSDT', 'ZETAUSDT', 'ZILUSDT', 'ZKUSDT', 'ZRCUSDT', 'ZROUSDT', 'ZRXUSDT'
]))

def test_connection():
    try:
        exchange.fetch_ticker('BTCUSDT')
        print(f"{datetime.now()} - اتصال به API بایننس برقراره!")
    except Exception as e:
        print(f"{datetime.now()} - مشکل اتصال: {e}")

def validate_symbols():
    try:
        exchange.load_markets()
        valid_symbols = [s for s in exchange.symbols if 'USDT' in s and 'futures' in exchange.markets[s]['type']]
        return valid_symbols
    except Exception as e:
        print(f"{datetime.now()} - خطا در گرفتن لیست نمادها: {e}")
        return []

def get_futures_symbols():
    valid_symbols = validate_symbols()
    if not valid_symbols:
        print(f"{datetime.now()} - لیست نمادها خالی است. از لیست پیش‌فرض استفاده می‌شود.")
        return FUTURES_SYMBOLS[:200]
    filtered_symbols = [s for s in FUTURES_SYMBOLS if s in valid_symbols]
    print(f"{datetime.now()} - تعداد جفت‌ارزها قبل از فیلتر: {len(FUTURES_SYMBOLS)}, بعد از فیلتر: {len(filtered_symbols)}")
    return filtered_symbols[:200]

def get_live_data(symbol, timeframe=TIMEFRAME, limit=LIMIT):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        return df
    except ccxt.BaseError as e:
        print(f"{datetime.now()} - خطا در گرفتن دیتای {symbol}: {str(e)}")
        return None

def get_order_book(symbol, limit=10):
    try:
        order_book = exchange.fetch_order_book(symbol, limit=limit)
        bids = sum([bid[1] for bid in order_book['bids']])
        asks = sum([ask[1] for ask in order_book['asks']])
        return bids, asks
    except Exception as e:
        print(f"{datetime.now()} - خطا در گرفتن اردر بوک {symbol}: {e}")
        return None, None

def get_trade_delta(symbol, limit=100):
    try:
        trades = exchange.fetch_trades(symbol, limit=limit)
        buy_volume = sum([t['amount'] for t in trades if t['side'] == 'buy'])
        sell_volume = sum([t['amount'] for t in trades if t['side'] == 'sell'])
        delta = buy_volume - sell_volume
        return delta
    except Exception as e:
        print(f"{datetime.now()} - خطا در گرفتن دلتا {symbol}: {e}")
        return None

def find_local_extrema(df, window=WINDOW):
    if df is None or len(df) < window * 2 + 1:
        return df
    df['local_high'] = False
    df['local_low'] = False
    for i in range(window, len(df) - window):
        if df.iloc[i]['high'] == max(df.iloc[i-window:i+window+1]['high']):
            df.loc[df.index[i], 'local_high'] = True
        if df.iloc[i]['low'] == min(df.iloc[i-window:i+window+1]['low']):
            df.loc[df.index[i], 'local_low'] = True
    return df

def check_higher_timeframe_rsi(symbol, timestamp, higher_timeframes=HIGHER_TIMEFRAMES):
    rsi_values = {}
    for timeframe in higher_timeframes:
        try:
            df_higher = get_live_data(symbol, timeframe, limit=50)
            if df_higher is None or df_higher.empty:
                print(f"{datetime.now()} - دیتای {timeframe} برای {symbol} در دسترس نیست")
                continue
            df_higher['rsi'] = ta.momentum.RSIIndicator(df_higher['close'], window=14).rsi()
            closest_idx = df_higher['timestamp'].sub(timestamp).abs().idxmin()
            rsi_value = df_higher.loc[closest_idx, 'rsi']
            rsi_values[timeframe] = rsi_value
            print(f"{datetime.now()} - RSI در {timeframe} برای {symbol}: {rsi_value}")
        except Exception as e:
            print(f"{datetime.now()} - خطا در چک RSI تایم‌فریم {timeframe} برای {symbol}: {e}")
    return rsi_values if rsi_values else None

def calculate_fibo_and_atr(df, div, is_bearish):
    if is_bearish:
        high_idx = div['timestamps'][2]
        high_price = div['prices'][2]
        low_idx = df.iloc[:high_idx]['low'].idxmin()
        low_price = df.loc[low_idx, 'low']
    else:
        low_idx = div['timestamps'][2]
        low_price = div['prices'][2]
        high_idx = df.iloc[:low_idx]['high'].idxmax()
        high_price = df.loc[high_idx, 'high']

    df['atr'] = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'], window=14).average_true_range()
    atr = df['atr'].iloc[-1]

    diff = high_price - low_price
    fibo_786 = high_price - (diff * 0.786) if not is_bearish else low_price + (diff * 0.786)
    fibo_1618 = high_price - (diff * 1.618) if is_bearish else low_price + (diff * 1.618)

    stop = high_price + (ATR_MULTIPLIER * atr) if is_bearish else low_price - (ATR_MULTIPLIER * atr)
    stop = min(stop, high_price + (diff * 0.786)) if is_bearish else max(stop, low_price - (diff * 0.786))

    target = fibo_1618
    return stop, target

def find_all_3_push_divergences(df, symbol, window=WINDOW, min_distance=MIN_DISTANCE, live_window=LIVE_WINDOW):
    if df is None or len(df) < min_distance * 3:
        return [], []
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
    df = find_local_extrema(df, window)

    high_indices = df.index[df['local_high']].tolist()
    low_indices = df.index[df['local_low']].tolist()

    bearish_divergences = []
    bullish_divergences = []

    last_idx = len(df) - 1
    live_threshold = last_idx - live_window

    for i in range(len(high_indices) - 2):
        idx1, idx2, idx3 = high_indices[i], high_indices[i+1], high_indices[i+2]
        if (idx2 - idx1 < min_distance) or (idx3 - idx2 < min_distance) or (idx3 < live_threshold):
            continue
        price1, price2, price3 = df.loc[idx1, 'high'], df.loc[idx2, 'high'], df.loc[idx3, 'high']
        if price1 < price2 < price3:
            rsi1, rsi2, rsi3 = df.loc[idx1, 'rsi'], df.loc[idx2, 'rsi'], df.loc[idx3, 'rsi']
            if rsi1 > 70 and rsi1 > rsi2 > rsi3:
                timestamp = df.iloc[idx3]['timestamp']
                rsi_higher_dict = check_higher_timeframe_rsi(symbol, timestamp)
                if rsi_higher_dict and any(rsi > 65 for rsi in rsi_higher_dict.values()):
                    stop, target = calculate_fibo_and_atr(df, {'timestamps': [idx1, idx2, idx3], 'prices': [price1, price2, price3]}, True)
                    bearish_divergences.append({
                        'timestamps': [idx1, idx2, idx3],
                        'prices': [price1, price2, price3],
                        'rsi_values': [rsi1, rsi2, rsi3],
                        'type': 'bearish',
                        'stop': stop,
                        'target': target
                    })
                    print(f"{datetime.now()} - واگرایی نزولی پیدا شد برای {symbol} در {timestamp} با RSI تایم‌فریم بالاتر: {rsi_higher_dict}")

    for i in range(len(low_indices) - 2):
        idx1, idx2, idx3 = low_indices[i], low_indices[i+1], low_indices[i+2]
        if (idx2 - idx1 < min_distance) or (idx3 - idx2 < min_distance) or (idx3 < live_threshold):
            continue
        price1, price2, price3 = df.loc[idx1, 'low'], df.loc[idx2, 'low'], df.loc[idx3, 'low']
        if price1 > price2 > price3:
            rsi1, rsi2, rsi3 = df.loc[idx1, 'rsi'], df.loc[idx2, 'rsi'], df.loc[idx3, 'rsi']
            if rsi1 < 30 and rsi1 < rsi2 < rsi3:
                timestamp = df.iloc[idx3]['timestamp']
                rsi_higher_dict = check_higher_timeframe_rsi(symbol, timestamp)
                if rsi_higher_dict and any(rsi < 35 for rsi in rsi_higher_dict.values()):
                    stop, target = calculate_fibo_and_atr(df, {'timestamps': [idx1, idx2, idx3], 'prices': [price1, price2, price3]}, False)
                    bullish_divergences.append({
                        'timestamps': [idx1, idx2, idx3],
                        'prices': [price1, price2, price3],
                        'rsi_values': [rsi1, rsi2, rsi3],
                        'type': 'bullish',
                        'stop': stop,
                        'target': target
                    })
                    print(f"{datetime.now()} - واگرایی صعودی پیدا شد برای {symbol} در {timestamp} با RSI تایم‌فریم بالاتر: {rsi_higher_dict}")

    return bearish_divergences, bullish_divergences

def check_imbalance_and_delta(df, symbol, bearish_divs, bullish_divs):
    imbalance_signals = []
    delta_signals = []

    if bearish_divs:
        last_bearish_idx = bearish_divs[-1]['timestamps'][2]
        last_bearish_price = bearish_divs[-1]['prices'][2]
        for i in range(last_bearish_idx + 1, len(df)):
            current_price = df.iloc[i]['high']
            if current_price > last_bearish_price:
                bids, asks = get_order_book(symbol)
                delta = get_trade_delta(symbol)
                timestamp = df.iloc[i]['timestamp']

                if bids and asks and asks / bids > IMBALANCE_THRESHOLD:
                    imbalance_signals.append({
                        'timestamp': timestamp,
                        'price': current_price,
                        'type': 'bearish_imbalance'
                    })
                    print(f"{datetime.now()} - ایمبالنس نزولی برای {symbol} در {timestamp}")

                if delta and delta < -DELTA_THRESHOLD:
                    delta_signals.append({
                        'timestamp': timestamp,
                        'price': current_price,
                        'type': 'bearish_delta'
                    })
                    print(f"{datetime.now()} - دلتا نزولی برای {symbol} در {timestamp}")

    if bullish_divs:
        last_bullish_idx = bullish_divs[-1]['timestamps'][2]
        last_bullish_price = bullish_divs[-1]['prices'][2]
        for i in range(last_bullish_idx + 1, len(df)):
            current_price = df.iloc[i]['low']
            if current_price < last_bullish_price:
                bids, asks = get_order_book(symbol)
                delta = get_trade_delta(symbol)
                timestamp = df.iloc[i]['timestamp']

                if bids and asks and bids / asks > IMBALANCE_THRESHOLD:
                    imbalance_signals.append({
                        'timestamp': timestamp,
                        'price': current_price,
                        'type': 'bullish_imbalance'
                    })
                    print(f"{datetime.now()} - ایمبالنس صعودی برای {symbol} در {timestamp}")

                if delta and delta > DELTA_THRESHOLD:
                    delta_signals.append({
                        'timestamp': timestamp,
                        'price': current_price,
                        'type': 'bullish_delta'
                    })
                    print(f"{datetime.now()} - دلتا صعودی برای {symbol} در {timestamp}")

    return imbalance_signals, delta_signals

def plot_and_save_divergences(df, bearish_divs, bullish_divs, imbalance_signals, delta_signals, symbol, timeframe, filename):
    if df is None or len(df) == 0:
        return
    try:
        fig = go.Figure()

        fig.add_trace(go.Candlestick(
            x=df['timestamp'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name=symbol,
            increasing_line_color='green',
            decreasing_line_color='red',
            line=dict(width=2)
        ))

        # واگرایی نزولی
        for div in bearish_divs:
            timestamp_c = df.loc[div['timestamps'][2], 'timestamp']
            price_c = div['prices'][2]
            stop = div['stop']
            target = div['target']
            idx = div['timestamps'][2]
            x_start = df['timestamp'].iloc[max(0, idx - 5)]  # 5 کندل قبل
            x_end = df['timestamp'].iloc[min(len(df) - 1, idx + 5)]  # 5 کندل بعد

            fig.add_trace(go.Scatter(
                x=[timestamp_c],
                y=[price_c],
                mode='text',
                text=["🐻"],
                textposition="top center",
                textfont=dict(size=22, color="red"),
                showlegend=False
            ))
            # خط استاپ
            fig.add_shape(type="line", x0=x_start, x1=x_end, y0=stop, y1=stop,
                          line=dict(color="red", width=2, dash="dash"))
            fig.add_trace(go.Scatter(
                x=[x_end], y=[stop], mode='text', text=["Stop"],
                textposition="middle right", textfont=dict(size=12, color="red"), showlegend=False
            ))
            # خط تارگت
            fig.add_shape(type="line", x0=x_start, x1=x_end, y0=target, y1=target,
                          line=dict(color="green", width=2, dash="dash"))
            fig.add_trace(go.Scatter(
                x=[x_end], y=[target], mode='text', text=["Target"],
                textposition="middle right", textfont=dict(size=12, color="green"), showlegend=False
            ))

        # واگرایی صعودی
        for div in bullish_divs:
            timestamp_c = df.loc[div['timestamps'][2], 'timestamp']
            price_c = div['prices'][2]
            stop = div['stop']
            target = div['target']
            idx = div['timestamps'][2]
            x_start = df['timestamp'].iloc[max(0, idx - 5)]  # 5 کندل قبل
            x_end = df['timestamp'].iloc[min(len(df) - 1, idx + 5)]  # 5 کندل بعد

            fig.add_trace(go.Scatter(
                x=[timestamp_c],
                y=[price_c],
                mode='text',
                text=["🐮"],
                textposition="top center",
                textfont=dict(size=22, color="green"),
                showlegend=False
            ))
            # خط استاپ
            fig.add_shape(type="line", x0=x_start, x1=x_end, y0=stop, y1=stop,
                          line=dict(color="red", width=2, dash="dash"))
            fig.add_trace(go.Scatter(
                x=[x_end], y=[stop], mode='text', text=["Stop"],
                textposition="middle right", textfont=dict(size=12, color="red"), showlegend=False
            ))
            # خط تارگت
            fig.add_shape(type="line", x0=x_start, x1=x_end, y0=target, y1=target,
                          line=dict(color="green", width=2, dash="dash"))
            fig.add_trace(go.Scatter(
                x=[x_end], y=[target], mode='text', text=["Target"],
                textposition="middle right", textfont=dict(size=12, color="green"), showlegend=False
            ))

        # ایمبالنس
        for signal in imbalance_signals:
            fig.add_trace(go.Scatter(
                x=[signal['timestamp']],
                y=[signal['price']],
                mode='text',
                text=["⚠️"],
                textposition="top center",
                textfont=dict(size=22, color="orange" if signal['type'] == 'bearish_imbalance' else "yellow"),
                showlegend=False
            ))

        # دلتا
        for signal in delta_signals:
            fig.add_trace(go.Scatter(
                x=[signal['timestamp']],
                y=[signal['price']],
                mode='text',
                text=["📉" if signal['type'] == 'bearish_delta' else "📈"],
                textposition="top center",
                textfont=dict(size=22, color="red" if signal['type'] == 'bearish_delta' else "green"),
                showlegend=False
            ))

        fig.update_layout(
            title=f'{symbol} 3-Push Divergences with Imbalance & Delta ({timeframe})',
            yaxis_title='Price',
            height=600,
            template='plotly_white',
            font=dict(family="Courier New", size=12),
            showlegend=False,
            plot_bgcolor='white',
            paper_bgcolor='lightgray',
            xaxis=dict(showline=True, gridcolor='lightgray'),
            yaxis=dict(showline=True, gridcolor='lightgray')
        )

        full_path = os.path.join(OUTPUT_DIR, filename)
        fig.write_image(full_path)
        print(f"{datetime.now()} - فایل {full_path} با موفقیت ذخیره شد.")
    except Exception as e:
        print(f"{datetime.now()} - خطا در ذخیره نمودار برای {symbol}: {e}")

def send_telegram_signal(symbol, timeframe, signal_type, filename):
    full_path = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(full_path):
        message = f"سیگنال {signal_type} برای {symbol} در تایم‌فریم {timeframe}"
        try:
            send_message_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            requests.post(send_message_url, data={
                'chat_id': TELEGRAM_CHAT_ID,
                'text': message
            })

            send_photo_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            with open(full_path, 'rb') as photo:
                requests.post(send_photo_url, data={'chat_id': TELEGRAM_CHAT_ID}, files={'photo': photo})

            os.remove(full_path)
            print(f"{datetime.now()} - سیگنال برای {symbol} با موفقیت ارسال شد.")
        except Exception as e:
            print(f"{datetime.now()} - خطا در ارسال تلگرام برای {symbol}: {e}")
    else:
        print(f"{datetime.now()} - فایل {full_path} برای ارسال وجود ندارد.")

def monitor_symbol(symbol, timeframe=TIMEFRAME, interval=INTERVAL):
    if symbol not in reported_divergences:
        reported_divergences[symbol] = []
    if symbol not in reported_imbalances:
        reported_imbalances[symbol] = []

    while True:
        try:
            df = get_live_data(symbol, timeframe)
            if df is not None and not df.empty:
                bearish_divs, bullish_divs = find_all_3_push_divergences(df, symbol, live_window=LIVE_WINDOW)
                imbalance_signals, delta_signals = check_imbalance_and_delta(df, symbol, bearish_divs, bullish_divs)

                new_bearish = []
                new_bullish = []
                new_imbalance = []
                new_delta = []

                for div in bearish_divs:
                    div_key = (div['timestamps'][2], div['type'])
                    if div_key not in reported_divergences[symbol]:
                        new_bearish.append(div)
                        reported_divergences[symbol].append(div_key)

                for div in bullish_divs:
                    div_key = (div['timestamps'][2], div['type'])
                    if div_key not in reported_divergences[symbol]:
                        new_bullish.append(div)
                        reported_divergences[symbol].append(div_key)

                for signal in imbalance_signals:
                    signal_key = (signal['timestamp'], signal['type'])
                    if signal_key not in reported_imbalances[symbol]:
                        new_imbalance.append(signal)
                        reported_imbalances[symbol].append(signal_key)

                for signal in delta_signals:
                    signal_key = (signal['timestamp'], signal['type'])
                    if signal_key not in reported_imbalances[symbol]:
                        new_delta.append(signal)
                        reported_imbalances[symbol].append(signal_key)

                if new_bearish or new_bullish or new_imbalance or new_delta:
                    filename = f"{symbol.replace('/', '_')}_{timeframe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    plot_and_save_divergences(df, new_bearish, new_bullish, new_imbalance, new_delta, symbol, timeframe, filename)

                    for div in new_bearish:
                        send_telegram_signal(symbol, timeframe, "فروش (واگرایی)", filename)
                    for div in new_bullish:
                        send_telegram_signal(symbol, timeframe, "خرید (واگرایی)", filename)
                    for signal in new_imbalance:
                        send_telegram_signal(symbol, timeframe, "فروش (ایمبالنس)" if signal['type'] == 'bearish_imbalance' else "خرید (ایمبالنس)", filename)
                    for signal in new_delta:
                        send_telegram_signal(symbol, timeframe, "فروش (دلتا)" if signal['type'] == 'bearish_delta' else "خرید (دلتا)", filename)

            time.sleep(interval + random.uniform(0.1, 0.5))
        except Exception as e:
            print(f"{datetime.now()} - خطا در {symbol}: {e}")
            time.sleep(interval)

def main():
    test_connection()
    symbols = get_futures_symbols()
    print(f"{datetime.now()} - تعداد جفت‌ارزهای فیوچرز انتخاب‌شده: {len(symbols)}")
    if not symbols:
        print(f"{datetime.now()} - هیچ جفت‌ارزی پیدا نشد. برنامه متوقف می‌شود.")
        return

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(monitor_symbol, symbol): symbol for symbol in symbols}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"{datetime.now()} - خطا در پردازش موازی: {e}")

if __name__ == "__main__":
    main()
