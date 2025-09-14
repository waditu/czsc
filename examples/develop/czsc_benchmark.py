
import time
import pandas as pd
from loguru import logger
from rs_czsc import RawBar, Freq, CZSC, format_standard_kline


logger.disable("czsc.utils.cache")


# def format_standard_kline(df: pd.DataFrame, freq: Freq = Freq.F5):
#     """格式化标准K线数据为 CZSC 标准数据结构 RawBar 列表

#     :param df: 标准K线数据，DataFrame结构

#         ===================  =========  ======  =======  ======  =====  ===========  ===========
#         dt                   symbol       open    close    high    low          vol       amount
#         ===================  =========  ======  =======  ======  =====  ===========  ===========
#         2023-11-17 00:00:00  689009.SH   33.52    33.41   33.69  33.38  1.97575e+06  6.61661e+07
#         2023-11-20 00:00:00  689009.SH   33.4     32.91   33.45  32.25  5.15016e+06  1.68867e+08
#         ===================  =========  ======  =======  ======  =====  ===========  ===========

#     :param freq: K线级别
#     :return: list of RawBar
#     """
#     bars = []
#     for i, row in df.iterrows():
#         bar = RawBar(
#             id=i,
#             symbol=row["symbol"],
#             dt=row["dt"],
#             open=row["open"],
#             close=row["close"],
#             high=row["high"],
#             low=row["low"],
#             vol=row["vol"],
#             amount=row["amount"],
#             freq=freq,
#         )
#         bars.append(bar)
#     return bars


def create_benchmark(count=1000):
    """创建测试用的K线数据"""
    from czsc import mock
    
    df = mock.generate_klines()
    # df = pd.read_feather(r"A:\桌面临时数据\行情数据\BTCUSDT5分钟行情.feather")
    df = df.reset_index(drop=True)
    logger.info(f"开始创建 {count} 根K线的测试数据; 原始数据总共有 {len(df)} 根K线")
    start_time = time.time_ns()
    bars = format_standard_kline(df.tail(count))
    logger.info(f"format_standard_kline {count}；耗时 {(time.time_ns() - start_time) / 1_000_000:.2f} 毫秒")
    
    start_time = time.time_ns()
    c = CZSC(bars, max_bi_num=100)
    logger.warning(f"{count} bars -- CZSC初始化耗时 {(time.time_ns() - start_time) / 1_000_000:.2f} 毫秒")
    return c


if __name__ == '__main__':
    for count in [1000, 2000, 3000, 5000, 10000, 20000, 50000, 100000, 200000]:
        create_benchmark(count)
    