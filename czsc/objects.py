# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/3/10 12:21
describe: 常用对象结构
"""
import math
from dataclasses import dataclass
from datetime import datetime
from typing import List
from transitions import Machine
from czsc.enum import Mark, Direction, Freq, Operate
from czsc.utils.ta import RSQ


long_operates = [Operate.HO, Operate.LO, Operate.LA1, Operate.LA2, Operate.LE, Operate.LR1, Operate.LR2]
shor_operates = [Operate.HO, Operate.SO, Operate.SA1, Operate.SA2, Operate.SE, Operate.SR1, Operate.SR2]


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
    cache: dict = None    # cache 用户缓存，一个最常见的场景是缓存技术指标计算结果


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
    elements: List = None   # 存入具有包含关系的原始K线
    cache: dict = None      # cache 用户缓存

    @property
    def raw_bars(self):
        return self.elements


@dataclass
class FX:
    symbol: str
    dt: datetime
    mark: Mark
    high: [float, int]
    low: [float, int]
    fx: [float, int]
    elements: List = None
    cache: dict = None      # cache 用户缓存

    @property
    def new_bars(self):
        """构成分型的无包含关系K线"""
        return self.elements

    @property
    def raw_bars(self):
        """构成分型的原始K线"""
        res = []
        for e in self.elements:
            res.extend(e.raw_bars)
        return res

    @property
    def power_str(self):
        assert len(self.elements) == 3
        k1, k2, k3 = self.elements

        if self.mark == Mark.D:
            if k3.close > k1.high:
                x = "强"
            elif k3.close > k2.high:
                x = "中"
            else:
                x = "弱"
        else:
            assert self.mark == Mark.G
            if k3.close < k1.low:
                x = "强"
            elif k3.close < k2.low:
                x = "中"
            else:
                x = "弱"
        return x

    @property
    def power_volume(self):
        """成交量力度"""
        assert len(self.elements) == 3
        return sum([x.vol for x in self.elements])

    @property
    def has_zs(self):
        """构成分型的三根无包含K线是否有重叠中枢"""
        assert len(self.elements) == 3
        zd = max([x.low for x in self.elements])
        zg = min([x.high for x in self.elements])
        return zg >= zd


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
    cache: dict = None      # cache 用户缓存


def create_fake_bis(fxs: List[FX]) -> List[FakeBI]:
    """创建 fake_bis 列表

    :param fxs: 分型序列，必须顶底分型交替
    :return: fake_bis
    """
    if len(fxs) % 2 != 0:
        fxs = fxs[:-1]

    fake_bis = []
    for i in range(1, len(fxs)):
        fx1 = fxs[i-1]
        fx2 = fxs[i]
        assert fx1.mark != fx2.mark
        if fx1.mark == Mark.D:
            fake_bi = FakeBI(symbol=fx1.symbol, sdt=fx1.dt, edt=fx2.dt, direction=Direction.Up,
                             high=fx2.high, low=fx1.low, power=round(fx2.high-fx1.low, 2))
        elif fx1.mark == Mark.G:
            fake_bi = FakeBI(symbol=fx1.symbol, sdt=fx1.dt, edt=fx2.dt, direction=Direction.Down,
                             high=fx1.high, low=fx2.low, power=round(fx1.high-fx2.low, 2))
        else:
            raise ValueError
        fake_bis.append(fake_bi)
    return fake_bis


@dataclass
class BI:
    symbol: str
    fx_a: FX = None     # 笔开始的分型
    fx_b: FX = None     # 笔结束的分型
    fxs: List = None    # 笔内部的分型列表
    direction: Direction = None
    bars: List[NewBar] = None
    cache: dict = None  # cache 用户缓存

    def __post_init__(self):
        self.sdt = self.fx_a.dt
        self.edt = self.fx_b.dt

    def __repr__(self):
        return f"BI(symbol={self.symbol}, sdt={self.sdt}, edt={self.edt}, " \
               f"direction={self.direction}, high={self.high}, low={self.low})"

    # 定义一些附加属性，用的时候才会计算，提高效率
    # ======================================================================
    @property
    def fake_bis(self):
        return create_fake_bis(self.fxs)

    @property
    def high(self):
        return max(self.fx_a.high, self.fx_b.high)

    @property
    def low(self):
        return min(self.fx_a.low, self.fx_b.low)

    @property
    def power(self):
        return self.power_price

    @property
    def power_price(self):
        """价差力度"""
        return round(abs(self.fx_b.fx - self.fx_a.fx), 2)

    @property
    def power_volume(self):
        """成交量力度"""
        return sum([x.vol for x in self.bars[1:-1]])

    @property
    def change(self):
        """笔的涨跌幅"""
        c = round((self.fx_b.fx - self.fx_a.fx) / self.fx_a.fx, 4)
        return c

    @property
    def length(self):
        """笔的无包含关系K线数量"""
        return len(self.bars)

    @property
    def rsq(self):
        """笔的斜率"""
        close = [x.close for x in self.raw_bars]
        return round(RSQ(close), 4)

    @property
    def raw_bars(self):
        """构成笔的原始K线序列"""
        x = []
        for bar in self.bars[1:-1]:
            x.extend(bar.raw_bars)
        return x

    @property
    def hypotenuse(self):
        """笔的斜边长度"""
        return pow(pow(self.power_price, 2) + pow(len(self.raw_bars), 2), 1/2)

    @property
    def angle(self):
        """笔的斜边与竖直方向的夹角，角度越大，力度越大"""
        return round(math.asin(self.power_price / self.hypotenuse) * 180 / 3.14, 2)


@dataclass
class ZS:
    """中枢对象，主要用于辅助信号函数计算"""
    symbol: str
    bis: List[BI]
    cache: dict = None      # cache 用户缓存

    @property
    def sdt(self):
        """中枢开始时间"""
        return self.bis[0].sdt

    @property
    def edt(self):
        """中枢结束时间"""
        return self.bis[-1].edt

    @property
    def sdir(self):
        """中枢第一笔方向"""
        return self.bis[0].direction

    @property
    def edir(self):
        """中枢倒一笔方向"""
        return self.bis[-1].direction

    @property
    def zz(self):
        """中枢中轴"""
        return self.zd + (self.zg - self.zd) / 2

    @property
    def gg(self):
        """中枢最高点"""
        return max([x.high for x in self.bis])

    @property
    def zg(self):
        return min([x.high for x in self.bis[:3]])

    @property
    def dd(self):
        """中枢最低点"""
        return min([x.low for x in self.bis])

    @property
    def zd(self):
        return max([x.low for x in self.bis[:3]])

    def __repr__(self):
        return f"ZS(sdt={self.sdt}, sdir={self.sdir}, edt={self.edt}, edir={self.edir}, " \
               f"len_bis={len(self.bis)}, zg={self.zg}, zd={self.zd}, " \
               f"gg={self.gg}, dd={self.dd}, zz={self.zz})"

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

    # signals_all 必须全部满足的信号，允许为空
    signals_all: List[Signal] = None

    # signals_any 满足其中任一信号，允许为空
    signals_any: List[Signal] = None

    # signals_not 不能满足其中任一信号，允许为空
    signals_not: List[Signal] = None

    def is_match(self, s: dict):
        """判断 event 是否满足"""
        # 首先判断 event 层面的信号是否得到满足
        if self.signals_not:
            # 满足任意一个，直接返回 False
            for signal in self.signals_not:
                if signal.is_match(s):
                    return False, None

        if self.signals_all:
            # 任意一个不满足，直接返回 False
            for signal in self.signals_all:
                if not signal.is_match(s):
                    return False, None

        if self.signals_any:
            one_match = False
            for signal in self.signals_any:
                if signal.is_match(s):
                    one_match = True
                    break
            # 一个都不满足，直接返回 False
            if not one_match:
                return False, None

        # 判断因子是否满足，顺序遍历，找到第一个满足的因子就退出
        # 因子放入事件中时，建议因子列表按关注度从高到低排序
        for factor in self.factors:
            if factor.is_match(s):
                return True, factor.name

        return False, None


def cal_break_even_point(seq: List[float]) -> float:
    """计算单笔收益序列的盈亏平衡点

    :param seq: 单笔收益序列
    :return: 盈亏平衡点
    """
    if len(seq) <= 0 or sum(seq) < 0:
        return 1.0

    seq = sorted(seq)
    sub_ = 0
    sub_i = 0
    for i, s_ in enumerate(seq):
        sub_ += s_
        sub_i = i + 1
        if sub_ >= 0:
            break

    return sub_i / len(seq)


def evaluate_pairs(pairs, symbol: str, trade_dir: str, cost: float = 0.003) -> dict:
    """评估交易表现

    :param pairs:
    :param symbol: 交易标的
    :param trade_dir: 交易方向，可选值 ['多头', '空头']
    :param cost: 双边交易成本
    :return: 交易表现
    """
    p = {"交易标的": symbol, "交易方向": trade_dir,
         "交易次数": len(pairs), '累计收益': 0, '单笔收益': 0,
         '盈利次数': 0, '累计盈利': 0, '单笔盈利': 0,
         '亏损次数': 0, '累计亏损': 0, '单笔亏损': 0,
         '胜率': 0, "累计盈亏比": 0, "单笔盈亏比": 0, "盈亏平衡点": 1}

    if len(pairs) == 0:
        return p

    p['盈亏平衡点'] = round(cal_break_even_point([x['盈亏比例'] for x in pairs]), 4)

    p['复利收益'] = 1
    for pair in pairs:
        p['复利收益'] *= (1 + pair['盈亏比例'] - cost)
    p['复利收益'] = int((p['复利收益'] - 1) * 10000) / 10000

    p['累计收益'] = round(sum([x['盈亏比例'] for x in pairs]), 4)
    p['单笔收益'] = round(p['累计收益'] / p['交易次数'], 4)
    p['平均持仓天数'] = round(sum([x['持仓天数'] for x in pairs]) / len(pairs), 2)
    p['平均持仓K线数'] = round(sum([x['持仓K线数'] for x in pairs]) / len(pairs), 2)

    win_ = [x for x in pairs if x['盈亏比例'] >= 0]
    if len(win_) > 0:
        p['盈利次数'] = len(win_)
        p['累计盈利'] = sum([x['盈亏比例'] for x in win_])
        p['单笔盈利'] = round(p['累计盈利'] / p['盈利次数'], 4)
        p['胜率'] = round(p['盈利次数'] / p['交易次数'], 4)

    loss_ = [x for x in pairs if x['盈亏比例'] < 0]
    if len(loss_) > 0:
        p['亏损次数'] = len(loss_)
        p['累计亏损'] = sum([x['盈亏比例'] for x in loss_])
        p['单笔亏损'] = round(p['累计亏损'] / p['亏损次数'], 4)

        p['累计盈亏比'] = round(p['累计盈利'] / abs(p['累计亏损']), 4)
        p['单笔盈亏比'] = round(p['单笔盈利'] / abs(p['单笔亏损']), 4)

    return p


class PositionLong:
    def __init__(self, symbol: str,
                 hold_long_a: float = 0.5,
                 hold_long_b: float = 0.8,
                 hold_long_c: float = 1.0,
                 long_min_interval: int = None,
                 cost: float = 0.003,
                 T0: bool = False):
        """多头持仓对象

        :param symbol: 标的代码
        :param hold_long_a: 首次开多仓后的仓位
        :param hold_long_b: 第一次加多后的仓位
        :param hold_long_c: 第二次加多后的仓位
        :param long_min_interval: 两次开多仓之间的最小时间间隔，单位：秒
        :param cost: 双边交易成本，默认为千分之三
        :param T0: 是否允许T0交易，默认为 False 表示不允许T0交易
        """
        assert 0 <= hold_long_a <= hold_long_b <= hold_long_c <= 1.0

        self.pos_changed = False
        self.symbol = symbol
        self.long_min_interval = long_min_interval
        self.cost = cost
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
        self.last_pair_operates = []
        self.pairs = []
        self.long_high = -1         # 持多仓期间出现的最高价
        self.long_cost = -1         # 最近一次加多仓的成本
        self.long_bid = -1          # 最近一次加多仓的1分钟Bar ID

        self.today = None
        self.today_pos = 0

    @property
    def pos(self):
        """返回状态对应的仓位"""
        return self.pos_map[self.state]

    def operates_to_pair(self, operates):
        """返回买卖交易对"""
        assert operates[-1]['op'] == Operate.LE and operates[0]['op'] == Operate.LO
        lo_ = [x for x in operates if x['op'] in [Operate.LO, Operate.LA1, Operate.LA2]]
        le_ = [x for x in operates if x['op'] in [Operate.LE, Operate.LR1, Operate.LR2]]
        lo_ops = [x['op'] for x in lo_]

        if Operate.LA2 in lo_ops:
            max_pos_ = self.pos_map['hold_long_c']
        elif Operate.LA1 in lo_ops:
            max_pos_ = self.pos_map['hold_long_b']
        else:
            max_pos_ = self.pos_map['hold_long_a']

        pair = {
            '标的代码': operates[-1]['symbol'],
            '交易方向': "多头",
            '最大仓位': max_pos_,
            '开仓时间': operates[0]['dt'],
            '累计开仓': sum([x['price'] * x['pos_change'] for x in lo_]),
            '平仓时间': operates[-1]['dt'],
            '累计平仓': sum([x['price'] * x['pos_change'] for x in le_]),
            '累计换手': sum([x['pos_change'] for x in operates]),
            '持仓K线数': operates[-1]['bid'] - operates[0]['bid'],
            '事件序列': " > ".join([x['op_desc'] for x in operates]),
        }
        pair['持仓天数'] = (pair['平仓时间'] - pair['开仓时间']).total_seconds() / (24*3600)
        pair['盈亏金额'] = pair['累计平仓'] - pair['累计开仓']
        # 注意：【交易盈亏】的计算是对交易进行的，不是对账户，所以不能用来统计账户的收益
        pair['交易盈亏'] = int((pair['盈亏金额'] / pair['累计开仓']) * 10000) / 10000
        # 注意：根据 max_pos_ 调整【盈亏比例】的计算，便于用来统计账户的收益
        pair['盈亏比例'] = int((pair['盈亏金额'] / pair['累计开仓']) * max_pos_ * 10000) / 10000
        return pair

    def evaluate_operates(self):
        """评估操作表现"""
        return evaluate_pairs(self.pairs, self.symbol, '多头', self.cost)

    def update(self, dt: datetime, op: Operate, price: float, bid: int, op_desc: str = ""):
        """更新多头持仓状态

        :param dt: 最新时间
        :param op: 操作动作
        :param price: 最新价格
        :param bid: 最新1分钟Bar ID
        :param op_desc: 触发操作动作的事件描述
        :return: None
        """
        assert op in long_operates, f"{op} 不是支持的操作"

        if dt.date() != self.today:
            self.today_pos = 0

        state = self.state
        pos_changed = False
        old_pos = self.pos

        if state == 'hold_money' and op == Operate.LO:
            if self.long_min_interval and self.operates:
                assert self.operates[-1]['op'] == Operate.LE
                # 当前和上次平多仓时间的间隔（秒）小于 long_min_interval，不允许开仓
                if (dt - self.operates[-1]['dt']).total_seconds() < self.long_min_interval:
                    return

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

        # 执行卖的两种情况：1）允许T0交易；2）不允许T0交易且今仓为0
        if self.T0 or (not self.T0 and self.today_pos == 0):
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
            operate = {
                "symbol": self.symbol,
                "dt": dt,
                "price": price,
                "bid": bid,
                "op": op,
                "op_desc": op_desc,
                "pos_change": abs(self.pos - old_pos)
            }
            self.operates.append(operate)
            self.last_pair_operates.append(operate)

            if op in [Operate.LO, Operate.LA1, Operate.LA2]:
                # 如果仓位变动为开仓动作，记录开仓时间和价格
                self.long_bid = bid
                self.long_cost = price

            if op == Operate.LE:
                self.pairs.append(self.operates_to_pair(self.last_pair_operates))
                self.last_pair_operates = []

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
                 hold_short_a: float = 0.5,
                 hold_short_b: float = 0.8,
                 hold_short_c: float = 1.0,
                 short_min_interval: int = None,
                 cost: float = 0.003,
                 T0: bool = False):
        """空头持仓对象

        :param symbol: 标的代码
        :param hold_short_a: 首次开空仓后的仓位
        :param hold_short_b: 第一次加空后的仓位
        :param hold_short_c: 第二次加空后的仓位
        :param short_min_interval: 两次开空仓之间的最小时间间隔，单位：秒
        :param cost: 双边交易成本，默认为千分之三
        :param T0: 是否允许T0交易，默认为 False 表示不允许T0交易
        """
        assert 0 <= hold_short_a <= hold_short_b <= hold_short_c <= 1.0

        self.pos_changed = False
        self.symbol = symbol
        self.short_min_interval = short_min_interval
        self.cost = cost
        self.T0 = T0
        self.pos_map = {
            "hold_short_a": hold_short_a, "hold_short_b": hold_short_b,
            "hold_short_c": hold_short_c, "hold_money": 0
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
        self.last_pair_operates = []
        self.pairs = []
        self.short_low = -1          # 持多仓期间出现的最低价
        self.short_cost = -1         # 最近一次加空仓的成本
        self.short_bid = -1          # 最近一次加空仓的1分钟Bar ID

        self.today = None
        self.today_pos = 0

    @property
    def pos(self):
        """返回状态对应的仓位"""
        return self.pos_map[self.state]

    def operates_to_pair(self, operates):
        """返回买卖交易对"""
        assert operates[-1]['op'] == Operate.SE and operates[0]['op'] == Operate.SO
        o_ = [x for x in operates if x['op'] in [Operate.SO, Operate.SA1, Operate.SA2]]
        e_ = [x for x in operates if x['op'] in [Operate.SE, Operate.SR1, Operate.SR2]]
        o_ops = [x['op'] for x in o_]

        if Operate.SA2 in o_ops:
            max_pos_ = self.pos_map['hold_short_c']
        elif Operate.SA1 in o_ops:
            max_pos_ = self.pos_map['hold_short_b']
        else:
            max_pos_ = self.pos_map['hold_short_a']

        pair = {
            '标的代码': operates[-1]['symbol'],
            '交易方向': "空头",
            '最大仓位': max_pos_,
            '开仓时间': operates[0]['dt'],
            '累计开仓': sum([x['price'] * x['pos_change'] for x in o_]),
            '平仓时间': operates[-1]['dt'],
            '累计平仓': sum([x['price'] * x['pos_change'] for x in e_]),
            '累计换手': sum([x['pos_change'] for x in operates]),
            '持仓K线数': operates[-1]['bid'] - operates[0]['bid'],
            '事件序列': " > ".join([x['op_desc'] for x in operates]),
        }
        pair['持仓天数'] = (pair['平仓时间'] - pair['开仓时间']).total_seconds() / (24*3600)
        # 空头计算盈亏，需要取反
        pair['盈亏金额'] = -(pair['累计平仓'] - pair['累计开仓'])
        # 注意：【交易盈亏】的计算是对交易进行的，不是对账户，所以不能用来统计账户的收益
        pair['交易盈亏'] = int((pair['盈亏金额'] / pair['累计开仓']) * 10000) / 10000
        # 注意：根据 max_pos_ 调整【盈亏比例】的计算，便于用来统计账户的收益
        pair['盈亏比例'] = int((pair['盈亏金额'] / pair['累计开仓']) * max_pos_ * 10000) / 10000
        return pair

    def evaluate_operates(self):
        """评估操作表现"""
        return evaluate_pairs(self.pairs, self.symbol, '空头', self.cost)

    def update(self, dt: datetime, op: Operate, price: float, bid: int, op_desc: str = ""):
        """更新空头持仓状态

        :param dt: 最新时间
        :param op: 操作动作
        :param price: 最新价格
        :param bid: 最新1分钟Bar ID
        :param op_desc: 触发操作动作的事件描述
        :return: None
        """
        assert op in shor_operates, f"{op} 不是支持的操作"
        if dt.date() != self.today:
            self.today_pos = 0

        state = self.state
        pos_changed = False
        old_pos = self.pos

        if state == 'hold_money' and op == Operate.SO:
            if self.short_min_interval and self.operates:
                assert self.operates[-1]['op'] == Operate.SE
                # 当前和上次平多仓时间的间隔（秒）小于 long_min_interval，不允许开仓
                if (dt - self.operates[-1]['dt']).total_seconds() < self.short_min_interval:
                    return

            self.short_open()
            pos_changed = True
            self.today_pos = self.pos

        if state == 'hold_short_a' and op == Operate.SA1:
            self.short_add1()
            pos_changed = True
            self.today_pos = self.pos

        if state == 'hold_short_b' and op == Operate.SA2:
            self.short_add2()
            pos_changed = True
            self.today_pos = self.pos

        # 执行卖的两种情况：1）允许T0交易；2）不允许T0交易且今仓为0
        if self.T0 or (not self.T0 and self.today_pos == 0):
            if state == 'hold_short_c' and op == Operate.SR1:
                self.short_reduce1()
                pos_changed = True

            if state in ['hold_short_b', 'hold_short_c'] and op == Operate.SR2:
                self.short_reduce2()
                pos_changed = True

            if state in ['hold_short_a', 'hold_short_b', 'hold_short_c'] and op == Operate.SE:
                self.short_exit()
                pos_changed = True

        if pos_changed:
            operate = {
                "symbol": self.symbol,
                "dt": dt,
                "price": price,
                "bid": bid,
                "op": op,
                "op_desc": op_desc,
                "pos_change": abs(self.pos - old_pos)
            }
            self.operates.append(operate)
            self.last_pair_operates.append(operate)

            if op in [Operate.SO, Operate.SA1, Operate.SA2]:
                # 如果仓位变动为开仓动作，记录开仓时间和价格
                self.short_bid = bid
                self.short_cost = price

            if op == Operate.SE:
                self.pairs.append(self.operates_to_pair(self.last_pair_operates))
                self.last_pair_operates = []

        self.pos_changed = pos_changed
        self.today = dt.date()

        if self.pos > 0:
            # 如果有空头仓位，更新持仓期间的最低价
            self.short_low = price if self.short_low <= 0 else min(self.short_low, price)
        else:
            self.short_low = -1.0
            self.short_cost = -1.0
            self.short_bid = -1.0


class Position:
    def __init__(self, symbol: str,
                 events: List[Event],
                 hold_a: float = 0.5,
                 hold_b: float = 0.8,
                 hold_c: float = 1.0,
                 min_interval: int = None,
                 cost: float = 0.003,
                 T0: bool = False):
        """空头持仓对象

        :param symbol: 标的代码
        :param hold_a: 首次开仓后的仓位
        :param hold_b: 第一次加仓后的仓位
        :param hold_c: 第二次加仓的仓位
        :param min_interval: 两次开空仓之间的最小时间间隔，单位：秒
        :param cost: 双边交易成本，默认为千分之三
        :param T0: 是否允许T0交易，默认为 False 表示不允许T0交易
        """
        assert 0 <= hold_a <= hold_b <= hold_c <= 1.0
        if events[0].operate in long_operates:
            for event in events:
                assert event.operate in long_operates
            self._position = PositionLong(symbol, hold_a, hold_b, hold_c, min_interval, cost, T0)
        else:
            for event in events:
                assert event.operate in shor_operates
            self._position = PositionShort(symbol, hold_a, hold_b, hold_c, min_interval, cost, T0)
        self.events = events

    @property
    def pos(self):
        """返回状态对应的仓位"""
        return self._position.pos

    def update(self, s: dict):
        """更新持仓状态

        :param s: 最新信号字典
        :return:
        """
        op = Operate.HO
        op_desc = ""

        for event in self.events:
            m, f = event.is_match(s)
            if m:
                op = event.operate
                op_desc = f"{event.name}@{f}"
                break
        dt, price, bid = s['dt'], s['close'], s['bid']
        self._position.update(dt, op, price, bid, op_desc)
