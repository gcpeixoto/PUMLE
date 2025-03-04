import numpy as np
import json
import hashlib


def generate_param_hash(params_dict: dict) -> str:
    """
    Gera um hash (ID único) a partir dos parâmetros do dicionário.
    """
    # dumps com sort_keys=True garante consistência na ordem das chaves
    param_str = json.dumps(params_dict, sort_keys=True)
    hash_obj = hashlib.md5(param_str.encode("utf-8")).hexdigest()
    return hash_obj[:8]


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
        return json.load(file)


def write_json(json_path, data):
    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)
