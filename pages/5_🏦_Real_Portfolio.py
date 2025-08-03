import streamlit as st
import pandas as pd
import plotly.express as px
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data import fetcher
import data.kis_integration as kis_integration

# 자산 분류 설정 파일 경로
ASSET_CLASSIFICATION_FILE = "private/asset_classification.csv"

# 기본 자산 분류 정의
DEFAULT_ASSET_TYPES = {
    'IEF': '채권',
    'SGOV': '채권', 
    'SHV': '채권',
    'BIL': '채권',
    'QQQ': 'ETF',
    'QQQM': 'ETF',
    'SCHD': 'ETF',
    '360750': 'ETF',  # TIGER 미국S&P500
    '379800': 'ETF',  # KODEX 미국S&P500
    '472170': 'ETF',  # TIGER 미국테크TOP10채권혼합
}

# 자산 분류 데이터 로딩/저장 함수
@st.cache_data(ttl=60)
def load_asset_classification():
    """자산 분류 설정 로딩"""
    if os.path.exists(ASSET_CLASSIFICATION_FILE):
        df = pd.read_csv(ASSET_CLASSIFICATION_FILE)
        return dict(zip(df['ticker'], df['asset_type']))
    else:
        return DEFAULT_ASSET_TYPES.copy()

def save_asset_classification(classification_dict):
    """자산 분류 설정 저장"""
    df = pd.DataFrame(list(classification_dict.items()), columns=['ticker', 'asset_type'])
    df.to_csv(ASSET_CLASSIFICATION_FILE, index=False)
    st.cache_data.clear()  # 캐시 클리어

st.set_page_config(layout="wide", page_title="실제 포트폴리오")

st.title("🏦 실제 포트폴리오")
st.write("KIS API를 통해 실시간으로 조회한 실제 계좌 현황입니다.")
st.divider()

# 데이터 로딩
@st.cache_data(ttl=300)  # 5분간 캐시
def load_real_portfolio():
    try:
        kis = kis_integration.KISIntegration()
        balance = kis.get_balance()
        return balance
    except Exception as e:
        st.error(f"포트폴리오 데이터 로딩 실패: {e}")
        return None

# 환율 정보
@st.cache_data(ttl=300)
def get_exchange_rate():
    usd_krw_rate, _ = fetcher.get_index_data('USDKRW=X')
    return usd_krw_rate if usd_krw_rate else 1350.0  # 기본값

# UI: 필터 및 환율 정보
st.subheader("⚙️ 설정")
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    display_currency = st.radio(
        "표시 통화", ["원화 (KRW)", "달러 (USD)"], horizontal=True
    )
with col2:
    if st.button("🔄 데이터 새로고침"):
        st.cache_data.clear()
        st.rerun()
with col3:
    usd_krw_rate = get_exchange_rate()
    st.metric("현재 환율 (USD/KRW)", f"{usd_krw_rate:,.2f}")

# 데이터 처리 함수
def process_portfolio_data(balance_data, asset_classification):
    """KIS API 데이터를 DataFrame으로 변환"""
    all_data = []
    
    for account_id, account_data in balance_data.items():
        # 주식 데이터 처리
        if 'stock' in account_data:
            for stock in account_data['stock']:
                # 사용자 정의 자산 분류 적용
                custom_asset_type = asset_classification.get(stock['ticker'], '주식')
                
                all_data.append({
                    'account_id': account_id,
                    'name': stock['name'],
                    'ticker': stock['ticker'],
                    'quantity': stock['quantity'],
                    'avg_price': stock['avg_price'],
                    'currency': stock['currency'],
                    'asset_type': custom_asset_type,
                    'original_type': '주식',  # 원래 타입 보존
                    'total_purchase': stock['quantity'] * stock['avg_price']
                })
        
        # 예수금 데이터 처리
        if 'deposit' in account_data:
            for deposit in account_data['deposit']:
                all_data.append({
                    'account_id': account_id,
                    'name': deposit['name'],
                    'ticker': deposit['ticker'],
                    'quantity': deposit['quantity'],
                    'avg_price': deposit['avg_price'],
                    'currency': deposit['currency'],
                    'asset_type': '현금',
                    'original_type': '현금',
                    'total_purchase': deposit['quantity'] * deposit['avg_price']
                })
    
    return pd.DataFrame(all_data)

# 현재가 조회 함수
@st.cache_data(ttl=300)
def get_current_prices_for_portfolio(tickers):
    """포트폴리오 종목들의 현재가 조회"""
    kr_tickers = [t for t in tickers if t.endswith('.KS') or len(t) == 6]
    us_tickers = [t for t in tickers if t not in kr_tickers and t not in ['PENSION_DEPOSIT', 'OVERSEA_DEPOSIT', 'OVERSEA_KRW_DEPOSIT']]
    
    prices = {}
    
    if kr_tickers:
        kr_prices = fetcher.get_current_prices(kr_tickers)
        prices.update(kr_prices.to_dict())
    
    if us_tickers:
        us_prices = fetcher.get_current_prices(us_tickers)
        prices.update(us_prices.to_dict())
    
    return prices

st.divider()

# 포트폴리오 데이터 로딩
balance = load_real_portfolio()
if balance is None:
    st.error("포트폴리오 데이터를 불러올 수 없습니다.")
    st.stop()

# 자산 분류 설정
with st.expander("🏷️ 자산 분류 설정"):
    st.write("보유 종목의 자산 유형을 설정할 수 있습니다.")
    
    # 현재 자산 분류 로딩
    current_classification = load_asset_classification()
    
    # 포트폴리오에서 주식 종목만 추출
    temp_df = process_portfolio_data(balance, {})
    stock_tickers = temp_df[temp_df['original_type'] == '주식']['ticker'].unique().tolist()
    
    if stock_tickers:
        st.write("##### 보유 종목 분류 설정")
        
        # 자산 유형 옵션
        asset_type_options = ['주식', 'ETF', '채권', 'REITs', '원자재', '기타']
        
        # 각 종목별 분류 설정
        classification_changes = {}
        cols_per_row = 3
        
        for i in range(0, len(stock_tickers), cols_per_row):
            cols = st.columns(cols_per_row)
            for j, ticker in enumerate(stock_tickers[i:i+cols_per_row]):
                with cols[j]:
                    # 종목명 표시
                    stock_name = temp_df[temp_df['ticker'] == ticker]['name'].iloc[0]
                    st.write(f"**{ticker}**")
                    st.caption(f"{stock_name}")
                    
                    current_type = current_classification.get(ticker, '주식')
                    new_type = st.selectbox(
                        "자산 유형",
                        options=asset_type_options,
                        index=asset_type_options.index(current_type) if current_type in asset_type_options else 0,
                        key=f"asset_type_{ticker}"
                    )
                    classification_changes[ticker] = new_type
        
        # 저장 버튼
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("💾 분류 저장", use_container_width=True):
                # 기존 분류와 새로운 분류 합치기
                updated_classification = current_classification.copy()
                updated_classification.update(classification_changes)
                save_asset_classification(updated_classification)
                st.success("자산 분류가 저장되었습니다!")
                st.rerun()
        
        with col2:
            if st.button("🔄 기본값으로 초기화", use_container_width=True):
                save_asset_classification(DEFAULT_ASSET_TYPES.copy())
                st.success("기본 분류로 초기화되었습니다!")
                st.rerun()
    else:
        st.info("분류할 수 있는 주식 종목이 없습니다.")

# 최종 자산 분류 적용하여 데이터 처리

# 데이터 처리
final_classification = load_asset_classification()
portfolio_df = process_portfolio_data(balance, final_classification)

if not portfolio_df.empty:
    # 현재가 조회 (원래 타입이 주식인 것만)
    stock_tickers = portfolio_df[portfolio_df['original_type'] == '주식']['ticker'].unique().tolist()
    current_prices = get_current_prices_for_portfolio(stock_tickers)
    
    # 현재가 매핑 (예수금은 매입가와 동일)
    portfolio_df['current_price'] = portfolio_df.apply(
        lambda row: current_prices.get(row['ticker'], row['avg_price']) 
        if row['original_type'] == '주식' else row['avg_price'], axis=1
    )
    
    portfolio_df['current_value'] = portfolio_df['quantity'] * portfolio_df['current_price']
    
    # 통화 변환
    def convert_to_target_currency(row):
        if display_currency == "원화 (KRW)" and row['currency'] == 'USD':
            return row['total_purchase'] * usd_krw_rate, row['current_value'] * usd_krw_rate
        elif display_currency == "달러 (USD)" and row['currency'] == 'KRW':
            return row['total_purchase'] / usd_krw_rate, row['current_value'] / usd_krw_rate
        return row['total_purchase'], row['current_value']
    
    portfolio_df[['purchase_converted', 'value_converted']] = portfolio_df.apply(
        convert_to_target_currency, axis=1, result_type='expand'
    )
    
    portfolio_df['profit_loss'] = portfolio_df['value_converted'] - portfolio_df['purchase_converted']
    portfolio_df['return_rate'] = (portfolio_df['profit_loss'] / portfolio_df['purchase_converted'] * 100).fillna(0)
    
    target_symbol = "₩" if display_currency == "원화 (KRW)" else "$"
    
    # 요약 정보
    total_purchase = portfolio_df['purchase_converted'].sum()
    total_value = portfolio_df['value_converted'].sum()
    total_profit = portfolio_df['profit_loss'].sum()
    total_return_rate = (total_profit / total_purchase) * 100 if total_purchase > 0 else 0
    
    st.subheader(f"📈 포트폴리오 요약 ({target_symbol})")
    cols = st.columns(4)
    cols[0].metric("총 매입금액", f"{target_symbol}{total_purchase:,.0f}")
    cols[1].metric("총 평가금액", f"{target_symbol}{total_value:,.0f}")
    cols[2].metric("총 손익", f"{target_symbol}{total_profit:,.0f}", f"{total_return_rate:.2f}%")
    
    # 계좌별 요약
    account_summary = portfolio_df.groupby('account_id').agg({
        'purchase_converted': 'sum',
        'value_converted': 'sum',
        'profit_loss': 'sum'
    }).reset_index()
    account_summary['return_rate'] = (account_summary['profit_loss'] / account_summary['purchase_converted'] * 100).fillna(0)
    
    # 계좌명 매핑
    account_names = {
        '43143043': '퇴직연금계좌',
        '43103581': '해외주식계좌'
    }
    account_summary['account_name'] = account_summary['account_id'].map(account_names).fillna('기타계좌')
    
    cols[3].metric("보유 계좌 수", f"{len(account_summary)}개")
    
    st.divider()
    
    # 시각화
    st.subheader("📊 포트폴리오 시각화")
    viz_cols = st.columns(2)
    
    with viz_cols[0]:
        st.write("##### 자산 유형별 비중")
        asset_summary = portfolio_df.groupby('asset_type')['value_converted'].sum().reset_index()
        fig_pie_asset = px.pie(asset_summary, names='asset_type', values='value_converted', hole=0.3)
        fig_pie_asset.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie_asset, use_container_width=True)
    
    with viz_cols[1]:
        st.write("##### 계좌별 비중")
        fig_pie_account = px.pie(account_summary, names='account_name', values='value_converted', hole=0.3)
        fig_pie_account.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie_account, use_container_width=True)
    
    st.divider()
    
    # 계좌별 상세 현황
    st.subheader(f"🏛️ 계좌별 현황 ({target_symbol})")
    
    for account_id, account_name in account_names.items():
        if account_id in portfolio_df['account_id'].values:
            with st.expander(f"📁 {account_name} ({account_id})"):
                account_data = portfolio_df[portfolio_df['account_id'] == account_id].copy()
                
                # 계좌 요약
                acc_total_purchase = account_data['purchase_converted'].sum()
                acc_total_value = account_data['value_converted'].sum()
                acc_total_profit = account_data['profit_loss'].sum()
                acc_return_rate = (acc_total_profit / acc_total_purchase) * 100 if acc_total_purchase > 0 else 0
                
                acc_cols = st.columns(4)
                acc_cols[0].metric("매입금액", f"{target_symbol}{acc_total_purchase:,.0f}")
                acc_cols[1].metric("평가금액", f"{target_symbol}{acc_total_value:,.0f}")
                acc_cols[2].metric("손익", f"{target_symbol}{acc_total_profit:,.0f}", f"{acc_return_rate:.2f}%")
                acc_cols[3].metric("보유 종목", f"{len(account_data)}개")
                
                # 상세 테이블
                display_cols = ['name', 'ticker', 'asset_type', 'quantity', 'purchase_converted', 'value_converted', 'profit_loss', 'return_rate']
                styled_df = account_data[display_cols].style.format({
                    'quantity': '{:,.4f}',
                    'purchase_converted': target_symbol + '{:,.0f}',
                    'value_converted': target_symbol + '{:,.0f}',
                    'profit_loss': target_symbol + '{:,.0f}',
                    'return_rate': '{:.2f}%'
                }).background_gradient(cmap='RdYlGn', subset=['return_rate'], vmin=-20, vmax=20)
                
                st.dataframe(styled_df, use_container_width=True, hide_index=True)
    
    st.divider()
    
    # 전체 상세 현황
    st.subheader(f"📋 전체 자산 상세 현황 ({target_symbol})")
    
    # 정렬 옵션
    sort_col1, sort_col2 = st.columns(2)
    with sort_col1:
        sort_by = st.selectbox("정렬 기준", ['value_converted', 'return_rate', 'profit_loss'], 
                               format_func=lambda x: {'value_converted': '평가금액', 'return_rate': '수익률', 'profit_loss': '손익금액'}[x])
    with sort_col2:
        sort_order = st.radio("정렬 순서", ['내림차순', '오름차순'], horizontal=True)
    
    ascending = sort_order == '오름차순'
    portfolio_sorted = portfolio_df.sort_values(by=sort_by, ascending=ascending)
    
    # 계좌명 추가
    portfolio_sorted['account_name'] = portfolio_sorted['account_id'].map(account_names).fillna('기타계좌')
    
    display_cols = ['account_name', 'name', 'ticker', 'asset_type', 'quantity', 'purchase_converted', 'value_converted', 'profit_loss', 'return_rate']
    styled_df = portfolio_sorted[display_cols].style.format({
        'quantity': '{:,.4f}',
        'purchase_converted': target_symbol + '{:,.0f}',
        'value_converted': target_symbol + '{:,.0f}',
        'profit_loss': target_symbol + '{:,.0f}',
        'return_rate': '{:.2f}%'
    }).background_gradient(cmap='RdYlGn', subset=['return_rate'], vmin=-20, vmax=20)
    
    st.dataframe(styled_df, use_container_width=True, hide_index=True)

else:
    st.warning("포트폴리오 데이터가 없습니다.")

# 마지막 업데이트 시간 표시
st.caption(f"마지막 업데이트: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")

