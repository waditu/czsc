# coding: utf-8
import os
from . import a


author = "zengbin93"
version = "0.0.1"
email = "zeng_bin8888@163.com"


cache_path = os.path.join(os.path.expanduser('~'), ".chan")
if not os.path.exists(cache_path):
    os.mkdir(cache_path)

