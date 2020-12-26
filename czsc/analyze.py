# coding: utf-8

import warnings

try:
    import talib as ta
except ImportError:
    ta_lib_hint = "没有安装 ta-lib !!! 请到 https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib " \
                  "下载对应版本安装，预计分析速度提升2倍"
    warnings.warn(ta_lib_hint)
    from .utils import ta
import pandas as pd
import numpy as np
from .utils.plot import ka_to_image


def has_gap(k1, k2, min_gap=0.002):
    """判断 k1, k2 之间是否有缺口"""
    assert k2['dt'] > k1['dt']
    if k1['high'] < k2['low'] * (1 - min_gap) \
            or k2['high'] < k1['low'] * (1 - min_gap):
        return True
    else:
        return False


def get_potential_xd(bi_points):
    """获取潜在线段标记点

    :param bi_points: list of dict
        笔标记点
    :return: list of dict
        潜在线段标记点
    """
    xd_p = []
    bi_d = [x for x in bi_points if x['fx_mark'] == 'd']
    bi_g = [x for x in bi_points if x['fx_mark'] == 'g']
    for i in range(1, len(bi_d) - 1):
        d1, d2, d3 = bi_d[i - 1: i + 2]
        if d1['bi'] > d2['bi'] < d3['bi']:
            xd_p.append(d2)
    for j in range(1, len(bi_g) - 1):
        g1, g2, g3 = bi_g[j - 1: j + 2]
        if g1['bi'] < g2['bi'] > g3['bi']:
            xd_p.append(g2)

    xd_p = sorted(xd_p, key=lambda x: x['dt'], reverse=False)
    return xd_p


class KlineAnalyze:
    def __init__(self, kline, name="本级别", bi_mode="new", max_count=1000,
                 use_xd=False, use_ta=True, ma_params=(5, 34, 120), verbose=False):
        """

        :param kline: list or pd.DataFrame
        :param name: str
        :param bi_mode: str
            new 新笔；old 老笔；默认值为 new
        :param max_count: int
            最大保存的K线数量
        :param use_xd: bool
            是否进行线段识别，对于以笔作为 f0 的交易策略而言，不进行线段识别可以加快分析速度
        :param use_ta: bool
            是否进行辅助技术指标的计算，不进行辅助技术指标的计算可以加快分析速度
        :param ma_params: tuple of int
            均线系统参数
        :param verbose: bool
        """
        self.name = name
        self.verbose = verbose
        self.bi_mode = bi_mode
        self.max_count = max_count
        self.use_xd = use_xd
        self.use_ta = use_ta
        self.ma_params = ma_params
        self.kline_raw = []  # 原始K线序列
        self.kline_new = []  # 去除包含关系的K线序列

        # 辅助技术指标
        self.ma = []
        self.macd = []

        # 分型、笔、线段
        self.fx_list = []
        self.bi_list = []
        self.xd_list = []

        # 根据输入K线初始化
        if isinstance(kline, pd.DataFrame):
            columns = kline.columns.to_list()
            self.kline_raw = [{k: v for k, v in zip(columns, row)} for row in kline.values]
        else:
            self.kline_raw = kline

        self.symbol = self.kline_raw[0]['symbol']
        self.start_dt = self.kline_raw[0]['dt']
        self.end_dt = self.kline_raw[-1]['dt']
        self.latest_price = self.kline_raw[-1]['close']

        self._update_kline_new()

        if self.use_ta:
            self._update_ta()

        self._update_fx_list()
        self._update_bi_list()

        if self.use_xd:
            self._update_xd_list()

    def _update_ta(self):
        """更新辅助技术指标"""
        if not self.ma:
            ma_temp = dict()
            close_ = np.array([x["close"] for x in self.kline_raw], dtype=np.double)
            for p in self.ma_params:
                ma_temp['ma%i' % p] = ta.SMA(close_, p)

            for i in range(len(self.kline_raw)):
                ma_ = {'ma%i' % p: ma_temp['ma%i' % p][i] for p in self.ma_params}
                ma_.update({"dt": self.kline_raw[i]['dt']})
                self.ma.append(ma_)
        else:
            ma_ = {'ma%i' % p: sum([x['close'] for x in self.kline_raw[-p:]]) / p
                   for p in self.ma_params}
            ma_.update({"dt": self.kline_raw[-1]['dt']})
            if self.verbose:
                print("ma new: %s" % str(ma_))

            if self.kline_raw[-2]['dt'] == self.ma[-1]['dt']:
                self.ma.append(ma_)
            else:
                self.ma[-1] = ma_

        assert self.ma[-2]['dt'] == self.kline_raw[-2]['dt']

        if not self.macd:
            close_ = np.array([x["close"] for x in self.kline_raw], dtype=np.double)
            # m1 is diff; m2 is dea; m3 is macd
            m1, m2, m3 = ta.MACD(close_, fastperiod=12, slowperiod=26, signalperiod=9)
            for i in range(len(self.kline_raw)):
                self.macd.append({
                    "dt": self.kline_raw[i]['dt'],
                    "diff": m1[i],
                    "dea": m2[i],
                    "macd": m3[i]
                })
        else:
            close_ = np.array([x["close"] for x in self.kline_raw[-200:]], dtype=np.double)
            # m1 is diff; m2 is dea; m3 is macd
            m1, m2, m3 = ta.MACD(close_, fastperiod=12, slowperiod=26, signalperiod=9)
            macd_ = {
                "dt": self.kline_raw[-1]['dt'],
                "diff": m1[-1],
                "dea": m2[-1],
                "macd": m3[-1]
            }
            if self.verbose:
                print("macd new: %s" % str(macd_))

            if self.kline_raw[-2]['dt'] == self.macd[-1]['dt']:
                self.macd.append(macd_)
            else:
                self.macd[-1] = macd_

        assert self.macd[-2]['dt'] == self.kline_raw[-2]['dt']

    def _update_kline_new(self):
        """更新去除包含关系的K线序列"""
        if len(self.kline_new) < 4:
            for x in self.kline_raw[:4]:
                self.kline_new.append(dict(x))

        # 新K线只会对最后一个去除包含关系K线的结果产生影响
        self.kline_new = self.kline_new[:-2]
        if len(self.kline_new) <= 4:
            right_k = [x for x in self.kline_raw if x['dt'] > self.kline_new[-1]['dt']]
        else:
            right_k = [x for x in self.kline_raw[-100:] if x['dt'] > self.kline_new[-1]['dt']]

        if len(right_k) == 0:
            return

        for k in right_k:
            k = dict(k)
            last_kn = self.kline_new[-1]
            if self.kline_new[-1]['high'] > self.kline_new[-2]['high']:
                direction = "up"
            else:
                direction = "down"

            # 判断是否存在包含关系
            cur_h, cur_l = k['high'], k['low']
            last_h, last_l = last_kn['high'], last_kn['low']
            if (cur_h <= last_h and cur_l >= last_l) or (cur_h >= last_h and cur_l <= last_l):
                self.kline_new.pop(-1)
                # 有包含关系，按方向分别处理
                if direction == "up":
                    last_h = max(last_h, cur_h)
                    last_l = max(last_l, cur_l)
                elif direction == "down":
                    last_h = min(last_h, cur_h)
                    last_l = min(last_l, cur_l)
                else:
                    raise ValueError

                k.update({"high": last_h, "low": last_l})
                # 保留红绿不变
                if k['open'] >= k['close']:
                    k.update({"open": last_h, "close": last_l})
                else:
                    k.update({"open": last_l, "close": last_h})
            self.kline_new.append(k)

    def _update_fx_list(self):
        """更新分型序列

        对于底分型，第三元素收在第一元素的一半以上为强势，否则为弱势；
        对于顶分型，第三元素收在第一元素的一半以下为强势，否则为弱势；

        分型标记对象样例：
         {'dt': Timestamp('2020-11-26 00:00:00'),
          'fx_mark': 'd',       # 可选值：d / g
          'fx': 138.0,
          'start_dt': Timestamp('2020-11-25 00:00:00'),
          'end_dt': Timestamp('2020-11-27 00:00:00'),
          'fx_power': 'strong', # 可选值：strong / weak
          'fx_high': 144.87,
          'fx_low': 138.0}
        """
        if len(self.kline_new) < 3:
            return

        self.fx_list = self.fx_list[:-1]
        if len(self.fx_list) == 0:
            kn = self.kline_new
        else:
            kn = [x for x in self.kline_new[-100:] if x['dt'] >= self.fx_list[-1]['dt']]

        i = 1
        while i <= len(kn) - 2:
            k1, k2, k3 = kn[i - 1: i + 2]
            k1_mid = (k1['high'] - k1['low']) / 2 + k1['low']
            if k1['high'] < k2['high'] > k3['high']:
                if self.verbose:
                    print("顶分型：{} - {} - {}".format(k1['dt'], k2['dt'], k3['dt']))
                fx = {
                    "dt": k2['dt'],
                    "fx_mark": "g",
                    "fx": k2['high'],
                    "start_dt": k1['dt'],
                    "end_dt": k3['dt'],
                    'fx_power': 'strong' if k3['close'] < k1_mid else 'weak',
                    "fx_high": k2['high'],
                    # "fx_low": k2['low'] if has_gap(k1, k2) else k1['low'],
                    "fx_low": k1['low'],
                }
                self.fx_list.append(fx)

            elif k1['low'] > k2['low'] < k3['low']:
                if self.verbose:
                    print("底分型：{} - {} - {}".format(k1['dt'], k2['dt'], k3['dt']))
                fx = {
                    "dt": k2['dt'],
                    "fx_mark": "d",
                    "fx": k2['low'],
                    "start_dt": k1['dt'],
                    "end_dt": k3['dt'],
                    'fx_power': 'strong' if k3['close'] > k1_mid else 'weak',
                    # "fx_high": k2['high'] if has_gap(k1, k2) else k1['high'],
                    "fx_high": k1['high'],
                    "fx_low": k2['low'],
                }
                self.fx_list.append(fx)

            else:
                if self.verbose:
                    print("无分型：{} - {} - {}".format(k1['dt'], k2['dt'], k3['dt']))
            i += 1

    def _update_bi_list(self):
        """更新笔序列

        笔标记对象样例：
         {'dt': Timestamp('2020-11-26 00:00:00'),
          'fx_mark': 'd',
          'start_dt': Timestamp('2020-11-25 00:00:00'),
          'end_dt': Timestamp('2020-11-27 00:00:00'),
          'fx_high': 144.87,
          'fx_low': 138.0,
          'bi': 138.0}

         {'dt': Timestamp('2020-12-02 00:00:00'),
          'fx_mark': 'g',
          'start_dt': Timestamp('2020-12-01 00:00:00'),
          'end_dt': Timestamp('2020-12-03 00:00:00'),
          'fx_high': 150.67,
          'fx_low': 141.6,
          'bi': 150.67}
        """
        if len(self.fx_list) < 2:
            return

        self.bi_list = self.bi_list[:-2]
        if len(self.bi_list) == 0:
            for fx in self.fx_list[:2]:
                bi = dict(fx)
                bi['bi'] = bi.pop('fx')
                self.bi_list.append(bi)

        if len(self.bi_list) <= 2:
            right_fx = [x for x in self.fx_list if x['dt'] > self.bi_list[-1]['dt']]
            if self.bi_mode == "old":
                right_kn = [x for x in self.kline_new if x['dt'] >= self.bi_list[-1]['dt']]
            elif self.bi_mode == 'new':
                right_kn = [x for x in self.kline_raw if x['dt'] >= self.bi_list[-1]['dt']]
            else:
                raise ValueError
        else:
            right_fx = [x for x in self.fx_list[-50:] if x['dt'] > self.bi_list[-1]['dt']]
            if self.bi_mode == "old":
                right_kn = [x for x in self.kline_new[-300:] if x['dt'] >= self.bi_list[-1]['dt']]
            elif self.bi_mode == 'new':
                right_kn = [x for x in self.kline_raw[-300:] if x['dt'] >= self.bi_list[-1]['dt']]
            else:
                raise ValueError

        for fx in right_fx:
            last_bi = self.bi_list[-1]
            bi = dict(fx)
            bi['bi'] = bi.pop('fx')
            if last_bi['fx_mark'] == fx['fx_mark']:
                if (last_bi['fx_mark'] == 'g' and last_bi['bi'] < bi['bi']) \
                        or (last_bi['fx_mark'] == 'd' and last_bi['bi'] > bi['bi']):
                    if self.verbose:
                        print("笔标记移动：from {} to {}".format(self.bi_list[-1], bi))
                    self.bi_list[-1] = bi
            else:
                kn_inside = [x for x in right_kn if last_bi['end_dt'] < x['dt'] < bi['start_dt']]
                if len(kn_inside) <= 0:
                    continue

                # 确保相邻两个顶底之间不存在包含关系
                if (last_bi['fx_mark'] == 'g' and bi['fx_low'] < last_bi['fx_low']
                    and bi['fx_high'] < last_bi['fx_high']) or \
                        (last_bi['fx_mark'] == 'd' and bi['fx_high'] > last_bi['fx_high']
                         and bi['fx_low'] > last_bi['fx_low']):
                    if self.verbose:
                        print("新增笔标记：{}".format(bi))
                    self.bi_list.append(bi)

    def _update_xd_list(self):
        """更新线段序列

        线段标记对象样例：
         {'dt': Timestamp('2020-07-09 00:00:00'),
          'fx_mark': 'g',
          'start_dt': Timestamp('2020-07-08 00:00:00'),
          'end_dt': Timestamp('2020-07-14 00:00:00'),
          'fx_high': 187.99,
          'fx_low': 163.12,
          'xd': 187.99}

         {'dt': Timestamp('2020-11-02 00:00:00'),
          'fx_mark': 'd',
          'start_dt': Timestamp('2020-10-29 00:00:00'),
          'end_dt': Timestamp('2020-11-03 00:00:00'),
          'fx_high': 142.38,
          'fx_low': 135.0,
          'xd': 135.0}
        """
        if len(self.bi_list) < 4:
            return

        self.xd_list = []
        if len(self.xd_list) == 0:
            for i in range(3):
                xd = dict(self.bi_list[i])
                xd['xd'] = xd.pop('bi')
                self.xd_list.append(xd)

        right_bi = [x for x in self.bi_list if x['dt'] >= self.xd_list[-1]['dt']]

        xd_p = get_potential_xd(right_bi)
        for xp in xd_p:
            xd = dict(xp)
            xd['xd'] = xd.pop('bi')
            last_xd = self.xd_list[-1]
            if last_xd['fx_mark'] == xd['fx_mark']:
                if (last_xd['fx_mark'] == 'd' and last_xd['xd'] > xd['xd']) \
                        or (last_xd['fx_mark'] == 'g' and last_xd['xd'] < xd['xd']):
                    if self.verbose:
                        print("更新线段标记：from {} to {}".format(last_xd, xd))
                    self.xd_list[-1] = xd
            else:
                if (last_xd['fx_mark'] == 'd' and last_xd['xd'] > xd['xd']) \
                        or (last_xd['fx_mark'] == 'g' and last_xd['xd'] < xd['xd']):
                    continue

                bi_inside = [x for x in right_bi if last_xd['dt'] <= x['dt'] <= xd['dt']]
                if len(bi_inside) < 4:
                    if self.verbose:
                        print("{} - {} 之间笔标记数量少于4，跳过".format(last_xd['dt'], xd['dt']))
                    continue
                else:
                    self.xd_list.append(xd)

    def update(self, k):
        """更新分析结果

        :param k: dict
            单根K线对象，样例如下
            {'symbol': '000001.SH',
             'dt': Timestamp('2020-07-16 15:00:00'),
             'open': 3356.11,
             'close': 3210.1,
             'high': 3373.53,
             'low': 3209.76,
             'vol': 486366915.0}
        """
        if self.verbose:
            print("=" * 100)
            print("输入新K线：{}".format(k))
        if not self.kline_raw or k['open'] != self.kline_raw[-1]['open']:
            self.kline_raw.append(k)
        else:
            if self.verbose:
                print("输入K线处于未完成状态，更新：replace {} with {}".format(self.kline_raw[-1], k))
            self.kline_raw[-1] = k

        if self.use_ta:
            self._update_ta()

        self._update_kline_new()
        self._update_fx_list()
        self._update_bi_list()

        if self.use_xd:
            self._update_xd_list()

        self.end_dt = self.kline_raw[-1]['dt']
        self.latest_price = self.kline_raw[-1]['close']

        if len(self.kline_raw) > self.max_count:
            last_dt = self.kline_raw[-self.max_count:][0]['dt']
            self.kline_raw = self.kline_raw[-self.max_count:]
            self.kline_new = self.kline_new[-self.max_count:]
            self.ma = [x for x in self.ma if x['dt'] > last_dt]
            self.macd = [x for x in self.macd if x['dt'] > last_dt]
            self.fx_list = [x for x in self.fx_list if x['dt'] > last_dt]
            self.bi_list = [x for x in self.bi_list if x['dt'] > last_dt]
            if self.use_xd:
                self.xd_list = [x for x in self.xd_list if x['dt'] > last_dt]

        if self.verbose:
            print("更新结束\n\n")

    def to_df(self, ma_params=(5, 20), use_macd=False, max_count=1000, mode="raw"):
        """整理成 df 输出

        :param ma_params: tuple of int
            均线系统参数
        :param use_macd: bool
        :param max_count: int
        :param mode: str
            使用K线类型， raw = 原始K线，new = 去除包含关系的K线
        :return: pd.DataFrame
        """
        if mode == "raw":
            bars = self.kline_raw[-max_count:]
        elif mode == "new":
            bars = self.kline_raw[-max_count:]
        else:
            raise ValueError

        fx_list = {x["dt"]: {"fx_mark": x["fx_mark"], "fx": x['fx']} for x in self.fx_list[-(max_count // 2):]}
        bi_list = {x["dt"]: {"fx_mark": x["fx_mark"], "bi": x['bi']} for x in self.bi_list[-(max_count // 4):]}
        xd_list = {x["dt"]: {"fx_mark": x["fx_mark"], "xd": x['xd']} for x in self.xd_list[-(max_count // 8):]}
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
        for p in ma_params:
            df.loc[:, "ma{}".format(p)] = ta.SMA(df.close.values, p)
        if use_macd:
            diff, dea, macd = ta.MACD(df.close.values)
            df.loc[:, "diff"] = diff
            df.loc[:, "dea"] = diff
            df.loc[:, "macd"] = diff
        return df

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
        ka_to_image(self, file_image=file_image, mav=mav, max_k_count=max_k_count, dpi=dpi)

    def calculate_macd_power(self, start_dt, end_dt, mode='bi', direction="up"):
        """用 MACD 计算走势段（start_dt ~ end_dt）的力度

        :param start_dt: datetime
            走势开始时间
        :param end_dt: datetime
            走势结束时间
        :param mode: str
            分段走势类型，默认值为 bi，可选值 ['bi', 'xd']，分别表示笔分段走势和线段分段走势
        :param direction: str
            线段分段走势计算力度需要指明方向，可选值 ['up', 'down']
        :return: float
            走势力度
        """
        if not self.use_ta:
            warnings.warn("没有进行辅助技术指标的计算，macd_power 返回 0")
            return 0

        fd_macd = [x for x in self.macd if end_dt >= x['dt'] >= start_dt]

        if mode == 'bi':
            power = sum([abs(x['macd']) for x in fd_macd])
        elif mode == 'xd':
            if direction == 'up':
                power = sum([abs(x['macd']) for x in fd_macd if x['macd'] > 0])
            elif direction == 'down':
                power = sum([abs(x['macd']) for x in fd_macd if x['macd'] < 0])
            else:
                raise ValueError
        else:
            raise ValueError
        return power

    def calculate_vol_power(self, start_dt, end_dt):
        """用 VOL 计算走势段（start_dt ~ end_dt）的力度

        :param start_dt: datetime
            走势开始时间
        :param end_dt: datetime
            走势结束时间
        :return: float
            走势力度
        """
        fd_vol = [x for x in self.kline_raw if end_dt >= x['dt'] >= start_dt]
        power = sum([x['vol'] for x in fd_vol])
        return int(power)

    def get_bi_fd(self, n=6):
        """假定本级别笔为次级别线段，进行走势分段

        fd 为 dict 对象，表示一段走势，可以是笔、线段，样例如下：

        fd = {
            "start_dt": "",
            "end_dt": "",
            "start_mark": p1,        # 笔开始标记
            "end_mark": p2,          # 笔结束标记
            "price_power": 0,        # 走势段价差
            "vol_power": 0,          # 成交量面积（柱子和）
            "length": 0,             # 笔长度，即笔内部的原始K线数量
            "direction": "up",
            "high": 0,
            "low": 0,
            "mode": "bi"
        }

        :param n:
        :return: list of dict
        """
        points = self.bi_list[-(n + 1):]
        assert len(points) == n + 1

        res = []
        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i + 1]
            direction = "up" if p1["bi"] < p2["bi"] else "down"
            k_inside = [x for x in self.kline_raw if p2['dt'] >= x['dt'] >= p1['dt']]
            vol_power = int(sum([x['vol'] for x in k_inside]))
            res.append({
                "start_dt": p1['dt'],
                "end_dt": p2['dt'],
                "start_mark": p1,
                "end_mark": p2,
                "price_power": abs(p1['bi'] - p2['bi']),
                "vol_power": vol_power,
                "length": len(k_inside),
                "direction": direction,
                "high": max(p1["bi"], p2["bi"]),
                "low": min(p1["bi"], p2["bi"]),
                "mode": "bi"
            })
        return res
