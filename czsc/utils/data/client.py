import os
import time
import shutil
import loguru
import hashlib
import requests
import threading
import pandas as pd
from pathlib import Path
from functools import partial, lru_cache
from typing import Optional, Dict, Any


def set_url_token(token, url, **kwargs):
    """设置指定 URL 数据接口的凭证码，通常一台机器只需要设置一次即可

    :param token: 凭证码
    :param url: 数据接口地址
    """
    logger = kwargs.get("logger", loguru.logger)
    hash_key = hashlib.md5(str(url).encode("utf-8")).hexdigest()
    file_token = Path("~").expanduser() / f"{hash_key}.txt"
    with open(file_token, "w", encoding="utf-8") as f:
        f.write(token)
    logger.info(f"{url} 数据访问凭证码已保存到 {file_token}")


def get_url_token(url, **kwargs):
    """获取指定 URL 数据接口的凭证码"""
    logger = kwargs.get("logger", loguru.logger)
    hash_key = hashlib.md5(str(url).encode("utf-8")).hexdigest()
    file_token = Path("~").expanduser() / f"{hash_key}.txt"
    if file_token.exists():
        logger.info(f"从 {file_token} 读取 {url} 的访问凭证码")
        return open(file_token, "r", encoding="utf-8").read()

    logger.warning(f"请设置 {url} 的访问凭证码，如果没有请联系管理员申请")
    token = input(f"请输入 {url} 的访问凭证码（token）：")
    if token:
        set_url_token(token, url)
        return token
    return None


class DataClient:
    """
    数据接口客户端，支持本地缓存，兼容Tushare数据接口。
    支持多线程/多进程安全，详细日志，异常处理。
    """
    __version__ = "V250719"
    _cache_lock = threading.Lock()  # 进程内线程锁，防止并发冲突
    
    @lru_cache(maxsize=128)
    def _get_cache_key(self, req_params_str: str) -> str:
        """缓存哈希计算，避免重复计算"""
        return hashlib.md5(req_params_str.encode('utf-8')).hexdigest().upper()[:8]

    def __init__(self, token: Optional[str] = None, url: str = "http://api.tushare.pro", timeout: int = 300, verbose: bool = False, **kwargs):
        """
        初始化数据客户端。
        :param token: str, API接口TOKEN
        :param url: str, API接口地址
        :param timeout: int, 请求超时时间
        :param verbose: bool, 是否开启详细日志模式，显示请求细节
        :param kwargs: 其他参数（clear_cache, cache_path, logger）
        """
        from czsc.utils.cache import get_dir_size
        self.logger = kwargs.pop("logger", loguru.logger)

        self.__token = token or get_url_token(url, logger=self.logger)
        self.__http_url = url
        self.__timeout = timeout
        self.__url_hash = hashlib.md5(str(url).encode("utf-8")).hexdigest()[:8]
        assert self.__token, "请设置czsc_token凭证码，如果没有请联系管理员申请"
        self.cache_path = Path(kwargs.get("cache_path", os.path.expanduser("~/.quant_data_cache")))
        self.cache_path.mkdir(exist_ok=True, parents=True)
        self.verbose = verbose
        if self.verbose:
            self.logger.info(
                f"数据URL: {url} 数据缓存路径：{self.cache_path} 占用磁盘空间：{get_dir_size(self.cache_path) / 1024 / 1024:.2f} MB"
            )
        if kwargs.get("clear_cache", False):
            self.clear_cache()

    def _get_cache(self, file_cache: Path, api_name: str, kwargs: Dict[str, Any], logger) -> Optional[pd.DataFrame]:
        """读取缓存"""
        if file_cache.exists():
            with self._cache_lock:
                try:
                    df = pd.read_pickle(file_cache)
                    if self.verbose:
                        logger.info(f"缓存命中 | API：{api_name}；参数：{kwargs}；数据量：{df.shape}")
                    return df
                except Exception as e:
                    logger.warning(f"读取缓存文件失败: {file_cache}, 错误: {e}")
        return None

    def _set_cache(self, file_cache: Path, df: pd.DataFrame, logger) -> None:
        """写入缓存"""
        with self._cache_lock:
            try:
                df.to_pickle(file_cache)
            except Exception as e:
                logger.warning(f"写入缓存文件失败: {file_cache}, 错误: {e}")

    def _request_api(self, req_params: Dict[str, Any], api_name: str, kwargs: Dict[str, Any], logger, retries: int = 3) -> Optional[requests.Response]:
        """发起API请求，包含重试机制"""
        for attempt in range(retries):
            try:
                res = requests.post(self.__http_url, json=req_params, timeout=self.__timeout)
                if res.status_code == 200:
                    return res
                else:
                    # 处理非200状态码
                    if attempt == retries - 1:
                        logger.error(f"API请求失败(最后一次重试): {api_name}；参数：{kwargs}；状态码：{res.status_code}；响应：{res.text}")
                        return None
                    else:
                        logger.warning(f"API请求失败(第{attempt+1}次重试): {api_name}；状态码：{res.status_code}；响应：{res.text}")
                        time.sleep(0.5 * (attempt + 1))  # 递增延迟
                        continue
                
            except requests.RequestException as e:
                if attempt == retries - 1:
                    logger.error(f"请求API失败(最后一次重试): {api_name}；参数：{kwargs}；错误: {e}")
                    return None
                else:
                    logger.warning(f"请求API失败(第{attempt+1}次重试): {api_name}；错误: {e}")
                    time.sleep(0.5 * (attempt + 1))  # 递增延迟
                    
            except Exception as e:
                logger.error(f"请求API失败: {api_name}；参数：{kwargs}；错误: {e}")
                return None
        
        logger.error(f"API请求失败，所有重试都失败")
        return None

    def _validate_response(self, res: requests.Response, api_name: str, kwargs: Dict[str, Any], logger) -> Optional[Dict[str, Any]]:
        """校验API返回结构
        
        结构说明：
        {
            "code": 0,
            "data": {
                "items": [
                    {
                        "field1": "value1",
                        "field2": "value2"
                    }
                ],
                "fields": ["field1", "field2"]
            },
            "message": "success"
        }
        """
        try:
            result = res.json()
        except Exception as e:
            logger.error(f"API返回非JSON格式: {e}")
            return None
        if not isinstance(result, dict) or "code" not in result:
            logger.error(f"API返回结构异常: {result}")
            return None
        if result["code"] != 0:
            logger.error(f"API: {api_name} - {kwargs} 数据获取失败: {result}")
            return None
        data = result.get("data", {})
        if not isinstance(data, dict) or "items" not in data or "fields" not in data:
            logger.error(f"API返回data结构异常: {data}")
            return None
        return data

    def _build_dataframe(self, data: Dict[str, Any], logger) -> pd.DataFrame:
        """构建DataFrame"""
        try:
            df = pd.DataFrame(data["items"], columns=data["fields"])
            return df
        except Exception as e:
            self.logger.error(f"DataFrame构建失败: {e}")
            return pd.DataFrame()

    def clear_cache(self, **kwargs) -> None:
        """
        清空缓存目录。加锁防止并发冲突。
        """
        logger = kwargs.pop("logger", self.logger)
        with self._cache_lock:
            if self.cache_path.exists():
                try:
                    shutil.rmtree(self.cache_path)
                except Exception as e:
                    logger.warning(f"清空缓存时出错: {e}")
            if self.verbose:
                logger.info(f"{self.cache_path} 路径下的数据缓存已清空")
            self.cache_path.mkdir(exist_ok=True, parents=True)

    def clear_api_cache(self, api_name: str, expiration: int = -1) -> None:
        """
        清除指定API的缓存文件，过期时间单位秒。
        """
        path = self.cache_path / f"{self.__url_hash}_{api_name}"
        if path.exists() and expiration > 0:
            with self._cache_lock:
                for file in path.glob("*"):
                    if time.time() - file.stat().st_mtime > expiration:
                        try:
                            file.unlink()
                            if self.verbose:
                                self.logger.info(f"清除缓存文件: {file}")
                        except Exception as e:
                            self.logger.error(f"删除缓存文件失败: {file}, 错误: {e}")
        else:
            if self.verbose:
                self.logger.warning(f"未找到缓存目录: {path}")

    def post_request(self, api_name: str, fields: str = "", **kwargs) -> pd.DataFrame:
        """
        执行API数据查询，主流程调度。
        """
        if not api_name or not isinstance(api_name, str):
            raise ValueError(f"无效的api_name: {api_name}")

        logger = self.logger
        v = kwargs.get("v", 2)
        stime = time.time()
        if api_name in ["__getstate__", "__setstate__"]:
            return pd.DataFrame()

        ttl = int(kwargs.pop("ttl", -1))
        req_params = {
            "api_name": api_name,
            "token": self.__token,
            "params": kwargs,
            "fields": fields,
            "v": v
        }
        path = self.cache_path / f"{self.__url_hash}_{api_name}"
        path.mkdir(exist_ok=True, parents=True)
        cache_key = self._get_cache_key(str(req_params))
        file_cache = path / f"{cache_key}.pkl"

        # 读取缓存
        if file_cache.exists() and (ttl == -1 or time.time() - file_cache.stat().st_mtime < ttl):
            df = self._get_cache(file_cache, api_name, kwargs, logger)
            if df is not None:
                return df

        # 网络请求
        res = self._request_api(req_params, api_name, kwargs, logger)
        if res is None:
            return pd.DataFrame()

        # 校验返回结构
        data = self._validate_response(res, api_name, kwargs, logger)
        if data is None:
            return pd.DataFrame()

        # 构建DataFrame
        df = self._build_dataframe(data, logger)
        if df.empty:
            return df

        # 写缓存
        self._set_cache(file_cache, df, logger)

        if self.verbose:
            logger.info(f"本次获取数据总耗时：{time.time() - stime:.2f}秒；API：{api_name}；参数：{kwargs}；数据量：{df.shape}")
        return df

    def __getattr__(self, name):
        """
        动态API方法调用，等价于 self.post_request(name, ...)
        """
        return partial(self.post_request, name)

