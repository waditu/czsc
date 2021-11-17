# coding: utf-8
from deprecated import deprecated
from datetime import datetime, timedelta
from typing import List, Union
from ..enum import Freq
from ..objects import RawBar


def bar_end_time(dt: datetime, m=1):
    """获取 dt 对应的分钟周期结束时间

    :param dt: datetime
    :param m: int
        分钟周期，1 表示 1分钟，5 表示 5分钟 ...
    :return: datetime
    """
    dt = dt.replace(second=0, microsecond=0)
    dt_span = {
        60: ["01:00", "2:00", "3:00", '10:30', "11:30", "14:00", "15:00", "22:00", "23:00", "23:59"],
    }

    if m < 60:
        if (dt.hour == 15 and dt.minute == 0) or (dt.hour == 11 and dt.minute == 30):
            return dt

        delta_m = dt.minute % m
        if delta_m != 0:
            dt += timedelta(minutes=m - delta_m)
        else:
            dt += timedelta(minutes=m)
        return dt
    else:
        for v in dt_span[m]:
            hour, minute = v.split(":")
            edt = dt.replace(hour=int(hour), minute=int(minute))
            if dt <= edt:
                return edt
    return dt

def freq_end_time(dt: datetime, freq: Freq) -> datetime:
    """获取 dt 对应的K线周期结束时间

    :param dt: datetime
    :param freq: Freq
        周期，1 表示 1分钟，5 表示 5分钟 ...
    :return: datetime
    """
    dt = dt.replace(second=0, microsecond=0)

    if freq in [Freq.F1, Freq.F5, Freq.F15, Freq.F30, Freq.F60]:
        m = int(freq.value.strip("分钟"))
        if m < 60:
            if (dt.hour == 15 and dt.minute == 0) or (dt.hour == 11 and dt.minute == 30):
                return dt

            delta_m = dt.minute % m
            if delta_m != 0:
                dt += timedelta(minutes=m - delta_m)
            return dt

        else:
            dt_span = {
                60: ["01:00", "2:00", "3:00", '10:30', "11:30", "14:00", "15:00", "22:00", "23:00", "23:59"],
            }
            for v in dt_span[m]:
                hour, minute = v.split(":")
                edt = dt.replace(hour=int(hour), minute=int(minute))
                if dt <= edt:
                    return edt

    # 处理 日、周、月、季、年 的结束时间
    dt = dt.replace(hour=0, minute=0)

    if freq == Freq.D:
        return dt

    if freq == Freq.W:
        sdt = dt + timedelta(days=5-dt.isoweekday())
        return sdt

    if freq == Freq.M:
        if dt.month == 12:
            sdt = datetime(year=dt.year+1, month=1, day=1) - timedelta(days=1)
        else:
            sdt = datetime(year=dt.year, month=dt.month+1, day=1) - timedelta(days=1)
        return sdt

    if freq == Freq.S:
        dt_m = dt.month
        if dt_m in [1, 2, 3]:
            sdt = datetime(year=dt.year, month=4, day=1) - timedelta(days=1)
        elif dt_m in [4, 5, 6]:
            sdt = datetime(year=dt.year, month=7, day=1) - timedelta(days=1)
        elif dt_m in [7, 8, 9]:
            sdt = datetime(year=dt.year, month=10, day=1) - timedelta(days=1)
        else:
            sdt = datetime(year=dt.year+1, month=1, day=1) - timedelta(days=1)
        return sdt

    if freq == Freq.Y:
        return datetime(year=dt.year, month=12, day=31)

    print(f'freq_end_time error: {dt} - {freq}')
    return dt


@deprecated(reason="请使用 BarGenerator，性能更高，且支持从任意周期开始合成", version='1.0.0')
class KlineGenerator:
    """K线生成器，仿实盘"""

    def __init__(self, max_count: int = 5000, freqs: List[Union[str, Freq]] = None):
        """

        :param max_count: int
            最大K线数量
        :param freqs: list of str
            级别列表，默认值为 ['周线', '日线', '60分钟', '30分钟', '15分钟', '5分钟', '1分钟']
        """
        self.max_count = max_count
        if freqs is None:
            self.freqs = ['月线', '周线', '日线', '60分钟', '30分钟', '15分钟', '5分钟', '1分钟']
        else:
            self.freqs = freqs
        self.m1: List[RawBar] = []
        self.m5: List[RawBar] = []
        self.m15: List[RawBar] = []
        self.m30: List[RawBar] = []
        self.m60: List[RawBar] = []
        self.D: List[RawBar] = []
        self.W: List[RawBar] = []
        self.M: List[RawBar] = []
        self.end_dt = None
        self.symbol = None

    def __update_end_dt(self):
        if self.m1:
            self.end_dt = self.m1[-1].dt
            self.symbol = self.m1[-1].symbol

    def init_kline(self, freq: [Freq, str], kline: List[RawBar]):
        """输入K线进行初始化

        :param freq: str
        :param kline: list of dict
        :return:
        """
        freqs_map = {"1分钟": self.m1, "5分钟": self.m5, "15分钟": self.m15, "30分钟": self.m30,
                     "60分钟": self.m60, "日线": self.D, "周线": self.W, "月线": self.M}
        m = freqs_map[freq.value if isinstance(freq, Freq) else freq]
        m.extend(kline)
        self.__update_end_dt()

    def __repr__(self):
        return "<KlineGenerator for {}; latest_dt={}>".format(self.symbol, self.end_dt)

    @staticmethod
    def __update_from_1min(last: RawBar, k: RawBar, next_end_dt: datetime):
        new = RawBar(
            symbol=last.symbol,
            dt=next_end_dt,
            id=last.id,
            freq=last.freq,
            open=last.open,
            close=k.close,
            high=max(last.high, k.high),
            low=min(last.low, k.low),
            vol=last.vol + k.vol,
        )
        return new

    def __update_1min(self, k: RawBar):
        """更新1分钟线"""
        assert '1分钟' in self.freqs
        if not self.m1:
            self.m1.append(k)
        else:
            if k.dt > self.m1[-1].dt:
                self.m1.append(k)
            elif k.dt == self.m1[-1].dt:
                self.m1[-1] = k
            else:
                raise ValueError("1分钟新K线的时间{}必须大于等于最后一根K线的时间{}".format(k.dt, self.m1[-1].dt))

        self.m1 = self.m1[-self.max_count:]

    def __update_minutes(self, k: RawBar, minutes=(5, 15, 30, 60)):
        """更新分钟线"""
        fm_map = {5: self.m5, 15: self.m15, 30: self.m30, 60: self.m60}
        freq_map = {5: Freq.F5, 15: Freq.F15, 30: Freq.F30, 60: Freq.F60}

        for minute in minutes:
            if "{}分钟".format(minute) not in self.freqs:
                continue

            m = fm_map[minute]
            next_end_dt = bar_end_time(k.dt, m=minute)
            if not m:
                m.append(RawBar(symbol=k.symbol, id=1, freq=freq_map[minute],
                                dt=next_end_dt, open=k.open, close=k.close,
                                high=k.high, low=k.low, vol=k.vol))
            else:
                last = m[-1]
                if next_end_dt != last.dt:
                    m.append(RawBar(symbol=k.symbol, id=last.id+1, freq=freq_map[minute],
                                    dt=next_end_dt, open=k.open, close=k.close,
                                    high=k.high, low=k.low, vol=k.vol))
                else:
                    next_bar = self.__update_from_1min(last, k, next_end_dt)
                    m[-1] = next_bar
            fm_map[minute] = m[-self.max_count:]

    def __update_d(self, k=None):
        if "日线" not in self.freqs:
            return

        next_end_dt = k.dt.replace(hour=0, minute=0, second=0, microsecond=0)
        k = RawBar(symbol=k.symbol, id=1, freq=Freq.D, dt=next_end_dt, open=k.open, close=k.close, high=k.high, low=k.low, vol=k.vol)
        if not self.D:
            self.D.append(k)
        last = self.D[-1]
        if next_end_dt.date() != last.dt.date():
            k.id = last.id + 1
            self.D.append(k)
        else:
            self.D[-1] = self.__update_from_1min(last, k, next_end_dt)

        self.D = self.D[-self.max_count:]

    def __update_w(self, k=None):
        if "周线" not in self.freqs:
            return

        next_end_dt = k.dt.replace(hour=0, minute=0, second=0, microsecond=0)
        k = RawBar(symbol=k.symbol, id=1, freq=Freq.W, dt=next_end_dt, open=k.open,
                   close=k.close, high=k.high, low=k.low, vol=k.vol)
        if not self.W:
            self.W.append(k)

        last = self.W[-1]
        if next_end_dt.weekday() == 0 and k.dt.weekday() != last.dt.weekday():
            k.id = last.id + 1
            self.W.append(k)
        else:
            self.W[-1] = self.__update_from_1min(last, k, next_end_dt)

        self.W = self.W[-self.max_count:]

    def __update_m(self, k=None):
        if "月线" not in self.freqs:
            return

        next_end_dt: datetime = k.dt.replace(hour=0, minute=0, second=0, microsecond=0)
        k = RawBar(symbol=k.symbol, id=1, freq=Freq.M, dt=next_end_dt, open=k.open,
                   close=k.close, high=k.high, low=k.low, vol=k.vol)
        if not self.M:
            self.M.append(k)

        last = self.M[-1]
        if next_end_dt.month != last.dt.month:
            k.id = last.id + 1
            self.M.append(k)
        else:
            self.M[-1] = self.__update_from_1min(last, k, next_end_dt)

        self.M = self.M[-self.max_count:]

    def update(self, k: RawBar):
        """输入1分钟、Tick最新数据，更新其他级别K线

        :param k: 1分钟K线
        """
        assert k.freq == Freq.F1, "目前仅支持从1分钟K线生成"
        if self.m1:
            k.id = self.m1[-1].id + 1
        else:
            k.id = 0
        if self.end_dt and k.dt <= self.end_dt:
            # print("输入1分钟K时间小于最近一个更新时间，{} <= {}，不进行K线更新".format(k.dt, self.end_dt))
            return

        self.end_dt = k.dt
        self.symbol = k.symbol

        self.__update_1min(k)
        self.__update_minutes(k, minutes=(5, 15, 30, 60))
        self.__update_d(k)
        self.__update_w(k)
        self.__update_m(k)

    def get_kline(self, freq: str, count: int = 1000) -> List[RawBar]:
        """获取单个级别的K线

        :param freq: str
            级别名称，可选值 1分钟；5分钟；15分钟；30分钟；60分钟；日线；周线
        :param count: int
            数量
        :return: list of dict
        """
        freqs_map = {"1分钟": self.m1, "5分钟": self.m5, "15分钟": self.m15, "30分钟": self.m30,
                     "60分钟": self.m60, "日线": self.D, "周线": self.W, "月线": self.M}
        return freqs_map[freq][-count:]

    def get_klines(self, counts=None):
        """获取多个级别的K线

        :param counts: dict
            默认值 {"1分钟": 1000, "5分钟": 1000, "30分钟": 1000, "日线": 100}
        :return: dict of list of dict
        """
        if counts is None:
            counts = {"1分钟": 1000, "5分钟": 1000, "30分钟": 1000, "日线": 100}
        return {k: self.get_kline(k, v) for k, v in counts.items()}

@deprecated(reason="请使用 BarGenerator，性能更高，且支持从任意周期开始合成", version='1.0.0')
class KlineGeneratorD:
    """使用日线合成周线、月线、季线"""
    def __init__(self, freqs: List[str] = None):
        self.symbol = None
        self.end_dt = None
        if freqs:
            self.freqs = freqs
        else:
            self.freqs: List[str] = [Freq.D.value, Freq.W.value, Freq.M.value, Freq.S.value, Freq.Y.value]
        self.bars = {v: [] for v in self.freqs}

    def __repr__(self):
        return f"<KlineGeneratorD for {self.symbol} @ {self.end_dt}>"

    def _update_freq(self, bar: RawBar, freq: Freq):
        """更新指定周期K线"""
        freq_edt = freq_end_time(bar.dt, freq)

        if not self.bars[freq.value]:
            bar_ = RawBar(symbol=bar.symbol, freq=freq, dt=freq_edt, id=0, open=bar.open,
                           close=bar.close, high=bar.high, low=bar.low, vol=bar.vol)
            self.bars[freq.value].append(bar_)
            return

        last = self.bars[freq.value][-1]
        if freq_edt != self.bars[freq.value][-1].dt:
            bar_ = RawBar(symbol=bar.symbol, freq=freq, dt=freq_edt, id=last.id + 1, open=bar.open,
                           close=bar.close, high=bar.high, low=bar.low, vol=bar.vol)
            self.bars[freq.value].append(bar_)

        else:
            bar_ = RawBar(symbol=bar.symbol, freq=freq, dt=freq_edt, id=last.id, open=last.open, close=bar.close,
                           high=max(last.high, bar.high), low=min(last.low, bar.low), vol=last.vol + bar.vol)
            self.bars[freq.value][-1] = bar_

    def update(self, bar: RawBar):
        """

        :param bar: 必须是已经结束的日线 Bar
        :return:
        """
        assert bar.freq == Freq.D
        self.symbol = bar.symbol
        self.end_dt = bar.dt

        if self.bars[Freq.D.value] and self.bars[Freq.D.value][-1].dt.date() == bar.dt.date():
            return

        self.bars[Freq.D.value].append(bar)

        if Freq.W.value in self.freqs:
            self._update_freq(bar, Freq.W)

        if Freq.M.value in self.freqs:
            self._update_freq(bar, Freq.M)

        if Freq.S.value in self.freqs:
            self._update_freq(bar, Freq.S)

        if Freq.Y.value in self.freqs:
            self._update_freq(bar, Freq.Y)

