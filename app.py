import streamlit as st
import psycopg2
import pandas as pd
from streamlit_cookies_controller import CookieController

# 🔑 최상단 레이아웃 설정
st.set_page_config(layout="wide")

# 🎨 럭셔리 네온 다크 UI 디자인 시스템 매핑 (비주얼 고도화 및 모바일 클라우드 패치)
st.markdown("""
    <style>
    /* 1. 기본 브랜딩 배지 및 여백 제거 */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container {padding-top: 2rem !important; background-color: #0B0F19;}

    /* 2. 전체 배경 및 글로벌 텍스트 밸런스 */
    body {
        background-color: #0B0F19;
        color: #E2E8F0;
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* 3. 로그인 / 회원가입 세련된 네온 카드 레이아웃 */
    div[data-testid="stForm"] {
        background: linear-gradient(145deg, #131A2C 0%, #0E1424 100%);
        border: 1px solid rgba(99, 102, 241, 0.2) !important;
        border-radius: 18px !important;
        padding: 30px !important;
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5), 0 0 25px rgba(99, 102, 241, 0.05) !important;
        transition: all 0.3s ease-in-out;
    }
    div[data-testid="stForm"]:hover {
        border-color: rgba(99, 102, 241, 0.45) !important;
        box-shadow: 0 16px 45px rgba(0, 0, 0, 0.6), 0 0 35px rgba(99, 102, 241, 0.15) !important;
        transform: translateY(-2px);
    }

    /* 4. 입력 폼(Input) 필드 모던 스타일링 */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #1A233A !important;
        color: #FFFFFF !important;
        border: 1px solid #2E3A59 !important;
        border-radius: 10px !important;
        padding: 12px 16px !important;
        font-size: 16px !important;
        transition: all 0.25s ease;
    }
    .stTextInput input:focus, .stSelectbox div[data-baseweb="select"]:focus-within {
        border-color: #6366F1 !important;
        box-shadow: 0 0 12px rgba(99, 102, 241, 0.4) !important;
        background-color: #1E294B !important;
    }

    /* 5. 화려한 그라데이션 메인 버튼 효과 */
    button[data-testid="stFormSubmitButton"] {
        background: linear-gradient(90deg, #4F46E5 0%, #7C3AED 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 14px 24px !important;
        font-size: 17px !important;
        font-weight: 700 !important;
        letter-spacing: 0.05em !important;
        box-shadow: 0 4px 20px rgba(79, 70, 229, 0.4) !important;
        transition: all 0.3s ease !important;
        cursor: pointer !important;
    }
    button[data-testid="stFormSubmitButton"]:hover {
        background: linear-gradient(90deg, #5A52E7 0%, #8B4BF6 100%) !important;
        box-shadow: 0 6px 25px rgba(99, 102, 241, 0.6) !important;
        transform: scale(1.01);
    }
    button[data-testid="stFormSubmitButton"]:active {
        transform: scale(0.99);
    }

    /* 6. 라디오 버튼 그룹 프리미엄 세그먼트 스타일 */
    div[data-testid="stRadio"] label {
        background-color: #131A2C;
        border: 1px solid #2E3A59;
        padding: 10px 20px !important;
        border-radius: 10px !important;
        margin-right: 12px !important;
        transition: all 0.2s ease;
    }
    div[data-testid="stRadio"] label:hover {
        border-color: #6366F1;
        background-color: #1A233A;
    }
    div[data-testid="stRadio"] label[data-checked="true"] {
        background: rgba(99, 102, 241, 0.15) !important;
        border-color: #6366F1 !important;
    }

    /* 7. 아이디/비밀번호 찾기 익스팬더 투명도 배치 */
    div[data-testid="stExpander"] {
        background-color: #0E1424 !important;
        border: 1px solid #2E3A59 !important;
        border-radius: 12px !important;
        margin-top: 15px !important;
    }

    /* 8. 타이틀 전용 럭셔리 텍스트 효과 */
    .main-title {
        font-size: 42px !important; 
        font-weight: 900; 
        background: linear-gradient(90deg, #FFFFFF 0%, #CBD5E1 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0 4px 20px rgba(0,0,0,0.3);
        margin-bottom: 25px;
    }
    .sub-title {
        color: #818CF8;
        font-size: 24px !important;
        font-weight: 800;
        margin-bottom: 15px;
        border-left: 4px solid #6366F1;
        padding-left: 12px;
    }

    /* 🛠️ [박스 흔적 제거 패치] 비활성화 상태이거나 라디오 버튼이 1개일 때 테두리 컨테이너 선을 아예 소멸시킴 */
    div[data-testid="stRadio"] {
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
        padding: 0 !important;
    }

    /* 🚀 [모바일 클라우드 서버 전용 완벽 차단 패치] */
    /* 클라우드 호스팅 서버가 모바일 화면 하단에 강제 주입하는 모든 iframe, 배너, 액션 버튼의 흔적을 원천 소멸시킵니다. */
    iframe[title="Streamlit Cloud Footer"],
    div[class*="StyledActionButton"],
    div[class*="stActionButton"],
    .viewerBadge,
    #streamlitViewerFooter,
    footer,
    [data-testid="stStatusWidget"],
    div[data-testid="stDecoration"] {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        height: 0 !important;
        max-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        pointer-events: none !important;
    }

    /* 모바일 브라우저에서 하단 툴바가 가리고 있던 빈 공백 영역(바닥 패딩)을 정상화합니다. */
    .stApp {
        bottom: 0 !important;
        height: 100vh !important;
        padding-bottom: 0px !important;
    }
    </style>
""", unsafe_allow_html=True)

# 🍪 브라우저 쿠키 컨트롤러 초기화
controller = CookieController()

# 분리된 탭 모듈 가져오기
try:
    from tabs.tab_member import run_tab_member
    from tabs.tab_manage import run_tab_manage
    from tabs.tab_play import run_tab_play
    from tabs.tab_ranking import run_tab_ranking
except ImportError:
    def run_tab_member(conn):
        st.info("👥 회원 관리 페이지")


    def run_tab_manage(conn):
        st.info("🏆 대회 생성 페이지")


    def run_tab_play(conn):
        st.info("🎮 경기 기록 페이지")


    def run_tab_ranking(conn):
        st.info("📊 랭킹 조회 페이지")


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


# ==========================================
# 🔄 쿠키 기반 영구 세션 처리 기능
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.club_id = None
    st.session_state.club_name = None
    st.session_state.user_role = None
    st.session_state.user_name = None
    st.session_state.user_id = None

# 쿠키 복원 로직
saved_club_id = controller.get('club_id')
saved_club_name = controller.get('club_name')
saved_user_id = controller.get('user_id')
saved_user_role = controller.get('user_role')
saved_user_name = controller.get('user_name')

if saved_user_id and not st.session_state.logged_in:
    st.session_state.logged_in = True
    st.session_state.club_id = int(saved_club_id) if saved_club_id and saved_club_id != 'None' else None
    st.session_state.club_name = saved_club_name
    st.session_state.user_id = int(saved_user_id) if str(saved_user_id).isdigit() else saved_user_id
    st.session_state.user_role = saved_user_role
    st.session_state.user_name = saved_user_name


def create_app_session(club_id, club_name, user_id, role, name):
    st.session_state.logged_in = True
    st.session_state.club_id = club_id
    st.session_state.club_name = club_name
    st.session_state.user_id = user_id
    st.session_state.user_role = role
    st.session_state.user_name = name

    controller.set('club_id', str(club_id))
    controller.set('club_name', str(club_name))
    controller.set('user_id', str(user_id))
    controller.set('user_role', role)
    controller.set('user_name', name)


def delete_app_session():
    st.session_state.logged_in = False
    st.session_state.club_id = None
    st.session_state.club_name = None
    st.session_state.user_id = None
    st.session_state.user_role = None
    st.session_state.user_name = None

    controller.remove('club_id')
    controller.remove('club_name')
    controller.remove('user_id')
    controller.remove('user_role')
    controller.remove('user_name')


# ==========================================
# 🎯 로그인 상태에 따른 동적 타이틀 분기 출력
# ==========================================
if st.session_state.logged_in and st.session_state.user_role == "super_admin":
    st.markdown("<h1 class='main-title'>🛡️ 플랫폼 총괄 최고 슈퍼 관리자 룸</h1>", unsafe_allow_html=True)
elif st.session_state.logged_in and st.session_state.club_name:
    st.markdown(f"<h1 class='main-title'>🏓 {st.session_state.club_name}</h1>", unsafe_allow_html=True)
else:
    app_title = st.secrets["auth"].get("app_title", "🏓 멀티 탁구동호회 통합 관리 플랫폼")
    st.markdown(f"<h1 class='main-title'>{app_title}</h1>", unsafe_allow_html=True)

# ==========================================
# 🖥️ 로그인 / 동호회 생성 / 회원 가입 통합 인터페이스
# ==========================================
if not st.session_state.logged_in:

    # ⚙️ ⭐ [SaaS 인프라 롤백 스위치] 나중에 동호회 개설 기능을 되살릴 때 아래 False를 True로만 바꾸시면 원클릭 부활합니다!
    is_dev_mode = False

    if is_dev_mode:
        auth_mode = st.radio("⚙️ 원하시는 작업을 선택하세요", ["기존 동호회 로그인 및 가입", "🏢 우리 탁구 동호회 신규 개설하기"], horizontal=True)
    else:
        # 단일 고정 모드일 때는 라디오 위젯을 아예 실행하지 않아 컨테이너 사각형 테두리를 원천 파괴합니다.
        auth_mode = "기존 동호회 로그인 및 가입"

    st.markdown("<br>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # 🏢 A 구역: 신규 동호회(클럽) 개설 신청 폼
    # -------------------------------------------------------------
    if auth_mode == "🏢 우리 탁구 동호회 신규 개설하기":
        st.markdown("<p class='sub-title'>📝 전국 탁구동호회 플랫폼 입점 및 신규 신청</p>", unsafe_allow_html=True)
        st.warning("🚨 동호회 신청 후 플랫폼 총괄 최고관리자의 '최종 승인'이 완료되어야 정상 로그인이 가능합니다.")

        with st.form("create_club_form", clear_on_submit=True):
            reg_club_name = st.text_input("🏢 동호회 / 탁구 클럽명", placeholder="예: 용호메이트 탁구클럽")
            col_mid, col_mpw = st.columns(2)
            with col_mid:
                reg_manager_id = st.text_input("🔑 관리자 로그인 ID", placeholder="예: yongho_master")
            with col_mpw:
                reg_manager_pwd = st.text_input("🔒 관리자 비밀번호", type="password", placeholder="최소 4자 이상 안전한 비밀번호")

            reg_manager_phone = st.text_input("📱 대표자 연락처 (숫자만)", placeholder="예: 01012345678")
            reg_address = st.text_input("📍 동호회 주소 / 구장 위치", placeholder="예: 부산광역시 남구...")

            col_g, col_jm = st.columns(2)
            with col_g:
                reg_max_grade = st.selectbox("🏓 동호회 내 최대 부수 제한 설정", list(range(1, 13)), index=10,
                                             format_func=lambda x: f"{x}부")
            with col_jm:
                reg_join_method = st.selectbox("🔒 일반회원 가입 승인 방식", ["auto", "manual"],
                                               format_func=lambda x: "자동 승인 (즉시가입)" if x == "auto" else "관리자 승인제")

            if st.form_submit_button("🚀 탁구 동호회 개설 신청서 제출", use_container_width=True):
                if reg_club_name and reg_manager_id and reg_manager_pwd and reg_manager_phone:
                    try:
                        conn = get_db_connection()
                        cur = conn.cursor()

                        cur.execute(
                            "SELECT id FROM clubs WHERE (manager_id = %s OR club_name = %s) AND status IN ('active', 'pending')",
                            (reg_manager_id.strip(), reg_club_name.strip()))
                        if cur.fetchone():
                            st.error("❌ 이미 신청 진행 중이거나 사용 중인 동호회 이름/ID입니다.")
                            cur.close()
                            conn.close()
                        else:
                            cur.execute("""
                                INSERT INTO clubs (club_name, manager_id, manager_password, manager_phone, address, max_grade, join_method, status)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending') RETURNING id
                            """, (reg_club_name.strip(), reg_manager_id.strip(), reg_manager_pwd.strip(),
                                  reg_manager_phone.strip(), reg_address.strip(), reg_max_grade, reg_join_method))
                            new_club_id = cur.fetchone()[0]

                            cur.execute("""
                                INSERT INTO members (club_id, name, grade, username, phone, password, status, role)
                                VALUES (%s, %s, %s, %s, %s, %s, 'active', 'admin')
                            """, (
                                new_club_id, f"{reg_club_name} 관리자", 1, reg_manager_id.strip(),
                                reg_manager_phone.strip(),
                                reg_manager_pwd.strip()))

                            conn.commit()
                            cur.close()
                            conn.close()
                            st.success(f"📩 [{reg_club_name}] 동호회 개설 신청서가 정상 접수되었습니다!")
                    except Exception as e:
                        st.error(f"동호회 개설 실패 (DB 오류): {e}")
                else:
                    st.warning("필수 입력 항목들을 모두 채워주세요.")

    # -------------------------------------------------------------
    # 🔑 B 구역: 프리미엄 단일 통합 로그인 창 및 ID/PW 찾기 모듈
    # -------------------------------------------------------------
    else:
        try:
            conn = get_db_connection()
            df_clubs = pd.read_sql("SELECT id, club_name FROM clubs WHERE status = 'active' ORDER BY id DESC", conn)
            conn.close()
        except:
            df_clubs = pd.DataFrame()

        club_list = df_clubs.to_dict('records')

        col_login, col_notice = st.columns([1, 1], gap="large")

        with col_login:
            st.markdown("<p class='sub-title'>🔑 통합 로그인</p>", unsafe_allow_html=True)
            with st.form("unified_login_form"):
                user_id_input = st.text_input("👤 로그인 아이디", placeholder="개인 고유 아이디 입력")
                pwd_input = st.text_input("🔒 비밀번호", type="password")

                if st.form_submit_button("로그인", use_container_width=True):
                    if user_id_input and pwd_input:
                        try:
                            conn = get_db_connection()
                            cur = conn.cursor()
                            query = """
                                SELECT m.id, m.name, m.role, m.club_id, c.club_name 
                                FROM members m
                                LEFT JOIN clubs c ON m.club_id = c.id
                                WHERE m.username = %s AND m.password = %s AND m.status = 'active'
                            """
                            cur.execute(query, (user_id_input.strip(), pwd_input.strip()))
                            res = cur.fetchone()
                            cur.close()
                            conn.close()

                            if res:
                                m_id, m_name, m_role, m_club_id, m_club_name = res
                                if m_role == "super_admin":
                                    create_app_session(None, "플랫폼 본부", m_id, "super_admin", m_name)
                                    st.success("🛡️ 최고 수퍼 권한으로 로그인되었습니다!")
                                    st.rerun()
                                else:
                                    if m_club_name is None:
                                        st.error("❌ 현재 이용이 일시 중지된 동호회입니다.")
                                    else:
                                        create_app_session(m_club_id, m_club_name, m_id, m_role, m_name)
                                        st.success(f"🎉 환영합니다! ({m_club_name} 소속)")
                                        st.rerun()
                            else:
                                st.error("❌ 로그인 실패: 아이디 또는 비밀번호가 일치하지 않습니다.")
                        except Exception as e:
                            st.error(f"로그인 처리 중 오류 발생: {e}")
                    else:
                        st.warning("아이디와 비밀번호를 모두 입력해주세요.")

            with st.expander("🔍 아이디 / 비밀번호를 잊으셨나요?"):
                find_mode = st.radio("찾으실 정보를 고르세요", ["아이디 찾기", "비밀번호 재설정"], horizontal=True)

                if find_mode == "아이디 찾기":
                    find_name = st.text_input("이름 입력", key="f_name")
                    find_phone = st.text_input("가입 연락처 입력 (숫자만)", key="f_phone")
                    if st.button("아이디 조회하기", use_container_width=True):
                        if find_name and find_phone:
                            try:
                                conn = get_db_connection()
                                cur = conn.cursor()
                                cur.execute(
                                    "SELECT username FROM members WHERE name = %s AND phone = %s AND status = 'active'",
                                    (find_name.strip(), find_phone.strip()))
                                row = cur.fetchone()
                                cur.close()
                                conn.close()
                                if row:
                                    raw_username = row[0]
                                    masked_username = raw_username[:3] + "*" * (len(raw_username) - 3) if len(
                                        raw_username) > 3 else raw_username[:1] + "**"
                                    st.info(f"💡 회원님의 아이디는 **[{masked_username}]** 입니다.")
                                else:
                                    st.error("❌ 일치하는 회원 정보가 존재하지 않습니다.")
                            except Exception as e:
                                st.error(f"오류: {e}")
                        else:
                            st.warning("이름과 연락처를 모두 입력해 주세요.")

                else:
                    reset_id = st.text_input("가입 아이디 입력", key="r_id")
                    reset_name = st.text_input("이름 입력", key="r_name")
                    reset_phone = st.text_input("가입 연락처 입력", key="r_phone")
                    new_password_input = st.text_input("🔒 새로 사용할 신규 비밀번호", type="password", key="r_pw")

                    if st.button("비밀번호 안전 변경 실행", use_container_width=True):
                        if reset_id and reset_name and reset_phone and new_password_input:
                            try:
                                conn = get_db_connection()
                                cur = conn.cursor()
                                cur.execute(
                                    "SELECT id FROM members WHERE username = %s AND name = %s AND phone = %s AND status = 'active'",
                                    (reset_id.strip(), reset_name.strip(), reset_phone.strip()))
                                user_exists = cur.fetchone()

                                if user_exists:
                                    cur.execute("UPDATE members SET password = %s WHERE id = %s",
                                                (new_password_input.strip(), user_exists[0]))
                                    conn.commit()
                                    st.success("🎉 비밀번호가 변경되었습니다! 가입한 아이디로 로그인해 주세요.")
                                else:
                                    st.error("❌ 회원 정보가 일치하지 않아 비밀번호를 재설정할 수 없습니다.")
                                cur.close()
                                conn.close()
                            except Exception as e:
                                st.error(f"오류: {e}")
                        else:
                            st.warning("모든 항목을 입력하셔야 비밀번호 변경이 가능합니다.")

        with col_notice:
            st.markdown("<p class='sub-title'>📝 신규 회원 자가 가입</p>", unsafe_allow_html=True)
            if club_list:
                selected_club = st.selectbox("", club_list, format_func=lambda x: x['club_name'])
                with st.form("public_register_form", clear_on_submit=True):
                    reg_name = st.text_input("이름")
                    reg_grade = st.selectbox("본인 부수", list(range(1, 12)), index=7, format_func=lambda x: f"{x}부")
                    reg_username = st.text_input("👤 희망 로그인 아이디", placeholder="예: pingpong77 (로그인용)")
                    reg_pwd = st.text_input("🔒 로그인 비밀번호", type="password", placeholder="로그인에 사용할 암호")
                    reg_phone = st.text_input("📱 전화번호 (연락 및 주소록용, 분실 찾기 시 인증용)")

                    if st.form_submit_button("해당 동호회 가입 신청 완료", use_container_width=True):
                        if reg_name and reg_username and reg_pwd and reg_phone:
                            try:
                                conn = get_db_connection()
                                cur = conn.cursor()
                                cur.execute(
                                    "INSERT INTO members (club_id, name, grade, username, phone, password, status, role) VALUES (%s, %s, %s, %s, %s, %s, 'active', 'member')",
                                    (selected_club['id'], reg_name.strip(), reg_grade, reg_username.strip(),
                                     reg_phone.strip(), reg_pwd.strip())
                                )
                                conn.commit()
                                cur.close()
                                conn.close()
                                st.success(f"✅ 회원 가입이 완료되었습니다! 가입한 아이디로 로그인해 주세요.")
                            except:
                                st.error("❌ 이미 이 동호회에 존재하거나 사용 중인 아이디입니다.")
                        else:
                            st.warning("모든 필드를 빠짐없이 입력해 주세요.")
            else:
                st.info("현재 개설되어 승인 완료된 동호회가 존재하지 않습니다.")
    st.stop()

# ==========================================
# 🚪 로그인 이후 레이아웃 및 작동 탭 분기 (기존 보존)
# ==========================================
c_user, c_logout = st.columns([8, 1])
with c_user:
    st.markdown(
        f"👤 사용자: **{st.session_state.user_name}** | 소속: **{st.session_state.club_name}** | 등급: **{st.session_state.user_role.upper()}**")
with c_logout:
    if st.button("🚪 로그아웃", use_container_width=True):
        delete_app_session()
        st.rerun()

if st.session_state.user_role == "super_admin":
    st.subheader("🏢 전국 탁구동호회 신규 입점/승인 대기 리스트")
    try:
        conn = get_db_connection()
        df_pending = pd.read_sql(
            "SELECT id, club_name, manager_id, manager_phone, address, created_at FROM clubs WHERE status = 'pending' ORDER BY id ASC",
            conn)
        conn.close()
    except Exception as e:
        df_pending = pd.DataFrame()
        st.error(f"대기 데이터 로드 중 오류: {e}")

    if df_pending.empty:
        st.success("✨ 현재 처리할 신규 동호회 승인 대기 건이 없습니다.")
    else:
        for _, row in df_pending.iterrows():
            c_info, c_ok, c_no = st.columns([6, 1.5, 1.5])
            with c_info:
                st.markdown(
                    f"📍 **{row['club_name']}** (ID: `{row['manager_id']}`)  \n• 연락처: {row['manager_phone']} | 주소: {row['address']}")
            with c_ok:
                if st.button("✅ 최종 승인 허가", key=f"ok_{row['id']}", use_container_width=True, type="primary"):
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("UPDATE clubs SET status = 'active' WHERE id = %s", (row['id'],))
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.rerun()
            with c_no:
                if st.button("❌ 개설 반려/거절", key=f"no_{row['id']}", use_container_width=True):
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("UPDATE clubs SET status = 'deleted', deleted_at = CURRENT_TIMESTAMP WHERE id = %s",
                                (row['id'],))
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.rerun()
            st.markdown("---")

elif st.session_state.user_role == "admin":
    with st.expander("🏢 우리 동호회 정보 관리 및 설정 제어판"):
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT club_name, manager_phone, address, max_grade, join_method FROM clubs WHERE id = %s",
                        (st.session_state.club_id,))
            club_data = cur.fetchone()
            cur.close()
            conn.close()
        except:
            club_data = None

        if club_data:
            c_name, c_phone, c_address, c_max_grade, c_join_method = club_data
            with st.form("update_club_info_form_main"):
                up_club_name = st.text_input("🏢 동호회 / 탁구 클럽명 변경", value=c_name)
                up_manager_phone = st.text_input("📱 대표자 연락처 수정", value=c_phone)
                up_address = st.text_input("📍 구장 위치 / 주소", value=c_address)

                col1, col2 = st.columns(2)
                with col1:
                    grade_list = list(range(1, 13))
                    default_grade_idx = grade_list.index(c_max_grade) if c_max_grade in grade_list else 10
                    up_max_grade = st.selectbox("🏓 참가 허용 최대 부수", grade_list, index=default_grade_idx,
                                                format_func=lambda x: f"{x}부")
                with col2:
                    default_method_idx = 0 if c_join_method == 'auto' else 1
                    up_join_method = st.selectbox("🔒 신규회원 가입 방식", ["auto", "manual"], index=default_method_idx,
                                                  format_func=lambda x: "자동 승인" if x == "auto" else "운영진 승인제")

                if st.form_submit_button("💾 설정 및 동호회 정보 업데이트 저장", use_container_width=True):
                    if up_club_name and up_manager_phone:
                        try:
                            conn = get_db_connection()
                            cur = conn.cursor()
                            cur.execute("""
                                UPDATE clubs SET club_name = %s, manager_phone = %s, address = %s, max_grade = %s, join_method = %s WHERE id = %s
                            """, (up_club_name.strip(), up_manager_phone.strip(), up_address.strip(), up_max_grade,
                                  up_join_method, st.session_state.club_id))
                            conn.commit()
                            cur.close()
                            conn.close()
                            st.session_state.club_name = up_club_name.strip()
                            st.success("🎉 정보가 성공적으로 변경되었습니다!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"오류: {e}")

    tab_member, tab_manage_tour, tab_play, tab_ranking = st.tabs(
        ["👥 회원 DB 관리", "🏆 대회 생성 및 명단 선발", "🎮 대회 진행 및 결과 기록", "📊 연도별 통합 랭킹"])
    with tab_member:
        run_tab_member(get_db_connection)
    with tab_manage_tour:
        run_tab_manage(get_db_connection)
    with tab_play:
        run_tab_play(get_db_connection)
    with tab_ranking:
        run_tab_ranking(get_db_connection)

else:
    tab_my_info, tab_play, tab_ranking = st.tabs(["👤 내 정보 수정", "🎮 대회 진행 및 결과 기록", "📊 연도별 통합 랭킹"])
    with tab_my_info:
        run_tab_member(get_db_connection)
    with tab_play:
        run_tab_play(get_db_connection)
    with tab_ranking:
        run_tab_ranking(get_db_connection)