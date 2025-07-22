import streamlit as st
import yfinance as yf
import requests
import pandas as pd
from datetime import datetime, time
import pytz
import os

# --- 로컬 캐시 설정 ---
CACHE_DIR = "cache" # 데이터를 저장할 폴더 이름
CACHE_TTL_SECONDS = 15 * 60 # 캐시 유효 시간 (15분)

def load_daily_data(ticker_symbol):
    """
    지정된 티커의 일봉 데이터를 다운로드합니다.
    로컬 캐시를 확인하고, 데이터가 15분 이내의 최신 데이터이면 캐시를 사용합니다.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    file_path = os.path.join(CACHE_DIR, f"{ticker_symbol}.csv")

    if os.path.exists(file_path):
        mod_time = os.path.getmtime(file_path)
        if (datetime.now().timestamp() - mod_time) < CACHE_TTL_SECONDS:
            try:
                return pd.read_csv(file_path, index_col='Date', parse_dates=True)
            except Exception as e:
                print(f"Error loading from cache, refetching: {e}")

    try:
        data = yf.download(ticker_symbol, period='500d', interval='1d')
        if not data.empty:
            data.to_csv(file_path)
        return data
    except Exception as e:
        print(f"Failed to fetch data for {ticker_symbol}: {e}")
        return pd.DataFrame()


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

@st.cache_data(ttl=60) # 1분 캐시
def get_watchlist_data(ticker_list):
    """
    (핵심 재작성) 관심종목 데이터를 가져옵니다. 
    1개 티커와 여러 개 티커의 경우를 명확히 구분하고, Volume을 제외한 필수 데이터만 반환합니다.
    """
    if not ticker_list:
        return pd.DataFrame()
    
    try:
        data = yf.download(tickers=ticker_list, period='2d', progress=False)
        
        if data.empty or len(data) < 2:
            return pd.DataFrame()

        # Case 1: Single Ticker
        if len(ticker_list) == 1:
            ticker = ticker_list[0]
            latest = data.iloc[-1]
            previous = data.iloc[-2]
            
            change = latest['Close'] - previous['Close']
            percent_change = (change / previous['Close']) * 100 if previous['Close'] != 0 else 0
            
            return pd.DataFrame([{
                'Ticker': ticker,
                'Current Price': latest['Close'],
                'Change': change,
                '% Change': percent_change,
            }])

        # Case 2: Multiple Tickers
        else:
            latest = data.iloc[-1]
            previous = data.iloc[-2]
            
            change = latest['Close'] - previous['Close']
            percent_change = (change / previous['Close']) * 100
            
            result = pd.DataFrame({
                'Current Price': latest['Close'],
                'Change': change,
                '% Change': percent_change,
            })
            result = result.reset_index().rename(columns={'Ticker': 'Ticker'})
            return result.dropna(subset=['Current Price'])

    except Exception as e:
        print(f"Error in get_watchlist_data: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300) # 5분 캐시
def get_fear_and_greed_index():
    """CNN Fear and Greed 지수를 API를 통해 가져옵니다."""
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9,ko;q=0.8',
            'Origin': 'https://www.cnn.com',
            'Referer': 'https://www.cnn.com/markets/fear-and-greed',
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        score = int(data['fear_and_greed']['score'])
        rating = data['fear_and_greed']['rating'].capitalize()
        return f"{score}", rating
    except Exception as e:
        print("--- Fear & Greed Index Error ---")
        print(e)
        print("---------------------------------")
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
