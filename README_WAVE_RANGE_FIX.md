# LearnPilot 數字範圍波浪號修正版

來源：原對話可取得的 LearnPilot.zip。無法取得先前生成的 LearnPilot_fix_markdown_wave.zip，因此依指定採用備用附件。

## 修改
- shared.py 新增集中式 normalize_ai_display_text()，將數字之間的 ~ / ~~ 轉成 ～，包含時間、小數與空格。
- render_ai_plan_text() 在 section 解析前處理文字，涵蓋本週學習狀況分析、下一週學習計畫、學習調整建議，以及新生成與已儲存計畫。
- 桌面與行動日曆的科目、內容均在顯示時處理。
- Gemini prompt 要求範圍使用 ～，並修正提示中的 2~3 範例。
- 保留一般 Markdown 刪除線、程式碼區塊、行內程式碼、連結與 HTML comments。只處理顯示副本，未修改 Supabase 儲存、metadata 序列化、編輯、登入、依週刪除或自訂 section icons。

## 驗證
全部 6 個 Python 檔案通過 compile 語法檢查；18 個範例與重複處理一致性檢查通過。以 AST 比對確認上述顯示函式及 Gemini prompt 以外的既有函式未變動。未連線執行 Streamlit、Gemini 或 Supabase，需部署後進行實際帳號操作驗收。

## 更新
解壓縮後以 LearnPilot 資料夾內容更新既有專案（主要程式變更只有 shared.py），保留部署環境的 Secrets。重新啟動 Streamlit，再開啟既有計畫或產生新計畫確認顯示。無須資料庫 migration。

此檔案由 Windows Codex 環境產生，交付於 outputs/LearnPilot_fix_wave_range_final.zip（本環境無 /mnt/data）。
