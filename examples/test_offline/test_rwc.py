import sys
sys.path.insert(0, ".")
sys.path.insert(0, "..")

import czsc
import pandas as pd

assert czsc.RedisWeightsClient.version == "V231005"

redis_url = 'redis://20.205.5.**:9103/1'
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
