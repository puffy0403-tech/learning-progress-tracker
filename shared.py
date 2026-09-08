import os
import re
from datetime import date, datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st
from PIL import Image

# Optional Gemini support
try:
    from google import genai
except Exception:
    genai = None

# Supabase
try:
    from supabase import create_client
except Exception:
    create_client = None

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_LOGO_ICON_PATH = os.path.join(_BASE_DIR, "assets", "learnpilot_icon.png")

_page_icon = "🤖"
if os.path.exists(_LOGO_ICON_PATH):
    try:
        _page_icon = Image.open(_LOGO_ICON_PATH)
    except Exception:
        pass

st.set_page_config(
    page_title="LearnPilot",
    page_icon=_page_icon,
    layout="wide",
)


# =========================================================
# Supabase configuration / authentication
# =========================================================
def _secret(name, default=""):
    try:
        value = st.secrets.get(name, default)
        return str(value).strip() if value is not None else default
    except Exception:
        return str(os.getenv(name, default)).strip()


def supabase_configured():
    return bool(_secret("SUPABASE_URL") and _secret("SUPABASE_KEY") and create_client is not None)


def _new_supabase_client():
    if not supabase_configured():
        return None
    return create_client(_secret("SUPABASE_URL"), _secret("SUPABASE_KEY"))


def _store_auth_response(response):
    session = getattr(response, "session", None)
    user = getattr(response, "user", None)

    if session is not None:
        st.session_state["sb_access_token"] = session.access_token
        st.session_state["sb_refresh_token"] = session.refresh_token

    if user is not None:
        st.session_state["user_id"] = str(user.id)
        st.session_state["user_email"] = str(user.email or "")
        metadata = getattr(user, "user_metadata", None) or {}
        st.session_state["display_name"] = str(metadata.get("display_name", "")).strip()


def get_supabase():
    """Return a Supabase client authenticated as the current Streamlit user."""
    client = _new_supabase_client()
    if client is None:
        return None

    access_token = st.session_state.get("sb_access_token")
    refresh_token = st.session_state.get("sb_refresh_token")

    if access_token and refresh_token:
        try:
            response = client.auth.set_session(access_token, refresh_token)
            _store_auth_response(response)
        except Exception:
            # Token/session is no longer valid.
            for key in (
                "sb_access_token", "sb_refresh_token",
                "user_id", "user_email", "display_name"
            ):
                st.session_state.pop(key, None)
            return _new_supabase_client()

    return client


def is_logged_in():
    return bool(
        st.session_state.get("user_id")
        and st.session_state.get("sb_access_token")
        and st.session_state.get("sb_refresh_token")
    )


def current_user_id():
    return str(st.session_state.get("user_id", "")).strip()


def current_user_label():
    return (
        st.session_state.get("display_name")
        or st.session_state.get("user_email")
        or "使用者"
    )


def sign_up(email, password, display_name=""):
    client = _new_supabase_client()
    if client is None:
        raise RuntimeError("尚未設定 Supabase。")

    payload = {
        "email": email.strip(),
        "password": password,
    }
    if display_name.strip():
        payload["options"] = {"data": {"display_name": display_name.strip()}}

    response = client.auth.sign_up(payload)
    _store_auth_response(response)
    return response


def sign_in(email, password):
    client = _new_supabase_client()
    if client is None:
        raise RuntimeError("尚未設定 Supabase。")

    response = client.auth.sign_in_with_password(
        {"email": email.strip(), "password": password}
    )
    _store_auth_response(response)
    return response


def sign_out():
    try:
        client = get_supabase()
        if client is not None and is_logged_in():
            client.auth.sign_out()
    except Exception:
        pass

    for key in (
        "sb_access_token", "sb_refresh_token",
        "user_id", "user_email", "display_name",
        "generated_plan"
    ):
        st.session_state.pop(key, None)




def render_feature_menu():
    """側邊欄功能列表：每個功能以圖片 + 名稱呈現，點擊後切換頁面。"""
    st.sidebar.markdown("### 功能列表")

    menu_items = [
        ("AI Study Plan", "assets/ai_plan.png", "pages/1_AI_Study_Plan.py"),
        ("學習紀錄管理", "assets/study_record.png", "pages/2_學習紀錄管理.py"),
        ("本週目標進度", "assets/progress.png", "pages/3_本週目標進度.py"),
        ("我的下週學習日曆", "assets/calendar.png", "pages/4_我的下週學習日曆.py"),
    ]

    for label, icon_rel, page in menu_items:
        icon_path = os.path.join(os.path.dirname(__file__), icon_rel)
        c1, c2 = st.sidebar.columns([0.18, 0.82], vertical_alignment="center")
        with c1:
            if os.path.exists(icon_path):
                st.image(icon_path, width=30)
        with c2:
            st.page_link(page, label=label, use_container_width=True)


def render_feature_title(title, icon_filename, caption=None, icon_width=58):
    """顯示功能頁標題：左側圖片 + 右側標題。"""
    icon_path = os.path.join(os.path.dirname(__file__), "assets", icon_filename)
    icon_col, title_col = st.columns([0.55, 8.45], vertical_alignment="center")
    with icon_col:
        if os.path.exists(icon_path):
            st.image(icon_path, width=icon_width)
    with title_col:
        st.markdown(
            f"<h1 style='margin:0; padding:0;'>{title}</h1>",
            unsafe_allow_html=True,
        )
        if caption:
            st.caption(caption)


def render_brand_header(subtitle=""):
    """顯示 LearnPilot 圖示 + 系統名稱，可在首頁與各功能頁重複使用。"""
    icon_path = os.path.join(os.path.dirname(__file__), "assets", "learnpilot_icon.png")

    brand_col1, brand_col2 = st.columns([0.55, 5.45], vertical_alignment="center")
    with brand_col1:
        if os.path.exists(icon_path):
            st.image(icon_path, width=78)
    with brand_col2:
        st.markdown(
            "<h1 style='margin:0; padding:0;'>LearnPilot</h1>",
            unsafe_allow_html=True,
        )
        if subtitle:
            st.caption(subtitle)


def render_auth():
    """Login / registration screen. Returns True when logged in."""
    if is_logged_in():
        return True
    icon_path = os.path.join(os.path.dirname(__file__), "assets", "learnpilot_icon.png")
    _, auth_brand, _ = st.columns([1.15, 1.7, 1.15])
    with auth_brand:
        logo_col, name_col = st.columns([0.75, 2.25], vertical_alignment="center")
        with logo_col:
            if os.path.exists(icon_path):
                st.image(icon_path, width=88)
        with name_col:
            st.markdown(
                "<h1 style='margin:0; padding:0;'>LearnPilot</h1>",
                unsafe_allow_html=True,
            )

    st.markdown(
        "<p style='text-align:center;opacity:.7;margin-top:.35rem;'>"
        "登入或建立帳號，開始記錄自己的學習進度"
        "</p>",
        unsafe_allow_html=True,
    )

    if not supabase_configured():
        st.error(
            "尚未完成 Supabase 設定。請在 Streamlit Cloud Secrets 加入 "
            "SUPABASE_URL 與 SUPABASE_KEY。"
        )
        st.stop()

    _, center, _ = st.columns([1, 1.3, 1])
    with center:
        login_tab, signup_tab = st.tabs([" 登入", " 註冊"])

        with login_tab:
            with st.form("supabase_login_form"):
                email = st.text_input("Email", key="login_email", placeholder="name@example.com")
                password = st.text_input("密碼", type="password", key="login_password")
                submitted = st.form_submit_button("登入", type="primary", use_container_width=True)

            if submitted:
                if not email.strip() or not password:
                    st.warning("請輸入 Email 與密碼。")
                else:
                    try:
                        sign_in(email, password)
                        st.success("登入成功。")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"登入失敗：{exc}")

        with signup_tab:
            with st.form("supabase_signup_form"):
                display_name = st.text_input("顯示名稱（選填）", key="signup_name")
                email = st.text_input("Email", key="signup_email", placeholder="name@example.com")
                password = st.text_input("密碼（至少 6 碼）", type="password", key="signup_password")
                confirm = st.text_input("確認密碼", type="password", key="signup_confirm")
                submitted = st.form_submit_button("建立帳號", type="primary", use_container_width=True)

            if submitted:
                if not email.strip():
                    st.warning("請輸入 Email。")
                elif len(password) < 6:
                    st.warning("密碼至少需要 6 個字元。")
                elif password != confirm:
                    st.warning("兩次輸入的密碼不一致。")
                else:
                    try:
                        response = sign_up(email, password, display_name)
                        if getattr(response, "session", None) is not None:
                            st.success("註冊成功，已自動登入。")
                            st.rerun()
                        else:
                            st.success("註冊成功！請先到 Email 完成驗證，再回來登入。")
                    except Exception as exc:
                        st.error(f"註冊失敗：{exc}")

    return False


def login_required():
    if not is_logged_in():
        st.warning("🔐 請先登入。")
        st.page_link("app.py", label="回到登入頁", icon="🔐")
        st.stop()



def render_sidebar_menu():
    """自訂左側功能列表，取代 Streamlit 自動產生的 pages 導覽。"""
    st.markdown(
        """
        <style>
        [data-testid="stSidebarNav"] {
            display: none;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        sidebar_icon = os.path.join(os.path.dirname(__file__), "assets", "learnpilot_icon.png")
        brand_col1, brand_col2 = st.columns([0.7, 2.3], vertical_alignment="center")
        with brand_col1:
            if os.path.exists(sidebar_icon):
                st.image(sidebar_icon, width=56)
        with brand_col2:
            st.markdown(
                "<h3 style='margin:0; padding:0;'>LearnPilot</h3>",
                unsafe_allow_html=True,
            )

        with st.expander(" 功能列表", expanded=True):
            st.page_link("app.py", label="首頁", icon="🏠", use_container_width=True)
            st.page_link("pages/1_AI_Study_Plan.py", label="AI Study Plan", icon="🤖", use_container_width=True)
            st.page_link("pages/2_學習紀錄管理.py", label="學習紀錄管理", icon="📝", use_container_width=True)
            st.page_link("pages/3_本週目標進度.py", label="本週目標進度", icon="🎯", use_container_width=True)
            st.page_link("pages/4_我的下週學習日曆.py", label="我的下週學習日曆", icon="📅", use_container_width=True)


def render_account_sidebar():
    if not is_logged_in():
        return
    st.sidebar.divider()
    st.sidebar.caption(f"👤 {current_user_label()}")
    if st.sidebar.button(" 登出", use_container_width=True):
        sign_out()
        st.rerun()


# =========================================================
# Supabase database helpers — every row belongs to user_id
# =========================================================
def _table(name):
    client = get_supabase()
    if client is None or not is_logged_in():
        raise RuntimeError("尚未登入 Supabase。")
    return client.table(name)


def _df(data, columns):
    if not data:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(data)


def add_goal(subject, weekly_hours, target_score, target_date):
    uid = current_user_id()
    _table("goals").insert({
        "user_id": uid,
        "subject": subject,
        "weekly_hours": float(weekly_hours),
        "target_score": float(target_score) if target_score is not None else None,
        "target_date": str(target_date) if target_date else None,
    }).execute()


def add_log(study_date, subject, minutes, note):
    uid = current_user_id()
    _table("study_logs").insert({
        "user_id": uid,
        "study_date": str(study_date),
        "subject": subject,
        "minutes": int(minutes),
        "note": note,
    }).execute()


def update_log(log_id, study_date, subject, minutes, note):
    uid = current_user_id()
    (
        _table("study_logs")
        .update({
            "study_date": str(study_date),
            "subject": subject,
            "minutes": int(minutes),
            "note": note,
        })
        .eq("id", int(log_id))
        .eq("user_id", uid)
        .execute()
    )


def delete_log(log_id):
    uid = current_user_id()
    (
        _table("study_logs")
        .delete()
        .eq("id", int(log_id))
        .eq("user_id", uid)
        .execute()
    )


def save_plan(week_start, content):
    uid = current_user_id()
    _table("plans").insert({
        "user_id": uid,
        "week_start": str(week_start),
        "content": content,
    }).execute()


def load_goals():
    uid = current_user_id()
    response = (
        _table("goals")
        .select("*")
        .eq("user_id", uid)
        .order("id", desc=True)
        .execute()
    )
    return _df(
        response.data,
        ["id", "user_id", "subject", "weekly_hours", "target_score",
         "target_date", "created_at"]
    )


def load_logs():
    uid = current_user_id()
    response = (
        _table("study_logs")
        .select("*")
        .eq("user_id", uid)
        .order("study_date", desc=True)
        .order("id", desc=True)
        .execute()
    )
    return _df(
        response.data,
        ["id", "user_id", "study_date", "subject", "minutes", "note", "created_at"]
    )


def load_latest_plan():
    uid = current_user_id()
    response = (
        _table("plans")
        .select("*")
        .eq("user_id", uid)
        .order("id", desc=True)
        .limit(1)
        .execute()
    )
    return None if not response.data else response.data[0]["content"]


# =========================================================
# Learning helpers
# =========================================================
today = date.today()
week_start = today - timedelta(days=today.weekday())
week_end = week_start + timedelta(days=6)


def current_week_logs(logs):
    if logs.empty:
        return logs.copy()
    x = logs.copy()
    x["study_date"] = pd.to_datetime(x["study_date"]).dt.date
    return x[(x["study_date"] >= week_start) & (x["study_date"] <= week_end)]


def build_rule_based_plan(goals, logs):
    if goals.empty:
        return "目前還沒有學習目標。請先在左側設定至少一個每週目標。"

    wk = current_week_logs(logs)
    studied = (
        wk.groupby("subject")["minutes"].sum().div(60).to_dict()
        if not wk.empty else {}
    )

    latest_goals = goals.drop_duplicates("subject", keep="first")
    lines = ["### 下週學習計畫", ""]
    weekdays = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]

    day_i = 0
    for _, row in latest_goals.iterrows():
        subject = row["subject"]
        target = float(row["weekly_hours"])
        done = float(studied.get(subject, 0))
        remaining = max(target - done, target * 0.6)
        sessions = max(2, min(5, round(remaining)))
        each = max(0.5, remaining / sessions)

        lines.append(f"**{subject}**：建議安排 {sessions} 次，每次約 {each:.1f} 小時。")
        for _ in range(sessions):
            lines.append(f"- {weekdays[day_i % 7]}：{subject} {each:.1f} 小時")
            day_i += 1
        lines.append("")

    lines.append("> 這是依目前目標與本週完成量產生的基本規劃。")
    return "\n".join(lines)


def gemini_api_ready():
    return bool(_secret("GEMINI_API_KEY") and genai is not None)


def build_ai_plan(goals, logs):
    api_key = _secret("GEMINI_API_KEY")
    if not api_key or genai is None:
        return build_rule_based_plan(goals, logs)

    wk = current_week_logs(logs)
    latest_goals = goals.drop_duplicates("subject", keep="first")

    goals_text = latest_goals[
        ["subject", "weekly_hours", "target_score", "target_date"]
    ].to_dict("records")

    logs_text = (
        wk[["study_date", "subject", "minutes", "note"]].to_dict("records")
        if not wk.empty else []
    )

    prompt = f"""
你是一個個人學習規劃助手。請依照使用者的學習目標與本週學習紀錄，
產生「下一週」可執行的學習計畫。

要求：
1. 以繁體中文輸出。
2. 先簡短分析各科目的完成狀況。
3. 再安排週一到週日的學習內容與時數。
4. 每日不要塞太多工作。
5. 若本週某科目落後，下一週稍微提高該科目比重。
6. 最後給 2~3 點調整建議。
7. 每一個實際排程都必須獨立一行，並嚴格使用以下格式：
   - 週一：英文｜1.0 小時｜單字複習
   - 週二：Python｜1.5 小時｜完成資料分析練習
   一週七天都可以安排，也可以保留休息日。

學習目標：
{goals_text}

本週學習紀錄：
{logs_text}
"""

    client = genai.Client(api_key=api_key)

    # Gemini 模型自動備援：
    # 1) 優先使用 gemini-3.6-flash
    # 2) 若遇到 503 / 高流量 / 暫時不可用，再改用 gemini-3.5-flash-lite
    model_candidates = [
        "gemini-3.6-flash",
        "gemini-3.5-flash-lite",
    ]

    last_error = None

    for model_name in model_candidates:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            return response.text
        except Exception as exc:
            last_error = exc

    # 兩個 Gemini 模型都失敗時，交給外層頁面既有的 fallback
    # 顯示錯誤後改用規則式方法產生計畫。
    raise last_error


def parse_plan_calendar(plan_text, start_date):
    weekday_map = {
        "週一": 0, "星期一": 0,
        "週二": 1, "星期二": 1,
        "週三": 2, "星期三": 2,
        "週四": 3, "星期四": 3,
        "週五": 4, "星期五": 4,
        "週六": 5, "星期六": 5,
        "週日": 6, "星期日": 6, "週天": 6, "星期天": 6,
    }

    rows = []
    if not plan_text:
        return pd.DataFrame(columns=["date", "weekday", "subject", "hours", "content"])

    for raw_line in plan_text.splitlines():
        line = raw_line.strip().lstrip("-•").strip()
        if not line:
            continue

        day_name = next((d for d in weekday_map if d in line), None)
        if not day_name:
            continue

        day_index = weekday_map[day_name]
        item_date = start_date + timedelta(days=day_index)

        parts = [p.strip() for p in re.split(r"[｜|]", line) if p.strip()]
        first = parts[0] if parts else line
        first = re.sub(
            r"^(週一|週二|週三|週四|週五|週六|週日|星期一|星期二|星期三|星期四|星期五|星期六|星期日|星期天)\s*[：:]\s*",
            "",
            first,
        )

        hours = 1.0
        hour_match = re.search(
            r"(\d+(?:\.\d+)?)\s*(?:小時|hr|hrs|hour|hours)",
            line,
            re.I,
        )
        if hour_match:
            hours = float(hour_match.group(1))

        subject = re.sub(
            r"\s*\d+(?:\.\d+)?\s*(?:小時|hr|hrs|hour|hours).*",
            "",
            first,
            flags=re.I,
        ).strip() or "學習"

        content = ""
        if len(parts) >= 3:
            content = parts[2]
        elif len(parts) >= 2 and not re.search(r"(小時|hr|hour)", parts[1], re.I):
            content = parts[1]

        rows.append({
            "date": item_date,
            "weekday": ["週一", "週二", "週三", "週四", "週五", "週六", "週日"][day_index],
            "subject": subject,
            "hours": hours,
            "content": content,
        })

    return pd.DataFrame(rows)


def render_week_calendar(plan_text, next_week_start):
    cal = parse_plan_calendar(plan_text, next_week_start)

    st.markdown("###  我的下週學習日曆")
    st.caption(
        f"{next_week_start.strftime('%Y/%m/%d')} ～ "
        f"{(next_week_start + timedelta(days=6)).strftime('%Y/%m/%d')}"
    )

    cols = st.columns(7)
    weekday_labels = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]

    for i, col in enumerate(cols):
        current_date = next_week_start + timedelta(days=i)
        with col:
            st.markdown(
                f"""
                <div style="
                    text-align:center;
                    padding:10px 6px;
                    border:1px solid rgba(128,128,128,.25);
                    border-radius:12px;
                    margin-bottom:8px;
                ">
                    <div style="font-weight:700;">{weekday_labels[i]}</div>
                    <div style="font-size:0.85rem; opacity:.7;">{current_date.strftime('%m/%d')}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            day_rows = cal[cal["date"] == current_date] if not cal.empty else pd.DataFrame()

            if day_rows.empty:
                st.caption("休息 / 彈性")
            else:
                for _, item in day_rows.iterrows():
                    detail = f"{item['hours']:.1f} hr"
                    if item["content"]:
                        detail += (
                            f"<br><span style='font-size:.78rem;opacity:.72'>"
                            f"{item['content']}</span>"
                        )

                    st.markdown(
                        f"""
                        <div style="
                            padding:9px;
                            border-left:4px solid var(--primary-color);
                            border-radius:8px;
                            background:rgba(128,128,128,.08);
                            margin-bottom:7px;
                            min-height:72px;
                        ">
                            <div style="font-weight:650;font-size:.9rem;">{item['subject']}</div>
                            <div style="font-size:.82rem;margin-top:4px;">{detail}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    if cal.empty:
        st.info("目前的 AI 文字計畫中沒有辨識到「週一～週日」的排程。")
