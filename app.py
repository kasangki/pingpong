import streamlit as st
import psycopg2
import pandas as pd
from streamlit_cookies_controller import CookieController

# 🔑 최상단 레이아웃 설정
st.set_page_config(layout="wide")

# 🍪 브라우저 쿠키 컨트롤러 초기화
controller = CookieController()

# 분리된 탭 모듈 가져오기 (기존 구조 유지)
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
    st.session_state.user_role = None  # super_admin / admin / member
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
# ==========================================
# 🎯 [핵심 패치] 로그인 상태에 따른 동적 타이틀 분기 출력 (글자 크기 확대)
# ==========================================
if st.session_state.logged_in and st.session_state.user_role == "super_admin":
    st.markdown("<h1 style='font-size: 42px !important; font-weight: 900; color: #F8FAFC; margin-bottom: 20px;'>🛡️ 탁구 플랫폼 총괄 최고 슈퍼 관리자 룸</h1>", unsafe_allow_html=True)
elif st.session_state.logged_in and st.session_state.club_name:
    # 💡 로그인 성공 시 동호회 구장 명칭을 거대하고 멋지게 출력합니다.
    st.markdown(f"<h1 style='font-size: 45px !important; font-weight: 900; color: #FFFFFF; text-shadow: 0 4px 12px rgba(79, 70, 229, 0.3); margin-bottom: 20px;'>🏓 {st.session_state.club_name}</h1>", unsafe_allow_html=True)
else:
    # 💡 로그인 전 기본 타이틀 크기 확대
    app_title = st.secrets["auth"].get("app_title", "🏓 멀티 탁구동호회 통합 관리 플랫폼")
    st.markdown(f"<h1 style='font-size: 38px !important; font-weight: 800; color: #F1F5F9; margin-bottom: 25px;'>{app_title}</h1>", unsafe_allow_html=True)

# ==========================================
# 🖥️ 로그인 / 동호회 생성 / 회원 가입 통합 인터페이스
# ==========================================
if not st.session_state.logged_in:

    #auth_mode = st.radio("⚙️ 원하시는 작업을 선택하세요", ["기존 동호회 로그인 및 가입", "🏢 우리 탁구 동호회 신규 개설하기"], horizontal=True)
    auth_mode = st.radio("⚙️ 원하시는 작업을 선택하세요", ["동호회 로그인 및 가입"], horizontal=True)
    st.markdown("---")

    # -------------------------------------------------------------
    # 🏢 A 구역: 신규 동호회(클럽) 개설 신청 폼
    # -------------------------------------------------------------
    if auth_mode == "🏢 우리 탁구 동호회 신규 개설하기":
        st.subheader("📝 전국 탁구동호회 플랫폼 입점 및 신규 신청")
        st.warning("🚨 동호회 신청 후 플랫폼 총괄 최고관리자의 '최종 승인'이 완료되어야 정상 로그인이 가능합니다.")

        with st.form("create_club_form", clear_on_submit=True):
            reg_club_name = st.text_input("🏢 동호회 / 탁구 클럽명", placeholder="예: 용호메이트 탁구클럽")
            col_mid, col_mpw = st.columns(2)
            with col_mid:
                reg_manager_id = st.text_input("🔑 관리자 로그인 ID", placeholder="동호회 관리용 영문/숫자 아이디")
            with col_mpw:
                reg_manager_pwd = st.text_input("🔒 관리자 비밀번호", type="password", placeholder="최소 4자 이상 안전한 비밀번호")

            reg_manager_phone = st.text_input("📱 대표자 연락처 (숫자만)", placeholder="예: 01012345678")
            reg_address = st.text_input("📍 동호회 주소 / 구장 위치", placeholder="예: 부산광역시 남구 용호동...")

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
                            st.error("❌ 이미 신청 진행 중이거나 사용 중인 동호회 이름/관리자 ID입니다.")
                            cur.close()
                            conn.close()
                        else:
                            cur.execute("""
                                INSERT INTO clubs (club_name, manager_id, manager_password, manager_phone, address, max_grade, join_method, status)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending')
                            """, (reg_club_name.strip(), reg_manager_id.strip(), reg_manager_pwd.strip(),
                                  reg_manager_phone.strip(), reg_address.strip(), reg_max_grade, reg_join_method))
                            conn.commit()
                            cur.close()
                            conn.close()
                            st.success(f"📩 [{reg_club_name}] 동호회 개설 신청서가 정상 접수되었습니다! 최고 관리자 승인 후 연락드리겠습니다.")
                    except Exception as e:
                        st.error(f"동호회 개설 실패 (DB 오류): {e}")
                else:
                    st.warning("필수 입력 항목들을 모두 채워주세요.")

    # -------------------------------------------------------------
    # 🔑 B 구역: 기존 동호회 로그인 (수퍼관리자 로그인 히든 패치)
    # -------------------------------------------------------------
    else:
        try:
            conn = get_db_connection()
            df_clubs = pd.read_sql("SELECT id, club_name FROM clubs WHERE status = 'active' ORDER BY id DESC", conn)
            conn.close()
        except:
            df_clubs = pd.DataFrame()

        if df_clubs.empty:
            st.info("현재 시스템에 승인 완료된 동호회가 없습니다. 수퍼 관리자 로그인을 통해 승인을 진행해 주세요.")

        club_list = df_clubs.to_dict('records')
        selected_club = st.selectbox("🏢 탁구 동호회 선택",
                                     club_list if club_list else [{"id": 0, "club_name": "등록 대기 중"}],
                                     format_func=lambda x: x['club_name'])

        st.markdown("<br>", unsafe_allow_html=True)
        col_login, col_notice = st.columns([1, 1])

        with col_login:
            # 💡 [보안 패치] 최고수퍼관리자 라디오 단추를 화면에서 영구 삭제
            login_type = st.radio("로그인 유형 선택", ["일반 회원 로그인", "동호회 관리자 로그인"], horizontal=True)

            # ① 회원 로그인
            if login_type == "일반 회원 로그인" and club_list:
                with st.form("member_login_form"):
                    phone_input = st.text_input("📱 전화번호 (ID)")
                    pwd_input = st.text_input("🔒 비밀번호", type="password")

                    if st.form_submit_button("회원 로그인", use_container_width=True):
                        if phone_input and pwd_input:
                            try:
                                conn = get_db_connection()
                                cur = conn.cursor()
                                cur.execute(
                                    "SELECT id, name FROM members WHERE club_id = %s AND phone = %s AND password = %s AND status = 'active'",
                                    (selected_club['id'], phone_input.strip(), pwd_input.strip()))
                                res = cur.fetchone()
                                cur.close()
                                conn.close()

                                if res:
                                    create_app_session(selected_club['id'], selected_club['club_name'], res[0],
                                                       "member", res[1])
                                    st.success(f"🎉 환영합니다!")
                                    st.rerun()
                                else:
                                    st.error("❌ 정보가 잘못되었거나 승인 대기 계정입니다.")
                            except Exception as e:
                                st.error(f"오류: {e}")

            # ② 동호회 회장 로그인 (여기에 이스터에그 히든 로그인 탑재)
            elif login_type == "동호회 관리자 로그인":
                with st.form("admin_login_form"):
                    admin_id_input = st.text_input("👤 관리자 ID")
                    admin_pwd_input = st.text_input("🔒 패스워드", type="password")

                    if st.form_submit_button("동호회 관리자 로그인", use_container_width=True):
                        # 🤫 [이스터에그 발동 조건] ID가 'super_admin'이면 수퍼 관리자 인증 로직으로 자동 우회 처리
                        if admin_id_input.strip() == "super_admin":
                            sec_su_pwd = st.secrets["auth"].get("super_password", "admin1234")
                            if admin_pwd_input.strip() == sec_su_pwd:
                                create_app_session(None, "플랫폼 본부", -99, "super_admin", "최고 수퍼 관리자")
                                st.success("🛡️ 최고 수퍼 권한으로 히든 로그인 성공!")
                                st.rerun()
                            else:
                                st.error("❌ 마스터 비밀번호 정보가 올바르지 않습니다.")

                        # 일반 동호회 관리자 로그인 프로세스
                        elif club_list:
                            try:
                                conn = get_db_connection()
                                cur = conn.cursor()
                                cur.execute(
                                    "SELECT id, club_name FROM clubs WHERE id = %s AND manager_id = %s AND manager_password = %s AND status = 'active'",
                                    (selected_club['id'], admin_id_input.strip(), admin_pwd_input.strip()))
                                res = cur.fetchone()
                                cur.close()
                                conn.close()

                                if res:
                                    create_app_session(selected_club['id'], res[1], 0, "admin", f"{res[1]} 관리자")
                                    st.rerun()
                                else:
                                    st.error("❌ 정보가 유효하지 않거나 미승인 상태 클럽입니다.")
                            except Exception as e:
                                st.error(f"오류: {e}")
                        else:
                            st.error("❌ 로그인할 수 있는 활성화된 동호회가 없습니다.")

        with col_notice:
            if club_list:
                st.info(f"💡 **{selected_club['club_name']} 신규 회원 등록**")
                with st.form("public_register_form", clear_on_submit=True):
                    reg_name = st.text_input("이름")
                    reg_grade = st.selectbox("본인 부수", list(range(1, 12)), index=7, format_func=lambda x: f"{x}부")
                    reg_phone = st.text_input("연락처 (숫자만)")

                    if st.form_submit_button("📝 회원 가입", use_container_width=True):
                        if reg_name and reg_phone:
                            try:
                                conn = get_db_connection()
                                cur = conn.cursor()
                                cur.execute(
                                    "INSERT INTO members (club_id, name, grade, phone, password, status) VALUES (%s, %s, %s, %s, %s, 'active')",
                                    (selected_club['id'], reg_name.strip(), reg_grade, reg_phone.strip(),
                                     reg_phone.strip())
                                )
                                conn.commit()
                                cur.close()
                                conn.close()
                                st.success(f"✅ 회원 가입 완료!")
                            except:
                                st.error("❌ 이미 등록된 연락처입니다.")
            else:
                st.info("현재 개설되어 승인 완료된 동호회가 존재하지 않아 일반회원 가입이 불가능합니다.")
    st.stop()

# ==========================================
# 🚪 로그인 이후 네비게이션 공통 바 (기존 유지)
# ==========================================
c_user, c_logout = st.columns([8, 1])
with c_user:
    st.markdown(f"👤 담당자: **{st.session_state.user_name}** | 권한 등급: **{st.session_state.user_role.upper()}**")
with c_logout:
    if st.button("🚪 로그아웃", use_container_width=True):
        delete_app_session()
        st.rerun()

# ==========================================
# 🛠️ 수퍼 관리자 전용 '동호회 개설 승인 전용 화면' (기존 유지)
# ==========================================
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
        st.success("✨ 현재 처리할 신규 동호회 승인 대기 건이 없습니다. 클린 상태입니다!")
    else:
        for _, row in df_pending.iterrows():
            c_info, c_ok, c_no = st.columns([6, 1.5, 1.5])
            with c_info:
                st.markdown(f"""
                📍 **{row['club_name']}** (ID: `{row['manager_id']}`)  
                • 연락처: {row['manager_phone']} | 주소: {row['address']} | 신청일시: {row['created_at']}
                """, unsafe_allow_html=True)

            with c_ok:
                if st.button("✅ 최종 승인 허가", key=f"ok_{row['id']}", use_container_width=True, type="primary"):
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("UPDATE clubs SET status = 'active' WHERE id = %s", (row['id'],))
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.toast(f"🎉 [{row['club_name']}] 승인이 완료되어 활성화되었습니다!")
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
                    st.toast(f"🚫 신청이 정상적으로 반려되었습니다.")
                    st.rerun()
            st.markdown("---")

# ==========================================
# 🛡️ 동호회 중간관리자 및 일반 회원 분기 처리 (기존 유지)
# ==========================================
elif st.session_state.user_role == "admin":
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