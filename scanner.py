import asyncio
import json
import websockets
import pandas as pd
from datetime import datetime, timedelta
import pytz
from config import APP_ID, API_TOKEN, PAIRS, TIMEFRAMES, SCAN_INTERVAL, COOLDOWN_PERIOD, TIMEZONE
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
    
    wat = pytz.timezone(TIMEZONE)
    now_wat = datetime.now(wat).strftime('%Y-%m-%d %H:%M:%S')

    if trend == "Bullish" and recent_ob and recent_ob['type'] == 'Bullish OB' and recent_fvg and recent_fvg['type'] == 'Bullish FVG':
        if not check_cooldown(pair, "Entry"):
            print(f"[{now_wat}] ALERT: {pair} Bullish Setup Found! (H4 Trend Up + H1 Bull OB + M15 Bull FVG)")
            set_cooldown(pair, "Entry")
            
    elif trend == "Bearish" and recent_ob and recent_ob['type'] == 'Bearish OB' and recent_fvg and recent_fvg['type'] == 'Bearish FVG':
        if not check_cooldown(pair, "Entry"):
            print(f"[{now_wat}] ALERT: {pair} Bearish Setup Found! (H4 Trend Down + H1 Bear OB + M15 Bear FVG)")
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
