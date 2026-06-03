import streamlit as st
import pandas as pd
import math

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

def run_tab_play(get_db_connection):
    st.header("3. 실시간 경기 진행 및 결과 기록")
    try:
        conn = get_db_connection()
        df_active_t = pd.read_sql("SELECT id, title FROM tournaments ORDER BY id DESC", conn)
        conn.close()
    except:
        df_active_t = pd.DataFrame()

    if df_active_t.empty:
        st.warning("개설된 대회가 없습니다. 관리자가 대회를 먼저 생성해야 합니다.")
        return

    active_tour = st.selectbox("진행할 대회를 선택하세요", df_active_t.to_dict('records'), format_func=lambda x: x['title'])
    try:
        conn = get_db_connection()
        df_players = pd.read_sql(f"SELECT m.name, m.grade FROM tournament_players tp JOIN members m ON tp.member_id = m.id WHERE tp.tournament_id = {active_tour['id']} ORDER BY m.id ASC", conn)
        df_saved_matches = pd.read_sql(f"SELECT group_idx, player1_name, player2_name, score_text FROM match_results WHERE tournament_id = {active_tour['id']}", conn)
        conn.close()
    except:
        df_players, df_saved_matches = pd.DataFrame(), pd.DataFrame()

    if len(df_players) < 2:
        st.info("출전 선수가 부족합니다. (최소 2명 필요)")
        return

    if "db_scores" not in st.session_state:
        st.session_state.db_scores = {}
    for _, row in df_saved_matches.iterrows():
        st.session_state.db_scores[(row['group_idx'], row['player1_name'], row['player2_name'])] = row['score_text']

    col_method, col_group_num = st.columns([2, 1])
    with col_method:
        game_method = st.radio("경기 방식 선택", ["라운드로빈(풀리그)", "토너먼트", "혼합 방식 (리그 후 토너먼트)"], index=2 if len(df_players) >= 4 else 0, horizontal=True)
    with col_group_num:
        if game_method in ["라운드로빈(풀리그)", "혼합 방식 (리그 후 토너먼트)"]:
            max_groups = max(1, len(df_players) // 2)
            num_groups = st.number_input("📋 생성할 조(Group) 갯수", min_value=1, max_value=max_groups, value=2 if len(df_players) >= 4 else 1, step=1)
        else:
            num_groups = 1

    final_rule = "선택지 1"
    if game_method == "혼합 방식 (리그 후 토너먼트)":
        final_rule = st.radio("본선 대진표 구성 방식", ["선택지 1 (전체 크로스 - 전원 본선행)", "선택지 2 (상위권 본선 - 조 1,2위만 본선행)"], horizontal=True)
    st.markdown("---")

    player_list = df_players.to_dict('records')
    final_pool = []

    if game_method in ["라운드로빈(풀리그)", "혼합 방식 (리그 후 토너먼트)"]:
        groups = [[] for _ in range(num_groups)]
        for idx, p in enumerate(player_list):
            groups[idx % num_groups].append(p)

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
                    st.markdown(f"<div style='margin-top:12px; color:gray;'>{idx + 1}경기</div>", unsafe_allow_html=True)
                with c_p1:
                    st.markdown(f"<div style='background-color:#F3F4F6; padding:6px; border-radius:4px; text-align:center;'><b>{p1}</b></div>", unsafe_allow_html=True)
                with c_s1:
                    sc1 = st.number_input("🔹", min_value=0, max_value=5, value=v1, step=1, key=f"s1_{group_idx}_{idx}", label_visibility="collapsed")
                with c_vs:
                    st.markdown("<div style='text-align:center; padding-top:4px;'>:</div>", unsafe_allow_html=True)
                with c_s2:
                    sc2 = st.number_input("🔸", min_value=0, max_value=5, value=v2, step=1, key=f"s2_{group_idx}_{idx}", label_visibility="collapsed")
                with c_p2:
                    st.markdown(f"<div style='background-color:#F3F4F6; padding:6px; border-radius:4px; text-align:center;'><b>{p2}</b></div>", unsafe_allow_html=True)
                with c_btn:
                    if st.button("💾 저장", key=f"b_{group_idx}_{idx}", use_container_width=True):
                        final_score = f"{sc1}:{sc2}" if p1 == db_p1 else f"{sc2}:{sc1}"
                        st.session_state.db_scores[score_key] = final_score
                        conn = get_db_connection()
                        cur = conn.cursor()
                        cur.execute("INSERT INTO match_results (tournament_id, group_idx, match_order, player1_name, player2_name, score_text) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (tournament_id, group_idx, player1_name, player2_name) DO UPDATE SET score_text = EXCLUDED.score_text", (active_tour['id'], group_idx, idx + 1, db_p1, db_p2, final_score))
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
                for i in range(0, len(temp_bracket), 2):
                    match_pairs.append((temp_bracket[i], temp_bracket[i + 1]))

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
                    st.markdown(f"<div style='margin-top:10px; color:#1E3A8A;'>매치 {idx + 1}</div>", unsafe_allow_html=True)
                with c_p1:
                    st.markdown(f"<div style='background-color:#ECFDF5; padding:6px; text-align:center;'><b>{p1}</b></div>", unsafe_allow_html=True)
                with c_s1:
                    sc1 = st.number_input("🔹", min_value=0, max_value=5, value=v1, step=1, key=f"t1_{round_level}_{idx}", label_visibility="collapsed")
                with c_vs:
                    st.markdown("<div style='text-align:center; padding-top:4px;'>:</div>", unsafe_allow_html=True)
                with c_s2:
                    sc2 = st.number_input("🔸", min_value=0, max_value=5, value=v2, step=1, key=f"t2_{round_level}_{idx}", label_visibility="collapsed")
                with c_p2:
                    st.markdown(f"<div style='background-color:#FFFBEB; padding:6px; text-align:center;'><b>{p2}</b></div>", unsafe_allow_html=True)
                with c_save:
                    if st.button("💾 기록", key=f"tsave_{round_level}_{idx}", use_container_width=True):
                        final_score = f"{sc1}:{sc2}" if p1 == db_p1 else f"{sc2}:{sc1}"
                        st.session_state.db_scores[score_key] = final_score
                        conn = get_db_connection()
                        cur = conn.cursor()
                        cur.execute("INSERT INTO match_results (tournament_id, group_idx, match_order, player1_name, player2_name, score_text) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (tournament_id, group_idx, player1_name, player2_name) DO UPDATE SET score_text = EXCLUDED.score_text", (active_tour['id'], g_code, idx + 1, db_p1, db_p2, final_score))
                        conn.commit()
                        cur.close()
                        conn.close()
                        st.rerun()

            total_expected_matches = len([m for m in match_pairs if m[0] != "부전승" and m[1] != "부전승"])
            recorded_matches_count = sum(1 for m in match_pairs if (g_code, (m[0] if m[0] < m[1] else m[1]), (m[1] if m[0] < m[1] else m[0])) in st.session_state.db_scores)

            if recorded_matches_count < total_expected_matches:
                st.warning(f"💡 모든 경기가 기록되어야 다음 라운드가 노출됩니다. ({recorded_matches_count}/{total_expected_matches})")
                break
            current_round_players = next_round_players
            round_level += 1
            st.markdown("---")

        if len(current_round_players) == 1:
            st.balloons()
            st.success(f"👑 최종 우승자: **[{current_round_players[0]}]**")