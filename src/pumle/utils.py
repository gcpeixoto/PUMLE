import numpy as np
import json


def convert_ndarray(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_ndarray(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_ndarray(i) for i in obj]
    else:
        return obj


def read_json(json_path):
    with open(json_path, "r", encoding="utf-8") as file:
        readed_json = json.load(file)
    return readed_json


def write_json(json_path, data):
    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)
