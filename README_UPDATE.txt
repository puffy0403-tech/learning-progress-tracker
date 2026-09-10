學習紀錄管理展開選單更新

將更新包內的檔案覆蓋到部署中的 GitHub 專案：
shared.py → 與 app.py 同一層的 shared.py
pages/2_學習紀錄管理.py → pages/2_學習紀錄管理.py

不要把更新包再放進額外的 LearnPilot 子資料夾，也不要只更新 pages。
提交至 Streamlit 部署所使用的 repository / branch，等待部署完成。
若仍顯示舊版，於 Manage app 執行 Reboot app，再重新整理頁面。

確認：shared.py 搜尋 elif label == "學習紀錄管理"，下方應有 st.expander("學習紀錄管理"...)
成功後：學習紀錄管理左側會出現展開箭頭，點開有三項子選單。
不需要修改 Supabase SQL。
