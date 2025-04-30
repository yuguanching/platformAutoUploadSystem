import time

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By


# 自定義的webDriverWait,在滾動時使用,確認若滾動已產生新的資料,則繼續滾動,否則等待
class scrollWait:

    def __init__(self, locator, oldList, count):
        self._locator = locator
        self._oldList = oldList
        self._count = count

    def __call__(self, driver):
        sleep = (self._count // 10) + 1
        time.sleep(sleep)
        new_list = driver.find_elements(By.XPATH, self._locator)
        if (len(new_list) > len(self._oldList)):
            return new_list
        else:
            return False
