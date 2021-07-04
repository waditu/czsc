# coding: utf-8
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
        k = RawBar(symbol=k.symbol, id=1, freq=Freq.W, dt=next_end_dt, open=k.open, close=k.close, high=k.high, low=k.low, vol=k.vol)
        if not self.W:
            self.W.append(k)
        last = self.W[-1]
        if next_end_dt.weekday() == 0 and k.dt.weekday() != last.dt.weekday():
            k.id = last.id + 1
            self.W.append(k)
        else:
            self.W[-1] = self.__update_from_1min(last, k, next_end_dt)

        self.W = self.W[-self.max_count:]

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
            print("输入1分钟K时间小于最近一个更新时间，{} <= {}，不进行K线更新".format(k.dt, self.end_dt))
            return

        self.end_dt = k.dt
        self.symbol = k.symbol

        self.__update_1min(k)
        self.__update_minutes(k, minutes=(5, 15, 30, 60))
        if "日线" in self.freqs:
            self.__update_d(k)
        if "周线" in self.freqs:
            self.__update_w(k)

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

