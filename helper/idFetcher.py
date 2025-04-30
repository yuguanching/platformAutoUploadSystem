import requests
import re
import random
import os
import configSetting
import urllib.parse
import httpx
import traceback
from fake_useragent import UserAgent
from typing import Union
from bs4 import BeautifulSoup
from webManager import webDriver
from ioService import writer, reader


def fetchEigenvaluesAndID(
    func, customDriver: configSetting.allDriverType, pageURL, errString, checkOption=2
) -> Union[tuple[str, str, str, bool], tuple[str, str, str, str, str, bool]]:
    # checkOption-> 0: 只檢查id , 1:只檢查docid , 2: 兩個都檢查(預設值為2)
    accounts_len = len(configSetting.json_array_data["user"]["account"])
    account_num = os.environ.get("account_number_now")
    id = ""
    docid = ""
    req_name = ""
    comment_docid = ""
    comment_req_name = ""
    if account_num is None:
        account_num = random.randint(0, accounts_len - 1)
    else:
        account_num = int(account_num)

    # 先檢查登入狀態,若未登入則先完成首次登入
    # 下方的判斷中,只要發現有取不到必要資料的情形,則捨棄當前的driver實體,重新創立一個並重新登入
    if customDriver.isLogin:
        pass
    else:
        customDriver.login(account_num)
        customDriver.isLogin = True

    while True:
        id, docid, req_name, comment_docid, comment_req_name, is_been_banned = func(
            pageURL=pageURL, customDriver=customDriver
        )

        # 若發現該頁面被臉書封鎖,則直接回傳空值與標記,由外部判斷處理
        if is_been_banned:
            break

        match checkOption:
            case 0:
                if id != "":
                    os.environ["account_number_now"] = str(account_num)
                    break
                else:
                    print(errString)
                    account_num += 1
                    if account_num == accounts_len:
                        account_num = 0
                    os.environ["account_number_now"] = str(account_num)
                    customDriver.clearDriver()
                    customDriver.driverInitialize()
                    customDriver.login(account_num)
                    customDriver.isLogin = True
                    continue
            case 1:
                if docid != "":
                    os.environ["account_number_now"] = str(account_num)
                    break
                else:
                    print(errString)
                    account_num += 1
                    if account_num == accounts_len:
                        account_num = 0
                    os.environ["account_number_now"] = str(account_num)
                    customDriver.clearDriver()
                    customDriver.driverInitialize()
                    customDriver.login(account_num)
                    customDriver.isLogin = True
                    continue
            case 2:
                if docid != "" and id != "":
                    os.environ["account_number_now"] = str(account_num)
                    break
                else:
                    print(errString)
                    account_num += 1
                    if account_num == accounts_len:
                        account_num = 0
                    os.environ["account_number_now"] = str(account_num)
                    customDriver.clearDriver()
                    customDriver.driverInitialize()
                    customDriver.login(account_num)
                    customDriver.isLogin = True
                    continue
    return id, docid, req_name, comment_docid, comment_req_name, is_been_banned


def __getDocIDFeedback__(
    pageURL, customDriver: webDriver.feedbackDriver
) -> tuple[str, str, str, str, str, bool]:

    # *部分粉專有鎖年齡與國家,導致只能登入後才能瀏覽,故改用爬蟲登入法取得頁面資料
    print("以selenium的爬蟲登入法取得feedback 的 docid")
    is_been_banned = False
    resp = customDriver._getSource(pageURL=pageURL)

    if ("目前無法查看此內容" in resp) and ("empty_states_icons" in resp):
        is_been_banned = True
        return "", "", "", is_been_banned
    # feedbackid
    soup = BeautifulSoup(resp, "lxml")
    docid = ""
    req_name = ""
    comment_docid = ""
    comment_req_name = ""
    for js in soup.findAll("link", {"rel": "preload"}):
        resp = requests.get(js["href"])
        for line in resp.text.split("\n", -1):
            if "CometResharesFeedPaginationQuery_" in line:
                docid = re.findall('e.exports="([0-9]{1,})"', line)[0]
                req_name = "CometResharesFeedPaginationQuery"
                break
            if "ProfileCometTimelineFeedRefetchQuery_" in line:
                docid = re.findall('e.exports="([0-9]{1,})"', line)[0]
                req_name = "ProfileCometTimelineFeedRefetchQuery"
                break
            if "CometUFICommentsProviderQuery_" in line:
                docid = re.findall('e.exports="([0-9]{1,})"', line)[0]
                req_name = "CometUFICommentsProviderQuery"
                break
            else:
                continue

        # 抓留言用的docid
        for line in resp.text.split("\n", -1):
            if "CometFocusedStoryViewUFIQuery_" in line:
                comment_ans_list = re.findall('e.exports="([0-9]{1,})"', line)
                if len(comment_ans_list) > 0:
                    comment_docid = comment_ans_list[0]
                    comment_req_name = "CometFocusedStoryViewUFIQuery"
                    break

        resp.close()
        if (
            req_name == "CometResharesFeedPaginationQuery"
            and comment_req_name == "CometFocusedStoryViewUFIQuery"
        ):
            break
    print(f"feedback docid is: {docid}, req_name is: {req_name}")
    print(f"comment docid is: {comment_docid}, req_name is: {comment_req_name}")
    return "", docid, req_name, comment_docid, comment_req_name, is_been_banned


def __getPageID__(
    pageURL, customDriver: webDriver.postsDriver
) -> tuple[str, str, str, str, str, bool]:

    pageid = ""
    is_been_banned = False
    # *部分粉專有鎖年齡與國家,導致只能登入後才能瀏覽,故改用爬蟲登入法取得頁面資料
    resp = customDriver._getSource(pageURL=pageURL)
    if ("目前無法查看此內容" in resp) and ("empty_states_icons" in resp):
        is_been_banned = True
        return "", "", "", is_been_banned

    # pageID
    if len(re.findall('"pageID":"([0-9]{1,})",', resp)) >= 1:
        pageid = re.findall('"pageID":"([0-9]{1,})",', resp)[0]
    elif len(re.findall(r'"identifier":(.*?),', resp)) >= 1:
        pageid = re.findall(r'"identifier":(.*?),', resp)[0]
    elif (
        len(
            re.findall(r'https://www.facebook.com/profile.php\?id=([0-9]{1,}).*"', resp)
        )
        >= 1
    ):
        pageid = re.findall(
            r'https://www.facebook.com/profile.php\?id=([0-9]{1,}).*"', resp
        )[0]
    elif (
        len(
            re.findall(
                r'https:\\/\\/www.facebook.com\\/profile.php\?id=([0-9]{1,}).*"', resp
            )
        )
        >= 1
    ):
        pageid = re.findall(
            r'https:\\/\\/www.facebook.com\\/profile.php\?id=([0-9]{1,}).*"', resp
        )[0]
    elif len(re.findall("fb://group|page|profile/([0-9]{1,})", resp)) >= 1:
        pageid = re.findall("fb://group|page|profile/([0-9]{1,})", resp)[0]
    elif len(re.findall('delegate_page":\{"id":"(.*?)"\},', resp)) >= 1:
        pageid = re.findall('delegate_page":\{"id":"(.*?)"\},', resp)[0]
    else:
        pageid = ""

    # postid
    soup = BeautifulSoup(resp, "lxml")
    docid = ""
    req_name = ""
    for js in soup.findAll("link", {"rel": "preload"}):
        resp_href = requests.get(js["href"])
        for line in resp_href.text.split("\n", -1):
            if "ProfileCometTimelineFeedRefetchQuery_" in line:
                docid = re.findall('e.exports="([0-9]{1,})"', line)[0]
                req_name = "ProfileCometTimelineFeedRefetchQuery"
                # 針對此種特殊類型的粉專,重新導向抓取正確的pageid
                if len(re.findall('"userID":"(.*?)"', resp)) >= 1:
                    pageid = re.findall('"userID":"(.*?)"', resp)[0]
                break

            if "CometModernPageFeedPaginationQuery_" in line and docid == "":
                docid = re.findall('e.exports="([0-9]{1,})"', line)[0]
                req_name = "CometModernPageFeedPaginationQuery"
                break
                # 抓留言用的docid
        for line in resp_href.text.split("\n", -1):
            if "CometFocusedStoryViewUFIQuery_" in line:
                comment_ans_list = re.findall('e.exports="([0-9]{1,})"', line)
                if len(comment_ans_list) > 0:
                    comment_docid = comment_ans_list[0]
                    comment_req_name = "CometFocusedStoryViewUFIQuery"
                    break
        resp_href.close()

    print("page_id is: {}".format(pageid))
    print("page_docid is: {}".format(docid))
    print(f"page_req_name is: {req_name}")
    print("comment_docid is: {}".format(comment_docid))
    print(f"comment_req_name is: {comment_req_name}")
    return pageid, docid, req_name, comment_docid, comment_req_name, is_been_banned
