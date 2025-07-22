import streamlit as st
import pandas as pd
import os
from data import fetcher

# --- 페이지 기본 설정 ---
st.set_page_config(layout="wide", page_title="관심종목")
st.title("⭐ 관심종목 대시보드")
st.write("관심종목을 등록하고 최신 시세를 확인하세요.")

# --- 상수 정의 ---
WATCHLIST_FILE_PATH = "private/watchlist.csv"
os.makedirs("private", exist_ok=True)
# --- 데이터 관리 함수 ---
def load_watchlist_from_file():
    """CSV 파일에서 관심종목을 불러옵니다. ticker 컬럼은 항상 문자열로 불러옵니다."""
    if not os.path.exists(WATCHLIST_FILE_PATH):
        return pd.DataFrame({"ticker": ["AAPL", "MSFT", "005930.KS"]})
    try:
        df = pd.read_csv(WATCHLIST_FILE_PATH, dtype={'ticker': str})
        return df if not df.empty else pd.DataFrame({"ticker": []})
    except pd.errors.EmptyDataError:
        return pd.DataFrame({"ticker": []})

def save_watchlist_to_file(df):
    """데이터프레임을 CSV 파일로 저장합니다."""
    os.makedirs(os.path.dirname(WATCHLIST_FILE_PATH), exist_ok=True)
    df[['ticker']].dropna(subset=['ticker']).drop_duplicates().to_csv(WATCHLIST_FILE_PATH, index=False)

# --- 세션 상태 초기화 ---
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_watchlist_from_file()

# --- UI: 관심종목 편집기 ---
with st.expander("✏️ 관심종목 편집하기"):
    edited_watchlist = st.data_editor(
        st.session_state.watchlist,
        num_rows="dynamic",
        use_container_width=True,
        column_config={"ticker": st.column_config.TextColumn("Ticker", required=True)}
    )
    if st.button("💾 관심종목 저장", use_container_width=True, type="primary"):
        save_watchlist_to_file(edited_watchlist)
        st.session_state.watchlist = edited_watchlist
        st.toast("관심종목이 저장되었습니다!", icon="🎉")

st.divider()

# --- 데이터 처리 및 시세 표시 ---
watchlist_tickers = st.session_state.watchlist['ticker'].dropna().unique().tolist()

if not watchlist_tickers:
    st.info("위의 '관심종목 편집하기'에서 티커를 추가하고 저장해주세요.")
else:
    st.subheader("📈 실시간 시세")
    with st.spinner("관심종목의 최신 데이터를 불러오는 중입니다..."):
        watchlist_data = fetcher.get_watchlist_data(watchlist_tickers)

        if watchlist_data.empty:
            st.warning("데이터를 불러오지 못했습니다. 티커를 확인해주세요.")
        else:
            # 데이터 표시 전, 데이터프레임 전체를 먼저 정제합니다
            for col in ['Current Price', 'Change', '% Change']:
                if col in watchlist_data.columns:
                    watchlist_data[col] = pd.to_numeric(watchlist_data[col], errors='coerce').fillna(0)
            
            # 메트릭 뷰 표시
            num_cols = min(len(watchlist_data), 4)
            cols = st.columns(num_cols)
            for i, row in watchlist_data.iterrows():
                with cols[i % num_cols]:
                    change_val = row.get('Change', 0)
                    price_val = row.get('Current Price', 0)
                    percent_val = row.get('% Change', 0)
                    
                    # --- (핵심 수정) 등락에 따라 색상 결정 ---
                    # st.metric의 delta_color="normal"은 상승은 초록, 하락은 빨강으로 자동 표시합니다.
                    # 등락이 없을 때만 회색으로 표시되도록 "off"로 설정합니다.
                    if change_val == 0:
                        delta_color = "off"
                    else:
                        delta_color = "normal"
                    
                    st.metric(
                        label=row['Ticker'],
                        value=f"{price_val:,.2f}",
                        delta=f"{change_val:,.2f} ({percent_val:.2f}%)",
                        delta_color=delta_color
                    )
            
            st.divider()

            # 테이블 뷰 표시
            display_df = watchlist_data.set_index('Ticker')
            
            def style_change(val):
                return 'color: red' if val < 0 else 'color: green' if val > 0 else 'color: gray'

            # 포맷 매핑에서 공백 제거
            format_mapping = {
                'Current Price': '{:,.2f}',
                'Change': '{:+,.2f}',
                '% Change': '{:+.2f}%'
            }
            
            st.dataframe(
                display_df.style.format(format_mapping).map(style_change, subset=['Change', '% Change']),
                use_container_width=True
            )
