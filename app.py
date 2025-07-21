import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import pandas_ta as ta
import requests
import json
import os
from datetime import datetime, time
import pytz

# Streamlit 페이지 설정
st.set_page_config(layout="wide", page_title="주식 대시보드")

# 메트릭 폰트 크기 조정을 위한 CSS 주입
st.markdown("""
<style>
[data-testid="stMetricValue"] {
    font-size: 24px;
}
</style>
""", unsafe_allow_html=True)

# --- 스타일 설정 파일 처리 ---
STYLE_SETTINGS_FILE = 'ma_styles.json'

def load_styles(default_styles):
    """JSON 파일에서 스타일 설정을 불러옵니다. 파일이 없거나 손상된 경우 기본값을 반환합니다."""
    if os.path.exists(STYLE_SETTINGS_FILE):
        try:
            with open(STYLE_SETTINGS_FILE, 'r') as f:
                loaded_styles = json.load(f)
                # 기본 스타일 딕셔너리를 복사한 후, 저장된 값으로 업데이트
                # 이렇게 하면 코드에 새로운 MA가 추가되어도 기본값이 유지됨
                styles = default_styles.copy()
                for ma_name, style_values in loaded_styles.items():
                    if ma_name in styles:
                        styles[ma_name].update(style_values)
                return styles
        except (json.JSONDecodeError, IOError):
            return default_styles # 파일이 손상되었거나 읽을 수 없는 경우 기본값 반환
    return default_styles

def save_styles(styles_to_save):
    """스타일 설정을 JSON 파일에 저장합니다."""
    try:
        with open(STYLE_SETTINGS_FILE, 'w') as f:
            json.dump(styles_to_save, f, indent=4)
    except IOError as e:
        st.warning(f"색상 설정을 저장하는 데 실패했습니다: {e}")

# --- 세션 상태 초기화 ---
if 'ma_styles' not in st.session_state:
    default_styles = {
        ma: {'color': color, 'linewidth': 1.0, 'linestyle': '-'}
        for ma, color in {
            'MA5': '#FFBF00',   # Amber
            'MA20': '#00BFFF',  # DeepSkyBlue
            'MA60': '#9400D3',  # DarkViolet
            'MA120': '#32CD32', # LimeGreen
            'MA200': '#FF4500'  # OrangeRed
        }.items()
    }
    st.session_state.ma_styles = load_styles(default_styles)

# --- 사이드바 설정 ---
st.sidebar.header('차트 설정')

# Ticker 입력
ticker_input = st.sidebar.text_input('Ticker', value='AAPL', help='예: AAPL, GOOG, MSFT').upper()
# 사용자가 여러 티커를 입력하는 경우(공백, 콤마 등) 첫 번째 티커만 사용하도록 처리
ticker = ticker_input.split(',')[0].strip().split(' ')[0]

# 이동평균선(MA) 선택
st.sidebar.subheader('이동평균선')
ma_options = {
    'MA5': 5,
    'MA20': 20,
    'MA60': 60,
    'MA120': 120,
    'MA200': 200
}

selected_ma_periods = []
for ma_name, ma_period in ma_options.items():
    if st.sidebar.checkbox(ma_name, value=ma_name in ['MA20', 'MA200']):
        selected_ma_periods.append(ma_period)

# 이동평균선 스타일 설정
with st.sidebar.expander("⚙️ 이동평균선 스타일 설정"):
    # 각 MA에 대한 스타일 설정 UI
    for ma_name, ma_period in ma_options.items():
        st.write(f"**{ma_name}**")
        cols = st.columns(3)
        current_style = st.session_state.ma_styles[ma_name]

        # UI 위젯들
        new_color = cols[0].color_picker("색상", current_style['color'], key=f"{ma_name}_color", label_visibility="collapsed")
        new_width = cols[1].number_input("굵기", min_value=0.5, max_value=5.0, value=current_style['linewidth'], step=0.1, key=f"{ma_name}_width", label_visibility="collapsed")
        new_style_str = cols[2].selectbox("스타일", options=['-', '--', '-.', ':'], format_func=lambda x: {'-':'Solid', '--':'Dashed', '-.':'Dash-Dot', ':':'Dotted'}[x], index=['-', '--', '-.', ':'].index(current_style['linestyle']), key=f"{ma_name}_style", label_visibility="collapsed")

        # 변경 사항 감지 및 저장
        if (new_color != current_style['color'] or
            new_width != current_style['linewidth'] or
            new_style_str != current_style['linestyle']):
            
            st.session_state.ma_styles[ma_name]['color'] = new_color
            st.session_state.ma_styles[ma_name]['linewidth'] = new_width
            st.session_state.ma_styles[ma_name]['linestyle'] = new_style_str
            
            save_styles(st.session_state.ma_styles)

# 보조지표 선택
st.sidebar.subheader('보조지표')
show_bbands = st.sidebar.checkbox('볼린저 밴드 (Bollinger Bands)')
show_rsi = st.sidebar.checkbox('상대강도지수 (RSI)')
show_macd = st.sidebar.checkbox('MACD')
show_stoch = st.sidebar.checkbox('스토캐스틱 (Stochastic)')

# --- 보조 지표 데이터 로드 함수 ---
@st.cache_data(ttl=900) # 15분 캐시
def get_fear_and_greed_index():
    """CNN Fear and Greed 지수를 API를 통해 가져옵니다."""
    try:
        # CNN의 데이터 API를 직접 호출하는 것이 더 안정적입니다.
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        # 일부 서버는 자동화된 요청을 차단하므로 User-Agent 헤더를 추가합니다.
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        score = int(data['fear_and_greed']['score'])
        rating = data['fear_and_greed']['rating'].capitalize()
        #return f"{rating} ({score})"
        return f"{score}", rating # score only
    except Exception as e:
        # 만약 이 코드로도 실패한다면, 아래 에러 메시지를 통해 정확한 원인을 확인할 수 있습니다.
        st.error(f"Fear & Greed 지수 로딩 실패: {e}")
        return "데이터 로드 실패"

@st.cache_data(ttl=900) # 15분 캐시
def get_index_data(ticker_symbol):
    """지정된 티커의 최신 값과 변화량을 가져옵니다."""
    try:
        data = yf.Ticker(ticker_symbol).history(period='2d')
        if len(data) < 2:
            return None, None
        latest_price = data['Close'].iloc[-1]
        previous_price = data['Close'].iloc[-2]
        delta = latest_price - previous_price
        return latest_price, delta
    except Exception:
        # yfinance가 특정 지수 로드에 실패하더라도 전체 대시보드가 멈추지 않도록 함
        return None, None

@st.cache_data(ttl=3600) # 1시간 캐싱
def get_company_name(ticker_symbol):
    """yf.Ticker.info에서 회사 이름을 가져옵니다."""
    try:
        # .info는 요청이 느릴 수 있으므로 캐싱합니다.
        info = yf.Ticker(ticker_symbol).info
        # longName이 있으면 사용하고, 없으면 shortName을 사용합니다.
        name = info.get('longName', info.get('shortName'))
        if not name: # 이름 정보가 없는 경우 Ticker를 그대로 반환합니다.
            return ticker_symbol
        return name
    except Exception:
        # 에러 발생 시(잘못된 Ticker 등) Ticker를 그대로 반환합니다.
        return ticker_symbol

@st.cache_data(ttl=60) # 1분마다 갱신
def get_market_status(timezone_str, open_time, close_time):
    """
    지정된 시간대의 시장 개장 여부와 현지 시간을 반환합니다.
    (주말 여부만 체크하며, 공휴일은 고려하지 않습니다.)
    """
    try:
        tz = pytz.timezone(timezone_str)
        now = datetime.now(tz)
        
        # 주말인지 확인 (월요일=0, 일요일=6)
        is_weekday = now.weekday() < 5
        
        # 거래 시간 내에 있는지 확인
        is_trading_hours = open_time <= now.time() < close_time

        status = "🟢 Open" if is_weekday and is_trading_hours else "🔴 Closed"
        return status, now.strftime('%H:%M')
    except Exception:
        return "Error", "N/A"

# --- 메인 화면 ---

# --- 주요 지표 표시 ---
# 7개의 컬럼을 만들고, 첫 번째 컬럼을 여백으로 사용하여 지표들을 오른쪽에 작게 배치합니다.
col_us, col_kr, col_sp, col_nasdaq, col_kospi, col_usd, col_fg, col_vix = st.columns([1, 1, 1, 1, 1, 1, 1, 1])

with col_us:
    us_status, us_time = get_market_status('America/New_York', time(9, 30), time(16, 0))
    st.metric(label="🇺🇸 미국 (ET)", value=us_status, delta=us_time)

with col_kr:
    kr_status, kr_time = get_market_status('Asia/Seoul', time(9, 0), time(15, 30))
    st.metric(label="🇰🇷 한국 (KST)", value=kr_status, delta=kr_time)

with col_sp:
    sp500_price, sp500_delta = get_index_data('^GSPC')
    if sp500_price is not None:
        st.metric(label="S&P 500", value=f"{sp500_price:,.2f}", delta=f"{sp500_delta:,.2f}")
    else:
        st.metric(label="S&P 500", value="N/A")

with col_nasdaq:
    nasdaq_price, nasdaq_delta = get_index_data('^IXIC')
    if nasdaq_price is not None:
        st.metric(label="나스닥", value=f"{nasdaq_price:,.2f}", delta=f"{nasdaq_delta:,.2f}")
    else:
        st.metric(label="나스닥", value="N/A")

with col_kospi:
    kospi_price, kospi_delta = get_index_data('^KS200')
    if kospi_price is not None:
        st.metric(label="코스피200", value=f"{kospi_price:,.2f}", delta=f"{kospi_delta:,.2f}")
    else:
        st.metric(label="코스피200", value="N/A")

with col_usd:
    usd_krw_price, usd_krw_delta = get_index_data('USDKRW=X')
    if usd_krw_price is not None:
        st.metric(label="USD/KRW", value=f"{usd_krw_price:,.2f}", delta=f"{usd_krw_delta:,.2f}")
    else:
        st.metric(label="USD/KRW", value="N/A")

with col_fg:
    fear_and_greed, rating = get_fear_and_greed_index()
    st.metric(label="Fear & Greed", value=fear_and_greed)

with col_vix:
    vix_price, vix_delta = get_index_data('^VIX')
    if vix_price is not None:
        st.metric(label="VIX", value=f"{vix_price:.2f}", delta=f"{vix_delta:.2f}")
    else:
        st.metric(label="VIX", value="N/A")


company_name = get_company_name(ticker)
# 회사 이름이 Ticker와 다를 경우에만 괄호 안에 Ticker를 함께 표시합니다.
if company_name and company_name.lower() != ticker.lower():
    st.title(f'{company_name} ({ticker}) 주가 차트 대시보드')
else:
    st.title(f'{ticker} 주가 차트 대시보드')
st.divider()

# 데이터 로드 및 에러 처리
@st.cache_data(ttl=3600) # 1시간 동안 데이터 캐싱
def load_data(ticker_symbol):
    # 200일 이평선을 그리려면 최소 200일 + 200일(차트 표시 기간) = 400일 이상의 데이터가 필요하므로 넉넉하게 500일치 다운로드
    return yf.download(ticker_symbol, period='500d', interval='1d')

try:
    with st.spinner('데이터를 불러오는 중입니다...'):
        data = load_data(ticker)

    # yfinance가 단일 티커에 대해 MultiIndex 컬럼을 반환하는 경우에 대한 처리
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
        data = data.loc[:,~data.columns.duplicated()]

    if data.empty:
        st.error(f"'{ticker}'에 대한 데이터를 찾을 수 없습니다. Ticker를 확인해주세요.")
    else:
        df = data.copy()
        
        # --- 데이터 클리닝 및 타입 변환 ---
        ohlcv_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in ohlcv_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        df.dropna(subset=ohlcv_cols, inplace=True)

        # --- 보조지표 및 이동평균선 계산 (전체 데이터프레임에 대해 사전 계산) ---
        # 이동평균선 계산
        for ma in selected_ma_periods:
            df[f'MA_{ma}'] = ta.sma(df['Close'], length=ma)
        
        # 기타 보조지표 계산
        if show_bbands:
            df.ta.bbands(length=20, append=True)
        if show_rsi:
            df.ta.rsi(append=True)
        if show_macd:
            df.ta.macd(append=True)
        if show_stoch:
            df.ta.stoch(append=True)

        # --- 차트 데이터 준비 ---
        chart_data = df.tail(200)

        # --- 추가 플롯(add_plots) 생성 ---
        add_plots = []

        # 보조지표 패널 인덱스는 2부터 시작 (패널 0: 가격, 패널 1: 거래량)
        panel_idx = 2

        # 볼린저 밴드는 메인 차트(패널 0)에 표시
        if show_bbands and all(c in chart_data.columns for c in ['BBU_20_2.0', 'BBL_20_2.0']):
            add_plots.extend([
                mpf.make_addplot(chart_data['BBU_20_2.0'], color='blue', alpha=0.5),
                mpf.make_addplot(chart_data['BBL_20_2.0'], color='blue', alpha=0.5)
            ])

        # RSI
        if show_rsi and 'RSI_14' in chart_data.columns:
            add_plots.append(mpf.make_addplot(chart_data['RSI_14'], panel=panel_idx, color='green', title='RSI'))
            panel_idx += 1

        # MACD
        if show_macd and all(c in chart_data.columns for c in ['MACD_12_26_9', 'MACDs_12_26_9', 'MACDh_12_26_9']):
            add_plots.extend([
                mpf.make_addplot(chart_data['MACD_12_26_9'], panel=panel_idx, color='blue', title='MACD'),
                mpf.make_addplot(chart_data['MACDs_12_26_9'], panel=panel_idx, color='red'),
                mpf.make_addplot(chart_data['MACDh_12_26_9'], type='bar', panel=panel_idx, color='gray', alpha=0.5)
            ])
            panel_idx += 1

        # Stochastic
        if show_stoch and all(c in chart_data.columns for c in ['STOCHk_14_3_3', 'STOCHd_14_3_3']):
            add_plots.extend([
                mpf.make_addplot(chart_data['STOCHk_14_3_3'], panel=panel_idx, color='blue', title='Stochastic'),
                mpf.make_addplot(chart_data['STOCHd_14_3_3'], panel=panel_idx, color='red')
            ])
            panel_idx += 1

        # 차트 스타일 및 속성 설정
        mc = mpf.make_marketcolors(up='r', down='b', inherit=True)
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')

        # 패널 비율 동적 조정
        num_indicator_panels = panel_idx - 2
        panel_ratios = [3, 1] + [1.5] * num_indicator_panels

        # 차트 생성
        fig, axes = mpf.plot(
            chart_data,
            type='candle',
            style=s,
            title=f'\n{ticker} Stock Price',
            ylabel='Price ($)',
            volume=True,
            addplot=add_plots,
            panel_ratios=panel_ratios,
            figsize=(20, 10),
            returnfig=True
        )
        
        # --- 이동평균선과 범례(legend)를 수동으로 추가 ---
        ax_main = axes[0]
        for ma_period in selected_ma_periods:
            ma_name = f'MA{ma_period}'
            style = st.session_state.ma_styles[ma_name]
            ma_col = f'MA_{ma_period}'
            if ma_col in chart_data.columns:
                ax_main.plot(range(len(chart_data.index)), chart_data[ma_col], 
                             color=style['color'], 
                             label=ma_name, 
                             linewidth=style['linewidth'],
                             linestyle=style['linestyle'])
        
        if selected_ma_periods:
            ax_main.legend(loc='upper left')

        # Streamlit에 차트 표시
        st.pyplot(fig)

        # 데이터 테이블 표시
        st.subheader('최근 10일 데이터')
        st.dataframe(chart_data.tail(10).style.format("{:.2f}"))

except Exception as e:
    st.exception(e)
