import configSetting
from ioService import writer
def send_msg_to_bot(msg: str) -> None:
    try:
        configSetting.telegram_bot.sendMessage(chat_id=configSetting.telegram_bot_group_id, text=msg)
    except Exception as e:
        writer.writeLogToFile(traceBack=e, isError=True)

def send_img_to_bot(img_path: str, extra_text: str = "") -> None:
    try:
        configSetting.telegram_bot.sendPhoto(chat_id=configSetting.telegram_bot_group_id, photo=open(img_path, 'rb'),
                                       caption=extra_text)
        # # os.remove(img_path)
        # Auxiliary.delete_file_from_system(file_path=img_path)
    except Exception as e:
        writer.writeLogToFile(traceBack=e, isError=True)
        writer.writeLogToFile(traceBack=f"msg length: {len(extra_text)}", isError=True)