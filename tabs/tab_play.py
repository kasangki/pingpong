import streamlit as st
import pandas as pd
import math
# 🚀 자동 새로고침 모듈
from streamlit_autorefresh import st_autorefresh


# 야간 모드(다크 테마) 전용 초고가시성 럭셔리 스타일 정의
def get_style():
    return """
    <style>
    html, body, [data-testid="stMarkdownContainer"] p { font-size: 17px !important; line-height: 1.6; }

    /* 입력창 및 레이아웃 확대 */
    .match-row-num { margin-top: 10px; color: #94A3B8; font-weight: bold; font-size: 17px; }
    .player-box-p1 { background-color: #1E1B4B; padding: 10px; text-align: center; border-radius: 8px; font-size: 20px !important; font-weight: 800; color: #C7D2FE; border: 1px solid #4338CA; }
    .player-box-p2 { background-color: #064E3B; padding: 10px; text-align: center; border-radius: 8px; font-size: 20px !important; font-weight: 800; color: #A7F3D0; border: 1px solid #059669; }
    .vs-divider { text-align: center; padding-top: 8px; font-weight: 900; font-size: 22px; color: #64748B; }

    /* 등수 변경 및 순위표 타이포그래피 */
    .rank-title { font-size: 22px !important; font-weight: bold; margin-bottom: 12px; color: #F8FAFC; }
    .text-main-bold { font-size: 18px !important; font-weight: 700; color: #F1F5F9; }

    /* 5위 이하 최종 종합 순위표 럭셔리 대시보드 스타일 */
    .luxury-table-container { width: 100%; margin: 25px 0; background: #1E293B; border-radius: 14px; box-shadow: 0 4px 20px rgba(0,0,0,0.3); border: 1px solid #334155; overflow: hidden; }
    .luxury-table { width: 100%; border-collapse: collapse; text-align: center; font-family: 'Pretendard', sans-serif; }
    .luxury-table thead { background: linear-gradient(135deg, #4F46E5 0%, #3730A3 100%); border-bottom: 2px solid #334155; }
    .luxury-table th { padding: 18px; color: #ffffff; font-weight: 700; font-size: 18px; letter-spacing: 0.05em; }
    .luxury-table td { padding: 18px; border-bottom: 1px solid #334155; color: #F1F5F9; font-size: 17px; }
    .luxury-table tbody tr:hover { background-color: #334155; transition: 0.2s; }

    .rank-badge-item { background: linear-gradient(135deg, #EF4444 0%, #DC2626 100%); color: white; padding: 6px 16px; border-radius: 20px; font-weight: 800; font-size: 15px; box-shadow: 0 2px 4px rgba(239, 68, 68, 0.4); }
    .name-cell-item { font-weight: 800; font-size: 19px; color: #FFFFFF; }
    .wins-cell-item { color: #818CF8; font-weight: 900; font-size: 19px; }
    .text-plus-item { color: #60A5FA; font-weight: 700; font-size: 17px; }
    .text-minus-item { color: #F87171; font-weight: 700; font-size: 17px; }
    .text-gray-item { color: #94A3B8; font-weight: 500; font-size: 17px; }

    .stNumberInput input { font-size: 20px !important; font-weight: 900 !important; text-align: center !important; color: #FFFFFF !important; }
    .stTabs button p { font-size: 18px !important; font-weight: bold !important; }
    </style>
    """


def generate_round_robin_matches(player_list):
    players = list(player_list)
    if len(players) % 2 != 0:
        players.append({"id": -1, "name": "부전승", "grade": 0})
    n = len(players)
    matches = []
    for round_idx in range(n - 1):
        for i in range(n // 2):
            p1 = players[i]
            p2 = players[n - 1 - i]
            if p1["id"] != -1 and p2["id"] != -1:
                matches.append((p1, p2))
        players = [players[0]] + [players[-1]] + players[1:-1]
    return matches


def run_tab_play(get_db_connection):
    st.markdown(get_style(), unsafe_allow_html=True)
    st.header("3. 실시간 경기 진행 및 결과 기록")

    club_id = st.session_state.club_id

    try:
        conn = get_db_connection()
        query_t = "SELECT id, title, status FROM tournaments WHERE club_id = %s AND deleted_at IS NULL ORDER BY id DESC"
        df_active_t = pd.read_sql(query_t, conn, params=(club_id,))
        conn.close()
    except:
        df_active_t = pd.DataFrame()

    if df_active_t.empty:
        st.warning("개설된 대회가 없습니다. 관리자가 대회를 먼저 생성해야 합니다.")
        return

    tour_dict_list = df_active_t.to_dict('records')
    active_tour = st.selectbox("진행할 대회를 선택하세요", tour_dict_list, format_func=lambda
        x: f"{x['title']} [{'🏆 완료됨' if x['status'] == 'finished' else '🎮 진행중'}]")
    current_tour_status = active_tour['status']

    # 💡 [마감 락 플래그] 대회가 종료되면 실시간 자동새로고침을 멈춥니다.
    is_tournament_finished = (current_tour_status == 'finished')
    if not is_tournament_finished:
        st_autorefresh(interval=60000, key="play_tab_refresh")

    try:
        conn = get_db_connection()
        df_players = pd.read_sql(
            f"SELECT m.id, m.name, m.grade FROM tournament_players tp JOIN members m ON tp.member_id = m.id WHERE tp.tournament_id = {active_tour['id']} AND m.club_id = {club_id} ORDER BY m.id ASC",
            conn)

        query_matches = """
            SELECT mr.group_idx, mr.player1_id, mr.player2_id, mr.player1_score, mr.player2_score 
            FROM match_results mr
            JOIN tournaments t ON mr.tournament_id = t.id
            WHERE mr.tournament_id = %s AND t.club_id = %s
        """
        df_saved_matches = pd.read_sql(query_matches, conn, params=(active_tour['id'], club_id))
        conn.close()
    except:
        df_players, df_saved_matches = pd.DataFrame(), pd.DataFrame()

    if len(df_players) < 2:
        st.info("출전 선수가 부족합니다. (최소 2명 필요)")
        return

    db_scores = {}
    for _, row in df_saved_matches.iterrows():
        g_idx = int(row['group_idx'])
        p1_id = int(row['player1_id'])
        p2_id = int(row['player2_id'])
        p1_sc = int(row['player1_score'])
        p2_sc = int(row['player2_score'])

        if p1_id < p2_id:
            db_scores[(g_idx, p1_id, p2_id)] = (p1_sc, p2_sc)
        else:
            db_scores[(g_idx, p2_id, p1_id)] = (p2_sc, p1_sc)

    is_game_started = len(db_scores) > 0
    is_score_locked = True if is_tournament_finished else False
    is_ui_disabled = is_game_started or is_tournament_finished

    if is_tournament_finished:
        st.success("🏆 이 대회는 최종 종료(마감)되었습니다. 자동 새로고침이 중지되었으며 성적 변경이 불가능합니다.")
    else:
        st.info("📢 전광판 모드 활성화: 60초 주기로 다른 태블릿의 경기 점수가 화면에 실시간 자동 동기화됩니다.")

    # 1. 최상단 즉시 새로고침
    c_status, c_refresh = st.columns([5.5, 1.5])
    with c_status:
        st.caption("💡 다른 태블릿이 입력한 점수를 즉시 땡겨오려면 우측 버튼을 누르세요.")
    with c_refresh:
        if st.button("🔄 즉시 화면 새로고침", use_container_width=True, type="secondary", key="top_refresh_btn"):
            st.rerun()

    col_method, col_group_num = st.columns([2, 1])
    with col_method:
        game_method = st.radio(
            "경기 방식 선택",
            ["라운드로빈(풀리그)", "토너먼트", "혼합 방식 (리그 후 토너먼트)"],
            index=2,
            horizontal=True,
            disabled=is_ui_disabled
        )
    with col_group_num:
        if game_method in ["라운드로빈(풀리그)", "혼합 방식 (리그 후 토너먼트)"]:
            # 이론상 선수가 완전히 불려왔을 때의 기본 상한선 계산
            max_groups = max(1, len(df_players) // 2)

            # 💡 [SaaS 무결점 패치]: DB에 이미 저장된 실제 경기 조 번호를 역추적합니다.
            if is_game_started:
                recorded_group_indices = [k[0] for k in db_scores.keys() if k[0] < 900]
                if recorded_group_indices:
                    default_g_value = max(recorded_group_indices) + 1
                else:
                    default_g_value = 2 if max_groups >= 2 else 1
            else:
                default_g_value = 2 if max_groups >= 2 else 1

            # 💡 [버그 격파 핵심]: 위젯이 로딩 편차로 인해 스스로 값을 깎아내리지 못하도록
            # max_value 상한선을 선수 기준, DB 기록 기준, 마진(30) 중 가장 큰 값으로 개방합니다.
            absolute_max_limit = max(max_groups, default_g_value, 30)

            num_groups = st.number_input(
                "📋 생성할 조(Group) 갯수",
                min_value=1,
                max_value=int(absolute_max_limit),  # 👈 상한선을 넉넉하게 열어 위젯의 리셋을 완벽 방어!
                value=int(default_g_value),
                step=1,
                disabled=is_ui_disabled
            )
        else:
            num_groups = 1

    final_rule = "선택지 1"
    if game_method == "혼합 방식 (리그 후 토너먼트)":
        final_rule = st.radio(
            "본선 대진표 구성 방식",
            ["선택지 1 (전체 크로스 - 전원 본선행)", "선택지 2 (상위권 본선 - 조 1,2위만 본선행)"],
            horizontal=True,
            disabled=is_ui_disabled
        )
    st.markdown("---")

    player_list = df_players.to_dict('records')
    final_pool = []

    all_league_stats = {}
    for p in player_list:
        all_league_stats[p['id']] = {
            "id": p['id'], "name": p['name'], "grade": p['grade'],
            "승": 0, "득실차": 0, "진출단계점수": 0, "탈락라운드텍스트": "예선 탈락"
        }

    # ==========================================
    # 🪵 1. 예선 리그전(라운드로빈) 파트
    # ==========================================
    if game_method in ["라운드로빈(풀리그)", "혼합 방식 (리그 후 토너먼트)"]:
        groups = [[] for _ in range(num_groups)]
        for idx, p in enumerate(player_list):
            groups[idx % num_groups].append(p)

        def render_flat_score_board(group_idx, group_players):
            st.subheader(f"🏆 {group_idx + 1}조 예선 리그 결과 입력")
            round_matches = generate_round_robin_matches(group_players)

            for idx, (p1, p2) in enumerate(round_matches):
                db_p1_id, db_p2_id = (p1['id'], p2['id']) if p1['id'] < p2['id'] else (p2['id'], p1['id'])
                score_key = (group_idx, db_p1_id, db_p2_id)

                saved_tuple = db_scores.get(score_key, (0, 0))
                s1_saved, s2_saved = saved_tuple

                if p1['id'] == db_p1_id:
                    v1, v2 = s1_saved, s2_saved
                else:
                    v1, v2 = s2_saved, s1_saved

                is_match_recorded = (v1 == 3 or v2 == 3)

                key_s1 = f"s1_val_{active_tour['id']}_{group_idx}_{idx}"
                key_s2 = f"s2_val_{active_tour['id']}_{group_idx}_{idx}"

                if is_match_recorded or (s1_saved != 0 or s2_saved != 0):
                    st.session_state[key_s1] = v1
                    st.session_state[key_s2] = v2
                else:
                    if key_s1 not in st.session_state:
                        st.session_state[key_s1] = v1
                    if key_s2 not in st.session_state:
                        st.session_state[key_s2] = v2

                with st.container():
                    c_num, c_p1, c_s1, c_vs, c_s2, c_p2, c_btn = st.columns([0.8, 2.3, 0.9, 0.3, 0.9, 2.3, 1.5])
                    with c_num:
                        st.markdown(f"<div class='match-row-num'>{idx + 1}경기</div>", unsafe_allow_html=True)
                    with c_p1:
                        st.markdown(f"<div class='player-box-p1'>{p1['name']}</div>", unsafe_allow_html=True)
                    with c_s1:
                        sc1 = st.number_input("🔹", min_value=0, max_value=3, key=key_s1,
                                              label_visibility="collapsed", disabled=is_score_locked)
                    with c_vs:
                        st.markdown("<div class='vs-divider'>:</div>", unsafe_allow_html=True)
                    with c_s2:
                        sc2 = st.number_input("🔸", min_value=0, max_value=3, key=key_s2,
                                              label_visibility="collapsed", disabled=is_score_locked)
                    with c_p2:
                        st.markdown(f"<div class='player-box-p2'>{p2['name']}</div>", unsafe_allow_html=True)

                    with c_btn:
                        btn_label = "🟢 저장완료" if is_match_recorded else "💾 결과저장"
                        btn_type = "secondary" if is_match_recorded else "primary"

                        if st.button(btn_label, key=f"b_{group_idx}_{idx}", use_container_width=True, type=btn_type,
                                     disabled=is_score_locked):
                            if sc1 == 3 and sc2 == 3:
                                st.error("⚠️ 3:3 동점은 입력할 수 없습니다.")
                            elif sc1 != 3 and sc2 != 3:
                                st.error("⚠️ 세트 종료 기준 미달 (3점 선취 필요)")
                            else:
                                f_p1_sc = sc1 if p1['id'] == db_p1_id else sc2
                                f_p2_sc = sc2 if p1['id'] == db_p1_id else sc1

                                conn = get_db_connection()
                                cur = conn.cursor()
                                cur.execute("""
                                    INSERT INTO match_results (tournament_id, group_idx, match_order, player1_id, player2_id, player1_score, player2_score) 
                                    VALUES (%s,%s,%s,%s,%s,%s,%s) 
                                    ON CONFLICT (tournament_id, group_idx, player1_id, player2_id) 
                                    DO UPDATE SET player1_score = EXCLUDED.player1_score, player2_score = EXCLUDED.player2_score
                                """, (active_tour['id'], group_idx, idx + 1, db_p1_id, db_p2_id, f_p1_sc, f_p2_sc))
                                conn.commit()
                                cur.close()
                                conn.close()
                                st.success(f"✅ 경기 결과가 안전하게 반영되었습니다!")
                                st.rerun()

            # 📊 1단계: 기본 성적 집계 (승, 세트득실차)
            rank_stats = []
            for p in group_players:
                wins, set_gain, set_loss = 0, 0, 0
                for opp in group_players:
                    if p['id'] == opp['id']: continue
                    r1_id, r2_id = (p['id'], opp['id']) if p['id'] < opp['id'] else (opp['id'], p['id'])

                    saved_tuple = db_scores.get((group_idx, r1_id, r2_id), (0, 0))
                    s1, s2 = saved_tuple

                    if s1 != 0 or s2 != 0:
                        p_score = s1 if p['id'] == r1_id else s2
                        opp_score = s2 if p['id'] == r1_id else s1
                        set_gain += p_score
                        set_loss += opp_score
                        if p_score > opp_score: wins += 1

                rank_stats.append({
                    "player_obj": p, "id": p['id'], "name": p['name'], "grade": p['grade'],
                    "승": wins, "득실차": (set_gain - set_loss), "승자승점수": 0.0
                })

            # 📊 2단계: 승수와 득실차가 모두 같을 때 작동하는 정밀 3순위 '승자승(H2H)' 알고리즘
            for i in range(len(rank_stats)):
                h2h_bonus = 0
                for j in range(len(rank_stats)):
                    if i == j: continue
                    if rank_stats[i]["승"] == rank_stats[j]["승"] and rank_stats[i]["득실차"] == rank_stats[j]["득실차"]:
                        p1_id, p2_id = rank_stats[i]["id"], rank_stats[j]["id"]
                        r1_id, r2_id = (p1_id, p2_id) if p1_id < p2_id else (p2_id, p1_id)

                        s1, s2 = db_scores.get((group_idx, r1_id, r2_id), (0, 0))
                        if s1 != 0 or s2 != 0:
                            if (p1_id == r1_id and s1 > s2) or (p1_id == r2_id and s2 > s1):
                                h2h_bonus += 0.1
                rank_stats[i]["승자승점수"] = h2h_bonus

            # 🚀 자동 정렬 축 고정
            rank_stats_sorted = sorted(rank_stats, key=lambda x: (x["승"], x["득실차"], x["승자승점수"]), reverse=True)

            # 공동 순위(동률) 처리 맵 빌드
            computed_ranks = {}
            current_rank = 1
            for idx, stat in enumerate(rank_stats_sorted):
                if idx > 0:
                    prev = rank_stats_sorted[idx - 1]
                    if stat["승"] == prev["승"] and stat["득실차"] == prev["득실차"] and stat["승자승점수"] == prev["승자승점수"]:
                        pass
                    else:
                        current_rank = idx + 1
                computed_ranks[stat["id"]] = current_rank

            manual_key = f"m_rank_map_{active_tour['id']}_{group_idx}"
            if manual_key not in st.session_state:
                st.session_state[manual_key] = {}
            m_ranks = st.session_state[manual_key]

            render_list = []
            for stat in rank_stats_sorted:
                p_id = stat["id"]
                final_rank = m_ranks.get(p_id, computed_ranks[p_id])
                render_list.append({
                    "player_obj": stat["player_obj"], "id": p_id, "name": stat["name"], "grade": stat["grade"],
                    "승": stat["승"], "득실차": stat["득실차"], "rank": int(final_rank)
                })

            render_list = sorted(render_list, key=lambda x: x["rank"])

            # 🌟 2. 각 조 리그 순위표 헤더 옆에 새로고침 배치
            c_title, c_ref = st.columns([5.5, 1.5])
            with c_title:
                st.markdown(f"<p class='rank-title'>📊 {group_idx + 1}조 리그전 실시간 순위 등수표</p>", unsafe_allow_html=True)
            with c_ref:
                if st.button("🔄 현재 조 갱신", use_container_width=True, type="secondary", key=f"ref_group_{group_idx}"):
                    st.rerun()

            c_h1, c_h2, c_h3, c_h4 = st.columns([1.5, 3.0, 1.5, 1.5])
            c_h1.markdown("**등수**")
            c_h2.markdown("**선수 정보**")
            c_h3.markdown("**승률(승)**")
            c_h4.markdown("**세트득실**")

            for item in render_list:
                rank_num = item["rank"]
                c_b1, c_b2, c_b3, c_b4 = st.columns([1.5, 3.0, 1.5, 1.5])

                medal = f"🥇 {rank_num}위" if rank_num == 1 else f"🥈 {rank_num}위" if rank_num == 2 else f"🥉 {rank_num}위" if rank_num == 3 else f"🏅 {rank_num}위"
                c_b1.markdown(f"**{medal}**")
                c_b2.markdown(f"<span class='text-main-bold'>{item['name']}</span> ({item['grade']}부)",
                              unsafe_allow_html=True)
                c_b3.markdown(f"**{item['승']}승**")

                diff_val = item['득실차']
                diff_text = f"+{diff_val}" if diff_val > 0 else f"{diff_val}"
                c_b4.markdown(f"**{diff_text}**")

                if item['id'] in all_league_stats:
                    all_league_stats[item['id']]["승"] = item['승']
                    all_league_stats[item['id']]["득실차"] = item['득실차']

            # 💡 [핵심 패치] 대회가 종료(마감) 상태이면 수동 미세 조정 패널 자체를 잠금(Disabled) 처리합니다.
            with st.expander(f"🛠️ {group_idx + 1}조 순위 강제 미세 조정 및 동률 파괴 제어판"):
                if is_score_locked:
                    st.caption("🔒 대회가 마감되어 순위 강제 조정 기능이 잠겼습니다.")
                for item in render_list:
                    p_id = item["id"]
                    current_saved = m_ranks.get(p_id, computed_ranks[p_id])
                    new_val = st.number_input(
                        f"🔺 {item['name']} 강제 등수 설정",
                        min_value=1, max_value=len(group_players), value=int(current_saved), step=1,
                        key=f"adjust_{group_idx}_{p_id}",
                        disabled=is_score_locked  # 락 반영
                    )
                    if not is_score_locked and new_val != current_saved:
                        m_ranks[p_id] = new_val
                        st.rerun()

                if not is_score_locked:
                    if st.button("🔄 이 조의 순위 미세조정 내역 초기화", key=f"reset_btn_{group_idx}", use_container_width=True):
                        st.session_state[manual_key] = {}
                        st.rerun()

            total_matches_count = len(round_matches)
            recorded_matches_count = sum(1 for (p1, p2) in round_matches if (
                group_idx, p1['id'] if p1['id'] < p2['id'] else p2['id'],
                p2['id'] if p1['id'] < p2['id'] else p1['id']) in db_scores)

            if total_matches_count == recorded_matches_count:
                st.markdown(f"##### 🏁 [{group_idx + 1}조 리그전 확정 최종 등수]")
                result_strings = [f"**{item['rank']}위**: {item['name']}" for item in render_list]
                st.info(" ➡️ ".join(result_strings))

            return [item["player_obj"] for item in render_list]

        for g_idx, g_players in enumerate(groups):
            if g_players:
                sorted_objects = render_flat_score_board(g_idx, g_players)
                if game_method == "혼합 방식 (리그 후 토너먼트)":
                    if "선택지 1" in final_rule:
                        final_pool.extend(sorted_objects)
                    else:
                        final_pool.extend(sorted_objects[:2])
                st.markdown("---")
    else:
        final_pool = list(player_list)

    # ==========================================
    # 🌲 2. 本선 토너먼트 파트
    # ==========================================
    if (game_method == "토너먼트" or game_method == "혼합 방식 (리그 후 토너먼트)") and len(final_pool) >= 2:

        # 🌟 3. 본선 토너먼트 대진표 헤더 옆에도 즉시 새로고침 배치
        c_tour_title, c_tour_ref = st.columns([5.5, 1.5])
        with c_tour_title:
            st.header("🏆 본선 토너먼트 매치 대진표")
        with c_tour_ref:
            if st.button("🔄 대진표 실시간 동기화", use_container_width=True, type="secondary", key="tour_refresh_btn"):
                st.rerun()

        next_power = 2 ** math.ceil(math.log2(len(final_pool)))
        full_bracket = list(final_pool)
        while len(full_bracket) < next_power:
            full_bracket.append({"id": -1, "name": "부전승", "grade": 0})

        first_round_matches = []
        half = len(full_bracket) // 2
        if game_method == "혼합 방식 (리그 후 토너먼트)" and "선택지 1" in final_rule:
            for i in range(half):
                first_round_matches.append((full_bracket[i], full_bracket[len(full_bracket) - 1 - i]))
        else:
            for i in range(0, len(full_bracket), 2):
                first_round_matches.append((full_bracket[i], full_bracket[i + 1]))

        current_round_players = list(final_pool)
        round_level = 1

        final_ranks_dict = {"우승 (1위)": "미정", "준우승 (2위)": "미정", "공동 3위": []}
        tournament_passed_ids = set()

        while len(current_round_players) > 1:
            p_count = 2 ** math.ceil(math.log2(len(current_round_players)))

            if p_count == 2:
                round_title = "🥇 최종 결승전"
            elif p_count == 4:
                round_title = "🥈 준결승전 (4강)"
            else:
                round_title = f"🟩 본선 {p_count}강전"

            st.subheader(round_title)

            next_round_players = []
            match_pairs = []

            if round_level == 1:
                match_pairs = first_round_matches
            else:
                temp_bracket = list(current_round_players)
                if len(temp_bracket) % 2 != 0:
                    temp_bracket.append({"id": -1, "name": "부전승", "grade": 0})
                for i in range(0, len(temp_bracket), 2):
                    match_pairs.append((temp_bracket[i], temp_bracket[i + 1]))

            round_all_clear = True
            any_valid_match = False

            for idx, (p1, p2) in enumerate(match_pairs):
                if p1["id"] == -1 and p2["id"] == -1: continue
                if p1["id"] == -1:
                    next_round_players.append(p2)
                    continue
                if p2["id"] == -1:
                    next_round_players.append(p1)
                    continue

                any_valid_match = True
                db_p1_id, db_p2_id = (p1['id'], p2['id']) if p1['id'] < p2['id'] else (p2['id'], p1['id'])
                g_code = 900 + round_level
                score_key = (g_code, db_p1_id, db_p2_id)

                s1_t_saved, s2_t_saved = db_scores.get(score_key, (0, 0))

                if p1['id'] == db_p1_id:
                    v1, v2 = s1_t_saved, s2_t_saved
                else:
                    v1, v2 = s2_t_saved, s1_t_saved

                is_recorded = (v1 == 3 or v2 == 3)

                if is_recorded:
                    winner = p1 if v1 > v2 else p2
                    loser = p2 if v1 > v2 else p1
                    next_round_players.append(winner)

                    if loser['id'] in all_league_stats:
                        all_league_stats[loser['id']]["진출단계점수"] = round_level * 1000
                        all_league_stats[loser['id']]["탈락라운드텍스트"] = f"본선 {p_count}강 탈락"

                    if p_count == 2:
                        final_ranks_dict["우승 (1위)"] = f"{winner['name']} ({winner['grade']}부)"
                        final_ranks_dict["준우승 (2위)"] = f"{loser['name']} ({loser['grade']}부)"
                        tournament_passed_ids.add(winner['id'])
                        tournament_passed_ids.add(loser['id'])
                    elif p_count == 4:
                        final_ranks_dict["공동 3위"].append(f"{loser['name']} ({loser['grade']}부)")
                        tournament_passed_ids.add(loser['id'])

                if not is_recorded:
                    round_all_clear = False

                key_t1 = f"t1_val_{active_tour['id']}_{round_level}_{idx}"
                key_t2 = f"t2_val_{active_tour['id']}_{round_level}_{idx}"

                if is_recorded or (s1_t_saved != 0 or s2_t_saved != 0):
                    st.session_state[key_t1] = v1
                    st.session_state[key_t2] = v2
                else:
                    if key_t1 not in st.session_state:
                        st.session_state[key_t1] = v1
                    if key_t2 not in st.session_state:
                        st.session_state[key_t2] = v2

                with st.container():
                    c_m, c_p1, c_s1, c_vs, c_s2, c_p2, c_save = st.columns([1.0, 2.3, 1.1, 0.4, 1.1, 2.3, 1.5])
                    with c_m:
                        st.markdown(
                            f"<div style='margin-top:12px; font-weight:bold; color:#60A5FA; font-size:16px;'>매치 {idx + 1}</div>",
                            unsafe_allow_html=True)
                    with c_p1:
                        st.markdown(
                            f"<div style='background-color:#064E3B; padding:10px; text-align:center; border-radius:8px; font-size:18px; color:#A7F3D0; border:1px solid #059669;'><b>{p1['name']}</b> <span style='font-size:13px; color:#94A3B8;'>({p1['grade']}부)</span></div>",
                            unsafe_allow_html=True)
                    with c_s1:
                        sc1 = st.number_input("🔹", min_value=0, max_value=3, key=key_t1, label_visibility="collapsed",
                                              disabled=is_score_locked)
                    with c_vs:
                        st.markdown(
                            "<div style='text-align:center; padding-top:8px; font-weight:bold; font-size:18px;'>:</div>",
                            unsafe_allow_html=True)
                    with c_s2:
                        sc2 = st.number_input("🔸", min_value=0, max_value=3, key=key_t2, label_visibility="collapsed",
                                              disabled=is_score_locked)
                    with c_p2:
                        st.markdown(
                            f"<div style='background-color:#78350F; padding:10px; text-align:center; border-radius:8px; font-size:18px; color:#FDE68A; border:1px solid #D97706;'><b>{p2['name']}</b> <span style='font-size:13px; color:#94A3B8;'>({p2['grade']}부)</span></div>",
                            unsafe_allow_html=True)

                    with c_save:
                        t_btn_label = "🟢 저장완료" if is_recorded else "💾 결과기록"
                        t_btn_type = "secondary" if is_recorded else "primary"

                        if st.button(t_btn_label, key=f"tsave_{round_level}_{idx}", use_container_width=True,
                                     type=t_btn_type, disabled=is_score_locked):
                            if sc1 == 3 and sc2 == 3:
                                st.error("⚠️ 3:3 동점은 저장할 수 없습니다.")
                            elif sc1 != 3 and sc2 != 3:
                                st.error("⚠️ 한 명은 반드시 3점승이어야 합니다.")
                            else:
                                f_t_p1 = sc1 if p1['id'] == db_p1_id else sc2
                                f_t_p2 = sc2 if p1['id'] == db_p1_id else sc1

                                conn = get_db_connection()
                                cur = conn.cursor()
                                cur.execute("""
                                    INSERT INTO match_results (tournament_id, group_idx, match_order, player1_id, player2_id, player1_score, player2_score) 
                                    VALUES (%s,%s,%s,%s,%s,%s,%s) 
                                    ON CONFLICT (tournament_id, group_idx, player1_id, player2_id) 
                                    DO UPDATE SET player1_score = EXCLUDED.player1_score, player2_score = EXCLUDED.player2_score
                                """, (active_tour['id'], g_code, idx + 1, db_p1_id, db_p2_id, f_t_p1, f_t_p2))
                                conn.commit()
                                cur.close()
                                conn.close()
                                st.success(f"🎉 본선 매치 결과 저장 성공!")
                                st.rerun()

            if p_count == 2 and round_all_clear and any_valid_match:
                if len(next_round_players) > 0:
                    st.markdown("---")
                    st.subheader("🏅 본선 토너먼트 최종 종합 순위 결과")

                    c_tr1, c_tr2, c_tr3 = st.columns(3)
                    with c_tr1:
                        st.markdown(
                            f"<div style='background-color:#78350F; padding:18px; border-radius:10px; text-align:center; border:2px solid #F59E0B;'><h4>🥇 우승 (1위)</h4><h2 style='color:#FBBF24;'>{final_ranks_dict['우승 (1위)']}</h2></div>",
                            unsafe_allow_html=True)
                    with c_tr2:
                        st.markdown(
                            f"<div style='background-color:#334155; padding:18px; border-radius:10px; text-align:center; border:2px solid #9CA3AF;'><h4>🥈 준우승 (2위)</h4><h2 style='color:#E2E8F0;'>{final_ranks_dict['준우승 (2위)']}</h2></div>",
                            unsafe_allow_html=True)
                    with c_tr3:
                        th3_players = ", ".join(final_ranks_dict["공동 3위"]) if final_ranks_dict["공동 3위"] else "없음"
                        st.markdown(
                            f"<div style='background-color:#451A03; padding:18px; border-radius:10px; text-align:center; border:2px solid #F97316;'><h4>🥉 공동 3위</h4><h3 style='color:#FB923C; margin-top:8px;'>{th3_players}</h3></div>",
                            unsafe_allow_html=True)

                    if st.session_state.user_role == "admin" and not is_tournament_finished:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("🏆 본 대회 최종 마감 및 종료하기 (수정 권한 영구 자물쇠)", use_container_width=True, type="primary"):
                            try:
                                conn = get_db_connection()
                                cur = conn.cursor()
                                cur.execute("UPDATE tournaments SET status = 'finished' WHERE id = %s",
                                            (active_tour['id'],))
                                conn.commit()
                                cur.close()
                                conn.close()
                                st.balloons()
                                st.success("🎉 대회가 마감되었습니다! 이제 모든 회원 화면이 완성된 결과로 영구 고정됩니다.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"마감 처리 실패: {e}")

                    if all_league_stats:
                        st.markdown("### 📉 5위 이하 최종 종합 순위표 (토너먼트 성적 + 리그 세트득실 합산)")

                        lower_ranks = [v for k, v in all_league_stats.items() if k not in tournament_passed_ids]
                        lower_ranks_sorted = sorted(lower_ranks, key=lambda x: (x["진출단계점수"], x["승"], x["득실차"]),
                                                    reverse=True)

                        if lower_ranks_sorted:
                            display_data = []
                            for rank_idx, item in enumerate(lower_ranks_sorted):
                                display_data.append({
                                    "rank": f"{5 + rank_idx}위",
                                    "name": item["name"],
                                    "grade": f"{item['grade']}부",
                                    "t_result": item["탈락라운드텍스트"],
                                    "l_wins": f"{item['승']}승",
                                    "l_diff": f"{item['득실차']:+d} 세트"
                                })

                            html_table = "<div class='luxury-table-container'>"
                            html_table += "<table class='luxury-table'>"
                            html_table += "<thead><tr><th>최종 순위</th><th>선수명</th><th>부수</th><th>토너먼트 성적</th><th>예선 리그 승수</th><th>예선 세트 득실차</th></tr></thead>"
                            html_table += "<tbody>"

                            for row in display_data:
                                diff_class = "text-plus-item" if "+" in row['l_diff'] else "text-minus-item" if "-" in \
                                                                                                                row[
                                                                                                                    'l_diff'] and "0" not in \
                                                                                                                row[
                                                                                                                    'l_diff'] else "text-gray-item"

                                html_table += "<tr>"
                                html_table += f"<td><span class='rank-badge-item'>{row['rank']}</span></td>"
                                html_table += f"<td class='name-cell-item'>{row['name']}</td>"
                                html_table += f"<td><span class='text-gray-item'>{row['grade']}</span></td>"
                                html_table += f"<td style='color: #818CF8; font-weight: 600;'>{row['t_result']}</td>"
                                html_table += f"<td class='wins-cell-item'>{row['l_wins']}</td>"
                                html_table += f"<td class='{diff_class}'>{row['l_diff']}</td>"
                                html_table += "</tr>"

                            html_table += "</tbody></table></div>"

                            st.markdown(html_table, unsafe_allow_html=True)
                break

            if not round_all_clear or not any_valid_match:
                st.info(f"💡 **{round_title}**의 모든 매치 성적이 기록되면 다음 라운드 대진표가 하단에 실시간으로 생성됩니다.")
                break

            current_round_players = next_round_players
            round_level += 1
            st.markdown("---")