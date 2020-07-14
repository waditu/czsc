# coding: utf-8
"""
缠论对象化
"""

import pandas as pd


class FX:
    """分型"""
    # __slots__ = ["elements", "number", 'mark', 'dt', 'price', 'is_end']

    def __init__(self):
        self.elements = []
        self.mark = None
        self.dt = None
        self.price = None
        self.is_end = False

    def __remove_include(self, bar: dict):
        """去除包含关系"""
        b = dict(bar)
        if len(self.elements) < 2:
            self.elements.append(b)
            return

        k1, k2 = self.elements[-2:]
        if k2['high'] > k1['high']:
            direction = "up"
        elif k2['low'] < k1['low']:
            direction = "down"
        else:
            direction = "up"

        # 判断 k2 与 k 之间是否存在包含关系
        cur_h, cur_l = b['high'], b['low']
        last_h, last_l = k2['high'], k2['low']

        # 左包含 or 右包含
        if (cur_h <= last_h and cur_l >= last_l) or (cur_h >= last_h and cur_l <= last_l):
            self.elements.pop(-1)
            # 有包含关系，按方向分别处理
            if direction == "up":
                last_h = max(last_h, cur_h)
                last_l = max(last_l, cur_l)
            elif direction == "down":
                last_h = min(last_h, cur_h)
                last_l = min(last_l, cur_l)
            else:
                raise ValueError
            b.update({"high": last_h, "low": last_l})

            # 保留红绿不变
            if b['open'] >= b['close']:
                b.update({"open": last_h, "close": last_l})
            else:
                b.update({"open": last_l, "close": last_h})
        self.elements.append(b)

    def update(self, bar: dict):
        """输入新的蜡烛，更新分型

        :param bar: dict
            k线蜡烛，数据示例如下
            {'symbol': '600797.SH', 'dt': '2020-01-08 11:30:00', 'open': 10.72, 'close': 10.67, 'high': 10.76, 'low': 10.63, 'vol': 4464800.0}
        :return:
        """
        self.__remove_include(bar)
        if len(self.elements) >= 3:
            k1, k2, k3 = self.elements[-3:]
            if k1['high'] < k2['high'] > k3['high']:
                self.mark = "g"
                self.price = k2['high']
                self.dt = k2['dt']
                self.is_end = True

            if k1['low'] > k2['low'] < k3['low']:
                self.mark = "d"
                self.price = k2['low']
                self.dt = k2['dt']
                self.is_end = True

    def __repr__(self):
        return f"<FX - {self.mark} - {self.dt} - {self.price}>"


class BI:
    """笔"""
    # __slots__ = ["elements", "number", 'mark', 'dt', 'price', 'is_end']
    def __init__(self):
        self.elements = []
        self.mark = None
        self.dt = None
        self.price = None
        self.is_end = False

    def update(self, fx: FX):
        """输入分型标记，更新笔标记

        :param fx: FX
        """
        if len(self.elements) == 0:
            self.elements.append(fx)
            self.mark = fx.mark
            self.dt = fx.dt
            self.price = fx.price
            return

        if not self.elements[-1].is_end:
            self.elements[-1] = fx
        else:
            self.elements.append(fx)

        # 一个新的分型进来，需要做两件事：
        # 1）如果与现有笔标记分型一样，判断是否要更新笔标记
        # 2）如果与现有笔标记分型不一样，判断当前笔标记是否确认成立
        if fx.mark == self.mark:
            if (self.mark == "g" and fx.price > self.price) or (self.mark == 'd' and fx.price < self.price):
                self.dt = fx.dt
                self.price = fx.price
        else:
            mid_fx = [x for x in self.elements if x.dt == self.dt]
            assert len(mid_fx) == 1
            mid_fx = mid_fx[0]

            fx_inside = [x for x in self.elements if x.dt >= self.dt]
            bars_inside = [y for x in fx_inside for y in x.elements]
            num_k = len(set([x['dt'] for x in bars_inside])) - len(mid_fx.elements) + 3
            if num_k >= 7:
                self.is_end = True

    def __repr__(self):
        return f"<BI - {self.mark} - {self.dt} - {self.price}>"


class XD:
    """线段"""
    def __init__(self):
        self.elements = []
        self.mark = None
        self.dt = None
        self.price = None
        self.is_end = False
        self.bi_g = []
        self.bi_d = []
        self.left = []
        self.right = []

    def make_seq(self):
        """计算标准特征序列

        :return: list of dict
        """
        if self.mark == 'd':
            direction = "up"
        elif self.mark == 'g':
            direction = "down"
        else:
            raise ValueError

        # assert self.right[0].mark == self.mark
        raw_seq = [{"dt": self.right[i].dt,
                    'high': max(self.right[i].price, self.right[i+1].price),
                    'low': min(self.right[i].price, self.right[i+1].price)}
                   for i in range(1, len(self.right), 2) if i <= len(self.right)-2]

        seq = []
        for row in raw_seq:
            if not seq:
                seq.append(row)
                continue
            last = seq[-1]
            cur_h, cur_l = row['high'], row['low']
            last_h, last_l = last['high'], last['low']

            # 左包含 or 右包含
            if (cur_h <= last_h and cur_l >= last_l) or (cur_h >= last_h and cur_l <= last_l):
                seq.pop(-1)
                # 有包含关系，按方向分别处理
                if direction == "up":
                    last_h = max(last_h, cur_h)
                    last_l = max(last_l, cur_l)
                elif direction == "down":
                    last_h = min(last_h, cur_h)
                    last_l = min(last_l, cur_l)
                else:
                    raise ValueError
                seq.append({"dt": row['dt'], "high": last_h, "low": last_l})
            else:
                seq.append(row)
        return seq

    def update(self, bi: BI):
        """输入笔标记，更新线段标记"""
        self.elements.append(bi)
        if bi.mark == 'd':
            self.bi_d.append(bi)
        elif bi.mark == 'g':
            self.bi_g.append(bi)
        else:
            raise ValueError

        if len(self.elements) < 6:
            return

        # 线段的顶必然大于相邻的两个顶；线段的底必然小于相邻的两个底
        if self.elements[0].mark == "g" and len(self.bi_d) >= 3:
            b1, b2, b3 = self.bi_d[-3:]
            if b1.price > b2.price < b3.price:
                if not self.mark or (self.mark == 'd' and self.price > b2.price):
                    self.mark = b2.mark
                    self.dt = b2.dt
                    self.price = b2.price
        
        if self.elements[0].mark == "d" and len(self.bi_g) >= 3:
            b1, b2, b3 = self.bi_g[-3:]
            if b1.price < b2.price > b3.price:
                if not self.mark or (self.mark == 'g' and self.price < b2.price):
                    self.mark = b2.mark
                    self.dt = b2.dt
                    self.price = b2.price

        # 判断线段标记是否有效
        if not self.mark:
            return

        self.left = [x for x in self.elements if x.dt <= self.dt]
        self.right = [x for x in self.elements if x.dt >= self.dt]

        if self.mark == "d" and len(self.right) >= 4 and len(self.left) >= 4:
            seq = self.make_seq()
            if self.right[1].price > self.left[-3].price:
                # 无缺口的处理
                max_g = max([x.price for x in self.right if x.mark == 'g'])
                if max_g > self.right[1].price:
                    self.is_end = True
            if len(seq) >= 3 and seq[-3]['high'] < seq[-2]['high'] > seq[-1]['high']:
                self.is_end = True

        if self.mark == 'g' and len(self.right) >= 4 and len(self.left) >= 4:
            seq = self.make_seq()
            if self.right[1].price < self.left[-3].price:
                # 无缺口的处理
                min_d = min([x.price for x in self.right if x.mark == 'd'])
                if min_d < self.right[1].price:
                    self.is_end = True
            if len(seq) >= 3 and seq[-3]['low'] > seq[-2]['low'] < seq[-1]['high']:
                self.is_end = True

    def __repr__(self):
        return f"<XD - {self.mark} - {self.dt} - {self.price}>"


class ZS:
    """中枢"""
    def __repr__(self):
        pass


class PZ:
    """盘整"""
    def __repr__(self):
        pass


class QS:
    """趋势"""
    def __repr__(self):
        pass


class KlineAnalyze(object):
    def __init__(self, kline, name="本级别", debug=False):
        """
        :param kline: list of dict or pd.DataFrame
            example kline:
            kline = [
                {'symbol': '600797.SH', 'dt': '2020-01-08 11:30:00', 'open': 10.72, 'close': 10.67, 'high': 10.76, 'low': 10.63, 'vol': 4464800.0},
                {'symbol': '600797.SH', 'dt': '2020-01-08 13:30:00', 'open': 10.66, 'close': 10.59, 'high': 10.66, 'low': 10.55, 'vol': 5004800.0},
                {'symbol': '600797.SH', 'dt': '2020-01-08 14:00:00', 'open': 10.58, 'close': 10.41, 'high': 10.6, 'low': 10.38, 'vol': 10650500.0},
                {'symbol': '600797.SH', 'dt': '2020-01-08 14:30:00', 'open': 10.42, 'close': 10.41, 'high': 10.48, 'low': 10.35, 'vol': 6610000.0},
                {'symbol': '600797.SH', 'dt': '2020-01-08 15:00:00', 'open': 10.42, 'close': 10.39, 'high': 10.48, 'low': 10.36, 'vol': 7160500.0}
            ]
        :param name: str
           级别名称，默认为 “本级别”
        """
        self.name = name
        if isinstance(kline, pd.DataFrame):
            columns = kline.columns.to_list()
            self.kline = [{k: v for k, v in zip(columns, row)} for row in kline.values]
        else:
            self.kline = kline
        self.debug = debug
        self.symbol = self.kline[0]['symbol']
        self.latest_price = self.kline[-1]['close']
        self.start_dt = self.kline[0]['dt']
        self.end_dt = self.kline[-1]['dt']
        self.fxs = []
        self.bis = []
        self.xds = []
        self.zss = []

        # 初始化
        for bar in self.kline:
            self.update(bar, save=False)

    def __repr__(self):
        return "<KlineAnalyze of %s@%s, from %s to %s>" % (self.symbol, self.name, self.start_dt, self.end_dt)

    @property
    def df(self):
        fx_list = {x.dt: {"fx_mark": x.mark, "fx": x.price} for x in self.fxs}
        bi_list = {x.dt: {"fx_mark": x.mark, "bi": x.price} for x in self.bis}
        xd_list = {x.dt: {"fx_mark": x.mark, "xd": x.price} for x in self.xds}

        results = []
        for k in self.kline:
            k['fx_mark'], k['fx'], k['bi'], k['xd'] = "o", None, None, None
            fx_ = fx_list.get(k['dt'], None)
            bi_ = bi_list.get(k['dt'], None)
            xd_ = xd_list.get(k['dt'], None)
            if fx_:
                k['fx_mark'] = fx_["fx_mark"]
                k['fx'] = fx_["fx"]

            if bi_:
                k['bi'] = bi_["bi"]

            if xd_:
                k['xd'] = xd_["xd"]

            results.append(k)
        return pd.DataFrame(results)

    def update(self, bar, save=True):
        """每次输入一根K线进行分析"""
        if save:
            self.kline.append(bar)

        if not self.fxs:
            fx = FX()
            self.fxs.append(fx)
        else:
            fx = self.fxs[-1]
            assert not fx.is_end, "最后一分型必须处于未完成状态"

        if not self.bis:
            bi = BI()
            self.bis.append(bi)
        else:
            bi = self.bis[-1]
            assert not bi.is_end, "最后一笔必须处于未完成状态"

        if not self.xds:
            xd = XD()
            self.xds.append(xd)
        else:
            xd = self.xds[-1]
            assert not xd.is_end, "最后一线段必须处于未完成状态"

        fx.update(bar)
        self.fxs[-1] = fx
        if fx.is_end:
            # 当一个分型确认结束，更新笔
            bi.update(fx)
            self.bis[-1] = bi

            fx_new = FX()
            for bar in fx.elements[-2:]:
                fx_new.update(bar)
            self.fxs.append(fx_new)

        if bi.is_end:
            # 当一个笔标记确认结束，更新线段
            xd.update(bi)
            self.xds[-1] = xd

            bi_new = BI()
            bi_new.update(bi.elements[-1])
            self.bis.append(bi_new)

        if xd.is_end:
            for i in range(5):
                xd_new = XD()
                for bi_ in xd.right:
                    xd_new.update(bi_)
                self.xds.append(xd_new)
                if xd_new.is_end:
                    print(f"{xd}确认结束，创建第{i}个线段标记 ...")
                    xd = xd_new
                    continue
                else:
                    break
