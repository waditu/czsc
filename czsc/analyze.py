# coding: utf-8
import os
import webbrowser
from typing import List, Callable
from datetime import datetime
import pandas as pd
import traceback
from collections import OrderedDict
from pyecharts.charts import Tab
from pyecharts.components import Table
from pyecharts.options import ComponentTitleOpts

from .utils.kline_generator import KlineGenerator
from .enum import Mark, Direction, Operate
from .objects import BI, FakeBI, FX, RawBar, NewBar, Event
from .utils.echarts_plot import kline_pro
from .utils.ta import RSQ


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


def check_bi(bars: List[NewBar]):
    """输入一串无包含关系K线，查找其中的一笔"""
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
    ab_include = (fx_a.high > fx_b.high and fx_a.low < fx_b.low) or (fx_a.high < fx_b.high and fx_a.low > fx_b.low)

    if len(bars_a) >= 7 and not ab_include:
        # 计算笔的相关属性
        power_price = round(abs(fx_b.fx - fx_a.fx), 2)
        change = round((fx_b.fx - fx_a.fx) / fx_a.fx, 4)
        fxs_ = [x for x in fxs if fx_a.elements[0].dt <= x.dt <= fx_b.elements[2].dt]
        fake_bis = create_fake_bis(fxs_)

        bi = BI(symbol=fx_a.symbol, fx_a=fx_a, fx_b=fx_b, fxs=fxs_, fake_bis=fake_bis,
                direction=direction, power=power_price, high=max(fx_a.high, fx_b.high),
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
    def __init__(self, bars: List[RawBar], max_bi_count=50, get_signals: Callable = None):
        """

        :param bars: K线数据
        :param get_signals: 自定义的信号计算函数
        :param max_bi_count: 最大保存的笔数量
            默认值为 50，仅使用内置的信号和因子，不需要调整这个参数。
            如果进行新的信号计算需要用到更多的笔，可以适当调大这个参数。
        """
        self.max_bi_count = max_bi_count
        self.bars_raw = []  # 原始K线序列
        self.bars_ubi = []  # 未完成笔的无包含K线序列
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
            print(f"{self.symbol} - {self.freq} - {bars_ubi_a[-1].dt} 未完成笔延伸超长，延伸数量: {len(bars_ubi_a)}")

        bi, bars_ubi_ = check_bi(bars_ubi_a)
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
        else:
            self.signals = OrderedDict()

    def to_echarts(self, width: str = "1400px", height: str = '580px'):
        kline = [x.__dict__ for x in self.bars_raw]
        if len(self.bi_list) > 0:
            bi = [{'dt': x.fx_a.dt, "bi": x.fx_a.fx} for x in self.bi_list] + \
                 [{'dt': self.bi_list[-1].fx_b.dt, "bi": self.bi_list[-1].fx_b.fx}]
        else:
            bi = None
        chart = kline_pro(kline, bi=bi, width=width, height=height, title="{}-{}".format(self.symbol, self.freq.value))
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
    def finished_bis(self) -> List[BI]:
        """返回当下基本确认完成的笔列表"""
        if not self.bi_list:
            return []

        min_ubi = min([x.low for x in self.bars_ubi])
        max_ubi = max([x.high for x in self.bars_ubi])
        if (self.bi_list[-1].direction == Direction.Down and min_ubi >= self.bi_list[-1].low) \
                or (self.bi_list[-1].direction == Direction.Up and max_ubi <= self.bi_list[-1].high):
            bis = self.bi_list
        else:
            bis = self.bi_list[:-1]
        return bis


class CzscTrader:
    """缠中说禅技术分析理论之多级别联立交易决策类"""

    def __init__(self, kg: KlineGenerator, get_signals: Callable, events: List[Event] = None):
        """

        :param kg: K线合成器
        :param get_signals: 自定义的单级别信号计算函数
        :param events: 自定义的交易事件组合，推荐平仓事件放到前面
        """
        self.name = "CzscTrader"
        self.kg = kg
        self.freqs = kg.freqs
        self.events = events
        self.op = dict()

        klines = self.kg.get_klines({k: 3000 for k in self.freqs})
        self.kas = {k: CZSC(klines[k], max_bi_count=50, get_signals=get_signals) for k in klines.keys()}
        self.symbol = self.kas["1分钟"].symbol
        self.end_dt = self.kas["1分钟"].bars_raw[-1].dt
        self.latest_price = self.kas["1分钟"].bars_raw[-1].close
        self.s = self._cal_signals()

        # cache 中会缓存一些实盘交易中需要的信息
        self.cache = OrderedDict({
            "last_op": Operate.HO.value,            # 最近一个操作类型
            "last_op_desc": "",                     # 最近一个操作变化的描述
            "long_open_price": -1,                  # 多仓开仓价格
            "long_max_high": -1,                    # 多仓开仓后的最高价
            "long_open_k1_id": -1,                  # 多仓开仓时的1分钟K线ID
            "short_open_price": -1,                 # 空仓开仓价格
            "short_min_low": -1,                    # 空仓开仓后的最低价
            "short_open_k1_id": -1,                 # 空仓开仓后的1分钟K线ID
        })

    def __repr__(self):
        return "<{} for {}>".format(self.name, self.symbol)

    def take_snapshot(self, file_html=None, width="1400px", height="580px"):
        """获取快照

        :param file_html: str
            交易快照保存的 html 文件名
        :param width: str
            图表宽度
        :param height: str
            图表高度
        :return:
        """
        tab = Tab(page_title="{}@{}".format(self.symbol, self.end_dt.strftime("%Y-%m-%d %H:%M")))
        for freq in self.freqs:
            chart = self.kas[freq].to_echarts(width, height)
            tab.add(chart, freq)

        for freq in self.freqs:
            t1 = Table()
            t1.add(["名称", "数据"], [[k, v] for k, v in self.s.items() if k.startswith("{}_".format(freq))])
            t1.set_global_opts(title_opts=ComponentTitleOpts(title="缠中说禅信号表", subtitle=""))
            tab.add(t1, "{}信号表".format(freq))

        t2 = Table()
        ths_ = [["同花顺F10",  "http://basic.10jqka.com.cn/{}".format(self.symbol[:6])]]
        t2.add(["名称", "数据"], [[k, v] for k, v in self.s.items() if "_" not in k] + ths_)
        t2.set_global_opts(title_opts=ComponentTitleOpts(title="缠中说禅因子表", subtitle=""))
        tab.add(t2, "因子表")

        if file_html:
            tab.render(file_html)
        else:
            return tab

    def open_in_browser(self, width="1400px", height="580px"):
        """直接在浏览器中打开分析结果"""
        home_path = os.path.expanduser("~")
        file_html = os.path.join(home_path, "temp_czsc_factors.html")
        self.take_snapshot(file_html, width, height)
        webbrowser.open(file_html)

    def _cal_signals(self):
        """计算信号"""
        s = OrderedDict()
        for freq, ks in self.kas.items():
            s.update(ks.signals)

        s.update(self.kas['1分钟'].bars_raw[-1].__dict__)
        return s

    def check_operate(self, bar: RawBar, stoploss: float = 0.1, timeout: int = 1000) -> dict:
        """更新信号，计算下一个操作动作

        :param timeout: 超时退出参数，数值表示持仓1分钟K线数量
        :param stoploss: 止损退出参数，0.1 表示10个点止损
            多头止损：当前价 < 买入后的最高价 * （1 - stoploss）
            空头止损：当前价 > 买入后的最低价 * （1 + stoploss）
        :param bar: 单根K线对象
        :return: 操作提示
        """
        self.kg.update(bar)
        klines_one = self.kg.get_klines({freq: 1 for freq in self.freqs})

        for freq, klines_ in klines_one.items():
            self.kas[freq].update(klines_[-1])

        self.symbol = self.kas["1分钟"].symbol
        self.end_dt = self.kas["1分钟"].bars_raw[-1].dt
        self.latest_price = self.kas["1分钟"].bars_raw[-1].close
        self.s = self._cal_signals()

        # 遍历 events，获得 operate
        op = {"operate": self.cache['last_op'], 'symbol': self.symbol, 'dt': self.end_dt,
              'price': self.latest_price, "desc": '', 'bid': self.kg.m1[-1].id}
        if self.events:
            for event in self.events:
                m, f = event.is_match(self.s)
                if m:
                    op['operate'] = event.operate.value
                    op['desc'] = f"{event.name}@{f}"
                    break

        # 结合 last_op ，修改 op
        last_op = self.cache['last_op']

        if last_op == Operate.LO.value:
            op['operate'] = Operate.HL.value

        elif last_op == Operate.SO.value:
            op['operate'] = Operate.HS.value

        elif last_op == Operate.LE.value:
            op['operate'] = Operate.HO.value

        elif last_op == Operate.SE.value:
            op['operate'] = Operate.HO.value

        elif last_op == Operate.HL.value:
            assert self.cache['long_open_price'] > 0
            assert self.cache['long_max_high'] > 0
            assert self.cache['long_open_k1_id'] > 0

            if op['operate'] == Operate.LO.value:
                op['operate'] = Operate.HL.value
                self.cache['long_open_price'] = min(self.cache['long_open_price'], self.latest_price)
                self.cache['long_open_k1_id'] = self.kg.m1[-1].id
                self.cache['last_op_desc'] = op['desc']
            else:
                # 判断是否达到多头异常退出条件
                if self.latest_price < self.cache.get('long_max_high', 0) * (1 - stoploss):
                    op['operate'] = Operate.LE.value
                    op['desc'] = f"long_stoploss_{stoploss}"

                if self.kg.m1[-1].id - self.cache.get('long_open_k1_id', 99999999999) > timeout:
                    op['operate'] = Operate.LE.value
                    op['desc'] = f"long_timeout_{timeout}"

        elif last_op == Operate.HS.value:
            assert self.cache['short_open_price'] > 0
            assert self.cache['short_min_low'] > 0
            assert self.cache['short_open_k1_id'] > 0

            if op['operate'] == Operate.SO.value:
                op['operate'] = Operate.HS.value
                self.cache['short_open_price'] = max(self.cache['short_open_price'], self.latest_price)
                self.cache['short_open_k1_id'] = self.kg.m1[-1].id
                self.cache['last_op_desc'] = op['desc']
            else:
                # 判断是否达到空头异常退出条件
                self.cache['short_min_low'] = min(self.latest_price, self.cache['short_min_low'])
                if self.latest_price > self.cache.get('short_min_low', 10000000000) * (1 + stoploss):
                    op['operate'] = Operate.SE.value
                    op['desc'] = f"short_stoploss_{stoploss}"

                if self.kg.m1[-1].id - self.cache.get('short_open_k1_id', 99999999999) > timeout:
                    op['operate'] = Operate.SE.value
                    op['desc'] = f"short_timeout_{timeout}"
        else:
            assert last_op == Operate.HO.value
            if op['operate'] in [Operate.LE.value, Operate.SE.value]:
                op['operate'] = Operate.HO.value

        # update cache
        if op['operate'] == Operate.LE.value:
            self.cache.update({
                "long_open_price": -1,
                "long_open_k1_id": -1,
                "long_max_high": -1,
            })
            self.cache['last_op_desc'] = op['desc']

        elif op['operate'] == Operate.LO.value:
            self.cache.update({
                "long_open_price": self.latest_price,
                "long_open_k1_id": self.kg.m1[-1].id,
            })
            self.cache['long_max_high'] = max(self.latest_price, self.cache['long_max_high'])
            self.cache['last_op_desc'] = op['desc']

        elif op['operate'] == Operate.HL.value:
            assert self.cache['long_open_price'] > 0
            assert self.cache['long_open_k1_id'] > 0
            self.cache['long_max_high'] = max(self.latest_price, self.cache['long_max_high'])
            assert self.cache['long_max_high'] > 0

        elif op['operate'] == Operate.SE.value:
            self.cache.update({
                "short_open_price": -1,
                "short_open_k1_id": -1,
                "short_min_low": -1,
            })
            self.cache['last_op_desc'] = op['desc']

        elif op['operate'] == Operate.SO.value:
            self.cache.update({
                "short_open_price": self.latest_price,
                "short_open_k1_id": self.kg.m1[-1].id,
            })
            self.cache['short_min_low'] = min(self.latest_price, self.cache['short_min_low'])
            self.cache['last_op_desc'] = op['desc']

        elif op['operate'] == Operate.HS.value:
            assert self.cache['short_open_price'] > 0
            assert self.cache['short_open_k1_id'] > 0
            self.cache['short_min_low'] = min(self.latest_price, self.cache['short_min_low'])
            assert self.cache['short_min_low'] > 0

        else:
            assert op['operate'] == Operate.HO.value
            assert self.cache['long_open_price'] == -1
            assert self.cache['long_open_k1_id'] == -1
            assert self.cache['long_max_high'] == -1
            assert self.cache['short_open_price'] == -1
            assert self.cache['short_open_k1_id'] == -1
            assert self.cache['short_min_low'] == -1

        self.cache['last_op'] = op['operate']
        self.op = op
        return op
