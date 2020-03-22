# coding: utf-8
import traceback
from copy import deepcopy
import pandas as pd

from .ta import macd


def up_zs_number(ka):
    """检查最新走势的连续向上中枢数量"""
    zs_num = 1
    if len(ka.zs) > 1:
        k_zs = ka.zs[::-1]
        zs_cur = k_zs[0]
        for zs_next in k_zs[1:]:
            if zs_cur['zs'][0] >= zs_next['zs'][1]:
                zs_num += 1
                zs_cur = zs_next
            else:
                break
    return zs_num


def down_zs_number(ka):
    """检查最新走势的连续向下中枢数量"""
    zs_num = 1
    if len(ka.zs) > 1:
        k_zs = ka.zs[::-1]
        zs_cur = k_zs[0]
        for zs_next in k_zs[1:]:
            if zs_cur['zs'][1] <= zs_next['zs'][0]:
                zs_num += 1
                zs_cur = zs_next
            else:
                break
    return zs_num


def is_bei_chi(ka, zs1, zs2, direction="down", mode="bi"):
    """判断 zs1 对 zs2 是否有背驰

    :param ka: KlineAnalyze
        缠论的分析结果，即去除包含关系后，识别出分型、笔、线段的K线
    :param direction: str
        default `down`, optional value [`up`, 'down']
    :param zs1: list of datetime
        用于比较的走势，通常是最近的走势
    :param zs2: list of datetime
        被比较的走势，通常是较前的走势
    :param mode: str
        default `bi`, optional value [`zs`, `xd`, `bi`]
        zs  判断两个走势类型之间是否存在背驰
        xd  判断两个线段之间是否存在背驰
        bi  判断两笔之间是否存在背驰
    :return:
    """
    df = pd.DataFrame(ka.kline)
    df = macd(df)
    k1 = df[(df['dt'] >= zs1[0]) & (df['dt'] <= zs1[1])]
    k2 = df[(df['dt'] >= zs2[0]) & (df['dt'] <= zs2[1])]

    bc = False
    if mode == 'bi':
        macd_sum1 = sum([abs(x) for x in k1.macd])
        macd_sum2 = sum([abs(x) for x in k2.macd])
        if macd_sum1 < macd_sum2:
            bc = True

    elif mode == 'xd':
        if direction == "down":
            macd_sum1 = sum([abs(x) for x in k1.macd if x < 0])
            macd_sum2 = sum([abs(x) for x in k2.macd if x < 0])
        elif direction == "up":
            macd_sum1 = sum([abs(x) for x in k1.macd if x > 0])
            macd_sum2 = sum([abs(x) for x in k2.macd if x > 0])
        else:
            raise ValueError('direction value error')
        if macd_sum1 < macd_sum2:
            bc = True

    else:
        raise ValueError("mode value error")

    return bc


class KlineAnalyze(object):
    def __init__(self, kline):
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
        """
        self.kline = self._preprocess(kline)
        self.symbol = self.kline[0]['symbol']
        self.latest_price = self.kline[-1]['close']
        self.start_dt = self.kline[0]['dt']
        self.end_dt = self.kline[-1]['dt']
        self.kline_new = self._remove_include()
        self.fx = self._find_fx()
        self.bi = self._find_bi()
        self.xd = self._find_xd()
        self.zs = self._find_zs()
        self.__update_kline()

    def __repr__(self):
        return "<chan.analyze.KlineAnalyze of %s, from %s to %s>" % (self.symbol, self.start_dt, self.end_dt)

    @staticmethod
    def _preprocess(kline):
        """新增分析所需字段"""
        if isinstance(kline, pd.DataFrame):
            kline = [row.to_dict() for _, row in kline.iterrows()]

        results = []
        for k in kline:
            k['fx_mark'], k['fx'], k['bi'], k['xd'] = "o", None, None, None
            results.append(k)
        return results

    def _remove_include(self):
        """去除包含关系，得到新的K线数据"""
        # 取前两根 K 线放入 k_new，完成初始化
        kline = deepcopy(self.kline)
        k_new = kline[:2]

        for k in kline[2:]:
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

                k['high'] = last_h
                k['low'] = last_l
                k_new.pop(-1)
                k_new.append(k)
            else:
                # 无包含关系，更新 K 线
                k_new.append(k)
        return k_new

    def _find_fx(self):
        """识别线分型标记

        o   非分型
        d   底分型
        g   顶分型

        :return:
        """
        kn = deepcopy(self.kline_new)
        i = 0
        while i < len(kn):
            if i == 0 or i == len(kn) - 1:
                i += 1
                continue
            k1, k2, k3 = kn[i - 1: i + 2]
            i += 1

            # 顶分型标记
            if k2['high'] > k1['high'] and k2['high'] > k3['high']:
                k2['fx_mark'] = 'g'
                k2['fx'] = k2['high']

            # 底分型标记
            if k2['low'] < k1['low'] and k2['low'] < k3['low']:
                k2['fx_mark'] = 'd'
                k2['fx'] = k2['low']
        self.kline_new = kn

        fx = [{"dt": x['dt'], "fx_mark": x['fx_mark'], "fx": x['fx']} for x in self.kline_new
              if x['fx_mark'] in ['d', 'g']]
        return fx

    def __get_potential_bi(self):
        """识别笔标记：从已经识别出来的分型中确定能够构建笔的分型

        划分笔的步骤：
        （1）确定所有符合标准的分型。
        （2）如果前后两分型是同一性质的，对于顶，前面的低于后面的，只保留后面的，前面那个可以忽略掉；对于底，
            前面的高于后面的，只保留后面的，前面那个可以忽略掉。不满足上面情况的，例如相等的，都可以先保留。
        （3）经过步骤（2）的处理后，余下的分型，如果相邻的是顶和底，那么这就可以划为一笔。
        """
        # 符合标准的分型
        kn = deepcopy(self.kline_new)
        fx_p = sorted(deepcopy(self.fx), key=lambda x: x['dt'], reverse=False)
        # 确认哪些分型可以构成笔
        bi = []
        for i in range(len(fx_p)):
            k = deepcopy(fx_p[i])
            k['bi'] = k['fx']
            del k['fx']
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
                    # 确保相邻两个顶底之间顶大于底
                    if (k0['fx_mark'] == 'g' and k['bi'] >= k0['bi']) or \
                            (k0['fx_mark'] == 'd' and k['bi'] <= k0['bi']):
                        bi.pop(-1)
                        continue

                    # 一笔的顶底分型之间至少包含5根K线
                    k_num = [x for x in kn if k0['dt'] <= x['dt'] <= k['dt']]
                    if len(k_num) >= 5:
                        bi.append(k)
        return bi

    def __handle_last_bi(self, bi):
        """判断最后一个笔标记是否有效，规则如下：
        1）如果最后一个笔标记为顶分型，最近一根K线的最高价在这个顶分型上方，该标记无效；
        2）如果最后一个笔标记为底分型，最近一根K线的最低价在这个底分型下方，该标记无效；
        """
        last_bi = bi[-1]

        last_k = self.kline_new[-1]
        if (last_bi['fx_mark'] == 'g' and last_k['high'] >= last_bi['bi']) or \
                (last_bi['fx_mark'] == 'd' and last_k['low'] <= last_bi['bi']):
            bi.pop()
        return bi

    def _find_bi(self):
        bi = self.__get_potential_bi()
        bi = self.__handle_last_bi(bi)
        bi_list = [x["dt"] for x in bi]

        for k in self.kline_new:
            if k['dt'] in bi_list:
                k['bi'] = k['fx']
        return bi

    def __handle_last_xd(self, xd_v):
        """判断最后一个线段标记是否有效，规则如下：
        1）如果最后一个线段标记为顶分型，最近一根K线的最高价在这个顶分型上方，该标记无效；
        2）如果最后一个线段标记为底分型，最近一根K线的最低价在这个底分型下方，该标记无效；
        """
        last_xd = xd_v[-1]
        last_k = self.kline_new[-1]
        if (last_xd['fx_mark'] == 'g' and last_k['high'] >= last_xd['xd']) or \
                (last_xd['fx_mark'] == 'd' and last_k['low'] <= last_xd['xd']):
            xd_v.pop()
        return xd_v

    def __get_potential_xd(self):
        """识别线段标记：从已经识别出来的笔中识别线段

        划分线段的步骤：
        （1）确定所有符合标准的笔标记。
        （2）如果前后两个笔标记是同一性质的，对于顶，前面的低于后面的，只保留后面的，前面那个可以忽略掉；对于底，
            前面的高于后面的，只保留后面的，前面那个可以忽略掉。不满足上面情况的，例如相等的，都可以先保留。
        （3）经过步骤（2）的处理后，余下的笔标记，如果相邻的是顶和底，那么这就可以划为线段。
        """
        bi_p = sorted(deepcopy(self.bi), key=lambda x: x['dt'], reverse=False)
        xd = []
        for i in range(len(bi_p)):
            k = deepcopy(bi_p[i])
            k['xd'] = k['bi']
            del k['bi']
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
                    if len(bi_m) >= 4:
                        if len(bi_m) == 4:
                            if len(bi_r) <= 1:
                                continue
                            # 两个连续线段标记之间只有三笔的处理
                            lp2 = bi_m[-2]
                            rp2 = bi_r[1]
                            if lp2['fx_mark'] != rp2['fx_mark']:
                                continue

                            if (k['fx_mark'] == "g" and lp2['bi'] < rp2['bi'] and bi_m[-1]['bi'] > bi_m[-3]['bi']) \
                                    or (k['fx_mark'] == "d" and lp2['bi'] > rp2['bi']
                                        and bi_m[-1]['bi'] < bi_m[-3]['bi']):
                                xd.append(k)
                        else:
                            xd.append(k)
        return xd

    def _find_xd(self):
        try:
            xd = self.__get_potential_xd()
            xd = self.__handle_last_xd(xd)
            dts = [x['dt'] for x in xd]

            def __add_xd(k):
                if k['dt'] in dts:
                    k['xd'] = k['fx']
                return k

            self.kline_new = [__add_xd(k) for k in self.kline_new]
            return xd
        except:
            traceback.print_exc()
            return []

    def _find_zs(self):
        """查找中枢"""
        if len(self.xd) <= 4:
            return []

        k_xd = self.xd
        k_zs = []
        zs_xd = []

        for i in range(len(k_xd)):
            if len(zs_xd) < 3:
                zs_xd.append(k_xd[i])
                continue
            xd_p = k_xd[i]
            zs_d = max([x['xd'] for x in zs_xd if x['fx_mark'] == 'd'])
            zs_g = min([x['xd'] for x in zs_xd if x['fx_mark'] == 'g'])

            if xd_p['fx_mark'] == "d" and xd_p['xd'] > zs_g:
                # 线段在中枢上方结束，形成三买
                k_zs.append({'zs': (zs_d, zs_g), "zs_xd": deepcopy(zs_xd)})
                zs_xd = deepcopy(k_xd[i - 2:i + 1])
            elif xd_p['fx_mark'] == "g" and xd_p['xd'] < zs_d:
                # 线段在中枢下方结束，形成三卖
                k_zs.append({'zs': (zs_d, zs_g), "zs_xd": deepcopy(zs_xd)})
                zs_xd = deepcopy(k_xd[i - 2:i + 1])
            else:
                zs_xd.append(deepcopy(xd_p))

        if len(zs_xd) >= 4:
            zs_d = max([x['xd'] for x in zs_xd if x['fx_mark'] == 'd'])
            zs_g = min([x['xd'] for x in zs_xd if x['fx_mark'] == 'g'])
            k_zs.append({'zs': (zs_d, zs_g), "zs_xd": deepcopy(zs_xd)})

        return k_zs

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
            latest_zs = deepcopy(self.xd[-n-1:])
            for x in latest_zs:
                x['fx'] = x['xd']
        elif mode == 'bi':
            latest_zs = deepcopy(self.bi[-n-1:])
            for x in latest_zs:
                x['fx'] = x['bi']
        else:
            raise ValueError("mode value error, only support 'xd' or 'bi'")

        wave = []
        for i in range(len(latest_zs)-1):
            x1 = latest_zs[i]['fx']
            x2 = latest_zs[i+1]['fx']
            w = abs(x1-x2)/x1
            wave.append(w)
        return round(sum(wave) / len(wave), 2)

