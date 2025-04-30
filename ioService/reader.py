import os
import json


def readInputJson(target_file="./config/input.json") -> dict:
    has_file = os.path.isfile(target_file)

    if has_file is True:
        with open(target_file, encoding='utf_8') as f:
            json_array_data = json.load(f)
            f.close()
    return json_array_data
