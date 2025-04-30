import time
import os
import traceback
import configSetting


from ioService import writer, reader
from helper import Auxiliary
from playwright.sync_api import sync_playwright
from playwright._impl._network import Request as p_request


os.environ['WDM_LOG_LEVEL'] = '0'

# 擷取具有"graphql" subpath的request, 留下其中的帶入參數(for fb_dtsg)


def inspectReq(req: p_request, params: list):
    if "graphql" in req.url:
        params.append(req.post_data_json)


def getCsrfToken():
    print("開始抓取fb_dtsg特徵與c_user、xs")
    cookies = list()
    params = list()
    param_fb_dtsg = dict()
    cookie_xs = dict()
    cookie_cuser = dict()
    input_data = configSetting.json_array_data
    target_url = input_data['targetURL'][0]
    username_list = configSetting.json_array_data['user']['account']
    password_list = configSetting.json_array_data['user']['password']
    account_number = 0

    while True:
        try:
            with sync_playwright() as p:
                # on: 動態監控接下來某種類型的流量
                # goto: 同一個分頁跳去其他網址
                browser = p.chromium.launch(headless=True)
                context = browser.new_context()
                page = context.new_page()
                page.on("request", lambda request: inspectReq(request, params))
                page.goto("https://www.facebook.com")
                page.get_by_test_id("royal_email").click()
                page.get_by_test_id("royal_email").fill(username_list[account_number])
                page.get_by_test_id("royal_pass").click()
                page.get_by_test_id("royal_pass").fill(password_list[account_number])
                page.get_by_test_id("royal_login_button").click()
                time.sleep(3)
                page.goto(target_url)
                time.sleep(3)
                cookies = context.cookies()
                # ---------------------
                page.close()
                context.close()
                browser.close()
                break

        except Exception as e:
            print("特徵抓取失敗,重試")
            writer.writeLogToFile(e, True)
            account_number += 1
            if account_number >= len(username_list):
                account_number = 0
            continue

    for param in params:
        if 'fb_dtsg' in param:
            param_fb_dtsg = param
            break
    for cookie in cookies:
        if cookie['name'] == 'xs':
            cookie_xs = cookie
        if cookie['name'] == 'c_user':
            cookie_cuser = cookie

    return param_fb_dtsg, cookie_xs, cookie_cuser


if __name__ == "__main__":
    getCsrfToken()
