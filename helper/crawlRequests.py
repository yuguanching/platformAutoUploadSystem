import requests
import re
import json
import time
import random
import os
import traceback
import urllib3
import requests.packages
import configSetting

from queue import Queue
from numpy import append
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from fake_useragent import UserAgent
from helper import proxy, Auxiliary, helper
from ioService import writer, reader
from urllib3.exceptions import ConnectTimeoutError, MaxRetryError, ProtocolError
from requests.exceptions import (
    ProxyError,
    ConnectTimeout,
    SSLError,
    ConnectionError,
    ChunkedEncodingError,
    RetryError,
    HTTPError
)
from http.client import HTTPConnection

# 關閉使用proxy不帶verify時報出的警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def __getHeaders__(pageurl) -> dict:
    """
    Send a request to get cookieid as headers.
    """
    fake_user_agent = UserAgent()

    # headers['cookie'] = '; '.join(['{}={}'.format(cookieid, resp.cookies.get_dict()[cookieid]) for cookieid in resp.cookies.get_dict()])
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "accept-language": "en",
    }
    headers["ec-ch-ua-platform"] = "Windows"
    headers["User-Agent"] = str(fake_user_agent.chrome)
    headers["sec-fetch-site"] = "same-origin"
    headers["origin"] = "https://www.facebook.com"
    headers["referer"] = pageurl
    # headers['cookie'] = ''
    pageurl = re.sub("www", "m", pageurl)
    resp = requests.get(pageurl)
    headers["cookie"] = "; ".join(
        [
            "{}={}".format(cookieid, resp.cookies.get_dict()[cookieid])
            for cookieid in resp.cookies.get_dict()
        ]
    )
    return headers


def crawlPagePosts(pageURL, pageID, docID, reqName, processNum, targetName, queue: Queue = None, queueSignal: Queue = None) -> list:

    try_count = 0  # 全任務使用各種IP重試的次數統計
    proxy_count = 0  # 單一輪proxy_ip_list的遍歷索引, 每次proxy ip 更新後都會歸零
    proxy_ip_list = json.loads(os.environ["proxy_list"])
    random_proxy_ip = "http://" + proxy_ip_list[proxy_count]
    contents = []
    cursor = ""
    current_time = ""
    url = ""
    data = dict()
    page_info_obj = dict()
    headers = __getHeaders__(pageURL)
    headers["Connection"] = "close"

    session = requests.session()

    # 設定失敗重試策略
    retry_strategy = Retry(
        connect=3,
        total=configSetting.retry,
        status_forcelist=[429, 500, 502, 503, 504],
        method_whitelist=["HEAD", "GET", "OPTIONS", "POST"],
        backoff_factor=0.5,
    )
    adapter = HTTPAdapter(
        pool_connections=20, pool_maxsize=100, max_retries=retry_strategy
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    is_up_to_time = True
    while True:
        writer.writeLogToFile(f"行程{processNum}-> {targetName}:時間戳記: {current_time},文章網址: {url}, 當前的標記 : {cursor}")
        data = {
            "variables": str(
                {
                    "count": 3,
                    "cursor": cursor,
                    "id": pageID,
                    "scale": 1,
                    "stream_count": 1,
                    "UFI2CommentsProvider_commentsKey": "ProfileCometTimelineRoute",
                    "feedLocation": "TIMELINE",
                    "privacySelectorRenderLocation": "COMET_STREAM",
                    "__relay_internal__pv__GroupsCometDelayCheckBlockedUsersrelayprovider": "false",
                    "__relay_internal__pv__IsWorkUserrelayprovider": "false",
                    "__relay_internal__pv__IsMergQAPollsrelayprovider": "false",
                    "__relay_internal__pv__StoriesArmadilloReplyEnabledrelayprovider": "false",
                    "__relay_internal__pv__StoriesRingrelayprovider": "false",
                }
            ),
            "doc_id": docID,
            "__a": "1",
            "__comet_req": "15",
            "fb_api_req_friendly_name": reqName,
            "server_timestamps": "false",
        }
        try:
            resp = session.post(
                url="https://www.facebook.com/api/graphql/",
                data=data,
                headers=headers,
                timeout=configSetting.timeout,
                proxies={"http": random_proxy_ip, "https": random_proxy_ip},
                verify=False,
            )

            if reqName == "ProfileCometTimelineFeedRefetchQuery":
                (
                    edge_list,
                    cursor_now,
                    is_up_to_time,
                    arrive_first_catch_time,
                    time_now,
                    page_info_obj,
                ) = helper.__parsingProfileComet__(resp, targetName)
            elif reqName == "CometModernPageFeedPaginationQuery":
                (
                    edge_list,
                    cursor_now,
                    is_up_to_time,
                    arrive_first_catch_time,
                    time_now,
                ) = helper.__parsingCometModern__(resp, targetName)

            # 文章有分享的資料才做處理
            if len(edge_list) != 0:
                contents = contents + edge_list
                url = edge_list[len(edge_list) - 1]["url"]
            if reqName == "ProfileCometTimelineFeedRefetchQuery":
                if not helper.hasNextPage_ProfileComet(page_info_obj):
                    raise UnboundLocalError(f"Reached the last page")
                else:
                    cursor = cursor_now
                    current_time = time_now
            elif reqName == "CometModernPageFeedPaginationQuery":
                if not helper.hasNextPage_CometModern(resp):
                    raise UnboundLocalError(f"Reached the last page")
                else:
                    cursor = cursor_now
                    current_time = time_now
            # 超過設定的撈取日期
            if (is_up_to_time == False) and (arrive_first_catch_time == True):
                break
            else:
                continue
        except UnboundLocalError:
            print("Reached the last page")
            break

        except Exception as e:
            if (
                (not isinstance(e, ProtocolError))
                and (not isinstance(e, ChunkedEncodingError))
                and (not isinstance(e, ConnectionError))
                and (not isinstance(e, SSLError))
                and (not isinstance(e, UnboundLocalError))
                and (not isinstance(e, TimeoutError))
                and (not isinstance(e, KeyError))
                and (not isinstance(e, ConnectTimeoutError))
                and (not isinstance(e, MaxRetryError))
                and (not isinstance(e, ConnectionResetError))
                and (not isinstance(e, ProxyError))
                and (not isinstance(e, RetryError))
                and (not isinstance(e, HTTPError))
                and (not isinstance(e, ConnectTimeout))
            ):
                writer.writeLogToFile(f"pageid: {pageID}, docid: {docID}, cursor: {cursor}, error:{traceback.format_exc()}", True)
            writer.writeLogToFile(e, True)

            if queueSignal is None:
                proxy_count, try_count, proxy_ip_list = proxy.updateProxyAndStatus(
                    proxy_count, try_count, proxy_ip_list, processNum
                )
            else:
                proxy_count, try_count, proxy_ip_list = (
                    proxy.updateMultiThreadProxyAndStatus(
                        proxy_count,
                        try_count,
                        proxy_ip_list,
                        processNum,
                        pageID,
                        len(contents),
                        queueSignal,
                    )
                )
            random_proxy_ip = "http://" + proxy_ip_list[proxy_count]
            if try_count >= configSetting.proxy_try_count:
                print(f"行程{processNum}-> failed to catch posts after {try_count} times trying...")
                break
            else:
                continue
        finally:
            time.sleep(random.randint(2, 3))
    print(f"{targetName} 完成抓取，共有{len(contents)}則")
    writer.writeLogToFile(f"{targetName} 完成抓取，共有{len(contents)}則")
    session.close()
    if queue is not None:
        queue.put(contents)
        fill = int(os.environ.get("fan_pages_list_len"))
        if queue.qsize() % configSetting.queue_show_interval == 0:
            print(f"行程{processNum}-> {targetName}:目前完成的任務數量為 {queue.qsize()}")
        if fill - queue.qsize() < 20:
            print(f"行程{processNum}-> {targetName}:還剩下 {fill - queue.qsize()} 個任務未完成")
    return contents, targetName


def crawlPostsComments(
    pageURL,
    postsCount,
    feedbackID,
    storyID,
    docID,
    reqName,
    targetName,
    processNum,
    queue: Queue = None,
    queueSignal: Queue = None,
) -> list:

    try_count = 0  # 全任務使用各種IP重試的次數統計
    proxy_count = 0  # 單一輪proxy_ip_list的遍歷索引, 每次proxy ip 更新後都會歸零
    proxy_ip_list = json.loads(os.environ["proxy_list"])
    random_proxy_ip = "http://" + proxy_ip_list[proxy_count]
    contents = []
    headers = __getHeaders__(pageURL)

    # 所有配合多執行緒的功能都要將keep-alive關閉,確保每次連線取完資料會關閉,避免連線數被吃滿導致無法開啟連線的錯誤
    headers["Connection"] = "close"

    session = requests.session()

    # 設定失敗重試策略
    retry_strategy = Retry(
        connect=5,
        total=configSetting.retry_feedback,
        status_forcelist=[429, 500, 502, 503, 504],
        method_whitelist=["HEAD", "GET", "OPTIONS", "POST"],
        backoff_factor=0.5,
    )
    adapter = HTTPAdapter(
        pool_connections=20, pool_maxsize=100, max_retries=retry_strategy
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    while True:
        data = {
            "variables": str(
                {
                    "feedbackID": feedbackID,
                    "storyID": storyID,
                    "scale": "1",
                    "feedbackSource": 110,
                    "feedLocation": "DEDICATED_COMMENTING_SURFACE",
                }
            ),
            "doc_id": docID,
            "__a": "1",
            "__comet_req": "15",
            "fb_api_req_friendly_name": reqName,
        }

        try:
            resp = session.post(
                url="https://www.facebook.com/api/graphql/",
                data=data,
                headers=headers,
                timeout=configSetting.timeout_feedback,
                proxies={"http": random_proxy_ip, "https": random_proxy_ip},
                verify=f"{configSetting.ROOT_PATH}/config/certs.pem",
            )

            edge_list = helper.__parsingComments__(resp, postsCount)
            contents.extend(edge_list)
            print(f"文章編號{postsCount}的留言抓取finished")
            break

        except Exception as e:
            if (
                (not isinstance(e, ProtocolError))
                and (not isinstance(e, ChunkedEncodingError))
                and (not isinstance(e, ConnectionError))
                and (not isinstance(e, SSLError))
                and (not isinstance(e, UnboundLocalError))
                and (not isinstance(e, TimeoutError))
                and (not isinstance(e, KeyError))
                and (not isinstance(e, ConnectTimeoutError))
                and (not isinstance(e, MaxRetryError))
                and (not isinstance(e, ConnectionResetError))
                and (not isinstance(e, ProxyError))
                and (not isinstance(e, ConnectTimeout))
            ):
                writer.writeLogToFile(traceback.format_exc(), True)
                writer.writeLogToFile(f"post_id:{postsCount}, feedback_id:{feedbackID}, story_id:{storyID}, docid:{docID}", True)

            # 沒有使用多執行緒的走這邊
            if queueSignal is None:
                proxy_count, try_count, proxy_ip_list = proxy.updateProxyAndStatus(
                    proxy_count, try_count, proxy_ip_list, processNum
                )
            else:
                proxy_count, try_count, proxy_ip_list = (
                    proxy.updateMultiThreadProxyAndStatus(
                        proxy_count,
                        try_count,
                        proxy_ip_list,
                        processNum,
                        postsCount,
                        len(contents),
                        queueSignal,
                    )
                )
            random_proxy_ip = "http://" + proxy_ip_list[proxy_count]
            if try_count >= configSetting.proxy_try_count:
                print(
                    f"行程{processNum}-> failed to catch posts after {try_count} times trying..."
                )
                return contents
            else:
                continue
        finally:
            time.sleep(random.randint(1, 2))
    session.close()
    if queue is not None:
        queue.put(contents)
        fill = int(os.environ.get("feedback_id_list_len"))
        if queue.qsize() % configSetting.queue_show_interval == 0:
            print(
                f"行程{processNum}-> {targetName}:目前完成的任務數量為 {queue.qsize()}"
            )
        if fill - queue.qsize() < 50:
            print(
                f"行程{processNum}-> {targetName}:還剩下 {fill - queue.qsize()} 個任務未完成"
            )
    return contents
