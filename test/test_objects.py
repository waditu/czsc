# coding: utf-8
import numpy as np
from czsc.utils import x_round
from czsc.py import Signal, Event, Freq, Operate
from czsc.utils.stats import cal_break_even_point
from loguru import logger


def test_operate():
    """测试 Operate 对象"""
    lo = Operate.LO
    assert lo.value == "开多"
    
    le = Operate.LE
    assert le.value == "平多"


def test_raw_bar():
    from czsc import mock
    from czsc.utils.ta import SMA
    from czsc.core import format_standard_kline, Freq

    # 使用mock数据替代硬编码数据文件
    df = mock.generate_symbol_kines("000001", "日线", sdt="20230101", edt="20240101", seed=42)
    bars = format_standard_kline(df, freq=Freq.D)
    ma = SMA(np.array([x.close for x in bars]), 5)
    key = "SMA5"
    logger.info(ma)
    # 技术指标的全部更新
    for i in range(1, len(bars) + 1):
        c = dict(bars[-i].cache) if bars[-i].cache else dict()
        c.update({key: ma[-i]})
        bars[-i].cache = c
    # 使用 nansum 处理可能存在的 NaN 值（ta-lib 的 SMA 在数据不足时会返回 NaN）
    cache_sum = np.nansum([x.cache[key] for x in bars])
    ma_sum = np.nansum(ma)
    logger.info(f"cache sum: {cache_sum}, ma sum: {ma_sum}, diff: {abs(cache_sum - ma_sum)}")
    assert np.allclose(cache_sum, ma_sum), f"Mismatch: cache_sum={cache_sum}, ma_sum={ma_sum}"

    # 技术指标的部分更新
    for i in range(1, 101):
        c = dict(bars[-i].cache) if bars[-i].cache else dict()
        # 处理 NaN：如果 ma[-i] 是 NaN，保持为 NaN；否则加 2
        c.update({key: ma[-i] + 2 if not np.isnan(ma[-i]) else ma[-i]})
        bars[-i].cache = c
    cache_sum2 = np.nansum([x.cache[key] for x in bars])
    expected_sum = ma_sum + 200
    logger.info(f"cache sum2: {cache_sum2}, expected: {expected_sum}, diff: {abs(cache_sum2 - expected_sum)}")
    assert np.allclose(cache_sum2, expected_sum), f"Mismatch: cache_sum2={cache_sum2}, expected={expected_sum}"


def test_cal_break_even_point():
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
    from rs_czsc import Signal
    
    s = Signal(key="1分钟_倒1_形态", value="类一买_七笔_基础型_3")
    assert str(s) == "Signal('1分钟_倒1_形态_类一买_七笔_基础型_3')"
    assert s.key == "1分钟_倒1_形态"
    s1 = Signal(signal="1分钟_倒1_形态_类一买_七笔_基础型_3")
    assert s == s1
    assert s.is_match({"1分钟_倒1_形态": "类一买_七笔_基础型_3"})
    assert not s.is_match({"1分钟_倒1_形态": "类一买_七笔_特例一_3"})
    assert not s.is_match({"1分钟_倒1_形态": "类一买_九笔_基础型_3"})

    s = Signal(key="1分钟_倒1形态_类一买", value="任意_任意_任意_3")
    assert str(s) == "Signal('1分钟_倒1形态_类一买_任意_任意_任意_3')"
    assert s.key == "1分钟_倒1形态_类一买"

    try:
        s = Signal(key="1分钟_倒1形态_类一买", value="任意_任意_任意_101")
    except ValueError as e:
        pass


def test_event():
    freq = Freq.F15
    s = {}
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
    m = event.is_match(s)
    assert m

    raw = event.dump()
    new_event = Event.load(raw)
    m = new_event.is_match(s)
    assert m

    raw1 = {
        "name": "单测",
        "operate": "开多",
        "signals_all": ["15分钟_倒0笔_方向_向上_其他_其他_0", 
                        "15分钟_倒0笔_长度_大于5_其他_其他_0"],
    }
    new_event = Event.load(raw1)
    m = new_event.is_match(s)
    assert m

    raw1 = {
        "operate": "开多",
        "signals_all": ["15分钟_倒0笔_方向_向上_其他_其他_0", 
                        "15分钟_倒0笔_长度_大于5_其他_其他_0"],
    }
    new_event = Event.load(raw1)
    m = new_event.is_match(s)
    assert m

    raw1 = {
        "operate": "开多",
        "signals_all": ["15分钟_倒0笔_方向_向上_其他_其他_0", 
                        "15分钟_倒0笔_长度_大于5_其他_其他_0"],
    }
    new_event = Event.load(raw1)
    m = new_event.is_match(s)
    assert m

    event = Event(
        name="单测",
        operate=Operate.LO,
        signals_all=[Signal(signal="15分钟_倒0笔_长度_大于5_其他_其他_0")],
        signals_any=[Signal(signal="15分钟_倒0笔_方向_向上_其他_其他_0"), Signal(signal="15分钟_倒0笔_长度_大于100_其他_其他_0")],
    )
    m = event.is_match(s)
    assert m

    event = Event(
        name="单测",
        operate=Operate.LO,
        signals_all=[Signal(signal=f"{freq.value}_倒0笔_长度_大于5_其他_其他_0")],
        signals_not=[Signal(signal=f"{freq.value}_倒0笔_方向_向上_其他_其他_0")],
    )
    m = event.is_match(s)
    assert not m

    event = Event(
        name="单测",
        operate=Operate.LO,
        signals_all=[
            Signal(signal=f"{freq.value}_倒0笔_方向_向上_其他_其他_0"),
            Signal(signal=f"{freq.value}_倒0笔_长度_大于5_其他_其他_0"),
        ],
    )
    m = event.is_match(s)
    assert m

    event = Event(
        name="单测",
        operate=Operate.LO,
        signals_all=[
            Signal(signal="15分钟_倒0笔_方向_向上_其他_其他_0"),
            Signal(signal="15分钟_倒0笔_长度_任意_其他_其他_0"),
        ],
    )
    m = event.is_match(s)
    assert m

    event = Event(
        name="单测",
        operate=Operate.LO,
        signals_all=[
            Signal(signal="15分钟_倒0笔_方向_向上_其他_其他_20"),
            Signal(signal="15分钟_倒0笔_长度_任意_其他_其他_0"),
        ],
    )
    m = event.is_match(s)
    assert not m

    event = Event(
        name="单测",
        operate=Operate.LO,
        signals_all=[
            Signal(signal="15分钟_倒0笔_方向_向下_其他_其他_0"),
            Signal(signal="15分钟_倒0笔_长度_任意_其他_其他_0"),
        ],
    )
    m = event.is_match(s)
    assert not m

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
