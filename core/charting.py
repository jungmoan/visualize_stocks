import streamlit as st
import pandas as pd
import mplfinance as mpf
from matplotlib.ticker import FuncFormatter

def _prepare_squeeze_plots(chart_data, panel_idx):
    """스퀴즈 모멘텀 지표를 위한 addplot 리스트를 생성합니다."""
    plots = []
    
    sqz_hist = chart_data['SQZ_VAL_CUSTOM']
    is_positive = sqz_hist >= 0
    momentum_increasing = sqz_hist.diff().fillna(0) >= 0

    sqz_pos_inc = sqz_hist.where(is_positive & momentum_increasing)
    sqz_pos_dec = sqz_hist.where(is_positive & ~momentum_increasing)
    sqz_neg_inc = sqz_hist.where(~is_positive & momentum_increasing)
    sqz_neg_dec = sqz_hist.where(~is_positive & ~momentum_increasing)

    sqz_on_marker = pd.Series(0, index=chart_data.index).where(chart_data['SQZ_ON_CUSTOM'])
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


def create_stock_chart(df, user_inputs, company_name, currency='USD'):
    """계산된 데이터와 사용자 입력을 바탕으로 mplfinance 차트를 생성합니다."""
    
    chart_data = df.tail(200)
    add_plots = []
    fill_between_args = None
    panel_idx = 2

    # --- Y축 레이블 및 통화 기호 결정 ---
    if currency == 'KRW':
        ylabel = 'Price (KRW)'
    else: # 기본값 USD 및 기타 통화
        ylabel = f'Price ({currency})'

    # --- 보조지표 패널 생성 ---
    if user_inputs['show_bbands'] and all(c in chart_data.columns for c in ['BBU_20_2.0', 'BBL_20_2.0']):
        fill_between_args = dict(y1=chart_data['BBU_20_2.0'].values, y2=chart_data['BBL_20_2.0'].values, color='grey', alpha=0.2)
        add_plots.extend([
            mpf.make_addplot(chart_data['BBU_20_2.0'], color='grey', linestyle='--', width=0.7),
            mpf.make_addplot(chart_data['BBL_20_2.0'], color='grey', linestyle='--', width=0.7)
        ])

    if user_inputs['show_rsi'] and 'RSI_14' in chart_data.columns:
        add_plots.append(mpf.make_addplot(chart_data['RSI_14'], panel=panel_idx, color='green', title='RSI(14)'))
        panel_idx += 1

    if user_inputs['show_macd'] and all(c in chart_data.columns for c in ['MACD_12_26_9', 'MACDs_12_26_9', 'MACDh_12_26_9']):
        add_plots.extend([
            mpf.make_addplot(chart_data['MACD_12_26_9'], panel=panel_idx, color='blue', title='MACD'),
            mpf.make_addplot(chart_data['MACDs_12_26_9'], panel=panel_idx, color='red', linestyle='--'),
            mpf.make_addplot(chart_data['MACDh_12_26_9'], type='bar', panel=panel_idx, color='gray', alpha=0.5)
        ])
        panel_idx += 1

    if user_inputs['show_stoch'] and all(c in chart_data.columns for c in ['STOCHk_14_3_3', 'STOCHd_14_3_3']):
        add_plots.extend([
            mpf.make_addplot(chart_data['STOCHk_14_3_3'], panel=panel_idx, color='blue', title='Stochastic'),
            mpf.make_addplot(chart_data['STOCHd_14_3_3'], panel=panel_idx, color='red', linestyle='--')
        ])
        panel_idx += 1

    buy_signal_prices = pd.Series(dtype=float)
    sell_signal_prices = pd.Series(dtype=float)
    if user_inputs['show_squeeze'] and all(c in chart_data.columns for c in ['SQZ_VAL_CUSTOM', 'SQZ_ON_CUSTOM', 'SQZ_OFF_CUSTOM']):
        add_plots.extend(_prepare_squeeze_plots(chart_data, panel_idx))
        
        squeeze_fired = (chart_data['SQZ_ON_CUSTOM'].shift(1) & chart_data['SQZ_OFF_CUSTOM'])
        momentum_increasing = chart_data['SQZ_VAL_CUSTOM'].diff().fillna(0) >= 0
        buy_signals = squeeze_fired & (chart_data['SQZ_VAL_CUSTOM'] > 0) & momentum_increasing
        buy_signal_prices = chart_data['Low'][buy_signals] * 0.98 
        
        prev_momentum = chart_data['SQZ_VAL_CUSTOM'].shift(1)
        current_momentum = chart_data['SQZ_VAL_CUSTOM']
        sell_signals = (prev_momentum >= 0) & (current_momentum < 0)
        sell_signal_prices = chart_data['High'][sell_signals] * 1.02
        
        panel_idx += 1

    # --- 차트 생성 ---
    mc = mpf.make_marketcolors(up='r', down='b', inherit=True)
    s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')
    panel_ratios = [3, 1] + [1.5] * (panel_idx - 2)

    plot_kwargs = dict(
        type='candle', style=s,
        volume=True, addplot=add_plots,
        panel_ratios=panel_ratios, figsize=(20, 10), returnfig=True
    )
    if fill_between_args:
        plot_kwargs['fill_between'] = fill_between_args

    fig, axes = mpf.plot(chart_data, **plot_kwargs)
    
    # --- (핵심 수정) 차트 후처리: 폰트 크기 및 제목, 레이블 설정 ---
    ax_main = axes[0]
    ax_volume = axes[2] # 거래량 패널

    # 1. 메인 타이틀 설정
    fig.suptitle(f'{company_name} ({user_inputs["ticker"]}) Price', fontsize=24, y=0.95)

    # 2. Y축 레이블 폰트 크기 설정
    ax_main.set_ylabel(ylabel, fontsize=14)
    ax_volume.set_ylabel('Volume', fontsize=14)

    # 3. Y축 틱(눈금) 레이블 폰트 크기 및 포맷 설정
    def comma_formatter(x, pos):
        return f'{int(x):,}'
    ax_main.yaxis.set_major_formatter(FuncFormatter(comma_formatter))
    ax_main.tick_params(axis='y', labelsize=12)

    # 4. X축 틱(날짜) 레이블 폰트 크기 설정
    ax_main.tick_params(axis='x', labelsize=12)
    # 모든 하단 패널의 x축 레이블 크기도 동일하게 설정
    for i in range(2, len(axes), 2):
        axes[i].tick_params(axis='x', labelsize=12)

    # --- 이동평균선, 신호, 최신가 라인 추가 ---
    for ma_period in user_inputs['selected_ma_periods']:
        ma_name = f'MA{ma_period}'
        style = st.session_state.ma_styles[ma_name]
        ma_col = f'MA_{ma_period}'
        if ma_col in chart_data.columns:
            ax_main.plot(range(len(chart_data.index)), chart_data[ma_col], 
                         color=style['color'], label=ma_name, 
                         linewidth=style['linewidth'], linestyle=style['linestyle'])
    
    if user_inputs['show_squeeze']:
        date_to_loc = pd.Series(range(len(chart_data.index)), index=chart_data.index)
        buy_points = buy_signal_prices.dropna()
        if not buy_points.empty:
            ax_main.scatter(date_to_loc[buy_points.index], buy_points.values, marker='^', color='lime', s=120, zorder=10, label='SMI Buy (Squeeze Fire)')
        sell_points = sell_signal_prices.dropna()
        if not sell_points.empty:
            ax_main.scatter(date_to_loc[sell_points.index], sell_points.values, marker='v', color='red', s=120, zorder=10, label='SMI Sell (Zero-Cross)')

    latest_price = chart_data['Close'].iloc[-1]
    latest_price_formatted = f'{latest_price:,.2f}'

    ax_main.axhline(y=latest_price, color='dodgerblue', linestyle='--', linewidth=1, alpha=0.7)
    ax_main.text(1.01, latest_price, latest_price_formatted,
                 transform=ax_main.get_yaxis_transform(),
                 verticalalignment='center',
                 color='white',
                 bbox=dict(facecolor='dodgerblue', alpha=0.9, pad=2, boxstyle='round,pad=0.2'),
                 zorder=20)

    if user_inputs['selected_ma_periods'] or (user_inputs['show_squeeze'] and (not buy_signal_prices.dropna().empty or not sell_signal_prices.dropna().empty)):
        ax_main.legend(loc='upper left')

    return fig, axes
