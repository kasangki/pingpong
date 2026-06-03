import streamlit as st
import pandas as pd


def run_tab_member(get_db_connection):
    st.header("1. 전체 회원 등록 및 관리")

    # 관리자인 경우에만 좌우 분할 레이아웃 적용 (등록 폼 노출)
    if st.session_state.user_role == "admin":
        col_in, col_list = st.columns([1, 2])

        with col_in:
            st.subheader("새 회원 추가 등록")
            with st.form("member_form_tab", clear_on_submit=True):
                m_name = st.text_input("회원 이름")
                m_grade = st.selectbox("부수", list(range(1, 12)), index=7, format_func=lambda x: f"{x}부")
                m_phone = st.text_input("연락처 (로그인 ID가 됨)")
                if st.form_submit_button("회원 저장") and m_name:
                    try:
                        conn = get_db_connection()
                        cur = conn.cursor()
                        cur.execute("INSERT INTO members (name, grade, phone) VALUES (%s, %s, %s)",
                                    (m_name, m_grade, m_phone.strip()))
                        conn.commit()
                        cur.close()
                        conn.close()
                        st.success(f"회원 '{m_name}' 등록 완료")
                        st.rerun()
                    except:
                        st.error("❌ 회원 저장 실패")
    else:
        # 일반 회원인 경우 폼 없이 명단만 가로로 넓게 노출
        col_list = st.container()

    with col_list:
        st.subheader("등록된 회원 명단")
        try:
            conn = get_db_connection()
            df_m = pd.read_sql("SELECT id, name, grade, phone FROM members ORDER BY id DESC", conn)
            conn.close()

            # 일반 회원 화면: 데이터 프레임만 깔끔하게 조회
            if st.session_state.user_role != "admin":
                st.dataframe(df_m, use_container_width=True, hide_index=True)
                st.caption("🔒 회원 등록 및 삭제는 관리자 계정에서만 가능합니다.")

            # 관리자 화면: 선택하여 영구 삭제할 수 있는 인터랙티브 테이블 가동
            else:
                st.markdown("🗑️ **삭제할 회원의 행을 선택한 후 하단의 삭제 버튼을 눌러주세요.**")
                selected_rows = st.dataframe(
                    df_m,
                    use_container_width=True,
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row",
                    key="member_delete_dataframe"
                )

                clicked_index = selected_rows.get("selection", {}).get("rows", [])

                if clicked_index:
                    selected_player = df_m.iloc[clicked_index[0]]
                    st.warning(f"⚠️ **주의: [{selected_player['name']}] 회원을 삭제하시겠습니까?**")

                    if st.button(f"❌ {selected_player['name']} 회원 영구 삭제", type="primary", use_container_width=True):
                        try:
                            conn = get_db_connection()
                            cur = conn.cursor()
                            cur.execute("DELETE FROM tournament_players WHERE member_id = %s",
                                        (int(selected_player['id']),))
                            cur.execute("DELETE FROM members WHERE id = %s", (int(selected_player['id']),))
                            conn.commit()
                            cur.close()
                            conn.close()

                            if "member_delete_dataframe" in st.session_state:
                                del st.session_state["member_delete_dataframe"]

                            st.success(f"🗑️ {selected_player['name']} 회원이 안전하게 삭제되었습니다.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ 회원 삭제 중 오류 발생: {e}")
                else:
                    st.info("💡 명단에서 회원을 클릭하면 삭제 버튼이 나타납니다.")
        except:
            st.info("등록된 회원 목록이 없습니다.")