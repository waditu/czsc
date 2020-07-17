# coding: utf-8
import traceback
import pandas as pd
from functools import lru_cache

from .ta import macd, ma, boll
from .utils import plot_kline, plot_ka


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

    df = create_df(ka, ma_params=(5,), use_macd=True, use_boll=False)
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


def get_ka_feature(ka):
    """获取 KlineAnalyze 的特征

    这只是一个样例，想做多因子的，可以发挥自己的想法，大幅扩展特征数量。
    """
    feature = dict()

    feature["分型标记"] = 1 if ka.fx[-1]['fx_mark'] == 'g' else 0
    feature["笔标记"] = 1 if ka.bi[-1]['fx_mark'] == 'g' else 0
    feature["线段标记"] = 1 if ka.xd[-1]['fx_mark'] == 'g' else 0

    feature['向上笔背驰'] = 1 if ka.bi[-1]['fx_mark'] == 'g' and ka.bi_bei_chi() else 0
    feature['向下笔背驰'] = 1 if ka.bi[-1]['fx_mark'] == 'd' and ka.bi_bei_chi() else 0
    feature['向上线段背驰'] = 1 if ka.xd[-1]['fx_mark'] == 'g' and ka.xd_bei_chi() else 0
    feature['向下线段背驰'] = 1 if ka.xd[-1]['fx_mark'] == 'd' and ka.xd_bei_chi() else 0

    ma_params = (5, 20, 120, 250)
    df = create_df(ka, ma_params)
    last = df.iloc[-1].to_dict()
    for p in ma_params:
        feature['收于MA%i上方' % p] = 1 if last['close'] > last['ma%i' % p] else 0

    feature["MACD金叉"] = 1 if last['diff'] > last['dea'] else 0
    feature["MACD死叉"] = 1 if last['diff'] < last['dea'] else 0

    return {ka.name + k: v for k, v in feature.items()}


def find_zs(points):
    """输入笔或线段标记点，输出中枢识别结果"""
    if len(points) <= 4:
        return []

    # 当输入为笔的标记点时，新增 xd 值
    for i, x in enumerate(points):
        if x.get("bi", 0):
            points[i]['xd'] = x["bi"]

    k_xd = points
    k_zs = []
    zs_xd = []

    for i in range(len(k_xd)):
        if len(zs_xd) < 5:
            zs_xd.append(k_xd[i])
            continue
        xd_p = k_xd[i]
        zs_d = max([x['xd'] for x in zs_xd[:4] if x['fx_mark'] == 'd'])
        zs_g = min([x['xd'] for x in zs_xd[:4] if x['fx_mark'] == 'g'])
        if zs_g <= zs_d:
            zs_xd.append(k_xd[i])
            zs_xd.pop(0)
            continue

        # 定义四个指标,GG=max(gn),G=min(gn),D=max(dn),DD=min(dn)，
        # n遍历中枢中所有Zn。特别地，再定义ZG=min(g1、g2),
        # ZD=max(d1、d2)，显然，[ZD，ZG]就是缠中说禅走势中枢的区间
        if xd_p['fx_mark'] == "d" and xd_p['xd'] > zs_g:
            # 线段在中枢上方结束，形成三买
            k_zs.append({
                'ZD': zs_d,
                "ZG": zs_g,
                'G': min([x['xd'] for x in zs_xd if x['fx_mark'] == 'g']),
                'GG': max([x['xd'] for x in zs_xd if x['fx_mark'] == 'g']),
                'D': max([x['xd'] for x in zs_xd if x['fx_mark'] == 'd']),
                'DD': min([x['xd'] for x in zs_xd if x['fx_mark'] == 'd']),
                "points": zs_xd,
                "third_buy": xd_p
            })
            zs_xd = k_xd[i - 1: i + 1]
        elif xd_p['fx_mark'] == "g" and xd_p['xd'] < zs_d:
            # 线段在中枢下方结束，形成三卖
            k_zs.append({
                'ZD': zs_d,
                "ZG": zs_g,
                'G': min([x['xd'] for x in zs_xd if x['fx_mark'] == 'g']),
                'GG': max([x['xd'] for x in zs_xd if x['fx_mark'] == 'g']),
                'D': max([x['xd'] for x in zs_xd if x['fx_mark'] == 'd']),
                'DD': min([x['xd'] for x in zs_xd if x['fx_mark'] == 'd']),
                "points": zs_xd,
                "third_sell": xd_p
            })
            zs_xd = k_xd[i - 1: i + 1]
        else:
            zs_xd.append(xd_p)

    if len(zs_xd) >= 5:
        zs_d = max([x['xd'] for x in zs_xd[:4] if x['fx_mark'] == 'd'])
        zs_g = min([x['xd'] for x in zs_xd[:4] if x['fx_mark'] == 'g'])
        k_zs.append({
            'ZD': zs_d,
            "ZG": zs_g,
            'G': min([x['xd'] for x in zs_xd if x['fx_mark'] == 'g']),
            'GG': max([x['xd'] for x in zs_xd if x['fx_mark'] == 'g']),
            'D': max([x['xd'] for x in zs_xd if x['fx_mark'] == 'd']),
            'DD': min([x['xd'] for x in zs_xd if x['fx_mark'] == 'd']),
            "points": zs_xd,
        })

    return k_zs


@lru_cache(maxsize=64)
def create_df(ka, ma_params=(5, 20, 120, 250), use_macd=True, use_boll=True):
    df = pd.DataFrame(ka.kline)
    df = ma(df, params=ma_params)
    if use_macd:
        df = macd(df)
    if use_boll:
        df = boll(df)
    return df


class KlineAnalyze(object):
    def __init__(self, kline, name="本级别", bi_mode="new", xd_mode="strict",
                 min_bi_gap=0.001, handle_last=True, debug=False):
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
        :param bi_mode: str
           笔识别控制参数，默认为 new，表示新笔；如果不想用新笔定义识别，设置为 old
        :param xd_mode: str
            线段识别控制参数，默认为 loose，在这种模式下，只要线段标记内有三笔就满足会识别；另外一个可选值是 strict，
            在 strict 模式下，对于三笔形成的线段，要求其后的一笔不跌破或升破线段最后一笔的起始位置。
        :param min_bi_gap: float
           笔内部缺口的最小百分比，默认值 0.001
        :param handle_last: bool
            是否使用默认的 handle_last 方法，默认值为 True
        """
        self.name = name
        assert bi_mode in ['new', 'old'], "bi_mode 参数错误"
        assert xd_mode in ['loose', 'strict'], "bi_mode 参数错误"
        self.bi_mode = bi_mode
        self.xd_mode = xd_mode
        self.handle_last = handle_last
        self.min_bi_gap = min_bi_gap
        self.debug = debug
        self.kline = self._preprocess(kline)
        self.symbol = self.kline[0]['symbol']
        self.latest_price = self.kline[-1]['close']
        self.start_dt = self.kline[0]['dt']
        self.end_dt = self.kline[-1]['dt']
        self.kline_new = self._remove_include()
        self.fx = self._find_fx()
        self.bi = self._find_bi()
        self.xd = self._find_xd()
        self.zs = find_zs(self.xd)
        self.__update_kline()

    def __repr__(self):
        return "<KlineAnalyze of %s@%s, from %s to %s>" % (self.symbol, self.name, self.start_dt, self.end_dt)

    @staticmethod
    def _preprocess(kline):
        """新增分析所需字段"""
        if isinstance(kline, pd.DataFrame):
            columns = kline.columns.to_list()
            kline = [{k: v for k, v in zip(columns, row)} for row in kline.values]

        results = []
        for k in kline:
            k['fx_mark'], k['fx'], k['bi'], k['xd'] = "o", None, None, None
            results.append(k)
        return results

    def _remove_include(self):
        """去除包含关系，得到新的K线数据"""
        k_new = []

        for k in self.kline:
            if len(k_new) <= 2:
                k_new.append({
                    "symbol": k['symbol'],
                    "dt": k['dt'],
                    "open": k['open'],
                    "close": k['close'],
                    "high": k['high'],
                    "low": k['low'],
                    "vol": k['vol'],
                    "fx_mark": k['fx_mark'],
                    "fx": k['fx'],
                    "bi": k['bi'],
                    "xd": k['xd'],
                })
                continue

            # 从 k_new 中取最后两根 K 线计算方向
            k1, k2 = k_new[-2:]
            if k2['high'] > k1['high']:
                direction = "up"
            elif k2['low'] < k1['low']:
                direction = "down"
            else:
                direction = "up"

            # 判断 k2 与 k 之间是否存在包含关系
            cur_h, cur_l = k['high'], k['low']
            last_h, last_l = k2['high'], k2['low']

            # 左包含 or 右包含
            if (cur_h <= last_h and cur_l >= last_l) or (cur_h >= last_h and cur_l <= last_l):
                # 有包含关系，按方向分别处理
                if direction == "up":
                    last_h = max(last_h, cur_h)
                    last_l = max(last_l, cur_l)
                elif direction == "down":
                    last_h = min(last_h, cur_h)
                    last_l = min(last_l, cur_l)
                else:
                    raise ValueError

                k_new.pop(-1)
                if k['open'] >= k['close']:
                    k_new.append({
                        "symbol": k['symbol'],
                        "dt": k['dt'],
                        "open": last_h,
                        "close": last_l,
                        "high": last_h,
                        "low": last_l,
                        "vol": k['vol'],
                        "fx_mark": k['fx_mark'],
                        "fx": k['fx'],
                        "bi": k['bi'],
                        "xd": k['xd'],
                    })
                else:
                    k_new.append({
                        "symbol": k['symbol'],
                        "dt": k['dt'],
                        "open": last_l,
                        "close": last_h,
                        "high": last_h,
                        "low": last_l,
                        "vol": k['vol'],
                        "fx_mark": k['fx_mark'],
                        "fx": k['fx'],
                        "bi": k['bi'],
                        "xd": k['xd'],
                    })
            else:
                # 无包含关系，更新 K 线
                k_new.append({
                    "symbol": k['symbol'],
                    "dt": k['dt'],
                    "open": k['open'],
                    "close": k['close'],
                    "high": k['high'],
                    "low": k['low'],
                    "vol": k['vol'],
                    "fx_mark": k['fx_mark'],
                    "fx": k['fx'],
                    "bi": k['bi'],
                    "xd": k['xd'],
                })
        return k_new

    def _find_fx(self):
        """识别线分型标记

        o   非分型
        d   底分型
        g   顶分型

        :return:
        """
        i = 0
        fx = []
        while i < len(self.kline_new):
            if i == 0 or i == len(self.kline_new) - 1:
                i += 1
                continue
            k1, k2, k3 = self.kline_new[i - 1: i + 2]
            i += 1

            # 顶分型标记
            if k2['high'] > k1['high'] and k2['high'] > k3['high']:
                k2['fx_mark'] = 'g'
                k2['fx'] = k2['high']
                fx.append({
                    "dt": k2['dt'],
                    "fx_mark": "g",
                    "fx": k2['high'],
                    "fx_high": k2['high'],
                    "fx_low": max(k1['low'], k2['low'])
                })

            # 底分型标记
            if k2['low'] < k1['low'] and k2['low'] < k3['low']:
                k2['fx_mark'] = 'd'
                k2['fx'] = k2['low']
                fx.append({
                    "dt": k2['dt'],
                    "fx_mark": "d",
                    "fx": k2['low'],
                    "fx_high": min(k1['high'], k2['high']),
                    "fx_low": k2['low']
                })

        # fx = [{"dt": x['dt'], "fx_mark": x['fx_mark'], "fx": x['fx']}
        #       for x in self.kline_new if x['fx_mark'] in ['d', 'g']]
        return fx

    def __extract_potential(self, mode='fx', fx_mark='d'):
        if mode == 'fx':
            points = self.fx
        elif mode == 'bi':
            points = self.bi
        else:
            raise ValueError

        seq = [x for x in points if x['fx_mark'] == fx_mark]
        seq = sorted(seq, key=lambda x: x['dt'], reverse=False)

        p = [seq[0]]
        i = 1
        while i < len(seq):
            if fx_mark == 'd':
                # 对于底，前面的高于后面的，只保留后面的
                s1 = seq[i-1]
                s2 = seq[i]
                if i == len(seq) - 1:
                    p.append(s2)
                else:
                    s3 = seq[i + 1]
                    if s1[mode] > s2[mode] < s3[mode]:
                        p.append(s2)

            elif fx_mark == 'g':
                # 对于顶，前面的低于后面的，只保留后面的
                s1 = seq[i-1]
                s2 = seq[i]
                if i == len(seq) - 1:
                    p.append(s2)
                else:
                    s3 = seq[i + 1]
                    if s1[mode] < s2[mode] > s3[mode]:
                        p.append(s2)
            else:
                raise ValueError
            i += 1

        return p

    def __handle_hist_bi(self):
        """识别笔标记：从已经识别出来的分型中确定能够构建笔的分型
        """
        if self.bi_mode == "new":
            min_k_num = 4
        elif self.bi_mode == "old":
            min_k_num = 5
        else:
            raise ValueError
        self.min_k_num = min_k_num
        kn = self.kline_new
        fx_p = self.fx

        # 确认哪些分型可以构成笔
        bi = []
        for i in range(len(fx_p)):
            k = {
                "dt": fx_p[i]['dt'],
                "fx_mark": fx_p[i]['fx_mark'],
                "bi": fx_p[i]['fx'],
                "fx_high": fx_p[i]['fx_high'],
                "fx_low": fx_p[i]['fx_low'],
            }
            if len(bi) == 0:
                bi.append(k)
            else:
                k0 = bi[-1]
                if k0['fx_mark'] == k['fx_mark']:
                    if (k0['fx_mark'] == "g" and k0['bi'] < k['bi']) or \
                            (k0['fx_mark'] == "d" and k0['bi'] > k['bi']):
                        bi.pop(-1)
                        bi.append(k)
                else:
                    k_inside = [x for x in kn if k0['dt'] <= x['dt'] <= k['dt']]

                    # 缺口处理：缺口的出现说明某一方力量很强，当做N根K线处理
                    k_pair = [k_inside[x: x+2] for x in range(len(k_inside)-2)]
                    has_gap = False
                    for pair in k_pair:
                        kr, kl = pair
                        # 向下缺口
                        if kr['low'] > kl['high'] * (1+self.min_bi_gap):
                            has_gap = True
                            break

                        # 向上缺口
                        if kr['high'] < kl['low'] * (1-self.min_bi_gap):
                            has_gap = True
                            break

                    if has_gap:
                        # bi.append(k)
                        if (k0['fx_mark'] == 'g' and k['fx_high'] < k0['fx_low']) or \
                                (k0['fx_mark'] == 'd' and k['fx_low'] > k0['fx_high']):
                            bi.append(k)
                        continue

                    # max_high = max([x['high'] for x in k_inside])
                    # min_low = min([x['low'] for x in k_inside])
                    if len(k_inside) >= min_k_num:
                        # 确保相邻两个顶底之间顶大于底，并且笔分型是极值
                        if (k0['fx_mark'] == 'g' and k['fx_high'] < k0['fx_low']) or \
                                (k0['fx_mark'] == 'd' and k['fx_low'] > k0['fx_high']):
                            bi.append(k)
        return bi

    def __handle_last_bi(self, bi):
        """处理最后一个笔标记

        特别的，对应最后一个笔标记：最后一根K线的最高价大于顶，或最后一根K线的最低价大于底，则删除这个标记。
        """
        last_bi = bi[-1]
        last_k = self.kline_new[-1]

        if (last_bi['fx_mark'] == 'd' and last_k['low'] < last_bi['bi']) \
                or (last_bi['fx_mark'] == 'g' and last_k['high'] > last_bi['bi']):
            bi.pop(-1)
        return bi

    def _find_bi(self):
        try:
            bi = self.__handle_hist_bi()
            if self.handle_last:
                bi = self.__handle_last_bi(bi)

            dts = [x["dt"] for x in bi]
            for k in self.kline_new:
                if k['dt'] in dts:
                    k['bi'] = k['fx']
            return bi
        except:
            if self.debug:
                traceback.print_exc()
            return []

    def __handle_hist_xd(self):
        """识别线段标记：从已经识别出来的笔中识别线段"""
        bi_p = []  # 存储潜在线段标记
        bi_p.extend(self.__extract_potential(mode='bi', fx_mark='d'))
        bi_p.extend(self.__extract_potential(mode='bi', fx_mark='g'))
        bi_p = sorted(bi_p, key=lambda x: x['dt'], reverse=False)

        xd = []
        for i in range(len(bi_p)):
            k = {
                "dt": bi_p[i]['dt'],
                "fx_mark": bi_p[i]['fx_mark'],
                "xd": bi_p[i]['bi'],
            }
            if len(xd) == 0:
                xd.append(k)
            else:
                k0 = xd[-1]
                if k0['fx_mark'] == k['fx_mark']:
                    # 处理同一性质的笔标记
                    if (k0['fx_mark'] == "g" and k0['xd'] < k['xd']) or \
                            (k0['fx_mark'] == "d" and k0['xd'] > k['xd']):
                        xd.pop(-1)
                        xd.append(k)
                else:
                    # 确保相邻两个顶底之间顶大于底
                    if (k0['fx_mark'] == 'g' and k['xd'] >= k0['xd']) or \
                            (k0['fx_mark'] == 'd' and k['xd'] <= k0['xd']):
                        xd.pop(-1)
                        continue

                    bi_m = [x for x in self.bi if k0['dt'] <= x['dt'] <= k['dt']]
                    bi_r = [x for x in self.bi if x['dt'] >= k['dt']]
                    # 一线段内部至少三笔
                    if len(bi_m) < 4 or len(bi_r) < 4:
                        continue

                    # 线段的顶必然大于相邻的两个顶；线段的底必然小于相邻的两个底
                    assert k['fx_mark'] == bi_m[-3]['fx_mark'] == bi_r[2]['fx_mark']
                    if k['fx_mark'] == "d" and not (bi_m[-3]['bi'] > k['xd'] < bi_r[2]['bi']):
                        print("不满足线段的底必然小于相邻的两个底")
                        print(bi_m[-3], k, bi_r[2])
                        continue

                    if k['fx_mark'] == "g" and not (bi_m[-3]['bi'] < k['xd'] > bi_r[2]['bi']):
                        print("不满足线段的顶必然大于相邻的两个顶")
                        print(bi_m[-3], k, bi_r[2])
                        continue

                    # 判断线段标记是否有效
                    left_last = bi_m[-3]
                    right_first = bi_r[1]
                    assert left_last['fx_mark'] != right_first['fx_mark']

                    if k['fx_mark'] == 'd':
                        max_g = max([x['bi'] for x in bi_r[:8] if x['fx_mark'] == 'g'])
                        if max_g > right_first['bi'] and max_g > left_last['bi']:
                            xd.append(k)

                    if k['fx_mark'] == 'g':
                        min_d = min([x['bi'] for x in bi_r[:8] if x['fx_mark'] == 'd'])
                        if min_d < right_first['bi'] and min_d < left_last['bi']:
                            xd.append(k)
        return xd

    def __handle_last_xd(self, xd):
        """处理最后一个线段标记

        特别的，对最后一个线段标记：最后一根K线的最高价大于顶，或最后一根K线的最低价大于底，则删除这个标记。
        """
        last_k = self.kline_new[-1]
        if (xd[-1]['fx_mark'] == 'd' and last_k['low'] < xd[-1]['xd']) \
                or (xd[-1]['fx_mark'] == 'g' and last_k['high'] > xd[-1]['xd']):
            xd.pop(-1)
        return xd

    def _find_xd(self):
        try:
            xd = self.__handle_hist_xd()
            if self.handle_last:
                xd = self.__handle_last_xd(xd)

            dts = [x["dt"] for x in xd]
            for k in self.kline_new:
                if k['dt'] in dts:
                    k['xd'] = k['fx']
            return xd
        except:
            if self.debug:
                traceback.print_exc()
            return []

    def __update_kline(self):
        kn_map = {x['dt']: x for x in self.kline_new}
        for k in self.kline:
            k1 = kn_map.get(k['dt'], None)
            if k1:
                k['fx_mark'], k['fx'], k['bi'], k['xd'] = k1['fx_mark'], k1['fx'], k1['bi'], k1['xd']

    def zs_mean(self, n=6, mode='xd'):
        """计算最近 n 个走势的平均波动幅度

        :param n: int
            线段数量
        :param mode: str
            xd -> 线段平均波动； bi -> 笔平均波动
        :return: float
        """
        if mode == 'xd':
            latest_zs = self.xd[-n - 1:]
        elif mode == 'bi':
            latest_zs = self.bi[-n - 1:]
        else:
            raise ValueError("mode value error, only support 'xd' or 'bi'")

        wave = []
        for i in range(len(latest_zs) - 1):
            x1 = latest_zs[i][mode]
            x2 = latest_zs[i + 1][mode]
            w = abs(x1 - x2) / x1
            wave.append(w)
        return round(sum(wave) / len(wave), 2)

    def bi_bei_chi(self):
        """判断最后一笔是否背驰"""
        bi = self.bi

        # 最后一笔背驰出现的两种情况：
        # 1）向上笔新高且和前一个向上笔不存在包含关系；
        # 2）向下笔新低且和前一个向下笔不存在包含关系。
        if (bi[-1]['fx_mark'] == 'g' and bi[-1]["bi"] > bi[-3]["bi"] and bi[-2]["bi"] > bi[-4]["bi"]) or \
                (bi[-1]['fx_mark'] == 'd' and bi[-1]['bi'] < bi[-3]['bi'] and bi[-2]['bi'] < bi[-4]['bi']):
            zs1 = {"start_dt": bi[-2]['dt'], "end_dt": bi[-1]['dt']}
            zs2 = {"start_dt": bi[-4]['dt'], "end_dt": bi[-3]['dt']}
            return is_bei_chi(self, zs1, zs2, mode="bi")
        else:
            return False

    def xd_bei_chi(self):
        """判断最后一个线段是否背驰"""
        xd = self.xd
        last_xd = xd[-1]
        if last_xd['fx_mark'] == 'g':
            direction = "up"
        elif last_xd['fx_mark'] == 'd':
            direction = "down"
        else:
            raise ValueError

        # 最后一个线段背驰出现的两种情况：
        # 1）向上线段新高且和前一个向上线段不存在包含关系；
        # 2）向下线段新低且和前一个向下线段不存在包含关系。
        if (last_xd['fx_mark'] == 'g' and xd[-1]["xd"] > xd[-3]["xd"] and xd[-2]["xd"] > xd[-4]["xd"]) or \
                (last_xd['fx_mark'] == 'd' and xd[-1]['xd'] < xd[-3]['xd'] and xd[-2]['xd'] < xd[-4]['xd']):
            zs1 = {"start_dt": xd[-2]['dt'], "end_dt": xd[-1]['dt'], "direction": direction}
            zs2 = {"start_dt": xd[-4]['dt'], "end_dt": xd[-3]['dt'], "direction": direction}
            return is_bei_chi(self, zs1, zs2, mode="xd")
        else:
            return False

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

    def up_zs_number(self):
        """检查最新走势的连续向上中枢数量"""
        ka = self
        zs_num = 1
        if len(ka.zs) > 1:
            k_zs = ka.zs[::-1]
            zs_cur = k_zs[0]
            for zs_next in k_zs[1:]:
                if zs_cur["ZD"] >= zs_next["ZG"]:
                    zs_num += 1
                    zs_cur = zs_next
                else:
                    break
        return zs_num

    def down_zs_number(self):
        """检查最新走势的连续向下中枢数量"""
        ka = self
        zs_num = 1
        if len(ka.zs) > 1:
            k_zs = ka.zs[::-1]
            zs_cur = k_zs[0]
            for zs_next in k_zs[1:]:
                if zs_cur["ZG"] <= zs_next["ZD"]:
                    zs_num += 1
                    zs_cur = zs_next
                else:
                    break
        return zs_num
