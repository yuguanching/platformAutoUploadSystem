import json
import time
import httpx
import re
import asyncio
import random
import configSetting
import urllib.parse
from helper import Auxiliary
from ioService import reader, writer
from httpx import AsyncClient


async def alive_check() -> list:
    json_data = configSetting.json_array_data
    inspect_account_dict = configSetting.inspect_data
    # 分批
    targets_split = Auxiliary.split(json_data["targets"], configSetting.check_alive_batch)
    new_target_list = []
    new_url_list = []
    new_name_list = []
    id_list = []
    check_url_use = 0

    # 分批處理網址檢查
    for idx in range(0, configSetting.check_alive_batch):
        task_list = list()
        async with httpx.AsyncClient(timeout=configSetting.timeout_async) as client:
            for target_object in targets_split[idx]:
                task_list.append(check(
                    target_object["targetName"], 
                    target_object["targetURL"], 
                    target_object["targetID"], 
                    target_object["targetType"], 
                    check_url_use, 
                    client))
                check_url_use = check_url_use ^ 1
            results = await asyncio.gather(*task_list)

        for name, url, id, type, is_alive in results:
            if is_alive:
                # 確認存活，從觀察清單中剃除
                if name in inspect_account_dict:
                    del inspect_account_dict[name]
                new_target_list.append({
                    "targetName": name,
                    "targetURL": url,
                    "targetID": id,
                    "targetType": type
                })
            else:
                if name in inspect_account_dict:
                    inspect_account_dict[name]["count"] = inspect_account_dict[name]["count"] + 1
                    # 還在觀察狀態，可持續保留
                    if inspect_account_dict[name]["count"] <= configSetting.check_alive_deadline:
                        new_target_list.append({
                            "targetName": name,
                            "targetURL": url,
                            "targetID": id,
                            "targetType": type
                        })
                else:
                    # 第一次觀察到可能被封，首次加進觀察名單中
                    inspect_account_dict[name] = {
                        "name":name,
                        "url": url,
                        "id": id,
                        "type": type,
                        "count": 1
                    }
                    new_target_list.append({
                        "targetName": name,
                        "targetURL": url,
                        "targetID": id,
                        "targetType": type
                    })
        print(f"第{idx+1}批檢查完畢，休息{configSetting.check_alive_sleep}秒")
        if idx+1 == configSetting.check_alive_batch:
            break
        else:
            time.sleep(configSetting.check_alive_sleep)

    json_data["targets"] = new_target_list
    json_obj = json.dumps(json_data, indent=4, ensure_ascii=False)
    inspect_obj = json.dumps(inspect_account_dict, indent=4, ensure_ascii=False)
    with open(f"{configSetting.ROOT_PATH}/config/input.json", "w", encoding="utf-8") as outfile:
        outfile.write(json_obj)
    with open(f"{configSetting.ROOT_PATH}/config/inspect.json", "w", encoding="utf-8") as outfile:
        outfile.write(inspect_obj)
    return page_id_list


async def check(
    name: str, url: str, page_id_old:str, type:str, check_url_use: int, client: AsyncClient
) -> tuple[str, str, str, bool]:
    try:
        print(f"檢查粉專:{name}")
        url_format_mobile = ""
        url_format_PC = ""
        if "profile.php" in url:
            re_search = re.findall(r"https:\/\/www.facebook.com\/profile.php\?id=([0-9]{1,}).*", url)
            parse_name = name.replace("，", "").replace("。", "").replace("！", "")
            url_format_mobile = f"https://m.facebook.com/p/{urllib.parse.quote_plus(parse_name).replace('+','-')}/{re_search[0]}/"
            url_format_PC = f"https://www.facebook.com/people/{urllib.parse.quote_plus(parse_name).replace('+','-')}/{re_search[0]}/"
        else:
            url_format_PC = url
            url_format_mobile = re.sub("www", "m", url_format_PC)  # 關鍵
        is_alive = False
        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "accept-language": "zh-TW,zh;q=0.9",
            "authority": "www.facebook.com",
        }
        headers["sec-fetch-site"] = "same-origin"
        headers["origin"] = "https://www.facebook.com"
        if check_url_use==0:
            headers["user-agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        else:
            headers["user-agent"] = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"

        page_id_pattern_for_mobile = re.compile(pattern=r"\?id=([0-9]{1,})")
        page_id_pattern_for_PC = re.compile(pattern=r"\"fb:\/\/profile\/([0-9]{1,})\"")
        spare_pattern = re.compile(pattern=r"profile\/([0-9]{1,})\"")
        url_pattern_list = []
        url_pattern_list.append((url_format_PC, page_id_pattern_for_PC))
        url_pattern_list.append((url_format_mobile, page_id_pattern_for_mobile))
        # if name == "哭吧！雙標仔":
        #     print(url_pattern_list)
        #     writer.writeTempFile(filename="qqJerry", content=f"{url_pattern_list}")

        search_page_id = ""
        use_url = url_pattern_list[check_url_use][0]
        use_pattern = url_pattern_list[check_url_use][1]
        for _ in range(5):
            resp = await client.get(url=use_url, headers=headers)
            if len(use_pattern.findall(resp.text)) != 0:
                search_page_id = use_pattern.findall(resp.text)
                break
            elif len(spare_pattern.findall(resp.text)) != 0:
                search_page_id = spare_pattern.findall(resp.text)
                break
            else:
                await asyncio.sleep(2)
                continue
        is_alive = True if len(search_page_id) > 0 else False
        page_id = ""
        if len(search_page_id) > 0:
            page_id = search_page_id[0]
        else:
            writer.writeTempFile(filename=f"page_dTree_{name}", content=resp.text)
            page_id = page_id_old

        return name, url, page_id, type, is_alive
    except Exception as e:
        print(f"異常錯誤:{name}, 錯誤訊息: {e}")
        raise BaseException


if __name__ == "__main__":
    # 檢查粉專目前有哪些存活並更新檔案
    page_id_list = asyncio.run(alive_check())
    writer.writeTempFile(filename="aliveIP", content=str(page_id_list))
    writer.writeLogToFile("粉專存活更新完成")
    print("粉專存活更新完成")
