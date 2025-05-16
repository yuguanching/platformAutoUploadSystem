import jieba
import pandas as pd
import configSetting
import asyncio
import re
import emoji
import traceback
import os
import copy
import numpy as np
from queue import Queue
from collections import Counter
from datetime import datetime, timedelta
from constant import *
from ioService import writer
from webManager import webDriver
from helper import Auxiliary


async def jieba_handle(contentList: list) -> tuple[list, list]:
    task_list = []
    word_list_all = []
    url_list_all = []
    for content in contentList:
        task_list.append(parse_content_to_word(content))

    result = await asyncio.gather(*task_list)
    for word_list, url_list in result:
        word_list_all.append(word_list)
        url_list_all.append(url_list)
    return word_list_all, url_list_all


async def parse_content_to_word(content: str) -> tuple[list, list]:
    stop_words = JIEBA_STOP_WORDS
    sentence_counter = Counter()
    word_counter = Counter()
    sentence_list = []
    url_list = []
    content = emoji.replace_emoji(content, replace="")
    content = content.replace("～", "")
    content = content.replace("－", "")
    content = content.replace(".", "")
    content = content.replace("…", "")

    temp = re.sub(SPECIAL_CHARS, " ", content)
    temp = re.sub(EMOJI_PATTERN, r" ", temp)
    temp = temp.strip()
    split_temp = re.split(r"[\s|\r\n]+", temp)
    for split_str in split_temp:
        if len(re.findall(URL_DETECT_REGEX, split_str)) > 0:
            url_list.extend(re.findall(URL_DETECT_REGEX, split_str))
        else:
            sentence_list.append(split_str)

    sentence_counter.update(sentence_list)

    async def update_word_counter(wordCounter: Counter) -> Counter:
        for key in sentence_counter:
            parse_list = jieba.lcut(key, cut_all=False)
            parse_list = [w for w in parse_list if len(w) > 1 and not re.match("^[a-z|A-Z|0-9|.]*$", w)]
            parse_list = [w for w in parse_list if w not in stop_words]
            wordCounter.update(parse_list)
        return wordCounter

    word_counter = await update_word_counter(word_counter)
    word_list = [key for key, _ in word_counter.most_common()]
    return word_list, url_list


def content_clean(content: str) -> str:
    content = emoji.replace_emoji(content, replace="")
    content = content.replace("\n", " ")
    content = content.replace("\r", " ")
    # content = re.sub(SPECIAL_CHARS, "", content)
    content = re.sub(EMOJI_PATTERN, r"", content)
    content = Auxiliary.strF2H(content)
    return content


def calculate_effect_topic(word_list: list) -> str:
    final_topic = ""
    max_score = 0
    score_record_board = {
        "政府施政": 0,
        "外交議題": 0,
        "民生經濟": 0,
        "兩岸關係": 0,
        "改革議題": 0,
        "國防軍事": 0,
        "選舉議題": 0,
        "新冠疫情": 0,
        "資安議題": 0,
    }
    for word in word_list:
        if word in EFFECT_TOPIC_DICT:
            score_record_board[EFFECT_TOPIC_DICT[word]] += EFFECT_TOPIC_SCORE_POINT[EFFECT_TOPIC_DICT[word]]
    for key, value in score_record_board.items():
        if value > max_score:
            max_score = value
            final_topic = key
    if max_score == 0:
        final_topic = "政府施政"
    return final_topic


def calculate_accosiate_department(content: str) -> str:
    max_score = 0
    final_department = ""
    # 判斷相關府院有沒有在內文中
    for key, value in ACCOSIATE_DEPARTMENT_SCORE_POINT.items():
        if key in content:
            if value >= max_score:
                max_score = value
                final_department = key

    # 地方政府另外判斷
    has_lacal_department_key_word = False
    for key, _ in TAIWAN_CITY.items():
        if (f"{key}市" in content) or (f"{key}縣" in content):
            has_lacal_department_key_word = True
            break
    if has_lacal_department_key_word and max_score < 14:
        final_department = "地方政府"
    if max_score == 0:
        final_department = "內政部"
    return final_department


def summeryTodayCollection(date: datetime, today_path: str) -> list:
    df = pd.DataFrame()
    old_df = None
    collection_file_list = []
    jieba.load_userdict(f"{configSetting.ROOT_PATH}/config/jieba/dict.txt.big.txt")

    dirname = f"summery-{date.strftime('%Y-%m-%d')}"
    print(f"開始進行{dirname}的資料彙整")
    try:
        # 檢查並創建當日的資料夾
        if os.path.exists(f"{today_path}"):
            print(f"subDir {dirname} is already exists")
        else:
            os.mkdir(f"{today_path}")
            os.mkdir(f"{today_path}/img")

        # 從粉專中拉取資料
        for root, _, files in os.walk(configSetting.output_root):
            for file in files:
                if "collectData" in file:
                    collection_file_list.append(f"{root}/{file}")
                    
        df = asyncio.run(read_all_fans_page_data(df, collection_file_list))
        # for file_path in collection_file_list:
        #     dir_name = file_path.split("/")[-2]
        #     new_df = pd.read_excel(
        #         file_path,
        #         sheet_name="collection",
        #         usecols="B:M",
        #         converters={"文章id": str},
        #     )
        #     new_df.insert(loc=0, column="粉專名稱", value=dir_name)
        #     df = pd.concat([df, new_df], axis=0, ignore_index=True)
        
        # 超過時間段的濾掉
        start_time_obj = date - configSetting.fetch_inteval
        end_time_obj = date
        for idx in df.index:
            dtype_date = datetime.strptime(df.loc[idx, "時間"], "%Y-%m-%d %H:%M:%S")
            df.loc[idx, "時間"] = (
                np.nan
                if (dtype_date < start_time_obj) or (dtype_date > end_time_obj)
                else df.loc[idx, "時間"]
            )
        df.dropna(subset=["時間"], inplace=True)

        # 若已有舊檔存在，讀取當天sumery中的資料作重複性比對
        if os.path.isfile(f"{today_path}/summery-collection.xlsx"):
            old_df = pd.read_excel(
                f"{today_path}/summery-collection.xlsx",
                sheet_name="collection",
                usecols="B:R",
                converters={"文章id": str},
            )
            old_df_dict = old_df.to_dict("records")
            old_post_id_dict = dict()
            for data_dict in old_df_dict:
                old_post_id_dict[data_dict["文章id"]] = 1

            duplicate_index = [idx for idx, val in df["文章id"].items() if val in old_post_id_dict]
            df.drop(duplicate_index, inplace=True)

        # 主文簡單清洗
        df["內容"] = df["內容"].replace("", np.nan)
        df.dropna(subset=["內容"], inplace=True)
        df["內容"] = df["內容"].map(content_clean)
        df["內容"] = df["內容"].replace("", np.nan)
        df.dropna(subset=["內容"], inplace=True)
        
        # 客製化過濾
        if configSetting.json_array_data["taskSetting"]["contentCustomFilter"]:
            keywords = configSetting.json_array_data["taskSetting"]["filterList"]
            filter_pattern = '|'.join(keywords)
            df = df[df["內容"].str.contains(filter_pattern, na=False)]
            df["匹配關鍵字"] = df["內容"].apply(lambda x: Auxiliary.match_all_keywords(x, keywords))
            
        if len(df.index) <= 0:
            return list()
        record_list = df.to_dict("records")
        contents_for_jieba = df["內容"].to_list()

        # 獲得主文的斷詞分析結果以及可能存在內文中的外部連結
        # 另外根據內文與斷詞結果分析此文的影響標的與事涉部門
        word_list_all, url_list_all = asyncio.run(jieba_handle(contents_for_jieba))
        for record, word_list, url_list in zip(record_list, word_list_all, url_list_all):
            record["斷詞分析"] = word_list
            writer.writeLogToFile(str(word_list))
            record["內容中的外部連結"] = url_list
            record["影響標的"] = calculate_effect_topic(word_list)
            record["事涉部門"] = calculate_accosiate_department(record["內容"])

        adjust_df = pd.DataFrame(record_list)
        if old_df is not None:
            adjust_df = pd.concat([old_df, adjust_df], axis=0, ignore_index=True)
            adjust_df["時間"] = pd.to_datetime(adjust_df["時間"], format="%Y-%m-%d %H:%M:%S")
            adjust_df.sort_values(by="時間", inplace=True, ascending=False)
            adjust_df["時間"] = adjust_df["時間"].dt.strftime("%Y-%m-%d %H:%M:%S")

        writer.pdToExcel(
            df=adjust_df,
            sheetName="collection",
            des=f"{today_path}/summery-collection.xlsx",
            autoFitIsNeed=False,
            mode="w",
        )
    except:
        writer.writeLogToFile(traceBack=traceback.format_exc(), isError=True)
        raise ValueError
    return record_list


def fetchPostsPicture(queue:Queue, recordList: list, path: str, screenDriver: webDriver.screenshotDriver) -> None:
    for idx, record in enumerate(recordList):
        print(f"開始進行貼文的截圖，id: {idx}")
        screenDriver._getSource(url=record["文章網址"], postID=record["文章id"], subDir=path)
        # deep_copy_record = copy.deepcopy(record)
        # queue.put(deep_copy_record)


async def read_all_fans_page_data(df:pd.DataFrame, fans_page_path_list: list) -> pd.DataFrame:
    task_list = []
    for file_path in fans_page_path_list:
        task_list.append(read_fans_page_data(file_path))
    results = await asyncio.gather(*task_list)
    for new_df in results:
        df = pd.concat([df, new_df], axis=0, ignore_index=True)
    return df

async def read_fans_page_data(file_path:str) -> pd.DataFrame:
    dir_name = file_path.split("/")[-2]
    new_df = pd.read_excel(
    file_path,
    sheet_name="collection",
    usecols="B:M",
    converters={"文章id": str},
    )
    new_df.insert(loc=0, column="粉專名稱", value=dir_name)
    return new_df