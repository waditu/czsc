# coding: utf-8
from dataclasses import dataclass
from datetime import datetime
from typing import List
from transitions import Machine

from .enum import Mark, Direction, Freq, Operate


@dataclass
class Tick:
    symbol: str
    name: str = ""
    price: float = 0
    vol: float = 0


@dataclass
class RawBar:
    """原始K线元素"""
    symbol: str
    id: int  # id 必须是升序
    dt: datetime
    freq: Freq
    open: [float, int]
    close: [float, int]
    high: [float, int]
    low: [float, int]
    vol: [float, int]
    amount: [float, int] = None


@dataclass
class NewBar:
    """去除包含关系后的K线元素"""
    symbol: str
    id: int  # id 必须是升序
    dt: datetime
    freq: Freq
    open: [float, int]
    close: [float, int]
    high: [float, int]
    low: [float, int]
    vol: [float, int]
    amount: [float, int] = None
    elements: List = None  # 存入具有包含关系的原始K线


@dataclass
class FX:
    symbol: str
    dt: datetime
    mark: Mark
    high: [float, int]
    low: [float, int]
    fx: [float, int]
    power: str = None
    elements: List = None


@dataclass
class FakeBI:
    """虚拟笔：主要为笔的内部分析提供便利"""
    symbol: str
    sdt: datetime
    edt: datetime
    direction: Direction
    high: [float, int]
    low: [float, int]
    power: [float, int]


@dataclass
class BI:
    symbol: str
    fx_a: FX = None  # 笔开始的分型
    fx_b: FX = None  # 笔结束的分型
    fxs: List = None  # 笔内部的分型列表
    direction: Direction = None
    high: float = None
    low: float = None
    power: float = None
    bars: List = None
    rsq: float = None
    change: float = None
    length: float = None
    fake_bis: List = None

    def __post_init__(self):
        self.sdt = self.fx_a.dt
        self.edt = self.fx_b.dt


@dataclass
class Signal:
    signal: str = None

    # score 取值在 0~100 之间，得分越高，信号越强
    score: int = 0

    # k1, k2, k3 是信号名称
    k1: str = "任意"
    k2: str = "任意"
    k3: str = "任意"

    # v1, v2, v3 是信号取值
    v1: str = "任意"
    v2: str = "任意"
    v3: str = "任意"

    # 任意 出现在模板信号中可以指代任何值

    def __post_init__(self):
        if not self.signal:
            self.signal = f"{self.k1}_{self.k2}_{self.k3}_{self.v1}_{self.v2}_{self.v3}_{self.score}"
        else:
            self.k1, self.k2, self.k3, self.v1, self.v2, self.v3, score = self.signal.split("_")
            self.score = int(score)

        if self.score > 100 or self.score < 0:
            raise ValueError("score 必须在0~100之间")

    def __repr__(self):
        return f"Signal('{self.signal}')"

    @property
    def key(self) -> str:
        """获取信号名称"""
        key = ""
        for k in [self.k1, self.k2, self.k3]:
            if k != "任意":
                key += k + "_"
        return key.strip("_")

    @property
    def value(self) -> str:
        """获取信号值"""
        return f"{self.v1}_{self.v2}_{self.v3}_{self.score}"

    def is_match(self, s: dict) -> bool:
        """判断信号是否与信号列表中的值匹配

        :param s: 所有信号字典
        :return: bool
        """
        key = self.key
        v = s.get(key, None)
        if not v:
            raise ValueError(f"{key} 不在信号列表中")

        v1, v2, v3, score = v.split("_")
        if int(score) >= self.score:
            if v1 == self.v1 or self.v1 == '任意':
                if v2 == self.v2 or self.v2 == '任意':
                    if v3 == self.v3 or self.v3 == '任意':
                        return True
        return False


@dataclass
class Factor:
    name: str

    # signals_all 必须全部满足的信号，至少需要设定一个信号
    signals_all: List[Signal]

    # signals_any 满足其中任一信号，允许为空
    signals_any: List[Signal] = None

    # signals_not 不能满足其中任一信号，允许为空
    signals_not: List[Signal] = None

    def is_match(self, s: dict) -> bool:
        """判断 factor 是否满足"""
        if self.signals_not:
            for signal in self.signals_not:
                if signal.is_match(s):
                    return False

        for signal in self.signals_all:
            if not signal.is_match(s):
                return False

        if not self.signals_any:
            return True

        for signal in self.signals_any:
            if signal.is_match(s):
                return True
        return False


@dataclass
class Event:
    name: str
    operate: Operate

    # 多个信号组成一个因子，多个因子组成一个事件。
    # 单个事件是一系列同类型因子的集合，事件中的任一因子满足，则事件为真。
    factors: List[Factor]

    def is_match(self, s: dict):
        """判断 event 是否满足"""
        for factor in self.factors:
            if factor.is_match(s):
                # 顺序遍历，找到第一个满足的因子就退出。建议因子列表按关注度从高到低排序
                return True, factor.name

        return False, None


class PositionLong:
    def __init__(self, symbol: str,
                 hold_long_a: float = 0.5,
                 hold_long_b: float = 0.8,
                 hold_long_c: float = 1.0,
                 T0: bool = False):
        """多头持仓对象

        :param symbol: 标的代码
        :param hold_long_a: 首次开多仓后的仓位
        :param hold_long_b: 第一次加多后的仓位
        :param hold_long_c: 第二次加多后的仓位
        :param T0: 是否允许T0交易，默认为 False 表示不允许T0交易
        """
        assert 0 <= hold_long_a <= hold_long_b <= hold_long_c <= 1.0

        self.pos_changed = False
        self.symbol = symbol
        self.T0 = T0
        self.pos_map = {
            "hold_long_a": hold_long_a, "hold_long_b": hold_long_b,
            "hold_long_c": hold_long_c, "hold_money": 0
        }
        self.states = list(self.pos_map.keys())
        self.machine = Machine(model=self, states=self.states, initial='hold_money')
        self.machine.add_transition('long_open', 'hold_money', 'hold_long_a')
        self.machine.add_transition('long_add1', 'hold_long_a', 'hold_long_b')
        self.machine.add_transition('long_add2', 'hold_long_b', 'hold_long_c')
        self.machine.add_transition('long_reduce1', 'hold_long_c', 'hold_long_b')
        self.machine.add_transition('long_reduce2', ['hold_long_b', 'hold_long_c'], 'hold_long_a')
        self.machine.add_transition('long_exit', ['hold_long_a', 'hold_long_b', 'hold_long_c'], 'hold_money')

        self.operates = []
        self.long_high = -1         # 持多仓期间出现的最高价
        self.long_cost = -1         # 最近一次加多仓的成本
        self.long_bid = -1          # 最近一次加多仓的1分钟Bar ID

        self.today = None
        self.today_pos = 0

    @property
    def pos(self):
        """返回状态对应的仓位"""
        return self.pos_map[self.state]

    @property
    def pairs(self):
        """返回买卖交易对"""
        operates = self.operates
        pairs = []
        latest_pair = []
        for op in operates:
            latest_pair.append(op)
            if op['op'] == Operate.LE:
                lo_ = [x for x in latest_pair if x['op'] in [Operate.LO, Operate.LA1, Operate.LA2]]
                le_ = [x for x in latest_pair if x['op'] in [Operate.LE, Operate.LR1, Operate.LR2]]
                pair = {
                    '标的代码': op['symbol'],
                    '交易方向': "多头",
                    '开仓时间': lo_[0]['dt'],
                    '累计开仓': sum([x['price'] * x['pos_change'] for x in lo_]),
                    '平仓时间': op['dt'],
                    '累计平仓': sum([x['price'] * x['pos_change'] for x in le_]),
                }
                pair['盈亏金额'] = pair['累计平仓'] - pair['累计开仓']
                pair['盈亏比例'] = int((pair['盈亏金额'] / pair['累计开仓']) * 10000) / 10000
                pairs.append(pair)
                latest_pair = []
        return pairs

    def evaluate_operates(self):
        """评估操作表现"""
        pairs = self.pairs
        p = {"交易标的": self.symbol, "交易次数": len(pairs), '累计收益': 0, '单笔收益': 0,
             '盈利次数': 0, '累计盈利': 0, '单笔盈利': 0,
             '亏损次数': 0, '累计亏损': 0, '单笔亏损': 0,
             '胜率': 0, "累计盈亏比": 0, "单笔盈亏比": 0}

        if len(pairs) == 0:
            return p

        p['累计收益'] = sum([x['盈亏比例'] for x in pairs])
        p['单笔收益'] = p['累计收益'] / p['交易次数']

        win_ = [x for x in pairs if x['盈亏比例'] >= 0]
        if len(win_) > 0:
            p['盈利次数'] = len(win_)
            p['累计盈利'] = sum([x['盈亏比例'] for x in win_])
            p['单笔盈利'] = p['累计盈利'] / p['盈利次数']
            p['胜率'] = round(p['盈利次数'] / p['交易次数'], 4)

        loss_ = [x for x in pairs if x['盈亏比例'] < 0]
        if len(loss_) > 0:
            p['亏损次数'] = len(loss_)
            p['累计亏损'] = sum([x['盈亏比例'] for x in loss_])
            p['单笔亏损'] = p['累计亏损'] / p['亏损次数']

            p['累计盈亏比'] = round(p['累计盈利']/p['累计亏损'], 4)
            p['单笔盈亏比'] = round(p['单笔盈利']/p['单笔亏损'], 4)

        return p

    def update(self, dt: datetime, op: Operate, price: float, bid: int, op_desc: str = ""):
        """更新多头持仓状态

        :param dt: 最新时间
        :param op: 操作动作
        :param price: 最新价格
        :param bid: 最新1分钟Bar ID
        :param op_desc: 触发操作动作的事件描述
        :return: None
        """
        if dt.date() != self.today:
            self.today_pos = 0

        state = self.state
        pos_changed = False
        old_pos = self.pos

        if state == 'hold_money' and op == Operate.LO:
            self.long_open()
            pos_changed = True
            self.today_pos = self.pos

        if state == 'hold_long_a' and op == Operate.LA1:
            self.long_add1()
            pos_changed = True
            self.today_pos = self.pos

        if state == 'hold_long_b' and op == Operate.LA2:
            self.long_add2()
            pos_changed = True
            self.today_pos = self.pos

        if not self.T0:
            # 不允许 T0 交易时，今仓为 0 才可以卖
            if self.today_pos == 0:
                if state == 'hold_long_c' and op == Operate.LR1:
                    self.long_reduce1()
                    pos_changed = True

                if state in ['hold_long_b', 'hold_long_c'] and op == Operate.LR2:
                    self.long_reduce2()
                    pos_changed = True

                if state in ['hold_long_a', 'hold_long_b', 'hold_long_c'] and op == Operate.LE:
                    self.long_exit()
                    pos_changed = True
        else:
            if state == 'hold_long_c' and op == Operate.LR1:
                self.long_reduce1()
                pos_changed = True

            if state in ['hold_long_b', 'hold_long_c'] and op == Operate.LR2:
                self.long_reduce2()
                pos_changed = True

            if state in ['hold_long_a', 'hold_long_b', 'hold_long_c'] and op == Operate.LE:
                self.long_exit()
                pos_changed = True

        if pos_changed:
            if op in [Operate.LO, Operate.LA1, Operate.LA2]:
                # 如果仓位变动为开仓动作，记录开仓时间和价格
                self.long_bid = bid
                self.long_cost = price

            self.operates.append({
                "symbol": self.symbol,
                "dt": dt,
                "price": price,
                "bid": bid,
                "op": op,
                "op_desc": op_desc,
                "pos_change": abs(self.pos - old_pos)
            })
        self.pos_changed = pos_changed
        self.today = dt.date()

        if self.pos > 0:
            # 如果有多头仓位，更新持仓期间的最高价
            self.long_high = max(self.long_high, price)
        else:
            self.long_high = -1.0
            self.long_cost = -1.0
            self.long_bid = -1.0


class PositionShort:
    def __init__(self, symbol: str,
                 hold_short_a: float = -0.5,
                 hold_short_b: float = -0.8,
                 hold_short_c: float = -1.0,
                 ):
        """持仓对象

        :param symbol: 标的代码
        :param hold_short_a: 首次开空仓后的仓位
        :param hold_short_b: 第一次加空后的仓位
        :param hold_short_c: 第二次加空后的仓位
        """
        assert 0 >= hold_short_a >= hold_short_b >= hold_short_c >= -1.0

        self.symbol = symbol
        self.pos_map = {
            "hold_money": 0, "hold_short_a": hold_short_a,
            "hold_short_b": hold_short_b,  "hold_short_c": hold_short_c
        }
        self.states = list(self.pos_map.keys())
        self.machine = Machine(model=self, states=self.states, initial='hold_money')

        self.machine.add_transition('short_open', 'hold_money', 'hold_short_a')
        self.machine.add_transition('short_add1', 'hold_short_a', 'hold_short_b')
        self.machine.add_transition('short_add2', 'hold_short_b', 'hold_short_c')
        self.machine.add_transition('short_reduce1', 'hold_short_c', 'hold_short_b')
        self.machine.add_transition('short_reduce2', ['hold_short_b', 'hold_short_c'], 'hold_short_a')
        self.machine.add_transition('short_exit', ['hold_short_a', 'hold_short_b', 'hold_short_c'], 'hold_money')

        self.operates = []
        self.short_low = -1             # 持空仓期间出现的最低价
        self.short_cost = -1            # 最近一次加空仓的成本
        self.short_bid = -1             # 最近一次加空仓的1分钟Bar ID

    @property
    def pos(self):
        """返回状态对应的仓位"""
        return self.pos_map[self.state]

    def update(self, dt: datetime, op: Operate, price: float, bid: int) -> bool:
        """更新空头持仓状态

        :param dt: 最新时间
        :param op: 操作动作
        :param price: 最新价格
        :param bid: 最新1分钟Bar ID
        :return: bool
        """
        state = self.state
        pos_changed = False

        if state == 'hold_money' and op == Operate.SO:
            self.short_open()
            return True

        if state == 'hold_short_a' and op == Operate.SA1:
            self.short_add1()
            return True

        if state == 'hold_short_b' and op == Operate.SA2:
            self.short_add2()
            return True

        if state == 'hold_short_c' and op == Operate.SR1:
            self.short_reduce1()
            return True

        if state in ['hold_short_b', 'hold_short_c'] and op == Operate.SR2:
            self.short_reduce2()
            return True

        if state in ['hold_short_a', 'hold_short_b', 'hold_short_c'] and op == Operate.SE:
            self.short_exit()
            return True

        return pos_changed
