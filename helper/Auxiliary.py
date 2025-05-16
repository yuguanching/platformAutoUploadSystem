import os
import json
import pandas as pd
import time
import configSetting

from datetime import datetime, timedelta
from ioService import writer, reader


def createIndexExcelAndRead() -> None:
    target_name_list = []
    target_url_list = []
    target_type_list = []
    target_id_list = []
    for target in configSetting.json_array_data["targets"]:
        # 每個粉專資料有自己的子資料夾存放
        target_name_list.append(target["targetName"])
        target_url_list.append(target["targetURL"])
        target_type_list.append(target["targetType"])
        target_id_list.append(target["targetID"])
        

    # 創建目標粉專的目錄excel
    index_df = pd.DataFrame(
        {
            "粉專": target_name_list,
            "連結": target_url_list,
            "ID": target_id_list,
            "類型": target_type_list,
        }
    )
    writer.pdToExcel(
        des=f"{configSetting.output_root}index.xlsx",
        df=index_df,
        sheetName="sheet1",
        autoFitIsNeed=False,
    )
    print("已完成目標粉專的目錄建置")


def checkDirAndCreate(dir_name:str) -> None:
    if os.path.exists(f"{configSetting.output_root}" + str(dir_name)):
        print("subDir " + str(dir_name) + " is already exists")
    else:
        os.mkdir(f"{configSetting.output_root}" + str(dir_name))
        os.makedirs(f"{configSetting.output_root}" + str(dir_name) + "/img/sharer")
        os.makedirs(
            f"{configSetting.output_root}" + str(dir_name) + "/img/been_sharer"
        )
        os.makedirs(
            f"{configSetting.output_root}" + str(dir_name) + "/img/word_cloud"
        )
        os.makedirs(f"{configSetting.output_root}" + str(dir_name) + "/img/report")
        print("subDir " + str(dir_name) + " created successfully")


def detectURL(str: str) -> str:
    return (
        (str.find("http://") == -1)
        and (str.find("https://") == -1)
        and (str.find("=") == -1)
    )

def dateCompareByLocalFile(targetDate:datetime, targetName:str)->int:
    # 和可能存在的本地端資料比較，只要目前抓到的資料時間比本地端時間還新，就繼續抓
    # return 1: 還能抓, 0: 不能抓, 2: 因檔案不存在或是檔案中沒有資料，故無法作為判斷依據
    check_file = f"{configSetting.output_root}{str(targetName)}/collectData.xlsx"
    if os.path.isfile(check_file):
        target_df = pd.read_excel(check_file, sheet_name="collection", usecols="B")
        if len(target_df.index) <=0:
            return 2
        else:
            target_df["時間"] = pd.to_datetime(target_df["時間"])
            return 1 if targetDate > max(target_df["時間"]) else 0
    else:
        return 2

def dateCompare(target_time_stamp, target_name) -> tuple[bool, bool, str]:
    
    arrive_first_catch_time = True
    target_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(target_time_stamp)))
    target_time_obj = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
    local_file_compare_status = dateCompareByLocalFile(target_time_obj, target_name)
    match local_file_compare_status:
        case 0:
            return False, arrive_first_catch_time, target_time
        case 1:
            return True, arrive_first_catch_time, target_time
        case 2:
            # 本地端無檔案或無資料，故採用與當前時間抓間隔作大致比較
            now = datetime.now()
            if os.environ.get("job_start_time_point") is None:
                user_start_time_obj = now - configSetting.fetch_inteval
            else:
                user_start_time_obj = datetime.strptime(os.environ.get("job_start_time_point"), "%Y-%m-%d %H:%M:%S")
            user_end_time_obj = now
            if target_time_obj >= user_end_time_obj:
                arrive_first_catch_time = False
            if (target_time_obj > user_start_time_obj) and (target_time_obj < user_end_time_obj):
                return True, arrive_first_catch_time, target_time
            else:
                return False, arrive_first_catch_time, target_time

    # # True : 還能抓 False:不能抓
    # return targetTimeObj > userTimeObj


def makeHyperlink(value, name, index="1") -> str:
    url = "#{}!A{}"
    return '=HYPERLINK("%s", "%s")' % (url.format(value, index), name)


# 陣列分群輔助函式
def split(a, n) -> list:
    k, m = divmod(len(a), n)
    return list((a[i * k + min(i, m) : (i + 1) * k + min(i + 1, m)] for i in range(n)))


# 嘗試透過profile個人頁連結擷取userid
def parseFBUserID(url) -> str:
    keyword = "?id="
    pos = url.find(keyword)
    if pos == -1:
        return ""
    else:
        userid = url[pos + 4 :]
        return userid


def checkTimeCooldown(recordTime: datetime) -> bool:
    time_now = datetime.now()

    time_delta = time_now - recordTime
    cooldown = configSetting.cooldown_timedelta

    if cooldown <= time_delta.seconds:
        return True
    else:
        return False


def convert_xls_datetime(xls_date):
    return datetime(1899, 12, 30) + timedelta(days=xls_date)


def strF2H(text:str)->str:
    # 字串全形轉半形
    FH = (
        # space
        (u"　", u" "),
        # number
        (u"０", u"0"), (u"１", u"1"), (u"２", u"2"), (u"３", u"3"), (u"４", u"4"),
        (u"５", u"5"), (u"６", u"6"), (u"７", u"7"), (u"８", u"8"), (u"９", u"9"),
        # alpha
        (u"ａ", u"a"), (u"ｂ", u"b"), (u"ｃ", u"c"), (u"ｄ", u"d"), (u"ｅ", u"e"),
        (u"ｆ", u"f"), (u"ｇ", u"g"), (u"ｈ", u"h"), (u"ｉ", u"i"), (u"ｊ", u"j"),
        (u"ｋ", u"k"), (u"ｌ", u"l"), (u"ｍ", u"m"), (u"ｎ", u"n"), (u"ｏ", u"o"),
        (u"ｐ", u"p"), (u"ｑ", u"q"), (u"ｒ", u"r"), (u"ｓ", u"s"), (u"ｔ", u"t"),
        (u"ｕ", u"u"), (u"ｖ", u"v"), (u"ｗ", u"w"), (u"ｘ", u"x"), (u"ｙ", u"y"), (u"ｚ", u"z"),
        (u"Ａ", u"A"), (u"Ｂ", u"B"), (u"Ｃ", u"C"), (u"Ｄ", u"D"), (u"Ｅ", u"E"),
        (u"Ｆ", u"F"), (u"Ｇ", u"G"), (u"Ｈ", u"H"), (u"Ｉ", u"I"), (u"Ｊ", u"J"),
        (u"Ｋ", u"K"), (u"Ｌ", u"L"), (u"Ｍ", u"M"), (u"Ｎ", u"N"), (u"Ｏ", u"O"),
        (u"Ｐ", u"P"), (u"Ｑ", u"Q"), (u"Ｒ", u"R"), (u"Ｓ", u"S"), (u"Ｔ", u"T"),
        (u"Ｕ", u"U"), (u"Ｖ", u"V"), (u"Ｗ", u"W"), (u"Ｘ", u"X"), (u"Ｙ", u"Y"), (u"Ｚ", u"Z"),
        # punctuation
        (u"．", u"."), (u"，", u","), (u"！", u"!"), (u"？", u"?"), (u"”", u'"'),
        (u"'", u"'"), (u"‘", u"`"), (u"＠", u"@"), (u"＿", u"_"), (u"：", u":"),
        (u"；", u";"), (u"＃", u"#"), (u"＄", u"$"), (u"％", u"%"), (u"＆", u"&"),
        (u"（", u"("), (u"）", u")"), (u"‐", u"-"), (u"＝", u"="), (u"＊", u"*"),
        (u"＋", u" "), (u"－", u"-"), (u"／", u"/"), (u"＜", u"<"), (u"＞", u">"),
        (u"［", u"["), (u"￥", u"\\"), (u"］", u"]"), (u"＾", u"^"), (u"｛", u"{"),
        (u"｜", u"|"), (u"｝", u"}"), (u"～", u"~"),
    )
    translator = str.maketrans(dict(FH))

    return text.translate(translator)



def clear_four_bytes_utf8(text:str)->str:
    output = ""
    output = "".join(c for c in text if len(c.encode("utf8")) < 4)
    return output


def match_all_keywords(text:str, keywords:list[str]) -> list[str]:
    return [kw for kw in keywords if kw in text]