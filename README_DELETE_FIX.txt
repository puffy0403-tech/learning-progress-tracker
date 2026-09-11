LearnPilot 學習日曆刪除功能最終修正

問題：
delete_plan() 誤用了專案中不存在的 authenticated_supabase()。

本專案原本實際使用：
- get_supabase()
- _table()
- current_user_id()

修正後 delete_plan() 完全沿用既有資料庫 helper：
    _table("plans").delete()
        .eq("id", int(plan_id))
        .eq("user_id", current_user_id())
        .execute()

因此：
- 可刪除選取週次的計畫
- 仍限制為目前登入使用者的 user_id
- 保留 Supabase RLS
- 不需要 SQL migration
- 同時保留未登入 page_link 的修正
