# -*- coding: utf-8 -*-
"""
测试 MACD 指标子图绘制

根据 lightweight-charts-python 的文档和示例，正确实现 MACD 子图功能

author: czsc
create_dt: 2025-01-27
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from lightweight_charts import Chart
from loguru import logger


def calculate_macd(df, fast_period=12, slow_period=26, signal_period=9):
    """计算 MACD 指标
    
    :param df: 包含 close 价格的数据框
    :param fast_period: 快线EMA周期
    :param slow_period: 慢线EMA周期 
    :param signal_period: 信号线EMA周期
    :return: 包含 MACD、Signal、Histogram 的字典
    """
    # 计算快线和慢线EMA
    ema_fast = df['close'].ewm(span=fast_period).mean()
    ema_slow = df['close'].ewm(span=slow_period).mean()
    
    # MACD线 = 快线EMA - 慢线EMA
    macd_line = ema_fast - ema_slow
    
    # 信号线 = MACD线的EMA
    signal_line = macd_line.ewm(span=signal_period).mean()
    
    # 柱状图 = MACD线 - 信号线
    histogram = macd_line - signal_line
    
    return {
        'macd': macd_line,
        'signal': signal_line, 
        'histogram': histogram
    }


def generate_test_data(start_date='2023-01-01', end_date='2024-01-01', symbol='TEST'):
    """生成测试数据"""
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    
    # 生成交易日
    date_range = pd.date_range(start=start_dt, end=end_dt, freq='D')
    
    # 生成价格数据（带趋势）
    np.random.seed(42)
    prices = []
    base_price = 100.0
    
    for i, dt in enumerate(date_range):
        # 添加趋势和噪音
        trend = np.sin(i / 50) * 0.02  # 长期趋势
        noise = np.random.normal(0, 0.02)  # 随机噪音
        
        price_change = trend + noise
        new_price = base_price * (1 + price_change)
        
        # 生成OHLC数据
        open_price = base_price
        close_price = new_price
        high_price = max(open_price, close_price) * (1 + np.random.uniform(0, 0.01))
        low_price = min(open_price, close_price) * (1 - np.random.uniform(0, 0.01))
        volume = np.random.uniform(1000000, 5000000)
        
        prices.append({
            'time': dt,
            'open': round(open_price, 2),
            'high': round(high_price, 2),
            'low': round(low_price, 2), 
            'close': round(close_price, 2),
            'volume': int(volume)
        })
        
        base_price = new_price
    
    return pd.DataFrame(prices)


def test_macd_subchart():
    """测试 MACD 子图功能"""
    logger.info("开始测试 MACD 子图功能")
    
    try:
        # 生成测试数据
        logger.info("生成测试数据...")
        df = generate_test_data()
        logger.info(f"生成了 {len(df)} 条K线数据")
        
        # 计算MACD指标
        logger.info("计算 MACD 指标...")
        macd_data = calculate_macd(df)
        
        # 创建主图表
        logger.info("创建主图表...")
        main_chart = Chart(inner_width=1, inner_height=0.7)  # 主图占70%高度
        main_chart.time_scale(visible=False)  # 隐藏主图的时间轴
        
        # 创建MACD子图 
        logger.info("创建 MACD 子图...")
        macd_chart = main_chart.create_subchart(width=1, height=0.3, sync=True)  # 子图占30%高度
        
        # 设置主图数据（K线图）
        logger.info("设置主图 K线数据...")
        main_chart.set(df)
        
        # 准备MACD线数据 - 直接使用原始的Series数据
        macd_line_data = pd.DataFrame({
            'time': df['time'],
            'MACD': macd_data['macd']
        }).dropna()
        
        # 准备信号线数据
        signal_line_data = pd.DataFrame({
            'time': df['time'],
            'Signal': macd_data['signal']
        }).dropna()
        
        # 准备柱状图数据 - 简化格式
        histogram_data = []
        for i, (time, value) in enumerate(zip(df['time'], macd_data['histogram'])):
            if not pd.isna(value):
                color = '#26a69a' if value >= 0 else '#ef5350'
                histogram_data.append({
                    'time': time,
                    'value': value,
                    'color': color
                })
        
        histogram_df = pd.DataFrame(histogram_data)
        
        logger.info(f"MACD 线数据点数: {len(macd_line_data)}")
        logger.info(f"信号线数据点数: {len(signal_line_data)}")
        logger.info(f"柱状图数据点数: {len(histogram_df)}")
        
        # 在MACD子图中添加MACD线
        logger.info("添加 MACD 线...")
        macd_line = macd_chart.create_line(color='#1976D2', width=2)
        macd_line.set(macd_line_data)
        
        # 在MACD子图中添加信号线
        logger.info("添加信号线...")
        signal_line = macd_chart.create_line(color='#FF5722', width=2)
        signal_line.set(signal_line_data)
        
        # 在MACD子图中添加柱状图
        logger.info("添加 MACD 柱状图...")
        histogram = macd_chart.create_histogram()
        histogram.set(histogram_df)
        
        # 设置图表样式
        logger.info("设置图表样式...")
        main_chart.legend(visible=True)
        macd_chart.legend(visible=True)
        
        # 设置主图标题
        main_chart.watermark('K线图 + MACD指标', color='rgba(0, 0, 0, 0.5)')
        
        logger.info("显示图表...")
        # 显示图表
        main_chart.show(block=True)
        
        logger.info("MACD 子图测试成功完成！")
        return True
        
    except Exception as e:
        logger.error(f"MACD 子图测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == '__main__':
    logger.info("=" * 50)
    logger.info("开始 MACD 子图测试")
    logger.info("=" * 50)
    
    result = test_macd_subchart()
    
    logger.info("=" * 50) 
    logger.info(f"测试结果: {'成功' if result else '失败'}")
    logger.info("=" * 50) 