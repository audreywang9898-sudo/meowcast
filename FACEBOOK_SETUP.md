# 台北天氣貓 Facebook 粉專發佈

台北每日早班、晚班在 Instagram 成功並保存收據後，使用同一支影片與原文案發佈至 **台北喵喵氣象台** 的 Facebook Reel。早晚 cron、IG 防重複、天氣圖輪替、墨爾本與週報流程維持原設定。

## 啟用

在 [GitHub Actions secrets](https://github.com/audreywang9898-sudo/meowcast/settings/secrets/actions) 新增：

| Secret | 值 |
| --- | --- |
| `TAIPEI_FB_PAGE_ID` | 台北喵喵氣象台粉專的數字 ID |
| `TAIPEI_FB_PAGE_ACCESS_TOKEN` | 此粉專的 Page Access Token，需具備粉專影片發佈權限；不能使用目前的 IG token 或 Facebook 個人帳號 token |

Meta 官方提供 [取得 Page Access Token 的流程](https://www.postman.com/meta/facebook/documentation/r56bjfd/facebook-api?entity=request-23987686-0b79260c-96bd-49de-875b-6076213785fc)。以可管理粉專的 Facebook 帳號及具備相應粉專發佈權限的 Meta app 授權後，取得該粉專 token。Token 直接存入 GitHub secret，不貼在聊天室、程式或公開媒體 repo。注意 token 的有效期限，過期時更新同名 secret。

先到 [Taipei Facebook Page](https://github.com/audreywang9898-sudo/meowcast/actions/workflows/facebook.yml) → Run workflow → `action=check`。這是唯讀檢查，驗證 token 指向正確名稱和 ID 的粉專，不會發文；它不能代替實際發佈權限的驗證。兩個 secret 都未設定時會明確警告 Facebook 尚未啟用，原本 IG 日報仍照常執行。

設定好後，下一次每日早班或晚班會接著執行 Facebook 發佈。以 `facebook/taipei/日期/班別/IG貼文ID.json` 的 `status=published`、Facebook `video_id` 與 `published_at` 作為完成證據；不能只看整個工作流程顯示綠色。

## 只補發 Facebook

在 **Taipei Facebook Page** → Run workflow 選 `action=publish`，填原 IG 發佈日期、早班 `0700` 或晚班 `1630`。要補舊日期或提前手動發佈的內容時，另填原 **Daily Meowcast** 的 run ID；程式會讀取永久收據與原影片，完全不呼叫 IG 發佈程式，也不更新 IG 排程標記。新功能上線前的舊收據沒有影片文案資訊，程式會停止並說明，避免為了 Facebook 補發而重發 IG。

Facebook 和 IG 各自保存收據。Facebook 失敗發生在 IG 收據提交之後，不會撤銷 IG 成功記錄。自動 recovery 在 IG 已通過原本班次去重時，只補 Facebook；提前手動發佈失敗時請使用上面的 Facebook-only 工作流程，不要重跑整個早班來補 Facebook。

Facebook 步驟失敗會在日報 summary 明確顯示「failed or pending」，保留 IG 工作流程原本的成功結果，避免 IG 既有守護流程把 Facebook 問題當成 IG 需要重發。請以 Facebook 步驟與獨立收據判斷是否成功。

上傳或完成發佈的回應逾時時，重試會查詢同一個 Facebook video ID。若仍未完成，會顯示待確認並停止，不另外建立或重發影片。若確認是權限拒絕或上傳失敗，需先查該 video ID 的實際狀態，再處理保存的 Facebook 收據；不要直接刪除收據造成重複發佈。

此功能涵蓋台北每日 Reel；週報 carousel 仍沿用原本流程。IG App 的「自動分享」設定保留給 App 內發文使用，程式日報改由獨立 Facebook API 步驟發佈。

## 開發驗證

`python -m unittest -v test_facebook` 覆蓋正常發佈、重試去重、提前手動與正式班次獨立、逾時查詢、儲存失敗阻擋發佈、錯誤粉專、缺少授權、dry run 無副作用、排程保持原設定。修改相關檔案會觸發唯讀 CI 和授權檢查，不會立即發出新貼文。

API 依據：[Meta 建立 Reel](https://www.postman.com/meta/facebook/request/rgkn91u/1-create-reel)、[官方 hosted upload 範例](https://github.com/fbsamples/Facebook-Reels-Publishing-API-Postman-Collection)、[完成發佈](https://www.postman.com/meta/facebook/request/juhnm3q/4-publish-reel)、[查詢三階段狀態](https://www.postman.com/meta/facebook/request/dtugkus/3-optional-get-upload-session-status)。
