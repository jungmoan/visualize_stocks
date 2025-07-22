import streamlit as st
from data import fetcher
from datetime import time

def display():
    """메인 화면 상단의 주요 지수 및 시장 현황 메트릭을 표시합니다."""
    
    # 8개의 컬럼을 생성합니다.
    cols = st.columns(8)

    with cols[0]:
        us_status, us_time = fetcher.get_market_status('America/New_York', time(9, 30), time(16, 0))
        st.metric(label="🇺🇸 미국 (ET)", value=us_status, delta=us_time)

    with cols[1]:
        kr_status, kr_time = fetcher.get_market_status('Asia/Seoul', time(9, 0), time(15, 30))
        st.metric(label="🇰🇷 한국 (KST)", value=kr_status, delta=kr_time)

    with cols[2]:
        sp500_price, sp500_delta = fetcher.get_index_data('^GSPC')
        if sp500_price is not None:
            st.metric(label="S&P 500", value=f"{sp500_price:,.2f}", delta=f"{sp500_delta:,.2f}")
        else:
            st.metric(label="S&P 500", value="N/A")

    with cols[3]:
        nasdaq_price, nasdaq_delta = fetcher.get_index_data('^IXIC')
        if nasdaq_price is not None:
            st.metric(label="나스닥", value=f"{nasdaq_price:,.2f}", delta=f"{nasdaq_delta:,.2f}")
        else:
            st.metric(label="나스닥", value="N/A")

    with cols[4]:
        # 코스피 200(^KS200)에서 코스피 종합(^KS11)으로 변경
        kospi_price, kospi_delta = fetcher.get_index_data('^KS11')
        if kospi_price is not None:
            st.metric(label="코스피", value=f"{kospi_price:,.2f}", delta=f"{kospi_delta:,.2f}")
        else:
            st.metric(label="코스피", value="N/A")

    with cols[5]:
        usd_krw_price, usd_krw_delta = fetcher.get_index_data('USDKRW=X')
        if usd_krw_price is not None:
            st.metric(label="USD/KRW", value=f"{usd_krw_price:,.2f}", delta=f"{usd_krw_delta:,.2f}")
        else:
            st.metric(label="USD/KRW", value="N/A")

    with cols[6]:
        fear_and_greed, rating = fetcher.get_fear_and_greed_index()
        st.metric(label="Fear & Greed", value=fear_and_greed, delta=rating)

    with cols[7]:
        vix_price, vix_delta = fetcher.get_index_data('^VIX')
        if vix_price is not None:
            st.metric(label="VIX", value=f"{vix_price:.2f}", delta=f"{vix_delta:.2f}")
        else:
            st.metric(label="VIX", value="N/A")
