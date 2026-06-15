import streamlit as st
import pandas as pd


def render_ranking_table(ranking_data):
    """럭셔리 랭킹 테이블 렌더링 함수 (다크 모드 최적화)"""
    html_table = "<style>"
    html_table += ".ranking-container { width: 100%; margin: 20px 0; background: #1E293B; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.3); border: 1px solid #334155; overflow: hidden; }"
    html_table += ".ranking-table { width: 100%; border-collapse: collapse; text-align: center; font-family: 'Pretendard', sans-serif; }"
    html_table += ".ranking-table thead { background: #1E1B4B; border-bottom: 2px solid #334155; }"
    html_table += ".ranking-table th { padding: 16px; color: #94A3B8; font-weight: 700; font-size: 0.95rem; letter-spacing: 0.05em; }"
    html_table += ".ranking-table td { padding: 16px; border-bottom: 1px solid #334155; color: #F1F5F9; }"
    html_table += ".ranking-table tbody tr:hover { background-color: #334155; transition: 0.2s; }"
    html_table += ".rank-num { font-weight: 800; font-size: 1.1rem; }"
    html_table += ".gold { color: #FBBF24; background: #78350F; padding: 4px 12px; border-radius: 20px; font-weight: bold; }"
    html_table += ".silver { color: #E2E8F0; background: #334155; padding: 4px 12px; border-radius: 20px; font-weight: bold; }"
    html_table += ".bronze { color: #FB923C; background: #451A03; padding: 4px 12px; border-radius: 20px; font-weight: bold; }"
    html_table += ".name-cell { font-weight: 700; font-size: 1.1rem; color: #FFFFFF; }"
    html_table += ".wins-cell { color: #818CF8; font-weight: 800; font-size: 1.15rem; }"
    html_table += "</style>"

    html_table += "<div class='ranking-container'><table class='ranking-table'>"
    html_table += "<thead><tr><th>순위</th><th>선수 이름</th><th>부수</th><th>총 승리 (순수 승수)</th></tr></thead><tbody>"

    for row in ranking_data:
        rank = int(row['rank'])
        if rank == 1:
            rank_cls, rank_txt = "gold", f"🥇 {rank}위"
        elif rank == 2:
            rank_cls, rank_txt = "silver", f"🥈 {rank}위"
        elif rank == 3:
            rank_cls, rank_txt = "bronze", f"🥉 {rank}위"
        else:
            rank_cls, rank_txt = "rank-num", f"{rank}위"

        html_table += f"<tr><td><span class='{rank_cls}'>{rank_txt}</span></td><td class='name-cell'>{row['name']}</td><td style='color:#94A3B8;'>{row['grade']}부</td><td class='wins-cell'>{row['total_wins']}승</td></tr>"

    html_table += "</tbody></table></div>"
    return html_table


def run_tab_ranking(get_db_connection):
    # 타이틀 우측에 즉시 동기화 새로고침 배치
    c_title, c_ref = st.columns([5.5, 1.5])
    with c_title:
        st.header("📊 연도별 통합 랭킹")
    with c_ref:
        if st.button("🔄 실시간 랭킹 갱신", use_container_width=True, type="secondary", key="ranking_refresh_btn"):
            st.rerun()

    # 전역 세션에서 현재 로그인한 동호회 고유 번호(club_id) 확보
    club_id = st.session_state.club_id

    # 1. 연도 선택 셀렉트박스
    current_year = pd.Timestamp.now().year
    year = st.selectbox("조회할 연도를 선택하세요", list(range(current_year, current_year - 5, -1)))

    try:
        conn = get_db_connection()

        # 💡 [SaaS 알고리즘 고도화 패치]
        # 무겁게 컬럼을 늘리는 대신, 본선 토너먼트 그룹 코드(901 이상)에서 승리한 기록에 '1.2점' 가중치를 곱해 SUM 해버립니다.
        # 이렇게 하면 같은 승수여도 본선에서 우승, 준우승을 차지하며 치고 올라간 엘리트 선수가 랭킹 정렬에서 무조건 우선권을 쥡니다!
        query = """
            SELECT m.name, m.grade, 
                   COUNT(*) as total_wins,
                   SUM(CASE WHEN mr.group_idx >= 900 THEN 1.2 ELSE 1.0 END) as ranking_score
            FROM match_results mr
            JOIN tournaments t ON mr.tournament_id = t.id
            JOIN members m ON (
                (mr.player1_id = m.id AND mr.player1_score = 3) OR 
                (mr.player2_id = m.id AND mr.player2_score = 3)
            )
            WHERE t.club_id = %s 
              AND m.club_id = %s
              AND m.status = 'active'
              AND mr.player1_id != -1 
              AND mr.player2_id != -1
              AND EXTRACT(YEAR FROM t.created_at) = %s
            GROUP BY m.id, m.name, m.grade
            ORDER BY ranking_score DESC, total_wins DESC
        """

        # 파라미터 바인딩
        df_ranking = pd.read_sql(query, conn, params=(club_id, club_id, year))
        conn.close()

        if df_ranking.empty:
            st.info(f"ℹ️ {year}년도에는 기록된 경기 데이터가 없습니다.")
        else:
            # 랭킹 데이터 가공 및 공동 순위(동률) 처리
            ranking_list = []
            current_rank = 1

            for i, row in df_ranking.iterrows():
                # 가중치 랭킹 스코어가 완전히 일치할 때만 공동 순위 처리
                if i > 0 and row['ranking_score'] == df_ranking.iloc[i - 1]['ranking_score']:
                    pass
                else:
                    current_rank = i + 1

                ranking_list.append({
                    "rank": current_rank,
                    "name": row['name'],
                    "grade": row['grade'],
                    "total_wins": row['total_wins']
                })

            # 고급 야간모드 디자인 테이블 출력
            st.markdown(render_ranking_table(ranking_list), unsafe_allow_html=True)

            # 통계 그래프
            st.subheader("📈 승리 횟수 분포")
            st.bar_chart(df_ranking.set_index('name')['total_wins'])

    except Exception as e:
        st.error(f"❌ 랭킹 데이터를 불러오는 중 오류가 발생했습니다: {e}")