# coding: utf-8
import os
import webbrowser
import traceback
from typing import List, Callable
from collections import OrderedDict

from .enum import Mark, Direction
from .objects import BI, FX, RawBar, NewBar, Signal
from .utils.echarts_plot import kline_pro


def remove_include(k1: NewBar, k2: NewBar, k3: RawBar):
    """去除包含关系：输入三根k线，其中k1和k2为没有包含关系的K线，k3为原始K线"""
    if k1.high < k2.high:
        direction = Direction.Up
    elif k1.high > k2.high:
        direction = Direction.Down
    else:
        k4 = NewBar(symbol=k3.symbol, id=k3.id, freq=k3.freq, dt=k3.dt, open=k3.open,
                    close=k3.close, high=k3.high, low=k3.low, vol=k3.vol, elements=[k3])
        return False, k4

    # 判断 k2 和 k3 之间是否存在包含关系，有则处理
    if (k2.high <= k3.high and k2.low >= k3.low) or (k2.high >= k3.high and k2.low <= k3.low):
        if direction == Direction.Up:
            high = max(k2.high, k3.high)
            low = max(k2.low, k3.low)
            dt = k2.dt if k2.high > k3.high else k3.dt
        elif direction == Direction.Down:
            high = min(k2.high, k3.high)
            low = min(k2.low, k3.low)
            dt = k2.dt if k2.low < k3.low else k3.dt
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
        elements = [x for x in k2.elements[:100] if x.dt != k3.dt] + [k3]
        k4 = NewBar(symbol=k3.symbol, id=k2.id, freq=k2.freq, dt=dt, open=open_,
                    close=close, high=high, low=low, vol=vol, elements=elements)
        return True, k4
    else:
        k4 = NewBar(symbol=k3.symbol, id=k3.id, freq=k3.freq, dt=k3.dt, open=k3.open,
                    close=k3.close, high=k3.high, low=k3.low, vol=k3.vol, elements=[k3])
        return False, k4


def check_fx(k1: NewBar, k2: NewBar, k3: NewBar):
    """查找分型"""
    fx = None
    if k1.high < k2.high > k3.high and k1.low < k2.low > k3.low:
        power = "强" if k3.close < k1.low else "弱"
        fx = FX(symbol=k1.symbol, dt=k2.dt, mark=Mark.G, high=k2.high, low=k2.low,
                fx=k2.high, elements=[k1, k2, k3], power=power)

    if k1.low > k2.low < k3.low and k1.high > k2.high < k3.high:
        power = "强" if k3.close > k1.high else "弱"
        fx = FX(symbol=k1.symbol, dt=k2.dt, mark=Mark.D, high=k2.high, low=k2.low,
                fx=k2.low, elements=[k1, k2, k3], power=power)

    return fx


def check_fxs(bars: List[NewBar]) -> List[FX]:
    """输入一串无包含关系K线，查找其中所有分型"""
    fxs = []
    for i in range(1, len(bars)-1):
        fx: FX = check_fx(bars[i-1], bars[i], bars[i+1])
        if isinstance(fx, FX):
            # 这里可能隐含Bug，默认情况下，fxs本身是顶底交替的，但是对于一些特殊情况下不是这样，这是不对的。
            # 临时处理方案，强制要求fxs序列顶底交替
            if len(fxs) >= 2 and fx.mark == fxs[-1].mark:
                fxs.pop()
            fxs.append(fx)
    return fxs


def check_bi(bars: List[NewBar], bi_min_len: int = 7):
    """输入一串无包含关系K线，查找其中的一笔

    :param bars: 无包含关系K线列表
    :param bi_min_len: 一笔的最少无包含关系K线数量，7是老笔的要求
    :return:
    """
    fxs = check_fxs(bars)
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

    # 判断fx_a和fx_b价格区间是否存在包含关系
    ab_include = (fx_a.high > fx_b.high and fx_a.low < fx_b.low) \
                 or (fx_a.high < fx_b.high and fx_a.low > fx_b.low)

    if len(bars_a) >= bi_min_len and not ab_include:
        fxs_ = [x for x in fxs if fx_a.elements[0].dt <= x.dt <= fx_b.elements[2].dt]
        bi = BI(symbol=fx_a.symbol, fx_a=fx_a, fx_b=fx_b, fxs=fxs_, direction=direction, bars=bars_a)
        return bi, bars_b
    else:
        return None, bars


class CZSC:
    def __init__(self,
                 bars: List[RawBar],
                 max_bi_count: int = 50,
                 bi_min_len: int = 7,
                 get_signals: Callable = None,
                 signals_n: int = 0,
                 verbose=False):
        """

        :param bars: K线数据
        :param get_signals: 自定义的信号计算函数
        :param bi_min_len: 笔的最小长度，包括左右分型，默认值为 7，是缠论原文老笔定义的长度
        :param signals_n: 缓存n个历史时刻的信号，0 表示不缓存；缓存的数据，主要用于计算信号连续次数
        :param max_bi_count: 最大保存的笔数量
            默认值为 50，仅使用内置的信号和因子，不需要调整这个参数。
            如果进行新的信号计算需要用到更多的笔，可以适当调大这个参数。
        """
        self.verbose = verbose
        self.max_bi_count = max_bi_count
        self.bi_min_len = bi_min_len
        self.signals_n = signals_n
        self.bars_raw = []  # 原始K线序列
        self.bars_ubi = []  # 未完成笔的无包含K线序列
        self.bi_list: List[BI] = []
        self.symbol = bars[0].symbol
        self.freq = bars[0].freq
        self.get_signals = get_signals
        self.signals = None
        self.signals_list = []

        for bar in bars:
            self.update(bar)

    def __repr__(self):
        return "<CZSC~{}~{}>".format(self.symbol, self.freq.value)

    def __update_bi(self):
        bars_ubi = self.bars_ubi
        if len(bars_ubi) < 3:
            return

        # 查找笔
        if not self.bi_list:
            # 第一个笔的查找
            fxs = check_fxs(bars_ubi)
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
            bars_ubi_a = last_bi.bars + [x for x in bars_ubi if x.dt > last_bi.bars[-1].dt]
            self.bi_list.pop(-1)

        elif last_bi.direction == Direction.Down and min_low_ubi < last_bi.low:
            bars_ubi_a = last_bi.bars + [x for x in bars_ubi if x.dt > last_bi.bars[-1].dt]
            self.bi_list.pop(-1)

        else:
            bars_ubi_a = bars_ubi

        if self.verbose and len(bars_ubi_a) > 300:
            print(f"{self.symbol} - {self.freq} - {bars_ubi_a[-1].dt} 未完成笔延伸超长，延伸数量: {len(bars_ubi_a)}")

        bi, bars_ubi_ = check_bi(bars_ubi_a, self.bi_min_len)
        self.bars_ubi = bars_ubi_
        if isinstance(bi, BI):
            self.bi_list.append(bi)

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
                bars_ubi.append(NewBar(symbol=bar.symbol, id=bar.id, freq=bar.freq, dt=bar.dt,
                                       open=bar.open, close=bar.close,
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

        if self.get_signals:
            self.signals = self.get_signals(c=self)
            if self.signals_n > 0:
                self.signals_list.append(self.signals)
                self.signals_list = self.signals_list[-self.signals_n:]
                self.signals.update(self.get_signal_counter())
        else:
            self.signals = OrderedDict()

    def to_echarts(self, width: str = "1400px", height: str = '580px'):
        kline = [x.__dict__ for x in self.bars_raw]
        if len(self.bi_list) > 0:
            bi = [{'dt': x.fx_a.dt, "bi": x.fx_a.fx} for x in self.bi_list] + \
                 [{'dt': self.bi_list[-1].fx_b.dt, "bi": self.bi_list[-1].fx_b.fx}]
            fx = []
            for bi_ in self.bi_list:
                fx.extend([{'dt': x.dt, "fx": x.fx} for x in bi_.fxs[1:]])
        else:
            bi = None
            fx = None
        chart = kline_pro(kline, bi=bi, fx=fx, width=width, height=height,
                          title="{}-{}".format(self.symbol, self.freq.value))
        return chart

    def open_in_browser(self, width: str = "1400px", height: str = '580px'):
        """直接在浏览器中打开分析结果

        :param width: 图表宽度
        :param height: 图表高度
        :return:
        """
        home_path = os.path.expanduser("~")
        file_html = os.path.join(home_path, "temp_czsc.html")
        chart = self.to_echarts(width, height)
        chart.render(file_html)
        webbrowser.open(file_html)

    def get_signal_counter(self) -> OrderedDict:
        """信号连续出现次数记录"""
        if not self.signals or not self.signals_list:
            return OrderedDict()

        signals_list = self.signals_list
        signals = [Signal(f"{k}_{v}") for k, v in self.signals.items()
                   if len(k.split("_")) == 3 and "连续次数" not in k]

        s = OrderedDict()
        for signal in signals:
            k1 = signal.k1
            k2 = f"{signal.k2}#{signal.k3}"
            k3 = "连续次数"
            seq = [signal.is_match(x) for x in signals_list]
            assert seq[-1], "最后一个信号匹配结果必须为 True"

            n = 0
            for x in seq:
                if x:
                    n += 1
                else:
                    n = 0
            assert n >= 1, "连续次数小于1，不合逻辑"

            signal_c = Signal(k1=k1, k2=k2, k3=k3, v1=f"{n}次")
            s[signal_c.key] = signal_c.value

        return s

    @property
    def last_bi_extend(self):
        """判断最后一笔是否在延伸中，True 表示延伸中"""
        if self.bi_list[-1].direction == Direction.Up \
                and max([x.high for x in self.bars_ubi]) > self.bi_list[-1].high:
            return True

        if self.bi_list[-1].direction == Direction.Down \
                and min([x.low for x in self.bars_ubi]) < self.bi_list[-1].low:
            return True

        return False

    @property
    def finished_bis(self) -> List[BI]:
        """返回当下基本确认完成的笔列表"""
        if not self.bi_list:
            return []
        else:
            if self.last_bi_extend:
                return self.bi_list[:-1]
        return self.bi_list


