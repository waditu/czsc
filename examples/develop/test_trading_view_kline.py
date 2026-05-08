# -*- coding: utf-8 -*-
"""
trading_view_kline 函数的可视化示例脚本

用途:
    展示如何把 czsc 的分析结果（分型 / 笔）渲染到 lightweight-charts 风格的
    交互式 K 线图上。脚本以 mock 模拟数据为输入，跑通"生成 -> 分析 -> 绘图"
    完整链路，可作为快速验证 trading_view_kline 集成是否正常的样例。

执行方式:
    python examples/develop/test_trading_view_kline.py

依赖:
    - czsc 主体（用于 CZSC 分析与 mock 数据）
    - czsc.utils.echarts_plot.trading_view_kline（实际的绘图函数）
    - lightweight_charts（可选；未安装时仅创建 chart 对象、不展示）

输出:
    通过 loguru 打印关键步骤日志与最终测试结果（"通过" / "失败"）。

作者: czsc
创建时间: 2025-01-27
"""
from loguru import logger
from czsc.utils.echarts_plot import trading_view_kline
from czsc import CZSC, Freq, RawBar, format_standard_kline
from czsc.mock import generate_symbol_kines


def test_trading_view_kline():
    """
    端到端验证 trading_view_kline 函数

    流程:
        1. 用 mock 生成 4 年的日线 K 线
        2. 调用 CZSC 完成分型与笔识别
        3. 把 RawBar / 分型 / 笔分别整理为 trading_view_kline 期望的字典列表
        4. 调用 trading_view_kline 创建图表对象
        5. 检查返回值是否具备 show 接口（依赖 lightweight_charts 是否安装）

    返回:
        bool: True 表示完整链路成功；False 表示中途抛异常
    """
    logger.info("开始测试 trading_view_kline 函数")

    try:
        # —— 步骤 1：生成 mock 日线 K 线，固定 seed 保证结果可复现 ——
        logger.info("生成模拟K线数据...")
        df = generate_symbol_kines('test', '日线', '20200101', '20240101', seed=42)
        raw_bars = format_standard_kline(df, freq=Freq.D)

        # —— 步骤 2：CZSC 缠论分析（max_bi_num 设大值以便绘图保留完整笔历史）——
        logger.info("使用CZSC分析K线数据...")
        czsc = CZSC(raw_bars, max_bi_num=10000)
        logger.info(f"分析完成：共{len(czsc.bi_list)}笔，{len(czsc.fx_list)}个分型")

        # —— 步骤 3：把对象列表转成绘图函数需要的 dict 列表 ——
        # K 线：直接 __dict__ 抽取所有字段，避免逐字段拷贝
        kline_data = [bar.__dict__ for bar in raw_bars]

        # 分型：仅保留时间戳与分型类型（顶分型 / 底分型）
        fx_data = [{"dt": fx.dt, "fx": fx.fx} for fx in czsc.fx_list] if czsc.fx_list else []

        # 笔：每一笔取起点分型，再额外补上最后一笔的终点，保证连续画线无断点
        if czsc.bi_list:
            bi_data = [{"dt": bi.fx_a.dt, "bi": bi.fx_a.fx} for bi in czsc.bi_list]
            bi_data.append({"dt": czsc.bi_list[-1].fx_b.dt, "bi": czsc.bi_list[-1].fx_b.fx})
        else:
            bi_data = []

        logger.info("数据转换完成，开始调用 trading_view_kline 函数...")

        # —— 步骤 4：调用绘图函数；t_seq 指定均线周期，bs 留空表示无买卖点标注 ——
        chart = trading_view_kline(
            kline=kline_data, fx=fx_data, bi=bi_data, bs=[], title="缠中说禅K线分析测试", t_seq=[5, 10, 20]
        )

        logger.info("trading_view_kline 函数调用成功！")

        # —— 步骤 5：检查返回对象；lightweight_charts 缺失时仅打印警告，不视为失败 ——
        if chart and hasattr(chart, "show"):
            logger.info("图表已创建成功，可调用 chart.show() 显示")
        else:
            logger.warning("图表对象无法显示，可能是 lightweight_charts 未正确安装")

        return True

    except Exception as e:
        # 捕获所有异常并完整打印 traceback，便于在 CI 或开发机上定位问题
        logger.error(f"测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """脚本入口：打印分隔线包裹的日志，便于在大量输出中肉眼定位本次测试结果"""
    logger.info("=" * 50)
    logger.info("开始 trading_view_kline 函数测试")
    logger.info("=" * 50)

    test_result = test_trading_view_kline()

    logger.info("=" * 50)
    logger.info(f"测试结果: {'通过' if test_result else '失败'}")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
