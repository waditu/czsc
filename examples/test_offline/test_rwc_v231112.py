import dotenv
dotenv.load_dotenv(r"D:\ZB\git_repo\waditu\czsc\examples\test_offline\.env", override=True)

import os
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "..")

import czsc
import pandas as pd

assert czsc.RedisWeightsClient.version == "V231112"

print(os.getenv("RWC_REDIS_URL"))


def test_writer():
    rwc = czsc.RedisWeightsClient('STK004_100', key_prefix='WeightsA', send_heartbeat=True)
    # 首次写入，建议设置一些策略元数据
    rwc.set_metadata(description='测试策略：仅用于读写redis测试', base_freq='日线', author='测试', outsample_sdt='20220101')
    print(rwc.metadata)

    dfw = pd.read_csv(r"C:\Users\zengb\Desktop\weights_example.csv")
    # 写入单条数据
    rwc.publish(**dfw.iloc[0].to_dict())

    # 批量写入整个dataframe；样例超100万行，写入耗时约3分钟
    rwc.publish_dataframe(dfw, overwrite=False, batch_size=10000)

    # 获取redis中该策略有持仓权重的品种列表
    symbols = rwc.get_symbols()
    print(symbols)


def test_reader():
    # 读取redis中的数据：send_heartbeat 推荐设置为 False，否则导致心跳数据异常
    rwc = czsc.RedisWeightsClient('STK002_100', key_prefix='WeightsA', send_heartbeat=False)
    symbols = rwc.get_symbols()

    # 读取单个品种的持仓历史
    df = rwc.get_hist_weights('000001.SZ', '20170101', '20230101')

    # 读取所有品种最近一个时间的持仓权重，忽略权重为0的品种
    df1 = rwc.get_last_weights(ignore_zero=True)

    # 读取策略全部持仓权重历史
    dfa1 = rwc.get_all_weights()
    dfa2 = rwc.get_all_weights(ignore_zero=False)
