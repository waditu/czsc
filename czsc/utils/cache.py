# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/7/16 11:51
"""

import os
import time
import dill
import shutil
import hashlib
import json
import pandas as pd
from pathlib import Path
from loguru import logger
from typing import Any


home_path = Path(os.environ.get("CZSC_HOME", os.path.join(os.path.expanduser("~"), '.czsc')))
home_path.mkdir(parents=True, exist_ok=True)


def get_dir_size(path):
    """获取目录大小，单位：Bytes"""
    total = 0
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += get_dir_size(entry.path)
    return total


def empty_cache_path():
    shutil.rmtree(home_path)
    os.makedirs(home_path, exist_ok=False)
    print(f"已清空缓存文件夹：{home_path}")


class DiskCache:
    def __init__(self, path=None):
        self.path = home_path / "disk_cache" if path is None else Path(path)
        if self.path.is_file():
            raise Exception("path has exist")

        self.path.mkdir(parents=True, exist_ok=True)

    def __str__(self) -> str:
        return "DiskCache: " + str(self.path)

    def is_found(self, k: str, suffix: str = "pkl", ttl=-1) -> bool:
        """判断缓存文件是否存在

        :param k: 缓存文件名
        :param suffix: 缓存文件后缀，支持 pkl, json, txt, csv, xlsx
        :param ttl: 缓存文件有效期，单位：秒，-1 表示永久有效
        :return: bool
        """
        file = self.path / f"{k}.{suffix}"
        if not file.exists():
            logger.info(f"文件不存在, {file}")
            return False

        if ttl > 0:
            create_time = file.stat().st_ctime
            if (time.time() - create_time) > ttl:
                logger.info(f"缓存文件已过期, {file}")
                return False

        return file.exists()

    def get(self, k: str, suffix: str = "pkl") -> Any:
        """读取缓存文件

        :param k: 缓存文件名
        :param suffix: 缓存文件后缀，支持 pkl, json, txt, csv, xlsx
        :return: 缓存文件内容
        """
        file = self.path / f"{k}.{suffix}"
        logger.info(f"正在读取缓存记录，地址：{file}")
        if not file.exists():
            logger.warning(f"文件不存在, {file}")
            return None

        if suffix == "pkl":
            res = dill.load(open(file, 'rb'))
        elif suffix == "json":
            res = json.load(open(file, 'r', encoding='utf-8'))
        elif suffix == "txt":
            res = file.read_text(encoding='utf-8')
        elif suffix == "csv":
            res = pd.read_csv(file, encoding='utf-8')
        elif suffix == "xlsx":
            res = pd.read_excel(file)
        else:
            raise ValueError(f"suffix {suffix} not supported")
        return res

    def set(self, k: str, v: Any, suffix: str = "pkl"):
        """写入缓存文件

        :param k: 缓存文件名
        :param v: 缓存文件内容
        :param suffix: 缓存文件后缀，支持 pkl, json, txt, csv, xlsx
        """
        file = self.path / f"{k}.{suffix}"
        if file.exists():
            logger.info(f"缓存文件 {file} 将被覆盖")

        if suffix == "pkl":
            dill.dump(v, open(file, 'wb'))

        elif suffix == "json":
            if not isinstance(v, dict):
                raise ValueError("suffix json only support dict")
            json.dump(v, open(file, 'w', encoding='utf-8'), ensure_ascii=False, indent=4)

        elif suffix == "txt":
            if not isinstance(v, str):
                raise ValueError("suffix txt only support str")
            file.write_text(v, encoding='utf-8')

        elif suffix == "csv":
            if not isinstance(v, pd.DataFrame):
                raise ValueError("suffix csv only support pd.DataFrame")
            v.to_csv(file, index=False, encoding='utf-8')

        elif suffix == 'xlsx':
            if not isinstance(v, pd.DataFrame):
                raise ValueError("suffix xlsx only support pd.DataFrame")
            v.to_excel(file, index=False)

        else:
            raise ValueError(f"suffix {suffix} not supported")

        logger.info(f"已写入缓存文件：{file}")

    def remove(self, k: str, suffix: str = "pkl"):
        file = self.path / f"{k}.{suffix}"
        logger.info(f"准备删除缓存文件：{file}")
        Path.unlink(file) if Path.exists(file) else None


def disk_cache(path: str, suffix: str = "pkl", ttl: int = -1):
    """缓存装饰器，支持多种数据格式

    :param path: 缓存文件夹路径
    :param suffix: 缓存文件后缀，支持 pkl, json, txt, csv, xlsx
    :param ttl: 缓存文件有效期，单位：秒
    """
    assert suffix in ["pkl", "json", "txt", "csv", "xlsx"], "suffix not supported"

    def decorator(func):
        nonlocal path
        _c = DiskCache(path=Path(path) / func.__name__)

        def cached_func(*args, **kwargs):
            hash_str = f"{func.__name__}{args}{kwargs}"
            k = hashlib.md5(hash_str.encode('utf-8')).hexdigest().upper()[:8]
            k = f"{k}_{func.__name__}"

            if _c.is_found(k, suffix=suffix, ttl=ttl):
                output = _c.get(k, suffix=suffix)
                return output

            else:
                output = func(*args, **kwargs)
                _c.set(k, output, suffix=suffix)
                return output

        return cached_func

    return decorator
