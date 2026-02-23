# -*- coding: utf-8 -*-
"""
测试 trading_view_kline 函数

本示例展示如何使用 czsc 的 trading_view_kline 函数进行 K 线可视化。
使用 mock 数据生成K线，通过 CZSC 分析后绘制带有分型和笔的K线图。

author: czsc
create_dt: 2025-01-27
"""
from loguru import logger
from czsc.utils.echarts_plot import trading_view_kline
from czsc.core import CZSC, Freq, RawBar, format_standard_kline
from czsc.mock import generate_symbol_kines


def test_trading_view_kline():
    """测试 trading_view_kline 函数"""
    logger.info("开始测试 trading_view_kline 函数")

    try:
        # 使用 mock 数据生成K线
        logger.info("生成模拟K线数据...")
        df = generate_symbol_kines('test', '日线', '20200101', '20240101', seed=42)
        raw_bars = format_standard_kline(df, freq=Freq.D)

        logger.info("使用CZSC分析K线数据...")
        czsc = CZSC(raw_bars, max_bi_num=10000)
        logger.info(f"分析完成：共{len(czsc.bi_list)}笔，{len(czsc.fx_list)}个分型")

        # 转换数据格式用于绘图
        kline_data = [bar.__dict__ for bar in raw_bars]

        # 获取分型数据
        fx_data = [{"dt": fx.dt, "fx": fx.fx} for fx in czsc.fx_list] if czsc.fx_list else []

        # 获取笔数据
        if czsc.bi_list:
            bi_data = [{"dt": bi.fx_a.dt, "bi": bi.fx_a.fx} for bi in czsc.bi_list]
            bi_data.append({"dt": czsc.bi_list[-1].fx_b.dt, "bi": czsc.bi_list[-1].fx_b.fx})
        else:
            bi_data = []

        logger.info("数据转换完成，开始调用 trading_view_kline 函数...")

        # 调用函数
        chart = trading_view_kline(
            kline=kline_data, fx=fx_data, bi=bi_data, bs=[], title="缠中说禅K线分析测试", t_seq=[5, 10, 20]
        )

        logger.info("trading_view_kline 函数调用成功！")

        if chart and hasattr(chart, "show"):
            logger.info("图表已创建成功，可调用 chart.show() 显示")
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

    test_result = test_trading_view_kline()

    logger.info("=" * 50)
    logger.info(f"测试结果: {'通过' if test_result else '失败'}")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
