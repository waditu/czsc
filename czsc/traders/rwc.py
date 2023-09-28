# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/9/24 15:19
describe: 策略持仓权重管理
"""
import time
import json
import redis
import threading
import pandas as pd
from loguru import logger
from datetime import datetime


class RedisWeightsClient:
    """策略持仓权重收发客户端"""

    def __init__(self, strategy_name, redis_url, **kwargs):
        """
        :param strategy_name: str, 策略名
        :param redis_url: str, redis连接字符串

            For example::

                redis://[[username]:[password]]@localhost:6379/0
                rediss://[[username]:[password]]@localhost:6379/0
                unix://[username@]/path/to/socket.sock?db=0[&password=password]

            Three URL schemes are supported:

            - `redis://` creates a TCP socket connection. See more at:
            <https://www.iana.org/assignments/uri-schemes/prov/redis>
            - `rediss://` creates a SSL wrapped TCP socket connection. See more at:
            <https://www.iana.org/assignments/uri-schemes/prov/rediss>
            - ``unix://``: creates a Unix Domain Socket connection.

        """
        self.strategy_name = strategy_name
        self.redis_url = redis_url

        self.heartbeat_client = redis.from_url(redis_url, decode_responses=True)
        self.heartbeat_prefix = kwargs.get("heartbeat_prefix", "heartbeat")

        thread_safe_pool = redis.BlockingConnectionPool.from_url(redis_url, decode_responses=True)
        self.r = redis.Redis(connection_pool=thread_safe_pool)
        self.lua_publish = RedisWeightsClient.register_lua_publish(self.r)

        self.heartbeat_thread = threading.Thread(target=self.__heartbeat, daemon=True)
        self.heartbeat_thread.start()
        self.key_prefix = kwargs.get("key_prefix", "Weights")

    def set_metadata(self, base_freq, description, author, outsample_sdt, **kwargs):
        """设置策略元数据"""
        outsample_sdt = pd.to_datetime(outsample_sdt).strftime('%Y%m%d')
        meta = {'name': self.strategy_name, 'base_freq': base_freq, 'key_prefix': self.key_prefix,
                'description': description, 'author': author, 'outsample_sdt': outsample_sdt,
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'kwargs': json.dumps(kwargs)}
        self.r.hset(f'{self.strategy_name}:meta', mapping=meta)

    @property
    def metadata(self):
        """获取策略元数据"""
        return self.r.hgetall(f'{self.strategy_name}:meta')

    def publish(self, symbol, dt, weight, price=0, ref=None, overwrite=False):
        """发布单个策略持仓权重

        :param symbol: str, eg; SFIF9001
        :param dt: py_datetime or pandas Timestamp
        :param weight: float, 信号值
        :param price: float, 产生信号时的价格
        :param ref: dict, 自定义数据
        :param overwrite: boolean, 是否覆盖已有记录
        :return: 成功发布信号的条数
        """
        if not isinstance(dt, datetime):
            dt = pd.to_datetime(dt)

        udt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        key = f'{self.key_prefix}:{self.strategy_name}:{symbol}:{dt.strftime("%Y%m%d%H%M%S")}'
        ref = ref if ref else '{}'
        ref_str = json.dumps(ref) if isinstance(ref, dict) else ref
        return self.lua_publish(keys=[key], args=[1 if overwrite else 0, udt, weight, price, ref_str])

    def publish_dataframe(self, df, overwrite=False, batch_size=10000):
        """批量发布多个策略信号

        :param df: pandas.DataFrame, 必需包含['symbol', 'dt', 'weight']列,
                可选['price', 'ref']列, 如没有price则写0, dtype同publish方法
        :param overwrite: boolean, 是否覆盖已有记录
        :return: 成功发布信号的条数
        """
        df = df.copy()
        df['dt'] = pd.to_datetime(df['dt'])
        df = df.sort_values('dt')

        if 'price' not in df.columns:
            df['price'] = 0
        if 'ref' not in df.columns:
            df['ref'] = '{}'

        keys, args = [], []
        for row in df[['symbol', 'dt', 'weight', 'price', 'ref']].to_numpy():
            key = f'{self.key_prefix}:{self.strategy_name}:{row[0]}:{row[1].strftime("%Y%m%d%H%M%S")}'
            keys.append(key)

            args.append(row[2])
            args.append(row[3])
            ref = row[4]
            args.append(json.dumps(ref) if isinstance(ref, dict) else ref)

        udt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        overwrite = 1 if overwrite else 0

        pub_cnt = 0
        len_keys = len(keys)
        for i in range(0, len_keys, batch_size):
            if i + batch_size < len_keys:
                tmp_keys = keys[i: i + batch_size]
                tmp_args = [overwrite, udt] + args[3 * i: 3 * (i + batch_size)]
            else:
                tmp_keys = keys[i: len_keys]
                tmp_args = [overwrite, udt] + args[3 * i: 3 * len_keys]
            logger.info(f"索引 {i}，即将发布 {len(tmp_keys)} 条权重信号")
            pub_cnt += self.lua_publish(keys=tmp_keys, args=tmp_args)
            logger.info(f"已完成 {pub_cnt} 次发布")
        return pub_cnt

    def __heartbeat(self):
        while True:
            key = f'{self.heartbeat_prefix}:{self.strategy_name}'
            try:
                self.heartbeat_client.set(key, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            except Exception:
                continue
            time.sleep(15)

    def get_keys(self, pattern):
        """使用 lua 获取 redis 中指定 pattern 的 keys"""
        return self.r.eval('''local pattern = ARGV[1]\nreturn redis.call('KEYS', pattern)''', 0, pattern)

    def clear_all(self):
        """删除该策略所有记录"""
        self.r.delete(f"{self.strategy_name}:meta")
        keys = self.get_keys(f'{self.key_prefix}:{self.strategy_name}*')
        if keys is not None and len(keys) > 0:
            self.r.delete(*keys)

    @staticmethod
    def register_lua_publish(client):
        lua_body = '''
local overwrite = ARGV[1]
local update_time = ARGV[2]
local cnt = 0
local ret
for i = 1, #KEYS do
    local key = KEYS[i]
    local sig = ARGV[3 + 3 * (i - 1)]
    local price = ARGV[4 + 3 * (i - 1)]
    local ref_str = ARGV[5 + 3 * (i - 1)]
    local split_str = {}
    key:gsub('[^:]+', function(s) table.insert(split_str, s) end)
    local model_key = split_str[1] .. ':' .. split_str[2] .. ':' .. split_str[3]

    local if_pass = true
    if overwrite ~= '0' then
        if_pass = false
    else
        local pos = redis.call('HGET', model_key .. ':LAST', 'weight')
        if not pos or math.abs(tonumber(sig) - tonumber(pos)) > 0.00001 then
            if_pass = false
        end
    end

    if not if_pass then
        local strategy_name, symbol, action_time = split_str[2], split_str[3], split_str[4]
        local at_str = string.sub(action_time, 1, 4) .. '-' .. string.sub(action_time, 5, 6) .. '-' ..
            string.sub(action_time, 7, 8) .. ' ' .. string.sub(action_time, 9, 10) .. ':' ..
            string.sub(action_time, 11, 12) .. ':' .. string.sub(action_time, 13, 14)
        redis.call('ZADD', model_key, tonumber(action_time), key)
        local ret1 = redis.call('HMSET', key, 'symbol', symbol, 'weight', sig, 'dt', at_str, 'update_time', update_time, 'price', price, 'ref', ref_str)
        local ret2 = redis.call('HMSET', key:gsub(action_time, 'LAST'), 'symbol', symbol, 'weight', sig, 'dt', at_str, 'update_time', update_time, 'price', price, 'ref', ref_str)
        if ret1.ok and ret2.ok then
            cnt = cnt + 1
            local pubKey = 'PUBSUB:' .. split_str[1] .. ':' .. strategy_name .. ':' .. symbol
            redis.call('PUBLISH', pubKey, key .. ':' .. sig .. ':' .. price .. ':' .. ref_str)
        end
    end
end
return cnt
'''
        return client.register_script(lua_body)

    def get_symbols(self):
        """获取策略交易的品种列表"""
        keys = self.get_keys(f'{self.key_prefix}:{self.strategy_name}*')
        symbols = {x.split(":")[2] for x in keys}
        return list(symbols)

    def get_last_weights(self, symbols=None):
        """获取最近的持仓权重"""
        symbols = symbols if symbols else self.get_symbols()
        with self.r.pipeline() as pipe:
            for symbol in symbols:
                pipe.hgetall(f'{self.key_prefix}:{self.strategy_name}:{symbol}:LAST')
            rows = pipe.execute()

        dfw = pd.DataFrame(rows)
        dfw['weight'] = dfw['weight'].astype(float)
        dfw['dt'] = pd.to_datetime(dfw['dt'])
        return dfw

    def get_hist_weights(self, symbol, sdt, edt) -> pd.DataFrame:
        """获取单个品种的持仓权重历史数据"""
        start_score = pd.to_datetime(sdt).strftime('%Y%m%d%H%M%S')
        end_score = pd.to_datetime(edt).strftime('%Y%m%d%H%M%S')
        model_key = f'{self.key_prefix}:{self.strategy_name}:{symbol}'
        key_list = self.r.zrangebyscore(model_key, start_score, end_score)

        if len(key_list) == 0:
            logger.warning(f'no history weights: {symbol} - {sdt} - {edt}')
            return pd.DataFrame()

        with self.r.pipeline() as pipe:
            for key in key_list:
                pipe.hmget(key, 'weight', 'price', 'ref')
            rows = pipe.execute()

        weights = []
        for i in range(len(key_list)):
            dt = pd.to_datetime(key_list[i].split(":")[-1]) # type: ignore
            weight, price, ref = rows[i]
            weight = weight if weight is None else float(weight)
            price = price if price is None else float(price)
            try:
                ref = json.loads(ref)
            except Exception:
                ref = ref
            weights.append((self.strategy_name, symbol, dt, weight, price, ref))
        dfw = pd.DataFrame(weights, columns=['strategy_name', 'symbol', 'dt', 'weight', 'price', 'ref'])
        return dfw