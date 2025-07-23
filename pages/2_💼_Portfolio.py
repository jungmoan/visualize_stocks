import streamlit as st
import pandas as pd
import plotly.express as px
import os
from data import fetcher # 데이터 모듈 임포트

st.set_page_config(layout="wide", page_title="내 포트폴리오")

st.title("💼 내 포트폴리오")
st.write("주식, 원자재, 현금 등 전체 자산 현황을 분류하고 분석합니다.")
st.divider()

# --- 파일 경로 설정 ---
ASSET_FILE_PATH = "private/asset.csv"
COMMODITIES_FILE_PATH = "private/commodities.csv"
CASH_FILE_PATH = "private/cash.csv"

# --- 데이터 로딩 함수 ---
def load_assets(file_path, sample_data):
    """지정된 경로의 자산 파일을 불러옵니다."""
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
    else:
        df = pd.DataFrame(sample_data)
    return df

# --- 세션 상태 초기화 ---
# 주식 포트폴리오 로딩
if 'stock_portfolio_df' not in st.session_state:
    sample_stocks = {
        "ticker": ["AAPL", "SCHD", "SGOV"], "수량": [10.0, 50.0, 100.0],
        "평균매입금액": [180.50, 75.00, 100.10], "카테고리": ["성장주", "배당주", "채권"]
    }
    st.session_state.stock_portfolio_df = load_assets(ASSET_FILE_PATH, sample_stocks)
    if '카테고리' not in st.session_state.stock_portfolio_df.columns:
        st.session_state.stock_portfolio_df['카테고리'] = '성장주'

# 원자재 포트폴리오 로딩
if 'commodity_portfolio_df' not in st.session_state:
    sample_commodities = {
        "자산명": ["Gold"], "수량": [10.0], "평균매입금액": [85000.00], "현재가": [90000.00]
    }
    st.session_state.commodity_portfolio_df = load_assets(COMMODITIES_FILE_PATH, sample_commodities)

# 현금 포트폴리오 로딩
if 'cash_portfolio_df' not in st.session_state:
    sample_cash = {"통화": ["KRW", "USD"], "금액": [1000000.0, 5000.0]}
    st.session_state.cash_portfolio_df = load_assets(CASH_FILE_PATH, sample_cash)


# --- 통화 선택 및 환율 정보 ---
col1, col2 = st.columns([3, 1])
with col1:
    display_currency = st.radio(
        "통합 표시 통화 선택", ["원화 (KRW)", "달러 (USD)"], horizontal=True, label_visibility="collapsed"
    )
with col2:
    usd_krw_rate, _ = fetcher.get_index_data('USDKRW=X')
    if usd_krw_rate:
        st.metric("현재 환율 (USD/KRW)", f"{usd_krw_rate:,.2f}")
    else:
        st.error("환율 정보를 가져올 수 없습니다.")

# --- 데이터 편집기 ---
with st.expander("✏️ 주식 포트폴리오 편집하기"):
    edited_stocks_df = st.data_editor(
        st.session_state.stock_portfolio_df, num_rows="dynamic", use_container_width=True,
        column_config={
            "ticker": st.column_config.TextColumn("Ticker", required=True),
            "수량": st.column_config.NumberColumn("수량", format="%.4f", required=True),
            "평균매입금액": st.column_config.NumberColumn("평균매입금액", format="%.2f", required=True),
            "카테고리": st.column_config.SelectboxColumn("자산 종류", options=["성장주", "배당주", "채권"], required=True)
        }
    )
    if st.button("💾 주식 저장", use_container_width=True):
        edited_stocks_df.to_csv(ASSET_FILE_PATH, index=False)
        st.session_state.stock_portfolio_df = edited_stocks_df
        st.toast("주식 포트폴리오가 저장되었습니다!", icon="📈")

with st.expander("✏️ 원자재 자산 편집하기 (KRW 기준)"):
    edited_commodities_df = st.data_editor(
        st.session_state.commodity_portfolio_df, num_rows="dynamic", use_container_width=True,
        column_config={
            "자산명": st.column_config.TextColumn("자산명", required=True),
            "수량": st.column_config.NumberColumn("수량", format="%.4f", required=True),
            "평균매입금액": st.column_config.NumberColumn("평균매입금액 (KRW)", format="%.0f", required=True),
            "현재가": st.column_config.NumberColumn("현재가 (KRW)", format="%.0f", required=True)
        }
    )
    if st.button("💾 원자재 저장", use_container_width=True):
        edited_commodities_df.to_csv(COMMODITIES_FILE_PATH, index=False)
        st.session_state.commodity_portfolio_df = edited_commodities_df
        st.toast("원자재 포트폴리오가 저장되었습니다!", icon="💰")

with st.expander("✏️ 현금 자산 편집하기"):
    edited_cash_df = st.data_editor(
        st.session_state.cash_portfolio_df, num_rows="dynamic", use_container_width=True,
        column_config={
            "통화": st.column_config.SelectboxColumn("통화", options=["KRW", "USD"], required=True),
            "금액": st.column_config.NumberColumn("금액", format="%.2f", required=True)
        }
    )
    if st.button("💾 현금 저장", use_container_width=True):
        edited_cash_df.to_csv(CASH_FILE_PATH, index=False)
        st.session_state.cash_portfolio_df = edited_cash_df
        st.toast("현금 포트폴리오가 저장되었습니다!", icon="💵")


# --- 포트폴리오 분석 ---
if usd_krw_rate:
    # 1. 주식 데이터 처리
    stocks_df = edited_stocks_df.copy()
    stocks_df.dropna(subset=["ticker", "수량", "평균매입금액", "카테고리"], inplace=True)
    stocks_df['총매입금액'] = pd.to_numeric(stocks_df['수량']) * pd.to_numeric(stocks_df['평균매입금액'])
    agg_stocks = stocks_df.groupby('ticker').agg(
        수량=('수량', 'sum'), 총매입금액=('총매입금액', 'sum'), 카테고리=('카테고리', 'first')
    ).reset_index()
    
    tickers = agg_stocks["ticker"].tolist()
    current_prices = fetcher.get_current_prices(tickers)
    agg_stocks['현재가'] = agg_stocks['ticker'].map(current_prices).fillna(0)
    agg_stocks['평가금액_원본'] = agg_stocks['수량'] * agg_stocks['현재가']
    agg_stocks['currency'] = agg_stocks['ticker'].apply(lambda x: 'KRW' if '.KS' in x.upper() else 'USD')

    # 2. 원자재 데이터 처리
    commodities_df = edited_commodities_df.copy()
    commodities_df.dropna(subset=["자산명", "수량", "평균매입금액", "현재가"], inplace=True)
    commodities_df.rename(columns={'자산명': 'ticker'}, inplace=True)
    commodities_df['카테고리'] = '금/원자재'
    commodities_df['currency'] = 'KRW'
    commodities_df['총매입금액'] = pd.to_numeric(commodities_df['수량']) * pd.to_numeric(commodities_df['평균매입금액'])
    commodities_df['평가금액_원본'] = pd.to_numeric(commodities_df['수량']) * pd.to_numeric(commodities_df['현재가'])
    
    # 3. 현금 데이터 처리
    cash_df = edited_cash_df.copy()
    cash_df.dropna(subset=["통화", "금액"], inplace=True)
    cash_df['ticker'] = cash_df['통화'].apply(lambda x: f"{x} 현금")
    cash_df['카테고리'] = '현금'
    cash_df.rename(columns={'통화': 'currency', '금액': '총매입금액'}, inplace=True)
    cash_df['평가금액_원본'] = cash_df['총매입금액'] # 현금의 가치는 변하지 않음

    # 4. 데이터 통합
    final_portfolio = pd.concat([agg_stocks, commodities_df, cash_df], ignore_index=True)

    # 5. 통화 변환
    if display_currency == "원화 (KRW)":
        target_symbol = "₩"
        is_usd = final_portfolio['currency'] == 'USD'
        final_portfolio.loc[is_usd, '매입금액_통합'] = final_portfolio.loc[is_usd, '총매입금액'] * usd_krw_rate
        final_portfolio.loc[is_usd, '평가금액_통합'] = final_portfolio.loc[is_usd, '평가금액_원본'] * usd_krw_rate
        is_krw = final_portfolio['currency'] == 'KRW'
        final_portfolio.loc[is_krw, '매입금액_통합'] = final_portfolio.loc[is_krw, '총매입금액']
        final_portfolio.loc[is_krw, '평가금액_통합'] = final_portfolio.loc[is_krw, '평가금액_원본']
    else: # 달러 (USD)
        target_symbol = "$"
        is_krw = final_portfolio['currency'] == 'KRW'
        final_portfolio.loc[is_krw, '매입금액_통합'] = final_portfolio.loc[is_krw, '총매입금액'] / usd_krw_rate
        final_portfolio.loc[is_krw, '평가금액_통합'] = final_portfolio.loc[is_krw, '평가금액_원본'] / usd_krw_rate
        is_usd = final_portfolio['currency'] == 'USD'
        final_portfolio.loc[is_usd, '매입금액_통합'] = final_portfolio.loc[is_usd, '총매입금액']
        final_portfolio.loc[is_usd, '평가금액_통합'] = final_portfolio.loc[is_usd, '평가금액_원본']

    final_portfolio['수익금_통합'] = final_portfolio['평가금액_통합'] - final_portfolio['매입금액_통합']
    final_portfolio['수익률'] = final_portfolio['수익금_통합'].divide(final_portfolio['매입금액_통합']).multiply(100).fillna(0)

    # 6. 요약 및 시각화
    st.divider()
    total_evaluation = final_portfolio['평가금액_통합'].sum()
    total_purchase = final_portfolio['매입금액_통합'].sum()
    total_profit = final_portfolio['수익금_통합'].sum()
    total_return_rate = (total_profit / total_purchase) * 100 if total_purchase > 0 else 0

    st.subheader(f"📈 포트폴리오 요약 ({target_symbol})")
    cols = st.columns(4)
    cols[0].metric("총 매입금액", f"{target_symbol}{total_purchase:,.0f}")
    cols[1].metric("총 평가금액", f"{target_symbol}{total_evaluation:,.0f}")
    cols[2].metric("총 손익", f"{target_symbol}{total_profit:,.0f}", f"{total_return_rate:.2f}%")
    
    st.divider()
    # 상세 현황 표시는 생략

    viz_cols = st.columns(2)
    with viz_cols[0]:
        st.subheader("자산 종류별 비중")
        category_summary = final_portfolio.groupby('카테고리')['평가금액_통합'].sum().reset_index()
        fig_pie_cat = px.pie(category_summary, names='카테고리', values='평가금액_통합',
                             title=f"평가금액({target_symbol}) 기준", hole=0.3)
        fig_pie_cat.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie_cat, use_container_width=True)

    with viz_cols[1]:
        st.subheader("개별 자산 비중 (상위 5개)")
        
        # (핵심 수정) 상위 5개 자산만 라벨을 표시하도록 로직 변경
        # 1. 평가금액 기준으로 데이터 정렬
        sorted_portfolio = final_portfolio.sort_values(by='평가금액_통합', ascending=False)
        
        # 2. 전체 평가금액 합계 계산
        total_eval_sum = sorted_portfolio['평가금액_통합'].sum()
        
        # 3. 상위 5개 티커 추출
        top_5_tickers = sorted_portfolio.head(5)['ticker'].tolist()
        
        # 4. 파이 차트에 표시될 텍스트 라벨 생성
        def get_pie_label(row):
            if row['ticker'] in top_5_tickers and total_eval_sum > 0:
                percentage = (row['평가금액_통합'] / total_eval_sum) * 100
                return f"{row['ticker']}<br>{percentage:.1f}%"
            return "" # 상위 5개가 아니면 라벨 없음

        sorted_portfolio['pie_label'] = sorted_portfolio.apply(get_pie_label, axis=1)

        # 5. 파이 차트 생성
        fig_pie_ticker = px.pie(sorted_portfolio, names='ticker', values='평가금액_통합',
                                 title=f"평가금액({target_symbol}) 기준", hole=0.3)
        
        # 6. 차트 업데이트: 생성된 라벨을 사용하고, 글자 크기 조정
        fig_pie_ticker.update_traces(
            text=sorted_portfolio['pie_label'],
            textinfo='text',
            textposition='inside',
            insidetextfont=dict(size=14) # 라벨 폰트 크기
        )
        st.plotly_chart(fig_pie_ticker, use_container_width=True)
