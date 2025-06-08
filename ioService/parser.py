from operator import mod
import time
import pandas as pd
import random
import re
import os
import jieba
import traceback
import numpy
import json
import openpyxl
import math
import configSetting
import demoji
import emoji


from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from collections import Counter
from ioService import writer, reader
from helper import Auxiliary
from webManager import webDriver
from wordcloud import WordCloud
from PIL import Image

# 關閉web driver的log訊息
os.environ["WDM_LOG_LEVEL"] = "0"


def buildCollectData(rawDataList, subDir, dropNA=False, is_use_for_group=False) -> tuple[list, list]:

    excel_file = f"{configSetting.output_root}" + subDir + "/collectData.xlsx"
    date = []
    image_url = []
    video_url = []
    like_count = []
    comment_count = []
    share_count = []
    content = []
    urls = []
    post_id = []
    feedback_id = []
    comment_id = []
    poster_url = []
    poster_name = []
    third_party_link = []

    print(f"開始產生{subDir}的文章統計資料")

    # 各內容的抓取位置請參考__resolverEdgesPage__()
    for raw_data in rawDataList:
        # 抓取並處理時間
        date.append(
            (lambda input_time: time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(input_time))))(raw_data["creation_time"])
        )

        # 抓取文章內容
        content.append(raw_data["message"])

        # 抓取圖片網址
        image_url.append(raw_data["image_url"])

        # 抓取影片網址
        video_url.append(raw_data["video_url"])

        # 抓取按讚數
        like_count.append(raw_data["reaction_count"])

        # 抓取留言數
        comment_count.append(raw_data["comment_count"])

        # 抓取分享數
        share_count.append(raw_data["share_count"])

        # 抓取文章網址
        urls.append(raw_data["url"])

        # 文章id
        post_id.append(str(raw_data["post_id"]))

        # 分享id
        feedback_id.append(raw_data["feedback_id"])

        # 留言id
        comment_id.append(raw_data["story_id"])

        # 發文者姓名
        poster_name.append(raw_data["poster_name"])

        # 發文者網址
        poster_url.append(raw_data["poster_url"])

        # 第三方連結
        third_party_link.append("")

    df = pd.DataFrame(
        {
            "時間": date,
            "文章id": post_id,
            "分享id": feedback_id,
            "留言id": comment_id,
            "內容": content,
            "圖片": image_url,
            "按讚數": like_count,
            "留言數": comment_count,
            "分享數": share_count,
            "影片網址": video_url,
            "文章網址": urls,
            "第三方連結": third_party_link,
        }
    )

    usecols = "B:M"
    # 抓取對象是社團而不是粉專的話
    if is_use_for_group:
        df["發文者"] = poster_name
        df["發文者個人網址"] = poster_url
        usecols = "B:O"

    if dropNA:
        df["內容"].replace("", numpy.nan, inplace=True)
        df.dropna(subset=["內容"], inplace=True)
        df.reset_index(drop=True)

    # 實作檢測已存在的舊collectData檔案, 若存在, 進行重複資料的篩選
    # 若有重複, 以新的資料為優先保留
    if os.path.isfile(f"{configSetting.output_root}{subDir}/collectData.xlsx"):
        old_df = pd.read_excel(
            f"{configSetting.output_root}{subDir}/collectData.xlsx",
            sheet_name="collection",
            usecols=usecols,
            converters={"文章id": str},
        )
        df_new = pd.concat([df, old_df], axis=0, ignore_index=True)
        sorted_df_new = df_new.sort_values(["分享數", "留言數", "按讚數"], ascending=[False, False, False])
        sorted_df_new = sorted_df_new.drop_duplicates(subset=["文章id"], keep="first")
        sorted_df_new["時間"] = pd.to_datetime(sorted_df_new["時間"], format="%Y-%m-%d %H:%M:%S")
        sorted_df_new.sort_values(by="時間", inplace=True, ascending=False)
        sorted_df_new["時間"] = sorted_df_new["時間"].dt.strftime("%Y-%m-%d %H:%M:%S")
        writer.pdToExcel(
            des=excel_file,
            df=sorted_df_new,
            sheetName="collection",
            autoFitIsNeed=False,
        )
        df = sorted_df_new
    else:
        writer.pdToExcel(des=excel_file, df=df, sheetName="collection", autoFitIsNeed=False)
    print(f"{subDir}的文章統計資料寫入完成")

    # 最後將分享與留言id回傳給外部使用
    feedback_id_list = df["分享id"].tolist()
    comment_id_list = df["留言id"].tolist()
    return feedback_id_list, comment_id_list


def extendCommentData(commentDataList, subDir):
    excel_file = f"{configSetting.output_root}" + subDir + "/collectData.xlsx"
    comment_data = []
    comment_posts_count = []

    for articleComments in commentDataList:
        for commentData in articleComments:
            msg = commentData["content"]
            comment_posts_count.append(commentData["posts_count"])
            urls = re.findall(
                "http[s]?:\/\/(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
                msg,
            )
            if len(urls) <= 0:
                comment_data.append("")
            else:
                comment_data.append(urls[0])

    df = pd.DataFrame({"編號": comment_posts_count, "第三方連結": comment_data})
    # 排序用, 用完就刪掉
    df = df.sort_values("編號")
    df.drop("編號", inplace=True, axis=1)
    with pd.ExcelWriter(
        excel_file, mode="a", engine="openpyxl", if_sheet_exists="overlay"
    ) as writer:
        df.to_excel(writer, index=False, sheet_name="collection", startcol=12)
    # filename_csv = excel_file.replace(".xlsx", "_" + "collection" + ".csv")
    # csv_df = pd.read_csv(filename_csv)
    # csv_df.insert(loc=8, column="第三方連結", value=df['第三方連結'])
    # csv_df.to_csv(filename_csv, index=False, encoding='utf_8_sig')
