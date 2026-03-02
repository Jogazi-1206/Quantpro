import streamlit as st
import time

def render_auth_screen(db):
    """로그인 및 회원가입 화면을 렌더링하는 함수"""
    
    st.markdown("<div style='height: 10vh;'></div>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: white; font-size: 3rem;'>QuantPro Terminal</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #9CA3AF; margin-bottom: 40px;'>AI 기반 글로벌 퀀트 투자 분석 플랫폼</p>", unsafe_allow_html=True)

    # 화면 중앙에 배치하기 위해 컬럼 분할 (1:2:1 비율)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    
    with col2:
        # 로그인 / 회원가입 탭 생성
        tab_login, tab_signup = st.tabs(["🔑 로그인", "📝 회원가입"])

        # --- [로그인 탭] ---
        with tab_login:
            with st.form("login_form"):
                username = st.text_input("아이디", placeholder="아이디를 입력하세요")
                password = st.text_input("비밀번호", type="password", placeholder="비밀번호를 입력하세요")
                submit_btn = st.form_submit_button("로그인", use_container_width=True)

                if submit_btn:
                    if not username or not password:
                        st.warning("아이디와 비밀번호를 모두 입력해주세요.")
                    else:
                        # DB 검증 로직 호출
                        user_id = db.verify_user(username, password)
                        if user_id:
                            # [핵심] 로그인 성공 시 session_state에 정보 저장!
                            st.session_state.user_id = user_id
                            st.session_state.username = username
                            st.success(f"환영합니다, {username}님! 터미널에 접속 중입니다...")
                            time.sleep(1) # 부드러운 화면 전환을 위한 딜레이
                            st.rerun() # 앱 새로고침하여 메인 화면으로 이동
                        else:
                            st.error("아이디 또는 비밀번호가 일치하지 않습니다.")

        # --- [회원가입 탭] ---
        with tab_signup:
            with st.form("signup_form"):
                new_username = st.text_input("새 아이디", placeholder="사용할 아이디를 입력하세요")
                new_password = st.text_input("새 비밀번호", type="password", placeholder="비밀번호를 입력하세요")
                new_password_check = st.text_input("비밀번호 확인", type="password", placeholder="비밀번호를 다시 입력하세요")
                signup_btn = st.form_submit_button("회원가입 완료", use_container_width=True)

                if signup_btn:
                    if not new_username or not new_password:
                        st.warning("모든 항목을 입력해주세요.")
                    elif new_password != new_password_check:
                        st.error("비밀번호가 일치하지 않습니다.")
                    else:
                        # DB 가입 로직 호출
                        success, msg = db.create_user(new_username, new_password)
                        if success:
                            st.success("🎉 회원가입이 완료되었습니다! '로그인' 탭으로 이동하여 접속해주세요.")
                            st.balloons()
                        else:
                            st.error(msg) # 예: "이미 존재하는 아이디입니다"