import sys
sys.path.insert(0, r"D:\ZB\git_repo\waditu\czsc")
sys.path.insert(0, "..")
import os
import czsc
import redis
import pandas as pd
from dotenv import load_dotenv, find_dotenv

load_dotenv(r"D:\ZB\git_repo\waditu\czsc\examples\test_offline\.env", override=True)
# load_dotenv(find_dotenv(), override=True)

redis_url = os.getenv("RWC_REDIS_URL")
connection_pool = redis.BlockingConnectionPool.from_url(redis_url, max_connections=10, timeout=30, decode_responses=True)


def test_redis_client():
    rwc = czsc.RedisWeightsClient('test', redis_url, key_prefix='WeightsA')

    # 如果需要清理 redis 中的数据，执行
    # rwc.clear_all()

    # 首次写入，建议设置一些策略元数据
    rwc.set_metadata(description='测试策略：仅用于读写redis测试', base_freq='1分钟', author='ZB', outsample_sdt='20220101')
    print(rwc.metadata)

    rwc.set_metadata(description='测试策略：仅用于读写redis测试', base_freq='1分钟', author='ZB',
                     outsample_sdt='20220101', overwrite=True)
    print(rwc.metadata)

    # 写入策略持仓权重，样例数据下载：https://s0cqcxuy3p.feishu.cn/wiki/Pf1fw1woQi4iJikbKJmcYToznxb
    weights = pd.read_feather(r"C:\Users\zengb\Downloads\weight_example.feather")

    # 写入单条数据
    rwc.publish(**weights.iloc[0].to_dict())

    # 批量写入整个dataframe；样例超300万行，写入耗时约5分钟
    rwc.publish_dataframe(weights, overwrite=False, batch_size=1000000)

    # 获取redis中该策略有持仓权重的品种列表
    symbols = rwc.get_symbols()
    print(symbols)

    # 获取指定品种在某个时间段的持仓权重数据
    dfw = rwc.get_hist_weights('ZZSF9001', '20210101', '20230101')

    # 获取所有品种最近一个时间的持仓权重
    dfr = rwc.get_last_weights(symbols=symbols)


def test_metas():
    from czsc.traders.rwc import get_strategy_mates
    mates = get_strategy_mates(connection_pool=connection_pool, key_prefix="WeightsA")
    print(mates)


def test_heartbeat():
    from czsc.traders.rwc import get_heartbeat_time

    # 获取指定策略的心跳时间
    hb = get_heartbeat_time(strategy_name="MKT001", connection_pool=connection_pool, key_prefix="WeightsA")
    print(hb)

    # 获取所有策略的心跳时间
    hb = get_heartbeat_time(connection_pool=connection_pool, key_prefix="WeightsA")
    print(hb)
