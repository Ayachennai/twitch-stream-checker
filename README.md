# Twitch 直播監控與自動登入工具

這是一個功能強大的 Python 工具，它不僅能監控您喜愛的 Twitch 直播主，並在他們開播時透過系統通知提醒您，還能自動開啟直播網頁。

## 核心功能

*   **API 監控**：透過 Twitch API 精準檢查直播狀態。
*   **自動開啟網頁**：偵測到開播時，可自動使用 `undetected-chromedriver` 開啟直播頁面，模擬真人行為以避免被偵測。
*   **系統通知**：當有追蹤的頻道開播時，會發送 Windows 系統通知。
*   **系統托盤運行**：程式會常駐在系統托盤 (System Tray) 中，方便隨時操作或關閉。
*   **可設定性**：可自由設定要監控的頻道列表和檢查的時間間隔。

## 設定與安裝

### 1. 環境需求
*   Python 3.12 (建議)
*   Windows 作業系統

### 2. 安裝依賴套件
在專案根目錄下開啟 PowerShell，並執行以下指令來安裝所有必要的套件：
```bash
pip install -r requirements.txt
```

### 3. 取得 Twitch API 金鑰
本工具需要使用 Twitch API 來檢查直播狀態，因此您需要一組 API 金鑰 (Client ID 和 Client Secret)。

1.  前往 [Twitch Developers Console](https://dev.twitch.tv/console) 並登入。
2.  在左側選擇「應用程式」，然後點擊「**註冊您的應用程式**」。
3.  **名稱**: 任意填寫，例如 `My Stream Checker`。
4.  **OAuth Redirect URLs**: 填寫 `http://localhost`。
5.  **分類**: 選擇「聊天機器人」或「網站整合」。
6.  點擊「**建立**」。
7.  建立成功後，您會看到一組 **Client ID**。請複製它。
8.  點擊「**新密鑰**」按鈕來產生一組 **Client Secret**。請複製並妥善保管它，此金鑰只會顯示一次。

### 4. 設定 `config.json`
1.  在專案中找到 `config.example.json` 這個範本檔案。
2.  將它**複製一份，並重新命名為 `config.json`**。
3.  用文字編輯器打開您剛剛建立的 `config.json` 檔案，並填入您的資訊。

*   `client_id`: 貼上您剛剛取得的 Client ID。
*   `client_secret`: 貼上您剛剛取得的 Client Secret。
*   `twitch_channels`: 在清單中填入您想監控的 Twitch 直播主帳號名稱 (英文小寫)。
*   `check_interval_seconds`: 檢查的間隔秒數，預設為 60 秒。

**範例 `config.json`:**
```json
{
  "client_id": "your_client_id_here",
  "client_secret": "your_client_secret_here",
  "twitch_channels": [
    "shroud",
    "pokimane"
  ],
  "check_interval_seconds": 60
}
```

## 如何執行
完成以上設定後，在專案根目錄下開啟 PowerShell，然後執行：
```bash
python twitch_checker.py
```
程式將會啟動並最小化到系統托盤開始在背景監控。

## 如何打包成執行檔 (.exe)

本專案使用 PyInstaller 進行打包。

### 重要注意事項
根據測試，最新的 PyInstaller 版本 (6.x) 可能會與某些 Windows 環境產生衝突，導致打包後的 `.exe` 檔案無法執行且沒有任何錯誤訊息。

**請務必使用 PyInstaller 5.13.2 版本進行打包。**

### 1. 安裝指定的 PyInstaller 版本
```bash
pip install pyinstaller==5.13.2
```

### 2. 執行打包
使用專案內附的 `.spec` 檔案進行打包，可以確保所有資源都被正確包含：
```bash
pyinstaller twitch_checker.spec
```

### 3. 找到執行檔
打包成功後，您可以在 `dist/TwitchStreamChecker` 資料夾中找到 `TwitchStreamChecker.exe`。將 `config.json` 檔案也複製到這個資料夾旁邊，就可以一起執行了。