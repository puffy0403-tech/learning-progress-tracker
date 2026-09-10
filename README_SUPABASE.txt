# Supabase 多使用者版設定

1. 到 https://supabase.com 建立 Project。
2. Supabase Dashboard > SQL Editor，執行 `supabase_setup.sql`。
3. Project Settings / API（或 Connect）取得：
   - Project URL
   - Publishable key（或 legacy anon key）
4. Streamlit Cloud > App settings > Secrets：
   GEMINI_API_KEY = "..."
   SUPABASE_URL = "https://....supabase.co"
   SUPABASE_KEY = "..."
5. GitHub 用此版本的 app.py、shared.py、requirements.txt、pages/ 覆蓋原專案。
6. Streamlit 重新部署後，首頁會提供「登入 / 註冊」。

若 Supabase Auth 的 Confirm email 開啟：
- 註冊後必須先收 Email 點驗證連結，再登入。
若想專題 Demo 註冊後立刻登入：
- Supabase > Authentication > Providers > Email，關閉 Confirm email。

安全設計：
- 使用 Supabase Auth 儲存/驗證密碼，程式不保存明文密碼。
- goals / study_logs / plans 均含 user_id。
- SQL 已啟用 Row Level Security (RLS)，每個登入者只能讀寫自己的資料。
- 不需要 Service Role Key，也不要把 Service Role/Secret Key 放進 GitHub。


介面更新：已隱藏 Streamlit 原生 pages 導覽，改為 LearnPilot「功能列表」下拉式選單。
