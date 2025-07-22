import streamlit as st
import yfinance as yf
import requests
import pandas as pd
from datetime import datetime, time
import pytz

@st.cache_data(ttl=3600)
def load_daily_data(ticker_symbol):
    """지정된 티커의 일봉 데이터를 다운로드합니다."""
    return yf.download(ticker_symbol, period='500d', interval='1d')

@st.cache_data(ttl=60) # 1분 캐시
def get_current_prices(ticker_list):
    """여러 티커의 최신 가격을 한 번에 가져옵니다."""
    if not ticker_list:
        return pd.Series(dtype=float)
    try:
        data = yf.download(tickers=ticker_list, period='2d', progress=False)
        if data.empty or 'Close' not in data:
            return pd.Series(dtype=float)
        
        if isinstance(data.columns, pd.MultiIndex):
            latest_prices = data['Close'].iloc[-1]
        else:
            latest_prices = data['Close'].iloc[-1] if not data.empty else None
            return pd.Series({ticker_list[0]: latest_prices})
            
        return latest_prices
    except Exception:
        return pd.Series(dtype=float)


@st.cache_data(ttl=300) # 5분 캐시
def get_fear_and_greed_index():
    """CNN Fear and Greed 지수를 API를 통해 가져옵니다."""
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        # --- (핵심 수정) 차단을 우회하기 위해 더 많은 브라우저 헤더 정보 추가 ---
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9,ko;q=0.8',
            'Origin': 'https://www.cnn.com',
            'Referer': 'https://www.cnn.com/markets/fear-and-greed',
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() # 오류가 있으면 여기서 예외 발생
        data = response.json()
        score = int(data['fear_and_greed']['score'])
        rating = data['fear_and_greed']['rating'].capitalize()
        return f"{score}", rating
    except Exception as e:
        # 오류 발생 시 콘솔에 에러 메시지 출력
        print("--- Fear & Greed Index Error ---")
        print(e)
        print("---------------------------------")
        # UI에는 간략한 메시지 표시
        st.error("F&G 지수 로딩 실패. 콘솔을 확인하세요.")
        return "N/A", "Error"

@st.cache_data(ttl=60) # 1분 캐시
def get_index_data(ticker_symbol):
    """지정된 티커의 최신 값과 변화량을 가져옵니다."""
    try:
        data = yf.Ticker(ticker_symbol).history(period='2d')
        if len(data) < 2: return None, None
        latest_price = data['Close'].iloc[-1]
        previous_price = data['Close'].iloc[-2]
        delta = latest_price - previous_price
        return latest_price, delta
    except Exception:
        return None, None

@st.cache_data(ttl=3600)
def get_stock_info(ticker_symbol):
    """yf.Ticker.info에서 주식 정보를 딕셔너리로 가져옵니다."""
    try:
        return yf.Ticker(ticker_symbol).info
    except Exception:
        return {}

@st.cache_data(ttl=3600)
def get_company_name(ticker_symbol):
    """get_stock_info를 사용해 회사 이름을 가져옵니다."""
    info = get_stock_info(ticker_symbol)
    name = info.get('longName', info.get('shortName'))
    return name if name else ticker_symbol

@st.cache_data(ttl=60)
def get_market_status(timezone_str, open_time, close_time):
    """지정된 시간대의 시장 개장 여부와 현지 시간을 반환합니다."""
    try:
        tz = pytz.timezone(timezone_str)
        now = datetime.now(tz)
        is_weekday = now.weekday() < 5
        is_trading_hours = open_time <= now.time() < close_time
        status = "🟢 Open" if is_weekday and is_trading_hours else "🔴 Closed"
        return status, now.strftime('%H:%M')
    except Exception:
        return "Error", "N/A"
