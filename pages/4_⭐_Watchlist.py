import streamlit as st
import pandas as pd
import os
from data import fetcher
import auth  # 인증 모듈 추가

# --- 페이지 기본 설정 ---
st.set_page_config(layout="wide", page_title="관심종목")

# --- 인증 확인 ---
if not auth.render_authentication_ui():
    st.stop()

st.title("⭐ 관심종목 대시보드")
st.write("포트폴리오 종목과 직접 추가한 관심종목의 최신 시세를 확인하세요.")

# --- 상수 정의 ---
ASSET_FILE_PATH = "private/asset.csv"
WATCHLIST_FILE_PATH = "private/watchlist.csv"

# --- 데이터 관리 함수 ---
def load_tickers_from_file(file_path):
    """지정된 CSV 파일에서 ticker 목록을 불러옵니다."""
    if not os.path.exists(file_path):
        return []
    try:
        df = pd.read_csv(file_path, dtype={'ticker': str})
        if 'ticker' in df.columns:
            return df['ticker'].dropna().unique().tolist()
        return []
    except (pd.errors.EmptyDataError, KeyError):
        return []

def save_manual_watchlist_to_file(df, asset_tickers):
    """포트폴리오 종목을 제외한, 수동으로 추가/삭제된 관심종목만 저장합니다."""
    os.makedirs(os.path.dirname(WATCHLIST_FILE_PATH), exist_ok=True)
    
    # 편집된 전체 리스트에서 포트폴리오 종목을 제외하여 순수 관심종목만 추출
    manual_tickers = df[~df['ticker'].isin(asset_tickers)]
    
    manual_tickers[['ticker']].dropna(subset=['ticker']).drop_duplicates().to_csv(WATCHLIST_FILE_PATH, index=False)

# --- 데이터 로딩 ---
# 1. 포트폴리오와 관심종목 파일에서 각각 티커를 불러옵니다.
asset_tickers = load_tickers_from_file(ASSET_FILE_PATH)
manual_tickers = load_tickers_from_file(WATCHLIST_FILE_PATH)

# 2. 두 리스트를 합치고 중복을 제거하여 전체 관심종목 리스트를 생성합니다.
combined_tickers = sorted(list(set(asset_tickers + manual_tickers)))
display_df = pd.DataFrame({"ticker": combined_tickers})


# --- UI: 관심종목 편집기 ---
with st.expander("✏️ 관심종목 편집하기 (포트폴리오 종목은 자동 포함됩니다)"):
    edited_watchlist = st.data_editor(
        display_df, # 포트폴리오가 포함된 전체 목록을 편집
        num_rows="dynamic",
        use_container_width=True,
        column_config={"ticker": st.column_config.TextColumn("Ticker", required=True)}
    )
    if st.button("💾 변경 사항 저장", use_container_width=True, type="primary"):
        save_manual_watchlist_to_file(edited_watchlist, asset_tickers)
        st.toast("관심종목이 저장되었습니다!", icon="🎉")
        # 저장이 성공하면 페이지를 다시 실행하여 최신 상태를 반영
        st.rerun()

st.divider()

# --- 데이터 처리 및 시세 표시 (구역별로 분리) ---
# 편집기에서 실시간으로 변경된 내용을 반영
all_watchlist_tickers = edited_watchlist['ticker'].dropna().unique().tolist()

# 관심종목과 포트폴리오 종목을 분리
pure_watchlist_tickers = [t for t in all_watchlist_tickers if t not in asset_tickers]
portfolio_tickers = [t for t in all_watchlist_tickers if t in asset_tickers]

def display_ticker_section(tickers, title, icon):
    """티커 목록에 대한 섹션을 표시하는 함수"""
    if not tickers:
        st.info(f"{title}에 종목이 없습니다.")
        return
    
    st.subheader(f"{icon} {title}")
    with st.spinner(f"{title} 데이터를 불러오는 중입니다..."):
        data = fetcher.get_watchlist_data(tickers)
        
        if data.empty:
            st.warning("데이터를 불러오지 못했습니다. 티커를 확인해주세요.")
            return
        
        # 데이터 정제
        for col in ['Current Price', 'Change', '% Change']:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0)
        
        # 메트릭 뷰
        num_cols = min(len(data), 4)
        cols = st.columns(num_cols)
        for i, row in data.iterrows():
            with cols[i % num_cols]:
                change_val = row.get('Change', 0)
                price_val = row.get('Current Price', 0)
                percent_val = row.get('% Change', 0)
                
                delta_color = "normal" if change_val != 0 else "off"
                
                st.metric(
                    label=row['Ticker'],
                    value=f"{price_val:,.2f}",
                    delta=f"{change_val:,.2f} ({percent_val:.2f}%)",
                    delta_color=delta_color
                )
        
        # 테이블 뷰
        display_table_df = data.set_index('Ticker')
        
        def style_change(val):
            return 'color: red' if val < 0 else 'color: green' if val > 0 else 'color: gray'

        format_mapping = {
            'Current Price': '{:,.2f}',
            'Change': '{:+,.2f}',
            '% Change': '{:+.2f}%'
        }
        
        st.dataframe(
            display_table_df.style.format(format_mapping).map(style_change, subset=['Change', '% Change']),
            use_container_width=True
        )

# 1. 관심종목 구간
display_ticker_section(pure_watchlist_tickers, "관심종목", "⭐")

if pure_watchlist_tickers and portfolio_tickers:
    st.divider()

# 2. 포트폴리오 보유종목 구간  
display_ticker_section(portfolio_tickers, "포트폴리오 보유종목", "💼")

if not pure_watchlist_tickers and not portfolio_tickers:
    st.info("포트폴리오에 종목을 추가하거나, 위의 편집기에서 관심종목을 추가하고 저장해주세요.")
