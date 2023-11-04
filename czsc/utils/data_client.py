import os
import hashlib
import requests
import pandas as pd
from time import time
from pathlib import Path
from loguru import logger
from functools import partial


def set_url_token(token, url):
    """设置指定 URL 数据接口的凭证码，通常一台机器只需要设置一次即可

    :param token: 凭证码
    :param url: 数据接口地址
    """
    hash_key = hashlib.md5(str(url).encode('utf-8')).hexdigest()
    file_token = Path("~").expanduser() / f"{hash_key}.txt"
    with open(file_token, 'w', encoding='utf-8') as f:
        f.write(token)
    logger.info(f"{url} 数据访问凭证码已保存到 {file_token}")


def get_url_token(url):
    """获取指定 URL 数据接口的凭证码"""
    hash_key = hashlib.md5(str(url).encode('utf-8')).hexdigest()
    file_token = Path("~").expanduser() / f"{hash_key}.txt"
    if file_token.exists():
        return open(file_token, 'r', encoding='utf-8').read()
    logger.warning(f"请设置 {url} 的访问凭证码，如果没有请联系管理员申请")
    return None


class DataClient:
    def __init__(self, token=None, url='http://api.tushare.pro', timeout=30, **kwargs):
        """数据接口客户端，支持缓存，默认缓存路径为 ~/.quant_data_cache；兼容Tushare数据接口

        :param token: str API接口TOKEN，用于用户认证
        :param url: str API接口地址
        :param timeout: int, 请求超时时间
        :param kwargs: dict, 其他参数

            - clear_cache: bool, 是否清空缓存
            - cache_path: str, 缓存路径

        """
        self.__token = token or get_url_token(url)
        self.__http_url = url
        self.__timeout = timeout
        assert self.__token, "请设置czsc_token凭证码，如果没有请联系管理员申请"
        self.cache_path = Path(kwargs.get("cache_path", os.path.expanduser("~/.quant_data_cache")))
        self.cache_path.mkdir(exist_ok=True, parents=True)
        logger.info(f"数据缓存路径：{self.cache_path}")
        if kwargs.get("clear_cache", False):
            self.clear_cache()

    def clear_cache(self):
        """清空缓存"""
        for file in self.cache_path.glob("*.pkl"):
            file.unlink()
        logger.info(f"{self.cache_path} 路径下的数据缓存已清空")

    def post_request(self, api_name, fields='', **kwargs):
        """执行API数据查询

        :param api_name: str, 查询接口名称
        :param fields: str, 查询字段
        :param kwargs: dict, 查询参数
        :return: pd.DataFrame
        """
        stime = time()
        if api_name in ['__getstate__', '__setstate__']:
            return pd.DataFrame()

        req_params = {'api_name': api_name, 'token': self.__token, 'params': kwargs, 'fields': fields}
        hash_key = hashlib.md5(str(req_params).encode('utf-8')).hexdigest()
        file_cache = self.cache_path / f"{hash_key}.pkl"
        if file_cache.exists():
            df = pd.read_pickle(file_cache)
            logger.info(f"缓存命中 | API：{api_name}；参数：{kwargs}；数据量：{df.shape}")
            return df

        res = requests.post(self.__http_url, json=req_params, timeout=self.__timeout)
        if res:
            result = res.json()
            if result['code'] != 0:
                raise Exception(f"API: {api_name} - {kwargs} 数据获取失败: {result}")

            df = pd.DataFrame(result['data']['items'], columns=result['data']['fields'])
            df.to_pickle(file_cache)
        else:
            df = pd.DataFrame()

        logger.info(f"本次获取数据总耗时：{time() - stime:.2f}秒；API：{api_name}；参数：{kwargs}；数据量：{df.shape}")
        return df

    def __getattr__(self, name):
        return partial(self.post_request, name)
