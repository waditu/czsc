# coding: utf-8
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '..')
from collections import OrderedDict
from czsc.objects import Signal, Factor, Event, Freq, Operate


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
