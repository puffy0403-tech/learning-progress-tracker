import os
import base64
import re
import json
import math
import hashlib
from html import escape
from datetime import date, datetime, timedelta, timezone
import random

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
    initial_sidebar_state="auto",
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
    for key in list(st.session_state):
        if key.startswith("plan_editor_") or key.startswith("plan_draft_"):
            st.session_state.pop(key, None)
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
    hide_streamlit_toolbar()
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
    hide_streamlit_toolbar()
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
        "登入或建立帳號，開始記錄自己的學習進度!"
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
        st.warning(" 請先登入。")
        st.page_link("app.py", label="回到登入頁", icon=" ")
        st.stop()



def render_sidebar_menu():
    """自訂左側功能列表：LearnPilot 品牌 + 圖片式功能選單。"""
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
        # LearnPilot 品牌
        sidebar_icon = os.path.join(
            os.path.dirname(__file__), "assets", "learnpilot_icon.png"
        )
        brand_col1, brand_col2 = st.columns(
            [0.7, 2.3], vertical_alignment="center"
        )
        with brand_col1:
            if os.path.exists(sidebar_icon):
                st.image(sidebar_icon, width=56)
        with brand_col2:
            st.markdown(
                "<h3 style='margin:0; padding:0;'>LearnPilot</h3>",
                unsafe_allow_html=True,
            )

        # 圖片式功能列表
        with st.container(border=True):
            st.caption("功能列表")
            # 首頁：使用 assets/app.png 作為功能列表圖片
            home_icon = os.path.join(
                os.path.dirname(__file__), "assets", "app.png"
            )
            home_icon_col, home_link_col = st.columns(
                [0.18, 0.82], vertical_alignment="center"
            )
            with home_icon_col:
                if os.path.exists(home_icon):
                    st.image(home_icon, width=18)
            with home_link_col:
                st.page_link(
                    "app.py",
                    label="首頁",
                    use_container_width=True,
                )

            menu_items = [
                ("AI Study Plan", "ai_plan.png", "pages/1_AI_Study_Plan.py"),
                ("學習紀錄管理", "study_record.png", "pages/2_學習紀錄管理.py"),
                ("本週目標進度", "progress.png", "pages/3_本週目標進度.py"),
                ("我的下週學習日曆", "calendar.png", "pages/4_我的下週學習日曆.py"),
            ]

            for label, icon_file, page_path in menu_items:
                icon_path = os.path.join(
                    os.path.dirname(__file__), "assets", icon_file
                )
                icon_col, link_col = st.columns(
                    [0.18, 0.82], vertical_alignment="center"
                )
                with icon_col:
                    if os.path.exists(icon_path):
                        st.image(icon_path, width=18)
                with link_col:
                    if label == "AI Study Plan":
                        with st.expander("AI Study Plan", expanded=False):
                            for section in ("手動建立讀書計畫", "AI建立讀書計畫"):
                                st.button(
                                    section,
                                    key="ai_menu_" + section,
                                    use_container_width=True,
                                    on_click=select_ai_section,
                                    args=(section,),
                                )
                    elif label == "學習紀錄管理":
                        with st.expander("學習紀錄管理", expanded=False):
                            for section in ("設定學習目標", "紀錄今日學習", "查看學習紀錄/編輯"):
                                st.button(
                                    section, key="records_menu_" + section,
                                    use_container_width=True,
                                    on_click=select_records_section, args=(section,),
                                )
                    else:
                        st.page_link(
                            page_path,
                            label=label,
                            use_container_width=True,
                        )



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
    table = _table("plans")
    uid = current_user_id()
    response = table.insert({
        "user_id": uid,
        "week_start": str(week_start),
        "content": content,
    }).execute()
    if not response.data:
        raise RuntimeError("未收到儲存結果，請重新載入日曆確認。")
    return response.data[0]


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



def render_ai_plan_text(plan_text):
    """顯示 AI 計畫，三個主要區段使用 LearnPilot 自訂 PNG 圖示。"""
    icon_map = {
        "本週學習狀況分析": "analyze.png",
        "下一週學習計畫": "calendar.png",
        "學習調整建議": "suggestion.png",
    }

    blocks = []
    current = []
    for raw_line in str(plan_text or "").splitlines():
        clean = re.sub(r"^[#\s📊📈📅🗓️💡✨]+", "", raw_line).strip()
        matched = next((title for title in icon_map if title in clean), None)
        if matched:
            if current:
                blocks.append(("text", "\n".join(current)))
                current = []
            blocks.append(("heading", matched))
        else:
            current.append(raw_line)

    if current:
        blocks.append(("text", "\n".join(current)))

    for kind, value in blocks:
        if kind == "text":
            if value.strip():
                st.markdown(value)
        else:
            icon_path = os.path.join(os.path.dirname(__file__), "assets", icon_map[value])
            c1, c2 = st.columns([0.07, 0.93], vertical_alignment="center")
            with c1:
                if os.path.exists(icon_path):
                    st.image(icon_path, width=42)
            with c2:
                st.markdown(
                    f"<h2 style='margin:0; padding:0;'>{value}</h2>",
                    unsafe_allow_html=True,
                )

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
6. 最後給 2~3 點調整建議。\n7. 三個主要段落標題請使用「本週學習狀況分析」、「下一週學習計畫」、「學習調整建議」，標題前不要加入 Emoji 或其他圖示。
8. 每一個實際排程都必須獨立一行，並嚴格使用以下格式：
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
            if not response.text or not response.text.strip():
                raise ValueError("AI 回傳空白計畫")
            return response.text
        except Exception as exc:
            last_error = exc

    # 兩個 Gemini 模型都失敗時，交給外層頁面既有的 fallback
    # 顯示錯誤後改用規則式方法產生計畫。
    raise last_error


def parse_plan_calendar(plan_text, start_date):
    if "<!-- learnpilot-v1:" in (plan_text or ""):
        rows, _ = editable_plan_data(plan_text, start_date)
        return pd.DataFrame([dict(date=r["date"], weekday=["週一","週二","週三","週四","週五","週六","週日"][r["date"].weekday()], subject=r["subject"], hours=r["minutes"]/60, content=r["content"]) for r in rows], columns=["date","weekday","subject","hours","content"])
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


def render_desktop_week_calendar(plan_text, next_week_start):
    cal = parse_plan_calendar(plan_text, next_week_start)

    render_calendar_heading()
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
                            f"{escape(str(item['content']))}</span>"
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
                            <div style="font-weight:650;font-size:.9rem;">{escape(str(item['subject']))}</div>
                            <div style="font-size:.82rem;margin-top:4px;">{detail}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    if cal.empty:
        st.info("目前的 AI 文字計畫中沒有辨識到「週一～週日」的排程。")


# Editable plans retain the existing content TEXT column and RLS.
def load_plans():
    table = _table("plans")
    return table.select("*").eq("user_id", current_user_id()).order("id", desc=True).execute().data or []


def update_plan(plan_id, start, content, original_content):
    table = _table("plans")
    response = (table.update({"week_start": str(start), "content": content})
                .eq("id", int(plan_id)).eq("user_id", current_user_id())
                .eq("content", original_content).execute())
    if not response.data:
        raise RuntimeError("未更新：計畫可能已在其他分頁修改、刪除或登入已失效。請重新載入後再試。")
    return response.data[0]


def editable_plan_data(text, start):
    marker = "<!-- learnpilot-v1:"
    if marker in (text or ""):
        try:
            payload = text.rsplit(marker, 1)[1].strip().removesuffix("-->").strip()
            data = json.loads(payload)
            rows = [{**r, "date": date.fromisoformat(r["date"])} for r in data["items"]]
            return rows, data["notes"]
        except (ValueError, KeyError, TypeError):
            raise ValueError("計畫格式損壞，請保留原始文字並聯絡管理者。")
    rows, notes = [], []
    for line in (text or "").splitlines():
        # Only consume actual schedule lines; retain all other original text.
        if re.match(r"^\s*[-•*]?\s*(?:週|星期)[一二三四五六日天]\s*[：:]", line):
            cal = parse_plan_calendar(line, start)
            if not cal.empty:
                r = cal.iloc[0]
                minutes_match = re.search(r"(\d+(?:\.\d+)?)\s*分鐘", line)
                minutes = float(minutes_match[1]) if minutes_match else float(r["hours"])*60
                subject = re.sub(r"\s*\d+(?:\.\d+)?\s*分鐘.*", "", r["subject"]).strip()
                rows.append(dict(date=r["date"], subject=subject, minutes=minutes, content=r["content"]))
                continue
        notes.append(line)
    return rows, "\n".join(notes).strip()


def serialize_editable_plan(rows, notes):
    if not rows:
        raise ValueError("請至少新增一個學習項目。")
    cleaned = []
    for i, row in enumerate(rows, 1):
        try:
            day = date.fromisoformat(str(row["date"])[:10])
            minutes = float(row["minutes"])
        except (ValueError, TypeError, KeyError):
            raise ValueError(f"第 {i} 列：請填寫有效日期與分鐘。")
        subject = str(row.get("subject") or "").strip()
        if not subject or subject == "nan":
            raise ValueError(f"第 {i} 列：科目不可空白。")
        if not math.isfinite(minutes) or not 0 < minutes <= 1440:
            raise ValueError(f"第 {i} 列：分鐘須大於 0 且不超過 1440。")
        cleaned.append(dict(date=day.isoformat(), subject=subject, minutes=minutes,
                            content=str(row.get("content") or "")))
    start = date.fromisoformat(min(r["date"] for r in cleaned))
    start -= timedelta(days=start.weekday())
    if any(date.fromisoformat(r["date"]) > start + timedelta(days=6) for r in cleaned):
        raise ValueError("一份計畫請安排在同一週；跨週項目請另建計畫。")
    lines = ["### 學習計畫", str(notes).strip(), ""]
    for r in cleaned:
        day = date.fromisoformat(r["date"])
        weekday = ["週一","週二","週三","週四","週五","週六","週日"][day.weekday()]
        lines.append(f"- {weekday}：{r['subject']}｜{r['minutes']/60:g} 小時｜{r['content']}")
    payload = json.dumps(dict(items=cleaned, notes=str(notes)), ensure_ascii=True)
    return start, "\n".join(lines) + "\n<!-- learnpilot-v1:" + payload + " -->"


def render_plan_editor(text, start, key, record=None):
    key = f"plan_editor_{current_user_id()}_{key}"
    try:
        rows, notes = editable_plan_data(text, start)
    except ValueError as exc:
        st.error(str(exc))
        return
    if not rows:
        rows = [dict(date=start, subject="", minutes=60.0, content="")]
    st.caption("")
    with st.form(key):
        edited = st.data_editor(
            pd.DataFrame(rows), num_rows="dynamic", hide_index=True,
            use_container_width=True, key=key+"_rows",
            column_config={
                "date": st.column_config.DateColumn("日期（星期依日期自動計算）", required=True),
                "subject": st.column_config.TextColumn("科目 / 學習項目", required=True),
                "minutes": st.column_config.NumberColumn("預計分鐘", min_value=1, max_value=1440, required=True),
                "content": st.column_config.TextColumn("學習內容"),
            })
        edited_notes = st.text_area("分析、建議與其他原始文字", notes, key=key+"_notes")
        submitted = st.form_submit_button("更新這份計畫" if record else "儲存新計畫", use_container_width=True)
    if submitted:
        try:
            new_start, content = serialize_editable_plan(edited.to_dict("records"), edited_notes)
            if record:
                saved = update_plan(record["id"], new_start, content, record["content"])
            else:
                # Repeated submission of the same draft updates its saved row.
                saved = st.session_state.get(key+"_saved")
                if saved:
                    saved = update_plan(saved["id"], new_start, content, saved["content"])
                else:
                    saved = save_plan(new_start, content)
                st.session_state[key+"_saved"] = saved
            st.session_state["plan_draft_home_" + current_user_id()] = saved["id"]
            st.success("計畫已儲存。回到首頁即可看到更新，也可到『我的下週學習日曆』再次編輯。")
            if record:
                st.rerun()
        except Exception as exc:
            st.error(f"儲存失敗，編輯內容仍保留：{exc}")


def load_week_plans(start):
    """Read the signed-in user's selected week directly, without cached content."""
    table = _table("plans")
    return (table.select("*").eq("user_id", current_user_id())
            .eq("week_start", str(start)).order("id", desc=True).execute().data or [])


def render_home_plan():
    now = date.today()
    start = now - timedelta(days=now.weekday()) + timedelta(days=7)
    st.subheader("我的最新讀書計畫")
    st.button("重新整理學習日曆", key="home_plan_refresh")
    try:
        all_plans = load_plans()
        active = designated_plan(all_plans)
        if active:
            st.caption(f"目前指定：計畫 #{active['id']}｜{active['week_start']} 當週")
            render_week_calendar(active["content"], date.fromisoformat(active["week_start"]))
            render_edit_plan_link("查看 / 編輯或更換最新計畫")
            return
        plans = [p for p in all_plans if p["week_start"] == str(start)]
    except Exception as exc:
        st.error(f"無法讀取下週計畫：{exc}")
        return
    if not plans:
        st.info(f"{start} ～ {start + timedelta(days=6)} 尚未儲存學習計畫。")
        render_ai_plan_dropdown("home_ai_entry")
        return
    ids = [r["id"] for r in plans]
    preferred = st.session_state.get("plan_draft_home_" + current_user_id())
    index = ids.index(preferred) if preferred in ids else 0
    selected = st.selectbox("首頁顯示的下週計畫", ids, index=index,
                            format_func=lambda value: f"計畫 #{value}",
                            key=f"home_plan_selection_{current_user_id()}_{preferred}")
    record = next(r for r in plans if r["id"] == selected)
    render_week_calendar(record["content"], date.fromisoformat(record["week_start"]))
    st.caption("每次回到首頁都會重新讀取已儲存內容；若在其他分頁修改，請按重新整理學習日曆。")
    render_edit_plan_link("查看 / 編輯學習日曆")


def render_learning_settings(goals, page_key, section=None, sidebar=True):
    """Shared sidebar controls on home and learning-record pages."""
    settings_today = datetime.now(timezone(timedelta(hours=8))).date()
    prefix = f"learning_settings_{current_user_id()}_{page_key}"
    with st.sidebar if sidebar else st.container():
        if sidebar:
            st.header(" 學習設定")
    
        if section in (None, "設定學習目標"):
            with st.expander(" 設定學習目標", expanded=True):
                goal_subject = st.text_input("科目 / 學習主題", placeholder="例如：英文", key=prefix + "_goal_subject")
                weekly_hours = st.number_input("每週目標時數", min_value=0.5, max_value=100.0, value=7.0, step=0.5, key=prefix + "_weekly_hours")
                target_score = st.number_input("目標分數（選填）", min_value=0.0, max_value=100.0, value=80.0, step=1.0, key=prefix + "_target_score")
                target_date = st.date_input("目標日期", value=settings_today + timedelta(days=30), key=prefix + "_target_date")
        
                if st.button("儲存目標", use_container_width=True):
                    if goal_subject.strip():
                        add_goal(goal_subject.strip(), weekly_hours, target_score, target_date)
                        st.success("目標已儲存")
                        st.rerun()
                    else:
                        st.warning("請輸入學習主題")

        if section in (None, "紀錄今日學習"):
            with st.expander(" 記錄今日學習", expanded=True):
                existing_subjects = goals["subject"].drop_duplicates().tolist() if not goals.empty else []
                log_subject = st.selectbox("學習科目", options=existing_subjects + ["其他"], key=prefix + "_log_subject")
                custom_subject = ""
                if log_subject == "其他":
                    custom_subject = st.text_input("其他科目名稱", key=prefix + "_custom_subject")
        
                study_date = st.date_input("日期", value=settings_today, key=prefix + "_study_date")
                minutes = st.number_input("學習時間（分鐘）", min_value=1, max_value=1440, value=60, step=10, key=prefix + "_minutes")
                note = st.text_area("學習內容", placeholder="例如：閱讀論文第二章、完成 Python 練習", key=prefix + "_note")
        
                if st.button("新增學習紀錄", use_container_width=True):
                    subject_to_save = custom_subject.strip() if log_subject == "其他" else log_subject
                    if subject_to_save:
                        add_log(study_date, subject_to_save, minutes, note)
                        st.success("學習紀錄已新增")
                        st.rerun()
                    else:
                        st.warning("請輸入科目名稱")



def daily_encouragement(day=None):
    """A shuffled daily rotation, stable within a Taiwan calendar day."""
    if day is None:
        day = datetime.now(timezone(timedelta(hours=8))).date()
    messages = [
        "今天多懂一點，明天就多一份自信。",
        "不用一次做到完美，先完成今天的一小步。",
        "每一次練習，都在替未來的你累積實力。",
        "慢慢學也沒關係，持續前進就有收穫。",
        "把大目標拆小，今天也能有所進展。",
        "專心做好眼前這一題，就是進步的開始。",
        "遇到不懂的地方，正是成長的機會。",
        "給自己一點耐心，你正在一步步學會。",
        "今天的努力，會成為明天的底氣。",
        "休息一下再出發，學習也需要好好照顧自己。",
        "每一筆學習紀錄，都是你努力的證明。",
        "先開始五分鐘，讓行動帶你往前走。",
        "不必和別人比速度，照自己的節奏前進。",
        "願意再試一次，就多一次學會的可能。",
        "把好奇心留下來，答案會在探索中慢慢清楚。",
        "今天完成的小事，也值得為自己鼓掌。",
    ]
    random.Random("LearnPilot-daily-" + current_user_id()).shuffle(messages)
    return messages[day.toordinal() % len(messages)]

def select_ai_section(choice):
    if choice in ("手動建立讀書計畫", "AI建立讀書計畫"):
        st.session_state["plan_draft_section_" + current_user_id()] = choice
        st.switch_page("pages/1_AI_Study_Plan.py")

def select_records_section(choice):
    if choice in ("設定學習目標", "紀錄今日學習", "查看學習紀錄/編輯"):
        st.session_state["plan_draft_records_section_" + current_user_id()] = choice
        st.switch_page("pages/2_學習紀錄管理.py")

def render_ai_plan_dropdown(key):
    """AI creation entry point with separate keys for body and sidebar."""
    with st.expander("AI Study Plan", expanded=False):
        for section in ("手動建立讀書計畫", "AI建立讀書計畫"):
            st.button(section, key=key + "_" + section,
                      use_container_width=True,
                      on_click=select_ai_section, args=(section,))

def designated_plan(plans):
    selected = [p for p in plans if p.get("selected_at")]
    return max(selected, key=lambda p: (datetime.fromisoformat(p["selected_at"].replace("Z", "+00:00")), int(p["id"]))) if selected else None


def designate_latest_plan(plan_id):
    table = _table("plans")
    response = (table.update({"selected_at": datetime.now(timezone.utc).isoformat()})
                .eq("id", int(plan_id)).eq("user_id", current_user_id()).execute())
    if not response.data:
        raise RuntimeError("未更新任何計畫，請確認登入狀態與計畫是否仍存在。")
    return response.data[0]

def render_calendar_heading():
    icon_path = os.path.join(_BASE_DIR, "assets", "calendar_heading.png")
    with open(icon_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode("ascii")
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px;margin:0 0 12px;">'
        f'<img src="data:image/png;base64,{encoded}" alt="" style="width:42px;height:42px;object-fit:contain;">'
        '<h3 style="margin:0;padding:0;">學習日曆</h3></div>',
        unsafe_allow_html=True,
    )


def render_edit_plan_link(label):
    icon_col, link_col = st.columns([0.05, 0.95], gap="small", vertical_alignment="center")
    with icon_col:
        st.image(os.path.join(_BASE_DIR, "assets", "edit.png"), width=28)
    with link_col:
        st.page_link("pages/4_我的下週學習日曆.py", label=label)

def render_home_link():
    icon_col, link_col = st.columns([0.05, 0.95], gap="small", vertical_alignment="center")
    with icon_col:
        st.image(os.path.join(_BASE_DIR, "assets", "app.png"), width=28)
    with link_col:
        st.page_link("app.py", label="回到首頁")

def hide_streamlit_toolbar():
    render_responsive_styles()
    """Hide app toolbar actions while keeping sidebar navigation controls."""
    st.markdown("""
        <style>
        [data-testid="stToolbarActions"],
        [data-testid="stToolbarActionButton"],
        [data-testid="stMainMenu"],
        #MainMenu {
            display: none !important;
        }
        </style>
    """, unsafe_allow_html=True)

def render_responsive_styles():
    st.markdown("""
    <style>
    .lp-mobile-calendar {display:none;}
    @media (max-width: 640px) {
        .st-key-desktop_calendar {display:none !important;}
        .lp-mobile-calendar {display:block;}
        .stMainBlockContainer {
            padding-left:1rem !important;padding-right:1rem !important;
            padding-top:4rem !important;
        }
        /* Keep only icon/text rows horizontal; leave data columns responsive. */
        [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:first-child [data-testid="stImage"]) {
            flex-direction:row !important;
            flex-wrap:nowrap !important;
            align-items:center !important;
            gap:0.6rem !important;
        }
        [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:first-child [data-testid="stImage"]) > [data-testid="stColumn"]:first-child {
            flex:0 0 44px !important;
            width:44px !important;
            min-width:44px !important;
        }
        [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:first-child [data-testid="stImage"]) > [data-testid="stColumn"]:nth-child(2) {
            flex:1 1 0 !important;
            width:auto !important;
            min-width:0 !important;
        }
        [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:first-child [data-testid="stImage"]) [data-testid="stImage"] {
            width:100% !important;
        }
        [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:first-child [data-testid="stImage"]) [data-testid="stImage"] img {
            max-width:100% !important;
            max-height:48px !important;
            object-fit:contain;
        }
        [data-testid="stSidebar"] [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:first-child [data-testid="stImage"]) > [data-testid="stColumn"]:first-child {
            flex:0 0 28px !important;
            width:28px !important;
            min-width:28px !important;
        }
        [data-testid="stSidebar"] [data-testid="stPageLink"] a {
            white-space:normal !important;
            overflow-wrap:anywhere;
        }
        h1 {font-size:1.8rem !important;overflow-wrap:anywhere;}
        h2 {font-size:1.5rem !important;}
        h3 {font-size:1.2rem !important;}
        [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) {
            flex-wrap:wrap !important;gap:0.75rem !important;
        }
        [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) > [data-testid="stColumn"] {
            flex:1 1 calc(50% - 0.75rem) !important;
            width:calc(50% - 0.75rem) !important;min-width:0 !important;
        }
        [data-testid="stMetricValue"] {font-size:1.7rem !important;}
        [data-testid="stHorizontalBlock"]:has([data-testid="stPlotlyChart"]) {
            flex-direction:column !important;
        }
        [data-testid="stHorizontalBlock"]:has([data-testid="stPlotlyChart"]) > [data-testid="stColumn"] {
            width:100% !important;flex:1 1 100% !important;
        }
        [data-testid="stButton"] button,
        [data-testid="stFormSubmitButton"] button {min-height:44px;white-space:normal;}
        [data-testid="stDataFrame"], [data-testid="stDataEditor"] {max-width:100%;overflow-x:auto;}
        .lp-day-card {border:1px solid rgba(128,128,128,.25);border-radius:12px;padding:12px;margin-bottom:12px;}
        .lp-day-title {font-weight:700;margin-bottom:8px;}
        .lp-day-item {border-left:4px solid var(--primary-color,#00a6ad);padding:8px 10px;margin:6px 0;background:rgba(128,128,128,.06);overflow-wrap:anywhere;}
        .lp-day-detail {font-size:.9rem;opacity:.8;white-space:pre-wrap;}
    }
    </style>
    """, unsafe_allow_html=True)


def render_week_calendar(plan_text, next_week_start):
    with st.container(key="desktop_calendar"):
        render_desktop_week_calendar(plan_text, next_week_start)
    cal = parse_plan_calendar(plan_text, next_week_start)
    icon_path = os.path.join(_BASE_DIR, "assets", "calendar_heading.png")
    with open(icon_path, "rb") as f:
        icon = base64.b64encode(f.read()).decode("ascii")
    parts = [
        '<section class="lp-mobile-calendar">',
        f'<h3><img src="data:image/png;base64,{icon}" alt="" style="width:32px;vertical-align:middle;margin-right:8px;">學習日曆</h3>',
        f'<p>{next_week_start:%Y/%m/%d} ～ {next_week_start + timedelta(days=6):%Y/%m/%d}</p>'
    ]
    for i, weekday in enumerate(["週一","週二","週三","週四","週五","週六","週日"]):
        day = next_week_start + timedelta(days=i)
        parts.append(f'<div class="lp-day-card"><div class="lp-day-title">{weekday} · {day:%m/%d}</div>')
        rows = cal[cal["date"] == day] if not cal.empty else pd.DataFrame()
        if rows.empty:
            parts.append('<div class="lp-day-detail">休息 / 彈性</div>')
        else:
            for _, row in rows.iterrows():
                subject = escape(str(row["subject"]))
                content = escape(str(row["content"]))
                minutes = float(row["hours"])*60
                parts.append(f'<div class="lp-day-item"><strong>{subject}</strong><div>{minutes:g} 分鐘</div><div class="lp-day-detail">{content}</div></div>')
        parts.append('</div>')
    parts.append('</section>')
    st.markdown("".join(parts), unsafe_allow_html=True)
