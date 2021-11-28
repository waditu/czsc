# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/11/14 12:39
describe: 从任意周期K线开始合成更高周期K线的工具类
"""
from datetime import datetime, timedelta
from typing import List
from ..objects import RawBar, Freq


def freq_end_time(dt: datetime, freq: Freq) -> datetime:
    """获取 dt 对应的K线周期结束时间

    :param dt: datetime
    :param freq: Freq
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
        sdt = dt + timedelta(days=5 - dt.isoweekday())
        return sdt

    if freq == Freq.M:
        if dt.month == 12:
            sdt = datetime(year=dt.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            sdt = datetime(year=dt.year, month=dt.month + 1, day=1) - timedelta(days=1)
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
            sdt = datetime(year=dt.year + 1, month=1, day=1) - timedelta(days=1)
        return sdt

    if freq == Freq.Y:
        return datetime(year=dt.year, month=12, day=31)

    print(f'freq_end_time error: {dt} - {freq}')
    return dt


class BarGenerator:
    """使用日线合成周线、月线、季线"""

    def __init__(self, base_freq: str, freqs: List[str], max_count: int = 5000):
        self.symbol = None
        self.end_dt = None
        self.base_freq = base_freq
        self.max_count = max_count
        self.freqs = freqs
        self.bars = {v: [] for v in self.freqs}
        self.bars.update({base_freq: []})
        self.freq_map = {f.value: f for _, f in Freq.__members__.items()}
        self.__validate_freq_params()

    def __validate_freq_params(self):
        # K线周期约束，由于要求 base_freq 的输入K必须是完成的，只能生成 base_freq 以上周期的K线
        self.base_freq_constraint = {
            "1分钟": ['5分钟', '15分钟', '30分钟', '60分钟', '日线', '周线', '月线', '季线', '年线'],
            "5分钟": ['15分钟', '30分钟', '60分钟', '日线', '周线', '月线', '季线', '年线'],
            "15分钟": ['30分钟', '60分钟', '日线', '周线', '月线', '季线', '年线'],
            "30分钟": ['60分钟', '日线', '周线', '月线', '季线', '年线'],
            "60分钟": ['日线', '周线', '月线', '季线', '年线'],
            "日线": ['周线', '月线', '季线', '年线'],
        }

        assert self.base_freq in self.freq_map.keys()
        assert self.base_freq in self.base_freq_constraint.keys()
        bfc = self.base_freq_constraint[self.base_freq]

        for freq in self.freqs:
            assert freq in self.freq_map.keys()
            assert freq in bfc, f"{freq} 不在允许生成的周期列表中"
        assert self.base_freq not in self.freqs, 'base_freq 不能在 freqs 列表中'

    def __repr__(self):
        return f"<BarGenerator for {self.symbol} @ {self.end_dt}>"

    def _update_freq(self, bar: RawBar, freq: Freq):
        """更新指定周期"""
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
        """更新各周期K线

        :param bar: 必须是已经结束的Bar
        :return:
        """
        base_freq = self.base_freq
        assert bar.freq.value == base_freq
        self.symbol = bar.symbol
        self.end_dt = bar.dt

        if self.bars[base_freq] and self.bars[base_freq][-1].dt == bar.dt:
            print(f"BarGenerator.update: 输入重复K线，基准周期为{base_freq}")
            return

        for freq in self.bars.keys():
            self._update_freq(bar, self.freq_map[freq])

        # 限制存在内存中的K限制数量
        for f, b in self.bars.items():
            self.bars[f] = b[-self.max_count:]
