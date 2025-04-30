import re
import json
import os
import requests
import time
import configSetting
import base64
import traceback
import httpx
import asyncio

from fake_useragent import UserAgent
from requests import Session
from py_mini_racer import MiniRacer
from queue import Queue
from bs4 import BeautifulSoup


def getNovaFreeProxyList(s: Session) -> list:
    ip_list = []
    try:
        ctx = MiniRacer()
        resp = s.get("https://www.proxynova.com/proxy-server-list/elite-proxies/", timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        resp.close()
        rows = soup.find("table", {"id": "tbl_proxy_list"}).find("tbody").find_all("tr")
        for row in rows:
            row_content = row.find_all("td")
            ip = ""
            for i in range(0, 2):
                if i == 0:
                    try:
                        jsStr = (
                            "function scriptRunner(){"
                            + str(row_content[i].find("script").text).replace(
                                "document.write", "return ") + "} scriptRunner()"
                        )
                        ip = ctx.eval(jsStr)
                    except:
                        break
                else:
                    port = str(row_content[i].text).strip()
                    ip += ":" + port
            if ip != "":
                ip_list.append(ip)
    except:
        pass
    return ip_list


def getCZFreeProxyList(s: Session) -> list:

    resp = s.get("http://free-proxy.cz/en/proxylist/country/all/http/uptime/all", timeout=10)
    soup = BeautifulSoup(resp.text, "html.parser")
    rows = soup.find("table", {"id": "proxy_list"}).find("tbody").find_all("tr")
    resp.close()
    ip_list = []
    for row in rows:
        row_content = row.find_all("td")
        if len(row_content) <= 1:
            continue
        else:
            ip = ""
            for i in range(0, 2):
                if i == 0:
                    target = str(row_content[i])
                    res = re.findall(r'Base64\.decode\("(.*?)"\)', target)[0]
                    res = base64.b64decode(res).decode("utf-8")
                    ip = res
                else:
                    ip = ip + ":" + row_content[i].text
            ip_list.append(ip)
    return ip_list


def getTaiwanFreeProxyList(s: Session) -> list:
    proxy_ips = []
    try:
        response = s.get("https://freeproxyupdate.com/taiwan-tw/http", timeout=configSetting.timeout)
        proxy_ip = re.findall(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", response.text)
        proxy_port = re.findall("d>\d+<", response.text)
        response.close()
        for ip, port in zip(proxy_ip, proxy_port):
            proxy_ips.append(ip + ":" + port[2 : len(port) - 1])
    except:
        print("tw的IP抓取失敗,直接捨棄結果")
    return proxy_ips


# 單線舊版,測試檢查用
def getFreeProxyList() -> dict:
    response = requests.get("https://www.google-proxy.net/")
    proxy_ips = re.findall("\d+\.\d+\.\d+\.\d+:\d+", response.text)  # 「\d+」代表數字一個位數以上
    proxy_ips = getTaiwanFreeProxyList() + proxy_ips
    valid_ips = []
    response.close()

    # 限制抓取一定數量的可用proxy即可
    limit_count = configSetting.valid_proxy_ip_len
    s = requests.session()
    for ip in proxy_ips:
        try:
            result = s.get(
                "https://ip.seeip.org/jsonip?",
                proxies={"http": ip, "https": ip},
                timeout=3,
            )
            print(result.json())
            valid_ips.append(ip)
            if len(valid_ips) == limit_count:
                break
        except:
            print(f"{ip} invalid 1")
            try:
                result = s.get("https://api.ipify.org?format=json", proxies={"http": ip, "https": ip}, timeout=3,)
                print(result.json())
                valid_ips.append(ip)
                if len(valid_ips) == limit_count:
                    break
            except:
                print(f"{ip} invalid 2")

    proxt_dict = {"proxyList": valid_ips}
    with open(f"{configSetting.ROOT_PATH}/config/proxyList.json", "w", encoding="utf_8") as f:
        json.dump(proxt_dict, f, ensure_ascii=False, indent=4)
    s.close()
    return proxt_dict


async def checkIPAlive(proxyList: list) -> list:
    task_list = []
    valid_list = []
    ua = UserAgent()
    for ip in proxyList:
        task_list.append(check(ip, ua))
    results = await asyncio.gather(*task_list)
    for r in results:
        if r != "":
            valid_list.append(r)

    return valid_list


async def check(ip: str, ua:UserAgent) -> str:
    vote = 0
    proxy_timeout = 3
    headers = {'user-agent':ua.chrome}
    proxies = {"http://": f"http://{ip}", "https://": f"http://{ip}"}
    async with httpx.AsyncClient(headers=headers, timeout=proxy_timeout, verify=False, proxies=proxies) as client:
        try:
            result_1 = await client.get("https://ip4.seeip.org/json")
        except:
            result_1 = None
        try:
            result_2 = await client.get("https://api.ipify.org?format=json")
        except:
            result_2 = None
        try:
            result_3 = await client.get("https://www.facebook.com")
        except:
            result_3 = None

    if result_1 is not None:
        vote += 1
    if result_2 is not None:
        vote += 1
    if result_3 is not None:
        vote += 2
    return ip if vote >= 2 else ""


def gRequestsProxyList(processNum=None) -> list:
    valid_ips = []
    proxy_ips = []
    s = requests.session()
    while True:
        try:
            if processNum is None:
                print("異步呼叫,蒐集可用的proxy")
            else:
                print(f"行程{processNum} : 異步呼叫,蒐集可用的proxy")

            # response_ssl = s.get("https://www.sslproxies.org/", timeout=10)
            response_anonymous = s.get("https://free-proxy-list.net/anonymous-proxy.html", timeout=10)
            response_free = s.get("https://free-proxy-list.net/", timeout=10)

            proxy_ips = getNovaFreeProxyList(s) + proxy_ips
            # proxy_ips = proxy_ips + re.findall("\d+\.\d+\.\d+\.\d+:\d+", response_ssl.text)  # 「\d+」代表數字一個位數以上
            proxy_ips = proxy_ips + re.findall("\d+\.\d+\.\d+\.\d+:\d+", response_anonymous.text)
            proxy_ips = proxy_ips + re.findall("\d+\.\d+\.\d+\.\d+:\d+", response_free.text)
            proxy_ips = getCZFreeProxyList(s) + proxy_ips
            proxy_ips = getTaiwanFreeProxyList(s) + proxy_ips

            # response_ssl.close()
            response_anonymous.close()
            response_free.close()

            # 濾掉重複的
            proxy_ips_set = set(proxy_ips)
            proxy_ips = list(proxy_ips_set)

            valid_ips = asyncio.run(checkIPAlive(proxy_ips))

            if len(valid_ips) <= 0:
                print(f"行程{processNum} 取proxy發生意外錯誤2,等待後重取")
                valid_ips = []
                proxy_ips = []
                continue
            else:
                break
        except Exception as e:
            print(f"行程{processNum} 取proxy發生意外錯誤1: {traceback.format_exc()},等待後重取")
            valid_ips = []
            proxy_ips = []
            continue
    s.close()
    return valid_ips[:20] if len(valid_ips)>20 else valid_ips


def updateProxyAndStatus(proxyCount, tryCount, ProxyIpList, processNum):

    proxyCount += 1
    if proxyCount >= len(ProxyIpList):
        print(f"行程{processNum}-> all proxy are down ! please refresh the proxyList")
        ProxyIpList = gRequestsProxyList(processNum)
        proxyCount = 0
        tryCount += 1

    return proxyCount, tryCount, ProxyIpList


def updateMultiThreadProxyAndStatus(
    proxyCount,
    tryCount,
    ProxyIpList,
    processNum,
    pageID,
    dataLength,
    queueSignal: Queue,
):

    proxyCount += 1
    if proxyCount >= len(ProxyIpList):
        # 先比較環境變數中的proxyList有沒有更新
        if json.dumps(ProxyIpList) != os.environ["proxy_list"]:
            # print(f"行程{process_num} 發現環境變數已更新,直接從環境變數刷新proxyList")
            ProxyIpList = json.loads(os.environ["proxy_list"])
            proxyCount = 0
        else:
            # 尚未有人更新,檢查當前是否有人占用更新proxyList的資格,若可以更新proxyList,執行後刷新環境變數
            if queueSignal.qsize() == 0:
                queueSignal.put(str(processNum))
                ProxyIpList = gRequestsProxyList(processNum)
                ip_list_str = json.dumps(ProxyIpList)
                os.environ["proxy_list"] = ip_list_str
                proxyCount = 0
                tryCount += 1
                queueSignal.get()  # 釋放信號
                print(f"行程{processNum}->文章or用戶編號{pageID} : proxyList更新完畢, 目前已抓取{dataLength}份資料,已嘗試了{tryCount}次")
            else:
                # 有人占用,就先不更新proxyList, 直接取得當前環境變數中的proxyList來(等於跳空一輪)
                # print(f"行程{process_num} 不更新proxyList,取當前的環境變數")
                ProxyIpList = json.loads(os.environ["proxy_list"])
                proxyCount = 0

    return proxyCount, tryCount, ProxyIpList
