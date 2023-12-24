# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/3/10 12:21
describe: 常用对象结构
"""
import math
import hashlib
import pandas as pd
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger
from deprecated import deprecated
from typing import List, Callable, Dict
from czsc.enum import Mark, Direction, Freq, Operate
from czsc.utils.corr import single_linear


@deprecated(version="1.0.0", reason="请使用 RawBar")
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
    open: float
    close: float
    high: float
    low: float
    vol: float
    amount: float
    cache: dict = field(default_factory=dict)  # cache 用户缓存，一个最常见的场景是缓存技术指标计算结果

    @property
    def upper(self):
        """上影"""
        return self.high - max(self.open, self.close)

    @property
    def lower(self):
        """下影"""
        return min(self.open, self.close) - self.low

    @property
    def solid(self):
        """实体"""
        return abs(self.open - self.close)


@dataclass
class NewBar:
    """去除包含关系后的K线元素"""

    symbol: str
    id: int  # id 必须是升序
    dt: datetime
    freq: Freq
    open: float
    close: float
    high: float
    low: float
    vol: float
    amount: float
    elements: List = field(default_factory=list)  # 存入具有包含关系的原始K线
    cache: dict = field(default_factory=dict)  # cache 用户缓存

    @property
    def raw_bars(self):
        return self.elements


@dataclass
class FX:
    symbol: str
    dt: datetime
    mark: Mark
    high: float
    low: float
    fx: float
    elements: List = field(default_factory=list)
    cache: dict = field(default_factory=dict)  # cache 用户缓存

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
    high: float
    low: float
    power: float
    cache: dict = field(default_factory=dict)  # cache 用户缓存


def create_fake_bis(fxs: List[FX]) -> List[FakeBI]:
    """创建 fake_bis 列表

    :param fxs: 分型序列，必须顶底分型交替
    :return: fake_bis
    """
    if len(fxs) % 2 != 0:
        fxs = fxs[:-1]

    fake_bis = []
    for i in range(1, len(fxs)):
        fx1 = fxs[i - 1]
        fx2 = fxs[i]
        assert fx1.mark != fx2.mark
        if fx1.mark == Mark.D:
            fake_bi = FakeBI(
                symbol=fx1.symbol,
                sdt=fx1.dt,
                edt=fx2.dt,
                direction=Direction.Up,
                high=fx2.high,
                low=fx1.low,
                power=round(fx2.high - fx1.low, 2),
            )
        elif fx1.mark == Mark.G:
            fake_bi = FakeBI(
                symbol=fx1.symbol,
                sdt=fx1.dt,
                edt=fx2.dt,
                direction=Direction.Down,
                high=fx1.high,
                low=fx2.low,
                power=round(fx1.high - fx2.low, 2),
            )
        else:
            raise ValueError
        fake_bis.append(fake_bi)
    return fake_bis


@dataclass
class BI:
    symbol: str
    fx_a: FX    # 笔开始的分型
    fx_b: FX    # 笔结束的分型
    fxs: List   # 笔内部的分型列表
    direction: Direction
    bars: List[NewBar] = field(default_factory=list)
    cache: dict = field(default_factory=dict)  # cache 用户缓存

    def __post_init__(self):
        self.sdt = self.fx_a.dt
        self.edt = self.fx_b.dt

    def __repr__(self):
        return (
            f"BI(symbol={self.symbol}, sdt={self.sdt}, edt={self.edt}, "
            f"direction={self.direction}, high={self.high}, low={self.low})"
        )

    def get_cache_with_default(self, key, default: Callable):
        """带有默认值计算的缓存读取

        :param key: 缓存 key
        :param default: 如果没有缓存数据，用来计算默认值并更新缓存的函数
        :return:
        """
        cache = self.cache if self.cache else {}
        value = cache.get(key, None)
        if not value:
            value = default()
            cache[key] = value
            self.cache = cache
        return value

    def get_price_linear(self, price_key="close"):
        """计算 price 的单变量线性回归特征

        :param price_key: 指定价格类型，可选值 open close high low
        :return value: 单变量线性回归特征，样例如下
            {'slope': 1.565, 'intercept': 67.9783, 'r2': 0.9967}

            slope       标识斜率
            intercept   截距
            r2          拟合优度
        """
        cache = self.cache if self.cache else {}
        key = f"{price_key}_linear_info"
        value = cache.get(key, None)

        if not value:
            value = single_linear([x.__dict__[price_key] for x in self.raw_bars])
            cache[key] = value
            self.cache = cache
        return value

    # 定义一些附加属性，用的时候才会计算，提高效率
    # ======================================================================
    @property
    def fake_bis(self):
        """笔的内部分型连接得到近似次级别笔列表"""

        def __default():
            return create_fake_bis(self.fxs)

        return self.get_cache_with_default("fake_bis", __default)

    @property
    def high(self):
        def __default():
            return max(self.fx_a.high, self.fx_b.high)

        return self.get_cache_with_default("high", __default)

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
        """笔的原始K线 close 单变量线性回归 r2"""
        value = self.get_price_linear("close")
        return round(value["r2"], 4)

    @property
    def raw_bars(self):
        """构成笔的原始K线序列"""

        def __default():
            value = []
            for bar in self.bars[1:-1]:
                value.extend(bar.raw_bars)
            return value

        return self.get_cache_with_default("raw_bars", __default)

    @property
    def hypotenuse(self):
        """笔的斜边长度"""
        return pow(pow(self.power_price, 2) + pow(len(self.raw_bars), 2), 1 / 2)

    @property
    def angle(self):
        """笔的斜边与竖直方向的夹角，角度越大，力度越大"""
        return round(math.asin(self.power_price / self.hypotenuse) * 180 / 3.14, 2)


@dataclass
class ZS:
    """中枢对象，主要用于辅助信号函数计算"""

    bis: List[BI]
    cache: dict = field(default_factory=dict)  # cache 用户缓存

    def __post_init__(self):
        self.symbol = self.bis[0].symbol

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
        """中枢第一笔方向，sdir 是 start direction 的缩写"""
        return self.bis[0].direction

    @property
    def edir(self):
        """中枢倒一笔方向，edir 是 end direction 的缩写"""
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
        """中枢上沿"""
        return min([x.high for x in self.bis[:3]])

    @property
    def dd(self):
        """中枢最低点"""
        return min([x.low for x in self.bis])

    @property
    def zd(self):
        """中枢下沿"""
        return max([x.low for x in self.bis[:3]])

    @property
    def is_valid(self):
        """中枢是否有效"""
        if self.zg < self.zd:
            return False

        for bi in self.bis:
            # 中枢内的笔必须与中枢的上下沿有交集
            if (
                self.zg >= bi.high >= self.zd
                or self.zg >= bi.low >= self.zd
                or bi.high >= self.zg > self.zd >= bi.low
            ):
                continue
            else:
                return False

        return True

    def __repr__(self):
        return (
            f"ZS(sdt={self.sdt}, sdir={self.sdir}, edt={self.edt}, edir={self.edir}, "
            f"len_bis={len(self.bis)}, zg={self.zg}, zd={self.zd}, "
            f"gg={self.gg}, dd={self.dd}, zz={self.zz})"
        )


@dataclass
class Signal:
    signal: str = ""

    # score 取值在 0~100 之间，得分越高，信号越强
    score: int = 0

    # k1, k2, k3 是信号名称
    k1: str = "任意"  # k1 一般是指明信号计算的K线周期，如 60分钟，日线，周线等
    k2: str = "任意"  # k2 一般是记录信号计算的参数
    k3: str = "任意"  # k3 用于区分信号，必须具有唯一性，推荐使用信号分类和开发日期进行标记

    # v1, v2, v3 是信号取值
    v1: str = "任意"
    v2: str = "任意"
    v3: str = "任意"

    # 任意 出现在模板信号中可以指代任何值

    def __post_init__(self):
        if not self.signal:
            self.signal = f"{self.k1}_{self.k2}_{self.k3}_{self.v1}_{self.v2}_{self.v3}_{self.score}"
        else:
            (
                self.k1,
                self.k2,
                self.k3,
                self.v1,
                self.v2,
                self.v3,
                score,
            ) = self.signal.split("_")
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

        代码的执行逻辑如下：

        接收一个字典 s 作为参数，该字典包含了所有信号的信息。从字典 s 中获取名称为 key 的信号的值 v。
        如果 v 不存在，则抛出异常。从信号的值 v 中解析出 v1、v2、v3 和 score 四个变量。

        如果当前信号的得分 score 大于等于目标信号的得分 self.score，则继续执行，否则返回 False。
        如果当前信号的第一个值 v1 等于目标信号的第一个值 self.v1 或者目标信号的第一个值为 "任意"，则继续执行，否则返回 False。
        如果当前信号的第二个值 v2 等于目标信号的第二个值 self.v2 或者目标信号的第二个值为 "任意"，则继续执行，否则返回 False。
        如果当前信号的第三个值 v3 等于目标信号的第三个值 self.v3 或者目标信号的第三个值为 "任意"，则返回 True，否则返回 False。

        :param s: 所有信号字典
        :return: bool
        """
        key = self.key
        v = s.get(key, None)
        if not v:
            raise ValueError(f"{key} 不在信号列表中")

        v1, v2, v3, score = v.split("_")
        if int(score) >= self.score:
            if v1 == self.v1 or self.v1 == "任意":
                if v2 == self.v2 or self.v2 == "任意":
                    if v3 == self.v3 or self.v3 == "任意":
                        return True
        return False


@dataclass
class Factor:
    # signals_all 必须全部满足的信号，至少需要设定一个信号
    signals_all: List[Signal]

    # signals_any 满足其中任一信号，允许为空
    signals_any: List[Signal] = field(default_factory=list)

    # signals_not 不能满足其中任一信号，允许为空
    signals_not: List[Signal] = field(default_factory=list)

    name: str = ""

    def __post_init__(self):
        if not self.signals_all:
            raise ValueError("signals_all 不能为空")
        _fatcor = self.dump()
        _fatcor.pop("name")
        sha256 = hashlib.sha256(str(_fatcor).encode("utf-8")).hexdigest().upper()[:8]
        self.name = f"{self.name}#{sha256}" if self.name else sha256

    @property
    def unique_signals(self) -> List[str]:
        """获取 Factor 的唯一信号列表"""
        signals = []
        signals.extend(self.signals_all)
        if self.signals_any:
            signals.extend(self.signals_any)
        if self.signals_not:
            signals.extend(self.signals_not)
        signals = {x.signal if isinstance(x, Signal) else x for x in signals}
        return list(signals)

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

    def dump(self) -> dict:
        """将 Factor 对象转存为 dict"""
        signals_all = [x.signal for x in self.signals_all]
        signals_any = [x.signal for x in self.signals_any] if self.signals_any else []
        signals_not = [x.signal for x in self.signals_not] if self.signals_not else []

        raw = {
            "name": self.name,
            "signals_all": signals_all,
            "signals_any": signals_any,
            "signals_not": signals_not,
        }
        return raw

    @classmethod
    def load(cls, raw: dict):
        """从 dict 中创建 Factor

        :param raw: 样例如下
            {'name': '单测',
            'signals_all': ['15分钟_倒0笔_方向_向上_其他_其他_0', '15分钟_倒0笔_长度_大于5_其他_其他_0'],
            'signals_any': [],
            'signals_not': []}

        :return:
        """
        signals_any = [Signal(x) for x in raw.get("signals_any", [])]
        signals_not = [Signal(x) for x in raw.get("signals_not", [])]

        fa = Factor(
            name=raw.get("name", ""),
            signals_all=[Signal(x) for x in raw["signals_all"]],
            signals_any=signals_any,
            signals_not=signals_not,
        )
        return fa


@dataclass
class Event:
    operate: Operate

    # 多个信号组成一个因子，多个因子组成一个事件。
    # 单个事件是一系列同类型因子的集合，事件中的任一因子满足，则事件为真。
    factors: List[Factor]

    # signals_all 必须全部满足的信号，允许为空
    signals_all: List[Signal] = field(default_factory=list)

    # signals_any 满足其中任一信号，允许为空
    signals_any: List[Signal] = field(default_factory=list)

    # signals_not 不能满足其中任一信号，允许为空
    signals_not: List[Signal] = field(default_factory=list)

    name: str = ""

    def __post_init__(self):
        if not self.factors:
            raise ValueError("factors 不能为空")
        _event = self.dump()
        _event.pop("name")
        sha256 = hashlib.sha256(str(_event).encode("utf-8")).hexdigest().upper()[:8]
        if self.name:
            self.name = f"{self.name}#{sha256}"
        else:
            self.name = f"{self.operate.value}#{sha256}"
        self.sha256 = sha256

    @property
    def unique_signals(self) -> List[str]:
        """获取 Event 的唯一信号列表"""
        signals = []
        if self.signals_all:
            signals.extend(self.signals_all)
        if self.signals_any:
            signals.extend(self.signals_any)
        if self.signals_not:
            signals.extend(self.signals_not)

        for factor in self.factors:
            signals.extend(factor.unique_signals)

        signals = {x.signal if isinstance(x, Signal) else x for x in signals}
        return list(signals)

    def get_signals_config(self, signals_module: str = "czsc.signals") -> List[Dict]:
        """获取事件的信号配置"""
        from czsc.traders.sig_parse import get_signals_config

        return get_signals_config(self.unique_signals, signals_module)

    def is_match(self, s: dict):
        """判断 event 是否满足

        代码的执行逻辑如下：

        1. 首先判断 signals_not 中的信号是否得到满足，如果满足任意一个信号，则直接返回 False，表示事件不满足。
        2. 接着判断 signals_all 中的信号是否全部得到满足，如果有任意一个信号不满足，则直接返回 False，表示事件不满足。
        3. 然后判断 signals_any 中的信号是否有一个得到满足，如果一个都不满足，则直接返回 False，表示事件不满足。
        4. 最后判断因子是否满足，顺序遍历因子列表，找到第一个满足的因子就退出，并返回 True 和该因子的名称，表示事件满足。
        5. 如果遍历完所有因子都没有找到满足的因子，则返回 False，表示事件不满足。
        """
        if self.signals_not and any(signal.is_match(s) for signal in self.signals_not):
            return False, None

        if self.signals_all and not all(signal.is_match(s) for signal in self.signals_all):
            return False, None

        if self.signals_any and not any(signal.is_match(s) for signal in self.signals_any):
            return False, None

        for factor in self.factors:
            if factor.is_match(s):
                return True, factor.name

        return False, None

    def dump(self) -> dict:
        """将 Event 对象转存为 dict"""
        signals_all = [x.signal for x in self.signals_all] if self.signals_all else []
        signals_any = [x.signal for x in self.signals_any] if self.signals_any else []
        signals_not = [x.signal for x in self.signals_not] if self.signals_not else []
        factors = [x.dump() for x in self.factors]

        raw = {
            "name": self.name,
            "operate": self.operate.value,
            "signals_all": signals_all,
            "signals_any": signals_any,
            "signals_not": signals_not,
            "factors": factors,
        }
        return raw

    @classmethod
    def load(cls, raw: dict):
        """从 dict 中创建 Event

        :param raw: 样例如下
                        {'name': '单测',
                         'operate': '开多',
                         'factors': [{'name': '测试',
                             'signals_all': ['15分钟_倒0笔_长度_大于5_其他_其他_0'],
                             'signals_any': [],
                             'signals_not': []}],
                         'signals_all': ['15分钟_倒0笔_方向_向上_其他_其他_0'],
                         'signals_any': [],
                         'signals_not': []}
        :return:
        """
        # 检查输入参数是否合法
        assert (
            raw["operate"] in Operate.__dict__["_value2member_map_"]
        ), f"operate {raw['operate']} not in Operate"
        assert raw["factors"], "factors can not be empty"

        e = Event(
            name=raw.get("name", ""),
            operate=Operate.__dict__["_value2member_map_"][raw["operate"]],
            factors=[Factor.load(x) for x in raw["factors"]],
            signals_all=[Signal(x) for x in raw.get("signals_all", [])],
            signals_any=[Signal(x) for x in raw.get("signals_any", [])],
            signals_not=[Signal(x) for x in raw.get("signals_not", [])],
        )
        return e


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


class Position:
    def __init__(
        self,
        symbol: str,
        opens: List[Event],
        exits: List[Event] = [],
        interval: int = 0,
        timeout: int = 1000,
        stop_loss=1000,
        T0: bool = False,
        name=None,
    ):
        """简单持仓对象，仓位表达：1 持有多头，-1 持有空头，0 空仓

        :param symbol: 标的代码
        :param opens: 开仓交易事件列表
        :param exits: 平仓交易事件列表，允许为空
        :param interval: 同类型开仓间隔时间，单位：秒；默认值为 0，表示同类型开仓间隔没有约束
                假设上次开仓为多头，那么下一次多头开仓时间必须大于 上次开仓时间 + interval；空头也是如此。
        :param timeout: 最大允许持仓K线数量限制为最近一个开仓事件触发后的 timeout 根基础周期K线
        :param stop_loss: 最大允许亏损比例，单位：BP， 1BP = 0.01%；成本的计算以最近一个开仓事件触发价格为准
        :param T0: 是否允许T0交易，默认为 False 表示不允许T0交易
        :param name: 仓位名称，默认值为第一个开仓事件的名称
        """
        assert name, "name 是必须的参数"
        self.symbol = symbol
        self.opens = opens
        self.name = name
        self.exits = exits if exits else []
        self.events = self.opens + self.exits
        for event in self.events:
            assert event.operate in [Operate.LO, Operate.LE, Operate.SO, Operate.SE]

        self.interval = interval
        self.timeout = timeout
        self.stop_loss = stop_loss
        self.T0 = T0

        self.pos_changed = False  # 仓位是否发生变化
        self.operates = []  # 事件触发的操作列表
        self.holds = []  # 持仓状态列表
        self.pos = 0

        # 辅助判断的缓存数据
        self.last_event = {
            "dt": None,
            "bid": None,
            "price": None,
            "op": None,
            "op_desc": None,
        }
        self.last_lo_dt = None  # 最近一次开多交易的时间
        self.last_so_dt = None  # 最近一次开空交易的时间
        self.end_dt = None  # 最近一次信号传入的时间

    def __repr__(self):
        return (
            f"Position(name={self.name}, symbol={self.symbol}, opens={[x.name for x in self.opens]}, "
            f"timeout={self.timeout}, stop_loss={self.stop_loss}BP, T0={self.T0}, interval={self.interval}s)"
        )

    @property
    def unique_signals(self) -> List[str]:
        """获取所有事件的唯一信号列表"""
        signals = []
        for e in self.events:
            signals.extend(e.unique_signals)
        return list(set(signals))

    def get_signals_config(self, signals_module: str = "czsc.signals") -> List[Dict]:
        """获取事件的信号配置"""
        from czsc.traders.sig_parse import get_signals_config

        return get_signals_config(self.unique_signals, signals_module)

    def dump(self, with_data=False):
        """将对象转换为 dict"""
        raw = {
            "symbol": self.symbol,
            "name": self.name,
            "opens": [x.dump() for x in self.opens],
            "exits": [x.dump() for x in self.exits],
            "interval": self.interval,
            "timeout": self.timeout,
            "stop_loss": self.stop_loss,
            "T0": self.T0,
        }
        if with_data:
            raw.update({"pairs": self.pairs, "holds": self.holds})
        return raw

    @classmethod
    def load(cls, raw: dict):
        """从 dict 中创建 Position

        :param raw: 样例如下
        :return:
        """
        pos = Position(
            name=raw["name"],
            symbol=raw["symbol"],
            opens=[Event.load(x) for x in raw["opens"] if raw.get("opens")],
            exits=[Event.load(x) for x in raw["exits"] if raw.get("exits")],
            interval=raw["interval"],
            timeout=raw["timeout"],
            stop_loss=raw["stop_loss"],
            T0=raw["T0"],
        )
        return pos

    @property
    def pairs(self):
        """开平交易列表

        返回样例：

        [{'标的代码': '000001.SH',
          '交易方向': '多头',
          '开仓时间': Timestamp('2020-04-17 00:00:00'),
          '平仓时间': Timestamp('2020-04-20 00:00:00'),
          '开仓价格': 2838.49,
          '平仓价格': 2852.55,
          '持仓K线数': 1,
          '事件序列': '开多@站上SMA5 -> 开多@站上SMA5',
          '持仓天数': 3.0,
          '盈亏比例': 49.53},
         {'标的代码': '000001.SH',
          '交易方向': '多头',
          '开仓时间': Timestamp('2020-04-20 00:00:00'),
          '平仓时间': Timestamp('2020-04-24 00:00:00'),
          '开仓价格': 2852.55,
          '平仓价格': 2808.53,
          '持仓K线数': 4,
          '事件序列': '开多@站上SMA5 -> 平多@100BP止损',
          '持仓天数': 4.0,
          '盈亏比例': -154.32}]

        数据说明：

        1. 盈亏比例，单位是 BP
        2. 持仓天数，单位是 自然日
        3. 持仓K线数，指基础周期K线数量
        """
        pairs = []

        for op1, op2 in zip(self.operates, self.operates[1:]):
            if op1["op"] not in [Operate.LO, Operate.SO]:
                continue

            ykr = (
                op2["price"] / op1["price"] - 1
                if op1["op"] == Operate.LO
                else 1 - op2["price"] / op1["price"]
            )
            pair = {
                "标的代码": self.symbol,
                "策略标记": self.name,
                "交易方向": "多头" if op1["op"] == Operate.LO else "空头",
                "开仓时间": op1["dt"],
                "平仓时间": op2["dt"],
                "开仓价格": op1["price"],
                "平仓价格": op2["price"],
                "持仓K线数": op2["bid"] - op1["bid"],
                "事件序列": f"{op1['op_desc']} -> {op2['op_desc']}",
                "持仓天数": (op2["dt"] - op1["dt"]).total_seconds() / (24 * 3600),
                "盈亏比例": round(ykr * 10000, 2),  # 盈亏比例 转换成以 BP 为单位的收益，1BP = 0.0001
            }
            pairs.append(pair)

        return pairs

    @deprecated(version="1.0.0", reason="请使用 czsc.utils.stats.evaluate_pairs")
    def evaluate_pairs(self, trade_dir: str = "多空") -> dict:
        """评估交易表现

        :param trade_dir: 交易方向，可选值 ['多头', '空头', '多空']
        :return: 交易表现
        """
        if trade_dir == "多空":
            pairs = self.pairs
        else:
            pairs = [x for x in self.pairs if x["交易方向"] == trade_dir]
        p = {
            "交易标的": self.symbol,
            "策略标记": self.name,
            "交易方向": trade_dir,
            "交易次数": len(pairs),
            "累计收益": 0,
            "单笔收益": 0,
            "盈利次数": 0,
            "累计盈利": 0,
            "单笔盈利": 0,
            "亏损次数": 0,
            "累计亏损": 0,
            "单笔亏损": 0,
            "胜率": 0,
            "累计盈亏比": 0,
            "单笔盈亏比": 0,
            "盈亏平衡点": 1,
        }

        if len(pairs) == 0:
            return p

        p["盈亏平衡点"] = round(cal_break_even_point([x["盈亏比例"] for x in pairs]), 4)
        p["累计收益"] = round(sum([x["盈亏比例"] for x in pairs]), 2)
        p["单笔收益"] = round(p["累计收益"] / p["交易次数"], 2)
        p["平均持仓天数"] = round(sum([x["持仓天数"] for x in pairs]) / len(pairs), 2)
        p["平均持仓K线数"] = round(sum([x["持仓K线数"] for x in pairs]) / len(pairs), 2)

        win_ = [x for x in pairs if x["盈亏比例"] >= 0]
        if len(win_) > 0:
            p["盈利次数"] = len(win_)
            p["累计盈利"] = sum([x["盈亏比例"] for x in win_])
            p["单笔盈利"] = round(p["累计盈利"] / p["盈利次数"], 4)
            p["胜率"] = round(p["盈利次数"] / p["交易次数"], 4)

        loss_ = [x for x in pairs if x["盈亏比例"] < 0]
        if len(loss_) > 0:
            p["亏损次数"] = len(loss_)
            p["累计亏损"] = sum([x["盈亏比例"] for x in loss_])
            p["单笔亏损"] = round(p["累计亏损"] / p["亏损次数"], 4)

            p["累计盈亏比"] = round(p["累计盈利"] / abs(p["累计亏损"]), 4)
            p["单笔盈亏比"] = round(p["单笔盈利"] / abs(p["单笔亏损"]), 4)

        return p

    def evaluate_holds(self, trade_dir: str = "多空") -> dict:
        """按持仓信号评估交易表现

        :param trade_dir: 交易方向，可选值 ['多头', '空头', '多空']
        :return: 交易表现
        """
        holds = deepcopy(self.holds)
        if trade_dir != "多空":
            _OD = 1 if trade_dir == "多头" else -1
            for hold in holds:
                if hold["pos"] != 0 and hold["pos"] != _OD:
                    hold["pos"] = 0

        p = {
            "交易标的": self.symbol,
            "策略标记": self.name,
            "交易方向": trade_dir,
            "开始时间": "",
            "结束时间": "",
            "覆盖率": 0,
            "夏普": 0,
            "卡玛": 0,
            "最大回撤": 0,
            "年化收益": 0,
            "日胜率": 0,
        }

        if len(holds) == 0 or all(x["pos"] == 0 for x in holds):
            return p

        dfh = pd.DataFrame(holds)
        dfh["n1b"] = (dfh["price"].shift(-1) - dfh["price"]) / dfh["price"]
        dfh["trade_date"] = dfh["dt"].apply(lambda x: x.strftime("%Y-%m-%d"))
        dfh["edge"] = dfh["n1b"] * dfh["pos"]  # 持有下一根K线的边际收益

        # 按日期聚合
        dfv = dfh.groupby("trade_date")["edge"].sum()
        dfv = dfv.cumsum()

        yearly_n = 252
        yearly_ret = dfv.iloc[-1] * (yearly_n / len(dfv))
        sharp = (
            dfv.diff().mean() / dfv.diff().std() * pow(yearly_n, 0.5)
            if dfv.diff().std() != 0
            else 0
        )
        df0 = dfv.shift(1).ffill().fillna(0)
        mdd = (1 - (df0 + 1) / (df0 + 1).cummax()).max()
        calmar = yearly_ret / mdd if mdd != 0 else 1

        p.update(
            {
                "开始时间": dfh["dt"].iloc[0].strftime("%Y-%m-%d"),
                "结束时间": dfh["dt"].iloc[-1].strftime("%Y-%m-%d"),
                "覆盖率": round(len(dfh[dfh["pos"] != 0]) / len(dfh), 4),
                "夏普": round(sharp, 4),
                "卡玛": round(calmar, 4),
                "最大回撤": round(mdd, 4),
                "年化收益": round(yearly_ret, 4),
                "日胜率": round(sum(dfv > 0) / len(dfv), 4),
            }
        )
        return p

    def evaluate(self, trade_dir: str = "多空") -> dict:
        """评估交易表现

        :param trade_dir: 交易方向，可选值 ['多头', '空头', '多空']
        :return: 交易表现
        """
        from czsc.utils.stats import evaluate_pairs

        p = evaluate_pairs(pd.DataFrame(self.pairs), trade_dir)
        p.update(self.evaluate_holds(trade_dir))
        return p

    def update(self, s: dict):
        """更新持仓状态

        函数执行逻辑：

        - 首先，检查最新信号的时间是否在上次信号之前，如果是则打印警告信息并返回。
        - 初始化一些变量，包括操作类型（op）和操作描述（op_desc）。
        - 遍历所有的事件，检查是否与最新信号匹配。如果匹配，则记录操作类型和操作描述，并跳出循环。
        - 提取最新信号的相关信息，包括交易对符号、时间、价格和成交量。
        - 更新持仓状态的结束时间为最新信号的时间。
        - 如果操作类型是开仓（LO或SO），更新最后一个事件的信息。
        - 定义一个内部函数__create_operate，用于创建操作记录。
        - 根据操作类型更新仓位和操作记录。

            - 如果操作类型是LO（开多），检查是否满足开仓条件，如果满足则开多仓，否则只平空仓。
            - 如果操作类型是SO（开空），检查是否满足开仓条件，如果满足则开空仓，否则只平多仓。
            - 如果当前持仓为多仓，进行多头出场的判断：
                - 如果操作类型是LE（平多），平多仓。
                - 如果当前价格相对于最后一个事件的价格的收益率小于止损阈值，平多仓。
                - 如果当前成交量相对于最后一个事件的成交量的增加量大于超时阈值，平多仓。

            - 如果当前持仓为空仓，进行空头出场的判断：
                - 如果操作类型是SE（平空），平空仓。
                - 如果当前价格相对于最后一个事件的价格的收益率小于止损阈值，平空仓。
                - 如果当前成交量相对于最后一个事件的成交量的增加量大于超时阈值，平空仓。

        - 将当前持仓状态和价格记录到持仓列表中。

        :param s: 最新信号字典
        :return:
        """
        if self.end_dt and s["dt"] <= self.end_dt:
            logger.warning(f"请检查信号传入：最新信号时间{s['dt']}在上次信号时间{self.end_dt}之前")
            return

        self.pos_changed = False
        op = Operate.HO
        op_desc = ""
        for event in self.events:
            m, f = event.is_match(s)
            if m:
                op = event.operate
                op_desc = f"{event.name}@{f}"
                break

        symbol, dt, price, bid = s["symbol"], s["dt"], s["close"], s["id"]
        self.end_dt = dt

        # 当有新的开仓 event 发生，更新 last_event
        if op in [Operate.LO, Operate.SO]:
            self.last_event = {
                "dt": dt,
                "bid": bid,
                "price": price,
                "op": op,
                "op_desc": op_desc,
            }

        def __create_operate(_op, _op_desc):
            self.pos_changed = True
            return {
                "symbol": symbol,
                "dt": dt,
                "bid": bid,
                "price": price,
                "op": _op,
                "op_desc": _op_desc,
                "pos": self.pos,
            }

        # 更新仓位
        if op == Operate.LO:
            if self.pos != 1 and (
                not self.last_lo_dt
                or (dt - self.last_lo_dt).total_seconds() > self.interval
            ):
                # 与前一次开多间隔时间大于 interval，直接开多
                self.pos = 1
                self.operates.append(__create_operate(Operate.LO, op_desc))
                self.last_lo_dt = dt
            else:
                # 与前一次开多间隔时间小于 interval，仅对空头平仓
                if self.pos == -1 and (self.T0 or dt.date() != self.last_so_dt.date()):
                    self.pos = 0
                    self.operates.append(__create_operate(Operate.SE, op_desc))

        if op == Operate.SO:
            if self.pos != -1 and (
                not self.last_so_dt
                or (dt - self.last_so_dt).total_seconds() > self.interval
            ):
                # 与前一次开空间隔时间大于 interval，直接开空
                self.pos = -1
                self.operates.append(__create_operate(Operate.SO, op_desc))
                self.last_so_dt = dt
            else:
                # 与前一次开空间隔时间小于 interval，仅对多头平仓
                if self.pos == 1 and (self.T0 or dt.date() != self.last_lo_dt.date()):
                    self.pos = 0
                    self.operates.append(__create_operate(Operate.LE, op_desc))

        # 多头出场
        if self.pos == 1 and (self.T0 or dt.date() != self.last_lo_dt.date()):
            assert self.last_event["dt"] >= self.last_lo_dt

            # 多头平仓
            if op == Operate.LE:
                self.pos = 0
                self.operates.append(__create_operate(Operate.LE, op_desc))

            # 多头止损
            if price / self.last_event["price"] - 1 < -self.stop_loss / 10000:
                self.pos = 0
                self.operates.append(
                    __create_operate(Operate.LE, f"平多@{self.stop_loss}BP止损")
                )

            # 多头超时
            if bid - self.last_event["bid"] > self.timeout:
                self.pos = 0
                self.operates.append(
                    __create_operate(Operate.LE, f"平多@{self.timeout}K超时")
                )

        # 空头出场
        if self.pos == -1 and (self.T0 or dt.date() != self.last_so_dt.date()):
            assert self.last_event["dt"] >= self.last_so_dt

            # 空头平仓
            if op == Operate.SE:
                self.pos = 0
                self.operates.append(__create_operate(Operate.SE, op_desc))

            # 空头止损
            if 1 - price / self.last_event["price"] < -self.stop_loss / 10000:
                self.pos = 0
                self.operates.append(
                    __create_operate(Operate.SE, f"平空@{self.stop_loss}BP止损")
                )

            # 空头超时
            if bid - self.last_event["bid"] > self.timeout:
                self.pos = 0
                self.operates.append(
                    __create_operate(Operate.SE, f"平空@{self.timeout}K超时")
                )

        self.holds.append({"dt": self.end_dt, "pos": self.pos, "price": price})
