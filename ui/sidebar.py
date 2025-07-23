import streamlit as st
from utils import settings

def display():
    """사이드바 UI를 표시하고 사용자 입력을 반환합니다."""
    
    st.sidebar.header('차트 설정')


    # --- 보유종목/관심종목 불러오기 ---
    import pandas as pd
    import os
    asset_tickers, watchlist_tickers = [], []
    asset_path = os.path.join('private', 'asset.csv')
    watchlist_path = os.path.join('private', 'watchlist.csv')
    if os.path.exists(asset_path):
        try:
            asset_df = pd.read_csv(asset_path)
            asset_tickers = sorted(set(str(t).strip().upper() for t in asset_df['ticker'].dropna().unique()))
        except Exception:
            pass
    if os.path.exists(watchlist_path):
        try:
            wl_df = pd.read_csv(watchlist_path)
            watchlist_tickers = sorted(set(str(t).strip().upper() for t in wl_df['ticker'].dropna().unique()))
        except Exception:
            pass

    st.sidebar.subheader('Select Ticker')
    col1, col2 = st.sidebar.columns(2)
    selected_asset = col1.selectbox('From My Assets', [''] + asset_tickers, index=0, key='asset_ticker')
    selected_watch = col2.selectbox('From Watchlist', [''] + watchlist_tickers, index=0, key='watchlist_ticker')
    # 기존 텍스트 입력도 유지
    ticker_input = st.sidebar.text_input('Or type Ticker', value='GOOGL', help='예: AAPL, GOOG, MSFT').upper()

    # 우선순위: 보유종목 > 관심종목 > 직접입력
    ticker = selected_asset or selected_watch or ticker_input

    # --- 이동평균선(MA) 선택 ---
    st.sidebar.subheader('이동평균선')
    ma_options = {
        'MA5': 5, 'MA20': 20, 'MA60': 60, 'MA120': 120, 'MA200': 200, 'EMA200': 200
    }
    
    selected_ma_periods = []
    # 기본값으로 20일, 200일선 선택
    default_ma_selection = ['MA20', 'MA200']
    for ma_name, ma_period in ma_options.items():
        if st.sidebar.checkbox(ma_name, value=(ma_name in default_ma_selection)):
            selected_ma_periods.append(ma_name)

    # --- 이동평균선 스타일 설정 ---
    with st.sidebar.expander("⚙️ 이동평균선 스타일 설정"):
        for ma_name, _ in ma_options.items():
            # 기본 스타일이 없으면 자동 추가
            if ma_name not in st.session_state.ma_styles:
                st.session_state.ma_styles[ma_name] = {
                    'color': '#888888' if 'EMA' in ma_name else '#1976d2',
                    'linewidth': 2.0,
                    'linestyle': '-' if 'EMA' in ma_name else '-',
                }
            st.write(f"**{ma_name}**")
            cols = st.columns(3)
            current_style = st.session_state.ma_styles[ma_name]

            # UI 위젯들
            new_color = cols[0].color_picker("색상", current_style['color'], key=f"{ma_name}_color", label_visibility="collapsed")
            new_width = cols[1].number_input("굵기", min_value=0.5, max_value=5.0, value=current_style['linewidth'], step=0.1, key=f"{ma_name}_width", label_visibility="collapsed")
            new_style_str = cols[2].selectbox("스타일", options=['-', '--', '-.', ':'], format_func=lambda x: {'-':'Solid', '--':'Dashed', '-.':'Dash-Dot', ':':'Dotted'}[x], index=['-', '--', '-.', ':'].index(current_style['linestyle']), key=f"{ma_name}_style", label_visibility="collapsed")

            # 변경 사항이 있으면 세션 상태 업데이트 및 파일 저장
            if (new_color != current_style['color'] or
                new_width != current_style['linewidth'] or
                new_style_str != current_style['linestyle']):
                st.session_state.ma_styles[ma_name]['color'] = new_color
                st.session_state.ma_styles[ma_name]['linewidth'] = new_width
                st.session_state.ma_styles[ma_name]['linestyle'] = new_style_str
                settings.save_styles(st.session_state.ma_styles)
                # st.experimental_rerun()

    # --- 보조지표 선택 ---
    st.sidebar.subheader('보조지표')
    show_bbands = st.sidebar.checkbox('볼린저 밴드 (Bollinger Bands)')
    show_rsi = st.sidebar.checkbox('상대강도지수 (RSI)')
    show_macd = st.sidebar.checkbox('MACD')
    show_stoch = st.sidebar.checkbox('스토캐스틱 (Stochastic)')
    show_squeeze = st.sidebar.checkbox('스퀴즈 모멘텀 (Squeeze Momentum)')

    # 사용자의 모든 입력을 딕셔너리로 묶어 반환
    return {
        'ticker': ticker,
        'selected_ma_periods': selected_ma_periods,
        'show_bbands': show_bbands,
        'show_rsi': show_rsi,
        'show_macd': show_macd,
        'show_stoch': show_stoch,
        'show_squeeze': show_squeeze
    }
