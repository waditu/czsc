# coding: utf-8

import pandas as pd
from czsc.ta import ma, macd, boll
from czsc.utils import plot_ka, plot_kline


class KlineAnalyze:
    def __init__(self, name="本级别", verbose=True):
        self.name = name
        self.verbose = verbose
        self.symbol = None
        self.latest_price = None
        self.start_dt = None
        self.end_dt = None
        self.kline_raw = []     # 原始K线序列
        self.kline_new = []     # 去除包含关系的K线序列

        # 分型、笔、线段
        self.fx_list = []
        self.bi_list = []
        self.xd_list = []

        # 中枢识别结果
        self.zs_list_l1 = []
        self.zs_list_l2 = []
        self.zs_list_l3 = []

        # 走势分段结果
        self.fd_list_l1 = []
        self.fd_list_l2 = []
        self.fd_list_l3 = []

    def _update_kline_new(self):
        """更新去除包含关系的K线序列

        原始K线序列样例：
         {'symbol': '000001.SH',
          'dt': Timestamp('2020-07-16 15:00:00'),
          'open': 3356.11,
          'close': 3210.1,
          'high': 3373.53,
          'low': 3209.76,
          'vol': 486366915.0,
          'is_end': True}

        无包含关系K线对象样例：
         {'symbol': '000001.SH',
          'dt': Timestamp('2020-07-16 15:00:00'),
          'open': 3356.11,
          'close': 3210.1,
          'high': 3373.53,
          'low': 3209.76,
          'vol': 486366915.0,
          'is_end': True,
          'direction': 'down'}
        """
        if len(self.kline_new) < 3:
            last_k = self.kline_raw[-1]
            new_k = dict(last_k)
            new_k['direction'] = "up"
            self.kline_new.append(new_k)
            return

        # 新K线只会对最后一个去除包含关系K线的结果产生影响
        self.kline_new = self.kline_new[:-1]
        right_k = [x for x in self.kline_raw if x['dt'] > self.kline_new[-1]['dt']]

        for k in right_k:
            k = dict(k)
            last_kn = self.kline_new[-1]
            direction = last_kn['direction']

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

            # 加上 direction 信息
            if k['high'] > self.kline_new[-1]['high']:
                k['direction'] = "up"
            elif k['low'] < self.kline_new[-1]["low"]:
                k['direction'] = "down"
            else:
                raise ValueError
            self.kline_new.append(k)

            if self.verbose:
                print(f"原始序列长度：{len(self.kline_raw)}；去除包含关系之后的序列长度：{len(self.kline_new)}")

    def _update_fx_list(self):
        """更新分型序列

        分型对象样例：

         {'dt': Timestamp('2020-06-29 15:00:00'),
          'fx_mark': 'd',
          'fx': 2951.77,
          'fx_high': 2977.91,
          'fx_low': 2951.77}

         {'dt': Timestamp('2020-07-09 15:00:00'),
          'fx_mark': 'g',
          'fx': 3456.97,
          'fx_high': 3456.97,
          'fx_low': 3366.08}
        """
        if len(self.kline_new) < 3:
            return

        self.fx_list = self.fx_list[:-1]
        if len(self.fx_list) == 0:
            kn = self.kline_new
        else:
            kn = [x for x in self.kline_new if x['dt'] >= self.fx_list[-1]['dt']]

        i = 1
        while i <= len(kn)-2:
            k1, k2, k3 = kn[i-1: i+2]

            if k1['high'] < k2['high'] > k3['high']:
                if self.verbose:
                    print(f"顶分型：{k1['dt']} - {k2['dt']} - {k3['dt']}")
                fx = {
                    "dt": k2['dt'],
                    "fx_mark": "g",
                    "fx": k2['high'],
                    "fx_high": k2['high'],
                    "fx_low": max(k1['low'], k3['low']),
                    # "left": [x for x in kn if x['dt'] <= k2['dt']]
                }
                self.fx_list.append(fx)

            elif k1['low'] > k2['low'] < k3['low']:
                if self.verbose:
                    print(f"底分型：{k1['dt']} - {k2['dt']} - {k3['dt']}")
                fx = {
                    "dt": k2['dt'],
                    "fx_mark": "d",
                    "fx": k2['low'],
                    "fx_high": min(k1['high'], k2['high']),
                    "fx_low": k2['low'],
                    # "left": [x for x in kn if x['dt'] <= k2['dt']]
                }
                self.fx_list.append(fx)

            else:
                if self.verbose:
                    print(f"无分型：{k1['dt']} - {k2['dt']} - {k3['dt']}")
            i += 1

    def _update_bi_list(self):
        """更新笔序列

        笔标记样例：
         {'dt': Timestamp('2020-05-25 15:00:00'),
          'fx_mark': 'd',
          'fx_high': 2821.5,
          'fx_low': 2802.47,
          'bi': 2802.47}

         {'dt': Timestamp('2020-07-09 15:00:00'),
          'fx_mark': 'g',
          'fx_high': 3456.97,
          'fx_low': 3366.08,
          'bi': 3456.97}

        """
        if len(self.fx_list) < 2:
            return

        if len(self.bi_list) == 0:
            for fx in self.fx_list:
                bi = dict(fx)
                bi['bi'] = bi.pop('fx')
                self.bi_list.append(bi)

        self.bi_list = self.bi_list[:-1]
        if len(self.bi_list) == 0:
            return

        right_fx = [x for x in self.fx_list if x['dt'] > self.bi_list[-1]['dt']]
        right_kn = [x for x in self.kline_new if x['dt'] >= self.bi_list[-1]['dt']]

        for fx in right_fx:
            last_bi = self.bi_list[-1]
            bi = dict(fx)
            bi['bi'] = bi.pop('fx')
            if last_bi['fx_mark'] == fx['fx_mark']:
                if (last_bi['fx_mark'] == 'g' and last_bi['bi'] < bi['bi']) \
                        or (last_bi['fx_mark'] == 'd' and last_bi['bi'] > bi['bi']):
                    if self.verbose:
                        print(f"笔标记移动：from {self.bi_list[-1]} to {bi}")
                    self.bi_list[-1] = bi
            else:
                kn_inside = [x for x in right_kn if last_bi['dt'] <= x['dt'] <= bi['dt']]
                if len(kn_inside) >= 5:
                    # 确保相邻两个顶底之间不存在包含关系
                    if (last_bi['fx_mark'] == 'g' and bi['fx_high'] < last_bi['fx_low']) or \
                            (last_bi['fx_mark'] == 'd' and bi['fx_low'] > last_bi['fx_high']):
                        if self.verbose:
                            print(f"新增笔标记：{bi}")
                        self.bi_list.append(bi)

    def _update_xd_list(self):
        """更新线段序列"""
        if len(self.bi_list) < 4:
            return

        if len(self.xd_list) == 0:
            for i in range(3):
                xd = dict(self.xd_list[i])
                xd['xd'] = xd.pop('bi')
                self.xd_list.append(xd)

        self.xd_list = self.xd_list[:-2]
        if len(self.xd_list) == 0:
            return

        right_bi = [x for x in self.bi_list if x['dt'] > self.xd_list[-1]['dt']]
        for bi in right_bi:
            last_xd = self.xd_list[-1]
            xd = dict(bi)
            xd['xd'] = xd.pop('bi')

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
             'vol': 486366915.0,
             'is_end': True}
        """
        if k['is_end']:
            self.kline_raw.append(k)
        else:
            if self.verbose:
                print(f"输入K线处于未完成状态，更新：replace {self.kline_raw[-1]} with {k}")
            self.kline_raw[-1] = k

        self.symbol = k['symbol']
        self.end_dt = k['dt']
        self.latest_price = k['close']
        self.start_dt = self.kline_raw[0]['dt']

        self._update_kline_new()
        self._update_fx_list()
        self._update_bi_list()
        # self._update_xd_list()

    def to_df(self, ma_params=(5, 20), use_macd=True, use_boll=False, max_count=5000):
        """整理成 df 输出

        :param ma_params: tuple of int
            均线系统参数
        :param use_macd: bool
        :param use_boll: bool
        :param max_count: int
        :return: pd.DataFrame
        """
        bars = self.kline_raw[-max_count:]
        fx_list = {x["dt"]: {"fx_mark": x["fx_mark"], "fx": x['fx']} for x in self.fx_list}
        bi_list = {x["dt"]: {"fx_mark": x["fx_mark"], "bi": x['bi']} for x in self.bi_list}
        xd_list = {x["dt"]: {"fx_mark": x["fx_mark"], "xd": x['xd']} for x in self.xd_list}
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


