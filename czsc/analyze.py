# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/3/10 11:21
describe: 缠论分型、笔的识别
"""
import os
import webbrowser
import numpy as np
from loguru import logger
from typing import List, Callable
from collections import OrderedDict
from czsc.enum import Mark, Direction
from czsc.objects import BI, FX, RawBar, NewBar
from czsc.utils.echarts_plot import kline_pro
from czsc import envs

logger.disable('czsc.analyze')


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
        fx = FX(symbol=k1.symbol, dt=k2.dt, mark=Mark.G, high=k2.high,
                low=k2.low, fx=k2.high, elements=[k1, k2, k3])

    if k1.low > k2.low < k3.low and k1.high > k2.high < k3.high:
        fx = FX(symbol=k1.symbol, dt=k2.dt, mark=Mark.D, high=k2.high,
                low=k2.low, fx=k2.low, elements=[k1, k2, k3])

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
                if envs.get_verbose():
                    logger.info(f"\n\ncheck_fxs: 输入数据错误{'+' * 100}")
                    logger.info(f"当前：{fx.mark}, 上个：{fxs[-1].mark}")
                    for bar in fx.raw_bars:
                        logger.info(f"{bar}\n")

                    logger.info(f'last fx raw bars: \n')
                    for bar in fxs[-1].raw_bars:
                        logger.info(f"{bar}\n")
            else:
                fxs.append(fx)
    return fxs


def check_bi(bars: List[NewBar], benchmark: float = None):
    """输入一串无包含关系K线，查找其中的一笔

    :param bars: 无包含关系K线列表
    :param benchmark: 当下笔能量的比较基准
    :return:
    """
    min_bi_len = envs.get_min_bi_len()
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
            for fx in fxs_b[1:]:
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
        logger.exception("笔识别错误")
        return None, bars

    bars_a = [x for x in bars if fx_a.elements[0].dt <= x.dt <= fx_b.elements[2].dt]
    bars_b = [x for x in bars if x.dt >= fx_b.elements[0].dt]

    # 判断fx_a和fx_b价格区间是否存在包含关系
    ab_include = (fx_a.high > fx_b.high and fx_a.low < fx_b.low) \
                 or (fx_a.high < fx_b.high and fx_a.low > fx_b.low)

    # 判断当前笔的涨跌幅是否超过benchmark的一定比例
    if benchmark and abs(fx_a.fx - fx_b.fx) > benchmark * envs.get_bi_change_th():
        power_enough = True
    else:
        power_enough = False

    # 成笔的条件：1）顶底分型之间没有包含关系；2）笔长度大于等于min_bi_len 或 当前笔的涨跌幅已经够大
    if (not ab_include) and (len(bars_a) >= min_bi_len or power_enough):
        fxs_ = [x for x in fxs if fx_a.elements[0].dt <= x.dt <= fx_b.elements[2].dt]
        bi = BI(symbol=fx_a.symbol, fx_a=fx_a, fx_b=fx_b, fxs=fxs_, direction=direction, bars=bars_a)

        low_ubi = min([x.low for x in bars_b])
        high_ubi = max([x.high for x in bars_b])
        if (bi.direction == Direction.Up and high_ubi > bi.high) \
                or (bi.direction == Direction.Down and low_ubi < bi.low):
            return None, bars
        else:
            return bi, bars_b
    else:
        return None, bars


class CZSC:
    def __init__(self,
                 bars: List[RawBar],
                 get_signals: Callable = None,
                 max_bi_num=envs.get_max_bi_num(),
                 ):
        """

        :param bars: K线数据
        :param max_bi_num: 最大允许保留的笔数量
        :param get_signals: 自定义的信号计算函数
        """
        self.verbose = envs.get_verbose()
        self.max_bi_num = max_bi_num
        self.bars_raw: List[RawBar] = []  # 原始K线序列
        self.bars_ubi: List[NewBar] = []  # 未完成笔的无包含K线序列
        self.bi_list: List[BI] = []
        self.symbol = bars[0].symbol
        self.freq = bars[0].freq
        self.get_signals = get_signals
        self.signals = None

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
        if (last_bi.direction == Direction.Up and bars_ubi[-1].high > last_bi.high) \
                or (last_bi.direction == Direction.Down and bars_ubi[-1].low < last_bi.low):
            bars_ubi_a = last_bi.bars[:-1] + [x for x in bars_ubi if x.dt >= last_bi.bars[-1].dt]
            self.bi_list.pop(-1)
        else:
            bars_ubi_a = bars_ubi

        if self.verbose and len(bars_ubi_a) > 100:
            logger.info(f"czsc_update_bi: {self.symbol} - {self.freq} - {bars_ubi_a[-1].dt} 未完成笔延伸数量: {len(bars_ubi_a)}")

        if envs.get_bi_change_th() > 0.5 and len(self.bi_list) >= 5:
            benchmark = min(last_bi.power_price, np.mean([x.power_price for x in self.bi_list[-5:]]))
        else:
            benchmark = None

        bi, bars_ubi_ = check_bi(bars_ubi_a, benchmark)
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
            # 当前 bar 是上一根 bar 的时间延伸
            self.bars_raw[-1] = bar
            if len(self.bars_ubi) >= 3:
                edt = self.bars_ubi[1].dt
                self.bars_ubi = [x for x in self.bars_ubi if x.dt <= edt]
                last_bars = [x for x in self.bars_raw[-50:] if x.dt > edt]
            else:
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
        self.bi_list = self.bi_list[-self.max_bi_num:]
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
        else:
            self.signals = OrderedDict()

    def to_echarts(self, width: str = "1400px", height: str = '580px', bs=None):
        """绘制K线分析图

        :param width: 宽
        :param height: 高
        :param bs: 交易标记，默认为空
        :return:
        """
        kline = [x.__dict__ for x in self.bars_raw]
        if len(self.bi_list) > 0:
            bi = [{'dt': x.fx_a.dt, "bi": x.fx_a.fx} for x in self.bi_list] + \
                 [{'dt': self.bi_list[-1].fx_b.dt, "bi": self.bi_list[-1].fx_b.fx}]
            fx = [{'dt': x.dt, "fx": x.fx} for x in self.fx_list]
        else:
            bi = None
            fx = None
        chart = kline_pro(kline, bi=bi, fx=fx, width=width, height=height, bs=bs,
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

    @property
    def ubi_fxs(self) -> List[FX]:
        """返回当下基本确认完成的笔列表"""
        if not self.bars_ubi:
            return []
        else:
            return check_fxs(self.bars_ubi)

    @property
    def fx_list(self) -> List[FX]:
        """返回当下基本确认完成的笔列表"""
        fxs = []
        for bi_ in self.bi_list:
            fxs.extend(bi_.fxs[1:])
        ubi = self.ubi_fxs
        for x in ubi:
            if x.dt > fxs[-1].dt:
                fxs.append(x)
        return fxs
