# chan - 缠论技术分析工具
>缠论来源于[缠中说缠博客](http://blog.sina.com.cn/chzhshch)，欢迎加微信探讨，我的微信号是 `zengbin93`

* [在线体验](http://103.235.232.152:8005/?ts_code=000001.SH&asset=I&trade_date=20200228&freqs=5min,30min)
* 参数说明：1）ts_code 是 tushare 的代码；2）asset 现在有两个值，E 表示股票，I 表示指数

## 安装

Pypi上已经存在一个名为chan的库，以致于这个库没法上传到Pypi。

执行以下代码直接从github安装：
```
pip install git+git://github.com/zengbin93/chan.git -U
```

## K线数据样例

`dt` 的格式统一为 `%Y-%m-%d %H:%M:%S`，如 `2020-02-27 00:00:00`

```markdown
         symbol                   dt   open  close   high    low     vol
0     300803.SZ  2020-01-17 09:31:00  44.08  44.19  44.30  44.01  170160
1     300803.SZ  2020-01-17 09:32:00  44.06  44.24  44.24  43.93   91100
2     300803.SZ  2020-01-17 09:33:00  44.10  43.91  44.17  43.91   90251
3     300803.SZ  2020-01-17 09:34:00  43.90  43.86  43.90  43.81   61100
4     300803.SZ  2020-01-17 09:35:00  43.86  43.66  43.86  43.61   75900
5     300803.SZ  2020-01-17 09:36:00  43.66  43.80  43.86  43.66   56600
6     300803.SZ  2020-01-17 09:37:00  43.81  43.67  43.82  43.67   68600
7     300803.SZ  2020-01-17 09:38:00  43.67  43.60  43.67  43.53   97554
8     300803.SZ  2020-01-17 09:39:00  43.60  43.62  43.70  43.57  118861
```

* dt 表示 该周期的交易结束时间


## 使用方法

目前已经实现了缠论的 笔、线段、中枢 的自动识别，核心代码在 `chan.analyze` 中；
此外，基于这个库，开发了一个web页面，关联 tushare.pro 的数据，输入相应的交易代码等就可以直接查看对应的分析结果。

> 前端页面（使用Tushare的数据）: https://github.com/waditu/tushare_chan

> 前端页面（使用掘金的数据）: https://github.com/zengbin93/gm_chan

> 前端页面（使用聚宽的数据）: https://github.com/zengbin93/jq_chan

## 结合 tushare.pro 的数据使用

py 文件地址： examples/combine_with_tushare.py

没有 token，到 https://tushare.pro/register?reg=7 注册下

```python
import tushare as ts
from datetime import datetime, timedelta
from chan import KlineAnalyze, SolidAnalyze

# 首次使用，需要在这里设置你的 tushare token，用于获取数据；在同一台机器上，tushare token 只需要设置一次
# 没有 token，到 https://tushare.pro/register?reg=7 注册获取
# ts.set_token("your tushare token")


def _get_start_date(end_date, freq):
    end_date = datetime.strptime(end_date, '%Y%m%d')
    if freq == '1min':
        start_date = end_date - timedelta(days=30)
    elif freq == '5min':
        start_date = end_date - timedelta(days=70)
    elif freq == '30min':
        start_date = end_date - timedelta(days=500)
    elif freq == 'D':
        start_date = end_date - timedelta(weeks=500)
    elif freq == 'W':
        start_date = end_date - timedelta(weeks=1000)
    else:
        raise ValueError("'freq' value error, current value is %s, "
                         "optional valid values are ['1min', '5min', '30min', "
                         "'D', 'W']" % freq)
    return start_date


def get_kline(ts_code, end_date, freq='30min', asset='E'):
    """获取指定级别的前复权K线

    :param ts_code: str
        股票代码，如 600122.SH
    :param freq: str
        K线级别，可选值 [1min, 5min, 15min, 30min, 60min, D, M, Y]
    :param end_date: str
        日期，如 20190610
    :param asset: str
        交易资产类型，可选值 E股票 I沪深指数 C数字货币 FT期货 FD基金 O期权 CB可转债（v1.2.39），默认E
    :return: pd.DataFrame
        columns = ["symbol", "dt", "open", "close", "high", "low", "vol"]
    """
    start_date = _get_start_date(end_date, freq)
    start_date = start_date.date().__str__().replace("-", "")
    end_date = datetime.strptime(end_date, '%Y%m%d')
    end_date = end_date + timedelta(days=1)
    end_date = end_date.date().__str__().replace("-", "")

    df = ts.pro_bar(ts_code=ts_code, freq=freq, start_date=start_date, end_date=end_date,
                    adj='qfq', asset=asset)

    # 统一 k 线数据格式为 6 列，分别是 ["symbol", "dt", "open", "close", "high", "low", "vr"]
    if "min" in freq:
        df.rename(columns={'ts_code': "symbol", "trade_time": "dt"}, inplace=True)
    else:
        df.rename(columns={'ts_code': "symbol", "trade_date": "dt"}, inplace=True)

    df.drop_duplicates(subset='dt', keep='first', inplace=True)
    df.sort_values('dt', inplace=True)
    df['dt'] = df.dt.apply(str)
    if freq.endswith("min"):
        # 清理 9:30 的空数据
        df['not_start'] = df.dt.apply(lambda x: not x.endswith("09:30:00"))
        df = df[df['not_start']]
    df.reset_index(drop=True, inplace=True)

    k = df[['symbol', 'dt', 'open', 'close', 'high', 'low', 'vol']]

    for col in ['open', 'close', 'high', 'low']:
        k[col] = k[col].apply(round, args=(2,))
    return k


def get_klines(ts_code, end_date, freqs='1min,5min,30min,D', asset='E'):
    """获取不同级别K线"""
    freq_map = {"1min": "1分钟", "5min": "5分钟", "30min": "30分钟", "D": "日线"}
    klines = dict()
    freqs = freqs.split(",")
    for freq in freqs:
        df = get_kline(ts_code, end_date, freq=freq, asset=asset)
        klines[freq_map[freq]] = df
    return klines


def use_kline_analyze():
    print('=' * 100, '\n')
    print("KlineAnalyze 的使用方法：\n")
    kline = get_kline(ts_code="000009.SZ", end_date="20200210", freq='30min', asset="I")
    ka = KlineAnalyze(kline)
    print("线段：", ka.xd, "\n")
    print("中枢：", ka.zs, "\n")


def use_solid_analyze():
    print('=' * 100, '\n')
    print("SolidAnalyze 的使用方法：\n")
    klines = get_klines(ts_code="300455.SZ", end_date="20200202", freqs='1min,5min,30min,D', asset='E')
    sa = SolidAnalyze(klines)

    # 查看指定级别的三买
    tb, _ = sa.is_third_buy('30分钟')
    print("指定级别三买：", tb, "\n")


if __name__ == '__main__':
    use_kline_analyze()
    use_solid_analyze()
```

## 结合掘金的数据使用

py 文件地址： examples/combine_with_goldminer.py

```python

from gm.api import *
from datetime import datetime
from chan import KlineAnalyze, SolidAnalyze

# 在这里设置你的掘金token，用于获取数据
set_token("your gm token")


def get_kline(symbol, end_date=None, freq='1d', k_count=5000):
    """从掘金获取历史K线数据

    参考： https://www.myquant.cn/docs/python/python_select_api#6fb030ec42984aff

    :param symbol:
    :param end_date: str
        交易日期，如 2019-12-31
    :param freq: str
        K线级别，如 1d
    :param k_count: int
    :return: pd.DataFrame
    """
    if not end_date:
        end_date = datetime.now()
    df = history_n(symbol=symbol, frequency=freq, end_time=end_date,
                   fields='symbol,eob,open,close,high,low,volume',
                   count=k_count, df=True)
    if freq == '1d':
        df = df.iloc[:-1]
    df['dt'] = df['eob']
    df['vol'] = df['volume']
    df = df[['symbol', 'dt', 'open', 'close', 'high', 'low', 'vol']]
    df.sort_values('dt', inplace=True, ascending=True)
    df['dt'] = df.dt.apply(lambda x: x.strftime(r"%Y-%m-%d %H:%M:%S"))
    df.reset_index(drop=True, inplace=True)

    for col in ['open', 'close', 'high', 'low']:
        df[col] = df[col].apply(round, args=(2,))
    return df


def get_klines(symbol, end_date=None, freqs='60s,300s,1800s,1d', k_count=5000):
    """获取不同级别K线"""
    freq_map = {"60s": "1分钟", "300s": "5分钟", "1800s": "30分钟", "1d": "日线"}
    klines = dict()
    freqs = freqs.split(",")
    for freq in freqs:
        df = get_kline(symbol, end_date, freq, k_count)
        klines[freq_map[freq]] = df
    return klines


def use_kline_analyze():
    print('=' * 100, '\n')
    print("KlineAnalyze 的使用方法：\n")
    kline = get_kline(symbol='SHSE.000300', end_date="2020-02-02")
    ka = KlineAnalyze(kline)
    print("线段：", ka.xd, "\n")
    print("中枢：", ka.zs, "\n")


def use_solid_analyze():
    print('=' * 100, '\n')
    print("SolidAnalyze 的使用方法：\n")
    klines = get_klines(symbol='SZSE.300455', end_date="2020-02-02")
    sa = SolidAnalyze(klines)

    # 查看指定级别的三买
    tb, _ = sa.is_third_buy('30分钟')
    print("指定级别三买：", tb, "\n")


if __name__ == '__main__':
    use_kline_analyze()
    use_solid_analyze()
```

