import pandas as pd
import win32com.client as win32
import os
import traceback
import configSetting
import xlwings as xw
from xlwings import Sheet
from datetime import datetime


def pdToExcel(
    des, df: pd.DataFrame, sheetName, mode="w", autoFitIsNeed=True, indexIsNeed=True
) -> None:

    file_dir = os.path.dirname(os.path.realpath("__file__"))
    filename = os.path.join(file_dir, des)

    # product csv file
    # filename_csv = filename.replace(".xlsx", "_" + sheetName + ".csv")
    # df.to_csv(filename_csv, index=False, encoding='utf_8_sig')

    if indexIsNeed is True:
        if mode == "w":
            with pd.ExcelWriter(filename, mode=mode, engine="openpyxl") as writer:
                df.to_excel(writer, index_label="id", sheet_name=sheetName)
        else:
            with pd.ExcelWriter(
                filename, mode=mode, engine="openpyxl", if_sheet_exists="replace"
            ) as writer:
                df.to_excel(writer, index_label="id", sheet_name=sheetName)
    else:
        if mode == "w":
            with pd.ExcelWriter(filename, mode=mode, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name=sheetName)
        else:
            with pd.ExcelWriter(
                filename, mode=mode, engine="openpyxl", if_sheet_exists="replace"
            ) as writer:
                df.to_excel(writer, index=False, sheet_name=sheetName)

    if autoFitIsNeed is True:
        try:
            excel = win32.DispatchEx("Excel.Application")
            wb = excel.Workbooks.Open(filename)
            ws = wb.Worksheets(sheetName)
            ws.Columns.AutoFit()
            wb.Save()
            excel.Application.Quit()
        except:
            writeLogToFile(traceback.format_exc(), True)
            print(f"Some error were founded, failed to formated the excel file : {des}")

        # for column in df:
        #     print(column)
        #     print(df[column].astype(str).map(len))
        #     column_length = max(df[column].astype(str).map(len).max(), len(column))
        #     col_idx = df.columns.get_loc(column)
        #     writer.sheets[sheetName].set_column(col_idx, col_idx, column_length)


def writeLogToFile(traceBack, isError:bool=False) -> None:
    now = datetime.now()
    now_for_filename = now.strftime("%Y-%m-%d")
    now_for_log = now.strftime("%Y-%m-%d, %H:%M:%S")
    if isError:
        filename = f"{configSetting.ROOT_PATH}/log/" + now_for_filename + "-error.log"
    else:
        filename = f"{configSetting.ROOT_PATH}/log/" + now_for_filename + "-access.log"
    sourceFile = open(filename, "a", encoding="utf_8_sig")
    print(f"[{now_for_log}] : {traceBack}", file=sourceFile)
    sourceFile.close()


def writeTempFile(filename, content, mode="w") -> None:
    f = open(
        f"{configSetting.ROOT_PATH}/temp/" + filename + ".txt",
        mode=mode,
        encoding="utf_8_sig",
    )
    f.write(content)
    f.close()


def writeJsonFile(filename, content) -> None:
    f = open(
        f"{configSetting.ROOT_PATH}/temp/" + filename + ".json",
        "w",
        encoding="utf_8_sig",
    )
    f.write(content)
    f.close()


def copyFileFromSrcToDst(src: str, dst: str) -> None:
    command = f"copy {src} {dst}"
    os.system(command)


def updateDataToExcelCertainCell(
    data: pd.DataFrame, filename: str, sheetname: str, cell_index: str
) -> None:
    app = xw.App(visible=False)
    wb = xw.Book(filename)
    ws: Sheet = wb.sheets[sheetname]
    ws.range(cell_index).options(index=False, header=False).value = data

    wb.save()
    wb.close()
    app.quit()


def updateFormulaToExcel(filename: str, sheetname: str, start: int, end: int) -> None:
    app = xw.App(visible=False)
    wb = xw.Book(filename)
    ws: Sheet = wb.sheets[sheetname]
    for i in range(start, end + 1):
        ws.range(f"T{i}").formula = (
            f'=IF($E{i}="V",$E$4,0)+IF($F{i}="V",$F$4,0)+IF($G{i}="V",$G$4,0)+IF($H{i}="V",$H$4,0)+IF($I{i}="V",$I$4,0)+IF($J{i}="V",$J$4,0)+IF($K{i}="V",$K$4,0)+IF($L{i}="V",$L$4,0)+IF($M{i}="V",$M$4,0)+IF($N{i}="V",$N$4,0)+IF($O{i}="V",$O$4,0)+IF($P{i}="V",$P$4,0)+IF($Q{i}="V",$Q$4,0)+IF($R{i}="V",$R$4,0)'
        )
    wb.save()
    wb.close()
    app.quit()
