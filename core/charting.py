import streamlit as st
import pandas as pd
import mplfinance as mpf

def _prepare_squeeze_plots(chart_data, panel_idx):
    """스퀴즈 모멘텀 지표를 위한 addplot 리스트를 생성합니다."""
    plots = []
    
    sqz_hist = chart_data['SQZ_VAL_CUSTOM']
    is_positive = sqz_hist >= 0
    momentum_increasing = sqz_hist.diff().fillna(0) >= 0

    # 4가지 조건에 따라 히스토그램 바를 위한 4개의 개별 시리즈 생성
    sqz_pos_inc = sqz_hist.where(is_positive & momentum_increasing)
    sqz_pos_dec = sqz_hist.where(is_positive & ~momentum_increasing)
    sqz_neg_inc = sqz_hist.where(~is_positive & momentum_increasing)
    sqz_neg_dec = sqz_hist.where(~is_positive & ~momentum_increasing)

    # Squeeze ON/OFF 신호 (0선에 마커 표시) - 색상 수정
    # 검은색 십자가: 스퀴즈 ON (변동성 축소)
    sqz_on_marker = pd.Series(0, index=chart_data.index).where(chart_data['SQZ_ON_CUSTOM'])
    # 초록색 십자가: 스퀴즈 OFF (변동성 확장)
    sqz_off_marker = pd.Series(0, index=chart_data.index).where(chart_data['SQZ_OFF_CUSTOM'])
    
    plots.extend([
        mpf.make_addplot(sqz_pos_inc, type='bar', panel=panel_idx, color='lightgreen', title='Squeeze Momentum'),
        mpf.make_addplot(sqz_pos_dec, type='bar', panel=panel_idx, color='darkgreen'),
        mpf.make_addplot(sqz_neg_inc, type='bar', panel=panel_idx, color='lightcoral'),
        mpf.make_addplot(sqz_neg_dec, type='bar', panel=panel_idx, color='darkred'),
        mpf.make_addplot(sqz_on_marker, type='scatter', panel=panel_idx, color='black', marker='+'),
        mpf.make_addplot(sqz_off_marker, type='scatter', panel=panel_idx, color='green', marker='+')
    ])
    return plots


def create_stock_chart(df, user_inputs):
    """계산된 데이터와 사용자 입력을 바탕으로 mplfinance 차트를 생성합니다."""
    
    chart_data = df.tail(200)
    add_plots = []
    fill_between_args = None
    panel_idx = 2 # 패널 0: 가격, 패널 1: 거래량

    # 볼린저 밴드 (메인 차트)
    if user_inputs['show_bbands'] and all(c in chart_data.columns for c in ['BBU_20_2.0', 'BBL_20_2.0']):
        fill_between_args = dict(y1=chart_data['BBU_20_2.0'].values, y2=chart_data['BBL_20_2.0'].values, color='grey', alpha=0.2)
        add_plots.extend([
            mpf.make_addplot(chart_data['BBU_20_2.0'], color='grey', linestyle='--', width=0.7),
            mpf.make_addplot(chart_data['BBL_20_2.0'], color='grey', linestyle='--', width=0.7)
        ])

    # RSI
    if user_inputs['show_rsi'] and 'RSI_14' in chart_data.columns:
        add_plots.append(mpf.make_addplot(chart_data['RSI_14'], panel=panel_idx, color='green', title='RSI(14)'))
        panel_idx += 1

    # MACD
    if user_inputs['show_macd'] and all(c in chart_data.columns for c in ['MACD_12_26_9', 'MACDs_12_26_9', 'MACDh_12_26_9']):
        add_plots.extend([
            mpf.make_addplot(chart_data['MACD_12_26_9'], panel=panel_idx, color='blue', title='MACD'),
            mpf.make_addplot(chart_data['MACDs_12_26_9'], panel=panel_idx, color='red', linestyle='--'),
            mpf.make_addplot(chart_data['MACDh_12_26_9'], type='bar', panel=panel_idx, color='gray', alpha=0.5)
        ])
        panel_idx += 1

    # Stochastic
    if user_inputs['show_stoch'] and all(c in chart_data.columns for c in ['STOCHk_14_3_3', 'STOCHd_14_3_3']):
        add_plots.extend([
            mpf.make_addplot(chart_data['STOCHk_14_3_3'], panel=panel_idx, color='blue', title='Stochastic'),
            mpf.make_addplot(chart_data['STOCHd_14_3_3'], panel=panel_idx, color='red', linestyle='--')
        ])
        panel_idx += 1

    # Squeeze Momentum
    buy_signal_prices = pd.Series(dtype=float) # 빈 시리즈로 초기화
    sell_signal_prices = pd.Series(dtype=float) # 빈 시리즈로 초기화
    if user_inputs['show_squeeze'] and all(c in chart_data.columns for c in ['SQZ_VAL_CUSTOM', 'SQZ_ON_CUSTOM', 'SQZ_OFF_CUSTOM']):
        # 스퀴즈 모멘텀 하단 패널 생성
        add_plots.extend(_prepare_squeeze_plots(chart_data, panel_idx))
        
        # --- 매수/매도 신호 로직 강화 ---
        # 1. 스퀴즈가 "터지는" 시점 (이전 봉: ON, 현재 봉: OFF)
        squeeze_fired = (chart_data['SQZ_ON_CUSTOM'].shift(1) & chart_data['SQZ_OFF_CUSTOM'])

        # 2. 모멘텀 방향성 확인 (증가 또는 감소)
        momentum_increasing = chart_data['SQZ_VAL_CUSTOM'].diff().fillna(0) >= 0

        # 3. 매수 신호: 스퀴즈가 터지고, 모멘텀이 양수이며, 모멘텀이 증가 추세(또는 유지)일 때
        buy_signals = squeeze_fired & (chart_data['SQZ_VAL_CUSTOM'] > 0) & momentum_increasing
        buy_signal_prices = chart_data['Low'][buy_signals] * 0.98
        
        # 4. 매도 신호: 스퀴즈가 터지고, 모멘텀이 음수이며, 모멘텀이 감소 추세일 때
        sell_signals = squeeze_fired & (chart_data['SQZ_VAL_CUSTOM'] < 0) & ~momentum_increasing
        sell_signal_prices = chart_data['High'][sell_signals] * 1.02
        # --- 신호 계산 끝 ---

        panel_idx += 1

    # 차트 스타일 및 속성 설정
    mc = mpf.make_marketcolors(up='r', down='b', inherit=True)
    s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')
    panel_ratios = [3, 1] + [1.5] * (panel_idx - 2)

    plot_kwargs = dict(
        type='candle', style=s, title=f'\n{user_inputs["ticker"]} Stock Price',
        ylabel='Price ($)', volume=True, addplot=add_plots,
        panel_ratios=panel_ratios, figsize=(20, 10), returnfig=True
    )
    if fill_between_args:
        plot_kwargs['fill_between'] = fill_between_args

    # 차트 생성
    fig, axes = mpf.plot(chart_data, **plot_kwargs)
    
    # --- 이동평균선 및 매매 신호 수동 추가 ---
    ax_main = axes[0]
    
    # 이동평균선 추가
    for ma_period in user_inputs['selected_ma_periods']:
        ma_name = f'MA{ma_period}'
        style = st.session_state.ma_styles[ma_name]
        ma_col = f'MA_{ma_period}'
        if ma_col in chart_data.columns:
            ax_main.plot(range(len(chart_data.index)), chart_data[ma_col], 
                         color=style['color'], label=ma_name, 
                         linewidth=style['linewidth'], linestyle=style['linestyle'])
    
    # 스퀴즈 모멘텀 매매 신호 추가
    if user_inputs['show_squeeze']:
        date_to_loc = pd.Series(range(len(chart_data.index)), index=chart_data.index)

        buy_points = buy_signal_prices.dropna()
        if not buy_points.empty:
            buy_x_coords = date_to_loc[buy_points.index]
            ax_main.scatter(buy_x_coords, buy_points.values, marker='^', color='lime', s=120, zorder=10, label='Buy Signal')

        sell_points = sell_signal_prices.dropna()
        if not sell_points.empty:
            sell_x_coords = date_to_loc[sell_points.index]
            ax_main.scatter(sell_x_coords, sell_points.values, marker='v', color='red', s=120, zorder=10, label='Sell Signal')

    # 범례 표시
    if user_inputs['selected_ma_periods'] or (user_inputs['show_squeeze'] and (not buy_signal_prices.dropna().empty or not sell_signal_prices.dropna().empty)):
        ax_main.legend(loc='upper left')

    return fig, axes
