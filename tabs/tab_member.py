import streamlit as st
import pandas as pd


def run_tab_member(get_db_connection):
    # 💡 전역 소속 동호회 ID 확보
    club_id = st.session_state.club_id

    # ==========================================
    # 👑 1. 관리자 권한의 화면 구성 (동호회별 분리)
    # ==========================================
    if st.session_state.user_role == "admin":
        st.header("1. 전체 회원 등록 및 관리")

        # 💡 탈퇴 회원 포함 여부 마스터 필터 스위치
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
                            # 💡 [멀티 패치] 회원을 추가할 때 현재 관리자의 club_id를 명확히 바인딩합니다.
                            cur.execute(
                                "INSERT INTO members (club_id, name, grade, phone, password, status) VALUES (%s, %s, %s, %s, %s, 'active')",
                                (club_id, m_name.strip(), m_grade, m_phone.strip(), m_phone.strip())
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
                            st.error("❌ 회원 저장 실패 (이 동호회에 이미 중복된 연락처가 존재하거나 DB 오류)")
                    else:
                        st.warning("이름 and 연락처를 입력해 주세요.")

        with col_list:
            st.subheader("등록된 회원 명단")
            try:
                conn = get_db_connection()
                # 💡 [멀티 패치] 다른 동호회 회원이 보이지 않도록 WHERE club_id = %s 조건을 필수로 바인딩합니다.
                if show_all:
                    query = "SELECT id, name, grade, phone, status FROM members WHERE club_id = %s ORDER BY id DESC"
                    df_m = pd.read_sql(query, conn, params=(club_id,))
                else:
                    query = "SELECT id, name, grade, phone, status FROM members WHERE club_id = %s AND status = 'active' ORDER BY id DESC"
                    df_m = pd.read_sql(query, conn, params=(club_id,))
                conn.close()

                st.markdown("⚙️ **작업할 회원의 행을 선택한 후 하단의 제어판을 이용해 주세요.**")

                # 가공하여 보여주기
                if not df_m.empty:
                    df_view = df_m[["name", "grade", "phone", "status"]].copy()
                    df_view.columns = ["이름", "부수", "연락처", "상태"]
                    # 💡 스키마 설계 구조에 맞게 'deleted' 상태 한글 직관화 처리
                    df_view["상태"] = df_view["상태"].map({"active": "🟢 활동 중", "deleted": "🔴 탈퇴/숨김"})

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
                        if "last_selected_id" not in st.session_state or st.session_state.last_selected_id != selected_player['id']:
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
                            # 💡 영구 삭제 대신 상태 토글(deleted 처리 <-> 복구하기) 방식으로 안전 운영
                            if current_status == "active":
                                if st.button("❌ 회원 탈퇴(숨김) 처리", type="primary", use_container_width=True):
                                    try:
                                        conn = get_db_connection()
                                        cur = conn.cursor()
                                        # 💡 설계된 구조인 'deleted'로 상태를 업데이트하고, 탈퇴일시 기록
                                        cur.execute("UPDATE members SET status = 'deleted', deleted_at = CURRENT_TIMESTAMP WHERE id = %s",
                                                    (int(selected_player['id']),))
                                        # 현재 진행중인 대진표 선발 명단에서 배제
                                        cur.execute("DELETE FROM tournament_players WHERE member_id = %s",
                                                    (int(selected_player['id']),))
                                        conn.commit()
                                        cur.close()
                                        conn.close()
                                        st.success(f"🗑️ {selected_player['name']} 회원이 탈퇴(숨김) 처리되었습니다. (과거 경기 전적은 그대로 보존됩니다.)")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"처리 실패: {e}")
                            else:
                                if st.button("🔄 본 회원을 다시 활동 상태로 복구", use_container_width=True):
                                    try:
                                        conn = get_db_connection()
                                        cur = conn.cursor()
                                        cur.execute("UPDATE members SET status = 'active', deleted_at = NULL WHERE id = %s",
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
                                        st.success("회원 정보 수정이 완료되었습니다.")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"수정 실패: {e}")
                    else:
                        st.info("💡 명단에서 회원을 클릭하면 제어판이 나타갑니다.")
                else:
                    st.info("현재 등록된 회원이 없습니다. 좌측 폼에서 첫 회원을 추가해 주세요.")
            except Exception as e:
                st.error(f"회원 명단 로드 중 오류 발생: {e}")

    # ==========================================
    # 🏃 2. 일반 회원 권한의 화면 구성 (셀프 정보 수정)
    # ==========================================
    else:
        st.header("👤 내 프로필 및 정보 수정")
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            # 💡 [보안 강화] 자신의 동호회 내부의 계정 정보만 확실하게 대조 및 바인딩
            cur.execute("SELECT id, name, grade, phone, password FROM members WHERE id = %s AND club_id = %s",
                        (st.session_state.user_id, club_id))
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
                                    "UPDATE members SET name = %s, password = %s WHERE id = %s AND club_id = %s",
                                    (new_name.strip(), new_pwd.strip(), my_id, club_id)
                                )
                                conn.commit()
                                cur.close()
                                conn.close()

                                st.session_state.user_name = new_name.strip()
                                st.success("✅ 회원님의 이름/비밀번호 정보가 안정적으로 업데이트 되었습니다.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"변경 실패: {e}")
                        else:
                            st.warning("이름을 공백으로 둘 수 없습니다.")
            else:
                st.error("유효하지 않은 유저 데이터이거나 세션이 만료되었습니다.")
        except Exception as e:
            st.error(f"내 정보를 불러올 수 없습니다: {e}")