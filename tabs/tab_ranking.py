import streamlit as st
import pandas as pd


def render_ranking_table(ranking_data):
    """럭셔리 랭킹 테이블 렌더링 함수"""
    html_table = "<style>"
    html_table += ".ranking-container { width: 100%; margin: 20px 0; background: #ffffff; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.06); border: 1px solid #E2E8F0; overflow: hidden; }"
    html_table += ".ranking-table { width: 100%; border-collapse: collapse; text-align: center; font-family: 'Pretendard', sans-serif; }"
    html_table += ".ranking-table thead { background: #F8FAFC; border-bottom: 2px solid #E2E8F0; }"
    html_table += ".ranking-table th { padding: 16px; color: #64748B; font-weight: 600; font-size: 0.9rem; letter-spacing: 0.05em; }"
    html_table += ".ranking-table td { padding: 16px; border-bottom: 1px solid #F1F5F9; color: #1E293B; }"
    html_table += ".ranking-table tbody tr:hover { background-color: #F1F5F9; transition: 0.2s; }"
    html_table += ".rank-num { font-weight: 800; font-size: 1.1rem; }"
    html_table += ".gold { color: #D97706; background: #FEF3C7; padding: 4px 12px; border-radius: 20px; }"
    html_table += ".silver { color: #475569; background: #E2E8F0; padding: 4px 12px; border-radius: 20px; }"
    html_table += ".bronze { color: #9A3412; background: #FFEDD5; padding: 4px 12px; border-radius: 20px; }"
    html_table += ".name-cell { font-weight: 700; font-size: 1.05rem; }"
    html_table += ".wins-cell { color: #4F46E5; font-weight: 800; font-size: 1.1rem; }"
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

        html_table += f"<tr><td><span class='{rank_cls}'>{rank_txt}</span></td><td class='name-cell'>{row['name']}</td><td style='color:#64748B;'>{row['grade']}부</td><td class='wins-cell'>{row['total_wins']}승</td></tr>"

    html_table += "</tbody></table></div>"
    return html_table


def run_tab_ranking(get_db_connection):
    st.header("📊 연도별 통합 랭킹")

    # 1. 연도 선택 사이드바
    current_year = pd.Timestamp.now().year
    year = st.selectbox("조회할 연도를 선택하세요", list(range(current_year, current_year - 5, -1)))

    try:
        conn = get_db_connection()
        # 대회 결과에서 연도별 승리 기록 합산 쿼리
        query = f"""
            SELECT m.name, m.grade, COUNT(*) as total_wins
            FROM match_results mr
            JOIN tournaments t ON mr.tournament_id = t.id
            JOIN members m ON (
                (mr.player1_id = m.id AND mr.score_text LIKE '3:%') OR 
                (mr.player2_id = m.id AND mr.score_text LIKE '%:3')
            )
            WHERE EXTRACT(YEAR FROM t.created_at) = {year}
            GROUP BY m.id, m.name, m.grade
            ORDER BY total_wins DESC
        """
        df_ranking = pd.read_sql(query, conn)
        conn.close()

        if df_ranking.empty:
            st.info(f"{year}년도에는 기록된 경기 데이터가 없습니다.")
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

            # 고급 디자인 테이블 출력
            st.markdown(render_ranking_table(ranking_list), unsafe_allow_html=True)

            # 통계 그래프 (선택사항)
            st.subheader("📈 승리 횟수 분포")
            st.bar_chart(df_ranking.set_index('name')['total_wins'])

    except Exception as e:
        st.error(f"랭킹 데이터를 불러오는 중 오류가 발생했습니다: {e}")