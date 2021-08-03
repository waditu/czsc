# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/7/22 15:09
"""

from typing import List
from ..objects import RawBar, Freq

class KlineGeneratorD:
    """使用日线合成周线、月线、季线"""
    def __init__(self):
        self.symbol = None
        self.end_dt = None
        self.freqs: List[Freq] = [Freq.D, Freq.W, Freq.M, Freq.S, Freq.Y]
        self.bars = {v.value: [] for v in self.freqs}

    def __repr__(self):
        return f"<KlineGeneratorD for {self.symbol} @ {self.end_dt}>"

    def _update_w(self, bar: RawBar):
        """更新周线"""
        if not self.bars[Freq.W.value]:
            bar_w = RawBar(symbol=bar.symbol, freq=Freq.W, dt=bar.dt, id=0, open=bar.open,
                           close=bar.close, high=bar.high, low=bar.low, vol=bar.vol)
            self.bars[Freq.W.value].append(bar_w)
            return

        last = self.bars[Freq.W.value][-1]
        if bar.dt.isoweekday() == 1:
            bar_w = RawBar(symbol=bar.symbol, freq=Freq.W, dt=bar.dt, id=last.id + 1, open=bar.open,
                           close=bar.close, high=bar.high, low=bar.low, vol=bar.vol)
            self.bars[Freq.W.value].append(bar_w)
        else:

            bar_w = RawBar(symbol=bar.symbol, freq=Freq.W, dt=bar.dt, id=last.id, open=last.open, close=bar.close,
                           high=max(last.high, bar.high), low=min(last.low, bar.low), vol=last.vol + bar.vol)
            self.bars[Freq.W.value][-1] = bar_w

    def _update_m(self, bar: RawBar):
        """更新月线"""
        if not self.bars[Freq.M.value]:
            bar_m = RawBar(symbol=bar.symbol, freq=Freq.M, dt=bar.dt, id=0, open=bar.open,
                           close=bar.close, high=bar.high, low=bar.low, vol=bar.vol)
            self.bars[Freq.M.value].append(bar_m)
            return

        last: RawBar = self.bars[Freq.M.value][-1]
        if bar.dt.month != last.dt.month:
            bar_m = RawBar(symbol=bar.symbol, freq=Freq.M, dt=bar.dt, id=last.id + 1, open=bar.open,
                           close=bar.close, high=bar.high, low=bar.low, vol=bar.vol)
            self.bars[Freq.M.value].append(bar_m)
        else:
            bar_m = RawBar(symbol=bar.symbol, freq=Freq.M, dt=bar.dt, id=last.id, open=last.open, close=bar.close,
                           high=max(last.high, bar.high), low=min(last.low, bar.low), vol=last.vol + bar.vol)
            self.bars[Freq.M.value][-1] = bar_m

    def _update_s(self, bar: RawBar):
        """更新季线"""
        if not self.bars[Freq.S.value]:
            bar_s = RawBar(symbol=bar.symbol, freq=Freq.S, dt=bar.dt, id=0, open=bar.open,
                           close=bar.close, high=bar.high, low=bar.low, vol=bar.vol)
            self.bars[Freq.S.value].append(bar_s)
            return

        last: RawBar = self.bars[Freq.S.value][-1]
        if bar.dt.month != last.dt.month and bar.dt.month in [1, 4, 7, 10]:
            bar_s = RawBar(symbol=bar.symbol, freq=Freq.S, dt=bar.dt, id=last.id + 1, open=bar.open,
                           close=bar.close, high=bar.high, low=bar.low, vol=bar.vol)
            self.bars[Freq.S.value].append(bar_s)
        else:
            bar_s = RawBar(symbol=bar.symbol, freq=Freq.S, dt=bar.dt, id=last.id, open=last.open, close=bar.close,
                           high=max(last.high, bar.high), low=min(last.low, bar.low), vol=last.vol + bar.vol)
            self.bars[Freq.S.value][-1] = bar_s

    def _update_y(self, bar: RawBar):
        """更新年线"""
        if not self.bars[Freq.Y.value]:
            bar_y = RawBar(symbol=bar.symbol, freq=Freq.Y, dt=bar.dt, id=0, open=bar.open,
                           close=bar.close, high=bar.high, low=bar.low, vol=bar.vol)
            self.bars[Freq.Y.value].append(bar_y)
            return

        last: RawBar = self.bars[Freq.Y.value][-1]
        if bar.dt.year != last.dt.year:
            bar_y = RawBar(symbol=bar.symbol, freq=Freq.Y, dt=bar.dt, id=last.id + 1, open=bar.open,
                           close=bar.close, high=bar.high, low=bar.low, vol=bar.vol)
            self.bars[Freq.Y.value].append(bar_y)
        else:
            bar_y = RawBar(symbol=bar.symbol, freq=Freq.Y, dt=bar.dt, id=last.id, open=last.open, close=bar.close,
                           high=max(last.high, bar.high), low=min(last.low, bar.low), vol=last.vol + bar.vol)
            self.bars[Freq.Y.value][-1] = bar_y

    def update(self, bar: RawBar):
        assert bar.freq == Freq.D
        self.symbol = bar.symbol
        self.end_dt = bar.dt

        if self.bars[Freq.D.value] and self.bars[Freq.D.value][-1].dt.date() == bar.dt.date():
            return

        self.bars[Freq.D.value].append(bar)
        self._update_w(bar)
        self._update_m(bar)
        self._update_s(bar)
        self._update_y(bar)


