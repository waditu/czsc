# https://s0cqcxuy3p.feishu.cn/wiki/OpxqwUjdaifQq9kigCUcIWeonsg
import czsc

# 首次使用需要设置 Tushare token，用于获取数据
# czsc.set_url_token(token="your tushare token", url="https://api.tushare.pro")

# 也可以在初始化 DataClient 时设置 token；不推荐直接在代码中写入 token
# dc = czsc.DataClient(url="https://api.tushare.pro", cache_path="~/czsc", token="your tushare token", timeout=300)

# 设置过 token 后，可以直接初始化 DataClient，不需要再次设置 token
# cache_path 用于设置缓存路径，后面的缓存文件会保存在该路径下
pro = czsc.DataClient(url="https://api.tushare.pro", cache_path=r"D:\.tushare_cache", timeout=300)

# 创建 pro 对象后，可以直接使用 Tushare 数据接口，与 Tushare 官方接口一致
# 首次调用会自动下载数据并缓存，后续调用，如果参数没有变化，会直接从缓存读取
df1 = pro.stock_basic(exchange="", list_status="L", fields="ts_code,symbol,name,area,industry,list_date")

# 再次执行同样参数的查询
df2 = pro.stock_basic(exchange="", list_status="L", fields="ts_code,symbol,name,area,industry,list_date")

# 如果需要刷新数据，可以设置 ttl 参数，单位秒；ttl=-1 表示不过期；ttl=0 表示每次都重新下载
df3 = pro.stock_basic(exchange="", list_status="L", fields="ts_code,symbol,name,area,industry,list_date", ttl=0)

# df = pro.daily(trade_date="20240614")
