
import time
import pandas as pd
from loguru import logger
# from czsc.core import CZSC, format_standard_kline
from rs_czsc import CZSC, format_standard_kline

logger.disable("czsc.utils.cache")


def create_benchmark(count=1000):
    """创建测试用的K线数据，测试 CZSC 分析性能"""
    from czsc import mock

    df = mock.generate_klines()
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
    # 100000+ 根K线的测试需要较大内存，按需调整
    for count in [1000, 2000, 3000, 5000, 10000, 20000, 50000]:
        create_benchmark(count)