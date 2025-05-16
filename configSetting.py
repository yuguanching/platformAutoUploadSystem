import os
import configSetting
import sys
import telepot
import multiprocessing as mp
from ioService import reader
from webManager import webDriver
from typing import Union
from datetime import datetime, timedelta
from configparser import ConfigParser

cfg = ConfigParser()

# ---------- input settings ----------
# 輸入資料與客製相關設定檔
if getattr(sys, "frozen", False):
    ROOT_PATH = os.path.dirname(sys.executable)
    EXE_PATH = os.path.dirname(sys.path[0])
    print(f"EXE_PATH from file: {EXE_PATH}")
    print(f"RootPath from file: {ROOT_PATH}")
    cfg.read(EXE_PATH + "/secret.ini", encoding="utf-8")
else:
    ROOT_PATH = os.path.dirname(os.path.realpath(sys.argv[0]))
    EXE_PATH = ROOT_PATH
    print(f"RootPath from system execute: {ROOT_PATH}")
    cfg.read(ROOT_PATH + "/secret.ini", encoding="utf-8")

# 上傳平台的相關資訊
upload_account_dict = {}
discover_platform = "臉書"
accounts = configSetting.cfg.get("UploadPlatform", "ACCOUNT").split(",")
passwords = configSetting.cfg.get("UploadPlatform", "PASSWORD").split(",")
for account, password in zip(accounts, passwords):
    upload_account_dict[account] = {
        "account": account,
        "password": password
    }
upload_platform_url = configSetting.cfg.get("UploadPlatform", "URL")
upload_platform_input_url = configSetting.cfg.get("UploadPlatform", "UPLOAD_INPUT_URL")

json_array_data = reader.readInputJson(target_file=f"{ROOT_PATH}/config/input.json")
inspect_data = reader.readInputJson(target_file=f"{ROOT_PATH}/config/inspect.json")
feedback_manual = False
output_root = f"{ROOT_PATH}/output/粉專/"

sp_time = datetime.strptime("2010-01-01 00:00:00", "%Y-%m-%d %H:%M:%S")

# Line Chat Bot 資訊
line_bot_group_id = configSetting.cfg.get("LineChatBot", "GROUP_ID")
line_bot_access_token = configSetting.cfg.get("LineChatBot", "ACCESS_TOKEN")
line_bot_channel_secret = configSetting.cfg.get("LineChatBot", "CHANNEL_SECRET")

# Telegram Bot 資訊
telegram_bot_token = configSetting.cfg.get("TelegramBot", "ACCESS_TOKEN")
telegram_bot_group_id = configSetting.cfg.get("TelegramBot", "GROUP_ID")
telegram_bot = telepot.Bot(telegram_bot_token)

# ---------- input settings ----------


# ---------- tasks settings ----------
# 根據輸入資料的多寡決定執行程序的個數
input_data_num = len(json_array_data["targets"])
process_worker = 1
if input_data_num >= 1 and input_data_num <= 4:
    process_worker = input_data_num
elif input_data_num >= 4 and input_data_num <= 500:
    process_worker = mp.cpu_count() // 4
else:
    process_worker = os.cpu_count()

# 多執行緒任務中統計進行中數量時每隔多少進行一次顯示
queue_show_interval = 50
multithread_median = 100
multithread_high = 200

# 圖片截圖開關
need_image_record = True

# ---------- tasks settings ----------


# ---------- connections settings ----------
# 發起request若出現異常的重試次數
retry = 3
retry_feedback = 5

# 連線出現延遲時的等待時間
timeout = 10
timeout_feedback = 60
timeout_async = 60

# 冷卻時間:是否可以關閉proxy使用一次本機公網ip呼叫(單位是秒)
cooldown_timedelta = 60
# 發生任何例外錯誤的容忍次數(使用一次本機公網IP後會重新計數)
exception_max_try = 100

# ---------- connections settings ----------


# ---------- webDriver settings ----------
# 爬蟲相關行為使用的瀏覽器是否要在背景執行
need_headless = True

# 分享行為截圖要截前幾名
screenshot_count = 3
screenshot_article_count = 10

# 隱式等待時間
implicitly_wait = 20

# 所有類型的webDriver type
allDriverType = Union[
    webDriver.postsDriver,
    webDriver.feedbackDriver,
]
# ---------- webDriver settings ----------


# ---------- proxy settings ----------
# 抓取proxy ip 時取回的數量, 限制抓取一定數量的可用proxy
valid_proxy_ip_len = 7

# 抓回來使用的prxoy_ip_list 全部失效後的重試次數
proxy_try_count = 3
# ---------- proxy settings ----------


# -----------parse setting -------------

fetch_inteval = timedelta(hours=8, minutes=0)

check_alive_deadline = 3
check_alive_batch = 8
check_alive_sleep = 3600