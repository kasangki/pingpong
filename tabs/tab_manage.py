import streamlit as st
import pandas as pd


def run_tab_manage(get_db_connection):
    st.header("2. 대회 관리 및 선수 선발")

    if st.session_state.user_role != "admin":
        st.warning("🔒 이 탭은 **관리자 전용** 공간입니다. 일반 회원은 대회를 관리할 수 없습니다.")
    else:
        col_t_create, col_t_p_select = st.columns([1, 1])
        with col_t_create:
            st.subheader("새로운 대회 개설")
            with st.form("tour_form", clear_on_submit=True):
                t_title = st.text_input("대회 명칭", placeholder="예: 2026년 오월 리그전")
                if st.form_submit_button("대회 생성") and t_title:
                    try:
                        conn = get_db_connection()
                        cur = conn.cursor()
                        cur.execute("INSERT INTO tournaments (title) VALUES (%s)", (t_title,))
                        conn.commit()
                        cur.close()
                        conn.close()
                        st.success(f"대회 [{t_title}]가 개설되었습니다.")
                        st.rerun()
                    except:
                        st.error("❌ 대회 생성 실패")
            try:
                conn = get_db_connection()
                df_t = pd.read_sql("SELECT id, title, created_at FROM tournaments ORDER BY id DESC", conn)
                conn.close()
                selected_rows = st.dataframe(df_t, use_container_width=True, hide_index=True, on_select="rerun",
                                             selection_mode="single-row")
                clicked_index = selected_rows.get("selection", {}).get("rows", [])
            except:
                df_t, clicked_index = pd.DataFrame(columns=["id", "title"]), []

        with col_t_p_select:
            st.subheader("대회별 출전 선수 선발")
            if df_t.empty:
                st.warning("대회를 먼저 생성해주세요.")
            else:
                tour_options = df_t.to_dict('records')
                selected_t = st.selectbox("대상 대회를 선택하세요", tour_options, index=clicked_index[0] if clicked_index else 0,
                                          format_func=lambda x: x['title'])
                try:
                    conn = get_db_connection()
                    df_all_m = pd.read_sql("SELECT id, name, grade FROM members ORDER BY name ASC", conn)
                    df_current_p = pd.read_sql(
                        f"SELECT tp.id, m.name, m.grade FROM tournament_players tp JOIN members m ON tp.member_id = m.id WHERE tp.tournament_id = {selected_t['id']} ORDER BY tp.id ASC",
                        conn)
                    conn.close()
                except:
                    df_all_m, df_current_p = pd.DataFrame(), pd.DataFrame()

                if not df_all_m.empty:
                    target_m = st.selectbox("출전시킬 회원 선택", df_all_m.to_dict('records'),
                                            format_func=lambda x: f"{x['name']} ({x['grade']}부)")
                    if st.button("🚀 대회 출전 명단에 추가"):
                        try:
                            conn = get_db_connection()
                            cur = conn.cursor()
                            cur.execute("INSERT INTO tournament_players (tournament_id, member_id) VALUES (%s, %s)",
                                        (selected_t['id'], target_m['id']))
                            conn.commit()
                            cur.close()
                            conn.close()
                            st.rerun()
                        except:
                            st.error("❌ 중복 등록이거나 저장 실패")
                st.write(f"📊 현재 출전 인원: {len(df_current_p)}명")
                st.dataframe(df_current_p, use_container_width=True, hide_index=True)