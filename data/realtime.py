import yfinance as yf
import pandas as pd

def get_realtime_price(ticker):
    """
    yfinance를 이용해 프리마켓/애프터마켓 포함 최신 가격을 반환합니다.
    우선 fast_info['last_price']를 시도, 실패시 1분봉 마지막값 사용.
    """
    try:
        t = yf.Ticker(ticker)
        # fast_info가 있으면 사용
        if hasattr(t, 'fast_info') and 'last_price' in t.fast_info:
            return float(t.fast_info['last_price'])
        # fallback: 1분봉 데이터의 마지막 Close
        hist = t.history(period='1d', interval='1m')
        if not hist.empty:
            return float(hist['Close'].iloc[-1])
    except Exception:
        pass
    return None
