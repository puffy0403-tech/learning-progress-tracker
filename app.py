from shared import *

# ---------- Supabase login / registration ----------
if not render_auth():
    st.stop()
render_sidebar_menu()
render_account_sidebar()
render_brand_header("一起紀錄及制定讀書計畫吧!!!")

goals = load_goals()
logs = load_logs()
week_logs = current_week_logs(logs)

with st.sidebar:
    st.header(" 學習設定")

    with st.expander(" 設定學習目標", expanded=True):
        goal_subject = st.text_input("科目 / 學習主題", placeholder="例如：英文")
        weekly_hours = st.number_input("每週目標時數", min_value=0.5, max_value=100.0, value=7.0, step=0.5)
        target_score = st.number_input("目標分數（選填）", min_value=0.0, max_value=100.0, value=80.0, step=1.0)
        target_date = st.date_input("目標日期", value=today + timedelta(days=30))

        if st.button("儲存目標", use_container_width=True):
            if goal_subject.strip():
                add_goal(goal_subject.strip(), weekly_hours, target_score, target_date)
                st.success("目標已儲存")
                st.rerun()
            else:
                st.warning("請輸入學習主題")

    with st.expander(" 記錄今日學習", expanded=True):
        existing_subjects = goals["subject"].drop_duplicates().tolist() if not goals.empty else []
        log_subject = st.selectbox("學習科目", options=existing_subjects + ["其他"])
        custom_subject = ""
        if log_subject == "其他":
            custom_subject = st.text_input("其他科目名稱")

        study_date = st.date_input("日期", value=today, key="study_date")
        minutes = st.number_input("學習時間（分鐘）", min_value=1, max_value=1440, value=60, step=10)
        note = st.text_area("學習內容", placeholder="例如：閱讀論文第二章、完成 Python 練習")

        if st.button("新增學習紀錄", use_container_width=True):
            subject_to_save = custom_subject.strip() if log_subject == "其他" else log_subject
            if subject_to_save:
                add_log(study_date, subject_to_save, minutes, note)
                st.success("學習紀錄已新增")
                st.rerun()
            else:
                st.warning("請輸入科目名稱")

latest_goals = goals.drop_duplicates("subject", keep="first") if not goals.empty else goals
weekly_goal_hours = float(latest_goals["weekly_hours"].sum()) if not latest_goals.empty else 0.0
weekly_study_hours = float(week_logs["minutes"].sum() / 60) if not week_logs.empty else 0.0
goal_rate = (weekly_study_hours / weekly_goal_hours * 100) if weekly_goal_hours > 0 else 0.0

today_minutes = 0
if not logs.empty:
    tmp = logs.copy()
    tmp["study_date"] = pd.to_datetime(tmp["study_date"]).dt.date
    today_minutes = int(tmp.loc[tmp["study_date"] == today, "minutes"].sum())

c1, c2, c3, c4 = st.columns(4)
c1.metric("今日學習", f"{today_minutes / 60:.1f} 小時")
c2.metric("本週累積", f"{weekly_study_hours:.1f} 小時")
c3.metric("本週目標", f"{weekly_goal_hours:.1f} 小時")
c4.metric("目標達成率", f"{goal_rate:.0f}%")
st.progress(min(goal_rate / 100, 1.0))
st.caption(f"本週：{week_start} ～ {week_end}")

left, right = st.columns([1.25, 1])
with left:
    st.subheader(" 每日學習時間")
    if week_logs.empty:
        st.info("目前還沒有本週學習紀錄。")
    else:
        daily = week_logs.groupby("study_date", as_index=False)["minutes"].sum().sort_values("study_date")
        daily["hours"] = daily["minutes"] / 60
        fig = px.bar(daily, x="study_date", y="hours", labels={"study_date": "日期", "hours": "學習時數"}, text_auto=".1f")
        fig.update_layout(margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader(" 各科目進度")
    if week_logs.empty:
        st.info("新增紀錄後會顯示各科目學習比例。")
    else:
        by_subject = week_logs.groupby("subject", as_index=False)["minutes"].sum()
        by_subject["hours"] = by_subject["minutes"] / 60
        fig2 = px.pie(by_subject, values="hours", names="subject", hole=0.45)
        fig2.update_layout(margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig2, use_container_width=True)

st.divider()


render_home_plan()
