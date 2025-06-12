# -*- coding: utf-8 -*-
"""
测试 trading_view_kline 函数

author: czsc
create_dt: 2025-01-27
"""

import sys
import os

# 添加当前项目路径到sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(current_dir)
sys.path.insert(0, project_dir)

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from czsc.utils.echarts_plot import trading_view_kline
from czsc.objects import Operate, RawBar
from czsc.analyze import CZSC
from czsc.enum import Freq
from loguru import logger


def generate_realistic_kline_data(start_date="2010-01-01", end_date="2025-06-08", symbol="测试股票"):
    """生成符合真实市场的K线数据（有涨有跌）

    :param start_date: 开始日期
    :param end_date: 结束日期
    :param symbol: 股票代码
    :return: RawBar对象列表
    """
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)

    # 生成交易日日期（跳过周末）
    date_range = pd.date_range(start=start_dt, end=end_dt, freq="B")  # B表示工作日

    raw_bars = []

    # 初始价格
    base_price = 100.0
    np.random.seed(42)  # 固定随机种子，确保结果可重现

    # 模拟不同的市场阶段
    total_days = len(date_range)
    phases = [
        {"name": "熊市", "trend": -0.0008, "volatility": 0.025, "length": 0.3},
        {"name": "震荡", "trend": 0.0002, "volatility": 0.015, "length": 0.2},
        {"name": "牛市", "trend": 0.0012, "volatility": 0.02, "length": 0.3},
        {"name": "调整", "trend": -0.0005, "volatility": 0.02, "length": 0.2},
    ]

    phase_idx = 0
    phase_days = 0
    current_phase = phases[phase_idx]

    for i, dt in enumerate(date_range):
        # 切换市场阶段
        if phase_days >= total_days * current_phase["length"]:
            phase_idx = (phase_idx + 1) % len(phases)
            current_phase = phases[phase_idx]
            phase_days = 0

        # 当前阶段的趋势和波动
        trend = current_phase["trend"]
        volatility = current_phase["volatility"]

        # 添加周期性波动
        cycle_factor = np.sin(i / 30) * 0.001  # 30天周期

        # 随机噪音
        noise = np.random.normal(0, volatility)

        open_price = base_price
        close_price = base_price * (1 + trend + cycle_factor + noise)

        # 确保价格不会变为负数
        if close_price <= 0:
            close_price = base_price * 0.95

        # 日内波动
        daily_range = abs(close_price - open_price) + base_price * np.random.uniform(0.01, 0.04)

        if close_price > open_price:  # 阳线
            high_price = close_price + daily_range * np.random.uniform(0.1, 0.5)
            low_price = open_price - daily_range * np.random.uniform(0.1, 0.3)
        else:  # 阴线
            high_price = open_price + daily_range * np.random.uniform(0.1, 0.3)
            low_price = close_price - daily_range * np.random.uniform(0.1, 0.5)

        # 确保价格关系正确
        high_price = max(high_price, open_price, close_price)
        low_price = min(low_price, open_price, close_price)

        # 模拟成交量 - 波动大的时候成交量大
        base_volume = np.random.uniform(100000, 300000)
        volatility_factor = abs(close_price - open_price) / open_price * 5
        volume = base_volume * (1 + volatility_factor)

        # 计算成交金额
        avg_price = (high_price + low_price + open_price + close_price) / 4
        amount = volume * avg_price

        # 创建RawBar对象
        bar = RawBar(
            symbol=symbol,
            id=i,
            freq=Freq.D,  # 日线
            dt=dt,
            open=round(open_price, 2),
            close=round(close_price, 2),
            high=round(high_price, 2),
            low=round(low_price, 2),
            vol=round(volume),
            amount=round(amount, 2),
        )
        raw_bars.append(bar)

        base_price = close_price
        phase_days += 1

    return raw_bars


def test_trading_view_kline():
    """测试 trading_view_kline 函数"""
    logger.info("开始测试 trading_view_kline 函数")

    try:
        # 生成模拟数据
        logger.info("生成真实市场K线数据...")
        raw_bars = generate_realistic_kline_data("2010-01-01", "2025-06-08")

        logger.info("使用CZSC分析K线数据...")
        # 使用CZSC类分析K线数据
        czsc = CZSC(raw_bars, max_bi_num=10000)

        logger.info(f"分析完成：共{len(czsc.bi_list)}笔，{len(czsc.fx_list)}个分型")

        # 转换数据格式用于绘图
        kline_data = [bar.__dict__ for bar in raw_bars]

        # 获取分型数据
        fx_data = [{"dt": fx.dt, "fx": fx.fx} for fx in czsc.fx_list] if czsc.fx_list else []

        # 获取笔数据
        if czsc.bi_list:
            bi_data = [{"dt": bi.fx_a.dt, "bi": bi.fx_a.fx} for bi in czsc.bi_list]
            # 添加最后一笔的终点
            bi_data.append({"dt": czsc.bi_list[-1].fx_b.dt, "bi": czsc.bi_list[-1].fx_b.fx})
        else:
            bi_data = []

        # 生成一些模拟买卖点用于测试
        bs_data = []
        if czsc.bi_list and len(czsc.bi_list) >= 4:
            # 在一些笔的端点添加买卖点标记
            for i, bi in enumerate(czsc.bi_list[::2]):  # 每隔一笔添加买卖点
                if i % 2 == 0:  # 买入
                    bs_data.append(
                        {"dt": bi.fx_a.dt, "price": bi.fx_a.fx, "op": Operate.LO, "op_desc": f"买入开仓-{i+1}"}
                    )
                else:  # 卖出
                    bs_data.append(
                        {"dt": bi.fx_a.dt, "price": bi.fx_a.fx, "op": Operate.LE, "op_desc": f"卖出平仓-{i+1}"}
                    )

        logger.info("数据转换完成，开始调用 trading_view_kline 函数...")

        # 调用函数
        chart = trading_view_kline(
            kline=kline_data, fx=fx_data, bi=bi_data, bs=bs_data, title="缠中说禅K线分析测试", t_seq=[5, 10, 20]
        )

        logger.info("trading_view_kline 函数调用成功！")

        # 显示图表（如果支持的话）
        if chart and hasattr(chart, "show"):
            logger.info("显示图表...")
            chart.show(block=True)
        else:
            logger.warning("图表对象无法显示，可能是 lightweight_charts 未正确安装")

        return True

    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return False


def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("开始 trading_view_kline 函数测试")
    logger.info("=" * 50)

    # 测试2：完整数据测试
    test2_result = test_trading_view_kline()

    # 总结测试结果
    logger.info("=" * 50)
    logger.info("测试结果总结:")
    logger.info(f"完整数据测试: {'通过' if test2_result else '失败'}")

    logger.info("=" * 50)


if __name__ == "__main__":
    main()
