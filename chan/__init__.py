# coding: utf-8
import os
import shutil
from . import a


author = "zengbin93"
version = "0.0.2"
email = "zeng_bin8888@163.com"


cache_path = os.path.join(os.path.expanduser('~'), ".chan")
if not os.path.exists(cache_path):
    os.mkdir(cache_path)


def clean_cache():
    shutil.rmtree(cache_path)
    os.mkdir(cache_path)


