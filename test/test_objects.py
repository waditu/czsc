# coding: utf-8
from collections import OrderedDict
import pandas as pd
from czsc.objects import Signal, Factor, Event, Freq, Operate, PositionLong, PositionShort


def test_signal():
    s = Signal(k1="1分钟", k3="倒1形态", v1="类一买", v2="七笔", v3="基础型", score=3)
    assert str(s) == "Signal('1分钟_任意_倒1形态_类一买_七笔_基础型_3')"
    assert s.key == "1分钟_倒1形态"
    s1 = Signal(signal='1分钟_任意_倒1形态_类一买_七笔_基础型_3')
    assert s == s1
    assert s.is_match({"1分钟_倒1形态": "类一买_七笔_基础型_3"})
    assert not s.is_match({"1分钟_倒1形态": "类一买_七笔_特例一_3"})
    assert not s.is_match({"1分钟_倒1形态": "类一买_九笔_基础型_3"})

    s = Signal(k1="1分钟", k2="倒1形态", k3="类一买", score=3)
    assert str(s) == "Signal('1分钟_倒1形态_类一买_任意_任意_任意_3')"
    assert s.key == "1分钟_倒1形态_类一买"

    try:
        s = Signal(k1="1分钟", k2="倒1形态", k3="类一买", score=101)
    except ValueError as e:
        assert str(e) == 'score 必须在0~100之间'


def test_factor():
    freq = Freq.F15
    s = OrderedDict()
    default_signals = [
        Signal(k1=str(freq.value), k2="倒0笔", k3="方向", v1="向上", v2='其他', v3='其他'),
        Signal(k1=str(freq.value), k2="倒0笔", k3="长度", v1="大于5", v2='其他', v3='其他'),
        Signal(k1=str(freq.value), k2="倒0笔", k3="三K形态", v1="顶分型", v2='其他', v3='其他'),

        Signal(k1=str(freq.value), k2="倒1笔", k3="表里关系", v1="其他", v2='其他', v3='其他'),
        Signal(k1=str(freq.value), k2="倒1笔", k3="RSQ状态", v1="小于0.2", v2='其他', v3='其他'),
    ]
    for signal in default_signals:
        s[signal.key] = signal.value

    factor = Factor(
        name="单测",
        signals_all=[
            Signal(k1=str(freq.value), k2="倒0笔", k3="方向", v1="向上", v2='其他', v3='其他'),
            Signal(k1=str(freq.value), k2="倒0笔", k3="长度", v1="大于5", v2='其他', v3='其他')
        ]
    )
    assert factor.is_match(s)

    factor = Factor(
        name="单测",
        signals_all=[
            Signal(k1=str(freq.value), k2="倒0笔", k3="方向", v1="向上", v2='其他', v3='其他'),
            Signal(k1=str(freq.value), k2="倒0笔", k3="长度", v1="大于5", v2='其他', v3='其他')
        ],
        signals_any=[
            Signal(k1=str(freq.value), k2="倒1笔", k3="RSQ状态", v1="小于0.2", v2='其他', v3='其他')
        ]
    )
    assert factor.is_match(s)

    factor = Factor(
        name="单测",
        signals_all=[
            Signal(k1=str(freq.value), k2="倒0笔", k3="方向", v1="向上", v2='其他', v3='其他'),
            Signal(k1=str(freq.value), k2="倒0笔", k3="长度", v1="大于5", v2='其他', v3='其他')
        ],
        signals_any=[
            Signal(k1=str(freq.value), k2="倒1笔", k3="RSQ状态", v1="小于0.8", v2='其他', v3='其他')
        ]
    )
    assert not factor.is_match(s)

    factor = Factor(
        name="单测",
        signals_all=[
            Signal(k1=str(freq.value), k2="倒0笔", k3="方向", v1="向上", v2='其他', v3='其他'),
            Signal(k1=str(freq.value), k2="倒0笔", k3="长度", v1="大于5", v2='其他', v3='其他')
        ],
        signals_any=[
            Signal(k1=str(freq.value), k2="倒1笔", k3="RSQ状态", v1="小于0.2", v2='其他', v3='其他')
        ],
        signals_not=[
            Signal(k1=str(freq.value), k2="倒0笔", k3="三K形态", v1="顶分型", v2='其他', v3='其他'),
        ]
    )
    assert not factor.is_match(s)


def test_event():
    freq = Freq.F15
    s = OrderedDict()
    default_signals = [
        Signal(k1=str(freq.value), k2="倒0笔", k3="方向", v1="向上", v2='其他', v3='其他'),
        Signal(k1=str(freq.value), k2="倒0笔", k3="长度", v1="大于5", v2='其他', v3='其他'),
        Signal(k1=str(freq.value), k2="倒0笔", k3="三K形态", v1="顶分型", v2='其他', v3='其他'),

        Signal(k1=str(freq.value), k2="倒1笔", k3="表里关系", v1="其他", v2='其他', v3='其他'),
        Signal(k1=str(freq.value), k2="倒1笔", k3="RSQ状态", v1="小于0.2", v2='其他', v3='其他'),
    ]
    for signal in default_signals:
        s[signal.key] = signal.value

    event = Event(name="单测", operate=Operate.LO, factors=[
        Factor(
            name="测试",
            signals_all=[
                Signal(k1=str(freq.value), k2="倒0笔", k3="方向", v1="向上", v2='其他', v3='其他'),
                Signal(k1=str(freq.value), k2="倒0笔", k3="长度", v1="大于5", v2='其他', v3='其他')]
        )
    ])
    m, f = event.is_match(s)
    assert m and f

    event = Event(name="单测", operate=Operate.LO, factors=[
        Factor(
            name="测试",
            signals_all=[
                Signal('15分钟_倒0笔_方向_向上_其他_其他_0'), Signal('15分钟_倒0笔_长度_任意_其他_其他_0')
            ]
        )
    ])
    m, f = event.is_match(s)
    assert m and f

    event = Event(name="单测", operate=Operate.LO, factors=[
        Factor(
            name="测试",
            signals_all=[
                Signal('15分钟_倒0笔_方向_向上_其他_其他_20'), Signal('15分钟_倒0笔_长度_任意_其他_其他_0')
            ]
        )
    ])
    m, f = event.is_match(s)
    assert not m and not f

    event = Event(name="单测", operate=Operate.LO, factors=[
        Factor(
            name="测试",
            signals_all=[
                Signal('15分钟_倒0笔_方向_向下_其他_其他_0'), Signal('15分钟_倒0笔_长度_任意_其他_其他_0')
            ]
        )
    ])
    m, f = event.is_match(s)
    assert not m and not f


def test_position_long():
    pos_long = PositionLong(symbol="000001.XSHG")
    pos_long.update(dt=pd.to_datetime('2021-01-01'), op=Operate.HO, price=100, bid=0)
    assert not pos_long.pos_changed and pos_long.pos == 0

    pos_long.update(dt=pd.to_datetime('2021-01-02'), op=Operate.LO, price=100, bid=1, op_desc="首次开仓测试")
    assert pos_long.pos_changed and pos_long.pos == 0.5

    pos_long.update(dt=pd.to_datetime('2021-01-03'), op=Operate.LO, price=100, bid=2, op_desc="首次开仓测试")
    assert not pos_long.pos_changed and pos_long.pos == 0.5

    pos_long.update(dt=pd.to_datetime('2021-01-04'), op=Operate.LA1, price=100, bid=3)
    assert pos_long.pos_changed and pos_long.pos == 0.8

    pos_long.update(dt=pd.to_datetime('2021-01-05'), op=Operate.LA1, price=100, bid=4)
    assert not pos_long.pos_changed and pos_long.pos == 0.8

    pos_long.update(dt=pd.to_datetime('2021-01-06'), op=Operate.LA2, price=100, bid=5)
    assert pos_long.pos_changed and pos_long.pos == 1

    pos_long.update(dt=pd.to_datetime('2021-01-07'), op=Operate.LR1, price=100, bid=6)
    assert pos_long.pos_changed and pos_long.pos == 0.8

    pos_long.update(dt=pd.to_datetime('2021-01-08'), op=Operate.LR2, price=100, bid=7)
    assert pos_long.pos_changed and pos_long.pos == 0.5

    pos_long.update(dt=pd.to_datetime('2021-01-08'), op=Operate.LR2, price=100, bid=7)
    assert not pos_long.pos_changed and pos_long.pos == 0.5

    pos_long.update(dt=pd.to_datetime('2021-01-09'), op=Operate.LA2, price=100, bid=8)
    assert not pos_long.pos_changed and pos_long.pos == 0.5

    pos_long.update(dt=pd.to_datetime('2021-01-10'), op=Operate.LA1, price=100, bid=9)
    assert pos_long.pos_changed and pos_long.pos == 0.8

    pos_long.update(dt=pd.to_datetime('2021-01-11'), op=Operate.LE, price=100, bid=10)
    assert pos_long.pos_changed and pos_long.pos == 0
    assert len(pos_long.pairs) == 1
    assert pos_long.pairs[0]['持仓天数'] == 9
    pos_long.evaluate_operates()


def test_position_long_t0():
    """测试T0逻辑"""
    pos_long = PositionLong(symbol="000001.XSHG", T0=False)
    pos_long.update(dt=pd.to_datetime('2021-01-01'), op=Operate.HO, price=100, bid=0)
    assert not pos_long.pos_changed and pos_long.pos == 0

    pos_long.update(dt=pd.to_datetime('2021-01-02'), op=Operate.LO, price=100, bid=1, op_desc="首次开仓测试")
    assert pos_long.pos_changed and pos_long.pos == 0.5

    pos_long.update(dt=pd.to_datetime('2021-01-02'), op=Operate.LA1, price=100, bid=3)
    assert pos_long.pos_changed and pos_long.pos == 0.8

    pos_long.update(dt=pd.to_datetime('2021-01-02'), op=Operate.LA2, price=100, bid=5)
    assert pos_long.pos_changed and pos_long.pos == 1

    # T0 平仓信号不生效
    pos_long.update(dt=pd.to_datetime('2021-01-02'), op=Operate.LE, price=100, bid=8)
    assert not pos_long.pos_changed and pos_long.pos == 1

    pos_long.update(dt=pd.to_datetime('2021-01-03'), op=Operate.LE, price=100, bid=10)
    assert pos_long.pos_changed and pos_long.pos == 0

    try:
        pos_long.update(dt=pd.to_datetime('2021-01-03'), op=Operate.SO, price=100, bid=11)
    except AssertionError as e:
        print(e)

    assert len(pos_long.pairs) == 1
    pos_long.evaluate_operates()


def test_position_long_min_interval():
    """测试T0逻辑"""
    pos_long = PositionLong(symbol="000001.XSHG", T0=False, long_min_interval=3600*72)

    pos_long.update(dt=pd.to_datetime('2021-01-01'), op=Operate.HO, price=100, bid=0)
    assert not pos_long.pos_changed and pos_long.pos == 0

    pos_long.update(dt=pd.to_datetime('2021-01-02'), op=Operate.LO, price=100, bid=1, op_desc="首次开仓测试")
    assert pos_long.pos_changed and pos_long.pos == 0.5

    pos_long.update(dt=pd.to_datetime('2021-01-02'), op=Operate.LA1, price=100, bid=3)
    assert pos_long.pos_changed and pos_long.pos == 0.8

    pos_long.update(dt=pd.to_datetime('2021-01-02'), op=Operate.LA2, price=100, bid=5)
    assert pos_long.pos_changed and pos_long.pos == 1

    # T0 平仓信号不生效
    pos_long.update(dt=pd.to_datetime('2021-01-02'), op=Operate.LE, price=100, bid=8)
    assert not pos_long.pos_changed and pos_long.pos == 1

    pos_long.update(dt=pd.to_datetime('2021-01-03'), op=Operate.LE, price=100, bid=10)
    assert pos_long.pos_changed and pos_long.pos == 0

    assert len(pos_long.pairs) == 1

    pos_long.update(dt=pd.to_datetime('2021-01-04'), op=Operate.LE, price=100, bid=11)
    assert not pos_long.pos_changed and pos_long.pos == 0

    # 测试最小开仓间隔
    pos_long.update(dt=pd.to_datetime('2021-01-04'), op=Operate.LO, price=100, bid=12, op_desc="第二次开仓测试")
    assert not pos_long.pos_changed and pos_long.pos == 0

    pos_long.update(dt=pd.to_datetime('2021-01-05'), op=Operate.LO, price=100, bid=13, op_desc="第二次开仓测试")
    assert not pos_long.pos_changed and pos_long.pos == 0

    pos_long.update(dt=pd.to_datetime('2021-01-06'), op=Operate.LO, price=100, bid=14, op_desc="第二次开仓测试")
    assert pos_long.pos_changed and pos_long.pos == 0.5

    pos_long.update(dt=pd.to_datetime('2021-01-09'), op=Operate.LA1, price=100, bid=15)
    assert pos_long.pos_changed and pos_long.pos == 0.8

    pos_long.update(dt=pd.to_datetime('2021-01-10'), op=Operate.LA2, price=100, bid=16)
    assert pos_long.pos_changed and pos_long.pos == 1

    assert len(pos_long.pairs) == 1

    print(pos_long.evaluate_operates())


def test_position_short():
    pos_short = PositionShort(symbol="000001.XSHG")
    pos_short.update(dt=pd.to_datetime('2021-01-01'), op=Operate.HO, price=100, bid=0)
    assert not pos_short.pos_changed and pos_short.pos == 0

    pos_short.update(dt=pd.to_datetime('2021-01-02'), op=Operate.SO, price=100, bid=1, op_desc="首次开仓测试")
    assert pos_short.pos_changed and pos_short.pos == 0.5

    pos_short.update(dt=pd.to_datetime('2021-01-03'), op=Operate.SO, price=100, bid=2, op_desc="首次开仓测试")
    assert not pos_short.pos_changed and pos_short.pos == 0.5

    pos_short.update(dt=pd.to_datetime('2021-01-04'), op=Operate.SA1, price=100, bid=3)
    assert pos_short.pos_changed and pos_short.pos == 0.8

    pos_short.update(dt=pd.to_datetime('2021-01-05'), op=Operate.SA1, price=100, bid=4)
    assert not pos_short.pos_changed and pos_short.pos == 0.8

    pos_short.update(dt=pd.to_datetime('2021-01-06'), op=Operate.SA2, price=100, bid=5)
    assert pos_short.pos_changed and pos_short.pos == 1

    pos_short.update(dt=pd.to_datetime('2021-01-07'), op=Operate.SR1, price=100, bid=6)
    assert pos_short.pos_changed and pos_short.pos == 0.8

    pos_short.update(dt=pd.to_datetime('2021-01-08'), op=Operate.SR2, price=100, bid=7)
    assert pos_short.pos_changed and pos_short.pos == 0.5

    pos_short.update(dt=pd.to_datetime('2021-01-08'), op=Operate.SR2, price=100, bid=7)
    assert not pos_short.pos_changed and pos_short.pos == 0.5

    pos_short.update(dt=pd.to_datetime('2021-01-09'), op=Operate.SA2, price=100, bid=8)
    assert not pos_short.pos_changed and pos_short.pos == 0.5

    pos_short.update(dt=pd.to_datetime('2021-01-10'), op=Operate.SA1, price=100, bid=9)
    assert pos_short.pos_changed and pos_short.pos == 0.8

    pos_short.update(dt=pd.to_datetime('2021-01-11'), op=Operate.SE, price=100, bid=10)
    assert pos_short.pos_changed and pos_short.pos == 0
    assert len(pos_short.pairs) == 1
    assert pos_short.pairs[0]['持仓天数'] == 9
    pos_short.evaluate_operates()


def test_position_short_t0():
    """测试T0逻辑"""
    pos_short = PositionShort(symbol="000001.XSHG", T0=False)
    pos_short.update(dt=pd.to_datetime('2021-01-01'), op=Operate.HO, price=100, bid=0)
    assert not pos_short.pos_changed and pos_short.pos == 0

    pos_short.update(dt=pd.to_datetime('2021-01-02'), op=Operate.SO, price=100, bid=1, op_desc="首次开仓测试")
    assert pos_short.pos_changed and pos_short.pos == 0.5

    pos_short.update(dt=pd.to_datetime('2021-01-02'), op=Operate.SA1, price=100, bid=3)
    assert pos_short.pos_changed and pos_short.pos == 0.8

    pos_short.update(dt=pd.to_datetime('2021-01-02'), op=Operate.SA2, price=100, bid=5)
    assert pos_short.pos_changed and pos_short.pos == 1

    # T0 平仓信号不生效
    pos_short.update(dt=pd.to_datetime('2021-01-02'), op=Operate.SE, price=100, bid=8)
    assert not pos_short.pos_changed and pos_short.pos == 1

    pos_short.update(dt=pd.to_datetime('2021-01-03'), op=Operate.SE, price=100, bid=10)
    assert pos_short.pos_changed and pos_short.pos == 0

    try:
        pos_short.update(dt=pd.to_datetime('2021-01-03'), op=Operate.LO, price=100, bid=11)
    except AssertionError as e:
        print(e)

    assert len(pos_short.pairs) == 1
    pos_short.evaluate_operates()


def test_position_short_min_interval():
    """测试T0逻辑"""
    pos_short = PositionShort(symbol="000001.XSHG", T0=False, short_min_interval=3600*72)

    pos_short.update(dt=pd.to_datetime('2021-01-01'), op=Operate.HO, price=100, bid=0)
    assert not pos_short.pos_changed and pos_short.pos == 0

    pos_short.update(dt=pd.to_datetime('2021-01-02'), op=Operate.SO, price=100, bid=1, op_desc="首次开仓测试")
    assert pos_short.pos_changed and pos_short.pos == 0.5

    pos_short.update(dt=pd.to_datetime('2021-01-02'), op=Operate.SA1, price=100, bid=3)
    assert pos_short.pos_changed and pos_short.pos == 0.8

    pos_short.update(dt=pd.to_datetime('2021-01-02'), op=Operate.SA2, price=100, bid=5)
    assert pos_short.pos_changed and pos_short.pos == 1

    # T0 平仓信号不生效
    pos_short.update(dt=pd.to_datetime('2021-01-02'), op=Operate.SE, price=100, bid=8)
    assert not pos_short.pos_changed and pos_short.pos == 1

    pos_short.update(dt=pd.to_datetime('2021-01-03'), op=Operate.SE, price=100, bid=10)
    assert pos_short.pos_changed and pos_short.pos == 0

    assert len(pos_short.pairs) == 1

    pos_short.update(dt=pd.to_datetime('2021-01-04'), op=Operate.SE, price=100, bid=11)
    assert not pos_short.pos_changed and pos_short.pos == 0

    # 测试最小开仓间隔
    pos_short.update(dt=pd.to_datetime('2021-01-04'), op=Operate.SO, price=100, bid=12, op_desc="第二次开仓测试")
    assert not pos_short.pos_changed and pos_short.pos == 0

    pos_short.update(dt=pd.to_datetime('2021-01-05'), op=Operate.SO, price=100, bid=13, op_desc="第二次开仓测试")
    assert not pos_short.pos_changed and pos_short.pos == 0

    pos_short.update(dt=pd.to_datetime('2021-01-06'), op=Operate.SO, price=100, bid=14, op_desc="第二次开仓测试")
    assert pos_short.pos_changed and pos_short.pos == 0.5

    pos_short.update(dt=pd.to_datetime('2021-01-09'), op=Operate.SA1, price=100, bid=15)
    assert pos_short.pos_changed and pos_short.pos == 0.8

    pos_short.update(dt=pd.to_datetime('2021-01-10'), op=Operate.SA2, price=100, bid=16)
    assert pos_short.pos_changed and pos_short.pos == 1

    assert len(pos_short.pairs) == 1

    print(pos_short.evaluate_operates())
