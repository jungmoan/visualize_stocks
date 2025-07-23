import pandas as pd
import pandas_ta as ta

def _calculate_squeeze_momentum(df, bb_length=20, kc_length=20, kc_mult=1.5, use_tr=True):
    """
    LazyBear의 Squeeze Momentum Indicator 로직을 기반으로 스퀴즈 모멘텀을 계산합니다.
    pandas-ta의 기본 squeeze와 달라 직접 구현합니다.
    """
    df_copy = df.copy()
    
    # 1. 볼린저 밴드 (켈트너 채널 승수 사용)
    basis = ta.sma(df_copy['Close'], length=bb_length)
    dev = kc_mult * ta.stdev(df_copy['Close'], length=bb_length)
    df_copy['BBU_LB'] = basis + dev
    df_copy['BBL_LB'] = basis - dev

    # 2. 켈트너 채널 (True Range의 SMA 사용)
    ma = ta.sma(df_copy['Close'], length=kc_length)
    tr = ta.true_range(df_copy['High'], df_copy['Low'], df_copy['Close']) if use_tr else (df_copy['High'] - df_copy['Low'])
    rangema = ta.sma(tr, length=kc_length)
    df_copy['KCU_LB'] = ma + rangema * kc_mult
    df_copy['KCL_LB'] = ma - rangema * kc_mult

    # 3. 스퀴즈 ON/OFF/NO 조건
    df_copy['SQZ_ON_CUSTOM'] = (df_copy['BBL_LB'] > df_copy['KCL_LB']) & (df_copy['BBU_LB'] < df_copy['KCU_LB'])
    df_copy['SQZ_OFF_CUSTOM'] = (df_copy['BBL_LB'] < df_copy['KCL_LB']) & (df_copy['BBU_LB'] > df_copy['KCU_LB'])
    df_copy['SQZ_NO_CUSTOM'] = ~df_copy['SQZ_ON_CUSTOM'] & ~df_copy['SQZ_OFF_CUSTOM']

    # 4. 모멘텀 값 (Linear Regression)
    highest_high = df_copy['High'].rolling(kc_length).max()
    lowest_low = df_copy['Low'].rolling(kc_length).min()
    sma_close = ta.sma(df_copy['Close'], length=kc_length)
    mom_source = df_copy['Close'] - ((highest_high + lowest_low) / 2 + sma_close) / 2
    df_copy['SQZ_VAL_CUSTOM'] = ta.linreg(close=mom_source, length=kc_length)

    return df_copy


def calculate_all_indicators(df, user_inputs):
    """
    원본 데이터프레임과 사용자 입력을 받아 모든 필요한 보조지표를 계산하고 추가합니다.
    """
    df_copy = df.copy()
    
    # 데이터 클리닝 및 타입 변환
    ohlcv_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    for col in ohlcv_cols:
        if col in df_copy.columns:
            df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce')
    df_copy.dropna(subset=ohlcv_cols, inplace=True)

    # 이동평균선 및 EMA 계산
    for ma_name in user_inputs['selected_ma_periods']:
        if str(ma_name).startswith('EMA'):
            period = int(str(ma_name).replace('EMA', ''))
            ema_col = f'EMA_{period}'
            if ema_col not in df_copy.columns:
                df_copy[ema_col] = df_copy['Close'].ewm(span=period, adjust=False).mean()
        else:
            period = int(str(ma_name).replace('MA', ''))
            ma_col = f'MA_{period}'
            if ma_col not in df_copy.columns:
                df_copy[ma_col] = df_copy['Close'].rolling(period).mean()
    
    # 기타 보조지표 계산
    if user_inputs['show_bbands']:
        df_copy.ta.bbands(length=20, append=True)
    if user_inputs['show_rsi']:
        df_copy.ta.rsi(append=True)
    if user_inputs['show_macd']:
        df_copy.ta.macd(append=True)
    if user_inputs['show_stoch']:
        df_copy.ta.stoch(append=True)
    if user_inputs['show_squeeze']:
        df_copy = _calculate_squeeze_momentum(df_copy)
        
    return df_copy
