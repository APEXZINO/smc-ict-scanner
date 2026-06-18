import pandas as pd
import numpy as np

def detect_trend(df, period=14):
    """Simple trend detection using EMA."""
    df['ema'] = df['close'].ewm(span=period, adjust=False).mean()
    if df['close'].iloc[-1] > df['ema'].iloc[-1]:
        return "Bullish"
    else:
        return "Bearish"

def detect_order_blocks(df, lookback=50):
    """Detects Order Blocks (OB)."""
    obs = []
    for i in range(len(df) - lookback, len(df) - 1):
        # Bullish OB: Last down candle before an impulsive move up
        if df['close'].iloc[i] < df['open'].iloc[i] and df['close'].iloc[i+1] > df['open'].iloc[i+1]:
            if (df['close'].iloc[i+1] - df['open'].iloc[i+1]) > (df['open'].iloc[i] - df['close'].iloc[i]) * 2:
                obs.append({
                    'type': 'Bullish OB',
                    'top': df['open'].iloc[i],
                    'bottom': df['low'].iloc[i],
                    'time': df.index[i]
                })
        # Bearish OB: Last up candle before an impulsive move down
        elif df['close'].iloc[i] > df['open'].iloc[i] and df['close'].iloc[i+1] < df['open'].iloc[i+1]:
            if (df['open'].iloc[i+1] - df['close'].iloc[i+1]) > (df['close'].iloc[i] - df['open'].iloc[i]) * 2:
                obs.append({
                    'type': 'Bearish OB',
                    'top': df['high'].iloc[i],
                    'bottom': df['open'].iloc[i],
                    'time': df.index[i]
                })
    return obs

def detect_fvg(df, lookback=20):
    """Detects Fair Value Gaps (FVG)."""
    fvgs = []
    for i in range(len(df) - lookback, len(df) - 2):
        # Bullish FVG: Gap between High of Candle 1 and Low of Candle 3
        if df['high'].iloc[i] < df['low'].iloc[i+2]:
            fvgs.append({
                'type': 'Bullish FVG',
                'top': df['low'].iloc[i+2],
                'bottom': df['high'].iloc[i],
                'time': df.index[i+1]
            })
        # Bearish FVG: Gap between Low of Candle 1 and High of Candle 3
        elif df['low'].iloc[i] > df['high'].iloc[i+2]:
            fvgs.append({
                'type': 'Bearish FVG',
                'top': df['low'].iloc[i],
                'bottom': df['high'].iloc[i+2],
                'time': df.index[i+1]
            })
    return fvgs
