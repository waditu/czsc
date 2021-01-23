# coding: utf-8
import warnings
from datetime import datetime, timedelta
from typing import List
from ..objects import RawBar


def bar_end_time(dt: datetime, m=1):
    """获取 dt 对应的分钟周期结束时间

    :param dt: datetime
    :param m: int
        分钟周期，1 表示 1分钟，5 表示 5分钟 ...
    :return: datetime
    """
    am_st = "09:30"
    am_et = "11:30"
    pm_st = "13:00"
    pm_et = "15:00"

    dt_span = {
        60: ['10:30', "11:30", "14:00", "15:00"]
    }

    dt = dt.replace(second=0)
    if dt.strftime("%H:%M") == am_et or dt.strftime("%H:%M") == pm_et:
        return dt.replace(second=0)

    if m < 60:
        delta = timedelta(minutes=1)
        for _ in range(1000):
            dt = dt + delta
            if dt.minute % m == 0:
                h = dt.strftime("%H:%M")
                if am_et >= h > am_st or pm_et >= h > pm_st:
                    return dt
    else:
        h = dt.strftime("%H:%M")
        for edt in dt_span[m]:
            if h <= edt:
                hour, minute = edt.split(":")
                return dt.replace(hour=int(hour), minute=int(minute))
    return dt


class KlineGeneratorBase:
    """K线生成器，仿实盘"""

    def __init__(self, max_count: int = 5000, freqs: List[str] = None):
        """

        :param max_count: int
            最大K线数量
        :param freqs: list of str
            级别列表，默认值为 ['周线', '日线', '60分钟', '30分钟', '15分钟', '5分钟', '1分钟']
        """
        self.max_count = max_count
        if freqs is None:
            self.freqs = ['周线', '日线', '60分钟', '30分钟', '15分钟', '5分钟', '1分钟']
        else:
            self.freqs = freqs
        self.m1: List[RawBar] = []
        self.m5: List[RawBar] = []
        self.m15: List[RawBar] = []
        self.m30: List[RawBar] = []
        self.m60: List[RawBar] = []
        self.D: List[RawBar] = []
        self.W: List[RawBar] = []
        self.end_dt = None
        self.symbol = None

    def __update_end_dt(self):
        if self.m1:
            self.end_dt = self.m1[-1].dt
            self.symbol = self.m1[-1].symbol

    def init_kline(self, freq: str, kline: List[RawBar]):
        """输入K线进行初始化

        :param freq: str
        :param kline: list of dict
        :return:
        """
        freqs_map = {"1分钟": self.m1, "5分钟": self.m5, "15分钟": self.m15,
                     "30分钟": self.m30, "60分钟": self.m60, "日线": self.D, "周线": self.W}
        m = freqs_map[freq]
        m.extend(kline)
        self.__update_end_dt()

    def __repr__(self):
        return "<KlineGenerator for {}; latest_dt={}>".format(self.symbol, self.end_dt)

    # def __update_minutes(self):
    #     pass
    #
    # def __update_d(self):
    #     pass
    #
    # def __update_w(self):
    #     pass
    #
    # def update(self):
    #     pass

    def get_kline(self, freq: str, count: int = 1000) -> List[RawBar]:
        """获取单个级别的K线

        :param freq: str
            级别名称，可选值 1分钟；5分钟；15分钟；30分钟；60分钟；日线；周线
        :param count: int
            数量
        :return: list of dict
        """
        freqs_map = {"1分钟": self.m1, "5分钟": self.m5, "15分钟": self.m15,
                     "30分钟": self.m30, "60分钟": self.m60, "日线": self.D, "周线": self.W}
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


class KlineGeneratorByTick(KlineGeneratorBase):
    """K线生成器，仿实盘，从tick开始生成"""

    def __init__(self, max_count: int = 5000, freqs: List[str] = None):
        """

        :param max_count: int
            最大K线数量
        :param freqs: list of str
            级别列表，默认值为 ['周线', '日线', '60分钟', '30分钟', '15分钟', '5分钟', '1分钟']
        """
        super().__init__(max_count, freqs)
        warnings.warn("KlineGeneratorByTick 存在已知Bug，慎用")

    def __repr__(self):
        return "<KlineGeneratorByTick for {}; latest_dt={}>".format(self.symbol, self.end_dt)

    @staticmethod
    def __update_from_tick(last, tick):
        new = dict(last)
        new.update({
            'close': round(tick['price'], 2),
            "dt": tick['dt'],
            "high": round(max(last['high'], tick['price']), 2),
            "low": round(min(last['low'], tick['price']), 2),
            "vol": last['vol'] + tick['vol']
        })
        if new['open'] <= 0:
            new['open'] = round(tick['price'], 2)

        if new['low'] <= 0:
            new['low'] = round(tick['price'], 2)

        return new

    @staticmethod
    def __init_bar_from_tick(tick):
        p = round(tick['price'], 2)
        return {
            'symbol': tick['symbol'],
            'open': p,
            'close': p,
            "dt": tick['dt'],
            "high": p,
            "low": p,
            "vol": tick['vol']
        }

    def __update_minutes(self, tick=None, minutes=(1, 5, 15, 30, 60)):
        # 更新分钟线
        fm_map = {1: self.m1, 5: self.m5, 15: self.m15, 30: self.m30, 60: self.m60}

        for minute in minutes:
            if "{}分钟".format(minute) not in self.freqs:
                continue

            m = fm_map[minute]
            if not m:
                next_bar = self.__init_bar_from_tick(tick)
                next_bar['dt'] = bar_end_time(tick['dt'], m=minute)
                m.append(next_bar)
            else:
                last = m[-1]
                next_end_dt = bar_end_time(tick['dt'], m=minute)
                if next_end_dt > last['dt'] and next_end_dt.minute != last['dt'].minute:
                    next_bar = self.__init_bar_from_tick(tick)
                    next_bar['dt'] = next_end_dt
                    m.append(next_bar)
                else:
                    next_bar = self.__update_from_tick(last, tick)
                    next_bar['dt'] = next_end_dt
                    m[-1] = next_bar
            fm_map[minute] = m[-self.max_count:]

    def __update_d(self, tick=None):
        if "日线" not in self.freqs:
            return

        if not self.D:
            self.D.append(self.__init_bar_from_tick(tick))
        else:
            last = self.D[-1]
            if last['dt'].date() != tick['dt'].date():
                self.D.append(self.__init_bar_from_tick(tick))
            else:
                self.D[-1] = self.__update_from_tick(last, tick)
        self.D = self.D[-self.max_count:]

    def __update_w(self, tick=None):
        if "周线" not in self.freqs:
            return

        if not self.W:
            self.W.append(self.__init_bar_from_tick(tick))
        else:
            last = self.W[-1]
            if tick['dt'].weekday() == 0 and tick['dt'].weekday() != last['dt'].weekday():
                self.W.append(self.__init_bar_from_tick(tick))
            else:
                self.W[-1] = self.__update_from_tick(last, tick)
        self.W = self.W[-self.max_count:]

    def update(self, tick=None):
        """输入1分钟最新K线 或 tick，更新其他级别K线

        :param tick: dict
            {'symbol': '000001.XSHG',
             'dt': Timestamp('2020-07-16 14:51:00'),
             'price': 3216.8,
             'vol': '270429600'}
        """
        if self.end_dt and tick['dt'] < self.end_dt:
            warnings.warn("输入 tick 时间小于最近一个更新时间，{} < {}，不进行K线更新".format(tick['dt'], self.end_dt))
            return

        assert isinstance(tick, dict)
        self.end_dt = tick['dt']
        self.symbol = tick['symbol']
        self.__update_minutes(tick, minutes=(1, 5, 15, 30, 60))
        if "日线" in self.freqs:
            self.__update_d(tick)
        if "周线" in self.freqs:
            self.__update_w(tick)


class KlineGeneratorBy1Min(KlineGeneratorBase):
    """K线生成器，仿实盘，从1分钟开始生成"""

    def __init__(self, max_count: int = 5000, freqs: List[str] = None):
        """

        :param max_count: int
            最大K线数量
        :param freqs: list of str
            级别列表，默认值为 ['周线', '日线', '60分钟', '30分钟', '15分钟', '5分钟', '1分钟']
        """
        super().__init__(max_count, freqs)

    def __repr__(self):
        return "<KlineGeneratorBy1Min for {}; latest_dt={}>".format(self.symbol, self.end_dt)

    @staticmethod
    def __update_from_1min(last: RawBar, k: RawBar, next_end_dt: datetime):
        new = RawBar(
            symbol=last.symbol,
            dt=next_end_dt,
            open=last.open,
            close=k.close,
            high=max(last.high, k.high),
            low=min(last.low, k.low),
            vol=last.vol + k.vol,
        )
        return new

    def __update_1min(self, k: RawBar):
        # 更新1分钟线
        if "1分钟" not in self.freqs:
            return

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
        # 更新分钟线
        fm_map = {5: self.m5, 15: self.m15, 30: self.m30, 60: self.m60}

        for minute in minutes:
            if "{}分钟".format(minute) not in self.freqs:
                continue

            m = fm_map[minute]
            next_end_dt = bar_end_time(k.dt, m=minute)
            if not m:
                m.append(RawBar(symbol=k.symbol, dt=next_end_dt, open=k.open, close=k.close,
                                high=k.high, low=k.low, vol=k.vol))
            else:
                last = m[-1]
                if next_end_dt != last.dt:
                    m.append(RawBar(symbol=k.symbol, dt=next_end_dt, open=k.open, close=k.close,
                                    high=k.high, low=k.low, vol=k.vol))
                else:
                    next_bar = self.__update_from_1min(last, k, next_end_dt)
                    m[-1] = next_bar
            fm_map[minute] = m[-self.max_count:]

    def __update_d(self, k=None):
        if "日线" not in self.freqs:
            return

        if not self.D:
            self.D.append(k)
        last = self.D[-1]
        next_end_dt = k.dt.replace(hour=0, minute=0, second=0, microsecond=0)
        if next_end_dt.date() != last.dt.date():
            self.D.append(k)
        else:
            self.D[-1] = self.__update_from_1min(last, k, next_end_dt)

        self.D = self.D[-self.max_count:]

    def __update_w(self, k=None):
        if "周线" not in self.freqs:
            return
        if not self.W:
            self.W.append(k)
        last = self.W[-1]
        next_end_dt = k.dt.replace(hour=0, minute=0, second=0, microsecond=0)
        if next_end_dt.weekday() == 0 and k.dt.weekday() != last.dt.weekday():
            self.W.append(k)
        else:
            self.W[-1] = self.__update_from_1min(last, k, next_end_dt)

        self.W = self.W[-self.max_count:]

    def update(self, k: RawBar):
        """输入1分钟最新K线，更新其他级别K线

        :param k: 1分钟K线
        """
        if self.end_dt and k.dt < self.end_dt:
            print("输入1分钟K时间小于最近一个更新时间，{} < {}，不进行K线更新".format(k.dt, self.end_dt))
            return

        self.end_dt = k.dt
        self.symbol = k.symbol

        self.__update_1min(k)
        self.__update_minutes(k, minutes=(5, 15, 30, 60))
        if "日线" in self.freqs:
            self.__update_d(k)
        if "周线" in self.freqs:
            self.__update_w(k)

