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
                st.caption("🔒 회원 등록 및 관리는 관리자 계정에서만 가능합니다.")

            # 👑 관리자 화면: 선택하여 수정/삭제할 수 있는 제어판 작동
            else:
                st.markdown("⚙️ **작업할 회원의 행을 선택한 후 하단의 제어판을 이용해 주세요.**")
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

                    # 수정을 위한 토글 상태 관리 (세션)
                    if "edit_mode" not in st.session_state:
                        st.session_state.edit_mode = False
                    if "last_selected_id" not in st.session_state or st.session_state.last_selected_id != \
                            selected_player['id']:
                        st.session_state.last_selected_id = selected_player['id']
                        st.session_state.edit_mode = False  # 다른 회원을 누르면 수정 모드 초기화

                    st.markdown("---")
                    st.markdown(f"👤 선택된 회원: **{selected_player['name']}** ({selected_player['grade']}부)")

                    # 버튼 레이아웃 분할 (수정 버튼 / 삭제 버튼)
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        if st.button("✏️ 회원 정보 수정", use_container_width=True):
                            st.session_state.edit_mode = not st.session_state.edit_mode
                            st.rerun()

                    with btn_col2:
                        if st.button("❌ 회원 영구 삭제", type="primary", use_container_width=True):
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
                                st.session_state.edit_mode = False

                                st.success(f"🗑️ {selected_player['name']} 회원이 안전하게 삭제되었습니다.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ 회원 삭제 중 오류 발생: {e}")

                    # ✏️ 정보 수정 입력 폼 열기 (수정 버튼 활성화 시 노출)
                    if st.session_state.edit_mode:
                        st.markdown("### 📝 회원 정보 수정하기")
                        with st.form("edit_member_form", clear_on_submit=False):
                            edit_name = st.text_input("수정할 이름", value=str(selected_player['name']))

                            # 기존 부수 데이터 가공 및 인덱스 매칭
                            try:
                                current_grade = int(selected_player['grade'])
                                grade_index = list(range(1, 12)).index(current_grade)
                            except:
                                grade_index = 7

                            edit_grade = st.selectbox("수정할 부수", list(range(1, 12)), index=grade_index,
                                                      format_func=lambda x: f"{x}부")
                            edit_phone = st.text_input("수정할 연락처 (로그인 ID)", value=str(selected_player['phone']))

                            if st.form_submit_button("✨ 변경 사항 저장하기", use_container_width=True):
                                if edit_name and edit_phone:
                                    try:
                                        conn = get_db_connection()
                                        cur = conn.cursor()
                                        cur.execute(
                                            "UPDATE members SET name = %s, grade = %s, phone = %s WHERE id = %s",
                                            (edit_name.strip(), edit_grade, edit_phone.strip(),
                                             int(selected_player['id']))
                                        )
                                        conn.commit()
                                        cur.close()
                                        conn.close()

                                        # 성공 후 세션 청소 및 화면 새로고침
                                        st.session_state.edit_mode = False
                                        if "member_delete_dataframe" in st.session_state:
                                            del st.session_state["member_delete_dataframe"]

                                        st.success(f"✅ {edit_name} 회원의 정보가 성공적으로 변경되었습니다!")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ 수정 실패 (중복된 연락처이거나 오류 발생): {e}")
                                else:
                                    st.warning("모든 필드를 채워주세요.")
                else:
                    st.info("💡 명단에서 회원을 클릭하면 제어 버튼들이 나타납니다.")
        except Exception as e:
            st.info(f"등록된 회원 목록이 없습니다. ({e})")