import streamlit as st
import pandas as pd
import mplfinance as mpf
from streamlit_autorefresh import st_autorefresh

# 프로젝트 모듈 임포트
from ui import sidebar, header
from data import fetcher
from core import calculator, charting
from utils import settings
import auth  # 인증 모듈 추가


# --- 페이지 기본 설정 ---
st.set_page_config(layout="wide", page_title="주식 대시보드 🔐")

# 메트릭 폰트 크기 조정을 위한 CSS
st.markdown("""
<style>
[data-testid="stMetricValue"] {
    font-size: 24px;
}
</style>
""", unsafe_allow_html=True)

# --- 인증 확인 ---
# 인증이 완료된 경우에만 앱의 나머지 부분을 실행합니다
if not auth.render_authentication_ui():
    st.stop()

# --- 자동 새로고침 설정 (10초마다) ---
# 인증 후에만 자동 새로고침 활성화
st_autorefresh(interval=10 * 1000, key="data_refresher")

# --- 세션 상태 초기화 ---
# 앱이 처음 실행될 때만 스타일 설정을 로드합니다.
if 'ma_styles' not in st.session_state:
    st.session_state.ma_styles = settings.load_styles()

def main():
    """메인 애플리케이션 함수"""
    
    # 1. 사이드바 UI 표시 및 사용자 입력 받기
    user_inputs = sidebar.display()
    ticker = user_inputs['ticker']

    # 2. 헤더 UI (주요 지수) 표시
    header.display()

    # 3. 메인 타이틀 및 주식 정보 가져오기
    stock_info = fetcher.get_stock_info(ticker)
    company_name = stock_info.get('longName', stock_info.get('shortName', ticker))
    currency = stock_info.get('currency', 'USD') # 정보가 없을 경우 기본값 USD

    if company_name and company_name.lower() != ticker.lower():
        st.title(f'{company_name} ({ticker})')
    else:
        st.title(f'{ticker}')
    st.divider()

    # 4. 데이터 로드 및 차트 생성 (앱 전체가 10초마다 자동 새로고침)
    try:
        with st.spinner('데이터를 불러오는 중입니다...'):
            data = fetcher.load_daily_data(ticker)

        if data.empty:
            st.error(f"'{ticker}'에 대한 데이터를 찾을 수 없습니다. Ticker를 확인해주세요.")
            return

        # 데이터 클리닝
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            data = data.loc[:,~data.columns.duplicated()]

        # 보조지표 계산
        df_with_indicators = calculator.calculate_all_indicators(data, user_inputs)

        # 차트 생성 (currency 정보 전달)
        fig, axes = charting.create_stock_chart(df_with_indicators, user_inputs, company_name, currency)        
        # Streamlit에 차트 표시
        st.pyplot(fig)

        # 데이터 테이블 표시
        st.subheader('최근 10일 데이터')
        display_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        for ma in user_inputs['selected_ma_periods']:
            if ma.startswith('EMA'):
                period = int(ma.replace('EMA', ''))
                display_cols.append(f'EMA_{period}')
            else:
                period = int(ma.replace('MA', ''))
                display_cols.append(f'MA_{period}')
        chart_data = df_with_indicators.tail(200)
        st.dataframe(chart_data.tail(10)[display_cols].style.format("{:.2f}"))
    except Exception as e:
        st.error("차트를 그리거나 데이터를 처리하는 중 오류가 발생했습니다.")
        st.exception(e)

if __name__ == "__main__":
    main()
