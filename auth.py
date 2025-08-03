"""
Streamlit 애플리케이션용 간단한 인증 모듈
"""

import streamlit as st
import hashlib
import hmac
import os

streamlit_id = os.environ.get('STREAMLIT_ID')
streamlit_password = os.environ.get('STREAMLIT_PASSWORD')

# 간단한 사용자 데이터베이스 (실제 환경에서는 더 안전한 방법 사용)
USERS = {
    streamlit_id: {"password": streamlit_password, "name": "Administrator"}
}

def check_password(username, password):
    """사용자명과 비밀번호를 확인합니다."""
    if username in USERS:
        return USERS[username]["password"] == password
    return False

def render_authentication_ui():
    """
    인증 UI를 렌더링하고 인증 상태를 확인합니다.
    
    Returns:
        bool: 인증 성공 여부
    """
    # 세션 상태 초기화
    if 'authentication_status' not in st.session_state:
        st.session_state.authentication_status = None
    if 'username' not in st.session_state:
        st.session_state.username = None

    # 이미 인증된 경우
    if st.session_state.authentication_status:
        # 상단에 사용자 정보와 로그아웃 버튼 표시
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            user_name = USERS.get(st.session_state.username, {}).get("name", st.session_state.username)
            st.write(f'환영합니다 *{user_name}*님! 👋')
        
        with col3:
            if st.button('로그아웃'):
                st.session_state.authentication_status = None
                st.session_state.username = None
                st.rerun()
        
        st.divider()
        return True

    # 로그인 폼
    st.markdown("## 🔐 로그인")
    
    with st.form("login_form"):
        username = st.text_input("사용자명")
        password = st.text_input("비밀번호", type="password")
        submit_button = st.form_submit_button("로그인")
        
        if submit_button:
            if check_password(username, password):
                st.session_state.authentication_status = True
                st.session_state.username = username
                st.success("로그인 성공!")
                st.rerun()
            else:
                st.error("사용자명 또는 비밀번호가 올바르지 않습니다")

    return False

def require_authentication(func):
    """
    데코레이터: 함수 실행 전에 인증을 요구합니다.
    """
    def wrapper(*args, **kwargs):
        if render_authentication_ui():
            return func(*args, **kwargs)
        else:
            st.stop()
    return wrapper
