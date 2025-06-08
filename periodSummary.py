import configSetting
import os
import difflib
import time
import pandas as pd
from ioService import writer
from datetime import datetime, timedelta
from docxtpl import DocxTemplate, InlineImage
from docx.shared import Cm
from wordDocExtension import DocxExtension
from docx import Document
from docx.document import Document as TDocument
from ioService import google_drive_api as google_drive_handler
from webManager import webDriver
from docx.shared import RGBColor

post_driver = webDriver.postsDriver(driver=None, options=None, isLogin=False)
post_driver.setOptions(needHeadless=configSetting.need_headless, needImage=False)
print("進行截圖器創建")
post_driver.driverInitialize()

#  先明確要抓取的起迄時間
end_date = datetime.now()
start_date = end_date - timedelta(days=7)
similarity_threshold = 0.75  # 設定相似度閾值

# 靜態參數
target_dir = f"{configSetting.output_root}當日彙整"
output_filename = f"report_{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}.docx"
output_excel_filename = f"report_{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}.xlsx"
output_path = f"{configSetting.ROOT_PATH}/output/定期報告/{output_filename}"
output_excel_path = f"{configSetting.ROOT_PATH}/output/定期報告/{output_excel_filename}"
target_detail_map = dict()

# 建立目標的map 後續存取相關資料
for target in configSetting.json_array_data["targets"]:
    target_name = target["targetName"]
    target_detail_map[target_name] = {
        "targetType": target["targetType"],
        "targetID": target["targetID"],
        "targetPopularity": target["targetPopularity"],
        "targetURL": target["targetURL"],
    }
    
# 讀取資料夾中的所有 Excel 檔案

restore_data_dir_list = os.listdir(path=target_dir)
current_month_dir_list = []
df = pd.DataFrame()

for dir in restore_data_dir_list:
    if "." in dir:
        continue
    dir_date = "-".join(dir.split("-")[1:])
    temp_date = datetime.strptime(dir_date, "%Y-%m-%d")
    # 檢查日期是否在指定範圍內
    if start_date <= temp_date <= end_date:
        current_month_dir_list.append(f"summery-{dir_date}")

# 讀取符合條件的 Excel 檔案並合併
for dir in current_month_dir_list:
    excel_path = f"{target_dir}/{dir}/summery-collection.xlsx"
    temp_df = pd.read_excel(excel_path, sheet_name="collection", usecols="B:U", converters={"文章id": str})
    df = pd.concat([df, temp_df], axis=0, ignore_index=True)
    
# 將時間列轉換為 datetime 格式
df["時間"] = pd.to_datetime(df["時間"], format="%Y-%m-%d %H:%M:%S")

# 遍歷 DataFrame 的每一行，組建一個新欄位: 截圖路徑
def build_screenshot_path(row):
    post_id = row["文章id"]
    date_str = f"summery-{row['時間'].strftime('%Y-%m-%d')}"
    return f"{target_dir}/{date_str}/img/{post_id}.png"
df["截圖路徑"] = df.apply(build_screenshot_path, axis=1)


# 開始進行影響力狀態更新(by 爬蟲)
is_dead_list = list()
for idx, row in df.iterrows():
    target_url = row["文章網址"]
    page_resource = post_driver.influenceReview(pageURL=target_url)
    if "videos" in target_url:
        thumb_count, comment_count, share_count, is_dead = post_driver.parsePageSource(page_resource, target_url, source_type="video")
    else:
        thumb_count, comment_count, share_count, is_dead = post_driver.parsePageSource(page_resource, target_url, source_type="post")
    print(f"文章網址: {target_url}, 按讚數: {thumb_count}, 留言數: {comment_count}, 分享數: {share_count}")
    is_dead_list.append(is_dead)
    if thumb_count > row['按讚數']:
        df.at[idx, '按讚數'] = thumb_count
    if comment_count > row['留言數']:
        df.at[idx, '留言數'] = comment_count
    if share_count > row['分享數']:
        df.at[idx, '分享數'] = share_count

df["已失效"] = is_dead_list
    


# 開始做資料間的文案相似度比對，聚合出以文案為主體的dictionary
# 採用python 內建套件: difflib
# 相似度達到 0.9 以上的視為同一篇文章
def group_similar_posts(df, threshold=similarity_threshold):
    post_dict = {}
    for idx, row in df.iterrows():
        content = row["內容"]
        if pd.isna(content) or content == "":
            continue
        found = False
        for key in post_dict.keys():
            similarity = difflib.SequenceMatcher(None, content, key).ratio()
            if similarity >= threshold:
                post_dict[key].append(row.to_dict())
                found = True
                break
        if not found:
            post_dict[content] = [row.to_dict()]
    return post_dict


# 採用python 內建套件: difflib
# 相似度達到 0.9 以上的視為同一個發文者(因為無論怎麼改名, 個人網址不會改變)
def group_similar_posters(df, threshold=0.9):
    post_dict = {}
    for idx, row in df.iterrows():
        content = row["發文者個人網址"]
        if pd.isna(content) or content == "":
            continue
        found = False
        for key in post_dict.keys():
            similarity = difflib.SequenceMatcher(None, content, key).ratio()
            if similarity >= threshold:
                post_dict[key].append(row.to_dict())
                found = True
                break
        if not found:
            post_dict[content] = [row.to_dict()]
    return post_dict


# 聚合發文者的資料，並另外輸出成一個excel檔案
res_of_agg_posters = group_similar_posters(df)
for key, value in res_of_agg_posters.items():
    represent_name = value[0]["發文者"]
    agg_df = pd.DataFrame.from_dict(value)
    # 先檢查檔案是否存在, 若存在則覆蓋
    if os.path.isfile(output_excel_path):
        mode = "a"
    else:
        mode = "w"
    writer.pdToExcel(
    df=agg_df,
    sheetName=represent_name,
    des=output_excel_path,
    autoFitIsNeed=False,
    mode=mode,
    )
writer.writeLogToFile(f"共聚合出 {len(res_of_agg_posters)} 個發文者", isError=False)



# 開始進行文章聚合
res = group_similar_posts(df)
writer.writeLogToFile(f"共聚合出 {len(res)} 篇文章", isError=False)

# 將聚合後的資料寫入 Word 檔案
tpl = DocxTemplate(f"{configSetting.ROOT_PATH}/template/report_template.docx")
context = {
    "target_detail_map": target_detail_map,
    "start_date_title": f"{start_date.strftime('%m')}{start_date.strftime('%d')}",
    "end_date_title": f"{end_date.strftime('%m')}{end_date.strftime('%d')}",
    "start_date": start_date.strftime('%Y/%m/%d'),
    "end_date": end_date.strftime('%Y/%m/%d'),
    "article_list": []
}
hyperlink_name_list = []
hyperlink_url_list = []

for content, records in res.items():
    if len(content) > 300:
        content = content[:300] + "..."
    article_dict = {
        "content": content,
        "img": InlineImage(tpl, records[0]["截圖路徑"], width=Cm(10), height=Cm(11)),
        "spread_list": [],
        "influence":"",
    }
    total_comment = 0
    total_thumb = 0
    total_share = 0
    for record in records:
        total_comment += record["留言數"]
        total_thumb += record["按讚數"]
        total_share += record["分享數"]
        post_date = record["時間"].strftime("%m%d%H%M")
        # account_element 主要是佔位符設計，要確保唯一性，供後續超連結添加進行定位(最終的view呈現是在超連結處處理)
        account_element = f"{record['發文者']}_{post_date}_{record['文章id']}_placeholder"
        hyperlink_name_list.append(account_element)
        hyperlink_url_list.append(record["發文者個人網址"])
        
        endpoint_element = f"{record['粉專名稱']}_{target_detail_map[record['粉專名稱']]['targetPopularity']}_{record['文章id']}_{record['已失效']}"
        hyperlink_name_list.append(endpoint_element)
        hyperlink_url_list.append(record["文章網址"])
        article_dict["spread_list"].append({
            "account": account_element,
            "endpoint": endpoint_element,
        })
    # 計算影響力
    total_influence = total_comment + total_thumb + total_share
    article_dict["total_influence"] = total_influence
    article_dict["influence"] = f"{total_comment} + {total_thumb} + {total_share} = {total_influence}"
    context["article_list"].append(article_dict)

# 讓資料依據影響力排序
context["article_list"].sort(key=lambda x: x["total_influence"], reverse=True)

# 儲存與渲染檔案
tpl.render(context)
tpl.save(output_path)


tpl_doc: TDocument = Document(output_path)
# 添加超連結(搜表格內部的文字)

for table in tpl_doc.tables:
    for row in table.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                for name, url in zip(hyperlink_name_list, hyperlink_url_list):
                    if name in p.text:
                        p.clear()
                        splits =  name.split("_")
                        main_name, describe, is_dead = splits[0], splits[1], splits[3]
                        DocxExtension.add_hyperlink(paragraph=p, 
                                                    url=url,
                                                    text=main_name, 
                                                    color="0377fc",
                                                    underline=False)
                        p.add_run(f" {describe}")
                        if is_dead == "True":
                            dead_note = p.add_run(f" (已被檢舉下架)")
                            dead_note.font.color.rgb = RGBColor(255, 51, 0)
                        break
tpl_doc.save(output_path)
writer.writeLogToFile(f"定期報告已生成: {output_filename}", isError=False)

time.sleep(2)  # 確保檔案寫入完成

# 將檔案上傳到google drive 
google_drive_handler.upload_file_to_drive(output_path, configSetting.json_array_data["google-drive-upload-setting"]["uploadFolderID"])
writer.writeLogToFile(f"定期報告已上傳: {output_filename}", isError=False)

# 關閉截圖器
post_driver.clearDriver()