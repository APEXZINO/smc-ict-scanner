import asyncio
import json
import websockets
import pandas as pd
from datetime import datetime, timedelta
import pytz
import requests
from config import APP_ID, API_TOKEN, PAIRS, TIMEFRAMES, SCAN_INTERVAL, COOLDOWN_PERIOD, TIMEZONE, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from indicators import detect_trend, detect_order_blocks, detect_fvg

# In-memory cooldown tracker
cooldowns = {}

async def get_candles(symbol, granularity, count=100):
    url = f"wss://ws.binaryws.com/websockets/v3?app_id={APP_ID}"
    try:
        async with websockets.connect(url) as websocket:
            request = {
                "ticks_history": symbol,
                "adjust_start_time": 1,
                "count": count,
                "end": "latest",
                "granularity": granularity,
                "style": "candles"
            }
            await websocket.send(json.dumps(request))
            response = await websocket.recv()
            data = json.loads(response)
            if 'candles' in data:
                df = pd.DataFrame(data['candles'])
                df['epoch'] = pd.to_datetime(df['epoch'], unit='s')
                df.set_index('epoch', inplace=True)
                return df
            else:
                print(f"Error fetching candles for {symbol}: {data.get('error', {}).get('message', 'Unknown error')}")
                return None
    except Exception as e:
        print(f"Connection error: {e}")
        return None

def check_cooldown(pair, level):
    key = f"{pair}_{level}"
    if key in cooldowns:
        if datetime.now() < cooldowns[key]:
            return True
    return False

def set_cooldown(pair, level):
    key = f"{pair}_{level}"
    cooldowns[key] = datetime.now() + timedelta(seconds=COOLDOWN_PERIOD)

def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            print(f"Telegram Error: {response.text}")
    except Exception as e:
        print(f"Telegram Exception: {e}")

async def scan_pair(pair):
    print(f"Scanning {pair}...")
    
    # 1. H4 Trend
    h4_data = await get_candles(pair, TIMEFRAMES['H4'])
    if h4_data is None: return
    trend = detect_trend(h4_data)
    
    # 2. H1 OB
    h1_data = await get_candles(pair, TIMEFRAMES['H1'])
    if h1_data is None: return
    obs = detect_order_blocks(h1_data)
    recent_ob = obs[-1] if obs else None
    
    # 3. M15 FVG
    m15_data = await get_candles(pair, TIMEFRAMES['M15'])
    if m15_data is None: return
    fvgs = detect_fvg(m15_data)
    recent_fvg = fvgs[-1] if fvgs else None
    
    # 4. M5 Entry Logic
    m5_data = await get_candles(pair, TIMEFRAMES['M5'])
    if m5_data is None: return
    current_price = m5_data['close'].iloc[-1]
    
    wat = pytz.timezone(TIMEZONE)
    now_wat = datetime.now(wat).strftime('%Y-%m-%d %H:%M:%S')

    if trend == "Bullish" and recent_ob and recent_ob['type'] == 'Bullish OB' and recent_fvg and recent_fvg['type'] == 'Bullish FVG':
        if not check_cooldown(pair, "Entry"):
            # Logic: Entry at FVG top, SL below OB bottom, TP 1:2 RR
            entry = recent_fvg['top']
            sl = recent_ob['bottom']
            risk = entry - sl
            tp = entry + (risk * 2)
            
            msg = f"🚀 *{pair} Bullish Setup Found!*\n\n" \
                  f"🕒 Time: {now_wat} (WAT)\n" \
                  f"📈 H4 Trend: Bullish\n" \
                  f"🧱 H1 OB: {recent_ob['bottom']:.2f} - {recent_ob['top']:.2f}\n" \
                  f"⚡ M15 FVG: {recent_fvg['bottom']:.2f} - {recent_fvg['top']:.2f}\n\n" \
                  f"📥 *Entry Zone:* {entry:.2f}\n" \
                  f"🛑 *Stop Loss:* {sl:.2f}\n" \
                  f"🎯 *Take Profit:* {tp:.2f}\n\n" \
                  f"🎯 Model: H4→H1→M15"
            print(msg)
            send_telegram_message(msg)
            set_cooldown(pair, "Entry")
            
    elif trend == "Bearish" and recent_ob and recent_ob['type'] == 'Bearish OB' and recent_fvg and recent_fvg['type'] == 'Bearish FVG':
        if not check_cooldown(pair, "Entry"):
            # Logic: Entry at FVG bottom, SL above OB top, TP 1:2 RR
            entry = recent_fvg['bottom']
            sl = recent_ob['top']
            risk = sl - entry
            tp = entry - (risk * 2)
            
            msg = f"🔻 *{pair} Bearish Setup Found!*\n\n" \
                  f"🕒 Time: {now_wat} (WAT)\n" \
                  f"📉 H4 Trend: Bearish\n" \
                  f"🧱 H1 OB: {recent_ob['bottom']:.2f} - {recent_ob['top']:.2f}\n" \
                  f"⚡ M15 FVG: {recent_fvg['bottom']:.2f} - {recent_fvg['top']:.2f}\n\n" \
                  f"📥 *Entry Zone:* {entry:.2f}\n" \
                  f"🛑 *Stop Loss:* {sl:.2f}\n" \
                  f"🎯 *Take Profit:* {tp:.2f}\n\n" \
                  f"🎯 Model: H4→H1→M15"
            print(msg)
            send_telegram_message(msg)
            set_cooldown(pair, "Entry")

async def main():
    print("SMC+ICT Scanner Started...")
    while True:
        tasks = [scan_pair(pair) for pair in PAIRS]
        await asyncio.gather(*tasks)
        print(f"Scan complete. Waiting {SCAN_INTERVAL/60} minutes...")
        await asyncio.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())
