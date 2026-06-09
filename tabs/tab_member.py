import streamlit as st
import pandas as pd


def run_tab_member(get_db_connection):
    # ==========================================
    # 👑 1. 관리자 권한의 화면 구성
    # ==========================================
    if st.session_state.user_role == "admin":
        st.header("1. 전체 회원 등록 및 관리")

        # 💡 [추가] 탈퇴 회원 포함 여부 마스터 필터 스위치
        show_all = st.checkbox("👁️ 탈퇴(숨김) 회원도 명단에 함께 표시하기", value=False)

        col_in, col_list = st.columns([1, 2])

        with col_in:
            st.subheader("새 회원 추가 등록")
            with st.form("member_form_tab", clear_on_submit=True):
                m_name = st.text_input("회원 이름")
                m_grade = st.selectbox("부수", list(range(1, 12)), index=7, format_func=lambda x: f"{x}부")
                m_phone = st.text_input("연락처 (로그인 ID / 초기비밀번호)")

                if st.form_submit_button("회원 저장"):
                    if m_name and m_phone:
                        save_success = False
                        try:
                            conn = get_db_connection()
                            cur = conn.cursor()
                            cur.execute(
                                "INSERT INTO members (name, grade, phone, password, status) VALUES (%s, %s, %s, %s, 'active')",
                                (m_name.strip(), m_grade, m_phone.strip(), m_phone.strip())
                            )
                            conn.commit()
                            cur.close()
                            conn.close()
                            save_success = True
                        except Exception as e:
                            save_success = False

                        if save_success:
                            st.success(f"🎉 회원 '{m_name}' 등록 완료")
                            st.rerun()
                        else:
                            st.error("❌ 회원 저장 실패 (중복된 연락처이거나 DB 오류)")
                    else:
                        st.warning("이름과 연락처를 입력해 주세요.")

        with col_list:
            st.subheader("등록된 회원 명단")
            try:
                conn = get_db_connection()
                # 💡 [변경] 필터 조건에 따라 SQL 문 동적 제어
                if show_all:
                    query = "SELECT id, name, grade, phone, status FROM members ORDER BY id DESC"
                else:
                    query = "SELECT id, name, grade, phone, status FROM members WHERE status = 'active' ORDER BY id DESC"

                df_m = pd.read_sql(query, conn)
                conn.close()

                st.markdown("⚙️ **작업할 회원의 행을 선택한 후 하단의 제어판을 이용해 주세요.**")

                # 가공하여 보여주기
                df_view = df_m[["name", "grade", "phone", "status"]].copy()
                df_view.columns = ["이름", "부수", "연락처", "상태"]
                # 상태 텍스트 한글 매핑 직관화
                df_view["상태"] = df_view["상태"].map({"active": "🟢 활동 중", "leave": "🔴 탈퇴/숨김"})

                selected_rows = st.dataframe(
                    df_view,
                    use_container_width=True,
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row",
                    key="admin_member_dataframe"
                )

                clicked_index = selected_rows.get("selection", {}).get("rows", [])

                if clicked_index:
                    selected_player = df_m.iloc[clicked_index[0]]
                    current_status = selected_player['status']

                    if "edit_mode" not in st.session_state: st.session_state.edit_mode = False
                    if "last_selected_id" not in st.session_state or st.session_state.last_selected_id != \
                            selected_player['id']:
                        st.session_state.last_selected_id = selected_player['id']
                        st.session_state.edit_mode = False

                    st.markdown("---")
                    st.markdown(
                        f"👤 선택된 회원: **{selected_player['name']}** ({selected_player['grade']}부 / {'활동 중' if current_status == 'active' else '탈퇴 상태'})")

                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        if st.button("✏️ 회원 정보 수정", use_container_width=True):
                            st.session_state.edit_mode = not st.session_state.edit_mode
                            st.rerun()
                    with btn_col2:
                        # 💡 [변경] 영구 삭제 대신 상태 토글(탈퇴처리 <-> 복구하기) 방식으로 안전 전환
                        if current_status == "active":
                            if st.button("❌ 회원 탈퇴(숨김) 처리", type="primary", use_container_width=True):
                                try:
                                    conn = get_db_connection()
                                    cur = conn.cursor()
                                    # 상태를 leave로 업데이트하고, 현재 열려있는 대회 명단 배제
                                    cur.execute("UPDATE members SET status = 'leave' WHERE id = %s",
                                                (int(selected_player['id']),))
                                    cur.execute("DELETE FROM tournament_players WHERE member_id = %s",
                                                (int(selected_player['id']),))
                                    conn.commit()
                                    cur.close()
                                    conn.close()
                                    st.success(f"🗑️ {selected_player['name']} 회원이 탈퇴(숨김) 처리되었습니다. (기존 경기 기록은 유지됨)")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"처리 실패: {e}")
                        else:
                            if st.button("🔄 본 회원을 다시 활동 상태로 복구", use_container_width=True):
                                try:
                                    conn = get_db_connection()
                                    cur = conn.cursor()
                                    cur.execute("UPDATE members SET status = 'active' WHERE id = %s",
                                                (int(selected_player['id']),))
                                    conn.commit()
                                    cur.close()
                                    conn.close()
                                    st.success(f"✨ {selected_player['name']} 회원이 다시 정상 활동 상태로 복구되었습니다.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"복구 실패: {e}")

                    if st.session_state.edit_mode:
                        with st.form("admin_edit_form"):
                            edit_name = st.text_input("수정할 이름", value=str(selected_player['name']))
                            edit_grade = st.selectbox("수정할 부수", list(range(1, 12)),
                                                      index=list(range(1, 12)).index(int(selected_player['grade'])))
                            edit_phone = st.text_input("수정할 연락처", value=str(selected_player['phone']))

                            if st.form_submit_button("✨ 변경 사항 저장하기", use_container_width=True):
                                try:
                                    conn = get_db_connection()
                                    cur = conn.cursor()
                                    cur.execute("UPDATE members SET name=%s, grade=%s, phone=%s WHERE id=%s", (
                                    edit_name.strip(), edit_grade, edit_phone.strip(), int(selected_player['id'])))
                                    conn.commit()
                                    cur.close()
                                    conn.close()
                                    st.session_state.edit_mode = False
                                    st.success("정보 수정이 완료되었습니다.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"수정 실패: {e}")
                else:
                    st.info("💡 명단에서 회원을 클릭하면 제어판이 나타납니다.")
            except Exception as e:
                st.info("회원 명단 로드 중 오류 발생")

    # ==========================================
    # 🏃 2. 일반 회원 권한의 화면 구성 (셀프 정보 수정)
    # ==========================================
    else:
        st.header("👤 내 프로필 및 정보 수정")
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT id, name, grade, phone, password FROM members WHERE id = %s",
                        (st.session_state.user_id,))
            my_data = cur.fetchone()
            cur.close()
            conn.close()

            if my_data:
                my_id, my_name, my_grade, my_phone, my_password = my_data
                st.write("✨ 회원님은 본인의 이름과 비밀번호를 스스로 변경할 수 있습니다.")

                with st.form("my_info_edit_form"):
                    st.markdown(
                        f"**📱 로그인 계정(연락처):** `{my_phone}`  /  **🏓 현재 등록 부수:** `{my_grade}부` *(부수 변경은 관리자에게 요청하세요)*")
                    new_name = st.text_input("📝 내 이름 (잘못 입력한 경우 수정 가능)", value=str(my_name))
                    new_pwd = st.text_input("🔒 변경할 비밀번호", value=str(my_password), type="password")

                    if st.form_submit_button("💾 내 정보 안전하게 변경하기", use_container_width=True):
                        if new_name.strip():
                            try:
                                conn = get_db_connection()
                                cur = conn.cursor()
                                cur.execute(
                                    "UPDATE members SET name = %s, password = %s WHERE id = %s",
                                    (new_name.strip(), new_pwd.strip(), my_id)
                                )
                                conn.commit()
                                cur.close()
                                conn.close()

                                st.session_state.user_name = new_name.strip()
                                st.success("✅ 회원님의 이름/비밀번호 정보가 업데이트 되었습니다.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"변경 실패: {e}")
                        else:
                            st.warning("이름을 공백으로 둘 수 없습니다.")
        except Exception as e:
            st.error("내 정보를 불러올 수 없습니다.")