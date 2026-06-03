import streamlit as st
import psycopg2
import pandas as pd
import math


# ==========================================
# 0. 데이터베이스 연결 함수 (네온 연동 규격)
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
# 1. 라운드 로빈 리그전 경기 순서 생성 알고리즘
# ==========================================
def generate_round_robin_matches(player_names):
    names = list(player_names)
    if len(names) % 2 != 0:
        names.append("부전승")
    n = len(names)
    matches = []
    for round_idx in range(n - 1):
        for i in range(n // 2):
            p1 = names[i]
            p2 = names[n - 1 - i]
            if p1 != "부전승" and p2 != "부전승":
                matches.append((p1, p2))
        names = [names[0]] + [names[-1]] + names[1:-1]
    return matches


# 페이지 레이아웃 설정
st.set_page_config(layout="wide")

# 타이틀 안전하게 읽어오기
app_title = st.secrets["auth"].get("app_title", "🏓 탁구 대회 통합 관리 시스템")
st.title(app_title)

# ==========================================
# 🔐 로그인 및 권한 관리 세션 제어
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_role" not in st.session_state:  # "admin" 또는 "member"
    st.session_state.user_role = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None

# ----------------- 로그인 화면 -----------------
if not st.session_state.logged_in:
    st.subheader("🔑 시스템 접속을 위해 로그인해 주세요")

    col_login, col_notice = st.columns([1, 1])

    with col_login:
        login_type = st.radio("로그인 유형 선택", ["일반 회원 (전화번호 로그인)", "관리자 로그인"], horizontal=True)

        if login_type == "일반 회원 (전화번호 로그인)":
            phone_input = st.text_input("📱 전화번호 입력 (아이디/비밀번호 공통)", placeholder="예: 01012345678")
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
                        st.error("❌ 등록되지 않은 전화번호입니다. 먼저 회원 가입(등록)을 하거나 관리자에게 문의하세요.")
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

    with col_notice:
        st.info("""
        💡 **처음 오셨나요?**
        일반 회원은 하단의 회원 등록 폼을 통해 먼저 정보를 등록해야 로그인이 가능합니다.
        등록 시 사용한 **전화번호**가 로그인 ID이자 패스워드가 됩니다.
        """)

        st.markdown("---")
        st.caption("🆕 **신규 회원 가입 / 정보 등록**")
        with st.form("public_register_form", clear_on_submit=True):
            reg_name = st.text_input("이름")
            reg_grade = st.selectbox("본인 부수", list(range(1, 12)), index=7, format_func=lambda x: f"{x}부")
            reg_phone = st.text_input("연락처 (숫자만 입력)", placeholder="예: 01012345678")
            if st.form_submit_button("가입 및 즉시 회원 등록"):
                if reg_name and reg_phone:
                    try:
                        conn = get_db_connection()
                        cur = conn.cursor()
                        cur.execute("INSERT INTO members (name, grade, phone) VALUES (%s, %s, %s)",
                                    (reg_name, reg_grade, reg_phone.strip()))
                        conn.commit()
                        cur.close()
                        conn.close()
                        st.success(f"✅ '{reg_name}'님 회원 등록이 완료되었습니다! 이제 로그인할 수 있습니다.")
                    except:
                        st.error("❌ 등록 실패 (이미 가입된 연락처이거나 입력 오류)")
                else:
                    st.warning("이름과 연락처를 모두 입력해 주세요.")
    st.stop()

# ----------------- 로그아웃 버튼 탑재 (상단 바) -----------------
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

# 탭 구성
tab_member, tab_manage_tour, tab_play, tab_ranking = st.tabs([
    "👥 회원 DB 관리",
    "🏆 대회 생성 및 명단 선발",
    "🎮 대회 진행 및 결과 기록",
    "📊 연도별 통합 랭킹"
])

# ==========================================
# TAB 1: 회원 관리 화면 (삭제 후 즉시 리프레시 반영)
# ==========================================
with tab_member:
    st.header("1. 전체 회원 등록 및 관리")
    col_in, col_list = st.columns([1, 2])
    with col_in:
        st.subheader("새 회원 추가 등록")
        with st.form("member_form_tab", clear_on_submit=True):
            m_name = st.text_input("회원 이름")
            m_grade = st.selectbox("부수", list(range(1, 12)), index=7, format_func=lambda x: f"{x}부")
            m_phone = st.text_input("연락처 (로그인 ID가 됨)")
            if st.form_submit_button("회원 저장") and m_name:
                try:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("INSERT INTO members (name, grade, phone) VALUES (%s, %s, %s)",
                                (m_name, m_grade, m_phone.strip()))
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.success(f"회원 '{m_name}' 등록 완료")
                    st.rerun()
                except:
                    st.error("❌ 회원 저장 실패")

    with col_list:
        st.subheader("등록된 회원 명단")
        try:
            conn = get_db_connection()
            df_m = pd.read_sql("SELECT id, name, grade, phone FROM members ORDER BY id DESC", conn)
            conn.close()

            # 일반 회원일 때: 테이블 단순 조회만 노출
            if st.session_state.user_role != "admin":
                st.dataframe(df_m, use_container_width=True, hide_index=True)
                st.caption("💡 회원 삭제는 관리자 계정으로 로그인 시 가능합니다.")

            # 관리자 회원일 때: 행 선택 기능을 켠 인터랙티브 테이블 및 삭제 로직 가동
            else:
                st.markdown("🗑️ **삭제할 회원의 행을 선택한 후 하단의 삭제 버튼을 눌러주세요.**")

                selected_rows = st.dataframe(
                    df_m,
                    use_container_width=True,
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row",
                    key="member_delete_dataframe"
                )

                clicked_index = selected_rows.get("selection", {}).get("rows", [])

                if clicked_index:
                    selected_player = df_m.iloc[clicked_index[0]]
                    st.warning(f"⚠️ **주의: [{selected_player['name']}] 회원을 삭제하시겠습니까?**")

                    if st.button(f"❌ {selected_player['name']} 회원 영구 삭제", type="primary", use_container_width=True):
                        try:
                            # 1. 데이터베이스 삭제 처리 시작
                            conn = get_db_connection()
                            cur = conn.cursor()

                            # 출전 대기 명단 찌꺼기 제거
                            cur.execute("DELETE FROM tournament_players WHERE member_id = %s",
                                        (int(selected_player['id']),))
                            # 회원 정보 삭제 실행 (과거 매치 결과는 텍스트 기반이라 유지됨)
                            cur.execute("DELETE FROM members WHERE id = %s", (int(selected_player['id']),))

                            conn.commit()
                            cur.close()
                            conn.close()

                            # 2. 잔여 선택 세션 메모리 초기화로 즉각적인 리프레시 보장
                            if "member_delete_dataframe" in st.session_state:
                                del st.session_state["member_delete_dataframe"]

                            # 3. 화면을 완전히 새로고침하여 갱신 데이터 출력
                            st.success(f"🗑️ {selected_player['name']} 회원이 안전하게 삭제되었습니다.")
                            st.rerun()

                        except Exception as e:
                            st.error(f"❌ 회원 삭제 중 오류 발생: {e}")
                else:
                    st.info("💡 명단에서 회원을 클릭하면 삭제 버튼이 나타납니다.")
        except:
            st.info("회원 목록이 없습니다.")

# ==========================================
# TAB 2: 대회 생성 및 출전 선수 선발 (관리자 전용)
# ==========================================
with tab_manage_tour:
    st.header("2. 대회 관리 및 선수 선발")

    if st.session_state.user_role != "admin":
        st.warning("🔒 이 탭은 **관리자 전용** 공간입니다. 일반 회원은 대회를 생성하거나 선수를 선발할 수 없습니다.")
    else:
        col_t_create, col_t_p_select = st.columns([1, 1])
        with col_t_create:
            st.subheader("새로운 대회 개설")
            with st.form("tour_form", clear_on_submit=True):
                t_title = st.text_input("대회 명칭", placeholder="예: 2026년 오월 리그전")
                if st.form_submit_button("대회 생성") and t_title:
                    try:
                        conn = get_db_connection()
                        cur = conn.cursor()
                        cur.execute("INSERT INTO tournaments (title) VALUES (%s)", (t_title,))
                        conn.commit()
                        cur.close()
                        conn.close()
                        st.success(f"대회 [{t_title}]가 개설되었습니다.")
                        st.rerun()
                    except:
                        st.error("❌ 대회 생성 실패")
            try:
                conn = get_db_connection()
                df_t = pd.read_sql("SELECT id, title, created_at FROM tournaments ORDER BY id DESC", conn)
                conn.close()
                selected_rows = st.dataframe(df_t, use_container_width=True, hide_index=True, on_select="rerun",
                                             selection_mode="single-row")
                clicked_index = selected_rows.get("selection", {}).get("rows", [])
            except:
                df_t, clicked_index = pd.DataFrame(columns=["id", "title"]), []

        with col_t_p_select:
            st.subheader("대회별 출전 선수 선발")
            if df_t.empty:
                st.warning("대회를 먼저 생성해주세요.")
            else:
                tour_options = df_t.to_dict('records')
                selected_t = st.selectbox("대상 대회를 선택하세요", tour_options, index=clicked_index[0] if clicked_index else 0,
                                          format_func=lambda x: x['title'])
                try:
                    conn = get_db_connection()
                    df_all_m = pd.read_sql("SELECT id, name, grade FROM members ORDER BY name ASC", conn)
                    df_current_p = pd.read_sql(
                        f"SELECT tp.id, m.name, m.grade FROM tournament_players tp JOIN members m ON tp.member_id = m.id WHERE tp.tournament_id = {selected_t['id']} ORDER BY tp.id ASC",
                        conn)
                    conn.close()
                except:
                    df_all_m, df_current_p = pd.DataFrame(), pd.DataFrame()
                if not df_all_m.empty:
                    target_m = st.selectbox("출전시킬 회원 선택", df_all_m.to_dict('records'),
                                            format_func=lambda x: f"{x['name']} ({x['grade']}부)")
                    if st.button("🚀 대회 출전 명단에 추가"):
                        try:
                            conn = get_db_connection()
                            cur = conn.cursor()
                            cur.execute("INSERT INTO tournament_players (tournament_id, member_id) VALUES (%s, %s)",
                                        (selected_t['id'], target_m['id']))
                            conn.commit()
                            cur.close()
                            conn.close()
                            st.rerun()
                        except:
                            st.error("❌ 중복 등록이거나 저장 실패")
                st.write(f"📊 현재 출전 인원: {len(df_current_p)}명")
                st.dataframe(df_current_p, use_container_width=True, hide_index=True)

# ==========================================
# TAB 3: 대회 진행 및 결과 기록
# ==========================================
with tab_play:
    st.header("3. 실시간 경기 진행 및 결과 기록")
    try:
        conn = get_db_connection()
        df_active_t = pd.read_sql("SELECT id, title FROM tournaments ORDER BY id DESC", conn)
        conn.close()
    except:
        df_active_t = pd.DataFrame()

    if df_active_t.empty:
        st.warning("개설된 대회가 없습니다. 관리자가 대회를 먼저 생성해야 합니다.")
    else:
        active_tour = st.selectbox("진행할 대회를 선택하세요", df_active_t.to_dict('records'), format_func=lambda x: x['title'])
        try:
            conn = get_db_connection()
            df_players = pd.read_sql(
                f"SELECT m.name, m.grade FROM tournament_players tp JOIN members m ON tp.member_id = m.id WHERE tp.tournament_id = {active_tour['id']} ORDER BY m.id ASC",
                conn)
            df_saved_matches = pd.read_sql(
                f"SELECT group_idx, player1_name, player2_name, score_text FROM match_results WHERE tournament_id = {active_tour['id']}",
                conn)
            conn.close()
        except:
            df_players, df_saved_matches = pd.DataFrame(), pd.DataFrame()

        if len(df_players) < 2:
            st.info("출전 선수가 부족합니다. (최소 2명 필요)")
        else:
            if "db_scores" not in st.session_state: st.session_state.db_scores = {}
            for _, row in df_saved_matches.iterrows():
                st.session_state.db_scores[(row['group_idx'], row['player1_name'], row['player2_name'])] = row[
                    'score_text']

            col_method, col_group_num = st.columns([2, 1])
            with col_method:
                game_method = st.radio("경기 방식 선택", ["라운드로빈(풀리그)", "토너먼트", "혼합 방식 (리그 후 토너먼트)"],
                                       index=2 if len(df_players) >= 4 else 0, horizontal=True)
            with col_group_num:
                if game_method in ["라운드로빈(풀리그)", "혼합 방식 (리그 후 토너먼트)"]:
                    max_groups = max(1, len(df_players) // 2)
                    num_groups = st.number_input("📋 생성할 조(Group) 갯수", min_value=1, max_value=max_groups,
                                                 value=2 if len(df_players) >= 4 else 1, step=1)
                else:
                    num_groups = 1

            final_rule = "선택지 1"
            if game_method == "혼합 방식 (리그 후 토너먼트)":
                final_rule = st.radio("본선 대진표 구성 방식", ["선택지 1 (전체 크로스 - 전원 본선행)", "선택지 2 (상위권 본선 - 조 1,2위만 본선행)"],
                                      horizontal=True)
            st.markdown("---")

            player_list = df_players.to_dict('records')
            final_pool = []

            if game_method in ["라운드로빈(풀리그)", "혼합 방식 (리그 후 토너먼트)"]:
                groups = [[] for _ in range(num_groups)]
                for idx, p in enumerate(player_list): groups[idx % num_groups].append(p)


                def render_flat_score_board(group_idx, group_players):
                    st.subheader(f"🏆 {group_idx + 1}조 예선 리그 결과 입력")
                    names_with_grade = {p['name']: p['grade'] for p in group_players}
                    round_matches = generate_round_robin_matches(list(names_with_grade.keys()))

                    for idx, (p1, p2) in enumerate(round_matches):
                        db_p1, db_p2 = (p1, p2) if p1 < p2 else (p2, p1)
                        score_key = (group_idx, db_p1, db_p2)
                        saved_score = st.session_state.db_scores.get(score_key, "")
                        v1, v2 = 0, 0
                        if ":" in saved_score:
                            s1, s2 = saved_score.split(":")
                            v1, v2 = (int(s1), int(s2)) if db_p1 == p1 else (int(s2), int(s1))

                        c_num, c_p1, c_s1, c_vs, c_s2, c_p2, c_btn = st.columns([0.8, 2.5, 1, 0.4, 1, 2.5, 1.2])
                        with c_num:
                            st.markdown(f"<div style='margin-top:12px; color:gray;'>{idx + 1}경기</div>",
                                        unsafe_allow_html=True)
                        with c_p1:
                            st.markdown(
                                f"<div style='background-color:#F3F4F6; padding:6px; border-radius:4px; text-align:center;'><b>{p1}</b></div>",
                                unsafe_allow_html=True)
                        with c_s1:
                            sc1 = st.number_input("🔹", min_value=0, max_value=5, value=v1, step=1,
                                                  key=f"s1_{group_idx}_{idx}", label_visibility="collapsed")
                        with c_vs:
                            st.markdown("<div style='text-align:center; padding-top:4px;'>:</div>",
                                        unsafe_allow_html=True)
                        with c_s2:
                            sc2 = st.number_input("🔸", min_value=0, max_value=5, value=v2, step=1,
                                                  key=f"s2_{group_idx}_{idx}", label_visibility="collapsed")
                        with c_p2:
                            st.markdown(
                                f"<div style='background-color:#F3F4F6; padding:6px; border-radius:4px; text-align:center;'><b>{p2}</b></div>",
                                unsafe_allow_html=True)
                        with c_btn:
                            if st.button("💾 저장", key=f"b_{group_idx}_{idx}", use_container_width=True):
                                final_score = f"{sc1}:{sc2}" if p1 == db_p1 else f"{sc2}:{sc1}"
                                st.session_state.db_scores[score_key] = final_score
                                conn = get_db_connection()
                                cur = conn.cursor()
                                cur.execute(
                                    "INSERT INTO match_results (tournament_id, group_idx, match_order, player1_name, player2_name, score_text) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (tournament_id, group_idx, player1_name, player2_name) DO UPDATE SET score_text = EXCLUDED.score_text",
                                    (active_tour['id'], group_idx, idx + 1, db_p1, db_p2, final_score))
                                conn.commit()
                                cur.close()
                                conn.close()
                                st.rerun()

                    rank_data = []
                    for p in group_players:
                        wins = 0
                        for opp in group_players:
                            if p['name'] == opp['name']: continue
                            r1, r2 = (p['name'], opp['name']) if p['name'] < opp['name'] else (opp['name'], p['name'])
                            score = st.session_state.db_scores.get((group_idx, r1, r2), "")
                            if ":" in score:
                                s1, s2 = map(int, score.split(":"))
                                if (p['name'] == r1 and s1 > s2) or (p['name'] == r2 and s2 > s1): wins += 1
                        rank_data.append({"이름": p['name'], "승": wins})
                    df_rank = pd.DataFrame(rank_data).sort_values(by="승", ascending=False)
                    return df_rank["이름"].tolist()


                for g_idx, g_players in enumerate(groups):
                    if g_players:
                        sorted_names = render_flat_score_board(g_idx, g_players)
                        if game_method == "혼합 방식 (리그 후 토너먼트)":
                            if "선택지 1" in final_rule:
                                final_pool.extend(sorted_names)
                            else:
                                final_pool.extend(sorted_names[:2])
                        st.markdown("---")
            else:
                final_pool = [p['name'] for p in player_list]

            # 토너먼트 진행
            if (game_method == "토너먼트" or game_method == "혼합 방식 (리그 후 토너먼트)") and len(final_pool) >= 2:
                st.header("🏆 본선 무한 토너먼트 라운드")
                next_power = 2 ** math.ceil(math.log2(len(final_pool)))
                full_bracket = list(final_pool)
                while len(full_bracket) < next_power: full_bracket.append("부전승")

                round_matches = []
                half = len(full_bracket) // 2
                if game_method == "혼합 방식 (리그 후 토너먼트)" and "선택지 1" in final_rule:
                    for i in range(half):
                        p1 = full_bracket[i]
                        p2 = full_bracket[len(full_bracket) - 1 - i]
                        if p1 != "부전승" or p2 != "부전승": round_matches.append((p1, p2))
                else:
                    for i in range(0, len(full_bracket), 2):
                        if full_bracket[i] != "부전승" or full_bracket[i + 1] != "부전승":
                            round_matches.append((full_bracket[i], full_bracket[i + 1]))

                current_round_players = list(final_pool)
                round_level = 1

                while len(current_round_players) > 1:
                    p_count = 2 ** math.ceil(math.log2(len(current_round_players)))
                    round_title = f"{p_count}강전" if p_count > 4 else ("준결승전(4강)" if p_count == 4 else "최종 결승전")
                    st.subheader(f"🟩 {round_title}")

                    next_round_players = []
                    match_pairs = []
                    temp_bracket = list(current_round_players)
                    if round_level == 1:
                        match_pairs = round_matches
                    else:
                        if len(temp_bracket) % 2 != 0: temp_bracket.append("부전승")
                        for i in range(0, len(temp_bracket), 2): match_pairs.append(
                            (temp_bracket[i], temp_bracket[i + 1]))

                    for idx, (p1, p2) in enumerate(match_pairs):
                        if p1 == "부전승" and p2 == "부전승": continue
                        if p1 == "부전승": next_round_players.append(p2); continue
                        if p2 == "부전승": next_round_players.append(p1); continue

                        db_p1, db_p2 = (p1, p2) if p1 < p2 else (p2, p1)
                        g_code = 900 + round_level
                        score_key = (g_code, db_p1, db_p2)
                        saved_score = st.session_state.db_scores.get(score_key, "")

                        v1, v2 = 0, 0
                        if ":" in saved_score:
                            s1, s2 = saved_score.split(":")
                            v1, v2 = (int(s1), int(s2)) if db_p1 == p1 else (int(s2), int(s1))
                            next_round_players.append(p1 if v1 > v2 else p2)

                        c_m, c_p1, c_s1, c_vs, c_s2, c_p2, c_save = st.columns([0.8, 2.5, 1, 0.4, 1, 2.5, 1.2])
                        with c_m:
                            st.markdown(f"<div style='margin-top:10px; color:#1E3A8A;'>매치 {idx + 1}</div>",
                                        unsafe_allow_html=True)
                        with c_p1:
                            st.markdown(
                                f"<div style='background-color:#ECFDF5; padding:6px; text-align:center;'><b>{p1}</b></div>",
                                unsafe_allow_html=True)
                        with c_s1:
                            sc1 = st.number_input("🔹", min_value=0, max_value=5, value=v1, step=1,
                                                  key=f"t1_{round_level}_{idx}", label_visibility="collapsed")
                        with c_vs:
                            st.markdown("<div style='text-align:center; padding-top:4px;'>:</div>",
                                        unsafe_allow_html=True)
                        with c_s2:
                            sc2 = st.number_input("🔸", min_value=0, max_value=5, value=v2, step=1,
                                                  key=f"t2_{round_level}_{idx}", label_visibility="collapsed")
                        with c_p2:
                            st.markdown(
                                f"<div style='background-color:#FFFBEB; padding:6px; text-align:center;'><b>{p2}</b></div>",
                                unsafe_allow_html=True)
                        with c_save:
                            if st.button("💾 기록", key=f"tsave_{round_level}_{idx}", use_container_width=True):
                                final_score = f"{sc1}:{sc2}" if p1 == db_p1 else f"{sc2}:{sc1}"
                                st.session_state.db_scores[score_key] = final_score
                                conn = get_db_connection()
                                cur = conn.cursor()
                                cur.execute(
                                    "INSERT INTO match_results (tournament_id, group_idx, match_order, player1_name, player2_name, score_text) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (tournament_id, group_idx, player1_name, player2_name) DO UPDATE SET score_text = EXCLUDED.score_text",
                                    (active_tour['id'], g_code, idx + 1, db_p1, db_p2, final_score))
                                conn.commit()
                                cur.close()
                                conn.close()
                                st.rerun()

                    total_expected_matches = len([m for m in match_pairs if m[0] != "부전승" and m[1] != "부전승"])
                    recorded_matches_count = sum(1 for m in match_pairs if (g_code, (m[0] if m[0] < m[1] else m[1]), (
                        m[1] if m[0] < m[1] else m[0])) in st.session_state.db_scores)

                    if recorded_matches_count < total_expected_matches:
                        st.warning(f"💡 모든 경기가 기록되어야 다음 라운드가 노출됩니다. ({recorded_matches_count}/{total_expected_matches})")
                        break
                    current_round_players = next_round_players
                    round_level += 1
                    st.markdown("---")

                if len(current_round_players) == 1:
                    st.balloons()
                    st.success(f"👑 최종 우승자: **[{current_round_players[0]}]**")

# ==========================================
# TAB 4: 연도별 통합 랭킹
# ==========================================
with tab_ranking:
    st.header("📊 연도별 동호회 통합 등수 / 랭킹 산정판")
    col_y, col_g = st.columns([1, 1])
    with col_y:
        ranking_year = st.selectbox("📅 조회 연도 선택", ["2026", "2025", "2024"])
    with col_g:
        grade_filter = st.selectbox("🏓 대상 부수 범위 필터", ["전체 부수 보기", "상위권 (1~5부)", "하위권 (6부 이하)"])

    try:
        conn = get_db_connection()
        df_year_tours = pd.read_sql(
            f"SELECT id, title FROM tournaments WHERE EXTRACT(YEAR FROM created_at) = {ranking_year}", conn)

        if df_year_tours.empty:
            st.info(f"📅 {ranking_year}년도에는 아직 대회 데이터가 없습니다.")
            conn.close()
        else:
            tour_ids = tuple(df_year_tours['id'].tolist())
            tour_ids_str = f"({tour_ids[0]})" if len(tour_ids) == 1 else str(tour_ids)
            df_all_res = pd.read_sql(
                f"SELECT tournament_id, group_idx, player1_name, player2_name, score_text FROM match_results WHERE tournament_id IN {tour_ids_str}",
                conn)
            df_mem_info = pd.read_sql("SELECT name, grade FROM members", conn)
            conn.close()

            mem_grade_map = dict(zip(df_mem_info['name'], df_mem_info['grade']))
            player_points = {}

            for t_id in df_year_tours['id'].tolist():
                df_t_res = df_all_res[df_all_res['tournament_id'] == t_id]
                if df_t_res.empty: continue
                t_codes = df_t_res[df_t_res['group_idx'] >= 901]['group_idx'].unique()

                if len(t_codes) > 0:
                    max_round = max(t_codes)
                    for _, row in df_t_res.iterrows():
                        g_idx = row['group_idx']
                        p1, p2 = row['player1_name'], row['player2_name']
                        if ":" in row['score_text']:
                            s1, s2 = map(int, row['score_text'].split(":"))
                            winner = p1 if s1 > s2 else p2
                            loser = p2 if s1 > s2 else p1

                            if winner not in player_points: player_points[winner] = 0
                            if loser not in player_points: player_points[loser] = 0

                            if g_idx == max_round:
                                player_points[winner] += 10
                                player_points[loser] += 7
                            elif g_idx == max_round - 1:
                                player_points[loser] += 5
                            elif g_idx == max_round - 2:
                                player_points[loser] += 3
                            elif g_idx >= 901:
                                player_points[loser] += 1
                else:
                    for _, row in df_t_res.iterrows():
                        if ":" in row['score_text']:
                            s1, s2 = map(int, row['score_text'].split(":"))
                            winner = row['player1_name'] if s1 > s2 else row['player2_name']
                            player_points[winner] = player_points.get(winner, 0) + 1

            rank_list = []
            for name, pts in player_points.items():
                p_grade = mem_grade_map.get(name, 99)
                if grade_filter == "상위권 (1~5부)" and p_grade > 5: continue
                if grade_filter == "하위권 (6부 이하)" and p_grade < 6: continue
                rank_list.append({"선수명": name, "부수": f"{p_grade}부" if p_grade != 99 else "미지정", "📊 누적 랭킹 포인트": pts})

            df_final_rank = pd.DataFrame(rank_list)
            if df_final_rank.empty:
                st.warning("조건에 일치하는 랭킹 데이터가 없습니다.")
            else:
                df_final_rank = df_final_rank.sort_values(by="📊 누적 랭킹 포인트", ascending=False).reset_index(drop=True)
                df_final_rank.insert(0, "🥇 최종 순위",
                                     df_final_rank["📊 누적 랭킹 포인트"].rank(ascending=False, method="min").astype(int))
                st.dataframe(df_final_rank, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"랭킹 산정 오류: {e}")