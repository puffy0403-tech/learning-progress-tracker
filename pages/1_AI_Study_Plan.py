from shared import *

# ---------- Supabase authentication ----------
login_required()
render_sidebar_menu()
render_account_sidebar()

st.title("🤖 AI Study Plan")
st.caption("依照學習目標與本週學習紀錄，產生下一週可執行的學習計畫。")
st.page_link("app.py", label="回到首頁", icon="🏠")

goals = load_goals()
logs = load_logs()
next_week_start = week_start + timedelta(days=7)

if goals.empty:
    st.warning("請先回首頁設定至少一個學習目標。")
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

    if "generated_plan" not in st.session_state:
        st.session_state.generated_plan = ""

    if st.button("✨ 產生下週學習計畫", type="primary", use_container_width=True):
        with st.spinner("正在產生學習計畫..."):
            try:
                st.session_state.generated_plan = build_ai_plan(goals, logs)
            except Exception as exc:
                st.error(f"產生 AI 計畫時發生錯誤：{exc}")
                st.session_state.generated_plan = build_rule_based_plan(goals, logs)
                st.info("已改用規則式方法產生計畫。")

    plan = st.session_state.generated_plan
    if plan:
        st.subheader("📋 產生結果")
        st.markdown(plan)
        render_week_calendar(plan, next_week_start)

        if st.button("💾 儲存目前計畫", use_container_width=True):
            save_plan(next_week_start, plan)
            st.success("下週學習計畫已儲存，可以到『我的下週學習日曆』查看。")
