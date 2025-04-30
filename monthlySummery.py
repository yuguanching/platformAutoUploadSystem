import configSetting
import os
import pandas as pd
from ioService import writer
from datetime import datetime

target_dir = f"{configSetting.output_root}/當日彙整"
current_month = datetime.now().month
restore_data_dir_list = os.listdir(path=target_dir)
current_month_dir_list = []
df = pd.DataFrame()

for dir in restore_data_dir_list:
    if "." in dir:
        continue
    dir_date = "-".join(dir.split("-")[1:])
    temp_date = datetime.strptime(dir_date, "%Y-%m-%d")
    # if dir_date in theList:
    #     current_month_dir_list.append(f"summery-{dir_date}")
    if temp_date.month == current_month:
        current_month_dir_list.append(f"summery-{dir_date}")

for dir in current_month_dir_list:
    excel_path = f"{target_dir}/{dir}/summery-collection.xlsx"
    temp_df = pd.read_excel(excel_path, sheet_name="collection", usecols="B:R")
    df = pd.concat([df, temp_df], axis=0, ignore_index=True)

writer.pdToExcel(
    df=df,
    sheetName="collection",
    # des=f"{target_dir}/special-summery-collection.xlsx",
    des=f"{target_dir}/{current_month}-summery-collection.xlsx",
    autoFitIsNeed=False,
    mode="w",
)
print(f"{current_month}月資料彙整完成")
