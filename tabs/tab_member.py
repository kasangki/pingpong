import streamlit as st
import pandas as pd


def run_tab_member(get_db_connection):
    club_id = st.session_state.club_id
    user_role = st.session_state.user_role

    # =============================================================
    # 👑 [CASE 1] 동호회 운영진(관리자) 로그인 시 화면 구성
    # =============================================================
    if user_role == "admin":
        st.header("1. 전체 회원 등록 및 관리")
        st.subheader("➕ 새 회원 추가 등록")

        show_deleted = st.checkbox("👁️ 탈퇴(숨김) 회원도 명단에 함께 표시하기", value=False)

        with st.form("admin_add_member_form", clear_on_submit=True):
            col_n, col_g = st.columns(2)
            with col_n:
                m_name = st.text_input("회원 이름", placeholder="예: 홍길동")
            with col_g:
                m_grade = st.selectbox("부수", list(range(1, 13)), index=7, format_func=lambda x: f"{x}부")

            col_uid, col_pw = st.columns(2)
            with col_uid:
                m_username = st.text_input("👤 로그인 아이디", placeholder="예: gildong123 (영문/숫자)")
            with col_pw:
                m_password = st.text_input("🔒 초기 비밀번호", type="password", placeholder="회원이 로그인할 때 쓸 암호")

            m_phone = st.text_input("📱 연락처 (숫자만)", placeholder="예: 01012345678")
            m_role = st.selectbox("👑 회원 권한 설정", ["member", "admin"],
                                  format_func=lambda x: "🏃 일반회원" if x == "member" else "⚙️ 동호회 관리자")

            if st.form_submit_button("회원 저장", use_container_width=True):
                if m_name and m_username and m_password and m_phone:
                    try:
                        conn = get_db_connection()
                        cur = conn.cursor()
                        cur.execute("""
                            INSERT INTO members (club_id, name, grade, username, phone, password, status, role)
                            VALUES (%s, %s, %s, %s, %s, %s, 'active', %s)
                        """, (club_id, m_name.strip(), m_grade, m_username.strip(), m_phone.strip(), m_password.strip(),
                              m_role))
                        conn.commit()
                        cur.close()
                        conn.close()
                        st.success(f"🎉 [{m_name}] 선수가 성공적으로 등록되었습니다!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 등록 실패: 이미 존재하는 아이디이거나 오류가 발생했습니다. ({e})")
                else:
                    st.warning("⚠️ 모든 필드를 빠짐없이 입력해야 등록이 가능합니다.")

        st.markdown("---")
        st.subheader("📋 우리 동호회 회원 명부")

        search_keyword = st.text_input("🔍 찾으실 회원의 이름 또는 연락처를 입력하세요 (실시간 검색)", placeholder="예: 홍길동 또는 0101234")

        try:
            conn = get_db_connection()
            if show_deleted:
                query = "SELECT id, name, grade, username, phone, status, role FROM members WHERE club_id = %s ORDER BY status ASC, grade ASC, name ASC"
            else:
                query = "SELECT id, name, grade, username, phone, status, role FROM members WHERE club_id = %s AND status = 'active' ORDER BY grade ASC, name ASC"

            df_members = pd.read_sql(query, conn, params=(club_id,))
            conn.close()
        except Exception as e:
            df_members = pd.DataFrame()
            st.error(f"회원 목록을 불러오는 중 오류 발생: {e}")

        if not df_members.empty:
            if search_keyword.strip():
                k = search_keyword.strip()
                df_members = df_members[
                    df_members['name'].str.contains(k, case=False) | df_members['phone'].str.contains(k)]

            df_display = df_members.copy()
            df_display['부수'] = df_display['grade'].apply(lambda x: f"{x}부")
            df_display['상태'] = df_display['status'].apply(lambda x: "정회원" if x == "active" else "탈퇴(숨김)")
            df_display['등급'] = df_display['role'].apply(lambda x: "👑 운영진" if x == "admin" else "🏃 일반회원")

            st.info("💡 수정하거나 상세 정보를 보려면 아래 목록에서 **해당 회원의 행(Row)을 마우스로 클릭**하세요.")

            event = st.dataframe(
                df_display[['name', '부수', 'username', 'phone', '등급', '상태']],
                column_config={"name": "선수 이름", "username": "로그인 아이디", "phone": "연락처"},
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row"
            )

            selected_mem = None
            if event and "selection" in event and "rows" in event["selection"] and len(event["selection"]["rows"]) > 0:
                selected_row_idx = event["selection"]["rows"][0]
                selected_mem = df_members.iloc[selected_row_idx].to_dict()

            if selected_mem:
                st.markdown("---")
                st.markdown(f"### ⚙️ **[{selected_mem['name']}]** 선수의 상세 정보 및 편집")

                with st.form(f"edit_member_form_click_{selected_mem['id']}"):
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        edit_name = st.text_input("선수 이름 변경", value=selected_mem['name'])
                    with col_e2:
                        edit_grade = st.selectbox("부수 변경", list(range(1, 13)), index=int(selected_mem['grade']) - 1,
                                                  format_func=lambda x: f"{x}부")

                    col_e3, col_e4 = st.columns(2)
                    with col_e3:
                        edit_username = st.text_input("로그인 아이디 변경", value=selected_mem['username'])
                    with col_e4:
                        edit_phone = st.text_input("연락처 변경", value=selected_mem['phone'])

                    default_role_idx = 1 if selected_mem['role'] == "admin" else 0
                    edit_role = st.selectbox("👑 권한 등급 변경", ["member", "admin"], index=default_role_idx,
                                             format_func=lambda x: "🏃 일반회원" if x == "member" else "⚙️ 동호회 관리자")
                    edit_password = st.text_input("비밀번호 강제 재설정 (공백 시 기존 암호 유지)", type="password",
                                                  placeholder="변경할 경우에만 입력")

                    c_save, c_status_toggle = st.columns([2, 1])
                    with c_save:
                        submit_edit = st.form_submit_button("💾 회원 정보 수정사항 저장", use_container_width=True)
                    with c_status_toggle:
                        if selected_mem['status'] == 'active':
                            btn_label = "🚨 회원 탈퇴(숨김)"
                            next_status = 'deleted'
                        else:
                            btn_label = "✅ 회원 복구(재가입)"
                            next_status = 'active'
                        submit_status = st.form_submit_button(btn_label, use_container_width=True)

                    if submit_edit:
                        if edit_name and edit_username and edit_phone:
                            try:
                                conn = get_db_connection()
                                cur = conn.cursor()
                                if edit_password.strip():
                                    cur.execute("""
                                        UPDATE members SET name=%s, grade=%s, username=%s, phone=%s, password=%s, role=%s WHERE id=%s
                                    """, (edit_name.strip(), edit_grade, edit_username.strip(), edit_phone.strip(),
                                          edit_password.strip(), edit_role, selected_mem['id']))
                                else:
                                    cur.execute("""
                                        UPDATE members SET name=%s, grade=%s, username=%s, phone=%s, role=%s WHERE id=%s
                                    """, (
                                    edit_name.strip(), edit_grade, edit_username.strip(), edit_phone.strip(), edit_role,
                                    selected_mem['id']))
                                conn.commit()
                                cur.close()
                                conn.close()
                                st.success(f"📢 {edit_name} 선수의 정보가 업데이트되었습니다.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ 정보 수정 실패: 중복 아이디이거나 오류가 발생했습니다. ({e})")

                    if submit_status:
                        try:
                            conn = get_db_connection()
                            cur = conn.cursor()
                            cur.execute("UPDATE members SET status = %s WHERE id = %s",
                                        (next_status, selected_mem['id']))
                            conn.commit()
                            cur.close()
                            conn.close()
                            st.success(f"정상적으로 반영되었습니다.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"상태 처리 실패: {e}")
            else:
                st.markdown("<br>", unsafe_allow_html=True)
                st.caption("ℹ️ 명단 테이블에서 특정 회원의 행을 마우스로 클릭하시면 상세 정보 편집 창이 활성화됩니다.")

    # =============================================================
    # 🏃 [CASE 2] 일반 회원 로그인 시 화면 구성 (지저분한 문구 전면 제거)
    # =============================================================
    elif user_role == "member":
        st.header("👤 내 프로필 및 비밀번호 수정")
        st.info("💡 이름과 로그인 ID는 구장 운영 방침상 본인이 직접 변경할 수 없습니다. 오입력된 경우 구장 관리자에게 수정을 요청하세요.")

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT name, grade, username, phone FROM members WHERE id = %s", (st.session_state.user_id,))
            my_row = cur.fetchone()
            cur.close()
            conn.close()
        except:
            my_row = None

        if my_row:
            with st.form("my_info_edit_form_clean"):
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    st.text_input("내 이름 (수정 불가)", value=my_row[0], disabled=True)
                with col_m2:
                    st.text_input("내 로그인 아이디 (수정 불가)", value=my_row[2], disabled=True)

                my_grade = st.selectbox("내 현재 탁구 부수", list(range(1, 13)), index=int(my_row[1]) - 1,
                                        format_func=lambda x: f"{x}부")
                my_phone = st.text_input("내 연락처 수정", value=my_row[3])
                my_pwd = st.text_input("🔒 새 비밀번호 입력 (변경할 경우에만 입력하세요)", type="password")

                if st.form_submit_button("💾 변경된 프로필 정보 저장하기", use_container_width=True):
                    try:
                        conn = get_db_connection()
                        cur = conn.cursor()
                        if my_pwd.strip():
                            cur.execute("UPDATE members SET grade=%s, phone=%s, password=%s WHERE id=%s",
                                        (my_grade, my_phone.strip(), my_pwd.strip(), st.session_state.user_id))
                        else:
                            cur.execute("UPDATE members SET grade=%s, phone=%s WHERE id=%s",
                                        (my_grade, my_phone.strip(), st.session_state.user_id))
                        conn.commit()
                        cur.close()
                        conn.close()
                        st.success("🎉 내 정보가 안전하게 수정되었습니다!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 수정 실패: {e}")