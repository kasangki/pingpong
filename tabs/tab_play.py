import streamlit as st
import pandas as pd
import math


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
        df_players = pd.read_sql(
            f"SELECT m.id, m.name, m.grade FROM tournament_players tp JOIN members m ON tp.member_id = m.id WHERE tp.tournament_id = {active_tour['id']} ORDER BY m.id ASC",
            conn)
        df_saved_matches = pd.read_sql(
            f"SELECT group_idx, player1_id, player2_id, score_text FROM match_results WHERE tournament_id = {active_tour['id']}",
            conn)
        conn.close()
    except:
        df_players, df_saved_matches = pd.DataFrame(), pd.DataFrame()

    if len(df_players) < 2:
        st.info("출전 선수가 부족합니다. (최소 2명 필요)")
        return

    db_scores = {}
    for _, row in df_saved_matches.iterrows():
        db_scores[(int(row['group_idx']), int(row['player1_id']), int(row['player2_id']))] = row['score_text']

    # -------------------------------------------------------------
    # 🔒 경기 진행 여부 및 대회 종료 여부 검증
    # -------------------------------------------------------------
    is_game_started = len(db_scores) > 0
    is_tournament_finished = False

    t_match_keys = [k for k in db_scores.keys() if k[0] >= 901]
    if t_match_keys:
        max_round_level = max(t_match_keys)
        for k, score in db_scores.items():
            if k[0] == max_round_level and ":" in score:
                s1, s2 = map(int, score.split(":"))
                if s1 == 3 or s2 == 3:
                    is_tournament_finished = True

    is_ui_disabled = is_game_started or is_tournament_finished
    is_score_locked = False if st.session_state.user_role == "admin" else True

    if is_tournament_finished:
        st.success("🏆 본 대회가 종료되어 결과가 안전하게 보존되었습니다. (경기 방식 및 조 설정 변경 기능 잠금)")
    elif is_game_started:
        st.info("📊 현재 경기가 진행 중이므로 경기 방식 및 조 갯수 설정이 고정되었습니다.")

    # -------------------------------------------------------------
    # 🛠️ 경기 방식 및 조 개수 입력 UI
    # -------------------------------------------------------------
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
            max_groups = max(1, len(df_players) // 2)
            default_g_value = 2 if max_groups >= 2 else 1

            num_groups = st.number_input(
                "📋 생성할 조(Group) 갯수",
                min_value=1,
                max_value=max_groups,
                value=default_g_value,
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

    # 📉 전체 참가자의 예선 리그 성적을 추적하는 메인 딕셔너리
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
                saved_score = db_scores.get(score_key, "0:0")

                v1, v2 = 0, 0
                if ":" in saved_score:
                    s1, s2 = saved_score.split(":")
                    v1, v2 = (int(s1), int(s2)) if db_p1_id == p1['id'] else (int(s2), int(s1))

                c_num, c_p1, c_s1, c_vs, c_s2, c_p2, c_btn = st.columns([0.8, 2.5, 1, 0.4, 1, 2.5, 1.2])
                with c_num:
                    st.markdown(f"<div style='margin-top:12px; color:gray;'>{idx + 1}경기</div>", unsafe_allow_html=True)
                with c_p1:
                    st.markdown(
                        f"<div style='background-color:#F3F4F6; padding:6px; text-align:center;'><b>{p1['name']}</b></div>",
                        unsafe_allow_html=True)
                with c_s1:
                    sc1 = st.number_input("🔹", min_value=0, max_value=3, value=v1, step=1, key=f"s1_{group_idx}_{idx}",
                                          label_visibility="collapsed", disabled=is_score_locked)
                with c_vs:
                    st.markdown("<div style='text-align:center; padding-top:4px;'>:</div>", unsafe_allow_html=True)
                with c_s2:
                    sc2 = st.number_input("🔸", min_value=0, max_value=3, value=v2, step=1, key=f"s2_{group_idx}_{idx}",
                                          label_visibility="collapsed", disabled=is_score_locked)
                with c_p2:
                    st.markdown(
                        f"<div style='background-color:#F3F4F6; padding:6px; text-align:center;'><b>{p2['name']}</b></div>",
                        unsafe_allow_html=True)

                with c_btn:
                    if st.button("💾 저장", key=f"b_{group_idx}_{idx}", use_container_width=True):
                        if sc1 == 3 and sc2 == 3:
                            st.error("⚠️ 3:3 동점은 입력할 수 없습니다.")
                        elif sc1 != 3 and sc2 != 3:
                            st.error("⚠️ 세트 종료 기준 미달 (3점 선취 필요)")
                        else:
                            final_score = f"{sc1}:{sc2}" if p1['id'] == db_p1_id else f"{sc2}:{sc1}"
                            conn = get_db_connection()
                            cur = conn.cursor()
                            cur.execute(
                                "INSERT INTO match_results (tournament_id, group_idx, match_order, player1_id, player2_id, score_text) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (tournament_id, group_idx, player1_id, player2_id) DO UPDATE SET score_text = EXCLUDED.score_text",
                                (active_tour['id'], group_idx, idx + 1, db_p1_id, db_p2_id, final_score))
                            conn.commit()
                            cur.close()
                            conn.close()
                            st.rerun()

            rank_stats = []
            for p in group_players:
                wins, set_gain, set_loss = 0, 0, 0
                for opp in group_players:
                    if p['id'] == opp['id']: continue
                    r1_id, r2_id = (p['id'], opp['id']) if p['id'] < opp['id'] else (opp['id'], p['id'])
                    score = db_scores.get((group_idx, r1_id, r2_id), "")
                    if ":" in score:
                        s1, s2 = map(int, score.split(":"))
                        p_score = s1 if p['id'] == r1_id else s2
                        opp_score = s2 if p['id'] == r1_id else s1
                        set_gain += p_score
                        set_loss += opp_score
                        if p_score > opp_score: wins += 1

                rank_stats.append({
                    "player_obj": p, "id": p['id'], "name": p['name'], "grade": p['grade'],
                    "승": wins, "득실차": (set_gain - set_loss)
                })

            for i in range(len(rank_stats)):
                h2h_bonus = 0
                for j in range(len(rank_stats)):
                    if i == j: continue
                    if rank_stats[i]["승"] == rank_stats[j]["승"] and rank_stats[i]["득실차"] == rank_stats[j]["득실차"]:
                        p1_id, p2_id = rank_stats[i]["id"], rank_stats[j]["id"]
                        r1_id, r2_id = (p1_id, p2_id) if p1_id < p2_id else (p2_id, p1_id)
                        score = db_scores.get((group_idx, r1_id, r2_id), "")
                        if ":" in score:
                            s1, s2 = map(int, score.split(":"))
                            if (p1_id == r1_id and s1 > s2) or (p1_id == r2_id and s2 > s1):
                                h2h_bonus += 0.1
                rank_stats[i]["승자승점수"] = rank_stats[i]["득실차"] + h2h_bonus

            rank_stats_sorted = sorted(rank_stats, key=lambda x: (x["승"], x["승자승점수"]), reverse=True)

            st.markdown(f"#### 📊 {group_idx + 1}조 리그전 현재 순위 등수표")
            if f"manual_rank_{active_tour['id']}_{group_idx}" not in st.session_state:
                st.session_state[f"manual_rank_{active_tour['id']}_{group_idx}"] = {}
            m_ranks = st.session_state[f"manual_rank_{active_tour['id']}_{group_idx}"]

            c_h1, c_h2, c_h3, c_h4, c_h5 = st.columns([1, 2.5, 1.2, 1.2, 3.1])
            c_h1.markdown("**등수**")
            c_h2.markdown("**선수 정보**")
            c_h3.markdown("**승률**")
            c_h4.markdown("**세트득실**")
            c_h5.markdown("**순위 강제 조정**")

            final_ordered_players = []
            for idx, stat in enumerate(rank_stats_sorted):
                p = stat["player_obj"]
                default_rank = m_ranks.get(p['id'], idx + 1)

                c_b1, c_b2, c_b3, c_b4, c_b5 = st.columns([1, 2.5, 1.2, 1.2, 3.1])
                medal = f"🥇 {default_rank}위" if default_rank == 1 else f"🥈 {default_rank}위" if default_rank == 2 else f"🥉 {default_rank}위" if default_rank == 3 else f"🏅 {default_rank}위"
                c_b1.markdown(f"**{medal}**")
                c_b2.markdown(f"**{stat['name']}** ({stat['grade']}부)")
                c_b3.markdown(f"{stat['승']}승")
                c_b4.markdown(f"{stat['득실차']:+d}")

                with c_b5:
                    new_rank = st.number_input(
                        f"등수 변경 {stat['name']}", min_value=1, max_value=len(group_players),
                        value=int(default_rank), step=1, key=f"mr_{group_idx}_{p['id']}", label_visibility="collapsed"
                    )
                    m_ranks[p['id']] = new_rank

                final_ordered_players.append({"player_obj": p, "final_rank": new_rank, "name": p['name']})

                if p['id'] in all_league_stats:
                    all_league_stats[p['id']]["승"] = stat['승']
                    all_league_stats[p['id']]["득실차"] = stat['득실차']

            final_ordered_players = sorted(final_ordered_players, key=lambda x: x["final_rank"])

            total_matches_count = len(round_matches)
            recorded_matches_count = sum(1 for (p1, p2) in round_matches if (
            group_idx, p1['id'] if p1['id'] < p2['id'] else p2['id'],
            p2['id'] if p1['id'] < p2['id'] else p1['id']) in db_scores)

            if total_matches_count == recorded_matches_count:
                st.markdown(f"##### 🏁 [{group_idx + 1}조 리그전 확정 최종 등수]")
                result_strings = [f"**{item['final_rank']}위**: {item['name']}" for item in final_ordered_players]
                st.info(" ➡️ ".join(result_strings))

            return [item["player_obj"] for item in final_ordered_players]

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
        st.header("🏆 본선 토너먼트 매치 대진표")

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
                saved_score = db_scores.get(score_key, "0:0")

                v1, v2 = 0, 0
                is_recorded = False
                if score_key in db_scores:
                    s1, s2 = saved_score.split(":")
                    v1, v2 = (int(s1), int(s2)) if db_p1_id == p1['id'] else (int(s2), int(s1))
                    if v1 != 0 or v2 != 0:
                        is_recorded = True
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

                c_m, c_p1, c_s1, c_vs, c_s2, c_p2, c_save = st.columns([1.0, 2.3, 1.1, 0.4, 1.1, 2.3, 1.2])
                with c_m:
                    st.markdown(f"<div style='margin-top:10px; font-weight:bold; color:#1E3A8A;'>매치 {idx + 1}</div>",
                                unsafe_allow_html=True)
                with c_p1:
                    st.markdown(
                        f"<div style='background-color:#ECFDF5; padding:6px; text-align:center; border-radius:4px;'><b>{p1['name']}</b> <span style='font-size:11px; color:gray;'>({p1['grade']}부)</span></div>",
                        unsafe_allow_html=True)
                with c_s1:
                    sc1 = st.number_input("🔹", min_value=0, max_value=3, value=v1, step=1,
                                          key=f"t1_{round_level}_{idx}", label_visibility="collapsed",
                                          disabled=is_score_locked)
                with c_vs:
                    st.markdown("<div style='text-align:center; padding-top:4px; font-weight:bold;'>:</div>",
                                unsafe_allow_html=True)
                with c_s2:
                    sc2 = st.number_input("🔸", min_value=0, max_value=3, value=v2, step=1,
                                          key=f"t2_{round_level}_{idx}", label_visibility="collapsed",
                                          disabled=is_score_locked)
                with c_p2:
                    st.markdown(
                        f"<div style='background-color:#FFFBEB; padding:6px; text-align:center; border-radius:4px;'><b>{p2['name']}</b> <span style='font-size:11px; color:gray;'>({p2['grade']}부)</span></div>",
                        unsafe_allow_html=True)

                with c_save:
                    if st.button("💾 기록", key=f"tsave_{round_level}_{idx}", use_container_width=True,
                                 type="secondary" if is_recorded else "primary"):
                        if sc1 == 3 and sc2 == 3:
                            st.error("⚠️ 3:3 동점은 저장할 수 없습니다.")
                        elif sc1 != 3 and sc2 != 3:
                            st.error("⚠️ 한 명은 반드시 3점승이어야 합니다.")
                        else:
                            final_score = f"{sc1}:{sc2}" if p1['id'] == db_p1_id else f"{sc2}:{sc1}"
                            conn = get_db_connection()
                            cur = conn.cursor()
                            cur.execute(
                                "INSERT INTO match_results (tournament_id, group_idx, match_order, player1_id, player2_id, score_text) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (tournament_id, group_idx, player1_id, player2_id) DO UPDATE SET score_text = EXCLUDED.score_text",
                                (active_tour['id'], g_code, idx + 1, db_p1_id, db_p2_id, final_score))
                            conn.commit()
                            cur.close()
                            conn.close()
                            st.toast(f"매치 {idx + 1} 결과 기록 완료!")
                            st.rerun()

            if p_count == 2 and round_all_clear and any_valid_match:
                if len(next_round_players) > 0:
                    st.balloons()
                    st.success(f"🏆 축하합니다!! 본 대회의 최종 우승자는 **[{next_round_players[0]['name']}]** 선수입니다!!")

                    st.markdown("---")
                    st.subheader("🏅 본선 토너먼트 최종 종합 순위 결과")

                    c_tr1, c_tr2, c_tr3 = st.columns(3)
                    with c_tr1:
                        st.markdown(
                            f"<div style='background-color:#FEF3C7; padding:15px; border-radius:8px; text-align:center; border:2px solid #F59E0B;'><h5>🥇 우승 (1위)</h5><h3 style='color:#B45309;'>{final_ranks_dict['우승 (1위)']}</h3></div>",
                            unsafe_allow_html=True)
                    with c_tr2:
                        st.markdown(
                            f"<div style='background-color:#E5E7EB; padding:15px; border-radius:8px; text-align:center; border:2px solid #9CA3AF;'><h5>🥈 준우승 (2위)</h5><h3 style='color:#4B5563;'>{final_ranks_dict['준우승 (2위)']}</h3></div>",
                            unsafe_allow_html=True)
                    with c_tr3:
                        th3_players = ", ".join(final_ranks_dict["공동 3위"]) if final_ranks_dict["공동 3위"] else "없음"
                        st.markdown(
                            f"<div style='background-color:#FFEDD5; padding:15px; border-radius:8px; text-align:center; border:2px solid #F97316;'><h5>🥉 공동 3위</h5><h4 style='color:#C2410C; margin-top:8px;'>{th3_players}</h4></div>",
                            unsafe_allow_html=True)

                    # -------------------------------------------------------------
                    # 🏁 [HTML 깨짐 수정 패치 완료] 커스텀 스타일 테이블 구역
                    # -------------------------------------------------------------
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

                            # 파싱 충돌을 방지하기 위해 HTML 코드의 들여쓰기를 완벽히 제거(바짝 붙임) 처리
                            html_table = "<style>"
                            html_table += ".custom-table { width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 15px; font-family: 'Malgun Gothic', sans-serif; text-align: center; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05); }"
                            html_table += ".custom-table thead tr { background-color: #4F46E5; color: #ffffff; font-weight: bold; height: 45px; }"
                            html_table += ".custom-table th, .custom-table td { padding: 12px 15px; border-bottom: 1px solid #E5E7EB; }"
                            html_table += ".custom-table tbody tr { transition: background-color 0.2s ease; }"
                            html_table += ".custom-table tbody tr:hover { background-color: #F9FAFB; }"
                            html_table += ".custom-table tbody tr:last-of-type { border-bottom: 2px solid #4F46E5; }"
                            html_table += ".rank-badge { background-color: #EF4444; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 13px; }"
                            html_table += ".text-bold { font-weight: bold; color: #1F2937; }"
                            html_table += ".text-gray { color: #6B7280; }"
                            html_table += ".text-plus { color: #2563EB; font-weight: bold; }"
                            html_table += ".text-minus { color: #DC2626; font-weight: bold; }"
                            html_table += "</style>"
                            html_table += "<table class='custom-table'>"
                            html_table += "<thead><tr><th>최종 순위</th><th>선수명</th><th>부수</th><th>토너먼트 성적</th><th>예선 리그 승수</th><th>예선 세트 득실차</th></tr></thead>"
                            html_table += "<tbody>"

                            for row in display_data:
                                diff_class = "text-plus" if "+" in row['l_diff'] else "text-minus" if "-" in row[
                                    'l_diff'] and row['l_diff'] != "-0 세트" else "text-gray"

                                html_table += "<tr>"
                                html_table += f"<td><span class='rank-badge'>{row['rank']}</span></td>"
                                html_table += f"<td class='text-bold'>{row['name']}</td>"
                                html_table += f"<td><span class='text-gray'>{row['grade']}</span></td>"
                                html_table += f"<td style='color: #4F46E5; font-weight: 500;'>{row['t_result']}</td>"
                                html_table += f"<td class='text-bold'>{row['l_wins']}</td>"
                                html_table += f"<td class='{diff_class}'>{row['l_diff']}</td>"
                                html_table += "</tr>"

                            html_table += "</tbody></table>"

                            st.markdown(html_table, unsafe_allow_html=True)
                        else:
                            st.info("5위 이하 대상 선수가 존재하지 않습니다.")
                break

            if not round_all_clear or not any_valid_match:
                st.info(f"💡 **{round_title}**의 모든 매치 성적이 기록되면 다음 라운드 대진표가 하단에 실시간으로 생성됩니다.")
                break

            current_round_players = next_round_players
            round_level += 1
            st.markdown("---")