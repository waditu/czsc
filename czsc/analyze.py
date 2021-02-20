# coding: utf-8

from typing import List
from collections import OrderedDict
from datetime import datetime
import pandas as pd
import traceback
from .objects import Mark, Direction, BI, FX, RawBar, NewBar
from .utils.echarts_plot import kline_pro
from .signals import check_five_fd, check_seven_fd, check_nine_fd
from .utils.ta import RSQ

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
        # 这里有一个隐藏Bug，len(k2.elements) 在一些及其特殊的场景下会有超大的数量，具体问题还没找到；
        # 临时解决方案是直接限定len(k2.elements)<=100
        elements = [x for x in k2.elements[:100]] + [k3]
        k4 = NewBar(symbol=k3.symbol, dt=dt, open=open_,
                    close=close, high=high, low=low, vol=vol, elements=elements)
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
            fxs_b = [x for x in fxs if x.mark == Mark.G and x.dt > fx_a.dt and x.fx > fx_a.fx]
            if not fxs_b:
                return None, bars
            fx_b = fxs_b[0]
            for fx in fxs_b:
                if fx.high >= fx_b.high:
                    fx_b = fx
        elif fxs[0].mark == Mark.G:
            direction = Direction.Down
            fxs_b = [x for x in fxs if x.mark == Mark.D and x.dt > fx_a.dt and x.fx < fx_a.fx]
            if not fxs_b:
                return None, bars
            fx_b = fxs_b[0]
            for fx in fxs_b[1:]:
                if fx.low <= fx_b.low:
                    fx_b = fx
        else:
            raise ValueError
    except:
        traceback.print_exc()
        return None, bars

    bars_a = [x for x in bars if fx_a.elements[0].dt <= x.dt <= fx_b.elements[2].dt]
    bars_b = [x for x in bars if x.dt >= fx_b.elements[0].dt]
    max_high_b = max([x.high for x in bars_b])
    min_low_b = min([x.low for x in bars_b])
    if (direction == Direction.Up and max_high_b > fx_b.high) \
            or (direction == Direction.Down and min_low_b < fx_b.low):
        return None, bars

    ab_include = (fx_a.high > fx_b.high and fx_a.low < fx_b.low) or (fx_a.high < fx_b.high and fx_a.low > fx_b.low)
    if len(bars_a) >= 7 and not ab_include:
        power_price = abs(fx_b.fx - fx_a.fx)
        change = round((fx_b.fx - fx_a.fx) / fx_a.fx, 4)
        bi = BI(symbol=fx_a.symbol, fx_a=fx_a, fx_b=fx_b, direction=direction,
                power=power_price, high=max(fx_a.high, fx_b.high),
                low=min(fx_a.low, fx_b.low), bars=bars_a, length=len(bars_a),
                rsq=RSQ([x.close for x in bars_a[1:-1]]), change=change)
        return bi, bars_b
    else:
        return None, bars


def get_sub_span(bis: List[BI], start_dt: [datetime, str], end_dt: [datetime, str], direction: Direction) -> List[BI]:
    """获取子区间（这是进行多级别联立分析的关键步骤）

    :param bis: 笔的列表
    :param start_dt: 子区间开始时间
    :param end_dt: 子区间结束时间
    :param direction: 方向
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

    if len(sub) > 0 and sub[0].direction != direction:
        sub = sub[1:]
    if len(sub) > 0 and sub[-1].direction != direction:
        sub = sub[:-1]
    return sub


def get_sub_bis(bis: List[BI], bi: BI) -> List[BI]:
    """获取大级别笔对象对应的小级别笔走势

    :param bis: 小级别笔列表
    :param bi: 大级别笔对象
    :return:
    """
    sub_bis = get_sub_span(bis, start_dt=bi.fx_a.dt, end_dt=bi.fx_b.dt, direction=bi.direction)
    if not sub_bis:
        return []
    return sub_bis


class CZSC:
    def __init__(self, bars: List[RawBar], freq: str, max_bi_count=20):
        """

        :param bars: K线数据
        :param freq: K线级别
        :param max_bi_count: 最大保存的笔数量
            默认值为 20，仅使用内置的信号和因子，不需要调整这个参数。
            如果进行新的信号计算需要用到更多的笔，可以适当调大这个参数。
        """
        self.max_bi_count = max_bi_count
        self.bars_raw = []  # 原始K线序列
        self.bars_ubi = []  # 未完成笔的无包含K线序列
        self.bi_list: List[BI] = []
        self.symbol = bars[0].symbol
        self.freq = freq

        for bar in bars:
            self.update(bar)
        self.signals = self.get_signals()

    def __update_bi(self):
        bars_ubi = self.bars_ubi
        if len(bars_ubi) < 3:
            return

        # 查找笔
        if not self.bi_list:
            # 第一个笔的查找
            fxs = []
            for i in range(1, len(bars_ubi)-1):
                fx = check_fx(bars_ubi[i-1], bars_ubi[i], bars_ubi[i+1])
                if isinstance(fx, FX):
                    fxs.append(fx)
            if not fxs:
                return

            fx_a = fxs[0]
            fxs_a = [x for x in fxs if x.mark == fx_a.mark]
            for fx in fxs_a:
                if (fx_a.mark == Mark.D and fx.low <= fx_a.low) \
                        or (fx_a.mark == Mark.G and fx.high >= fx_a.high):
                    fx_a = fx
            bars_ubi = [x for x in bars_ubi if x.dt >= fx_a.elements[0].dt]

            bi, bars_ubi_ = check_bi(bars_ubi)
            if isinstance(bi, BI):
                self.bi_list.append(bi)
            self.bars_ubi = bars_ubi_
            return

        last_bi = self.bi_list[-1]

        # 如果上一笔被破坏，将上一笔的bars与bars_ubi进行合并
        min_low_ubi = min([x.low for x in bars_ubi[2:]])
        max_high_ubi = max([x.high for x in bars_ubi[2:]])

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
        # 倒1，倒数第1笔的缩写，表示第N笔
        # 倒2，倒数第2笔的缩写，表示第N-1笔
        # 倒3，倒数第3笔的缩写，表示第N-2笔
        # 倒4，倒数第4笔的缩写，表示第N-3笔
        s.update({
            "倒1的长度": 0,
            "倒1的涨跌幅": 0,
            "倒1的拟合优度": 0,
            # "倒1的有效分型数量": "其他",

            "倒2的长度": 0,
            "倒2的涨跌幅": 0,
            "倒2的拟合优度": 0,

            "倒3的长度": 0,
            "倒3的涨跌幅": 0,
            "倒3的拟合优度": 0,

            "倒4的长度": 0,
            "倒4的涨跌幅": 0,
            "倒4的拟合优度": 0,

            "倒5的长度": 0,
            "倒5的涨跌幅": 0,
            "倒5的拟合优度": 0,

            "倒1的五笔形态": "其他",
            "倒2的五笔形态": "其他",
            "倒3的五笔形态": "其他",
            "倒4的五笔形态": "其他",
            "倒5的五笔形态": "其他",

            "倒1的七笔形态": "其他",
            "倒2的七笔形态": "其他",
            "倒3的七笔形态": "其他",
            "倒4的七笔形态": "其他",
            "倒5的七笔形态": "其他",

            "倒1的九笔形态": "其他",
            "倒2的九笔形态": "其他",
            "倒3的九笔形态": "其他",
            "倒4的九笔形态": "其他",
            "倒5的九笔形态": "其他",
        })

        bis = self.bi_list
        if len(bis) > 7:
            s['倒1的长度'] = bis[-1].length
            s['倒1的涨跌幅'] = bis[-1].change
            s['倒1的拟合优度'] = bis[-1].rsq

            s['倒2的长度'] = bis[-2].length
            s['倒2的涨跌幅'] = bis[-2].change
            s['倒2的拟合优度'] = bis[-2].rsq

            s['倒3的长度'] = bis[-3].length
            s['倒3的涨跌幅'] = bis[-3].change
            s['倒3的拟合优度'] = bis[-3].rsq

            s['倒4的长度'] = bis[-4].length
            s['倒4的涨跌幅'] = bis[-4].change
            s['倒4的拟合优度'] = bis[-4].rsq

            s['倒5的长度'] = bis[-5].length
            s['倒5的涨跌幅'] = bis[-5].change
            s['倒5的拟合优度'] = bis[-5].rsq

        if len(self.bi_list) > 9:
            bis = self.bi_list
            s['倒1的五笔形态'] = check_five_fd(bis[-5:])
            s['倒2的五笔形态'] = check_five_fd(bis[-6:-1])

        if len(self.bi_list) > 11:
            bis = self.bi_list
            s['倒3的五笔形态'] = check_five_fd(bis[-7:-2])
            s['倒4的五笔形态'] = check_five_fd(bis[-8:-3])
            s['倒5的五笔形态'] = check_five_fd(bis[-9:-4])

            s['倒1的七笔形态'] = check_seven_fd(bis[-7:])
            s['倒2的七笔形态'] = check_seven_fd(bis[-8:-1])

        if len(self.bi_list) > 13:
            bis = self.bi_list
            s['倒3的七笔形态'] = check_seven_fd(bis[-9:-2])
            s['倒4的七笔形态'] = check_seven_fd(bis[-10:-3])
            s['倒5的七笔形态'] = check_seven_fd(bis[-11:-4])

            s['倒1的九笔形态'] = check_nine_fd(bis[-9:])
            s['倒2的九笔形态'] = check_nine_fd(bis[-10:-1])

        if len(self.bi_list) > 15:
            bis = self.bi_list
            s['倒3的九笔形态'] = check_nine_fd(bis[-11:-2])
            s['倒4的九笔形态'] = check_nine_fd(bis[-12:-3])
            s['倒5的九笔形态'] = check_nine_fd(bis[-13:-4])

        # return {"{}_{}".format(self.freq, k) if k not in ['symbol', 'dt', 'close'] else k: v for k, v in s.items()}
        return s

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

        # 更新笔
        self.__update_bi()
        self.bi_list = self.bi_list[-self.max_bi_count:]
        if self.bi_list:
            sdt = self.bi_list[0].fx_a.elements[0].dt
            s_index = 0
            for i, bar in enumerate(self.bars_raw):
                if bar.dt >= sdt:
                    s_index = i
                    break
            self.bars_raw = self.bars_raw[s_index:]
        self.signals = self.get_signals()

    def to_echarts(self, width: str = "1400px", height: str = '580px'):
        kline = [x.__dict__ for x in self.bars_raw]
        if len(self.bi_list) > 0:
            bi = [{'dt': x.fx_a.dt, "bi": x.fx_a.fx} for x in self.bi_list] + \
                 [{'dt': self.bi_list[-1].fx_b.dt, "bi": self.bi_list[-1].fx_b.fx}]
        else:
            bi = None
        chart = kline_pro(kline, bi=bi, width=width, height=height, title="{}-{}".format(self.symbol, self.freq))
        return chart
