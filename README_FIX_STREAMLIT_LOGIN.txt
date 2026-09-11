LearnPilot 修正版

修正內容：
1. 修正未登入時 StreamlitAPIException：
   原本：
       st.page_link("app.py", label="回到登入頁", icon=" ")
   新版 Streamlit 不接受空白 icon。

   已改為：
       st.page_link("app.py", label="回到登入頁")

2. 保留「依週刪除學習日曆」功能與 delete_plan()。
3. 保留目前版本其他既有功能。
4. 全部 Python 檔案已通過語法檢查。

GitHub 更新建議：
至少一起覆蓋 shared.py 與 pages/4_我的下週學習日曆.py。
若要避免版本混用，建議整個 ZIP 內容一起覆蓋。
