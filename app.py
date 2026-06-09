import streamlit as st
import psycopg2
from streamlit_cookies_controller import CookieController

# 🔑 반드시 최상단에 배치 (Streamlit 레이아웃 설정)
st.set_page_config(layout="wide")

# 🍪 브라우저 쿠키 컨트롤러 초기화 (최상단)
controller = CookieController()

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


app_title = st.secrets["auth"].get("app_title", "🏓 탁구 대회 통합 관리 시스템")
st.title(app_title)

# ==========================================
# 🔄 쿠키 기반 영구 세션 처리 기능
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.user_name = None
    st.session_state.user_id = None

# 🔒 [복원 패치] 주소창 직접 접속 & 새로고침 시 브라우저 쿠키에서 정보 복구
saved_user_id = controller.get('user_id')
saved_user_role = controller.get('user_role')
saved_user_name = controller.get('user_name')

if saved_user_id and not st.session_state.logged_in:
    st.session_state.logged_in = True
    st.session_state.user_id = int(saved_user_id) if str(saved_user_id).isdigit() else saved_user_id
    st.session_state.user_role = saved_user_role
    st.session_state.user_name = saved_user_name


# 세션 생성 함수 (메모리 + 브라우저 쿠키 동시 저장)
def create_app_session(user_id, role, name):
    st.session_state.logged_in = True
    st.session_state.user_id = user_id
    st.session_state.user_role = role
    st.session_state.user_name = name

    # 브라우저 구석에 쿠키로 구워두기 (주소창 직접 접속 대비용)
    controller.set('user_id', str(user_id))
    controller.set('user_role', role)
    controller.set('user_name', name)


# 세션 제거 함수 (로그아웃 시 전체 파괴)
def delete_app_session():
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.user_role = None
    st.session_state.user_name = None

    # 쿠키 제거
    controller.remove('user_id')
    controller.remove('user_role')
    controller.remove('user_name')


# ----------------- 로그인 및 가입 화면 -----------------
if not st.session_state.logged_in:
    st.subheader("🔑 시스템 접속을 위해 로그인해 주세요")
    col_login, col_notice = st.columns([1, 1])

    with col_login:
        login_type = st.radio("로그인 유형 선택", ["일반 회원 로그인", "관리자 로그인"], horizontal=True)

        if login_type == "일반 회원 로그인":
            with st.form("member_login_form"):
                phone_input = st.text_input("📱 전화번호 (ID)", placeholder="예: 01012345678")
                pwd_input = st.text_input("🔒 비밀번호", type="password", placeholder="최초 로그인 시 전화번호와 동일")

                if st.form_submit_button("회원 로그인", use_container_width=True):
                    if phone_input and pwd_input:
                        try:
                            conn = get_db_connection()
                            cur = conn.cursor()
                            cur.execute(
                                "SELECT id, name FROM members WHERE phone = %s AND password = %s AND status = 'active'",
                                (phone_input.strip(), pwd_input.strip()))
                            res = cur.fetchone()
                            cur.close()
                            conn.close()

                            if res:
                                create_app_session(res[0], "member", res[1])
                                st.success(f"🎉 {res[1]} 회원님 환영합니다!")
                                st.rerun()
                            else:
                                st.error("❌ 로그인 실패: 정보가 일치하지 않거나 탈퇴 처리된 계정입니다.")
                        except Exception as e:
                            st.error(f"DB 오류 발생: {e}")
                    else:
                        st.warning("전화번호와 비밀번호를 모두 입력해주세요.")

        else:
            with st.form("admin_login_form"):
                admin_pwd = st.text_input("🔒 관리자 마스터 패스워드 입력", type="password")
                if st.form_submit_button("관리자 로그인", use_container_width=True):
                    if admin_pwd == st.secrets["auth"]["admin_password"]:
                        create_app_session(0, "admin", "관리자")
                        st.success("👑 관리자 권한으로 로그인되었습니다.")
                        st.rerun()
                    else:
                        st.error("❌ 비밀번호가 일치하지 않습니다.")

    with col_notice:
        st.info("💡 **동호회 신규 회원 가입**\n일반 회원은 아래 양식을 통해 스스로 정보를 등록한 후 service 로그인이 가능합니다.")
        st.markdown("---")
        st.caption("🆕 **자유 회원 가입 양식**")
        with st.form("public_register_form", clear_on_submit=True):
            reg_name = st.text_input("이름")
            reg_grade = st.selectbox("본인 부수", list(range(1, 12)), index=7, format_func=lambda x: f"{x}부")
            reg_phone = st.text_input("연락처 (숫자만)", placeholder="예: 01012345678")
            st.caption("ℹ️ *회원 가입 시 입력하신 전화번호가 초기 비밀번호로 자동 설정됩니다.*")

            if st.form_submit_button("📝 위 정보로 신규 가입 완료하기", use_container_width=True):
                if reg_name and reg_phone:
                    try:
                        conn = get_db_connection()
                        cur = conn.cursor()
                        cur.execute(
                            "INSERT INTO members (name, grade, phone, password, status) VALUES (%s, %s, %s, %s, 'active')",
                            (reg_name.strip(), reg_grade, reg_phone.strip(), reg_phone.strip())
                        )
                        conn.commit()
                        cur.close()
                        conn.close()
                        st.success(f"✅ '{reg_name}'님 회원 가입 완료! 설정된 아이디/비밀번호로 로그인해 주세요.")
                    except:
                        st.error("❌ 가입 실패 (이미 등록된 연락처이거나 데이터 오류)")
                else:
                    st.warning("모든 필드를 입력해 주세요.")
    st.stop()

# ----------------- 상단 유저 정보 및 로그아웃 바 -----------------
c_user, c_logout = st.columns([8, 1])
with c_user:
    st.markdown(
        f"👤 접속자: **{st.session_state.user_name}** ({'👑 관리자' if st.session_state.user_role == 'admin' else '🏃 일반 회원'})")
with c_logout:
    if st.button("🚪 로그아웃", use_container_width=True):
        delete_app_session()
        st.rerun()

# ==========================================
# 🛡️ 로그인 권한별 탭 동적 노출 제어 (오리지널 형태 보존)
# ==========================================
if st.session_state.user_role == "admin":
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
    tab_my_info, tab_play, tab_ranking = st.tabs([
        "👤 내 정보 수정",
        "🎮 대회 진행 및 결과 기록",
        "📊 연도별 통합 랭킹"
    ])
    with tab_my_info:
        run_tab_member(get_db_connection)
    with tab_play:
        run_tab_play(get_db_connection)
    with tab_ranking:
        run_tab_ranking(get_db_connection)