from shared import *

# ---------- Supabase authentication ----------
login_required()
render_sidebar_menu()
render_account_sidebar()
render_brand_header()
render_feature_title('AI Study Plan', 'ai_plan.png', daily_encouragement())
st.page_link("app.py", label="回到首頁", icon="🏠")

st.subheader("手動建立讀書計畫")
manual_version_key = "plan_draft_manual_version_" + current_user_id()
if st.button("開始另一份手動計畫"):
    st.session_state[manual_version_key] = st.session_state.get(manual_version_key, 0) + 1
with st.expander("自行安排日期、科目、內容與時間", expanded=True):
    render_plan_editor("", date.today() - timedelta(days=date.today().weekday()) + timedelta(days=7), "manual_" + str(st.session_state.get(manual_version_key, 0)))
st.page_link("pages/4_我的下週學習日曆.py", label="查看 / 編輯已儲存計畫", icon="📅")

goals = load_goals()
logs = load_logs()
next_week_start = week_start + timedelta(days=7)

if goals.empty:
    st.warning("若要使用 AI，請先回首頁設定至少一個學習目標；上方手動計畫可直接使用。")
else:
    latest_goals = goals.drop_duplicates("subject", keep="first")
    st.subheader("目前學習目標")
    st.dataframe(
        latest_goals[["subject", "weekly_hours", "target_score", "target_date"]].rename(columns={
            "subject": "科目",
            "weekly_hours": "每週目標時數",
            "target_score": "目標分數",
            "target_date": "目標日期",
        }),
        use_container_width=True,
        hide_index=True,
    )

    api_ready = gemini_api_ready()
    if api_ready:
        st.success("已偵測到 Gemini API，將使用 AI 產生計畫。")
    else:
        st.info("目前未偵測到 Gemini API，會先使用規則式方法產生計畫；之後設定 GEMINI_API_KEY 即可使用 Gemini。")

    draft_key = "plan_draft_" + current_user_id()
    if draft_key not in st.session_state:
        st.session_state[draft_key] = ""

    if st.button(" 產生下週學習計畫", type="primary", use_container_width=True):
        st.session_state[draft_key+"_version"] = st.session_state.get(draft_key+"_version", 0) + 1
        st.session_state[draft_key+"_start"] = next_week_start
        with st.spinner("正在產生學習計畫..."):
            try:
                st.session_state[draft_key] = build_ai_plan(goals, logs)
            except Exception as exc:
                st.error(f"產生 AI 計畫時發生錯誤：{exc}")
                st.session_state[draft_key] = build_rule_based_plan(goals, logs)
                st.info("已改用規則式方法產生計畫。")

    plan = st.session_state[draft_key]
    if plan:
        st.subheader(" 產生結果")
        st.markdown(plan)
        render_week_calendar(plan, st.session_state.get(draft_key+"_start", next_week_start))

        st.subheader("編輯後儲存")
        render_plan_editor(plan, st.session_state.get(draft_key+"_start", next_week_start),
                           "ai_" + str(st.session_state.get(draft_key+"_version", 0)))
