import streamlit as st
import pandas as pd
import plotly.express as px
import os
from data import fetcher # 데이터 모듈 임포트
import auth  # 인증 모듈 추가

st.set_page_config(layout="wide", page_title="내 포트폴리오")

# --- 인증 확인 ---
if not auth.render_authentication_ui():
    st.stop()

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
        "평균매입금액": [180.50, 75.00, 100.10], "카테고리": ["성장주", "배당주", "채권"],
        "연금계좌": [False, True, True], "계좌": ["일반계좌", "연금계좌", "연금계좌"]
    }
    st.session_state.stock_portfolio_df = load_assets(ASSET_FILE_PATH, sample_stocks)
    # 구버전 파일을 위한 호환성 처리
    if '카테고리' not in st.session_state.stock_portfolio_df.columns:
        st.session_state.stock_portfolio_df['카테고리'] = '성장주'
    if '연금계좌' not in st.session_state.stock_portfolio_df.columns:
        st.session_state.stock_portfolio_df['연금계좌'] = False
    if '계좌' not in st.session_state.stock_portfolio_df.columns:
        st.session_state.stock_portfolio_df['계좌'] = '일반계좌'

# 원자재 포트폴리오 로딩
if 'commodity_portfolio_df' not in st.session_state:
    sample_commodities = {
        "자산명": ["Gold"], "수량": [10.0], "평균매입금액": [85000.00], "현재가": [90000.00], "계좌": ["안전자산"]
    }
    st.session_state.commodity_portfolio_df = load_assets(COMMODITIES_FILE_PATH, sample_commodities)
    if '계좌' not in st.session_state.commodity_portfolio_df.columns:
        st.session_state.commodity_portfolio_df['계좌'] = '기타'

# 현금 포트폴리오 로딩
if 'cash_portfolio_df' not in st.session_state:
    sample_cash = {"자산명": ["원화예금", "달러예금"], "통화": ["KRW", "USD"], "금액": [1000000.0, 5000.0], "계좌": ["생활비", "투자대기"]}
    st.session_state.cash_portfolio_df = load_assets(CASH_FILE_PATH, sample_cash)
    if '계좌' not in st.session_state.cash_portfolio_df.columns:
        st.session_state.cash_portfolio_df['계좌'] = '기타'


# --- UI: 필터 및 환율 정보 ---
st.subheader("⚙️ 필터 설정")
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    display_currency = st.radio(
        "통합 표시 통화", ["원화 (KRW)", "달러 (USD)"], horizontal=True
    )
with col2:
    pension_filter = st.radio(
        "연금계좌 필터", ["전체 합산", "일반계좌만"], horizontal=True
    )
with col3:
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
            "카테고리": st.column_config.SelectboxColumn("자산 종류", options=["성장주", "배당주", "채권"], required=True),
            "연금계좌": st.column_config.CheckboxColumn("연금계좌", default=False),
            "계좌": st.column_config.TextColumn("계좌 별명", required=True)
        }
    )
    if st.button("✅ 주식 저장", use_container_width=True):
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
            "현재가": st.column_config.NumberColumn("현재가 (KRW)", format="%.0f", required=True),
            "계좌": st.column_config.TextColumn("계좌 별명", required=True)
        }
    )
    if st.button("✅ 원자재 저장", use_container_width=True):
        edited_commodities_df.to_csv(COMMODITIES_FILE_PATH, index=False)
        st.session_state.commodity_portfolio_df = edited_commodities_df
        st.toast("원자재 포트폴리오가 저장되었습니다!", icon="💰")

with st.expander("✏️ 현금 자산 편집하기"):
    edited_cash_df = st.data_editor(
        st.session_state.cash_portfolio_df, num_rows="dynamic", use_container_width=True,
        column_config={
            "자산명": st.column_config.TextColumn("자산명", required=True),
            "통화": st.column_config.SelectboxColumn("통화", options=["KRW", "USD"], required=True),
            "금액": st.column_config.NumberColumn("금액", format="%.2f", required=True),
            "계좌": st.column_config.TextColumn("계좌 별명", required=True)
        }
    )
    if st.button("✅ 현금 저장", use_container_width=True):
        edited_cash_df.to_csv(CASH_FILE_PATH, index=False)
        st.session_state.cash_portfolio_df = edited_cash_df
        st.toast("현금 포트폴리오가 저장되었습니다!", icon="💵")


# --- 포트폴리오 분석 ---
if usd_krw_rate:
    # 1. 주식 데이터 처리
    stocks_df = edited_stocks_df.copy()
    stocks_df.dropna(subset=["ticker", "수량", "평균매입금액", "카테고리", "계좌"], inplace=True)
    stocks_df['총매입금액'] = pd.to_numeric(stocks_df['수량']) * pd.to_numeric(stocks_df['평균매입금액'])
    agg_stocks = stocks_df.groupby(['ticker', '계좌']).agg(
        수량=('수량', 'sum'), 총매입금액=('총매입금액', 'sum'), 
        카테고리=('카테고리', 'first'), 연금계좌=('연금계좌', 'first')
    ).reset_index()
    
    tickers = agg_stocks["ticker"].tolist()
    kr_tickers = [t for t in tickers if '.KS' in t.upper()]
    other_tickers = [t for t in tickers if '.KS' not in t.upper()]
    kr_prices = fetcher.get_current_prices(kr_tickers)
    other_prices = fetcher.get_current_prices(other_tickers)
    current_prices = pd.concat([kr_prices, other_prices])
    
    agg_stocks['현재가'] = agg_stocks['ticker'].map(current_prices).fillna(0)
    agg_stocks['평가금액_원본'] = agg_stocks['수량'] * agg_stocks['현재가']
    agg_stocks['currency'] = agg_stocks['ticker'].apply(lambda x: 'KRW' if '.KS' in x.upper() else 'USD')

    # 2. 원자재 데이터 처리
    commodities_df = edited_commodities_df.copy()
    commodities_df.dropna(subset=["자산명", "수량", "평균매입금액", "현재가", "계좌"], inplace=True)
    commodities_df.rename(columns={'자산명': 'ticker'}, inplace=True)
    commodities_df['카테고리'] = '금/원자재'
    commodities_df['currency'] = 'KRW'
    commodities_df['총매입금액'] = pd.to_numeric(commodities_df['수량']) * pd.to_numeric(commodities_df['평균매입금액'])
    commodities_df['평가금액_원본'] = pd.to_numeric(commodities_df['수량']) * pd.to_numeric(commodities_df['현재가'])
    commodities_df['연금계좌'] = False

    # 3. 현금 데이터 처리
    cash_df = edited_cash_df.copy()
    cash_df.dropna(subset=["자산명", "통화", "금액", "계좌"], inplace=True)
    cash_df.rename(columns={'자산명': 'ticker', '통화': 'currency', '금액': '총매입금액'}, inplace=True)
    cash_df['카테고리'] = '현금'
    cash_df['평가금액_원본'] = cash_df['총매입금액']
    cash_df['연금계좌'] = False

    # 4. 데이터 통합
    final_portfolio = pd.concat([agg_stocks, commodities_df, cash_df], ignore_index=True)
    
    # --- 계좌 필터 UI 및 로직 ---
    all_accounts = sorted(final_portfolio['계좌'].unique().tolist())
    selected_accounts = st.multiselect(
        "분석할 계좌 선택",
        options=all_accounts,
        default=all_accounts
    )
    
    if not selected_accounts:
        selected_accounts = all_accounts
        
    final_portfolio = final_portfolio[final_portfolio['계좌'].isin(selected_accounts)]

    # 5. 연금계좌 필터링
    if pension_filter == "일반계좌만":
        final_portfolio = final_portfolio[final_portfolio['연금계좌'] == False]

    # 6. 통화 변환 로직
    def convert_currency(row):
        purchase_val = row['총매입금액']
        eval_val = row['평가금액_원본']
        if display_currency == "원화 (KRW)" and row['currency'] == 'USD':
            return purchase_val * usd_krw_rate, eval_val * usd_krw_rate
        elif display_currency == "달러 (USD)" and row['currency'] == 'KRW':
            return purchase_val / usd_krw_rate, eval_val / usd_krw_rate
        return purchase_val, eval_val

    final_portfolio[['매입금액_통합', '평가금액_통합']] = final_portfolio.apply(
        convert_currency, axis=1, result_type='expand'
    ).fillna(0)
    
    target_symbol = "₩" if display_currency == "원화 (KRW)" else "$"
    final_portfolio['수익금_통합'] = final_portfolio['평가금액_통합'] - final_portfolio['매입금액_통합']
    final_portfolio['수익률'] = final_portfolio['수익금_통합'].divide(final_portfolio['매입금액_통합']).multiply(100).fillna(0)

    # 7. 요약 및 시각화
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

    st.subheader("🤔 포트폴리오 시각화")
    viz_cols = st.columns(2)
    with viz_cols[0]:
        st.write("##### 자산 종류별 비중")
        category_summary = final_portfolio.groupby('카테고리')['평가금액_통합'].sum().reset_index()
        fig_pie_cat = px.pie(category_summary, names='카테고리', values='평가금액_통합', hole=0.3)
        fig_pie_cat.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie_cat, use_container_width=True)

    with viz_cols[1]:
        st.write("##### 개별 자산 비중 (상위 5개)")
        sorted_portfolio = final_portfolio.sort_values(by='평가금액_통합', ascending=False)
        total_eval_sum = sorted_portfolio['평가금액_통합'].sum()
        top_5_tickers = sorted_portfolio.head(5)['ticker'].tolist()
        
        def get_pie_label(row):
            if row['ticker'] in top_5_tickers and total_eval_sum > 0:
                percentage = (row['평가금액_통합'] / total_eval_sum) * 100
                return f"{row['ticker']}<br>{percentage:.1f}%"
            return ""

        sorted_portfolio['pie_label'] = sorted_portfolio.apply(get_pie_label, axis=1)

        fig_pie_ticker = px.pie(sorted_portfolio, names='ticker', values='평가금액_통합', hole=0.3)
        
        fig_pie_ticker.update_traces(
            text=sorted_portfolio['pie_label'], textinfo='text',
            textposition='inside', insidetextfont=dict(size=14)
        )
        st.plotly_chart(fig_pie_ticker, use_container_width=True)

    # --- (핵심 추가) 계좌별 자산 현황 섹션 ---
    st.divider()
    st.subheader(f"🏛️ 계좌별 자산 현황 ({target_symbol})")
    
    acc_cols = st.columns([1, 1])
    with acc_cols[0]:
        account_summary = final_portfolio.groupby('계좌')['평가금액_통합'].sum().reset_index()
        account_summary.rename(columns={'평가금액_통합': '총 평가금액'}, inplace=True)
        
        st.dataframe(
            account_summary.style.format({'총 평가금액': target_symbol + '{:,.0f}'}),
            use_container_width=True,
            hide_index=True
        )

    with acc_cols[1]:
        fig_pie_acc = px.pie(account_summary, names='계좌', values='총 평가금액', hole=0.3)
        fig_pie_acc.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie_acc, use_container_width=True)


    st.divider()
    st.subheader(f"📊 자산 상세 현황 ({target_symbol})")
    
    display_cols = ['ticker', '계좌', '카테고리', '수량', '매입금액_통합', '평가금액_통합', '수익금_통합', '수익률', '연금계좌']
    final_portfolio['수량'] = final_portfolio['수량'].fillna(0)

    styled_df = final_portfolio[display_cols].style.format({
        '수량': '{:,.4f}',
        '매입금액_통합': target_symbol + '{:,.0f}',
        '평가금액_통합': target_symbol + '{:,.0f}',
        '수익금_통합': target_symbol + '{:,.0f}',
        '수익률': '{:.2f}%'
    }).background_gradient(cmap='RdYlGn', subset=['수익률'], vmin=-20, vmax=20)
    
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
