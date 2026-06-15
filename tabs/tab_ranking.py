import streamlit as st
import pandas as pd


def render_ranking_table(ranking_data):
    """럭셔리 랭킹 테이블 렌더링 함수 (초고가시성 및 가독성 업그레이드 버전)"""
    html_table = "<style>"
    # 🎨 전체 컨테이너 배경 및 테두리 밝기 조정
    html_table += ".ranking-container { width: 100%; margin: 20px 0; background: #131A2C; border-radius: 16px; box-shadow: 0 4px 25px rgba(0,0,0,0.4); border: 1px solid #475569; overflow: hidden; }"
    html_table += ".ranking-table { width: 100%; border-collapse: collapse; text-align: center; font-family: 'Pretendard', sans-serif; }"

    # TableHeader: 기존보다 훨씬 밝고 선명한 테두리와 백색 텍스트 배치
    html_table += ".ranking-table thead { background: #1E293B; border-bottom: 3px solid #475569; }"
    html_table += ".ranking-table th { padding: 18px 16px; color: #FFFFFF; font-weight: 800; font-size: 1.05rem; letter-spacing: 0.05em; }"

    # TableBody: 데이터 가독성을 위해 테두리 구분선(border-bottom) 밝기 강화
    html_table += ".ranking-table td { padding: 18px 16px; border-bottom: 1px solid #334155; color: #F8FAFC; font-size: 1.05rem; }"
    html_table += ".ranking-table tbody tr { border-bottom: 1px solid #475569; }"
    html_table += ".ranking-table tbody tr:hover { background-color: #243249; transition: 0.2s; }"

    # 🏅 메달 배지 가시성 초고도화
    html_table += ".rank-num { font-weight: 800; font-size: 1.15rem; color: #CBD5E1; }"
    html_table += ".gold { color: #FBBF24; background: #78350F; padding: 6px 14px; border-radius: 20px; font-weight: 900; font-size: 1.1rem; border: 1px solid #F59E0B; }"
    html_table += ".silver { color: #F1F5F9; background: #334155; padding: 6px 14px; border-radius: 20px; font-weight: 900; font-size: 1.1rem; border: 1px solid #64748B; }"
    html_table += ".bronze { color: #FF9D43; background: #451A03; padding: 6px 14px; border-radius: 20px; font-weight: 900; font-size: 1.1rem; border: 1px solid #D97706; }"

    # 이름 및 승수 하이라이트 텍스트 밸런스
    html_table += ".name-cell { font-weight: 800; font-size: 1.15rem; color: #FFFFFF; }"
    html_table += ".wins-cell { color: #6366F1; font-weight: 900; font-size: 1.25rem; text-shadow: 0 0 10px rgba(99, 102, 241, 0.2); }"
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

        html_table += f"<tr><td><span class='{rank_cls}'>{rank_txt}</span></td><td class='name-cell'>{row['name']}</td><td style='color:#C8D2E6; font-weight: 600;'>{row['grade']}부</td><td class='wins-cell'>{row['total_wins']}승</td></tr>"

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

        # [SaaS 알고리즘 고도화 패치]
        # 본선 토너먼트 매치(group_idx >= 900) 승리자에겐 1.2 가중치를 곱해 정렬 스코어를 산출합니다.
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