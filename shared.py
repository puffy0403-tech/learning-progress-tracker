
import os
import sqlite3
from datetime import date, datetime, timedelta

import pandas as pd
import plotly.express as px
import re
import streamlit as st

# Optional Gemini support
try:
    from google import genai
except Exception:
    genai = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "learning_tracker.db")

st.set_page_config(
    page_title="Learning Progress Tracker",
    page_icon="📚",
    layout="wide",
)

# ---------- Database ----------
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            weekly_hours REAL NOT NULL,
            target_score REAL,
            target_date TEXT,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS study_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            study_date TEXT NOT NULL,
            subject TEXT NOT NULL,
            minutes INTEGER NOT NULL,
            note TEXT,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_start TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()

def add_goal(subject, weekly_hours, target_score, target_date):
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO goals(subject, weekly_hours, target_score, target_date, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            subject,
            weekly_hours,
            target_score if target_score is not None else None,
            str(target_date) if target_date else None,
            datetime.now().isoformat(timespec="seconds"),
        ),
    )
    conn.commit()
    conn.close()

def add_log(study_date, subject, minutes, note):
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO study_logs(study_date, subject, minutes, note, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            str(study_date),
            subject,
            int(minutes),
            note,
            datetime.now().isoformat(timespec="seconds"),
        ),
    )
    conn.commit()
    conn.close()

def update_log(log_id, study_date, subject, minutes, note):
    conn = get_conn()
    conn.execute(
        """
        UPDATE study_logs
        SET study_date = ?, subject = ?, minutes = ?, note = ?
        WHERE id = ?
        """,
        (str(study_date), subject, int(minutes), note, int(log_id)),
    )
    conn.commit()
    conn.close()

def delete_log(log_id):
    conn = get_conn()
    conn.execute("DELETE FROM study_logs WHERE id = ?", (int(log_id),))
    conn.commit()
    conn.close()

def save_plan(week_start, content):
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO plans(week_start, content, created_at)
        VALUES (?, ?, ?)
        """,
        (str(week_start), content, datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()

def load_goals():
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM goals ORDER BY id DESC", conn)
    conn.close()
    return df

def load_logs():
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM study_logs ORDER BY study_date DESC, id DESC", conn)
    conn.close()
    return df

def load_latest_plan():
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM plans ORDER BY id DESC LIMIT 1", conn)
    conn.close()
    return None if df.empty else df.iloc[0]["content"]

init_db()


# ---------- Login / Authentication ----------
def _get_login_config():
    """從 Streamlit Secrets 讀取登入帳號與密碼。"""
    try:
        login_cfg = st.secrets.get("login", {})
        username = str(login_cfg.get("username", "")).strip()
        password = str(login_cfg.get("password", ""))
        return username, password
    except Exception:
        return "", ""


def is_logged_in():
    return bool(st.session_state.get("logged_in", False))


def login_required():
    """保護功能頁面；未登入時停止執行頁面內容。"""
    if not is_logged_in():
        st.warning("🔐 請先登入 Learning Progress Tracker。")
        st.page_link("app.py", label="前往登入頁面", icon="🔐")
        st.stop()


def render_login():
    """顯示登入畫面；登入成功回傳 True。"""
    if is_logged_in():
        return True

    st.markdown(
        """
        <div style="max-width:520px;margin:5rem auto 1.5rem auto;text-align:center;">
            <div style="font-size:3rem;">📚</div>
            <h1 style="margin-bottom:.35rem;">Learning Progress Tracker</h1>
            <p style="opacity:.7;">請登入後使用個人學習進度追蹤系統</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    username_cfg, password_cfg = _get_login_config()

    if not username_cfg or not password_cfg:
        st.error("尚未設定登入帳號。請先在 Streamlit Cloud 的 Secrets 設定 [login] username 與 password。")
        st.stop()

    _, center, _ = st.columns([1, 1.2, 1])
    with center:
        with st.form("login_form"):
            username = st.text_input("帳號", placeholder="請輸入帳號")
            password = st.text_input("密碼", type="password", placeholder="請輸入密碼")
            submitted = st.form_submit_button("🔐 登入", type="primary", use_container_width=True)

        if submitted:
            import hmac
            user_ok = hmac.compare_digest(username.strip(), username_cfg)
            pass_ok = hmac.compare_digest(password, password_cfg)
            if user_ok and pass_ok:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("帳號或密碼錯誤。")

    return False


def render_logout_button():
    """在側邊欄顯示目前登入狀態與登出按鈕。"""
    if not is_logged_in():
        return

    username_cfg, _ = _get_login_config()
    st.sidebar.divider()
    st.sidebar.caption(f"👤 已登入：{username_cfg}")
    if st.sidebar.button("🚪 登出", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.pop("generated_plan", None)
        st.rerun()


def gemini_api_ready():
    """同時支援 Streamlit Cloud Secrets 與本機環境變數。"""
    api_key = ""
    try:
        api_key = str(st.secrets.get("GEMINI_API_KEY", "")).strip()
    except Exception:
        pass
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
    return bool(api_key) and genai is not None


# ---------- Helpers ----------
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

    lines.append("> 這是依目前目標與本週完成量產生的基本規劃；接上 Gemini API 後可進一步考慮空閒時段與學習內容。")
    return "\n".join(lines)

def build_ai_plan(goals, logs):
    # Prefer Streamlit Cloud secrets; fall back to local environment variable.
    api_key = ""
    try:
        api_key = str(st.secrets.get("GEMINI_API_KEY", "")).strip()
    except Exception:
        pass
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or genai is None:
        return build_rule_based_plan(goals, logs)

    wk = current_week_logs(logs)
    latest_goals = goals.drop_duplicates("subject", keep="first")

    goals_text = latest_goals[["subject", "weekly_hours", "target_score", "target_date"]].to_dict("records")
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
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return response.text


def parse_plan_calendar(plan_text, start_date):
    """把 AI / 規則式文字計畫轉成一週日曆資料。"""
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

        # 支援 Gemini 建議格式：週一：英文｜1.0 小時｜單字複習
        parts = [p.strip() for p in re.split(r"[｜|]", line) if p.strip()]
        subject = ""
        hours = 1.0
        content = ""

        first = parts[0] if parts else line
        first = re.sub(r"^(週一|週二|週三|週四|週五|週六|週日|星期一|星期二|星期三|星期四|星期五|星期六|星期日|星期天)\s*[：:]\s*", "", first)

        hour_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:小時|hr|hrs|hour|hours)", line, re.I)
        if hour_match:
            hours = float(hour_match.group(1))

        # 第一段若含「科目 1.0 小時」，移除時間後當科目
        subject = re.sub(r"\s*\d+(?:\.\d+)?\s*(?:小時|hr|hrs|hour|hours).*", "", first, flags=re.I).strip()
        if not subject:
            subject = "學習"

        if len(parts) >= 3:
            content = parts[2]
        elif len(parts) >= 2 and not re.search(r"(小時|hr|hour)", parts[1], re.I):
            content = parts[1]

        rows.append({
            "date": item_date,
            "weekday": ["週一","週二","週三","週四","週五","週六","週日"][day_index],
            "subject": subject,
            "hours": hours,
            "content": content,
        })

    return pd.DataFrame(rows)

def render_week_calendar(plan_text, next_week_start):
    cal = parse_plan_calendar(plan_text, next_week_start)

    st.markdown("### 🗓️ 我的下週學習日曆")
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
                        detail += f"<br><span style='font-size:.78rem;opacity:.72'>{item['content']}</span>"

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
        st.info("目前的 AI 文字計畫中沒有辨識到「週一～週日」的排程。重新產生計畫後會自動顯示在日曆中。")


