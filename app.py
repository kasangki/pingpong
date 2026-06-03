import streamlit as st
import psycopg2

# 분리된 탭 모듈 가져오기
from tabs.tab_member import run_tab_member
from tabs.tab_manage import run_tab_manage
from tabs.tab_play import run_tab_play
from tabs.tab_ranking import run_tab_ranking


# ==========================================
# 0. 데이터베이스 연결 함수
# ==========================================
def get_db_connection():
    return psycopg2.connect(
        host=st.secrets["postgres"]["host"],
        database=st.secrets["postgres"]["database"],
        user=st.secrets["postgres"]["user"],
        password=st.secrets["postgres"]["password"],
        port=st.secrets["postgres"]["port"]
    )


st.set_page_config(layout="wide")
app_title = st.secrets["auth"].get("app_title", "🏓 탁구 대회 통합 관리 시스템")
st.title(app_title)

# 세션 상태 초기화
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None

# ----------------- 로그인 화면 -----------------
if not st.session_state.logged_in:
    st.subheader("🔑 시스템 접속을 위해 로그인해 주세요")
    login_type = st.radio("로그인 유형 선택", ["일반 회원 (전화번호 로그인)", "관리자 로그인"], horizontal=True)

    if login_type == "일반 회원 (전화번호 로그인)":
        phone_input = st.text_input("📱 전화번호 입력", placeholder="예: 01012345678")
        if st.button("회원 로그인", use_container_width=True):
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("SELECT name FROM members WHERE phone = %s", (phone_input.strip(),))
                res = cur.fetchone()
                cur.close()
                conn.close()

                if res:
                    st.session_state.logged_in = True
                    st.session_state.user_role = "member"
                    st.session_state.user_name = res[0]
                    st.success(f"🎉 {res[0]} 회원님 환영합니다!")
                    st.rerun()
                else:
                    st.error("❌ 등록되지 않은 전화번호입니다. 관리자에게 등록을 요청하세요.")
            except Exception as e:
                st.error(f"DB 오류 발생: {e}")
    else:
        admin_pwd = st.text_input("🔒 관리자 마스터 패스워드 입력", type="password")
        if st.button("관리자 로그인", use_container_width=True):
            if admin_pwd == st.secrets["auth"]["admin_password"]:
                st.session_state.logged_in = True
                st.session_state.user_role = "admin"
                st.session_state.user_name = "관리자"
                st.success("👑 관리자 권한으로 로그인되었습니다.")
                st.rerun()
            else:
                st.error("❌ 비밀번호가 일치하지 않습니다.")
    st.stop()

# ----------------- 상단 유저 정보 및 로그아웃 바 -----------------
c_user, c_logout = st.columns([8, 1])
with c_user:
    st.markdown(
        f"👤 접속자: **{st.session_state.user_name}** ({'👑 관리자' if st.session_state.user_role == 'admin' else '🏃 일반 회원'})")
with c_logout:
    if st.button("🚪 로그아웃", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_role = None
        st.session_state.user_name = None
        st.rerun()

# ==========================================
# 🛡️ 로그인 권한별 탭 동적 노출 제어 (핵심 변경)
# ==========================================
if st.session_state.user_role == "admin":
    # 👑 관리자 로그인 시: 모든 탭 노출
    tab_member, tab_manage_tour, tab_play, tab_ranking = st.tabs([
        "👥 회원 DB 관리",
        "🏆 대회 생성 및 명단 선발",
        "🎮 대회 진행 및 결과 기록",
        "📊 연도별 통합 랭킹"
    ])

    with tab_member:
        run_tab_member(get_db_connection)
    with tab_manage_tour:
        run_tab_manage(get_db_connection)
    with tab_play:
        run_tab_play(get_db_connection)
    with tab_ranking:
        run_tab_ranking(get_db_connection)

else:
    # 🏃 일반 회원 로그인 시: 회원관리, 대회생성 탭을 완전히 지우고 실시간 진행/랭킹만 노출
    tab_play, tab_ranking = st.tabs([
        "🎮 대회 진행 및 결과 기록",
        "📊 연도별 통합 랭킹"
    ])

    with tab_play:
        run_tab_play(get_db_connection)
    with tab_ranking:
        run_tab_ranking(get_db_connection)