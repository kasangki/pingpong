import streamlit as st
import pandas as pd

def run_tab_ranking(get_db_connection):
    st.header("📊 연도별 동호회 통합 등수 / 랭킹 산정판")
    col_y, col_g = st.columns([1, 1])
    with col_y:
        ranking_year = st.selectbox("📅 조회 연도 선택", ["2026", "2025", "2024"])
    with col_g:
        grade_filter = st.selectbox("🏓 대상 부수 범위 필터", ["전체 부수 보기", "상위권 (1~5부)", "하위권 (6부 이하)"])

    try:
        conn = get_db_connection()
        df_year_tours = pd.read_sql(f"SELECT id, title FROM tournaments WHERE EXTRACT(YEAR FROM created_at) = {ranking_year}", conn)

        if df_year_tours.empty:
            st.info(f"📅 {ranking_year}년도에는 아직 대회 데이터가 없습니다.")
            conn.close()
            return

        tour_ids = tuple(df_year_tours['id'].tolist())
        tour_ids_str = f"({tour_ids[0]})" if len(tour_ids) == 1 else str(tour_ids)
        df_all_res = pd.read_sql(f"SELECT tournament_id, group_idx, player1_name, player2_name, score_text FROM match_results WHERE tournament_id IN {tour_ids_str}", conn)
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
            df_final_rank.insert(0, "🥇 최종 순위", df_final_rank["📊 누적 랭킹 포인트"].rank(ascending=False, method="min").astype(int))
            st.dataframe(df_final_rank, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"랭킹 산정 오류: {e}")