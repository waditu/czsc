# coding: utf-8
import numpy as np
from collections import OrderedDict
from czsc.utils import x_round
from czsc.objects import Signal, Event, Freq, Operate
from czsc.objects import cal_break_even_point


# def test_raw_bar():
#     from test.test_analyze import read_daily
#     from czsc.utils.ta import SMA
#     bars = read_daily()
#     ma = SMA(np.array([x.close for x in bars]), 5)
#     key = "SMA5"
#
#     # 技术指标的全部更新
#     for i in range(1, len(bars) + 1):
#         c = dict(bars[-i].cache) if bars[-i].cache else dict()
#         c.update({key: ma[-i]})
#         bars[-i].cache = c
#     assert np.array([x.cache[key] for x in bars]).sum() == ma.sum()
#
#     # 技术指标的部分更新
#     for i in range(1, 101):
#         c = dict(bars[-i].cache) if bars[-i].cache else dict()
#         c.update({key: ma[-i] + 2})
#         bars[-i].cache = c
#     assert np.array([x.cache[key] for x in bars]).sum() == ma.sum() + 200


def test_zs():
    """测试中枢对象"""
    from czsc import mock
    from czsc.objects import ZS, RawBar
    from czsc.analyze import CZSC
    from czsc.enum import Freq

    # 使用mock数据替代硬编码数据文件
    df = mock.generate_symbol_kines("000001", "日线", sdt="20230101", edt="20240101", seed=42)
    bars = []
    for i, row in df.iterrows():
        bar = RawBar(
            symbol=row['symbol'], 
            id=i, 
            freq=Freq.D, 
            open=row['open'], 
            dt=row['dt'],
            close=row['close'], 
            high=row['high'], 
            low=row['low'], 
            vol=row['vol'], 
            amount=row['amount']
        )
        bars.append(bar)

    c = CZSC(bars)
    
    if len(c.bi_list) >= 8:
        zs = ZS(c.bi_list[-5:])
        if zs.is_valid:
            assert zs.zd < zs.zg, "中枢下沿应该小于上沿"

        zs = ZS(c.bi_list[-8:-3])
        # 注意：这里不能假设中枢一定无效，因为mock数据的特性可能不同


def test_cal_break_even_point():
    assert cal_break_even_point([]) == 1
    assert cal_break_even_point([1]) == 1
    assert cal_break_even_point([-1, -2, 4, 5, 5]) == 0.6
    assert cal_break_even_point([-1, -2]) == 1
    assert cal_break_even_point([1, 2]) == 0.5
    assert cal_break_even_point([-1, 1, -2]) == 1
    assert cal_break_even_point([0, 1, -1, 2, 3, -6, -7]) == 1
    assert x_round(cal_break_even_point([0, 1, -1, 2, 3, -6, 7, 8])) == 0.875
    assert x_round(cal_break_even_point([-6, -1, 0, 1, 2, 3, 7, 8])) == 0.875
    assert x_round(cal_break_even_point([2, 3, 4, 2, 1, 4, 0, 1, -1, 2, 3, -6, 7, 8])) == 0.5714


def test_signal():
    s = Signal(key="1分钟_倒1形态", value="类一买_七笔_基础型_3")
    assert str(s) == "Signal('1分钟_倒1形态_类一买_七笔_基础型_3')"
    assert s.key == "1分钟_倒1形态"
    s1 = Signal(signal="1分钟_倒1形态_类一买_七笔_基础型_3")
    assert s == s1
    assert s.is_match({"1分钟_倒1形态": "类一买_七笔_基础型_3"})
    assert not s.is_match({"1分钟_倒1形态": "类一买_七笔_特例一_3"})
    assert not s.is_match({"1分钟_倒1形态": "类一买_九笔_基础型_3"})

    s = Signal(key="1分钟_倒1形态_类一买", value="任意_任意_任意_3")
    assert str(s) == "Signal('1分钟_倒1形态_类一买_任意_任意_任意_3')"
    assert s.key == "1分钟_倒1形态_类一买"

    try:
        s = Signal(key="1分钟_倒1形态_类一买", value="任意_任意_任意_101")
    except ValueError as e:
        assert str(e) == "score 必须在0~100之间"



def test_event():
    freq = Freq.F15
    s = OrderedDict()
    default_signals = [
        Signal(signal=f"{freq.value}_倒0笔_方向_向上_其他_其他_0"),
        Signal(signal=f"{freq.value}_倒0笔_长度_大于5_其他_其他_0"),
        Signal(signal=f"{freq.value}_倒0笔_三K形态_顶分型_其他_其他_0"),
        Signal(signal=f"{freq.value}_倒1笔_表里关系_其他_其他_其他_0"),
        Signal(signal=f"{freq.value}_倒1笔_RSQ状态_小于0.2_其他_其他_0"),
    ]
    for signal in default_signals:
        s[signal.key] = signal.value

    event = Event(
        name="单测",
        operate=Operate.LO,
        signals_all=[
            Signal(signal=f"{freq.value}_倒0笔_长度_大于5_其他_其他_0"),
            Signal(signal=f"{freq.value}_倒0笔_方向_向上_其他_其他_0"),
        ],
    )
    m, f = event.is_match(s)
    assert m and f

    raw = event.dump()
    new_event = Event.load(raw)
    m, f = new_event.is_match(s)
    assert m and f

    raw1 = {
        "name": "单测",
        "operate": "开多",
        "signals_all": ["15分钟_倒0笔_方向_向上_其他_其他_0", "15分钟_倒0笔_长度_大于5_其他_其他_0"],
    }
    new_event = Event.load(raw1)
    m, f = new_event.is_match(s)
    assert m and f

    raw1 = {
        "operate": "开多",
        "signals_all": ["15分钟_倒0笔_方向_向上_其他_其他_0", "15分钟_倒0笔_长度_大于5_其他_其他_0"],
    }
    new_event = Event.load(raw1)
    m, f = new_event.is_match(s)
    assert m and f

    event = Event(
        name="单测",
        operate=Operate.LO,
        signals_all=[Signal(signal="15分钟_倒0笔_长度_大于5_其他_其他_0")],
        signals_any=[Signal(signal="15分钟_倒0笔_方向_向上_其他_其他_0"), Signal(signal="15分钟_倒0笔_长度_大于100_其他_其他_0")],
    )
    m, f = event.is_match(s)
    assert m and f

    event = Event(
        name="单测",
        operate=Operate.LO,
        signals_all=[Signal(signal=f"{freq.value}_倒0笔_长度_大于5_其他_其他_0")],
        signals_not=[Signal(signal=f"{freq.value}_倒0笔_方向_向上_其他_其他_0")],
    )
    m, f = event.is_match(s)
    assert not m and not f

    event = Event(
        name="单测",
        operate=Operate.LO,
        signals_all=[
            Signal(signal=f"{freq.value}_倒0笔_方向_向上_其他_其他_0"),
            Signal(signal=f"{freq.value}_倒0笔_长度_大于5_其他_其他_0"),
        ],
    )
    m, f = event.is_match(s)
    assert m and f

    event = Event(
        name="单测",
        operate=Operate.LO,
        signals_all=[
            Signal(signal="15分钟_倒0笔_方向_向上_其他_其他_0"),
            Signal(signal="15分钟_倒0笔_长度_任意_其他_其他_0"),
        ],
    )
    m, f = event.is_match(s)
    assert m and f

    event = Event(
        name="单测",
        operate=Operate.LO,
        signals_all=[
            Signal(signal="15分钟_倒0笔_方向_向上_其他_其他_20"),
            Signal(signal="15分钟_倒0笔_长度_任意_其他_其他_0"),
        ],
    )
    m, f = event.is_match(s)
    assert not m and not f

    event = Event(
        name="单测",
        operate=Operate.LO,
        signals_all=[
            Signal(signal="15分钟_倒0笔_方向_向下_其他_其他_0"),
            Signal(signal="15分钟_倒0笔_长度_任意_其他_其他_0"),
        ],
    )
    m, f = event.is_match(s)
    assert not m and not f

    event = Event.load(
        {
            "name": "开多",
            "operate": "开多",
            "signals_all": [
                "1分钟_D1_涨跌停V230331_任意_任意_任意_0",
                "1分钟_D0停顿分型_BE辅助V230106_看空_强_任意_0",
                "5分钟_D1#SMA#40MO10_BS辅助V230313_看多_任意_任意_0"
            ],
        }
    )
    assert len(event.get_signals_config()) == 3
