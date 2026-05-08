"""K 线图（KlineChart）Plotly 绘图模块单元测试。

本测试套件验证 ``czsc.KlineChart`` 在结合缠论分析结果后能够正确生成
Plotly 交互式 K 线图，覆盖均线、成交量、MACD、分型与笔等常见叠加层。

业务背景：
    KlineChart 是 czsc 中用于交易研究和回放展示的核心可视化组件，基于
    Plotly 多子图架构（n_rows）实现。本测试用例使用 mock 数据驱动整条
    渲染流水线，并通过 HTML 文件落盘的方式验证最终产物可以被序列化输出。

模块作者：
    zengbin93 (zeng_bin8888@163.com)，创建于 2023/2/26 15:06
"""

import os

import pandas as pd

from czsc import CZSC, Freq, KlineChart, RawBar, mock


def test_kline_chart():
    """端到端验证 KlineChart 能够基于缠论 CZSC 对象绘制完整图表。

    测试场景：
        1. 通过 ``czsc.mock.generate_symbol_kines`` 生成 2023 年全年的日线
           mock 数据（seed=42 保证可重现）；
        2. 将 DataFrame 行逐条转换为 RawBar 对象列表；
        3. 构造 ``CZSC`` 分析对象并设置最大笔数量 max_bi_num=50；
        4. 创建 3 行子图布局的 KlineChart 实例并依次添加：
           - 主图：K 线 + 多组 SMA 均线（5/10/21 与 34/55/89/144）；
           - 第二行：成交量；
           - 第三行：MACD；
           - 主图叠加：分型散点 + 笔的连线（含端点文本标注）。
        5. 将图表导出为本地 HTML 文件并清理。

    关键断言：
        - 调用 ``write_html`` 后目标文件必须真实存在；
        - 删除文件后 ``os.path.exists`` 必须返回 False，确保资源清理彻底。
    """
    # 使用 mock 数据替代硬编码数据文件，固定 seed 保证测试可重现
    df = mock.generate_symbol_kines("000001", "日线", sdt="20230101", edt="20240101", seed=42)
    bars = []
    for i, row in df.iterrows():
        bar = RawBar(
            symbol=row["symbol"],
            id=i,
            freq=Freq.D,
            open=row["open"],
            dt=row["dt"],
            close=row["close"],
            high=row["high"],
            low=row["low"],
            vol=row["vol"],
            amount=row["amount"],
        )
        bars.append(bar)

    c = CZSC(bars, max_bi_num=50)

    # 从 bars_raw 手动构建 DataFrame，作为 KlineChart 各类 add_* 方法的输入
    df = pd.DataFrame(
        [
            {
                "dt": bar.dt,
                "open": bar.open,
                "close": bar.close,
                "high": bar.high,
                "low": bar.low,
                "vol": bar.vol,
                "amount": bar.amount,
            }
            for bar in c.bars_raw
        ]
    )
    df["text"] = "测试"
    kline = KlineChart(n_rows=3)
    kline.add_kline(df, name="K线")
    kline.add_sma(df, ma_seq=(5, 10, 21), row=1, visible=True, line_width=1.2)
    kline.add_sma(df, ma_seq=(34, 55, 89, 144), row=1, visible=False, line_width=1.2)
    kline.add_vol(df, row=2)
    kline.add_macd(df, row=3)
    if len(c.bi_list) > 0:
        bi1 = [{"dt": x.fx_a.dt, "bi": x.fx_a.fx, "text": x.fx_a.mark.value} for x in c.bi_list]
        bi2 = [{"dt": c.bi_list[-1].fx_b.dt, "bi": c.bi_list[-1].fx_b.fx, "text": c.bi_list[-1].fx_b.mark.value}]
        bi = pd.DataFrame(bi1 + bi2)
        fx = pd.DataFrame([{"dt": x.dt, "fx": x.fx} for x in c.fx_list])
        kline.add_scatter_indicator(fx["dt"], fx["fx"], name="分型", row=1, line_width=2)
        kline.add_scatter_indicator(bi["dt"], bi["bi"], name="笔", text=bi["text"], row=1, line_width=2)
    # kline.open_in_browser()
    file_html = "kline_chart_test.html"
    kline.fig.write_html(file_html)
    assert os.path.exists(file_html)
    os.remove(file_html)
    assert not os.path.exists(file_html)
