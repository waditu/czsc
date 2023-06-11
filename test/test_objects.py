# coding: utf-8
import numpy as np
from collections import OrderedDict
from czsc.utils import x_round
from czsc.objects import Signal, Factor, Event, Freq, Operate
from czsc.objects import cal_break_even_point


def test_raw_bar():
    from test.test_analyze import read_daily
    from czsc.utils.ta import SMA
    bars = read_daily()
    ma = SMA(np.array([x.close for x in bars]), 5)
    key = "SMA5"

    # 技术指标的全部更新
    for i in range(1, len(bars) + 1):
        c = dict(bars[-i].cache) if bars[-i].cache else dict()
        c.update({key: ma[-i]})
        bars[-i].cache = c
    assert np.array([x.cache[key] for x in bars]).sum() == ma.sum()

    # 技术指标的部分更新
    for i in range(1, 101):
        c = dict(bars[-i].cache) if bars[-i].cache else dict()
        c.update({key: ma[-i] + 2})
        bars[-i].cache = c
    assert np.array([x.cache[key] for x in bars]).sum() == ma.sum() + 200


def test_zs():
    """测试中枢对象"""
    from test.test_analyze import read_daily
    from czsc.objects import ZS
    from czsc.analyze import CZSC
    bars = read_daily()
    c = CZSC(bars)

    zs = ZS(c.bi_list[-5:])
    assert zs.zd < zs.zg
    assert zs.is_valid

    zs = ZS(c.bi_list[-8:-3])
    assert not zs.is_valid


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

    factor_raw = factor.dump()
    new_factor = Factor.load(factor_raw)
    assert new_factor.is_match(s)

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
        Factor(name="测试", signals_all=[
            Signal(k1=str(freq.value), k2="倒0笔", k3="长度", v1="大于5", v2='其他', v3='其他')])
    ], signals_all=[
        Signal(k1=str(freq.value), k2="倒0笔", k3="方向", v1="向上", v2='其他', v3='其他'),
    ])
    m, f = event.is_match(s)
    assert m and f

    raw = event.dump()
    new_event = Event.load(raw)
    m, f = new_event.is_match(s)
    assert m and f

    raw1 = {'name': '单测',
            'operate': '开多',
            'signals_all': ['15分钟_倒0笔_方向_向上_其他_其他_0'],
            'factors': [{'name': '测试', 'signals_all': ['15分钟_倒0笔_长度_大于5_其他_其他_0']}]}
    new_event = Event.load(raw1)
    m, f = new_event.is_match(s)
    assert m and f

    raw1 = {'operate': '开多',
            'signals_all': ['15分钟_倒0笔_方向_向上_其他_其他_0'],
            'factors': [{'name': '测试', 'signals_all': ['15分钟_倒0笔_长度_大于5_其他_其他_0']}]}
    new_event = Event.load(raw1)
    m, f = new_event.is_match(s)
    assert m and f

    event = Event(name="单测", operate=Operate.LO,
                  factors=[
                      Factor(name="测试", signals_all=[
                          Signal('15分钟_倒0笔_长度_大于5_其他_其他_0')
                      ]),
                  ],
                  signals_any=[
                      Signal('15分钟_倒0笔_方向_向上_其他_其他_0'),
                      Signal('15分钟_倒0笔_长度_大于100_其他_其他_0')
                  ])
    m, f = event.is_match(s)
    assert m and f

    event = Event(name="单测", operate=Operate.LO,
                  factors=[
                      Factor(name="测试", signals_all=[
                          Signal(k1=str(freq.value), k2="倒0笔", k3="长度", v1="大于5", v2='其他', v3='其他')])
                  ],
                  signals_not=[
                      Signal(k1=str(freq.value), k2="倒0笔", k3="方向", v1="向上", v2='其他', v3='其他'),
                  ])
    m, f = event.is_match(s)
    assert not m and not f

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

    event = Event.load(
        {
            "name": "开多",
            "operate": "开多",
            "signals_all": [
                "1分钟_D1_涨跌停V230331_任意_任意_任意_0",
                "1分钟_D0停顿分型_BE辅助V230106_看空_强_任意_0"
            ],
            "signals_any": [],
            "signals_not": [],
            "factors": [
                {
                    "name": "SMA#40多头",
                    "signals_all": [
                        "5分钟_D1#SMA#40MO10_BS辅助V230313_看多_任意_任意_0"
                    ],
                    "signals_any": [],
                    "signals_not": []
                }
            ]
        }
    )
    assert len(event.get_signals_config()) == 3
