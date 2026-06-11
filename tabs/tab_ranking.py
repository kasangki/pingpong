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
    html_table += "<thead><tr><th>순위</th><th>선수 이름</th><th>부수</th><th>총 승리 횟수</th></tr></thead><tbody>"

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
    st.header("📊 연도별 통합 랭킹")

    # 전역 세션에서 현재 로그인한 동호회 고유 번호(club_id) 확보
    club_id = st.session_state.club_id

    # 1. 연도 선택 셀렉트박스
    current_year = pd.Timestamp.now().year
    year = st.selectbox("조회할 연도를 선택하세요", list(range(current_year, current_year - 5, -1)))

    try:
        conn = get_db_connection()

        # 💡 [SaaS 최적화 쿼리 패치]
        # 1. t.club_id = %s 조건을 통해 우리 탁구클럽 안에서 열린 대회 기록만 정확히 필터링합니다.
        # 2. m.status = 'active' 조건만 남겨둠으로써, 'member' 권한이든 'admin'(구장 관리자) 권한이든
        #    정상적으로 시합을 뛰고 활성화된 계정이라면 차별 없이 랭킹 데이터 산출에 포함되도록 집계를 보완했습니다.
        query = """
            SELECT m.name, m.grade, COUNT(*) as total_wins
            FROM match_results mr
            JOIN tournaments t ON mr.tournament_id = t.id
            JOIN members m ON (
                (mr.player1_id = m.id AND mr.score_text LIKE '3:%%') OR 
                (mr.player2_id = m.id AND mr.score_text LIKE '%%:3')
            )
            WHERE t.club_id = %s 
              AND m.club_id = %s
              AND m.status = 'active'
              AND EXTRACT(YEAR FROM t.created_at) = %s
            GROUP BY m.id, m.name, m.grade
            ORDER BY total_wins DESC
        """

        # 파라미터 바인딩 (정확히 3개의 변수가 매핑됩니다)
        df_ranking = pd.read_sql(query, conn, params=(club_id, club_id, year))
        conn.close()

        if df_ranking.empty:
            st.info(f"ℹ️ {year}년도에는 기록된 경기 데이터가 없습니다.")
        else:
            # 랭킹 데이터 가공
            ranking_list = []
            for i, row in df_ranking.iterrows():
                ranking_list.append({
                    "rank": i + 1,
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