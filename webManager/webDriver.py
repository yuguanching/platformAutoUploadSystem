import os
import random
import time
import traceback
import configSetting

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webelement import WebElement
from typing import Union
from abc import ABC, abstractmethod
from webManager import customWait
from ioService import writer
from helper import Auxiliary


# 關閉web driver的log訊息
os.environ["WDM_LOG_LEVEL"] = "0"


# 有新的driver建立時要去configSetting.py登記型別


class customWebDriver(ABC):

    def __init__(self, driver=None, options=None, isLogin=False):
        """初始化driver實體,預設為未登入狀態."""

        self.driver = driver
        self.options = options
        self.loginURL = "https://www.facebook.com"
        self.isLogin = isLogin

    def setOptions(self, needImage, needHeadless):
        """設定模擬瀏覽器的設定參數.
        Args:
            needImage: 是否需要在加載頁面時載入圖片
            needHeadless: 是否要以無頭模式於背景執行
        """

        self.options = Options()
        # 避開彈跳視窗以免爬蟲被干擾
        self.options.add_argument("--disable-notifications")
        # 開啟無痕模式(有助於登入)
        self.options.add_argument("--incognito")

        # self.options.add_argument("--user-data-dir=D:\\我的資料夾\\文件\\fbCrawler\\.profile")
        # self.options.add_argument("--profile-directory=jerry")

        self.options.add_argument("--window-size=1920,1080")
        # 設定運行時的語系
        self.options.add_argument("--lang=zh-tw")
        # options.add_experimental_option('prefs', {'intl.accept_languages': 'en,en_US'})
        # 屏蔽部分警告型log
        self.options.add_experimental_option("useAutomationExtension", False)
        self.options.add_experimental_option("excludeSwitches", ['enable-logging', 'enable-automation'])
        # docker原本的分享記憶體在 /dev/shm 是 64MB，會造成chrome crash，所以要改成寫入到 /tmp
        self.options.add_argument("--disable-dev-shm-usage")
        # 以最高權限運行
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-setuid-sandbox")
        self.options.add_argument("--log-level=3")
        # google document 提到需要加上這個屬性來規避 bug
        self.options.add_argument("--disable-gpu")
        # 不加载图片, 提升速度(有操作截圖功能的話需要打開)
        
        # 2025-05-01 遇到的問題:機器本身沒有GPU,所以無法使用GPU加速,進而噴錯
        self.options.add_argument('--enable-unsafe-webgpu') # 避免 fallback 出錯（可選）
        self.options.add_argument('--enable-unsafe-swiftshader') # 避免 fallback 出錯（可選）
        
        if needImage:
            self.options.add_argument("blink-settings=imagesEnabled=false")
        if needHeadless:
            self.options.add_argument("--headless=new")

    def driverInitialize(self, driver = None):
        """
        建立啟動器,失敗時則重試到成功建立為止
        若有已存在的啟動器餵進來,則直接植入當前物件的屬性中
        """
        try:
            self.driver = None
            if driver is not None:
                self.driver = driver
            else:
                while True:
                    try:
                        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=self.options)
                        if self.driver is not None:
                            break  
                    except:
                        self.driver = None
                        continue
        finally:
            # 清掉暫存
            self.driver.implicitly_wait(configSetting.implicitly_wait)
            self.driver.delete_all_cookies()

    def login(self, accountCounter):
        """執行登入動作.
        Args:
            accountCounter: 當前是使用第幾組帳密做登入
        """
        username_list = configSetting.json_array_data["user"]["account"]
        password_list = configSetting.json_array_data["user"]["password"]
        account = username_list[accountCounter]
        pwd = password_list[accountCounter]
        print("開始登入,身分 :", account)
        url = self.loginURL
        self.driver.get(url)

        # 輸入賬號密碼
        WebDriverWait(self.driver, 30).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="email"]'))
        )
        elem = self.driver.find_element(By.ID, "email")
        elem.send_keys(account)

        elem = self.driver.find_element(By.ID, "pass")
        elem.send_keys(pwd)

        elem.send_keys(Keys.RETURN)

        print("登入完成")
        time.sleep(1)
        return

    def clearDriver(self):
        """清除啟動器,回收相關資源."""

        if self.driver is not None:
            self.driver.close()
            self.driver.quit()
            self.driver = None
        self.isLogin = False
        time.sleep(5)
        return

    @abstractmethod
    def _getSource(self):
        """抽象方法,待定義取得爬蟲資訊的手法."""
        pass


class uploadPlatformDriver(customWebDriver):

    def __init__(self, driver=None, options=None, isLogin=False):
        super().__init__(driver, options, isLogin)
        self.loginURL = configSetting.upload_platform_url
        self.account_name = ""

    def set_account_name(self, account_name:str):
        self.account_name = account_name

    def login(self):

        print(f"進入上傳平台，開始登入帳號: {self.account_name}")
        self.driver.get(self.loginURL)
        time.sleep(2)
        account_element = self.driver.find_element(
            By.XPATH,
            "//input[@class='form-control ng-untouched ng-pristine ng-invalid' and @id='floatingInput']",
        )
        account_element.send_keys(configSetting.upload_account_dict[self.account_name]["account"])

        password_element = self.driver.find_element(
            By.XPATH,
            "//input[@class='form-control ng-untouched ng-pristine ng-invalid' and @id='floatingPassword']",
        )
        password_element.send_keys(configSetting.upload_account_dict[self.account_name]["password"])

        time.sleep(2)
        sign_btn_element = self.driver.find_element(
            By.XPATH, "//button[@class='w-100 btn btn-lg btn-primary']"
        )
        sign_btn_element.click()
        time.sleep(2)
        print(f"{self.account_name}: 上傳平台登入完成")

    def _getSource(self, record: dict, path: str):
        upload_url = configSetting.upload_platform_input_url
        time_pause = 2
        self.driver.get(upload_url)
        self.driver.refresh()
        timeout = WebDriverWait(self.driver, 20)
        time.sleep(time_pause)

        content = record["內容"]
        discover_platform = configSetting.discover_platform
        # 為了不觸發chromedriver上傳文案時，對utf8字節>4不支援一事，進行清理，但excel中保留原文
        content = Auxiliary.clear_four_bytes_utf8(content)
        link = record["文章網址"]
        main_account = record["粉專名稱"]
        effect_topic = record["影響標的"]
        accosiate_department = record["事涉部門"]
        accosiate_media = f"{effect_topic}"
        local_img_link = f"{path}/img/{str(record['文章id'])}.png"
        main_content_area_element = self.driver.find_element(
            By.XPATH,
            "//textarea[@id='ReportContent']",
        )
        try:
            main_content_area_element.send_keys(content)
        except Exception as e:
            writer.writeLogToFile(f"疑似有上傳內容的非法格式: {content}", isError=True)
            raise e

        link_element = self.driver.find_element(
            By.XPATH,
            "//input[@id='PostLink']",
        )
        link_element.send_keys(link)

        main_account_name_element = self.driver.find_element(
            By.XPATH,
            "//input[@id='PostAccountinput']",
        )
        main_account_name_element.send_keys(main_account)

        accosiate_media_element = self.driver.find_element(
            By.XPATH,
            "//input[@id='TitleInput']",
        )
        accosiate_media_element.send_keys(accosiate_media)

        effect_topic_select = Select(
            self.driver.find_element(
                By.XPATH,
                "//select[@id='inputInfluenceSelect']",
            )
        )
        effect_topic_select.select_by_visible_text(effect_topic)

        accosiate_department_select = Select(
            self.driver.find_element(
                By.XPATH,
                "//select[@id='inputDepartmentSelect' and @formcontrolname='ReportDepartment']",            
            )
        )
        accosiate_department_select.select_by_visible_text(accosiate_department)

        discover_platform_select = Select(
            self.driver.find_element(
                By.XPATH,
                "//select[@id='inputDepartmentSelect' and @formcontrolname='ReportPlatform']",
            )
        )
        discover_platform_select.select_by_visible_text(discover_platform)

        # try:
        #     image_upload_element = self.driver.find_element(By.XPATH, "//input[@id='ScreenShotImageInput']")
        #     image_upload_element.send_keys(os.path.abspath(local_img_link))
        # except:
        #     print(f"貼文: {record['文章id']} 沒有找到對應圖片，請至log檔確認原因")
        #     writer.writeLogToFile(traceback.format_exc(), True)
        time.sleep(5)
        submit_element: WebElement = timeout.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[@id='modalSubmitBotton' and @type='submit']")
            )
        )
        time.sleep(time_pause)
        submit_element.click()
        time.sleep(time_pause)

        double_check_element: WebElement = timeout.until(
            EC.element_to_be_clickable((By.XPATH, "//button[@class='btn btn-primary']"))
        )
        double_check_element.click()
        time.sleep(time_pause)


class postsDriver(customWebDriver):
    """取得文章與使用者相關docid資源的driver"""

    def _getSource(self, pageURL):
        time_pause = 3
        self.driver.get(pageURL)

        time.sleep(time_pause)
        self.driver.refresh()
        time.sleep(time_pause)

        resp = self.driver.page_source

        time.sleep(time_pause)
        return resp


class feedbackDriver(customWebDriver):
    """取得分享行為相關docid資源的driver"""

    def _getSource(self, pageURL):
        print("開始動態加載feedback要用的js")
        time_pause = 2
        new_source = ""
        self.driver.get(pageURL)
        temp = []
        try:
            for x in range(1, 5):
                try:
                    self.driver.execute_script(
                        "window.scrollTo(0,document.body.scrollHeight)"
                    )
                    temp = WebDriverWait(self.driver, 5).until(
                        customWait.scrollWait(
                            '//div[@class="x1yztbdb x1n2onr6 xh8yej3 x1ja2u2z"]',  # 每一篇文章的開頭層級
                            temp,
                            x,
                        )
                    )
                except:
                    break
            article_locator = (
                By.XPATH,
                "//div[@class='x1yztbdb x1n2onr6 xh8yej3 x1ja2u2z']",
            )
            article_start_point = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located(article_locator)
            )

            for asp in article_start_point:

                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center', inline: 'center'});",
                    asp,
                )

                share_point_locator = (
                    By.XPATH,
                    ".//div[@class='x1n2onr6']//descendant::span[@class='x4k7w5x x1h91t0o x1h9r5lt x1jfb8zj xv2umb2 x1beo9mf xaigb6o x12ejxvf x3igimt xarpa2k xedcshv x1lytzrv x1t2pt76 x7ja8zs x1qrby5j']",
                )
                try:
                    share_list_point = WebDriverWait(asp, 5).until(
                        EC.presence_of_all_elements_located(share_point_locator)
                    )
                except:
                    print("搜索其他文章來觸發分享節點的js")
                    continue

                time.sleep(random.randint(1, 3))
                if len(share_list_point) <= 0:
                    print("搜索其他文章來觸發分享節點的js")
                    continue
                else:
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center', inline: 'center'});",
                        share_list_point[0],
                    )
                    text_check = ""
                    has_share_text = False
                    for slp in share_list_point:
                        text_check = slp.text
                        if "分享" in text_check:
                            has_share_text = True
                        hover = ActionChains(self.driver).move_to_element(slp)
                        hover.perform()
                        time.sleep(time_pause)

                    if not has_share_text:
                        print(
                            "鎖定的文章只有留言節點,沒有分享節點,無法觸發js加載,搜索其他文章來觸發分享節點的js"
                        )
                        continue
                    new_source = self.driver.page_source
                    break
        except Exception as e:
            print("動態加載feedback js 發生錯誤: ", str(e))
            print(
                "粉專沒有抓到分享者加載的js,可能是網頁失效或是登入帳號失效導致,直接回傳空字串"
            )
            time.sleep(time_pause)
            return new_source

        if len(new_source) > 0:
            print("粉專有抓到分享者加載的js")
        else:
            print("粉專沒有抓到分享者加載的js,回傳空字串")
        # driver.close()
        time.sleep(time_pause)
        return new_source


class screenshotDriver(customWebDriver):
    """擷取分享者或被分享者頁面
    Args:
        driver: 啟動器
        url: 目標網址
        subDir: 當前目標的資料夾名稱

    Cautions: 跑截圖的時候請勿晃動畫面,以免截到錯誤的畫面
    """

    def _getSource(self, url, postID, subDir) -> bool:
        try:
            self.driver.get(url)
        except Exception as e:
            print(f"截圖 {postID} 失敗，url: {url} 連線失敗, 錯誤訊息: {e}")
            return False
        time.sleep(3)
        path = ""
        current_url = self.driver.current_url

        try:
            jump_dialog_exit_locator = (By.XPATH, "//div[@class='x1n2onr6 x1ja2u2z x1afcbsf x78zum5 xdt5ytf x1a2a7pz x6ikm8r x10wlt62 x71s49j x1jx94hy x1qpq9i9 xdney7k xu5ydu1 xt3gfkd x104qc98 x1g2kw80 x16n5opg xl7ujzl xhkep3z x193iq5w' and @role='dialog']/child::div[@class='x92rtbv x10l6tqk x1tk7jg1 x1vjfegm']/child::div")
            jel_element = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located(jump_dialog_exit_locator))
            jel_element.click()
            time.sleep(2)
        except:
            print("no jump")
            pass
        path = f"{subDir}/img/{str(postID)}.png"
        if "video" in current_url or "watch" in current_url:  # 抓影片的類型
            if "live" in current_url:
                locator = (
                    By.XPATH,
                    "//div[@class='x78zum5 x5yr21d xl56j7k xh8yej3']",
                )
            else:
                locator = (
                    By.XPATH,
                    "//div[@class='x78zum5 xkrivgy x1gryazu x4pn7vq']",
                )
        elif "reel" in current_url:  # 抓短影音的類型
            locator = (
                By.XPATH,
                "//div[@class='xjbqb8w x1lq5wgf xgqcy7u x30kzoy x9jhf4c x78zum5 x1q0g3np xod5an3 x14vqqas x6ikm8r x10wlt62 x1n2onr6 x1k90msu x6o7n8i x9lcvmn x1m6m0jg']",
            )
        elif "group" in current_url:  # 抓社團的類型
            locator = (
                By.XPATH,
                "//div[@class='x1yztbdb x1n2onr6 xh8yej3 x1ja2u2z']",
            )
        else:
            locator = (
                By.XPATH,
                "//div[@class='html-div xdj266r x11i5rnm xat24cr x1mh8g0r xexx8yu x4uap5 x18d9i69 xkhd6sd']/../..",
            )
        try_success = False
        for try_count in range(2, 5):
            try:
                # personal_profile上面的部分截圖
                self.driver.execute_script("window.scrollTo(0,0)")
                time.sleep(2)
                # 統一暫存到img資料夾,因涉及存檔,故加time.sleep
                if "group" in current_url:
                    catch_element = WebDriverWait(self.driver, 20).until(EC.presence_of_all_elements_located(locator))
                    catch_element[0].screenshot(path) # 會是一個list,所以要取[0]
                else:
                    catch_element = WebDriverWait(self.driver, 20).until(EC.presence_of_element_located(locator))
                    catch_element.screenshot(path)
                try_success = True
                print(f"{subDir}: 文章ID:{postID} 截圖完成")
                break
            except:
                writer.writeLogToFile(traceback.format_exc(), True)
                writer.writeLogToFile(f"定位locator: {locator}", True)
                print(f"截圖異常，準備進行第{try_count}嘗試")
                self.driver.refresh()
                time.sleep(3)
                continue

        time.sleep(3)
        if try_success:
            return True
        else:
            print(f"截圖 {postID} 失敗，查看log檔確認原因")
            return False
