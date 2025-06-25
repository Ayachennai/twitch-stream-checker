# Twitch 直播監控與自動登入工具

這是一個功能強大的 Python 工具，它不僅能自動監控您喜愛的 Twitch 直播主，並在他們開播時自動開啟直播網頁，還能**保持您的 Twitch 登入狀態**，解決每次都要重新登入的煩惱。

## ✨ 核心功能

*   **保持登入狀態**：透過共享瀏覽器個人資料，您只需登入一次，未來即使重開程式，也能自動維持登入狀態，享受完整的 Twitch 互動體驗。
*   **智慧型反偵測**：採用 `undetected-chromedriver` 技術，模擬真人瀏覽行為，有效繞過 Twitch 的機器人偵測，確保登入過程順暢無阻。
*   **可靠的自動取消靜音**：透過 JavaScript 直接控制播放器，精準地取消直播靜音，不再受介面變動影響。
*   **完整的 UI 控制介面**：
    *   動態新增/刪除追蹤的直播主。
    *   可為每位直播主單獨設定是否在開播時自動開啟視窗。
    *   自由設定要用來開啟直播的瀏覽器程式路徑。
    *   自由設定用於保存登入資訊的個人資料資料夾路徑。
*   **系統托盤運行**：最小化後會在系統托盤顯示圖示，方便您隨時喚出或關閉程式。

## 🛠️ 設定教學

### 1. 安裝必要的套件

在開始之前，請確保您已安裝 Python。然後在終端機或命令提示字元中，切換到專案目錄下，執行以下指令來安裝所有必要的套件：

```bash
pip install -r requirements.txt
```

### 2. 取得 Twitch API 金鑰

本工具需要使用 Twitch API 來檢查直播狀態，因此您需要一組 API 金鑰 (Client ID 和 Client Secret)。

1.  前往 [Twitch Developers Console](https://dev.twitch.tv/console) 並登入。
2.  點擊「**註冊您的應用程式**」。
3.  **名稱**: 任意填寫，例如 `My Stream Checker`。
4.  **OAuth Redirect URLs**: 填寫 `http://localhost`。
5.  **分類**: 選擇「聊天機器人」或「網站整合」。
6.  點擊「**建立**」。
7.  建立成功後，您會看到一組 **Client ID**。請複製它。
8.  點擊「**新密鑰**」按鈕來產生一組 **Client Secret**。請複製並妥善保管它，此金鑰只會顯示一次。

### 3. 設定 `config.json`

1.  在專案中找到 `config.example.json` 這個範本檔案。
2.  將它**複製一份，並重新命名為 `config.json`**。
3.  用文字編輯器打開您剛剛建立的 `config.json` 檔案，並填入您的資訊。

-   `client_id`: 貼上您剛剛取得的 Client ID。
-   `client_secret`: 貼上您剛剛取得的 Client Secret。
-   `streamers`: 在清單中填入您想追蹤的 Twitch 直播主帳號名稱 (小寫)。
-   `check_interval_seconds`: 檢查的間隔秒數，預設為 60 秒。
-   `browser_path`: 您想用來開啟直播的瀏覽器執行檔路徑 (可透過 UI 設定)。
-   `user_data_dir`: 用於保存登入資訊的 Chrome 個人資料夾路徑 (可透過 UI 設定)。

**範例 `config.json`:**
```json
{
    "client_id": "your_client_id_here",
    "client_secret": "your_client_secret_here",
    "streamers": [
        "shroud",
        "pokimane"
    ],
    "check_interval_seconds": 60,
    "browser_path": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "user_data_dir": "D:\\Windsurf_code\\twitch\\chrome_profile",
    "auto_open_settings": {
        "shroud": true,
        "pokimane": true
    }
}
```

## 📦 下載與執行 (推薦給一般使用者)

如果您不想安裝 Python 或處理程式碼，可以直接下載打包好的執行檔：

1.  前往本專案的 [**Releases**](https://github.com/Ayachennai/twitch-stream-checker/releases) 頁面。
2.  下載最新版本的 `TwitchStreamChecker.exe` 檔案。
3.  在您電腦的任何地方，建立一個新的資料夾 (例如 `我的Twitch工具`)。
4.  將下載的 `TwitchStreamChecker.exe` 放到這個資料夾中。
5.  **依照下面的「設定教學」**，在同一個資料夾中建立並設定好您的 `config.json` 檔案。
6.  完成後，直接點兩下執行 `TwitchStreamChecker.exe` 即可！

## 🚀 如何執行 (開發者)


完成以上設定後，在終端機或命令提示字元中，切換到專案目錄下，然後執行：

```bash
python twitch_checker.py
```

程式將會啟動並開始在背景監控。當有直播主開播時，您會看到終端機顯示訊息，並自動開啟瀏覽器視窗。

**第一次使用時，請在開啟的瀏覽器視窗中手動登入您的 Twitch 帳號。** 由於設定了 `user_data_dir`，您的登入資訊將被保存，未來開啟時即可自動登入。
