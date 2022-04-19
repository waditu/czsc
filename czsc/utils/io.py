# coding: utf-8

import os
import pickle
import json
import zipfile


def save_pkl(data, file):
    with open(file, "wb") as f:
        pickle.dump(data, f)


def read_pkl(file):
    with open(file, "rb") as f:
        data = pickle.load(f)
    return data


def save_json(data, file):
    with open(file, "w", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def read_json(file):
    with open(file, "r", encoding='utf-8') as f:
        data = json.load(f)
    return data


def make_zip(source_dir: str, file_zip: str) -> None:
    """打包目录为zip文件

    :param source_dir: 文件夹路径
    :param file_zip: 输出 zip 文件名称
    :return: None
    """
    assert os.path.isdir(source_dir)

    f = zipfile.ZipFile(file_zip, 'w', compression=zipfile.ZIP_DEFLATED)
    for parent, _, filenames in os.walk(source_dir):
        for filename in filenames:
            file = os.path.join(parent, filename)
            f.write(file, file.replace(source_dir, ""))
    f.close()
    print(f"compress {source_dir} into {file_zip} success.")
