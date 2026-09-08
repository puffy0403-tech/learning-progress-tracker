from shared import *

# ---------- Supabase authentication ----------
login_required()
render_sidebar_menu()
render_account_sidebar()

render_brand_header()

st.title(" 本週目標進度")
st.caption(f"本週：{week_start} ～ {week_end}")
st.page_link("app.py", label="回到首頁", icon="🏠")

goals = load_goals()
logs = load_logs()
week_logs = current_week_logs(logs)
latest_goals = goals.drop_duplicates("subject", keep="first") if not goals.empty else goals

weekly_goal_hours = float(latest_goals["weekly_hours"].sum()) if not latest_goals.empty else 0.0
weekly_study_hours = float(week_logs["minutes"].sum() / 60) if not week_logs.empty else 0.0
goal_rate = (weekly_study_hours / weekly_goal_hours * 100) if weekly_goal_hours > 0 else 0.0
remaining_total = max(weekly_goal_hours - weekly_study_hours, 0)

c1, c2, c3, c4 = st.columns(4)
c1.metric("本週累積", f"{weekly_study_hours:.1f} 小時")
c2.metric("本週目標", f"{weekly_goal_hours:.1f} 小時")
c3.metric("目標達成率", f"{goal_rate:.0f}%")
c4.metric("剩餘時數", f"{remaining_total:.1f} 小時")
st.progress(min(goal_rate / 100, 1.0))

st.subheader(" 各科目目標進度")
if latest_goals.empty:
    st.info("目前尚未設定學習目標，請回首頁新增學習目標。")
else:
    studied_map = week_logs.groupby("subject")["minutes"].sum().div(60).to_dict() if not week_logs.empty else {}
    rows = []
    for _, row in latest_goals.iterrows():
        subject = row["subject"]
        target = float(row["weekly_hours"])
        actual = float(studied_map.get(subject, 0))
        rows.append({
            "科目": subject,
            "已完成（hr）": round(actual, 1),
            "目標（hr）": round(target, 1),
            "達成率（%）": round((actual / target * 100), 0) if target else 0,
            "剩餘（hr）": round(max(target - actual, 0), 1),
        })

    progress_df = pd.DataFrame(rows)
    st.dataframe(progress_df, use_container_width=True, hide_index=True)
    chart_df = progress_df.melt(id_vars="科目", value_vars=["已完成（hr）", "剩餘（hr）"], var_name="狀態", value_name="時數")
    fig = px.bar(chart_df, x="科目", y="時數", color="狀態", barmode="stack", labels={"時數": "小時"})
    fig.update_layout(margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig, use_container_width=True)
