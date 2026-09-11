from shared import *

# ---------- Supabase authentication ----------
login_required()
render_sidebar_menu()
render_account_sidebar()
render_brand_header()
render_feature_title('我的下週學習日曆', 'calendar.png', daily_encouragement())
render_home_link()


try:
    plans = load_plans()
except Exception as exc:
    st.error(f"無法讀取計畫：{exc}")
    st.stop()

if plans:
    active = designated_plan(plans)
    if active:
        st.caption(f"目前最新讀書計畫：#{active['id']}｜{active['week_start']} 當週")
    selected_id = st.selectbox("選擇已儲存計畫", [r["id"] for r in plans],
                              format_func=lambda value: next(f"#{r['id']}｜{r['week_start']} 當週" for r in plans if r["id"] == value))
    record = next(r for r in plans if r["id"] == selected_id)

    action_col1, action_col2 = st.columns(2)
    with action_col1:
        if st.button("以這個計畫作為我的最新讀書計畫", type="primary", use_container_width=True):
            try:
                designate_latest_plan(selected_id)
                st.success("已設為我的最新讀書計畫，回首頁即可查看。")
            except Exception as exc:
                st.error(f"設定失敗：{exc}")
                st.info("若錯誤提到 selected_at 欄位，請先在 Supabase SQL Editor 執行 migration_latest_plan.sql。")

    with action_col2:
        if st.button("刪除這一週的學習日曆", use_container_width=True):
            st.session_state["confirm_delete_week_plan"] = selected_id

    if st.session_state.get("confirm_delete_week_plan") == selected_id:
        st.warning(f"確定要刪除 #{selected_id}｜{record['week_start']} 當週的學習日曆嗎？刪除後無法復原。")
        confirm_col1, confirm_col2 = st.columns(2)
        with confirm_col1:
            if st.button("確認刪除", type="primary", use_container_width=True, key=f"confirm_delete_{selected_id}"):
                try:
                    delete_plan(selected_id)
                    st.session_state.pop("confirm_delete_week_plan", None)
                    st.success("已刪除這一週的學習日曆。")
                    st.rerun()
                except Exception as exc:
                    st.error(f"刪除失敗：{exc}")
        with confirm_col2:
            if st.button("取消", use_container_width=True, key=f"cancel_delete_{selected_id}"):
                st.session_state.pop("confirm_delete_week_plan", None)
                st.rerun()
    saved_start = date.fromisoformat(record["week_start"])
    render_week_calendar(record["content"], saved_start)
    with st.expander("查看原始學習計畫文字"):
        render_ai_plan_text(record["content"].split("<!-- learnpilot-v1:", 1)[0])
    with st.expander("編輯這份計畫", expanded=True):
        revision = hashlib.sha256(record["content"].encode()).hexdigest()[:12]
        render_plan_editor(record["content"], saved_start, f"saved_{selected_id}_{revision}", record)
else:
    st.info("尚未儲存計畫。可直接手動建立，或使用 AI 產生後編輯。")
render_ai_plan_dropdown("calendar_ai_entry")
