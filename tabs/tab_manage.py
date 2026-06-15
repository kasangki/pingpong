import streamlit as st
import pandas as pd


def run_tab_manage(get_db_connection):
    # 🌟 [UI 레이아웃 패치] 타이틀 우측에 즉시 동기화 새로고침 배치
    c_title, c_ref = st.columns([5.5, 1.5])
    with c_title:
        st.header("2.🏆 신규 대회 생성 및 출전 명단 선발")
    with c_ref:
        if st.button("🔄 관리자 대시보드 갱신", use_container_width=True, type="secondary", key="manage_refresh_btn"):
            st.rerun()

    club_id = st.session_state.club_id
    user_role = st.session_state.user_role

    if user_role != "admin":
        st.warning("⚠️ 대회 생성 및 수정 권한은 '동호회 운영진(관리자)' 계정에게만 부여됩니다. 일반 회원은 관전만 가능합니다.")
        return

    # ==========================================
    # ➕ 1 구역: 신규 대회 생성 폼 (날짜 선택 추가)
    # ==========================================
    st.subheader("🆕 새로운 탁구 대회 개설")
    with st.form("create_tournament_form", clear_on_submit=True):
        t_title = st.text_input("🏆 대회 명칭 입력", placeholder="예: 2026년 6월 용호메이트 정기 랭킹전")
        t_date = st.date_input("📅 대회 개최 날짜 선택", value=pd.Timestamp.now().date())

        if st.form_submit_button("🚀 신규 대회 개설하기", use_container_width=True):
            if t_title.strip():
                try:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO tournaments (club_id, title, status, tournament_date) 
                        VALUES (%s, %s, 'setup', %s)
                    """, (club_id, t_title.strip(), t_date))
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.toast(f"🎉 [{t_title}] 대회가 생성되었습니다.")
                    st.success(f"🎉 [{t_title}] 대회가 성공적으로 개설되었습니다! 아래에서 참가 선수를 선발해 주세요.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 대회 생성 실패 (DB 오류): {e}")
            else:
                st.warning("⚠️ 대회 명칭을 입력해 주세요.")

    st.markdown("---")

    # ==========================================
    # 🏃 2 구역: 진행 중인 대회 선택 및 참가 선수 명단 빌드
    # ==========================================
    st.subheader("👥 대회별 출전 선수 명단 구성")

    try:
        conn = get_db_connection()
        query_t = "SELECT id, title, status, tournament_date FROM tournaments WHERE club_id = %s AND deleted_at IS NULL ORDER BY id DESC"
        df_tournaments = pd.read_sql(query_t, conn, params=(club_id,))
        conn.close()
    except Exception as e:
        df_tournaments = pd.DataFrame()
        st.error(f"대회 목록 로드 실패: {e}")

    if df_tournaments.empty:
        st.info("ℹ️ 현재 개설된 대회가 없습니다. 먼저 상단에서 대회를 생성해 주세요.")
        return

    tour_options = df_tournaments.to_dict('records')

    selected_tour = st.selectbox(
        "선수 명단을 구성할 대회를 고르세요",
        tour_options,
        format_func=lambda
            x: f"📅 ({x['tournament_date']}) {x['title']} [{'🎮 진행중' if x['status'] == 'playing' else '🏆 종료됨' if x['status'] == 'finished' else '⚙️ 대기중'}]"
    )

    if not selected_tour:
        return

    try:
        conn = get_db_connection()
        query_m = "SELECT id, name, grade, username FROM members WHERE club_id = %s AND status = 'active' ORDER BY grade ASC, name ASC"
        df_members = pd.read_sql(query_m, conn, params=(club_id,))

        query_p = "SELECT member_id FROM tournament_players WHERE tournament_id = %s"
        df_players = pd.read_sql(query_p, conn, params=(selected_tour['id'],))
        conn.close()
    except Exception as e:
        df_members, df_players = pd.DataFrame(), pd.DataFrame()
        st.error(f"데이터 로드 실패: {e}")

    if df_members.empty:
        st.warning("⚠️ 동호회에 등록된 정회원이 없습니다. 회원 DB 관리 탭에서 회원을 먼저 등록해 주세요.")
        return

    registered_player_ids = set(df_players['member_id'].tolist())
    search_player = st.text_input("🔍 출전시킬 선수의 이름을 검색하세요 (실시간 필터링)", placeholder="선수 이름 입력", key="search_tour_p")

    filtered_members = df_members.copy()
    if search_player.strip():
        filtered_members = filtered_members[filtered_members['name'].str.contains(search_player.strip(), case=False)]

    st.markdown(f"📊 **선택된 대회:** `{selected_tour['title']}` (현재 선발된 인원: **{len(registered_player_ids)}명**)")

    # 💡 [UX 고도화 패치] 대회 상태가 'finished'이면 명단 수정 및 선택 불가하도록 제어
    is_tournament_locked = (selected_tour['status'] == 'finished')

    if is_tournament_locked:
        st.warning("🔒 이 대회는 이미 [최종 종료] 처리되었습니다. 출전 명단을 변경할 수 없도록 읽기 전용으로 잠겼습니다.")
    else:
        st.caption("💡 오늘 경기에 참여하는 선수들을 모두 체크한 후 하단의 [💾 출전 명단 최종 저장] 버튼을 눌러주세요.")

    with st.form(f"player_selection_form_{selected_tour['id']}"):
        selected_member_ids = []
        cols = st.columns(3)

        for idx, row in filtered_members.iterrows():
            m_id = int(row['id'])
            m_name = row['name']
            m_grade = row['grade']
            m_user = row['username']
            is_checked = m_id in registered_player_ids

            with cols[idx % 3]:
                # 💡 [핵심 패치] disabled 옵션을 주어 이미 끝난 대회의 체크박스는 해제/선택을 원천 차단합니다.
                chk = st.checkbox(
                    f"{m_name} ({m_grade}부) [ID:{m_user}]",
                    value=is_checked,
                    key=f"chk_{selected_tour['id']}_{m_id}",
                    disabled=is_tournament_locked
                )
                if chk:
                    selected_member_ids.append(m_id)

        # 💡 [핵심 패치] 이미 종료된 대회인 경우 폼 서브밋 버튼도 동작을 안 하도록 격리합니다.
        if not is_tournament_locked:
            if st.form_submit_button("💾 출전 명단 최종 저장 및 동기화", use_container_width=True, type="primary"):
                try:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("DELETE FROM tournament_players WHERE tournament_id = %s", (selected_tour['id'],))
                    for mem_id in selected_member_ids:
                        cur.execute("""
                            INSERT INTO tournament_players (tournament_id, member_id) 
                            VALUES (%s, %s)
                            ON CONFLICT (tournament_id, member_id) DO NOTHING
                        """, (selected_tour['id'], mem_id))
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.toast(f"✅ {len(selected_member_ids)}명의 출전 명단이 동기화되었습니다.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 명단 저장 중 오류가 발생했습니다: {e}")
        else:
            st.form_submit_button("🔒 마감된 대회는 변경할 수 없습니다", disabled=True, use_container_width=True)

    # ==========================================
    # 💾 3 구역: 데이터 독립 및 안전 백업 센터 (한글 인코딩 완료)
    # ==========================================
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("💾 Neon 클라우드 로컬 백업 센터")
    st.caption("💡 클라우드서버(Neon)의 유실에 대비해 주기적으로 컴퓨터에 안전하게 보관하세요. (엑셀 완벽 호환)")

    with st.container(border=True):
        bc1, bc2, bc3 = st.columns(3)
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M")

        try:
            conn = get_db_connection()

            with bc1:
                df_b_mem = pd.read_sql(
                    "SELECT id, name, grade, username, phone, role, status, created_at FROM members WHERE club_id = %s",
                    conn, params=(club_id,))
                csv_mem = df_b_mem.to_csv(index=False, encoding="utf-8-sig")
                st.download_button(
                    label="📥 회원 명부 다운로드",
                    data=csv_mem,
                    file_name=f"members_backup_{timestamp}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

            with bc2:
                df_b_tour = pd.read_sql(
                    "SELECT id, title, status, tournament_date, created_at FROM tournaments WHERE club_id = %s", conn,
                    params=(club_id,))
                csv_tour = df_b_tour.to_csv(index=False, encoding="utf-8-sig")
                st.download_button(
                    label="📥 대회 목록 다운로드",
                    data=csv_tour,
                    file_name=f"tournaments_backup_{timestamp}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

            with bc3:
                query_match_hd = """
                    SELECT 
                        t.title AS "대회명",
                        t.tournament_date AS "대회개최일",
                        CASE 
                            WHEN mr.group_idx >= 900 THEN '본선 토너먼트'
                            ELSE CONCAT(mr.group_idx, '조 (예선 리그)')
                        END AS "구분(조번호)",
                        m1.name AS "선수1 이름",
                        CONCAT(m1.grade, '부') AS "선수1 부수",
                        mr.player1_score AS "선수1 세트스코어",
                        mr.player2_score AS "선수2 세트스코어",
                        m2.name AS "선수2 이름",
                        CONCAT(m2.grade, '부') AS "선수2 부수",
                        CASE 
                            WHEN mr.match_status = 'finished' THEN '🏆 경기종료'
                            WHEN mr.match_status = 'playing' THEN '🎮 진행중'
                            ELSE '⚙️ 대기중'
                        END AS "경기상태",
                        mr.updated_at AS "최종입력시간"
                    FROM match_results mr
                    JOIN tournaments t ON mr.tournament_id = t.id
                    LEFT JOIN members m1 ON mr.player1_id = m1.id
                    LEFT JOIN members m2 ON mr.player2_id = m2.id
                    WHERE t.club_id = %s AND t.deleted_at IS NULL
                    ORDER BY t.id DESC, mr.group_idx ASC, mr.id ASC
                """
                df_b_match = pd.read_sql(query_match_hd, conn, params=(club_id,))
                csv_match = df_b_match.to_csv(index=False, encoding="utf-8-sig")
                st.download_button(
                    label="📥 리그/대진표 전체 다운로드",
                    data=csv_match,
                    file_name=f"league_match_results_{timestamp}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

            conn.close()
        except Exception as e:
            st.error(f"⚠️ 백업 데이터 구성 중 오류 발생: {e}")

    # ==========================================
    # 🚨 4 구역: 위험 관리 (대회 영구 삭제)
    # ==========================================
    st.markdown("<br><br>", unsafe_allow_html=True)
    with st.expander("🚨 위험 관리 구역 (대회 영구 삭제 및 관리)"):
        st.write("선택한 대회의 모든 경기 성적, 매치 스코어 및 출전 명단 데이터가 시스템에서 숨김 처리됩니다.")
        del_confirm = st.checkbox(f"정말로 [{selected_tour['title']}] 대회를 삭제하시는 것에 동의합니까?")

        if st.button("🗑️ 선택한 대회 삭제 실행", use_container_width=True, type="secondary", disabled=not del_confirm):
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("UPDATE tournaments SET deleted_at = CURRENT_TIMESTAMP WHERE id = %s",
                            (selected_tour['id'],))
                conn.commit()
                cur.close()
                conn.close()
                st.toast(f"🚫 [{selected_tour['title']}] 대회가 안전하게 삭제되었습니다.")
                st.rerun()
            except Exception as e:
                st.error(f"대회 삭제 실패: {e}")