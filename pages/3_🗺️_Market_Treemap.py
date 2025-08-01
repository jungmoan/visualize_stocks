import streamlit as st
import auth  # 인증 모듈 추가

# 페이지 레이아웃 설정
st.set_page_config(layout="wide", page_title="마켓 맵")

# --- 인증 확인 ---
if not auth.render_authentication_ui():
    st.stop()

# 페이지 제목과 설명
st.title("🗺️ 마켓 트라맵")
st.write(
    "Finviz에서 제공하는 시장 지도를 보여줍니다. "
    "각 사각형의 크기는 시가총액을, 색상은 주가 등락을 나타냅니다. (녹색: 상승, 적색: 하락)"
)

# --- 시장 종류 선택 라디오 버튼 추가 ---
st.divider()

# 시장 선택 옵션 (표시될 이름: Finviz URL 파라미터)
market_options = {
    "S&P 500": "sp500",
    "ETF": "etf",
    "암호화폐 (Crypto)": "crypto",
}

# 라디오 버튼을 가로로 배치 (horizontal=True)
selected_market_label = st.radio(
    "시장 종류 선택 (Market Type):",
    options=list(market_options.keys()),
    horizontal=True,
)

# 선택된 시장에 해당하는 URL 파라미터 가져오기
selected_market_code = market_options[selected_market_label]

# 동적으로 Finviz 트라맵 URL 생성
finviz_url = f"https://finviz.com/map.ashx?t={selected_market_code}"

st.divider()

# --- Finviz 맵으로 이동하는 링크 버튼 ---
st.info("아래 버튼을 클릭하면 새 탭에서 선택한 시장의 트라맵을 확인할 수 있습니다.")

# 링크 버튼을 가운데 정렬하기 위해 컬럼 사용
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    st.link_button(
        f"🔗 **{selected_market_label}** 맵 보러가기 (새 탭)",
        finviz_url,
        use_container_width=True
    )


# 데이터 출처 명시
st.caption("데이터 출처: [Finviz](https://finviz.com)")
