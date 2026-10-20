# 台北天氣貓：本機免費一鍵產片

本流程不使用 GitHub Actions 分鐘數，也不自動上傳 Instagram。沿用既有 render.py、caption.py、weather.py、asset/taipei、calendar 與 music 素材。

## 第一次準備

1. 將完整私人 GitHub 專案 `audreywang9898-sudo/meowcast` 下載 ZIP 並解壓縮。不要只下載 local 資料夾；原版圖片與音樂都在主專案。
2. 安裝 Python 3.12（Windows 安裝時勾選 Add Python to PATH）。
3. 安裝 FFmpeg，並確認終端機執行 `ffmpeg -version` 有結果。
4. Mac 使用者第一次執行前，在終端機進入專案資料夾，執行 `chmod +x local/*.command`。如果 Python 是由 Homebrew 管理，可能需要先建立虛擬環境再安裝 requirements.txt。

## 每天操作

- Windows 早班：雙擊 `local/run_morning_windows.bat`
- Windows 晚班：雙擊 `local/run_evening_windows.bat`
- Mac 早班：雙擊 `local/run_morning_mac.command`
- Mac 晚班：雙擊 `local/run_evening_mac.command`

程式會取得最新 Open-Meteo 天氣、選取原版圖片與音樂、輸出：
- `output/meowcast.mp4`：8 秒原版 Reels
- `output/caption.txt`：原版貼文文案
- `output/card.jpg`：原版封面

請在 Instagram App 手動上傳影片並貼上文案。每次執行會覆寫 output 內上次的同名檔案，請在下一班產片前先發佈或備份。

## 注意

- 電腦必須有網路。若 Open-Meteo 失敗，程式可能需要 CWA_API_KEY 才能使用台灣中央氣象署備援。
- 原程式的天氣圖片輪播狀態只有在原本 GitHub 自動發佈成功後才更新。本機手動產片不會推進遠端輪播狀態，因此連續幾天可能重複選到同一張天氣圖；節慶選圖仍依日期運作。
- 本機產片不會寫入遠端 Instagram 發佈紀錄，請先檢查 IG 避免重複發佈。
- 這些檔案不會停止 GitHub 現有定時排程。若要真正避免下個計費週期繼續消耗 Actions 額度，必須另外停用或精簡相關工作流程。
- 本流程尚未在你的 Windows 或 Mac 實機完成端到端驗證。
