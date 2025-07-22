import streamlit as st
import pandas as pd
import plotly.express as px
import os
from data import fetcher # 데이터 모듈 임포트

st.set_page_config(layout="wide", page_title="내 포트폴리오")

st.title("💼 내 포트폴리오")
st.write("`private/asset.csv` 파일의 내용을 직접 편집하고, 기준 통화를 선택하여 포트폴리오를 분석할 수 있습니다.")
st.divider()

# --- 포트폴리오 파일 경로 설정 ---
PORTFOLIO_FILE_PATH = "private/asset.csv"
os.makedirs("data", exist_ok=True)

# --- 통화 선택 및 환율 정보 ---
col1, col2 = st.columns([3, 1])
with col1:
    display_currency = st.radio(
        "통합 표시 통화 선택",
        ["원화 (KRW)", "달러 (USD)"],
        horizontal=True,
        label_visibility="collapsed"
    )
with col2:
    usd_krw_rate, _ = fetcher.get_index_data('USDKRW=X')
    if usd_krw_rate:
        st.metric("현재 환율 (USD/KRW)", f"{usd_krw_rate:,.2f}")
    else:
        st.error("환율 정보를 가져올 수 없습니다.")


# --- 데이터 로딩 및 편집 ---
try:
    if 'portfolio_df' not in st.session_state:
        if os.path.exists(PORTFOLIO_FILE_PATH):
            st.session_state.portfolio_df = pd.read_csv(PORTFOLIO_FILE_PATH)
        else:
            st.session_state.portfolio_df = pd.DataFrame({
                "ticker": ["AAPL", "005930.KS"], "수량": [10.0, 50.0], "평균매입금액": [150.50, 75000.00]
            })

    with st.expander("✏️ 포트폴리오 편집하기", expanded=False):
        edited_df = st.data_editor(
            st.session_state.portfolio_df,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "ticker": st.column_config.TextColumn("Ticker", required=True),
                "수량": st.column_config.NumberColumn("수량", format="%.4f", required=True),
                "평균매입금액": st.column_config.NumberColumn("평균매입금액", format="%.2f", required=True),
            }
        )
        if st.button("💾 변경 사항 저장", use_container_width=True, type="primary"):
            columns_to_save = ["ticker", "수량", "평균매입금액"]
            save_df = edited_df[columns_to_save]
            save_df.to_csv(PORTFOLIO_FILE_PATH, index=False)
            st.session_state.portfolio_df = edited_df
            st.toast("포트폴리오가 성공적으로 저장되었습니다!", icon="🎉")

    # --- 포트폴리오 분석 ---
    if usd_krw_rate:
        portfolio_df = edited_df.copy()
        required_cols = ["ticker", "수량", "평균매입금액"]
        if not all(col in portfolio_df.columns for col in required_cols):
            st.error(f"데이터에 필수 컬럼({', '.join(required_cols)})이 모두 포함되어 있는지 확인해주세요.")
        else:
            with st.spinner('포트폴리오를 집계하고 환율을 적용하여 분석 중입니다...'):
                portfolio_df.dropna(subset=required_cols, inplace=True)
                portfolio_df['수량'] = pd.to_numeric(portfolio_df['수량'], errors='coerce')
                portfolio_df['평균매입금액'] = pd.to_numeric(portfolio_df['평균매입금액'], errors='coerce')
                
                portfolio_df['총매입금액'] = portfolio_df['수량'] * portfolio_df['평균매입금액']
                
                agg_portfolio = portfolio_df.groupby('ticker').agg(
                    수량=('수량', 'sum'), 총매입금액=('총매입금액', 'sum')
                ).reset_index()
                
                # --- (핵심 수정) 현재가 조회를 시장별로 분리 ---
                tickers = agg_portfolio["ticker"].tolist()
                kr_tickers = [t for t in tickers if '.KS' in t.upper()]
                other_tickers = [t for t in tickers if '.KS' not in t.upper()]

                kr_prices = fetcher.get_current_prices(kr_tickers)
                other_prices = fetcher.get_current_prices(other_tickers)
                
                # 조회된 가격 정보를 다시 하나로 합침
                current_prices = pd.concat([kr_prices, other_prices])
                agg_portfolio['현재가'] = agg_portfolio['ticker'].map(current_prices).fillna(0)
                # --- 조회 로직 수정 끝 ---
                
                agg_portfolio['평가금액_원본'] = agg_portfolio['수량'] * agg_portfolio['현재가']

                agg_portfolio['currency'] = agg_portfolio['ticker'].apply(lambda x: 'KRW' if '.KS' in x.upper() else 'USD')

                if display_currency == "원화 (KRW)":
                    target_symbol = "₩"
                    is_usd = agg_portfolio['currency'] == 'USD'
                    agg_portfolio.loc[is_usd, '매입금액_통합'] = agg_portfolio.loc[is_usd, '총매입금액'] * usd_krw_rate
                    agg_portfolio.loc[is_usd, '평가금액_통합'] = agg_portfolio.loc[is_usd, '평가금액_원본'] * usd_krw_rate
                    is_krw = agg_portfolio['currency'] == 'KRW'
                    agg_portfolio.loc[is_krw, '매입금액_통합'] = agg_portfolio.loc[is_krw, '총매입금액']
                    agg_portfolio.loc[is_krw, '평가금액_통합'] = agg_portfolio.loc[is_krw, '평가금액_원본']
                else: # 달러 (USD)
                    target_symbol = "$"
                    is_krw = agg_portfolio['currency'] == 'KRW'
                    agg_portfolio.loc[is_krw, '매입금액_통합'] = agg_portfolio.loc[is_krw, '총매입금액'] / usd_krw_rate
                    agg_portfolio.loc[is_krw, '평가금액_통합'] = agg_portfolio.loc[is_krw, '평가금액_원본'] / usd_krw_rate
                    is_usd = agg_portfolio['currency'] == 'USD'
                    agg_portfolio.loc[is_usd, '매입금액_통합'] = agg_portfolio.loc[is_usd, '총매입금액']
                    agg_portfolio.loc[is_usd, '평가금액_통합'] = agg_portfolio.loc[is_usd, '평가금액_원본']

                agg_portfolio['매입단가_통합'] = agg_portfolio['매입금액_통합'].divide(agg_portfolio['수량']).fillna(0)
                agg_portfolio['현재가_통합'] = agg_portfolio['평가금액_통합'].divide(agg_portfolio['수량']).fillna(0)
                agg_portfolio['수익금_통합'] = agg_portfolio['평가금액_통합'] - agg_portfolio['매입금액_통합']
                agg_portfolio['수익률'] = agg_portfolio['수익금_통합'].divide(agg_portfolio['매입금액_통합']).multiply(100).fillna(0)

                st.divider()
                total_purchase = agg_portfolio['매입금액_통합'].sum()
                total_evaluation = agg_portfolio['평가금액_통합'].sum()
                total_profit = agg_portfolio['수익금_통합'].sum()
                total_return_rate = (total_profit / total_purchase) * 100 if total_purchase > 0 else 0

                st.subheader(f"📈 포트폴리오 요약 ({target_symbol})")
                cols = st.columns(4)
                cols[0].metric("총 매입금액", f"{target_symbol}{total_purchase:,.0f}")
                cols[1].metric("총 평가금액", f"{target_symbol}{total_evaluation:,.0f}")
                cols[2].metric("총 손익", f"{target_symbol}{total_profit:,.0f}", f"{total_return_rate:.2f}%")
                
                st.divider()

                st.subheader(f"📊 포트폴리오 상세 현황 ({target_symbol})")
                display_cols = ['ticker', '수량', 'currency', '매입단가_통합', '현재가_통합', '평가금액_통합', '수익금_통합', '수익률']
                
                styled_df = agg_portfolio[display_cols].style.format({
                    '수량': '{:,.4f}',
                    '매입단가_통합': target_symbol + '{:,.2f}',
                    '현재가_통합': target_symbol + '{:,.2f}',
                    '평가금액_통합': target_symbol + '{:,.0f}',
                    '수익금_통합': target_symbol + '{:,.0f}',
                    '수익률': '{:.2f}%'
                }).background_gradient(cmap='RdYlGn', subset=['수익률'], vmin=-20, vmax=20)
                st.dataframe(styled_df, use_container_width=True, hide_index=True)

                viz_cols = st.columns(2)
                with viz_cols[0]:
                    st.subheader("종목별 비중")
                    fig_pie = px.pie(agg_portfolio, names='ticker', values='평가금액_통합',
                                     hover_data=['수량', '현재가_통합'], hole=0.3,
                                     title=f"평가금액({target_symbol}) 기준")
                    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig_pie, use_container_width=True)

                with viz_cols[1]:
                    st.subheader("종목별 손익")
                    fig_bar = px.bar(agg_portfolio.sort_values('수익금_통합'), x='ticker', y='수익금_통합',
                                     color='수익금_통합', color_continuous_scale='RdYlGn',
                                     hover_data=['수익률', '평가금액_통합'],
                                     title=f"손익({target_symbol}) 기준")
                    st.plotly_chart(fig_bar, use_container_width=True)

except Exception as e:
    st.error(f"페이지를 로드하는 중 오류가 발생했습니다: {e}")
