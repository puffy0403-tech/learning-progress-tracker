from shared import *

# ---------- Supabase authentication ----------
login_required()
render_sidebar_menu()
render_account_sidebar()
render_brand_header()
render_feature_title('學習紀錄管理', 'study_record.png', daily_encouragement())
st.page_link("app.py", label="回到首頁", icon="🏠")

section = st.session_state.get("plan_draft_records_section_" + current_user_id(), "全部學習紀錄+編輯紀錄")
if section in ("設定學習目標", "紀錄今日學習"):
    st.subheader(section)
    render_learning_settings(load_goals(), "records", section=section, sidebar=False)
else:
    logs = load_logs()
    
    if logs.empty:
        st.info("目前還沒有學習紀錄。可在左側「學習紀錄管理 → 紀錄今日學習」直接新增。")
    else:
        display_df = logs.copy()
        display_df["study_date"] = pd.to_datetime(display_df["study_date"]).dt.date
        st.subheader(" 全部學習紀錄")
        st.dataframe(
            display_df[["id", "study_date", "subject", "minutes", "note"]].rename(columns={
                "id": "ID",
                "study_date": "日期",
                "subject": "科目",
                "minutes": "分鐘",
                "note": "學習內容",
            }),
            use_container_width=True,
            hide_index=True,
        )
    
        options = {}
        for _, row in display_df.iterrows():
            label = f"#{int(row['id'])}｜{row['study_date']}｜{row['subject']}｜{int(row['minutes'])} 分鐘"
            options[label] = int(row["id"])
    
        selected_label = st.selectbox("選擇要編輯的紀錄", list(options.keys()))
        selected_id = options[selected_label]
        selected = display_df.loc[display_df["id"] == selected_id].iloc[0]
    
        st.subheader(" 編輯紀錄")
        with st.form("edit_log_form"):
            edit_date = st.date_input("日期", value=selected["study_date"])
            edit_subject = st.text_input("科目", value=str(selected["subject"]))
            edit_minutes = st.number_input("學習時間（分鐘）", min_value=1, max_value=1440, value=int(selected["minutes"]), step=10)
            edit_note = st.text_area("學習內容", value="" if pd.isna(selected["note"]) else str(selected["note"]))
            submitted = st.form_submit_button(" 儲存修改", use_container_width=True)
    
        if submitted:
            if edit_subject.strip():
                update_log(selected_id, edit_date, edit_subject.strip(), edit_minutes, edit_note)
                st.success("學習紀錄已更新。")
                st.rerun()
            else:
                st.warning("科目不能留白。")
    
        with st.expander(" 刪除這筆紀錄"):
            confirm = st.checkbox("我確認要永久刪除這筆紀錄", key=f"confirm_delete_{selected_id}")
            if st.button("永久刪除", type="secondary", disabled=not confirm, use_container_width=True):
                delete_log(selected_id)
                st.success("學習紀錄已刪除。")
                st.rerun()
