import os
import json
import time
import sys
import traceback
import configSetting
import dataLoadAndParse
import multiprocessing
import dataUpload
import copy
import random
from datetime import datetime
from helper import Auxiliary, proxy, crawlRequests, thread
from ioService import parser, writer, reader
from webManager import webDriver
from queue import Queue
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed



def runFansPage(jsonArrayDataSub, processNum) -> str:
    """
    jsonArrayDataSub: 已經透過多行程分配過的輸入資料
    """
    target_urls = jsonArrayDataSub["targetURL"]
    target_names = jsonArrayDataSub["targetName"]
    target_page_ids = jsonArrayDataSub["targetPageID"]
    target_page_docids = jsonArrayDataSub["targetPageDocID"]
    target_page_reqnames = jsonArrayDataSub["targetPageReqName"]

    results = []
    q_data = Queue()  # 幫助內部計數用
    q_signal = Queue()  # 信號傳遞交換區
    thread_workers = thread.generateThreadWorkers(len(target_urls) // 3)
    with ThreadPoolExecutor(max_workers=thread_workers) as executor:
        print(f"行程{processNum}-> 啟動，抓取線程共{thread_workers}條")
        for target_url, target_name, page_id, page_docid, page_reqname in zip(
            target_urls,
            target_names,
            target_page_ids,
            target_page_docids,
            target_page_reqnames,
        ):
            # 每個粉專資料有自己的子資料夾存放
            Auxiliary.checkDirAndCreate(target_name)
            print(f"開始抓取 {target_name} 的文章資料")
            result = executor.submit(
                crawlRequests.crawlPagePosts,
                target_url,
                page_id,
                page_docid,
                page_reqname,
                processNum,
                target_name,
                q_data,
                q_signal,
            )
            results.append(result)
        for result in as_completed(results):
            try:
                payload = result.result()
                parser.buildCollectData(payload[0], payload[1])
            except Exception as thread_e:
                writer.writeLogToFile(f"行程{processNum}-> 運作時執行緒意外報錯: {thread_e}", True)
                writer.writeLogToFile(f"行程{processNum}-> 詳細錯誤原因: {traceback.format_exc()}", True)
    del q_data
    del q_signal
    return f"行程{processNum}-> 全部執行完成"


def scrapeFacebookDailyPosts():

    json_array_data = reader.readInputJson(target_file=f"{configSetting.ROOT_PATH}/config/input.json")

    process_worker = 1
    posts_driver = webDriver.postsDriver(driver=None, options=None, isLogin=False)
    posts_driver.setOptions(needHeadless=configSetting.need_headless, needImage=False)
    posts_driver.driverInitialize()
    page_docid = "8009237869104587"
    page_reqname = "ProfileCometTimelineFeedRefetchQuery"
    comment_docid = "7031467293642902"
    comment_reqname = "CometFocusedStoryViewUFIQuery"
    target_urls = json_array_data["targetURL"]
    target_names = json_array_data["targetName"]

    # 取第一組作一次doc_id 的嘗試抓取，有抓到就直接停止
    # for url_for_docid, name_for_docid in zip(target_urls, target_names):
    #     (
    #         page_id,
    #         page_docid,
    #         page_reqname,
    #         comment_docid,
    #         comment_reqname,
    #         is_been_banned,
    #     ) = idFetcher.fetchEigenvaluesAndID(
    #         func=idFetcher.__getPageID__,
    #         customDriver=posts_driver,
    #         errString="未能取得文章的docid 或 pageid,嘗試換其他帳號試試",
    #         pageURL=url_for_docid,
    #         checkOption=2,
    #     )
    #     if is_been_banned:
    #         writer.writeLogToFile(f"目標{name_for_docid}已被臉書封鎖,留下紀錄待處理")
    #         continue
    #     else:
    #         print("成功取得docid")
    #         break

    page_id_list = json_array_data["targetPageID"]
    os.environ['fan_pages_list_len'] = str(len(page_id_list))
    json_array_data["targetPageDocID"] = [page_docid for _ in range(len(page_id_list))]
    json_array_data["targetPageReqName"] = [page_reqname for _ in range(len(page_id_list))]
    # 按行程的數量平分工作量
    target_url_split = Auxiliary.split(json_array_data["targetURL"], process_worker)
    target_name_split = Auxiliary.split(json_array_data["targetName"], process_worker)
    target_page_id_split = Auxiliary.split(json_array_data["targetPageID"], process_worker)
    target_page_docid_split = Auxiliary.split(json_array_data["targetPageDocID"], process_worker)
    target_page_reqname_split = Auxiliary.split(json_array_data["targetPageReqName"], process_worker)

    args_list = []
    result_list = []
    process_futures = []

    for i in range(process_worker):
        json_array_data_copy_temp = json_array_data.copy()
        json_array_data_copy_temp["targetURL"] = target_url_split[i]
        json_array_data_copy_temp["targetName"] = target_name_split[i]
        json_array_data_copy_temp["targetPageID"] = target_page_id_split[i]
        json_array_data_copy_temp["targetPageDocID"] = target_page_docid_split[i]
        json_array_data_copy_temp["targetPageReqName"] = target_page_reqname_split[i]

        args_list.append(json_array_data_copy_temp)

    with ProcessPoolExecutor(max_workers=process_worker) as executor:
        print(f"已配置{process_worker}個處理行程等待執行")
        for i in range(len(args_list)):
            print(f"任務 {i} 植入任務列表")
            writer.writeLogToFile(f"process {str(i)} : {json.dumps(args_list[i]['targetName'], ensure_ascii=False)}")
            process_future = executor.submit(runFansPage, args_list[i], i)
            process_futures.append(process_future)
            time.sleep(i / 2)  # 避免短時間一次執行多條程序所作的緩衝
        for future in as_completed(process_futures):
            result_list.append(future.result())
    for result in result_list:  # 確認各行程有完成任務
        writer.writeLogToFile(result)
    posts_driver.clearDriver()
    print("爬蟲腳本執行完成，準備進行資料整理")


def data_summery_and_upload(queue: Queue, screenDriver: webDriver.screenshotDriver, today_path:str):
    # # 針對抓取到的各粉專貼文進行處理與彙整
    date = datetime.now()
    # date = datetime.strptime("2024-03-06 22:00:00", "%Y-%m-%d %H:%M:%S")
    record_list = dataLoadAndParse.summeryTodayCollection(date=date, today_path=today_path)
    writer.writeLogToFile(f"本輪共抓到有效資料{len(record_list)}則")

    if len(record_list) <= 0:
        writer.writeLogToFile("本輪沒有抓到有效資料，故直接進入休息")
        print("本輪沒有抓到有效資料，故直接進入休息")
        return
    # 直接將整批資料往queue中輸送
    deep_copy_record_list = copy.deepcopy(record_list)
    queue.put(deep_copy_record_list)

    # # 針對文章進行截圖存檔
    # 經討論暫時不需要截圖功能
    # dataLoadAndParse.fetchPostsPicture(queue=queue, recordList=record_list, path=today_path, screenDriver=screenDriver)


if __name__ == "__main__":
    print("資料初始化")
    Auxiliary.createIndexExcelAndRead()
    task_queue = multiprocessing.Queue()
    stop_event = multiprocessing.Event() # 用於終止子程序
    today_date = datetime.now()
    today_path = f"{configSetting.output_root}當日彙整/summery-{today_date.strftime('%Y-%m-%d')}"
    # 启动多个子进程
    p = multiprocessing.Process(target=dataUpload.data_upload_worker, args=(task_queue, today_path, stop_event,), daemon=True)
    p.start()
    try:
        while True:
            print("開始循環任務")
            screenshot_driver = webDriver.screenshotDriver(driver=None, options=None, isLogin=False)
            screenshot_driver.setOptions(needHeadless=configSetting.need_headless, needImage=False)
            print("進行截圖器創建")
            screenshot_driver.driverInitialize()
            now = datetime.now()
            time_point = now.strftime("%Y-%m-%d %H:%M:%S")

            if now.hour > 22 or now.hour < 8:
            # if False:
                stop_event.set()  # 发送子程序退出信号
                p.join()
                print("子程序已终止")
                sys.exit(0)
            else:
                proxy_ip_list = proxy.gRequestsProxyList(None)
                ip_list_str = json.dumps(proxy_ip_list)
                os.environ["proxy_list"] = ip_list_str
                scrapeFacebookDailyPosts()
                data_summery_and_upload(queue=task_queue, screenDriver=screenshot_driver, today_path=today_path)

            print("完成本輪資料抓取與歸檔任務")
            screenshot_driver.clearDriver()
            minutes_interval = random.randint(3, 5)
            print(f"現在時間:{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}，休息{minutes_interval}分鐘")
            writer.writeLogToFile(f"休息{minutes_interval}分鐘")
            time.sleep(minutes_interval * 60)
            os.environ["job_start_time_point"] = time_point
    except:
        writer.writeLogToFile(f"意外捕捉:{traceback.format_exc()}")
    writer.writeLogToFile("結束程式")
