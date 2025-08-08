import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
import os
from datetime import datetime, timedelta, date

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_manager import PortfolioDBManager

st.set_page_config(layout="wide", page_title="포트폴리오 히스토리")

st.title("📊 포트폴리오 히스토리")
st.write("저장된 포트폴리오 데이터의 히스토리를 조회하고 분석합니다.")
st.divider()

# DB 매니저 초기화
@st.cache_resource
def get_db_manager():
    return PortfolioDBManager()

db_manager = get_db_manager()

# 기간 선택
st.subheader("📅 조회 기간 설정")
col1, col2, col3 = st.columns([2, 2, 2])

with col1:
    start_date = st.date_input(
        "시작 날짜",
        value=date.today() - timedelta(days=30),
        max_value=date.today()
    )

with col2:
    end_date = st.date_input(
        "종료 날짜", 
        value=date.today(),
        max_value=date.today()
    )

with col3:
    display_currency = st.radio(
        "표시 통화", ["KRW", "USD"], horizontal=True
    )

# 데이터 로딩
@st.cache_data(ttl=300)
def load_history_data(start_date, end_date):
    return db_manager.get_portfolio_history(start_date, end_date)

history_df = load_history_data(start_date, end_date)

if history_df.empty:
    st.warning("선택한 기간에 저장된 데이터가 없습니다.")
    st.info("포트폴리오 스케줄러가 실행되면 데이터가 자동으로 저장됩니다.")
    st.stop()

st.divider()

# 요약 정보
st.subheader(f"📈 포트폴리오 요약 ({display_currency})")

latest_record = history_df.iloc[-1]  # 최신 기록
first_record = history_df.iloc[0]   # 첫 기록

# 통화에 따른 값 선택
if display_currency == "KRW":
    symbol = "₩"
    total_value = latest_record['total_value_krw']
    total_purchase = latest_record['total_purchase_krw']
    total_profit = latest_record['total_profit_krw']
    
    first_value = first_record['total_value_krw']
    period_change = total_value - first_value
    period_change_pct = (period_change / first_value * 100) if first_value > 0 else 0
else:
    symbol = "$"
    total_value = latest_record['total_value_usd']
    total_purchase = latest_record['total_purchase_usd']
    total_profit = latest_record['total_profit_usd']
    
    first_value = first_record['total_value_usd']
    period_change = total_value - first_value
    period_change_pct = (period_change / first_value * 100) if first_value > 0 else 0

cols = st.columns(5)
cols[0].metric(
    "현재 총 자산", 
    f"{symbol}{total_value:,.0f}"
)
cols[1].metric(
    "총 매입금액", 
    f"{symbol}{total_purchase:,.0f}"
)
cols[2].metric(
    "총 손익", 
    f"{symbol}{total_profit:,.0f}",
    f"{latest_record['total_return_rate']:.2f}%"
)
cols[3].metric(
    "기간 수익률",
    f"{period_change_pct:+.2f}%",
    f"{symbol}{period_change:+,.0f}"
)
cols[4].metric(
    "데이터 수", 
    f"{len(history_df)}개"
)

st.divider()

# 차트 섹션
st.subheader("📊 포트폴리오 추이")

# 총 자산 추이 차트
fig_value = px.line(
    history_df,
    x='record_datetime',
    y=f'total_value_{display_currency.lower()}',
    title=f"총 자산 추이 ({symbol}) - 분 단위",
    labels={
        'record_datetime': '날짜시간',
        f'total_value_{display_currency.lower()}': f'총 자산 ({symbol})'
    }
)

fig_value.update_layout(
    xaxis_title="날짜시간",
    yaxis_title=f"총 자산 ({symbol})",
    hovermode='x unified'
)

fig_value.update_traces(
    line=dict(width=2),
    hovertemplate=f'시간: %{{x}}<br>총 자산: {symbol}%{{y:,.0f}}<extra></extra>'
)

st.plotly_chart(fig_value, use_container_width=True)

# 계좌별/종목별 자산 추이 차트 (Stacked Area Chart)
st.write("##### 📊 자산 추이 (누적)")

# 토글 버튼 추가
chart_type = st.radio(
    "차트 종류 선택",
    ["계좌별", "종목별"],
    horizontal=True,
    help="계좌별 또는 종목별 자산 추이를 선택하여 보실 수 있습니다."
)

# 계좌별 데이터 처리 함수
@st.cache_data(ttl=300)
def get_account_history_data(start_date, end_date, currency):
    """계좌별 자산 추이 데이터 생성"""
    # 자산별 히스토리에서 계좌별로 집계
    import sqlite3
    
    query = f"""
    SELECT 
        record_datetime,
        account_id,
        SUM(value_{currency.lower()}) as account_value
    FROM asset_history 
    WHERE DATE(record_datetime) >= ? AND DATE(record_datetime) <= ?
    GROUP BY record_datetime, account_id
    ORDER BY record_datetime, account_id
    """
    
    with sqlite3.connect(db_manager.db_path) as conn:
        df = pd.read_sql_query(query, conn, params=[start_date, end_date])
    
    # 계좌명 매핑
    account_names = {
        '43147522': '개인연금계좌',
        '43143043': '퇴직연금계좌', 
        '43103581': '해외주식계좌',
        'ISA': 'ISA',
        'GOLD': '금계좌',
        'UPBIT': '업비트 계좌',
        'DC': 'DC 계좌'
    }
    
    df['account_name'] = df['account_id'].map(account_names).fillna('기타계좌')
    
    # 피벗 테이블로 변환 (시간별 계좌별 값)
    pivot_df = df.pivot(index='record_datetime', columns='account_name', values='account_value').fillna(0)
    pivot_df.reset_index(inplace=True)
    
    return pivot_df

# 종목별 데이터 처리 함수
@st.cache_data(ttl=300)
def get_ticker_history_data(start_date, end_date, currency):
    """종목별 자산 추이 데이터 생성"""
    import sqlite3
    
    query = f"""
    SELECT 
        record_datetime,
        ticker,
        name,
        SUM(value_{currency.lower()}) as ticker_value
    FROM asset_history 
    WHERE DATE(record_datetime) >= ? AND DATE(record_datetime) <= ?
    GROUP BY record_datetime, ticker, name
    ORDER BY record_datetime, ticker
    """
    
    with sqlite3.connect(db_manager.db_path) as conn:
        df = pd.read_sql_query(query, conn, params=[start_date, end_date])
    
    # 종목명 생성 (ticker가 있으면 "name(ticker)", 없으면 name만)
    df['display_name'] = df.apply(lambda row: f"{row['name']}({row['ticker']})" if pd.notna(row['ticker']) and row['ticker'].strip() else row['name'], axis=1)
    
    # 피벗 테이블로 변환 (시간별 종목별 값)
    pivot_df = df.pivot(index='record_datetime', columns='display_name', values='ticker_value').fillna(0)
    pivot_df.reset_index(inplace=True)
    
    return pivot_df

# 계좌별 데이터 가져오기
if chart_type == "계좌별" and not history_df.empty:
    account_data = get_account_history_data(start_date, end_date, display_currency)
    
    if not account_data.empty:
        # Stacked Area Chart 생성
        fig_stacked = go.Figure()
        
        # 계좌별 색상 정의
        account_colors = {
            '개인연금계좌': '#FF6B6B',
            '퇴직연금계좌': '#4ECDC4', 
            '해외주식계좌': '#45B7D1',
            'ISA': '#96CEB4',
            '금계좌': '#FFEAA7',
            '업비트 계좌': '#DDA0DD',
            'DC 계좌': '#98D8C8',
            '기타계좌': '#F7DC6F'
        }
        
        # 각 계좌별로 area trace 추가
        account_columns = [col for col in account_data.columns if col != 'record_datetime']
        
        for i, account in enumerate(account_columns):
            color = account_colors.get(account, f'hsl({i*30}, 70%, 60%)')
            
            fig_stacked.add_trace(go.Scatter(
                x=account_data['record_datetime'],
                y=account_data[account],
                mode='lines',
                stackgroup='one',
                name=account,
                line=dict(width=0.5),
                fillcolor=color,
                hovertemplate=f'<b>{account}</b><br>시간: %{{x}}<br>자산: {symbol}%{{y:,.0f}}<extra></extra>'
            ))
        
        fig_stacked.update_layout(
            title=f"계좌별 자산 추이 ({symbol}) - 누적 영역 그래프",
            xaxis_title="날짜시간",
            yaxis_title=f"자산 ({symbol})",
            hovermode='x unified',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            margin=dict(t=80)  # 범례를 위한 여백 추가
        )
        
        st.plotly_chart(fig_stacked, use_container_width=True)
    else:
        st.info("계좌별 자산 데이터가 없습니다.")

# 종목별 데이터 가져오기
elif chart_type == "종목별" and not history_df.empty:
    ticker_data = get_ticker_history_data(start_date, end_date, display_currency)
    
    if not ticker_data.empty:
        # Stacked Area Chart 생성
        fig_stacked = go.Figure()
        
        # 종목별로 area trace 추가 (상위 15개 종목만 표시)
        ticker_columns = [col for col in ticker_data.columns if col != 'record_datetime']
        
        # 최신 데이터 기준 상위 종목 선정
        latest_values = {}
        for col in ticker_columns:
            latest_values[col] = ticker_data[col].iloc[-1] if len(ticker_data) > 0 else 0
        
        # 상위 15개 종목 선정
        top_tickers = sorted(latest_values.items(), key=lambda x: x[1], reverse=True)[:15]
        top_ticker_names = [ticker[0] for ticker in top_tickers]
        
        # 나머지 종목들은 '기타'로 합침
        other_columns = [col for col in ticker_columns if col not in top_ticker_names]
        if other_columns:
            ticker_data['기타'] = ticker_data[other_columns].sum(axis=1)
            top_ticker_names.append('기타')
        
        # 색상 팔레트 생성 (더 많은 색상 필요)
        import plotly.colors as pc
        colors = pc.qualitative.Set3 + pc.qualitative.Pastel + pc.qualitative.Set1
        
        for i, ticker in enumerate(top_ticker_names):
            color = colors[i % len(colors)]
            
            fig_stacked.add_trace(go.Scatter(
                x=ticker_data['record_datetime'],
                y=ticker_data[ticker],
                mode='lines',
                stackgroup='one',
                name=ticker,
                line=dict(width=0.5),
                fillcolor=color,
                hovertemplate=f'<b>{ticker}</b><br>시간: %{{x}}<br>자산: {symbol}%{{y:,.0f}}<extra></extra>'
            ))
        
        fig_stacked.update_layout(
            title=f"종목별 자산 추이 ({symbol}) - 누적 영역 그래프 (상위 15개 + 기타)",
            xaxis_title="날짜시간",
            yaxis_title=f"자산 ({symbol})",
            hovermode='x unified',
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02,
                font=dict(size=10)
            ),
            margin=dict(r=200)  # 범례를 위한 여백 추가
        )
        
        st.plotly_chart(fig_stacked, use_container_width=True)
    else:
        st.info("종목별 자산 데이터가 없습니다.")

# 수익률 추이 차트
fig_return = px.line(
    history_df,
    x='record_datetime',
    y='total_return_rate',
    title="총 수익률 추이 (%) - 분 단위",
    labels={
        'record_datetime': '날짜시간',
        'total_return_rate': '수익률 (%)'
    }
)

fig_return.update_layout(
    xaxis_title="날짜시간",
    yaxis_title="수익률 (%)",
    hovermode='x unified'
)

fig_return.update_traces(
    line=dict(width=2),
    hovertemplate='시간: %{x}<br>수익률: %{y:.2f}%<extra></extra>'
)

# 0% 라인 추가
fig_return.add_hline(y=0, line_dash="dash", line_color="red", opacity=0.5)

st.plotly_chart(fig_return, use_container_width=True)

# 매입가 대비 평가액 비교 차트
fig_comparison = make_subplots(
    rows=2, cols=1,
    shared_xaxes=True,
    subplot_titles=(f"매입가 vs 평가액 ({symbol})", f"손익 ({symbol})"),
    vertical_spacing=0.08
)

# 매입가와 평가액 라인
fig_comparison.add_trace(
    go.Scatter(
        x=history_df['record_datetime'],
        y=history_df[f'total_purchase_{display_currency.lower()}'],
        mode='lines',
        name='총 매입가',
        line=dict(color='blue', width=2)
    ),
    row=1, col=1
)

fig_comparison.add_trace(
    go.Scatter(
        x=history_df['record_datetime'],
        y=history_df[f'total_value_{display_currency.lower()}'],
        mode='lines',
        name='총 평가액',
        line=dict(color='green', width=2)
    ),
    row=1, col=1
)

# 손익 바 차트
colors = ['red' if x < 0 else 'green' for x in history_df[f'total_profit_{display_currency.lower()}']]
fig_comparison.add_trace(
    go.Bar(
        x=history_df['record_datetime'],
        y=history_df[f'total_profit_{display_currency.lower()}'],
        name='손익',
        marker_color=colors
    ),
    row=2, col=1
)

fig_comparison.update_layout(
    height=600,
    showlegend=True,
    hovermode='x unified'
)

fig_comparison.update_yaxes(title_text=f"금액 ({symbol})", row=1, col=1)
fig_comparison.update_yaxes(title_text=f"손익 ({symbol})", row=2, col=1)
fig_comparison.update_xaxes(title_text="날짜시간", row=2, col=1)

st.plotly_chart(fig_comparison, use_container_width=True)

st.divider()

# 상세 데이터 테이블
st.subheader("📋 상세 데이터")

# 표시할 컬럼 선택
display_columns = [
    'record_datetime', 
    f'total_value_{display_currency.lower()}',
    f'total_purchase_{display_currency.lower()}',
    f'total_profit_{display_currency.lower()}',
    'total_return_rate',
    'account_count',
    'asset_count'
]

# 컬럼명 한글화
column_names = {
    'record_datetime': '날짜시간',
    f'total_value_{display_currency.lower()}': f'총 평가액({symbol})',
    f'total_purchase_{display_currency.lower()}': f'총 매입액({symbol})',
    f'total_profit_{display_currency.lower()}': f'총 손익({symbol})',
    'total_return_rate': '수익률(%)',
    'account_count': '계좌수',
    'asset_count': '자산수'
}

display_df = history_df[display_columns].copy()
display_df = display_df.rename(columns=column_names)

# 스타일링
styled_df = display_df.style.format({
    f'총 평가액({symbol})': f'{symbol}{{:,.0f}}',
    f'총 매입액({symbol})': f'{symbol}{{:,.0f}}',
    f'총 손익({symbol})': f'{symbol}{{:,.0f}}',
    '수익률(%)': '{:.2f}%'
}).background_gradient(
    cmap='RdYlGn', 
    subset=['수익률(%)'], 
    vmin=-10, 
    vmax=10
)

st.dataframe(styled_df, use_container_width=True, hide_index=True)

# 특정 날짜 자산별 상세 조회
st.divider()
st.subheader("🔍 특정 시간 자산별 상세")

selected_datetime = st.selectbox(
    "날짜시간 선택",
    options=history_df['record_datetime'].tolist(),
    index=len(history_df)-1,  # 최신 날짜시간 기본 선택
    format_func=lambda x: pd.to_datetime(x).strftime('%Y-%m-%d %H:%M:%S')
)

if selected_datetime:
    asset_history = db_manager.get_asset_history(selected_datetime)
    
    if not asset_history.empty:
        st.write(f"**{pd.to_datetime(selected_datetime).strftime('%Y-%m-%d %H:%M:%S')} 기준 자산별 현황**")
        
        # 자산별 데이터 표시
        asset_display_columns = [
            'account_id', 'ticker', 'name', 'asset_type', 'quantity',
            f'value_{display_currency.lower()}', 'return_rate'
        ]
        
        asset_column_names = {
            'account_id': '계좌ID',
            'ticker': '티커',
            'name': '자산명',
            'asset_type': '자산유형',
            'quantity': '수량',
            f'value_{display_currency.lower()}': f'평가액({symbol})',
            'return_rate': '수익률(%)'
        }
        
        asset_display_df = asset_history[asset_display_columns].copy()
        asset_display_df = asset_display_df.rename(columns=asset_column_names)
        
        # 스타일링
        asset_styled_df = asset_display_df.style.format({
            '수량': '{:,.4f}',
            f'평가액({symbol})': f'{symbol}{{:,.0f}}',
            '수익률(%)': '{:.2f}%'
        }).background_gradient(
            cmap='RdYlGn', 
            subset=['수익률(%)'], 
            vmin=-20, 
            vmax=20
        )
        
        st.dataframe(asset_styled_df, use_container_width=True, hide_index=True)
        
        # 자산별 파이 차트
        fig_pie = px.pie(
            asset_history,
            values=f'value_{display_currency.lower()}',
            names='ticker',
            title=f"{pd.to_datetime(selected_datetime).strftime('%Y-%m-%d %H:%M:%S')} 자산 구성비"
        )
        
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.warning(f"{pd.to_datetime(selected_datetime).strftime('%Y-%m-%d %H:%M:%S')}에 대한 자산별 데이터가 없습니다.")

# 푸터
st.divider()
st.caption(f"마지막 업데이트: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 수동 저장 버튼 (관리용)
if st.button("🔄 현재 포트폴리오 수동 저장", help="현재 포트폴리오 상태를 DB에 수동으로 저장합니다"):
    try:
        # 현재 포트폴리오 페이지의 저장 로직 import
        sys.path.append("/home/jungmo/apps/visualize_stocks")
        from portfolio_scheduler import save_daily_portfolio
        
        save_daily_portfolio()
        st.success("포트폴리오가 성공적으로 저장되었습니다!")
        st.rerun()
    except Exception as e:
        st.error(f"저장 실패: {e}")
