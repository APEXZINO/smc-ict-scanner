import asyncio
import json
import websockets
import pandas as pd
from datetime import datetime, timedelta
import pytz
import requests
from config import APP_ID, API_TOKEN, PAIRS, TIMEFRAMES, SCAN_INTERVAL, COOLDOWN_PERIOD, TIMEZONE, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from indicators import detect_trend, detect_order_blocks, detect_fvg

# Note: Cooldowns won't persist between GitHub Action runs without a database, 
# but the scanner will now complete each run in seconds.

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
            return None
    except Exception as e:
        print(f"Connection error: {e}")
        return None

def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except: pass

async def scan_pair(pair):
    print(f"Scanning {pair}...")
    h4_data = await get_candles(pair, TIMEFRAMES['H4'])
    h1_data = await get_candles(pair, TIMEFRAMES['H1'])
    m15_data = await get_candles(pair, TIMEFRAMES['M15'])
    
    if h4_data is None or h1_data is None or m15_data is None: return

    trend = detect_trend(h4_data)
    obs = detect_order_blocks(h1_data)
    fvgs = detect_fvg(m15_data)
    
    recent_ob = obs[-1] if obs else None
    recent_fvg = fvgs[-1] if fvgs else None
    
    wat = pytz.timezone(TIMEZONE)
    now_wat = datetime.now(wat).strftime('%Y-%m-%d %H:%M:%S')

    if trend == "Bullish" and recent_ob and recent_ob['type'] == 'Bullish OB' and recent_fvg and recent_fvg['type'] == 'Bullish FVG':
        entry = recent_fvg['top']
        sl = recent_ob['bottom']
        tp = entry + ((entry - sl) * 2)
        msg = f"🚀 *{pair} Bullish Setup Found!*\n\n🕒 {now_wat} (WAT)\n📥 Entry: {entry:.2f}\n🛑 SL: {sl:.2f}\n🎯 TP: {tp:.2f}"
        send_telegram_message(msg)
            
    elif trend == "Bearish" and recent_ob and recent_ob['type'] == 'Bearish OB' and recent_fvg and recent_fvg['type'] == 'Bearish FVG':
        entry = recent_fvg['bottom']
        sl = recent_ob['top']
        tp = entry - ((sl - entry) * 2)
        msg = f"🔻 *{pair} Bearish Setup Found!*\n\n🕒 {now_wat} (WAT)\n📥 Entry: {entry:.2f}\n🛑 SL: {sl:.2f}\n🎯 TP: {tp:.2f}"
        send_telegram_message(msg)

async def main():
    print("SMC+ICT Scanner Starting...")
    tasks = [scan_pair(pair) for pair in PAIRS]
    await asyncio.gather(*tasks)
    print("Scan complete. Exiting.")

if __name__ == "__main__":
    asyncio.run(main())
    
