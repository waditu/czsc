# coding: utf-8

from typing import List
from collections import OrderedDict
from datetime import datetime
import pandas as pd
from .objects import Mark, Direction, BI, FX, RawBar, NewBar
from .utils.echarts_plot import kline_pro
from .signals import check_three_fd, check_five_fd, check_seven_fd, check_nine_fd

def remove_include(k1: NewBar, k2: NewBar, k3: RawBar):
    """去除包含关系：输入三根k线，其中k1和k2为没有包含关系的K线，k3为原始K线"""
    if k1.high < k2.high:
        direction = Direction.Up
    elif k1.high > k2.high:
        direction = Direction.Down
    else:
        direction = Direction.Up

    # 判断 k2 和 k3 之间是否存在包含关系，有则处理
    if (k2.high <= k3.high and k2.low >= k3.low) or (k2.high >= k3.high and k2.low <= k3.low):
        if direction == Direction.Up:
            high = max(k2.high, k3.high)
            low = max(k2.low, k3.low)
            dt = k2.dt if k2.high >= k3.high else k3.dt
        elif direction == Direction.Down:
            high = min(k2.high, k3.high)
            low = min(k2.low, k3.low)
            dt = k2.dt if k2.low <= k3.low else k3.dt
        else:
            raise ValueError

        if k3.open > k3.close:
            open_ = high
            close = low
        else:
            open_ = low
            close = high
        vol = k2.vol + k3.vol
        k4 = NewBar(symbol=k3.symbol, dt=dt, open=open_,
                    close=close, high=high, low=low, vol=vol, elements=k2.elements + [k3])
        return True, k4
    else:
        k4 = NewBar(symbol=k3.symbol, dt=k3.dt, open=k3.open,
                    close=k3.close, high=k3.high, low=k3.low, vol=k3.vol, elements=[k3])
        return False, k4


def check_fx(k1: NewBar, k2: NewBar, k3: NewBar):
    """查找分型"""
    fx = None
    if k1.high < k2.high > k3.high:
        power = "强" if k3.close < k1.low else "弱"
        fx = FX(symbol=k1.symbol, dt=k2.dt, mark=Mark.G, high=k2.high, low=k2.low,
                fx=k2.high, elements=[k1, k2, k3], power=power)
    if k1.low > k2.low < k3.low:
        power = "强" if k3.close > k1.high else "弱"
        fx = FX(symbol=k1.symbol, dt=k2.dt, mark=Mark.D, high=k2.high, low=k2.low,
                fx=k2.low, elements=[k1, k2, k3], power=power)
    return fx


def check_bi(bars: List[NewBar]):
    """输入一串无包含关系K线，查找其中的一笔"""
    fxs = []
    for i in range(1, len(bars)-1):
        fx = check_fx(bars[i-1], bars[i], bars[i+1])
        if isinstance(fx, FX):
            fxs.append(fx)

    if len(fxs) < 2:
        return None, bars

    fx_a = fxs[0]
    try:
        if fxs[0].mark == Mark.D:
            direction = Direction.Up
            fxs_b = [x for x in fxs if x.mark == Mark.G]
            fx_b = fxs_b[0]
            for fx in fxs_b:
                if fx.high > fx_b.high:
                    fx_b = fx
            high = fx_b.high
            low = fx_a.low
        elif fxs[0].mark == Mark.G:
            direction = Direction.Down
            fxs_b = [x for x in fxs if x.mark == Mark.D]
            fx_b = fxs_b[0]
            for fx in fxs_b[1:]:
                if fx.low < fx_b.low:
                    fx_b = fx
            high = fx_a.high
            low = fx_b.low
        else:
            raise ValueError
    except:
        return None, bars

    bars_a = [x for x in bars if x.dt <= fx_b.elements[2].dt]
    bars_b = [x for x in bars if x.dt >= fx_b.elements[0].dt]
    max_high_b = max([x.high for x in bars_b])
    min_low_b = min([x.low for x in bars_b])
    if (direction == Direction.Up and max_high_b > fx_b.high) \
            or (direction == Direction.Down and min_low_b < fx_b.low):
        return None, bars

    ab_include = (fx_a.high > fx_b.high and fx_a.low < fx_b.low) or (fx_a.high < fx_b.high and fx_a.low > fx_b.low)
    if len(bars_a) >= 7 and not ab_include:
        power_price = abs(fx_b.fx - fx_a.fx)
        bi = BI(symbol=fx_a.symbol, fx_a=fx_a, fx_b=fx_b, direction=direction,
                power=power_price, high=high, low=low, bars=bars_a)
        return bi, bars_b
    else:
        return None, bars


def get_sub_span(bis: List[BI], start_dt: [datetime, str], end_dt: [datetime, str]) -> List[BI]:
    """获取子区间（这是进行多级别联立分析的关键步骤）

    :param bis: 笔的列表
    :param start_dt: 子区间开始时间
    :param end_dt: 子区间结束时间
    :return: 子区间
    """
    start_dt = pd.to_datetime(start_dt)
    end_dt = pd.to_datetime(end_dt)
    sub = []
    for bi in bis:
        if bi.fx_b.dt > start_dt > bi.fx_a.dt:
            sub.append(bi)
        elif start_dt <= bi.fx_a.dt < bi.fx_b.dt <= end_dt:
            sub.append(bi)
        elif bi.fx_a.dt < end_dt < bi.fx_b.dt:
            sub.append(bi)
        else:
            continue
    return sub


class CZSC:
    def __init__(self, bars: List[RawBar], freq: str, max_count=1000):
        """

        :param bars: K线数据
        :param max_count: int
            最大保存的K线数量
        """
        self.max_count = max_count
        self.bars_raw = []  # 原始K线序列
        self.bars_ubi = []  # 未完成笔的无包含K线序列
        self.bi_list: List[BI] = []
        self.symbol = bars[0].symbol
        self.freq = freq

        for bar in bars:
            self.update(bar)

    def __update_bi(self):
        bars_ubi = self.bars_ubi

        # 查找笔
        if not self.bi_list:
            bi, bars_ubi_ = check_bi(bars_ubi)
            if isinstance(bi, BI):
                self.bi_list.append(bi)
            self.bars_ubi = bars_ubi_
            return

        last_bi = self.bi_list[-1]

        # 如果上一笔被破坏，将上一笔的bars与bars_ubi进行合并
        min_low_ubi = min([x.low for x in bars_ubi])
        max_high_ubi = max([x.high for x in bars_ubi])

        if last_bi.direction == Direction.Up and max_high_ubi > last_bi.high:
            if min_low_ubi < last_bi.low and len(self.bi_list) > 2:
                bars_ubi_a = self.bi_list[-2].bars \
                             + [x for x in self.bi_list[-1].bars if x.dt > self.bi_list[-2].bars[-1].dt] \
                             + [x for x in bars_ubi if x.dt > self.bi_list[-1].bars[-1].dt]
                self.bi_list.pop(-1)
                self.bi_list.pop(-1)
            else:
                bars_ubi_a = last_bi.bars + [x for x in bars_ubi if x.dt > last_bi.bars[-1].dt]
                self.bi_list.pop(-1)
        elif last_bi.direction == Direction.Down and min_low_ubi < last_bi.low:
            if max_high_ubi > last_bi.high and len(self.bi_list) > 2:
                bars_ubi_a = self.bi_list[-2].bars \
                             + [x for x in self.bi_list[-1].bars if x.dt > self.bi_list[-2].bars[-1].dt] \
                             + [x for x in bars_ubi if x.dt > self.bi_list[-1].bars[-1].dt]
                self.bi_list.pop(-1)
                self.bi_list.pop(-1)
            else:
                bars_ubi_a = last_bi.bars + [x for x in bars_ubi if x.dt > last_bi.bars[-1].dt]
                self.bi_list.pop(-1)
        else:
            bars_ubi_a = bars_ubi

        if len(bars_ubi_a) > 300:
            print("{} - {} 未完成笔延伸超长，延伸数量: {}".format(self.symbol, self.freq, len(bars_ubi_a)))
        bi, bars_ubi_ = check_bi(bars_ubi_a)
        self.bars_ubi = bars_ubi_
        if isinstance(bi, BI):
            self.bi_list.append(bi)

    def get_signals(self):
        s = OrderedDict({"symbol": self.symbol, "dt": self.bars_raw[-1].dt, "close": self.bars_raw[-1].close})
        s.update({
            "最近三根无包含K线形态": "other",
            "未完成笔的延伸长度": 0,

            "第N笔方向": "other",
            "第N笔结束标记的上边沿": 0,
            "第N笔结束标记的下边沿": 0,
            "第N笔结束标记的分型强弱": 0,

            "第N-1笔结束标记的上边沿": 0,
            "第N-1笔结束标记的下边沿": 0,
            "第N-1笔结束标记的分型强弱": 0,

            "第N笔的三笔形态": "other",
            "第N-1笔的三笔形态": "other",
            "第N-2笔的三笔形态": "other",
            "第N-3笔的三笔形态": "other",

            "第N笔的五笔形态": "other",
            "第N-1笔的五笔形态": "other",
            "第N-2笔的五笔形态": "other",
            "第N-3笔的五笔形态": "other",

            "第N笔的七笔形态": "other",
            "第N-1笔的七笔形态": "other",
            "第N-2笔的七笔形态": "other",
            "第N-3笔的七笔形态": "other",

            "第N笔的九笔形态": "other",
            "第N-1笔的九笔形态": "other",
            "第N-2笔的九笔形态": "other",
            "第N-3笔的九笔形态": "other",
        })
        s['未完成笔的延伸长度'] = len(self.bars_ubi)

        if s['未完成笔的延伸长度'] > 3:
            k1, k2, k3 = self.bars_ubi[-3:]
            tri = check_fx(k1, k2, k3)
            if isinstance(tri, FX):
                s['最近三根无包含K线形态'] = tri.power + tri.mark.value

        bis = self.bi_list
        if len(bis) > 3:
            direction = bis[-1].direction
            s['第N笔方向'] = direction.value
            s['第N笔结束标记的上边沿'] = bis[-1].fx_b.high
            s['第N笔结束标记的下边沿'] = bis[-1].fx_b.low
            s['第N笔结束标记的分型强弱'] = bis[-1].fx_b.power

            s['第N-1笔结束标记的上边沿'] = bis[-2].fx_b.high
            s['第N-1笔结束标记的下边沿'] = bis[-2].fx_b.low
            s['第N-1笔结束标记的分型强弱'] = bis[-2].fx_b.power

        if len(self.bi_list) > 8:
            bis = self.bi_list
            s['第N笔的三笔形态'] = check_three_fd(bis[-3:])
            s['第N-1笔的三笔形态'] = check_three_fd(bis[-4:-1])
            s['第N-2笔的三笔形态'] = check_three_fd(bis[-5:-2])
            s['第N-3笔的三笔形态'] = check_three_fd(bis[-6:-3])

            s['第N笔的五笔形态'] = check_five_fd(bis[-5:])
            s['第N-1笔的五笔形态'] = check_five_fd(bis[-6:-1])

        if len(self.bi_list) > 10:
            bis = self.bi_list
            s['第N-2笔的五笔形态'] = check_five_fd(bis[-7:-2])
            s['第N-3笔的五笔形态'] = check_five_fd(bis[-8:-3])

            s['第N笔的七笔形态'] = check_seven_fd(bis[-7:])
            s['第N-1笔的七笔形态'] = check_seven_fd(bis[-8:-1])

        if len(self.bi_list) > 12:
            bis = self.bi_list
            s['第N-2笔的七笔形态'] = check_seven_fd(bis[-9:-2])
            s['第N-3笔的七笔形态'] = check_seven_fd(bis[-10:-3])

            s['第N笔的九笔形态'] = check_nine_fd(bis[-9:])
            s['第N-1笔的九笔形态'] = check_nine_fd(bis[-10:-1])

        if len(self.bi_list) > 15:
            bis = self.bi_list
            s['第N-2笔的九笔形态'] = check_nine_fd(bis[-11:-2])
            s['第N-3笔的九笔形态'] = check_nine_fd(bis[-12:-3])

        return {"{}_{}".format(self.freq, k) if k not in ['symbol', 'dt', 'close'] else k: v for k, v in s.items()}

    def update(self, bar: RawBar):
        """更新分析结果

        :param bar: 单根K线对象
        """
        # 更新K线序列
        if not self.bars_raw or bar.dt != self.bars_raw[-1].dt:
            self.bars_raw.append(bar)
            last_bars = [bar]
        else:
            self.bars_raw[-1] = bar
            last_bars = self.bars_ubi[-1].elements
            last_bars[-1] = bar
            self.bars_ubi.pop(-1)

        # 去除包含关系
        bars_ubi = self.bars_ubi
        for bar in last_bars:
            if len(bars_ubi) < 2:
                bars_ubi.append(NewBar(symbol=bar.symbol, dt=bar.dt, open=bar.open, close=bar.close,
                                       high=bar.high, low=bar.low, vol=bar.vol, elements=[bar]))
            else:
                k1, k2 = bars_ubi[-2:]
                has_include, k3 = remove_include(k1, k2, bar)
                if has_include:
                    bars_ubi[-1] = k3
                else:
                    bars_ubi.append(k3)

        self.bars_ubi = bars_ubi

        # 更新 笔
        self.__update_bi()
        self.bars_raw = self.bars_raw[-self.max_count:]
        self.bi_list = self.bi_list[-(self.max_count // 7):]

    def to_echarts(self, width: str = "1400px", height: str = '580px'):
        kline = [x.__dict__ for x in self.bars_raw]
        if len(self.bi_list) > 0:
            bi = [{'dt': x.fx_a.dt, "bi": x.fx_a.fx} for x in self.bi_list] + \
                 [{'dt': self.bi_list[-1].fx_b.dt, "bi": self.bi_list[-1].fx_b.fx}]
        else:
            bi = None
        chart = kline_pro(kline, bi=bi, width=width, height=height, title="{}-{}".format(self.symbol, self.freq))
        return chart
