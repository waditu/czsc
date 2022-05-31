# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/7/16 11:51
"""

import os
import shutil

home_path = os.path.join(os.path.expanduser("~"), '.czsc')
os.makedirs(home_path, exist_ok=True)


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


