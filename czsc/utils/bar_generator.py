# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/11/14 12:39
describe: 从任意周期K线开始合成更高周期K线的工具类
"""
import pandas as pd
from datetime import datetime, timedelta, date
from typing import List, Union, AnyStr, Optional
from czsc.objects import RawBar, Freq
from pathlib import Path
from loguru import logger


mss = pd.read_feather(Path(__file__).parent / "minites_split.feather")
freq_market_times, freq_edt_map = {}, {}
for _m, dfg in mss.groupby('market'):
    for _f in [x for x in mss.columns if x.endswith("分钟")]:
        freq_market_times[f"{_f}_{_m}"] = list(dfg[_f].unique())
        freq_edt_map[f"{_f}_{_m}"] = {k: v for k, v in dfg[["time", _f]].values}


def is_trading_time(dt: datetime = datetime.now(), market="A股"):
    """判断指定时间是否是交易时间"""
    hm = dt.strftime("%H:%M")
    times = freq_market_times[f"1分钟_{market}"]
    return True if hm in times else False


def get_intraday_times(freq='1分钟', market="A股"):
    """获取指定市场的交易时间段

    :param market: 市场名称，可选值：A股、期货、默认
    :return: 交易时间段列表
    """
    assert market in ['A股', '期货', '默认'], "market 参数必须为 A股 或 期货 或 默认"
    assert freq.endswith("分钟"), "freq 参数必须为分钟级别的K线周期"
    return freq_market_times[f"{freq}_{market}"]


def check_freq_and_market(time_seq: List[AnyStr], freq: Optional[AnyStr] = None):
    """检查时间序列是否为同一周期，是否为同一市场

    函数计算逻辑：

    1. 如果`freq`在特定列表中，函数直接返回`freq`和"默认"作为市场类型。
    2. 如果`freq`是'1分钟'，函数会添加额外的时间点到`time_seq`中。
    3. 函数去除`time_seq`中的重复时间点，并确保其长度至少为2。
    4. 函数遍历`freq_market_times`字典，寻找与`time_seq`匹配的项，并返回对应的`freq_x`和`market`。
    5. 如果没有找到匹配的项，函数返回None和"默认"。

    :param time_seq: 时间序列，如 ['11:00', '15:00', '23:00', '01:00', '02:30']
    :param freq: 时间序列对应的K线周期，可选参数，使用该参数可以加快检查速度。
        可选值：1分钟、5分钟、15分钟、30分钟、60分钟、日线、周线、月线、季线、年线
    :return:
        - freq      K线周期
        - market    交易市场
    """
    if freq in ['日线', '周线', '月线', '季线', '年线']:
        return freq, "默认"

    if freq == '1分钟':
        time_seq.extend(['14:57', '14:58', '14:59', '15:00'])

    time_seq = sorted(list(set(time_seq)))
    assert len(time_seq) >= 2, "time_seq长度必须大于等于2"

    for key, tts in freq_market_times.items():
        if freq and not key.startswith(freq):
            continue

        if set(time_seq) == set(tts[:len(time_seq)]):
            freq_x, market = key.split("_")
            return freq_x, market

    return None, "默认"


def freq_end_date(dt, freq: Union[Freq, AnyStr]):
    """交易日结束时间计算"""
    if not isinstance(dt, date):
        dt = pd.to_datetime(dt).date()
    if not isinstance(freq, Freq):
        freq = Freq(freq)

    dt = pd.to_datetime(dt)
    if freq == Freq.D:
        return dt

    if freq == Freq.W:
        return dt + timedelta(days=5 - dt.isoweekday())

    if freq == Freq.Y:
        return datetime(year=dt.year, month=12, day=31)

    if freq == Freq.M:
        if dt.month == 12:
            edt = datetime(year=dt.year, month=12, day=31)
        else:
            edt = datetime(year=dt.year, month=dt.month + 1, day=1) - timedelta(days=1)
        return edt

    if freq == Freq.S:
        dt_m = dt.month
        if dt_m in [1, 2, 3]:
            edt = datetime(year=dt.year, month=4, day=1) - timedelta(days=1)
        elif dt_m in [4, 5, 6]:
            edt = datetime(year=dt.year, month=7, day=1) - timedelta(days=1)
        elif dt_m in [7, 8, 9]:
            edt = datetime(year=dt.year, month=10, day=1) - timedelta(days=1)
        else:
            edt = datetime(year=dt.year, month=12, day=31)
        return edt

    logger.warning(f'error: {dt} - {freq}')
    return dt


def freq_end_time(dt: datetime, freq: Union[Freq, AnyStr], market="A股") -> datetime:
    """A股与期货市场精确的获取 dt 对应的K线周期结束时间

    :param dt: datetime
    :param freq: Freq
    :return: datetime
    """
    assert market in ['A股', '期货', '默认'], "market 参数必须为 A股 或 期货 或 默认"
    if not isinstance(freq, Freq):
        freq = Freq(freq)
    if dt.second > 0 or dt.microsecond > 0:
        dt = dt.replace(second=0, microsecond=0) + timedelta(minutes=1)

    hm = dt.strftime("%H:%M")
    key = f"{freq.value}_{market}"
    if freq.value.endswith("分钟"):
        h, m = map(int, freq_edt_map[key][hm].split(":"))
        edt = dt.replace(hour=h, minute=m)

        if h == m == 0 and freq != Freq.F1 and hm != "00:00":
            edt += timedelta(days=1)

        return edt

    # if not ("15:00" > hm > "09:00") and market == "期货":
    #     dt = next_trading_date(dt, n=1)

    return freq_end_date(dt.date(), freq)


def resample_bars(df: pd.DataFrame, target_freq: Union[Freq, AnyStr], raw_bars=True, **kwargs):
    """将给定的K线数据重新采样为目标周期的K线数据

    函数计算逻辑：

    1. 确定目标周期`target_freq`的类型和市场类型。
    2. 添加一个新列`freq_edt`，表示每个数据点对应的目标周期的结束时间。
    3. 根据`freq_edt`对数据进行分组，并对每组数据进行聚合，得到目标周期的K线数据。
    4. 重置索引，并选择需要的列。
    5. 根据`raw_bars`参数，决定返回的数据类型：如果为True，转换为`RawBar`对象；如果为False，直接返回DataFrame。
    6. 如果`drop_unfinished`参数为True，删除最后一根未完成的K线。

    :param df: 原始K线数据，必须包含以下列：symbol, dt, open, close, high, low, vol, amount。样例如下：
               symbol                  dt     open    close     high      low  \
        0  000001.XSHG 2015-01-05 09:31:00  3258.63  3259.69  3262.85  3258.63
        1  000001.XSHG 2015-01-05 09:32:00  3258.33  3256.19  3259.55  3256.19
        2  000001.XSHG 2015-01-05 09:33:00  3256.10  3257.50  3258.42  3256.10
        3  000001.XSHG 2015-01-05 09:34:00  3259.33  3261.76  3261.76  3257.98
        4  000001.XSHG 2015-01-05 09:35:00  3261.71  3264.88  3265.48  3261.71
                  vol        amount
        0  1333523100  4.346872e+12
        1   511386100  1.665170e+12
        2   455375200  1.483385e+12
        3   363393800  1.185303e+12
        4   402854600  1.315272e+12
    :param target_freq: 目标周期
    :param raw_bars: 是否将转换后的K线序列转换为RawBar对象
    :param kwargs:

        - base_freq: 基础周期，如果不指定，则根据df中的dt列自动推断
        - drop_unfinished: 是否删除最后一根未完成的K线

    :return: 转换后的K线序列
    """
    if not isinstance(target_freq, Freq):
        target_freq = Freq(target_freq)

    base_freq = kwargs.get('base_freq', None)
    if target_freq.value.endswith("分钟"):
        uni_times = df['dt'].head(2000).apply(lambda x: x.strftime("%H:%M")).unique().tolist()
        _, market = check_freq_and_market(uni_times, freq=base_freq)
    else:
        market = "默认"

    df['freq_edt'] = df['dt'].apply(lambda x: freq_end_time(x, target_freq, market))
    dfk1 = df.groupby('freq_edt').agg(
        {'symbol': 'first', 'dt': 'last', 'open': 'first', 'close': 'last', 'high': 'max',
         'low': 'min', 'vol': 'sum', 'amount': 'sum', 'freq_edt': 'last'})
    dfk1.reset_index(drop=True, inplace=True)
    dfk1['dt'] = dfk1['freq_edt']
    dfk1 = dfk1[['symbol', 'dt', 'open', 'close', 'high', 'low', 'vol', 'amount']]

    if raw_bars:
        _bars = []
        for i, row in enumerate(dfk1.to_dict("records"), 1):
            row.update({'id': i, 'freq': target_freq})
            _bars.append(RawBar(**row))

        if kwargs.get('drop_unfinished', True):
            # 清除最后一根未完成的K线
            if df['dt'].iloc[-1] < _bars[-1].dt:
                _bars.pop()
        return _bars
    else:
        return dfk1


class BarGenerator:

    version = 'V231008'

    def __init__(self, base_freq: str, freqs: List[str], max_count: int = 5000, market="默认"):
        self.symbol = None
        self.end_dt = None
        self.market = market
        self.base_freq = base_freq
        self.max_count = max_count
        self.freqs = freqs
        self.bars = {v: [] for v in self.freqs}
        self.bars.update({base_freq: []})
        self.freq_map = {f.value: f for _, f in Freq.__members__.items()}
        self.__validate_freqs()

    def __validate_freqs(self):
        from czsc.utils import sorted_freqs
        if self.base_freq not in sorted_freqs:
            raise ValueError(f'base_freq is not in sorted_freqs: {self.base_freq}')

        i = sorted_freqs.index(self.base_freq)
        f = sorted_freqs[i:]
        for freq in self.freqs:
            if freq not in f:
                raise ValueError(f'freqs中包含不支持的周期：{freq}')

    def init_freq_bars(self, freq: str, bars: List[RawBar]):
        """初始化某个周期的K线序列

        函数计算逻辑：

        1. 首先，它断言`freq`必须是`self.bars`的键之一。如果`freq`不在`self.bars`的键中，代码会抛出一个断言错误。
        2. 然后，它断言`self.bars[freq]`必须为空。如果`self.bars[freq]`不为空，代码会抛出一个断言错误，并显示一条错误消息。
        3. 如果以上两个断言都通过，它会将`bars`赋值给`self.bars[freq]`，从而初始化指定频率的K线序列。
        4. 最后，它会将`bars`列表中的最后一个`RawBar`对象的`symbol`属性赋值给`self.symbol`。

        :param freq: 周期名称
        :param bars: K线序列
        """
        assert freq in self.bars.keys()
        assert not self.bars[freq], f"self.bars['{freq}'] 不为空，不允许执行初始化"
        self.bars[freq] = bars
        self.symbol = bars[-1].symbol

    def __repr__(self):
        return f"<BarGenerator for {self.symbol} @ {self.end_dt}>"

    def _update_freq(self, bar: RawBar, freq: Freq) -> None:
        """更新指定周期K线

        函数计算逻辑：

        1. 计算目标频率的结束时间`freq_edt`。
        2. 检查`self.bars`中是否已经有目标频率的K线。如果没有，创建一个新的`RawBar`对象，并将其添加到`self.bars`中，然后返回。
        3. 如果已经有目标频率的K线，获取最后一根K线`last`。
        4. 检查`freq_edt`是否不等于最后一根K线的日期时间。如果不等于，创建一个新的`RawBar`对象，并将其添加到`self.bars`中。
        5. 如果`freq_edt`等于最后一根K线的日期时间，创建一个新的`RawBar`对象，其开盘价为最后一根K线的开盘价，
            收盘价为当前K线的收盘价，最高价为最后一根K线和当前K线的最高价中的最大值，最低价为最后一根K线和当前K线的最低价中的最小值，
            成交量和成交金额为最后一根K线和当前K线的成交量和成交金额的和。然后用这个新的`RawBar`对象替换`self.bars`中的最后一根K线。

        :param bar: 基础周期已完成K线
        :param freq: 目标周期
        """
        freq_edt = freq_end_time(bar.dt, freq, self.market)

        if not self.bars[freq.value]:
            bar_ = RawBar(symbol=bar.symbol, freq=freq, dt=freq_edt, id=0, open=bar.open,
                          close=bar.close, high=bar.high, low=bar.low, vol=bar.vol, amount=bar.amount)
            self.bars[freq.value].append(bar_)
            return

        last: RawBar = self.bars[freq.value][-1]
        if freq_edt != self.bars[freq.value][-1].dt:
            bar_ = RawBar(symbol=bar.symbol, freq=freq, dt=freq_edt, id=last.id + 1, open=bar.open,
                          close=bar.close, high=bar.high, low=bar.low, vol=bar.vol, amount=bar.amount)
            self.bars[freq.value].append(bar_)

        else:
            bar_ = RawBar(symbol=bar.symbol, freq=freq, dt=freq_edt, id=last.id,
                          open=last.open, close=bar.close, high=max(last.high, bar.high),
                          low=min(last.low, bar.low), vol=last.vol + bar.vol, amount=last.amount + bar.amount)
            self.bars[freq.value][-1] = bar_

    def update(self, bar: RawBar) -> None:
        """更新各周期K线

        函数计算逻辑：

        1. 首先，它获取基准频率`base_freq`，并断言`bar`的频率值等于`base_freq`。
        2. 然后，它将`bar`的符号和日期时间设置为`self.symbol`和`self.end_dt`。
        3. 接下来，它检查是否已经有一个与`bar`日期时间相同的K线存在于`self.bars[base_freq]`中。
            如果存在，它会记录一个警告并返回，不进行任何更新。
        4. 如果不存在重复的K线，它会遍历`self.bars`的所有键（即所有的频率），并对每个频率调用`self._update_freq`方法来更新该频率的K线。
        5. 最后，它会限制在内存中的K线数量，确保每个频率的K线数量不超过`self.max_count`。

        :param bar: 必须是已经结束的Bar
        :return: None
        """
        base_freq = self.base_freq
        if bar.freq.value != base_freq:
            raise ValueError(f"Input bar frequency does not match base frequency. Expected {base_freq}, got {bar.freq.value}")
        self.symbol = bar.symbol
        self.end_dt = bar.dt

        if self.bars[base_freq] and self.bars[base_freq][-1].dt == bar.dt:
            logger.warning(f"BarGenerator.update: 输入重复K线，基准周期为{base_freq}; \n\n输入K线为{bar};\n\n 上一根K线为{self.bars[base_freq][-1]}")
            return

        for freq in self.bars.keys():
            self._update_freq(bar, self.freq_map[freq])

        # 限制存在内存中的K限制数量
        for f, b in self.bars.items():
            if len(b) > self.max_count:
                self.bars[f] = b[-self.max_count:]
