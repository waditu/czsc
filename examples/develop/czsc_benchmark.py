"""
CZSC 分析性能基准测试脚本

用途:
    在不同 K 线规模下测量 ``format_standard_kline`` 与 ``CZSC`` 初始化的耗时，
    用于跟踪迁移到 Rust 后端后的性能基线，以及在重大改动前后对比性能波动。

执行方式:
    直接运行本文件即可：
        python examples/develop/czsc_benchmark.py
    输出经由 loguru 打印到控制台，包含每档样本量的两段耗时（毫秒级）。

注意事项:
    - 默认走 ``czsc.mock.generate_symbol_kines`` 生成确定性 30 分钟随机 K 线，
      不依赖外部数据源
    - 把 ``czsc.utils.cache`` 模块的日志禁用，避免缓存命中信息干扰耗时统计
    - 当 count 接近或超过 100k 根时，单次测试需要数百 MB 内存，按机器情况裁剪样本档位
"""

import time
import pandas as pd
from loguru import logger
from czsc import CZSC, Freq, format_standard_kline

# 关闭磁盘缓存模块的日志输出，避免命中/失效日志混淆基准结果
logger.disable("czsc.utils.cache")


def create_benchmark(count=1000):
    """
    创建指定根数的 30 分钟 K 线，并测量两段关键耗时

    参数:
        count: 取样末尾 K 线根数；越大越能贴近大数据量的真实场景

    返回:
        构造好的 CZSC 实例（保留多达 100 笔，便于后续二次分析）

    输出:
        通过 loguru 打印两条耗时日志：
            1. ``format_standard_kline`` 的转换耗时
            2. ``CZSC(...)`` 的初始化耗时（含分型/笔识别全流程）
    """
    # 仅在函数体内 import，避免 mock 模块在脚本加载阶段就被拉起
    from czsc.mock import generate_symbol_kines

    # 固定标的 / 周期 / 时间窗 / 默认种子，保证每次基准结果可复现
    df = generate_symbol_kines("000001", "30分钟", "20100101", "20250101")
    df = df.reset_index(drop=True)
    logger.info(f"开始创建 {count} 根K线的测试数据; 原始数据总共有 {len(df)} 根K线")

    # —— 第一段耗时：DataFrame -> List[RawBar] 的格式转换 ——
    start_time = time.time_ns()
    bars = format_standard_kline(df.tail(count), freq=Freq.F30)
    logger.info(f"format_standard_kline {count}；耗时 {(time.time_ns() - start_time) / 1_000_000:.2f} 毫秒")

    # —— 第二段耗时：CZSC 初始化（包含分型与笔的识别）——
    start_time = time.time_ns()
    c = CZSC(bars, max_bi_num=100)
    logger.warning(f"{count} bars -- CZSC初始化耗时 {(time.time_ns() - start_time) / 1_000_000:.2f} 毫秒")
    return c


if __name__ == '__main__':
    # 多档样本量逐次跑，便于观察耗时随规模的变化趋势
    # 10 万根以上的测试需要较大内存，按机器实际情况增删档位
    for count in [1000, 2000, 3000, 5000, 10000, 20000, 50000]:
        create_benchmark(count)
