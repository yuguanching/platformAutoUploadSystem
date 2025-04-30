import traceback
import configSetting
import copy
import random
from multiprocessing.synchronize import Event
from ioService import writer
from webManager import webDriver
from queue import Queue
from Line import action
from concurrent.futures import ThreadPoolExecutor, as_completed

# # 針對處理好的資料按上傳帳號分配進行上傳
def data_upload_worker(queue: Queue, today_path:str, is_event_stop:Event):
    print("啟動上傳manager成功")
    upload_account_allocate_info:dict = configSetting.json_array_data["uploadAccountResourceAllocate"]
    try:
        while True:
            print("等待資料上傳...")
            current_record_list = queue.get(block=True)
            print(f"取得欲上傳資料")
            results = []
            if configSetting.report_channel ==1 :
                # 帳號上傳清單初始化:
                for upload_account, _ in upload_account_allocate_info.items():
                    upload_account_allocate_info[upload_account]["round_post_upload_list"] = list()
                # 巢狀迴圈，填滿個帳號的上傳清單
                for current_record in current_record_list:
                    for upload_account, item in upload_account_allocate_info.items():
                        if current_record["粉專名稱"] in item["mapping"]:
                            deep_copy_record = copy.deepcopy(current_record)
                            item["round_post_upload_list"].append(deep_copy_record)
                        else:
                            continue
                
                with ThreadPoolExecutor(max_workers=len(upload_account_allocate_info)) as executor:
                    for upload_account, item in upload_account_allocate_info.items():
                        # 進行上傳前，將上傳清單順序打亂(in place)
                        random.shuffle(item["round_post_upload_list"])
                        upload_plarform_driver = webDriver.uploadPlatformDriver(driver=None, options=None, isLogin=False)
                        upload_plarform_driver.setOptions(needHeadless=configSetting.need_headless, needImage=False)
                        upload_plarform_driver.driverInitialize()
                        upload_plarform_driver.set_account_name(account_name=upload_account)
                        upload_plarform_driver.login()
                        result = executor.submit(callUpload, upload_plarform_driver, item["round_post_upload_list"], today_path)
                        results.append(result)
                    for result in as_completed(results):
                        try:
                            the_driver:webDriver.uploadPlatformDriver = result.result()
                            the_driver.clearDriver()
                        except:
                            print(traceback.format_exc())
                            writer.writeLogToFile(traceback.format_exc(), isError=True)
            else:
                for current_record in current_record_list:
                    msg = f'''
                            通報粉專:{current_record["粉專名稱"]}
                            發佈時間:{current_record["時間"]}
                            內容:{current_record["內容"]}
                            文章連結:{current_record["文章網址"]}                            
                            '''
                    action.send_msg_to_bot(msg=msg)

            if queue.empty() and is_event_stop.is_set():
                break
            else:
                continue
    except:
        print(traceback.format_exc())
        raise ValueError
    
def callUpload(upload_plarform_driver: webDriver.uploadPlatformDriver, record_list: list, today_path:str) -> webDriver.uploadPlatformDriver:
    for idx, record in enumerate(record_list):
        if idx % 40 == 0 and idx != 0:
            print(f"{upload_plarform_driver.account_name}: 刷新瀏覽器")
            upload_plarform_driver.clearDriver()
            upload_plarform_driver.driverInitialize()
            upload_plarform_driver.login()
        upload_plarform_driver._getSource(record=record, path=today_path)
        writer.writeLogToFile(f"{upload_plarform_driver.account_name}: 粉專名稱: {record['粉專名稱']}, 貼文: {record['文章id']} 上傳完成")
        print(f"{upload_plarform_driver.account_name}: 粉專名稱: {record['粉專名稱']}, 貼文: {record['文章id']} 上傳完成")
    return upload_plarform_driver