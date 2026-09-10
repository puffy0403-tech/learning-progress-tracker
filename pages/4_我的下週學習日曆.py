from shared import *

# ---------- Supabase authentication ----------
login_required()
render_sidebar_menu()
render_account_sidebar()
render_brand_header()
render_feature_title('我的下週學習日曆', 'calendar.png', daily_encouragement())
st.page_link("app.py", label="回到首頁", icon="🏠")


try:
    plans = load_plans()
except Exception as exc:
    st.error(f"無法讀取計畫：{exc}")
    st.stop()

if plans:
    selected_id = st.selectbox("選擇已儲存計畫", [r["id"] for r in plans],
                              format_func=lambda value: next(f"#{r['id']}｜{r['week_start']} 當週" for r in plans if r["id"] == value))
    record = next(r for r in plans if r["id"] == selected_id)
    saved_start = date.fromisoformat(record["week_start"])
    render_week_calendar(record["content"], saved_start)
    with st.expander("查看原始學習計畫文字"):
        st.markdown(record["content"].split("<!-- learnpilot-v1:", 1)[0])
    with st.expander("編輯這份計畫", expanded=True):
        revision = hashlib.sha256(record["content"].encode()).hexdigest()[:12]
        render_plan_editor(record["content"], saved_start, f"saved_{selected_id}_{revision}", record)
else:
    st.info("尚未儲存計畫。可直接手動建立，或使用 AI 產生後編輯。")
st.page_link("pages/1_AI_Study_Plan.py", label="手動建立 / 產生 AI 讀書計畫", icon="🤖")
