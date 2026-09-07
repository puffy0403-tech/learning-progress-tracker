from shared import *

# ---------- Login protection ----------
login_required()
render_logout_button()

st.title("🗓️ 我的下週學習日曆")
st.caption("顯示最近一次儲存的下一週學習計畫。")
st.page_link("app.py", label="回到首頁", icon="🏠")

saved_plan = load_latest_plan()
next_week_start = week_start + timedelta(days=7)

if saved_plan:
    render_week_calendar(saved_plan, next_week_start)
    with st.expander("查看原始學習計畫文字"):
        st.markdown(saved_plan)
    st.page_link("pages/1_AI_Study_Plan.py", label="重新產生 AI Study Plan", icon="🤖")
else:
    st.info("目前還沒有已儲存的下週學習計畫。請先到 AI Study Plan 產生並儲存計畫。")
    st.page_link("pages/1_AI_Study_Plan.py", label="前往 AI Study Plan", icon="🤖")
