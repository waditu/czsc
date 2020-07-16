# coding: utf-8
"""
缠论对象化
"""

import pandas as pd
from .utils import plot_ka, plot_kline
from .ta import macd, ma, boll

def is_bei_chi(ka, zs1, zs2, mode="bi", adjust=0.9):
    """判断 zs1 对 zs2 是否有背驰
    注意：力度的比较，并没有要求两段走势方向一致；但是如果两段走势之间存在包含关系，这样的力度比较是没有意义的。
    :param ka: KlineAnalyze
        缠论的分析结果，即去除包含关系后，识别出分型、笔、线段的K线
    :param zs1: dict
        用于比较的走势，通常是最近的走势，示例如下：
        zs1 = {"start_dt": "2020-02-20 11:30:00", "end_dt": "2020-02-20 14:30:00", "direction": "up"}
    :param zs2: dict
        被比较的走势，通常是较前的走势，示例如下：
        zs2 = {"start_dt": "2020-02-21 11:30:00", "end_dt": "2020-02-21 14:30:00", "direction": "down"}
    :param mode: str
        default `bi`, optional value [`xd`, `bi`]
        xd  判断两个线段之间是否存在背驰
        bi  判断两笔之间是否存在背驰
    :param adjust: float
        调整 zs2 的力度，建议设置范围在 0.6 ~ 1.0 之间，默认设置为 0.9；
        其作用是确保 zs1 相比于 zs2 的力度足够小。
    :return:
    """
    assert zs1["start_dt"] > zs2["end_dt"], "zs1 必须是最近的走势，用于比较；zs2 必须是较前的走势，被比较。"
    assert zs1["start_dt"] < zs1["end_dt"], "走势的时间区间定义错误，必须满足 start_dt < end_dt"
    assert zs2["start_dt"] < zs2["end_dt"], "走势的时间区间定义错误，必须满足 start_dt < end_dt"

    df = ka.to_df(ma_params=(5,), use_macd=True, use_boll=False)
    k1 = df[(df['dt'] >= zs1["start_dt"]) & (df['dt'] <= zs1["end_dt"])]
    k2 = df[(df['dt'] >= zs2["start_dt"]) & (df['dt'] <= zs2["end_dt"])]

    bc = False
    if mode == 'bi':
        macd_sum1 = sum([abs(x) for x in k1.macd])
        macd_sum2 = sum([abs(x) for x in k2.macd])
        # print("bi: ", macd_sum1, macd_sum2)
        if macd_sum1 < macd_sum2 * adjust:
            bc = True

    elif mode == 'xd':
        assert zs1['direction'] in ['down', 'up'], "走势的 direction 定义错误，可取值为 up 或 down"
        assert zs2['direction'] in ['down', 'up'], "走势的 direction 定义错误，可取值为 up 或 down"

        if zs1['direction'] == "down":
            macd_sum1 = sum([abs(x) for x in k1.macd if x < 0])
        else:
            macd_sum1 = sum([abs(x) for x in k1.macd if x > 0])

        if zs2['direction'] == "down":
            macd_sum2 = sum([abs(x) for x in k2.macd if x < 0])
        else:
            macd_sum2 = sum([abs(x) for x in k2.macd if x > 0])

        # print("xd: ", macd_sum1, macd_sum2)
        if macd_sum1 < macd_sum2 * adjust:
            bc = True

    else:
        raise ValueError("mode value error")

    return bc

class FX:
    """分型"""

    # __slots__ = ["elements", "number", 'mark', 'dt', 'price', 'is_end']

    def __init__(self):
        self.elements = []
        self.mark = None
        self.dt = None
        self.price = None
        self.is_end = False
        self.fx_g = 0
        self.fx_d = 0

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
            {'symbol': '600797.SH', 'dt': '2020-01-08 11:30:00', 'open': 10.72, 'close': 10.67, 'high': 10.76, 'low': 10.63}
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
                self.fx_g = k2['high']
                self.fx_d = k1['low']

            if k1['low'] > k2['low'] < k3['low']:
                self.mark = "d"
                self.price = k2['low']
                self.dt = k2['dt']
                self.is_end = True
                self.fx_g = k1['high']
                self.fx_d = k2['low']

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
            if num_k >= 6:
                if (fx.mark == "d" and fx.fx_g < mid_fx.fx_d) or (fx.mark == "g" and fx.fx_d > mid_fx.fx_g):
                    self.is_end = True

    def __repr__(self):
        return f"<BI - {self.mark} - {self.dt} - {self.price}>"


class XD:
    """线段"""

    def __init__(self):
        self.elements = []
        self.bi_g = []
        self.bi_d = []
        self.mark = None
        self.dt = None
        self.price = None
        self.is_end = False
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
                    'high': max(self.right[i].price, self.right[i + 1].price),
                    'low': min(self.right[i].price, self.right[i + 1].price)}
                   for i in range(1, len(self.right), 2) if i <= len(self.right) - 2]

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

    def __init__(self):
        # 组成中枢的元件：笔标记、线段标记、走势标记
        self.elements = []
        self.ZD = 0
        self.ZG = 0
        self.D = None
        self.G = None
        self.DD = None
        self.GG = None
        self.third_buy = None
        self.third_sell = None
        self.is_end = False
        self.start_dt = None
        self.end_dt = None
        self.left = []
        self.right = []
        self.inside = []

    def __repr__(self):
        return f"<ZS({self.ZD}~{self.ZG})>"

    def update(self, mark):
        self.elements.append(mark)
        if len(self.elements) < 5:
            return

        if not self.ZD and not self.ZG:
            zd = max([x.price for x in self.elements[-4:] if x.mark == "d"])
            zg = min([x.price for x in self.elements[-4:] if x.mark == "g"])
            if zg > zd:
                self.start_dt = self.elements[-4].dt
                self.ZD = zd
                self.ZG = zg
            else:
                return
        else:
            if mark.mark == 'g' and mark.price < self.ZD:
                self.end_dt = self.elements[-3].dt
                self.third_sell = mark
                self.is_end = True

            if mark.mark == 'd' and mark.price > self.ZG:
                self.end_dt = self.elements[-3].dt
                self.third_buy = mark
                self.is_end = True

            # 限制中枢延伸数量
            mark_n = len([x for x in self.elements if x.dt >= self.start_dt])
            if mark_n > 9:
                self.end_dt = self.elements[-3].dt
                self.is_end = True

        if self.is_end:
            self.left = [x for x in self.elements if x.dt <= self.start_dt]
            self.right = [x for x in self.elements if x.dt >= self.end_dt]
            self.inside = [x for x in self.elements if self.start_dt <= x.dt <= self.end_dt]


class FD:
    """走势分段：趋势 / 盘整"""

    def __repr__(self):
        pass


class KlineAnalyze(object):
    def __init__(self, kline, name="本级别", debug=False):
        """
        :param kline: list of dict or pd.DataFrame
            example kline:
            kline = [
                {'symbol': '600797.SH', 'dt': '2020-01-08 11:30:00', 'open': 10.72, 'close': 10.67, 'high': 10.76, 'low': 10.63},
                {'symbol': '600797.SH', 'dt': '2020-01-08 13:30:00', 'open': 10.66, 'close': 10.59, 'high': 10.66, 'low': 10.55},
                {'symbol': '600797.SH', 'dt': '2020-01-08 14:00:00', 'open': 10.58, 'close': 10.41, 'high': 10.6, 'low': 10.38},
                {'symbol': '600797.SH', 'dt': '2020-01-08 14:30:00', 'open': 10.42, 'close': 10.41, 'high': 10.48, 'low': 10.35},
                {'symbol': '600797.SH', 'dt': '2020-01-08 15:00:00', 'open': 10.42, 'close': 10.39, 'high': 10.48, 'low': 10.36}
            ]
        :param name: str
           级别名称，默认为 “本级别”
        """
        if isinstance(kline, pd.DataFrame):
            columns = kline.columns.to_list()
            bars = [{k: v for k, v in zip(columns, row)} for row in kline.values]
        else:
            bars = kline

        self.name = name
        self.kline = []
        self.debug = debug
        self.symbol = bars[0]['symbol']
        self.latest_price = bars[-1]['close']
        self.start_dt = bars[0]['dt']
        self.end_dt = bars[-1]['dt']
        self.fxs = []
        self.bis = []
        self.xds = []
        self.zss = []
        for bar in bars:
            self.update(bar)

    def __repr__(self):
        return "<KlineAnalyze of %s@%s, from %s to %s>" % (self.symbol, self.name, self.start_dt, self.end_dt)

    def to_df(self, ma_params=(5, 20), use_macd=True, use_boll=False):
        bars = self.kline
        fx_list = {x.dt: {"fx_mark": x.mark, "fx": x.price} for x in self.fxs if x.is_end}
        bi_list = {x.dt: {"fx_mark": x.mark, "bi": x.price} for x in self.bis if x.is_end}
        xd_list = {x.dt: {"fx_mark": x.mark, "xd": x.price} for x in self.xds if x.is_end}
        results = []
        for k in bars:
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
        df = pd.DataFrame(results)
        df = ma(df, ma_params)
        if use_macd:
            df = macd(df)
        if use_boll:
            df = boll(df)
        return df

    def update(self, bar):
        """每次输入一根K线进行分析"""
        self.latest_price = bar['close']

        if bar['dt'] != self.end_dt:
            self.end_dt = bar['dt']

        if self.kline:
            if bar['open'] == self.kline[-1]['open'] or bar['dt'] == self.kline[-1]['dt']:
                self.kline.pop(-1)
                self.kline.append(bar)
            else:
                self.kline.append(bar)
        else:
            self.kline.append(bar)

        if not self.fxs:
            fx = FX()
            self.fxs.append(fx)
        else:
            fx = self.fxs[-1]
            assert not fx.is_end, f"最后一分型必须处于未完成状态：{fx}"

        if not self.bis:
            bi = BI()
            self.bis.append(bi)
        else:
            bi = self.bis[-1]
            assert not bi.is_end, f"最后一笔必须处于未完成状态：{bi}"

        if not self.xds:
            xd = XD()
            self.xds.append(xd)
        else:
            xd = self.xds[-1]
            assert not xd.is_end, f"最后一线段必须处于未完成状态：{xd}"

        if not self.zss:
            zs = ZS()
            self.zss.append(zs)
        else:
            zs = self.zss[-1]
            assert not zs.is_end, "最后一线段必须处于未完成状态"

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
            zs.update(xd)
            for i in range(5):
                xd_new = XD()
                for bi_ in xd.right:
                    xd_new.update(bi_)
                self.xds.append(xd_new)
                if xd_new.is_end:
                    xd = xd_new
                    zs.update(xd)
                    continue
                else:
                    break
            self.zss[-1] = zs

        if zs.is_end:
            zs_new = ZS()
            zs_new.update(zs.elements[-1])
            self.zss.append(zs_new)

    def to_html(self, file_html="kline.html", width="1400px", height="680px"):
        """保存成 html

        :param file_html: str
            html文件名
        :param width: str
            页面宽度
        :param height: str
            页面高度
        :return:
        """
        plot_kline(self, file_html=file_html, width=width, height=height)

    def to_image(self, file_image, mav=(5, 20, 120, 250), max_k_count=1000, dpi=50):
        """保存成图片

        :param file_image: str
            图片名称，支持 jpg/png/svg 格式，注意后缀
        :param mav: tuple of int
            均线系统参数
        :param max_k_count: int
            设定最大K线数量，这个值越大，生成的图片越长
        :param dpi: int
            图片分辨率
        :return:
        """
        plot_ka(self, file_image=file_image, mav=mav, max_k_count=max_k_count, dpi=dpi)
