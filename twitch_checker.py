import customtkinter
import requests
import json
import time
import webbrowser
import os
import threading
import re
import subprocess
from customtkinter import filedialog
from PIL import Image, ImageDraw
import pystray
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import undetected_chromedriver as uc
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
import sys
import subprocess
import socket
import contextlib
import logging

# --- 日誌設定 ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='twitch_checker.log',
    filemode='a', # 'a' for append, 'w' for overwrite
    encoding='utf-8'
)

# --- 常數 ---
CONFIG_FILE = 'config.json'

# --- 主應用程式類別 ---
class TwitchApp(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        logging.info("應用程式啟動中...")

        self.title("Twitch 直播監控")
        self.geometry("350x570")
        self.protocol("WM_DELETE_WINDOW", self.hide_to_tray)

        # 設定視窗圖示
        self.icon_path = "app_icon.ico"
        if os.path.exists(self.icon_path):
            try:
                self.iconbitmap(self.icon_path)
            except Exception as e:
                print(f"設定圖示失敗: {e}")

        self.config = self.load_config()
        if not self.config:
            self.quit()
            return

        self.client_id = self.config.get('client_id')
        self.client_secret = self.config.get('client_secret')
        self.streamers_to_watch = [s.lower() for s in self.config.get('streamers', [])]
        self.check_interval = self.config.get('check_interval_seconds', 60)
        self.browser_path = self.config.get('browser_path')
        self.user_data_dir = self.config.get('user_data_dir')
        self.auto_open_states = self.config.get('auto_open_settings', {})
        for streamer in self.streamers_to_watch:
            if streamer not in self.auto_open_states:
                self.auto_open_states[streamer] = True

        self.token = None
        self.webdriver_instances = {}
        self.streamer_widgets = {}
        self.running = True
        self.temporary_message_active = False
        self.tray_icon = None
        self.after_id = None
        self.opening_stream_locks = {}

        self.setup_ui()
        self.redraw_streamer_list()

                # 在獨立執行緒中啟動監控和系統匣圖示
        logging.info("準備啟動背景任務執行緒...")
        threading.Thread(target=self.run_background_tasks, daemon=True).start()

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1) # 主要內容區域

        title_label = customtkinter.CTkLabel(self, text="追蹤頻道，直播不漏接", font=customtkinter.CTkFont(size=20, weight="bold"))
        title_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")

        add_frame = customtkinter.CTkFrame(self)
        add_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        add_frame.grid_columnconfigure(0, weight=1)

        self.url_entry = customtkinter.CTkEntry(add_frame, placeholder_text="貼上 Twitch 直播網址...")
        self.url_entry.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="ew")

        self.add_button = customtkinter.CTkButton(add_frame, text="新增", width=60, command=self.add_streamer_from_url)
        self.add_button.grid(row=0, column=1, padx=(5, 10), pady=10)

        self.streamers_frame = customtkinter.CTkScrollableFrame(self, label_text="監控列表")
        self.streamers_frame.grid(row=2, column=0, padx=20, pady=(10, 0), sticky="nsew")
        self.streamers_frame.grid_columnconfigure(0, weight=1)

        browser_frame = customtkinter.CTkFrame(self)
        browser_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        browser_frame.grid_columnconfigure((0, 1), weight=1)

        browser_button = customtkinter.CTkButton(browser_frame, text="設定開啟的瀏覽器", command=self.select_browser)
        browser_button.grid(row=0, column=0, padx=(0, 5), pady=5, sticky="ew")

        clear_browser_button = customtkinter.CTkButton(browser_frame, text="重設為預設瀏覽器", command=self.clear_browser_setting, fg_color="transparent", border_width=1, text_color=("gray10", "#DCE4EE"))
        clear_browser_button.grid(row=0, column=1, padx=(5, 0), pady=5, sticky="ew")

        user_data_button = customtkinter.CTkButton(browser_frame, text="設定個人資料路徑", command=self.select_user_data_dir)
        user_data_button.grid(row=1, column=0, columnspan=2, pady=5, sticky="ew")

        self.browser_status_label = customtkinter.CTkLabel(browser_frame, text="", text_color="green")
        self.browser_status_label.grid(row=2, column=0, columnspan=2, pady=(0, 5), sticky="ew")

        self.status_label = customtkinter.CTkLabel(self, text="正在初始化...", text_color="gray")
        self.status_label.grid(row=4, column=0, padx=20, pady=(5, 10), sticky="ew")

    def run_background_tasks(self):
        logging.info("背景任務執行緒已啟動。")
        self.tray_icon = self.setup_tray()
        logging.info("系統匣圖示已設定。")
        threading.Thread(target=self.stream_check_loop, daemon=True).start()
        self.tray_icon.run()
        logging.info("系統匣圖示 run() 已結束。")

    def setup_tray(self):
        try:
            image = Image.open(self.icon_path)
        except (FileNotFoundError, AttributeError):
            width, height, color1, color2 = 64, 64, (145, 70, 255), (255, 255, 255)
            image = Image.new('RGB', (width, height), color2)
            dc = ImageDraw.Draw(image)
            dc.rectangle((width // 4, height // 4, width * 3 // 4, height * 3 // 4), fill=color1)
        
        menu = (pystray.MenuItem('顯示', self.show_window, default=True), pystray.MenuItem('結束', self.quit_app))
        icon = pystray.Icon("TwitchChecker", image, "Twitch 直播監控", menu)
        return icon

    def show_window(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def hide_to_tray(self):
        self.withdraw()

    def quit_app(self):
        logging.info("收到關閉應用程式的請求。")
        print("正在關閉應用程式...")
        self.running = False
        if self.tray_icon:
            self.tray_icon.stop()

        # 建立要關閉的 streamer 列表的副本，以避免在迭代時修改字典
        streamers_to_close = list(self.webdriver_instances.keys())
        for streamer in streamers_to_close:
            self.close_webdriver(streamer)

        self.quit()

    def redraw_streamer_list(self):
        for widget in self.streamers_frame.winfo_children():
            widget.destroy()
        self.streamer_widgets = {}

        for streamer in self.streamers_to_watch:
            streamer_frame = customtkinter.CTkFrame(self.streamers_frame)
            streamer_frame.pack(pady=2, padx=5, fill="x")
            streamer_label = customtkinter.CTkLabel(streamer_frame, text=streamer, anchor="w")
            streamer_label.pack(side="left", padx=(10, 0), expand=True, fill="x")
            controls_frame = customtkinter.CTkFrame(streamer_frame, fg_color="transparent")
            controls_frame.pack(side="right", padx=(0, 5))
            status_label = customtkinter.CTkLabel(controls_frame, text="--", text_color="gray", width=60)
            status_label.grid(row=0, column=0, padx=5)
            auto_open_switch = customtkinter.CTkSwitch(controls_frame, text="", width=0, command=lambda s=streamer: self.toggle_auto_open(s))
            if self.auto_open_states.get(streamer, True):
                auto_open_switch.select()
            auto_open_switch.grid(row=0, column=1, padx=5)
            delete_button = customtkinter.CTkButton(controls_frame, text="X", width=25, fg_color="transparent", text_color=("gray10", "#DCE4EE"), hover_color=("#d9534f", "#d9534f"), command=lambda s=streamer: self.delete_streamer(s))
            delete_button.grid(row=0, column=2, padx=(5, 0))
            self.streamer_widgets[streamer] = {'status': status_label}

    def add_streamer_from_url(self):
        url = self.url_entry.get()
        match = re.search(r'twitch\.tv/(\w+)', url.lower())
        if not match:
            print(f"無效的 Twitch URL: {url}")
            return
        streamer_name = match.group(1)
        self.url_entry.delete(0, 'end')
        if streamer_name in self.streamers_to_watch:
            print(f"直播主 {streamer_name} 已在監控列表中。")
            return
        self.streamers_to_watch.append(streamer_name)
        self.auto_open_states[streamer_name] = True
        self.save_config()
        self.redraw_streamer_list()

    def delete_streamer(self, streamer_to_delete):
        self.streamers_to_watch.remove(streamer_to_delete)
        self.auto_open_states.pop(streamer_to_delete, None)
        # 正確地關閉 webdriver 實例
        self.close_webdriver(streamer_to_delete)
        self.save_config()
        self.redraw_streamer_list()

    def toggle_auto_open(self, streamer):
        self.auto_open_states[streamer] = not self.auto_open_states.get(streamer, True)
        self.save_config()

    def select_browser(self):
        filepath = filedialog.askopenfilename(title="選擇瀏覽器執行檔", filetypes=(("Application", "*.exe"), ("All files", "*.*")))
        if filepath:
            self.browser_path = filepath
            self.config['browser_path'] = filepath
            self.save_config()
            self.show_temporary_message(self.browser_status_label, "儲存成功！")

    def clear_browser_setting(self):
        self.browser_path = None
        self.config['browser_path'] = None
        self.save_config()
        self.show_temporary_message(self.browser_status_label, "已重設為預設瀏覽器。")

    def select_user_data_dir(self):
        dir_path = filedialog.askdirectory(title="選擇 Chrome 個人資料資料夾")
        if dir_path:
            self.user_data_dir = dir_path
            self.config['user_data_dir'] = dir_path
            self.save_config()
            self.show_temporary_message(self.browser_status_label, f"個人資料路徑已設定！")
            logging.info(f"使用者設定檔路徑已更新為: {dir_path}")

    def save_config(self):
        self.config['streamers'] = self.streamers_to_watch
        self.config['browser_path'] = self.browser_path
        self.config['user_data_dir'] = self.user_data_dir
        self.config['auto_open_settings'] = self.auto_open_states
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except IOError as e:
            print(f"儲存設定檔時發生錯誤: {e}")

    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            return {}
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            print(f"讀取或解析設定檔時發生錯誤: {e}")
            return {}

    def get_new_token(self):
        if not self.client_id or not self.client_secret:
            return None
        url = f"https://id.twitch.tv/oauth2/token?client_id={self.client_id}&client_secret={self.client_secret}&grant_type=client_credentials"
        try:
            response = requests.post(url, timeout=10)
            response.raise_for_status()
            return response.json()['access_token']
        except requests.exceptions.RequestException as e:
            print(f"獲取 Token 失敗: {e}")
            return None

    def stream_check_loop(self):
        logging.info("直播檢查迴圈已啟動。")
        while self.running:
            if not self.token:
                self.token = self.get_new_token()
                if not self.token:
                    self.after(0, self.update_status_label, "獲取Token失敗, 10秒後重試...")
                    logging.warning("獲取 Token 失敗，10秒後重試...")
                    time.sleep(10)
                    continue

            headers = {'Client-ID': self.client_id, 'Authorization': f'Bearer {self.token}'}
            live_streamers = set()
            logging.info(f"開始檢查 {len(self.streamers_to_watch)} 位直播主狀態...")

            for streamer in self.streamers_to_watch:
                if not self.running: return
                url = f'https://api.twitch.tv/helix/streams?user_login={streamer}'
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        if response.json().get('data'):
                            live_streamers.add(streamer)
                            logging.info(f"API 檢查: {streamer} 在線。")
                    elif response.status_code == 401:
                        self.token = None
                        logging.warning("Token 失效，將在下次迴圈重新獲取。")
                        break
                except requests.exceptions.RequestException as e:
                    logging.error(f"檢查 {streamer} 時網路錯誤: {e}")
                    print(f"檢查 {streamer} 時網路錯誤: {e}")
                time.sleep(0.5)
            
            logging.info(f"檢查完成。在線列表: {live_streamers}")
            self.after(0, self.update_ui_with_results, live_streamers)

            for i in range(self.check_interval, 0, -1):
                if not self.running: return
                self.after(0, self.update_status_label, f"下次更新在 {i} 秒後")
                time.sleep(1)

    def update_ui_with_results(self, live_streamers):
        for streamer, widgets in self.streamer_widgets.items():
            if streamer in live_streamers:
                widgets['status'].configure(text="在線", text_color="#1DB954")
                if self.auto_open_states.get(streamer, True):
                    # 總是嘗試呼叫 open_stream。該函式內部會處理重複開啟和手動關閉後重新開啟的情況。
                    logging.info(f"UI 更新: {streamer} 在線，觸發開啟/檢查程序。")
                    threading.Thread(target=self.open_stream, args=(streamer,), daemon=True).start()
                else:
                    logging.info(f"UI 更新: {streamer} 在線，但自動開啟為關閉狀態。")
            else:
                widgets['status'].configure(text="離線", text_color="gray")
                if streamer in self.webdriver_instances:
                    threading.Thread(target=self.close_webdriver, args=(streamer,), daemon=True).start()

    def find_free_port(self):
        """Finds a free port on localhost."""
        with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.bind(('', 0))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return s.getsockname()[1]

    def find_chrome_executable(self):
        """Tries to find the Chrome executable in common locations."""
        candidates = [
            "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google\\Chrome\\Application\\chrome.exe")
        ]
        for path in candidates:
            if os.path.exists(path):
                print(f"找到 Chrome 執行檔: {path}")
                return path
        return None

    def close_webdriver(self, streamer):
        if streamer in self.webdriver_instances:
            instance = self.webdriver_instances.get(streamer)
            driver = instance.get('driver')
            process = instance.get('process')

            try:
                if driver:
                    driver.quit()
            except WebDriverException as e:
                # This can happen if the browser was already closed manually. It's not a critical error.
                logging.warning(f"關閉 {streamer} 的 driver 時發生預期內的錯誤 (可能已手動關閉): {e.msg}")
                print(f"關閉 {streamer} 的 driver 時發生預期內的錯誤 (可能已手動關閉): {e.msg}")
            except Exception as e:
                logging.error(f"關閉 {streamer} 的 driver 時發生非預期的錯誤: {e}")
                print(f"關閉 {streamer} 的 driver 時發生非預期的錯誤: {e}")

            try:
                if process and process.poll() is None:
                    logging.info(f"正在終止 {streamer} 的瀏覽器程序 (PID: {process.pid})...")
                    print(f"正在終止 {streamer} 的瀏覽器程序...")
                    process.terminate()
                    process.wait(timeout=5)  # Wait for the process to terminate
            except Exception as e:
                logging.error(f"終止 {streamer} 的 process 時發生錯誤: {e}")
                print(f"終止 {streamer} 的 process 時發生錯誤: {e}")

            # After attempting cleanup, remove the key.
            self.webdriver_instances.pop(streamer, None)
            logging.info(f"已從 webdriver_instances 移除 {streamer} 並完成資源清理。")
            print(f"已完成 {streamer} 的資源清理程序。")

    def open_stream(self, streamer):
        # 檢查是否有正在開啟的鎖，防止重複進入
        if self.opening_stream_locks.get(streamer):
            print(f"正在處理 {streamer} 的視窗，請稍候...")
            return

        # 1. 檢查是否有一個看似活躍的實例
        if streamer in self.webdriver_instances:
            instance = self.webdriver_instances[streamer]
            driver = instance.get('driver')
            if driver:
                try:
                    _ = driver.window_handles
                    print(f"{streamer} 的直播視窗已在運行中，無需重複開啟。")
                    return
                except Exception as e:
                    logging.warning(f"檢測到 {streamer} 的瀏覽器實例可能已關閉 ({type(e).__name__})，將重新開啟。")
                    print(f"檢測到 {streamer} 的瀏覽器實例可能已關閉 ({type(e).__name__})，將重新開啟。")
                    self.close_webdriver(streamer)

        # 2. 如果程式執行到這裡，代表需要開啟一個全新的瀏覽器實例
        try:
            # 上鎖，表示我們開始處理這個 streamer
            self.opening_stream_locks[streamer] = True
            
            port = self.find_free_port()
            print(f"為 {streamer} 找到可用偵錯埠: {port}")
            
            chrome_path = self.browser_path or self.find_chrome_executable()
            if not chrome_path or not os.path.exists(chrome_path):
                logging.error("找不到 Chrome.exe，請在設定中指定正確的路徑。")
                raise Exception("找不到 Chrome.exe，請在設定中指定正確的路徑。")

            # --- 設定使用者設定檔路徑 ---
            if not self.user_data_dir:
                # 如果未設定，則在程式目錄下建立一個預設的
                default_dir = os.path.join(os.getcwd(), "chrome_profile")
                os.makedirs(default_dir, exist_ok=True)
                self.user_data_dir = default_dir
                self.config['user_data_dir'] = self.user_data_dir # 更新實例中的設定
                self.save_config() # 儲存起來供下次使用
            logging.info(f"使用個人資料路徑: {self.user_data_dir}")

            options = uc.ChromeOptions()
            # 不需要手動設定 binary_location，uc 會自動尋找
            options.add_argument(f'--user-data-dir={self.user_data_dir}')
            options.add_argument("--autoplay-policy=no-user-gesture-required")
            options.add_argument("--mute-audio") # 保持靜音啟動

            # 使用 undetected_chromedriver 啟動
            # 使用 webdriver-manager 來取得正確的驅動程式路徑
            driver_path = ChromeDriverManager().install()

            # 傳入瀏覽器和驅動程式的路徑，確保版本完全匹配
            driver = uc.Chrome(
                browser_executable_path=chrome_path,
                driver_executable_path=driver_path,
                options=options, 
                port=port
            )
            logging.info(f"已為 {streamer} 成功建立新的 WebDriver 實例。")
            
            self.webdriver_instances[streamer] = {'driver': driver, 'process': None}
            logging.info(f"{streamer} 已加入 webdriver_instances。")
            
            url = f"https://www.twitch.tv/{streamer}"
            driver.get(url)
            
            # 處理內容警告頁面
            try:
                mature_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-a-target='player-overlay-mature-accept']"))
                )
                print(f"檢測到內容警告，正在為 {streamer} 點擊 '開始觀看'...")
                mature_button.click()
                time.sleep(1)
            except TimeoutException:
                print(f"未在 {streamer} 頁面找到內容警告按鈕。")

            # 2. 檢查並取消直播靜音
            try:
                # 等待 video 元素載入
                video_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, 'video'))
                )
                
                # 使用 JavaScript 檢查是否靜音
                is_muted = driver.execute_script("return arguments[0].muted;", video_element)
                logging.info(f"檢查 {streamer} 直播，靜音狀態: {is_muted}")
                print(f"檢查 {streamer} 直播，靜音狀態: {is_muted}")

                if is_muted:
                    logging.info(f"{streamer} 的直播是靜音的，將執行取消靜音。")
                    print(f"{streamer} 的直播是靜音的，將執行取消靜音。")
                    # 使用 JavaScript 直接取消靜音並設定音量，更可靠
                    driver.execute_script("arguments[0].muted = false; arguments[0].volume = 0.5;", video_element)
                    
                    # 再次檢查以確認
                    time.sleep(0.5) # 給點時間讓狀態更新
                    new_is_muted = driver.execute_script("return arguments[0].muted;", video_element)
                    if not new_is_muted:
                        logging.info(f"已成功為 {streamer} 取消靜音。")
                        print(f"已成功為 {streamer} 取消靜音。")
                    else:
                        logging.warning(f"嘗試為 {streamer} 取消靜音後，仍處於靜音狀態。")
                        print(f"警告：嘗試為 {streamer} 取消靜音後，仍處於靜音狀態。")
                else:
                    logging.info(f"{streamer} 的直播已經是取消靜音狀態。")
                    print(f"{streamer} 的直播已經是取消靜音狀態。")

            except TimeoutException:
                logging.warning(f"在 10 秒內未為 {streamer} 找到 video 元素，無法確認靜音狀態。")
                print(f"警告：未找到 {streamer} 的 video 元素，跳過取消靜音步驟。")
            except Exception as e:
                logging.error(f"為 {streamer} 自動取消靜音時發生未知錯誤: {e}")
                print(f"錯誤：在為 {streamer} 自動取消靜音時發生錯誤: {e}")

            self.after(0, self.update_status_label, f"已開啟 {streamer} 的直播")

        except Exception as e:
            print(f"開啟 {streamer} 直播時發生未知錯誤: {e}")
            self.after(0, self.update_status_label, f"錯誤: 開啟 {streamer} 直播失敗")
            self.close_webdriver(streamer)
        
        finally:
            # 無論成功或失敗，最後都要解鎖
            if streamer in self.opening_stream_locks:
                del self.opening_stream_locks[streamer]

    def close_webdriver(self, streamer):
        if streamer in self.webdriver_instances:
            instance = self.webdriver_instances.pop(streamer, None)
            if instance:
                driver = instance.get('driver')
                if driver:
                    try:
                        driver.quit()
                        logging.info(f"已成功關閉 {streamer} 的 WebDriver。")
                    except Exception as e:
                        logging.error(f"關閉 {streamer} 的 WebDriver 時發生錯誤: {e}")
                        print(f"關閉 {streamer} 視窗時發生錯誤: {e}")

    def show_temporary_message(self, label, message, color="green", duration=3000):
        label.configure(text=message, text_color=color)
        label.after(duration, lambda: label.configure(text=""))

    def update_status_label(self, text):
        self.status_label.configure(text=text)

if __name__ == '__main__':
    # 設定日誌記錄
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s',
        handlers=[
            logging.FileHandler('app.log', encoding='utf-8', mode='w'), # 寫入檔案，每次重新執行時覆蓋
            logging.StreamHandler() # 顯示在終端機
        ]
    )

    if not os.path.exists(CONFIG_FILE):
        print(f"錯誤：找不到設定檔 {CONFIG_FILE}。請先建立並設定好檔案。")
    else:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        if 'YOUR_CLIENT_ID' in config.get('client_id', '') or 'YOUR_CLIENT_SECRET' in config.get('client_secret', ''):
            print("錯誤：請先在 config.json 中設定您的 Client ID 和 Client Secret。")
        else:
            app = TwitchApp()
            app.mainloop()
