# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/3/10 12:21
describe: 常用对象结构
"""
import hashlib
import pandas as pd
from copy import deepcopy
from dataclasses import dataclass, field
from loguru import logger
from deprecated import deprecated
from typing import List, Dict
from czsc.enum import Mark, Direction, Freq, Operate
from czsc.utils.corr import single_linear
from rs_czsc import (
    FakeBI, 
    RawBar, 
    NewBar, 
    BI, 
    FX, 
    ZS, 
    Signal, 
    Event, 
    Position
)

__all__ = [
    "RawBar",
    "NewBar",
    "FakeBI",
    "BI",
    "FX",
    "ZS",
    "Signal",
    "Event",
    "Position",
    "cal_break_even_point",
    "single_linear",
    "Freq",
]


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



# @dataclass
# class Event:
#     operate: Operate

#     # signals_all 必须全部满足的信号，允许为空
#     signals_all: List[Signal] = field(default_factory=list)

#     # signals_any 满足其中任一信号，允许为空
#     signals_any: List[Signal] = field(default_factory=list)

#     # signals_not 不能满足其中任一信号，允许为空
#     signals_not: List[Signal] = field(default_factory=list)

#     name: str = ""

#     def __post_init__(self):
#         _event = self.dump()
#         _event.pop("name")

#         sha256 = hashlib.sha256(str(_event).encode("utf-8")).hexdigest().upper()[:4]
#         if self.name:
#             self.name = self.name.split("#")[0] + f"#{sha256}"
#             # self.name = f"{self.name}#{sha256}"
#         else:
#             self.name = f"{self.operate.value}#{sha256}"
#         self.sha256 = sha256

#     @property
#     def unique_signals(self) -> List[str]:
#         """获取 Event 的唯一信号列表"""
#         signals = []
#         if self.signals_all:
#             signals.extend(self.signals_all)
#         if self.signals_any:
#             signals.extend(self.signals_any)
#         if self.signals_not:
#             signals.extend(self.signals_not)

#         signals = {x.to_string() if isinstance(x, Signal) else x for x in signals}
#         return list(signals)

#     def get_signals_config(self, signals_module: str = "czsc.signals") -> List[Dict]:
#         """获取事件的信号配置"""
#         from czsc.traders.sig_parse import get_signals_config

#         return get_signals_config(self.unique_signals, signals_module)

#     def is_match(self, s: dict):
#         """判断 event 是否满足

#         代码的执行逻辑如下：

#         1. 首先判断 signals_not 中的信号是否得到满足，如果满足任意一个信号，则直接返回 False，表示事件不满足。
#         2. 接着判断 signals_all 中的信号是否全部得到满足，如果有任意一个信号不满足，则直接返回 False，表示事件不满足。
#         3. 然后判断 signals_any 中的信号是否有一个得到满足，如果一个都不满足，则直接返回 False，表示事件不满足。
#         4. 最后判断因子是否满足，顺序遍历因子列表，找到第一个满足的因子就退出，并返回 True 和该因子的名称，表示事件满足。
#         5. 如果遍历完所有因子都没有找到满足的因子，则返回 False，表示事件不满足。
#         """
#         if self.signals_not and any(signal.is_match(s) for signal in self.signals_not):
#             return False

#         if self.signals_all and not all(signal.is_match(s) for signal in self.signals_all):
#             return False

#         if self.signals_any and not any(signal.is_match(s) for signal in self.signals_any):
#             return False

#         return True

#     def dump(self) -> dict:
#         """将 Event 对象转存为 dict"""
#         signals_all = [x.to_string() for x in self.signals_all] if self.signals_all else []
#         signals_any = [x.to_string() for x in self.signals_any] if self.signals_any else []
#         signals_not = [x.to_string() for x in self.signals_not] if self.signals_not else []
#         raw = {
#             "name": self.name,
#             "operate": self.operate.value,
#             "signals_all": signals_all,
#             "signals_any": signals_any,
#             "signals_not": signals_not,
#         }
#         return raw

#     @classmethod
#     def load(cls, raw: dict):
#         """从 dict 中创建 Event

#         :param raw: 样例如下
#                         {'name': '单测',
#                          'operate': '开多',
#                          'signals_all': ['15分钟_倒0笔_方向_向上_其他_其他_0'],
#                          'signals_any': [],
#                          'signals_not': []}
#         :return:
#         """
#         # 检查输入参数是否合法
#         assert (
#             raw["operate"] in Operate.__dict__["_value2member_map_"]
#         ), f"operate {raw['operate']} not in Operate"
        
#         e = Event(
#             name=raw.get("name", ""),
#             operate=Operate.__dict__["_value2member_map_"][raw["operate"]],
#             signals_all=[Signal(x) for x in raw.get("signals_all", [])],
#             signals_any=[Signal(x) for x in raw.get("signals_any", [])],
#             signals_not=[Signal(x) for x in raw.get("signals_not", [])],
#         )
#         return e


# def cal_break_even_point(seq: List[float]) -> float:
#     """计算单笔收益序列的盈亏平衡点

#     :param seq: 单笔收益序列
#     :return: 盈亏平衡点
#     """
#     if len(seq) <= 0 or sum(seq) < 0:
#         return 1.0

#     seq = sorted(seq)
#     sub_ = 0
#     sub_i = 0
#     for i, s_ in enumerate(seq):
#         sub_ += s_
#         sub_i = i + 1
#         if sub_ >= 0:
#             break

#     return sub_i / len(seq)


# class Position:
#     def __init__(
#         self,
#         symbol: str,
#         opens: List[Event],
#         exits: List[Event] = [],
#         interval: int = 0,
#         timeout: int = 1000,
#         stop_loss=1000,
#         T0: bool = False,
#         name=None,
#     ):
#         """简单持仓对象，仓位表达：1 持有多头，-1 持有空头，0 空仓

#         :param symbol: 标的代码
#         :param opens: 开仓交易事件列表
#         :param exits: 平仓交易事件列表，允许为空
#         :param interval: 同类型开仓间隔时间，单位：秒；默认值为 0，表示同类型开仓间隔没有约束
#                 假设上次开仓为多头，那么下一次多头开仓时间必须大于 上次开仓时间 + interval；空头也是如此。
#         :param timeout: 最大允许持仓K线数量限制为最近一个开仓事件触发后的 timeout 根基础周期K线
#         :param stop_loss: 最大允许亏损比例，单位：BP， 1BP = 0.01%；成本的计算以最近一个开仓事件触发价格为准
#         :param T0: 是否允许T0交易，默认为 False 表示不允许T0交易
#         :param name: 仓位名称，默认值为第一个开仓事件的名称
#         """
#         assert name, "name 是必须的参数"
#         self.symbol = symbol
#         self.opens = opens
#         self.name = name
#         self.exits = exits if exits else []
#         self.events = self.opens + self.exits
#         for event in self.events:
#             assert event.operate in [Operate.LO, Operate.LE, Operate.SO, Operate.SE]

#         self.interval = interval
#         self.timeout = timeout
#         self.stop_loss = stop_loss
#         self.T0 = T0

#         self.pos_changed = False  # 仓位是否发生变化
#         self.operates = []  # 事件触发的操作列表
#         self.holds = []  # 持仓状态列表
#         self.pos = 0

#         # 辅助判断的缓存数据
#         self.last_event = {
#             "dt": None,
#             "bid": None,
#             "price": None,
#             "op": None,
#             "op_desc": None,
#         }
#         self.last_lo_dt = None  # 最近一次开多交易的时间
#         self.last_so_dt = None  # 最近一次开空交易的时间
#         self.end_dt = None  # 最近一次信号传入的时间

#     def __repr__(self):
#         return (
#             f"Position(name={self.name}, symbol={self.symbol}, opens={[x.name for x in self.opens]}, "
#             f"timeout={self.timeout}, stop_loss={self.stop_loss}BP, T0={self.T0}, interval={self.interval}s)"
#         )

#     @property
#     def unique_signals(self) -> List[str]:
#         """获取所有事件的唯一信号列表"""
#         signals = []
#         for e in self.events:
#             signals.extend(e.unique_signals)
#         return list(set(signals))

#     def get_signals_config(self, signals_module: str = "czsc.signals") -> List[Dict]:
#         """获取事件的信号配置"""
#         from czsc.traders.sig_parse import get_signals_config

#         return get_signals_config(self.unique_signals, signals_module)

#     def dump(self, with_data=False):
#         """将对象转换为 dict"""
#         raw = {
#             "symbol": self.symbol,
#             "name": self.name,
#             "opens": [x.dump() for x in self.opens],
#             "exits": [x.dump() for x in self.exits],
#             "interval": self.interval,
#             "timeout": self.timeout,
#             "stop_loss": self.stop_loss,
#             "T0": self.T0,
#         }
#         if with_data:
#             raw.update({"pairs": self.pairs, "holds": self.holds})
#         return raw

#     @classmethod
#     def load(cls, raw: dict):
#         """从 dict 中创建 Position

#         :param raw: 样例如下
#         :return:
#         """
#         pos = Position(
#             name=raw["name"],
#             symbol=raw["symbol"],
#             opens=[Event.load(x) for x in raw["opens"] if raw.get("opens")],
#             exits=[Event.load(x) for x in raw["exits"] if raw.get("exits")],
#             interval=raw["interval"],
#             timeout=raw["timeout"],
#             stop_loss=raw["stop_loss"],
#             T0=raw["T0"],
#         )
#         return pos

#     @property
#     def pairs(self):
#         """开平交易列表

#         返回样例：

#         [{'标的代码': '000001.SH',
#           '交易方向': '多头',
#           '开仓时间': Timestamp('2020-04-17 00:00:00'),
#           '平仓时间': Timestamp('2020-04-20 00:00:00'),
#           '开仓价格': 2838.49,
#           '平仓价格': 2852.55,
#           '持仓K线数': 1,
#           '事件序列': '开多@站上SMA5 -> 开多@站上SMA5',
#           '持仓天数': 3.0,
#           '盈亏比例': 49.53},
#          {'标的代码': '000001.SH',
#           '交易方向': '多头',
#           '开仓时间': Timestamp('2020-04-20 00:00:00'),
#           '平仓时间': Timestamp('2020-04-24 00:00:00'),
#           '开仓价格': 2852.55,
#           '平仓价格': 2808.53,
#           '持仓K线数': 4,
#           '事件序列': '开多@站上SMA5 -> 平多@100BP止损',
#           '持仓天数': 4.0,
#           '盈亏比例': -154.32}]

#         数据说明：

#         1. 盈亏比例，单位是 BP
#         2. 持仓天数，单位是 自然日
#         3. 持仓K线数，指基础周期K线数量
#         """
#         pairs = []

#         for op1, op2 in zip(self.operates, self.operates[1:]):
#             if op1["op"] not in [Operate.LO, Operate.SO]:
#                 continue

#             ykr = (
#                 op2["price"] / op1["price"] - 1
#                 if op1["op"] == Operate.LO
#                 else 1 - op2["price"] / op1["price"]
#             )
#             pair = {
#                 "标的代码": self.symbol,
#                 "策略标记": self.name,
#                 "交易方向": "多头" if op1["op"] == Operate.LO else "空头",
#                 "开仓时间": op1["dt"],
#                 "平仓时间": op2["dt"],
#                 "开仓价格": op1["price"],
#                 "平仓价格": op2["price"],
#                 "持仓K线数": op2["bid"] - op1["bid"],
#                 "事件序列": f"{op1['op_desc']} -> {op2['op_desc']}",
#                 "持仓天数": (op2["dt"] - op1["dt"]).total_seconds() / (24 * 3600),
#                 "盈亏比例": round(ykr * 10000, 2),  # 盈亏比例 转换成以 BP 为单位的收益，1BP = 0.0001
#             }
#             pairs.append(pair)

#         return pairs

#     def evaluate_holds(self, trade_dir: str = "多空") -> dict:
#         """按持仓信号评估交易表现

#         :param trade_dir: 交易方向，可选值 ['多头', '空头', '多空']
#         :return: 交易表现
#         """
#         holds = deepcopy(self.holds)
#         if trade_dir != "多空":
#             _OD = 1 if trade_dir == "多头" else -1
#             for hold in holds:
#                 if hold["pos"] != 0 and hold["pos"] != _OD:
#                     hold["pos"] = 0

#         p = {
#             "交易标的": self.symbol,
#             "策略标记": self.name,
#             "交易方向": trade_dir,
#             "开始时间": "",
#             "结束时间": "",
#             "覆盖率": 0,
#             "夏普": 0,
#             "卡玛": 0,
#             "最大回撤": 0,
#             "年化收益": 0,
#             "日胜率": 0,
#         }

#         if len(holds) == 0 or all(x["pos"] == 0 for x in holds):
#             return p

#         dfh = pd.DataFrame(holds)
#         dfh["n1b"] = (dfh["price"].shift(-1) - dfh["price"]) / dfh["price"]
#         dfh["trade_date"] = dfh["dt"].apply(lambda x: x.strftime("%Y-%m-%d"))
#         dfh["edge"] = dfh["n1b"] * dfh["pos"]  # 持有下一根K线的边际收益

#         # 按日期聚合
#         dfv = dfh.groupby("trade_date")["edge"].sum()
#         dfv = dfv.cumsum()

#         yearly_n = 252
#         yearly_ret = dfv.iloc[-1] * (yearly_n / len(dfv))
#         sharp = (
#             dfv.diff().mean() / dfv.diff().std() * pow(yearly_n, 0.5)
#             if dfv.diff().std() != 0
#             else 0
#         )
#         df0 = dfv.shift(1).ffill().fillna(0)
#         mdd = (1 - (df0 + 1) / (df0 + 1).cummax()).max()
#         calmar = yearly_ret / mdd if mdd != 0 else 1

#         p.update(
#             {
#                 "开始时间": dfh["dt"].iloc[0].strftime("%Y-%m-%d"),
#                 "结束时间": dfh["dt"].iloc[-1].strftime("%Y-%m-%d"),
#                 "覆盖率": round(len(dfh[dfh["pos"] != 0]) / len(dfh), 4),
#                 "夏普": round(sharp, 4),
#                 "卡玛": round(calmar, 4),
#                 "最大回撤": round(mdd, 4),
#                 "年化收益": round(yearly_ret, 4),
#                 "日胜率": round(sum(dfv > 0) / len(dfv), 4),
#             }
#         )
#         return p

#     def evaluate(self, trade_dir: str = "多空") -> dict:
#         """评估交易表现

#         :param trade_dir: 交易方向，可选值 ['多头', '空头', '多空']
#         :return: 交易表现
#         """
#         from czsc.utils.stats import evaluate_pairs

#         p = evaluate_pairs(pd.DataFrame(self.pairs), trade_dir)
#         p.update(self.evaluate_holds(trade_dir))
#         return p

#     def update(self, s: dict):
#         """更新持仓状态

#         函数执行逻辑：

#         - 首先，检查最新信号的时间是否在上次信号之前，如果是则打印警告信息并返回。
#         - 初始化一些变量，包括操作类型（op）和操作描述（op_desc）。
#         - 遍历所有的事件，检查是否与最新信号匹配。如果匹配，则记录操作类型和操作描述，并跳出循环。
#         - 提取最新信号的相关信息，包括交易对符号、时间、价格和成交量。
#         - 更新持仓状态的结束时间为最新信号的时间。
#         - 如果操作类型是开仓（LO或SO），更新最后一个事件的信息。
#         - 定义一个内部函数__create_operate，用于创建操作记录。
#         - 根据操作类型更新仓位和操作记录。

#             - 如果操作类型是LO（开多），检查是否满足开仓条件，如果满足则开多仓，否则只平空仓。
#             - 如果操作类型是SO（开空），检查是否满足开仓条件，如果满足则开空仓，否则只平多仓。
#             - 如果当前持仓为多仓，进行多头出场的判断：
#                 - 如果操作类型是LE（平多），平多仓。
#                 - 如果当前价格相对于最后一个事件的价格的收益率小于止损阈值，平多仓。
#                 - 如果当前成交量相对于最后一个事件的成交量的增加量大于超时阈值，平多仓。

#             - 如果当前持仓为空仓，进行空头出场的判断：
#                 - 如果操作类型是SE（平空），平空仓。
#                 - 如果当前价格相对于最后一个事件的价格的收益率小于止损阈值，平空仓。
#                 - 如果当前成交量相对于最后一个事件的成交量的增加量大于超时阈值，平空仓。

#         - 将当前持仓状态和价格记录到持仓列表中。

#         :param s: 最新信号字典
#         :return:
#         """
#         if self.end_dt and s["dt"] <= self.end_dt:
#             logger.warning(f"请检查信号传入：最新信号时间{s['dt']}在上次信号时间{self.end_dt}之前")
#             return

#         self.pos_changed = False
#         op = Operate.HO
#         op_desc = ""
#         for event in self.events:
#             m, f = event.is_match(s)
#             if m:
#                 op = event.operate
#                 op_desc = event.name
#                 break

#         symbol, dt, price, bid = s["symbol"], s["dt"], s["close"], s["id"]
#         self.end_dt = dt

#         # 当有新的开仓 event 发生，更新 last_event
#         if op in [Operate.LO, Operate.SO]:
#             self.last_event = {
#                 "dt": dt,
#                 "bid": bid,
#                 "price": price,
#                 "op": op,
#                 "op_desc": op_desc,
#             }

#         def __create_operate(_op, _op_desc):
#             self.pos_changed = True
#             return {
#                 "symbol": symbol,
#                 "dt": dt,
#                 "bid": bid,
#                 "price": price,
#                 "op": _op,
#                 "op_desc": _op_desc,
#                 "pos": self.pos,
#             }

#         # 更新仓位
#         if op == Operate.LO:
#             if self.pos != 1 and (
#                 not self.last_lo_dt
#                 or (dt - self.last_lo_dt).total_seconds() > self.interval
#             ):
#                 # 与前一次开多间隔时间大于 interval，直接开多
#                 self.pos = 1
#                 self.operates.append(__create_operate(Operate.LO, op_desc))
#                 self.last_lo_dt = dt
#             else:
#                 # 与前一次开多间隔时间小于 interval，仅对空头平仓
#                 if self.pos == -1 and (self.T0 or dt.date() != self.last_so_dt.date()):
#                     self.pos = 0
#                     self.operates.append(__create_operate(Operate.SE, op_desc))

#         if op == Operate.SO:
#             if self.pos != -1 and (
#                 not self.last_so_dt
#                 or (dt - self.last_so_dt).total_seconds() > self.interval
#             ):
#                 # 与前一次开空间隔时间大于 interval，直接开空
#                 self.pos = -1
#                 self.operates.append(__create_operate(Operate.SO, op_desc))
#                 self.last_so_dt = dt
#             else:
#                 # 与前一次开空间隔时间小于 interval，仅对多头平仓
#                 if self.pos == 1 and (self.T0 or dt.date() != self.last_lo_dt.date()):
#                     self.pos = 0
#                     self.operates.append(__create_operate(Operate.LE, op_desc))

#         # 多头出场
#         if self.pos == 1 and (self.T0 or dt.date() != self.last_lo_dt.date()):
#             assert self.last_event["dt"] >= self.last_lo_dt

#             # 多头平仓
#             if op == Operate.LE:
#                 self.pos = 0
#                 self.operates.append(__create_operate(Operate.LE, op_desc))

#             # 多头止损
#             if price / self.last_event["price"] - 1 < -self.stop_loss / 10000:
#                 self.pos = 0
#                 self.operates.append(
#                     __create_operate(Operate.LE, f"平多@{self.stop_loss}BP止损")
#                 )

#             # 多头超时
#             if bid - self.last_event["bid"] > self.timeout:
#                 self.pos = 0
#                 self.operates.append(
#                     __create_operate(Operate.LE, f"平多@{self.timeout}K超时")
#                 )

#         # 空头出场
#         if self.pos == -1 and (self.T0 or dt.date() != self.last_so_dt.date()):
#             assert self.last_event["dt"] >= self.last_so_dt

#             # 空头平仓
#             if op == Operate.SE:
#                 self.pos = 0
#                 self.operates.append(__create_operate(Operate.SE, op_desc))

#             # 空头止损
#             if 1 - price / self.last_event["price"] < -self.stop_loss / 10000:
#                 self.pos = 0
#                 self.operates.append(
#                     __create_operate(Operate.SE, f"平空@{self.stop_loss}BP止损")
#                 )

#             # 空头超时
#             if bid - self.last_event["bid"] > self.timeout:
#                 self.pos = 0
#                 self.operates.append(
#                     __create_operate(Operate.SE, f"平空@{self.timeout}K超时")
#                 )

#         self.holds.append({"dt": self.end_dt, "pos": self.pos, "price": price})
