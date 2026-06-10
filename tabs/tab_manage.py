import streamlit as st
import pandas as pd
import datetime


def run_tab_manage(get_db_connection):
    st.header("2. 대회 관리 및 선수 선발")

    # 💡 전역 소속 동호회 ID 확보
    club_id = st.session_state.club_id

    if st.session_state.user_role != "admin":
        st.warning("🔒 이 탭은 **관리자 전용** 공간입니다. 일반 회원은 대회를 관리할 수 없습니다.")
    else:
        # 화면을 좌우 1:1 비율로 분할
        col_t_create, col_t_p_select = st.columns([1, 1])

        # -------------------------------------------------------------
        # 🧱 좌측: 새로운 대회 개설 및 대회 선택
        # -------------------------------------------------------------
        with col_t_create:
            st.subheader("새로운 대회 개설")
            with st.form("tour_form", clear_on_submit=True):
                t_title = st.text_input("대회 명칭", placeholder="예: 2026년 오월 리그전")
                t_date = st.date_input("대회 개최 날짜", value=datetime.date.today())

                if st.form_submit_button("대회 생성"):
                    if t_title:
                        try:
                            conn = get_db_connection()
                            cur = conn.cursor()
                            # 💡 대회를 생성할 때 현재 로그인한 동호회 고유 ID(club_id)를 정확히 바인딩합니다.
                            cur.execute(
                                "INSERT INTO tournaments (club_id, title, status) VALUES (%s, %s, 'setup')",
                                (club_id, t_title.strip())
                            )
                            conn.commit()
                            cur.close()
                            conn.close()
                            st.success(f"🎉 대회 [{t_title}]가 성공적으로 개설되었습니다.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ 대회 생성 실패: {e}")
                    else:
                        st.warning("대회 명칭을 입력해 주세요.")

            st.markdown("---")
            st.subheader("개설된 대회 선택")
            try:
                conn = get_db_connection()
                # 💡 [오타 수정 완료] SQL 내부의 잘못된 파이썬 주석 구문을 완전히 걷어냈습니다.
                query = "SELECT id, title, created_at FROM tournaments WHERE club_id = %s AND deleted_at IS NULL ORDER BY id DESC"
                df_t = pd.read_sql(query, conn, params=(club_id,))
                conn.close()

                if not df_t.empty:
                    df_t_view = df_t[["created_at", "title"]].copy()
                    df_t_view.columns = ["개최 등록일시", "대회 명칭"]

                    st.markdown("👇 **선수를 선발할 대회를 아래 명단에서 클릭해 주세요.**")
                    selected_rows = st.dataframe(
                        df_t_view,
                        use_container_width=True,
                        hide_index=True,
                        on_select="rerun",
                        selection_mode="single-row",
                        key="admin_tour_dataframe"
                    )
                    clicked_index = selected_rows.get("selection", {}).get("rows", [])
                else:
                    clicked_index = []
            except Exception as e:
                df_t, clicked_index = pd.DataFrame(columns=["id", "title", "created_at"]), []

        # -------------------------------------------------------------
        # 🎯 우측: 대회별 출전 선수 선발
        # -------------------------------------------------------------
        with col_t_p_select:
            st.subheader("대회별 출전 선수 다중 선발")
            if df_t.empty:
                st.warning("대회를 먼저 생성해야 선수를 선발할 수 있습니다.")
            else:
                tour_options = df_t.to_dict('records')
                selected_t = st.selectbox(
                    "대상 대회를 선택하세요",
                    tour_options,
                    index=clicked_index[0] if clicked_index else 0,
                    format_func=lambda x: f"{x['title']}"
                )

                try:
                    conn = get_db_connection()
                    # 1. 우리 동호회 소속이면서 정상 활동 중인('active') 회원 전체 목록 로드
                    df_all_m = pd.read_sql(
                        "SELECT id, name, grade FROM members WHERE club_id = %s AND status = 'active' ORDER BY name ASC",
                        conn, params=(club_id,))

                    # 2. 이미 이 대회에 선발되어 있는 우리 동호회 선수 ID 목록 로드
                    df_current_p = pd.read_sql(
                        f"SELECT m.id, m.name, m.grade FROM tournament_players tp JOIN members m ON tp.member_id = m.id WHERE tp.tournament_id = {selected_t['id']} AND m.club_id = {club_id} ORDER BY m.name ASC",
                        conn
                    )
                    conn.close()
                except:
                    df_all_m, df_current_p = pd.DataFrame(), pd.DataFrame()

                # 이미 등록된 선수 ID를 set 형태로 추출하여 비교 속도 최적화
                already_selected_ids = set(df_current_p['id'].tolist()) if not df_current_p.empty else set()

                if not df_all_m.empty:
                    st.markdown("💡 **이번 대회에 출전할 회원들을 체크박스로 모두 선택한 후 하단의 [일괄 등록] 버튼을 눌러주세요.**")

                    selected_member_ids = []

                    with st.container(height=300, border=True):
                        for _, row in df_all_m.iterrows():
                            m_id = int(row['id'])
                            m_name = row['name']
                            m_grade = row['grade']

                            if m_id in already_selected_ids:
                                st.checkbox(f"✅ {m_name} ({m_grade}부) - [선발 완료]", value=True, disabled=True,
                                            key=f"chk_done_{m_id}")
                            else:
                                is_checked = st.checkbox(f"⬜ {m_name} ({m_grade}부)", value=False, key=f"chk_new_{m_id}")
                                if is_checked:
                                    selected_member_ids.append(m_id)

                    # 🚀 선택된 인원 일괄 저장 버튼
                    if st.button(f"🚀 선택한 {len(selected_member_ids)}명 한 번에 출전 명단에 추가", use_container_width=True,
                                 type="primary"):
                        if not selected_member_ids:
                            st.warning("선택된 회원이 없습니다. 체크박스에 체크해 주세요.")
                        else:
                            try:
                                conn = get_db_connection()
                                cur = conn.cursor()
                                insert_query = "INSERT INTO tournament_players (tournament_id, member_id) VALUES (%s, %s)"
                                for target_id in selected_member_ids:
                                    cur.execute(insert_query, (selected_t['id'], target_id))
                                conn.commit()
                                cur.close()
                                conn.close()
                                st.success(f"🎉 성공적으로 {len(selected_member_ids)}명의 선수를 일괄 추가했습니다!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ 등록 중 오류가 발생했습니다: {e}")

                st.markdown("---")
                st.markdown(f"📊 **현재 대회 출전 확정 인원:** 총 `{len(df_current_p)}`명")

                if not df_current_p.empty:
                    df_p_view = df_current_p[["name", "grade"]].copy()
                    df_p_view.columns = ["선수명", "신청 부수"]
                    st.dataframe(df_p_view, use_container_width=True, hide_index=True)
                else:
                    st.info("아직 이 대회에 선발된 선수가 없습니다.")