import streamlit as st
import json
import os

STYLE_SETTINGS_FILE = 'ma_styles.json'

def get_default_styles():
    """기본 이동평균선 스타일을 반환합니다."""
    return {
        ma: {'color': color, 'linewidth': 1.0, 'linestyle': '-'}
        for ma, color in {
            'MA5': '#FFBF00',   # Amber
            'MA20': '#00BFFF',  # DeepSkyBlue
            'MA60': '#9400D3',  # DarkViolet
            'MA120': '#32CD32', # LimeGreen
            'MA200': '#FF4500'  # OrangeRed
        }.items()
    }

def load_styles():
    """JSON 파일에서 스타일 설정을 불러옵니다. 파일이 없으면 기본값을 사용합니다."""
    default_styles = get_default_styles()
    if os.path.exists(STYLE_SETTINGS_FILE):
        try:
            with open(STYLE_SETTINGS_FILE, 'r') as f:
                loaded_styles = json.load(f)
                # 기본 스타일에 저장된 값을 덮어써서 새로운 MA가 추가되어도 호환되도록 함
                styles = default_styles.copy()
                for ma_name, style_values in loaded_styles.items():
                    if ma_name in styles:
                        styles[ma_name].update(style_values)
                return styles
        except (json.JSONDecodeError, IOError):
            return default_styles
    return default_styles

def save_styles(styles_to_save):
    """스타일 설정을 JSON 파일에 저장합니다."""
    try:
        with open(STYLE_SETTINGS_FILE, 'w') as f:
            json.dump(styles_to_save, f, indent=4)
    except IOError as e:
        st.warning(f"색상 설정을 저장하는 데 실패했습니다: {e}")
