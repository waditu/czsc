from rs_czsc import CZSC

"""
测试CZSC Python绑定功能
"""
import pandas as pd
from datetime import datetime, timedelta
from rs_czsc import RawBar, Freq, CZSC, Direction, Mark


def format_standard_kline(df: pd.DataFrame, freq: Freq = Freq.F5):
    """格式化标准K线数据为 CZSC 标准数据结构 RawBar 列表

    :param df: 标准K线数据，DataFrame结构

        ===================  =========  ======  =======  ======  =====  ===========  ===========
        dt                   symbol       open    close    high    low          vol       amount
        ===================  =========  ======  =======  ======  =====  ===========  ===========
        2023-11-17 00:00:00  689009.SH   33.52    33.41   33.69  33.38  1.97575e+06  6.61661e+07
        2023-11-20 00:00:00  689009.SH   33.4     32.91   33.45  32.25  5.15016e+06  1.68867e+08
        ===================  =========  ======  =======  ======  =====  ===========  ===========

    :param freq: K线级别
    :return: list of RawBar
    """
    bars = []
    for i, row in df.iterrows():
        bar = RawBar(
            id=i,
            symbol=row["symbol"],
            dt=row["dt"],
            open=row["open"],
            close=row["close"],
            high=row["high"],
            low=row["low"],
            vol=row["vol"],
            amount=row["amount"],
            freq=freq,
        )
        bars.append(bar)
    return bars


def create_test_bars(count=1000):
    """创建测试用的K线数据"""
    from czsc import mock

    df = mock.generate_klines()
    bars = format_standard_kline(df.tail(count))
    return bars


def test_czsc_creation():
    """测试CZSC对象创建"""
    bars = create_test_bars(200000)
    czsc = CZSC(bars, max_bi_num=len(bars))

    assert czsc.symbol == "TEST.SZ"
    assert czsc.freq == Freq.D
    assert czsc.max_bi_num == 50
    print(f"创建CZSC成功: {czsc}")


def test_czsc_bi_list():
    """测试笔列表功能"""
    bars = create_test_bars(50)
    czsc = CZSC(bars, max_bi_num=50)

    bi_list = czsc.bi_list
    print(f"笔的数量: {len(bi_list)}")

    for i, bi in enumerate(bi_list):
        print(f"笔 {i+1}: {bi}")
        assert bi.symbol == "TEST.SZ"
        assert bi.direction in [Direction.Up, Direction.Down]
        assert bi.high > bi.low
        assert bi.sdt <= bi.edt


def test_czsc_fx_list():
    """测试分型列表功能"""
    bars = create_test_bars(50)
    czsc = CZSC(bars, max_bi_num=50)

    fx_list = czsc.get_fx_list()
    print(f"分型数量: {len(fx_list)}")

    for i, fx in enumerate(fx_list):
        print(f"分型 {i+1}: {fx}")
        assert fx.symbol == "TEST.SZ"
        assert fx.mark in [Mark.G, Mark.D]
        assert fx.high >= fx.low


def test_czsc_update():
    """测试CZSC更新功能"""
    bars = create_test_bars(30)
    czsc = CZSC(bars, max_bi_num=50)

    initial_bi_count = len(czsc.bi_list)
    print(f"初始笔数量: {initial_bi_count}")

    # 添加新的K线
    new_bars = create_test_bars(5)
    for bar in new_bars:
        czsc.update(bar)

    updated_bi_count = len(czsc.bi_list)
    print(f"更新后笔数量: {updated_bi_count}")

    # 验证更新后的状态
    assert czsc.symbol == "TEST.SZ"


def test_bi_properties():
    """测试BI对象的属性"""
    bars = create_test_bars(50000)
    czsc = CZSC(bars, max_bi_num=50000)

    bi_list = czsc.bi_list
    if len(bi_list) > 0:
        bi = bi_list[0]

        # 测试所有属性
        print(f"笔符号: {bi.symbol}")
        print(f"笔方向: {bi.direction}")
        print(f"笔高点: {bi.high}")
        print(f"笔低点: {bi.low}")
        print(f"开始时间: {bi.sdt}")
        print(f"结束时间: {bi.edt}")

        # 测试分型
        fx_a = bi.fx_a
        fx_b = bi.fx_b
        print(f"起始分型: {fx_a}")
        print(f"结束分型: {fx_b}")

        # 测试分型列表
        fxs = bi.fxs
        print(f"笔内分型数量: {len(fxs)}")


def test_fx_properties():
    """测试FX对象的属性"""
    bars = create_test_bars(50)
    czsc = CZSC(bars, max_bi_num=50)

    fx_list = czsc.get_fx_list()
    if len(fx_list) > 0:
        fx = fx_list[0]

        # 测试所有属性
        print(f"分型符号: {fx.symbol}")
        print(f"分型时间: {fx.dt}")
        print(f"分型标记: {fx.mark}")
        print(f"分型高点: {fx.high}")
        print(f"分型低点: {fx.low}")
        print(f"分型值: {fx.fx}")


if __name__ == "__main__":
    print("开始测试CZSC Python绑定...")

    test_czsc_creation()
    print("✓ CZSC创建测试通过")

    test_czsc_bi_list()
    print("✓ 笔列表测试通过")

    test_czsc_fx_list()
    print("✓ 分型列表测试通过")

    test_czsc_update()
    print("✓ CZSC更新测试通过")

    test_bi_properties()
    print("✓ BI属性测试通过")

    test_fx_properties()
    print("✓ FX属性测试通过")

    print("所有测试通过！🎉")
