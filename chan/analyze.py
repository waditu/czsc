# coding: utf-8
import traceback
from copy import deepcopy
import pandas as pd

from .ta import macd


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
        self.name = "缠论分析"
        self.kline = self._preprocess(kline)
        self.kline_new = self._remove_include()
        self.fx = self._find_fx()
        self.bi = self._find_bi()
        self.xd = self._find_xd()
        self.zs = self._find_zs()
        self.__update_kline()

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

    def _find_bi_v1(self):
        """识别笔标记：从已经识别出来的分型中确定能够构建笔的分型"""
        kn = deepcopy(self.kline_new)
        bi = []
        potential = None
        o_count = 0

        for k in kn:
            if not potential:
                if k['fx_mark'] in ['d', 'g']:
                    potential = deepcopy(k)
                else:
                    continue

            if k['fx_mark'] in ['d', 'g']:
                if k['fx_mark'] == potential['fx_mark']:
                    if k['fx_mark'] == "g" and k['fx'] > potential['fx']:
                        potential = deepcopy(k)
                    elif k['fx_mark'] == "d" and k['fx'] < potential['fx']:
                        potential = deepcopy(k)
                    else:
                        continue
                    o_count = 0
                else:
                    if o_count >= 3:
                        potential['bi'] = potential['fx']
                        bi.append(potential)
                        o_count = 0
                        potential = deepcopy(k)
            else:
                o_count += 1

        potential['bi'] = potential['fx']
        bi.append(potential)
        bi = [{"dt": x['dt'], "fx_mark": x['fx_mark'], "bi": x['bi']} for x in bi]
        return bi

    def _find_bi_v2(self):
        """识别笔标记：从已经识别出来的分型中确定能够构建笔的分型

        划分笔的步骤：
        （1）确定所有符合标准的分型，能够构成笔的标准底分型一定小于其前后的底分型，顶分型反之。
        （2）如果前后两分型是同一性质的，对于顶，前面的低于后面的，只保留后面的，前面那个可以忽略掉；对于底，
            前面的高于后面的，只保留后面的，前面那个可以忽略掉。不满足上面情况的，例如相等的，都可以先保留。
        （3）经过步骤（2）的处理后，余下的分型，如果相邻的是顶和底，那么这就可以划为一笔。
        """
        # 符合标准的分型
        kn = deepcopy(self.kline_new)

        fx_p = []
        for fx_mark in ['d', 'g']:
            fx = [x for x in deepcopy(self.fx) if x['fx_mark'] == fx_mark]
            fx = sorted(fx, key=lambda x: x['dt'], reverse=False)
            for i in range(1, len(fx)-1):
                fx1, fx2, fx3 = fx[i-1:i+2]
                if (fx_mark == "d" and fx1['fx'] >= fx2['fx'] <= fx3['fx']) or \
                        (fx_mark == "g" and fx1['fx'] <= fx2['fx'] >= fx3['fx']):
                    fx_p.append(deepcopy(fx2))

        # 两个相邻的顶点分型之间有1根非共用K线
        for i in range(len(self.fx)-1):
            fx1, fx2 = self.fx[i], self.fx[i+1]
            k_num = [x for x in kn if fx1['dt'] <= x['dt'] <= fx2['dt']]
            if len(k_num) >= 5:
                fx_p.append(deepcopy(fx1))
                fx_p.append(deepcopy(fx2))

        fx_p = sorted(fx_p, key=lambda x: x['dt'], reverse=False)

        # 确认哪些分型可以构成笔
        bi = []
        for i in range(len(fx_p)):
            k = deepcopy(fx_p[i])
            k['bi'] = k['fx']
            del k['fx']
            if i == 0:
                bi.append(k)
            else:
                k0 = bi[-1]
                if k0['fx_mark'] == k['fx_mark']:
                    if (k0['fx_mark'] == "g" and k0['bi'] < k['bi']) or \
                            (k0['fx_mark'] == "d" and k0['bi'] > k['bi']):
                        bi.pop(-1)
                        bi.append(k)
                else:
                    # 一笔的顶底分型之间至少包含5根K线
                    k_num = [x for x in kn if k0['dt'] <= x['dt'] <= k['dt']]
                    if len(k_num) >= 5:
                        bi.append(k)
        return bi

    def __handle_last_bi(self, bi):
        """判断最后一个笔标记是否有效，有两个方案：
        方案一规则如下：
        1）如果最后一个笔标记为顶分型，最近一根K线的最高价在这个顶分型上方，该标记无效；
        2）如果最后一个笔标记为底分型，最近一根K线的最低价在这个底分型下方，该标记无效；

        方案二规则如下：
        1）如果最后一个笔标记为顶分型，最近一个底分型在这个顶分型上方，该标记无效；
        2）如果最后一个笔标记为底分型，最近一个顶分型在这个底分型下方，该标记无效；
        """
        last_bi = bi[-1]
        last_k = self.kline_new[-1]
        if (last_bi['fx_mark'] == 'g' and last_k['high'] >= last_bi['bi'])or \
                (last_bi['fx_mark'] == 'd' and last_k['low'] <= last_bi['bi']):
            bi.pop()

        # fx_last_d = [x for x in self.fx if x['fx_mark'] == "d"][-1]
        # fx_last_g = [x for x in self.fx if x['fx_mark'] == "g"][-1]
        # if (last_bi['fx_mark'] == 'g' and fx_last_d['fx'] >= last_bi['bi']) or \
        #         (last_bi['fx_mark'] == 'd' and fx_last_g['fx'] <= last_bi['bi']):
        #     bi.pop()
        return bi

    def _find_bi(self, version='v2'):
        if version == 'v2':
            bi = self._find_bi_v2()
        else:
            bi = self._find_bi_v1()
        bi = self.__handle_last_bi(bi)
        bi_list = [x["dt"] for x in bi]

        for k in self.kline_new:
            if k['dt'] in bi_list:
                k['bi'] = k['fx']
        return bi

    def __get_potential_xd(self):
        """依据不创新高、新低的近似标准找出所有潜在线段标记"""
        bi = deepcopy(self.bi)
        xd = []
        potential = bi[0]

        i = 0
        while i < len(bi) - 3:
            k1, k2, k3 = bi[i+1], bi[i+2], bi[i+3]

            if potential['fx_mark'] == "d":
                assert k2['fx_mark'] == 'd'
                if k3['bi'] < k1['bi']:
                    potential['xd'] = potential['bi']
                    xd.append(potential)
                    i += 1
                    potential = deepcopy(bi[i])
                else:
                    i += 2
            elif potential['fx_mark'] == "g":
                assert k2['fx_mark'] == 'g'
                if k3['bi'] > k1['bi']:
                    potential['xd'] = potential['bi']
                    xd.append(potential)
                    i += 1
                    potential = deepcopy(bi[i])
                else:
                    i += 2
            else:
                raise ValueError

        potential['xd'] = potential['bi']
        xd.append(potential)
        xd = [{"dt": x['dt'], "fx_mark": x['fx_mark'], "xd": x['xd']} for x in xd]
        return xd

    def __get_valid_xd(self, xd_p):
        bi = deepcopy(self.bi)
        xd_v = []
        for i in range(len(xd_p)):
            p2 = deepcopy(xd_p[i])
            if i == 0:
                xd_v.append(p2)
            else:
                p1 = deepcopy(xd_v[-1])
                if p1['fx_mark'] == p2['fx_mark']:
                    if (p1['fx_mark'] == 'g' and p1['xd'] < p2['xd']) or \
                            (p1['fx_mark'] == 'd' and p1['xd'] > p2['xd']):
                        xd_v.pop(-1)
                        xd_v.append(p2)
                else:
                    # 连续两个不同类型线段标记不允许出现“线段高点低于线段低点”和“线段低点高于线段高点”的情况；
                    if (p1['fx_mark'] == "g" and p1['xd'] < p2['xd']) or \
                            (p1['fx_mark'] == "d" and p1['xd'] > p2['xd']):
                        continue

                    # bi_l = [x for x in bi if x['dt'] <= p1['dt']]
                    bi_m = [x for x in bi if p1['dt'] <= x['dt'] <= p2['dt']]
                    bi_r = [x for x in bi if x['dt'] >= p2['dt']]
                    if len(bi_m) == 2:
                        # 两个连续线段标记之间只有一笔的处理
                        if i == len(xd_p)-1:
                            break
                        p3 = deepcopy(xd_p[i+1])
                        if (p1['fx_mark'] == "g" and p1['xd'] < p3['xd']) or \
                                (p1['fx_mark'] == "d" and p1['xd'] > p3['xd']):
                            xd_v.pop(-1)
                            xd_v.append(p3)
                    elif len(bi_m) == 4:
                        # 两个连续线段标记之间只有三笔的处理
                        lp2 = bi_m[-2]
                        rp2 = bi_r[1]
                        assert lp2['fx_mark'] == rp2['fx_mark']
                        if (p2['fx_mark'] == "g" and lp2['bi'] < rp2['bi']) or \
                                (p2['fx_mark'] == "d" and lp2['bi'] > rp2['bi']):
                            xd_v.append(p2)
                    else:
                        xd_v.append(p2)
        return xd_v

    def __handle_last_xd(self, xd_v):
        """判断最后一个线段标记是否有效，有以下两个方案：

        方案一规则如下：
        1）如果最后一个线段标记为顶分型，最近一根K线的最高价在这个顶分型上方，该标记无效；
        2）如果最后一个线段标记为底分型，最近一根K线的最低价在这个底分型下方，该标记无效；


        方案二规则如下：
        1）如果最后一个线段标记为顶分型，最近一个向下笔结束在这个顶分型上方，该线段标记无效；
        2）如果最后一个线段标记为底分型，最近一个向上笔结束在这个底分型下方，该线段标记无效；

        """
        last_xd = xd_v[-1]
        last_k = self.kline_new[-1]
        if (last_xd['fx_mark'] == 'g' and last_k['high'] >= last_xd['xd']) or \
                (last_xd['fx_mark'] == 'd' and last_k['low'] <= last_xd['xd']):
            xd_v.pop()

        # bi_last_d = [x for x in self.bi if x['fx_mark'] == "d"][-1]
        # bi_last_g = [x for x in self.bi if x['fx_mark'] == "g"][-1]
        # if (last_xd['fx_mark'] == 'g' and bi_last_d['bi'] >= last_xd['xd']) or \
        #         (last_xd['fx_mark'] == 'd' and bi_last_g['bi'] <= last_xd['xd']):
        #     xd_v.pop()
        return xd_v

    def _find_xd(self):
        try:
            xd = self.__get_potential_xd()
            xd = self.__get_valid_xd(xd)
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
        if not self.xd:
            return None

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
                # print(i, "三买")
                # 线段在中枢上方结束，形成三买
                k_zs.append({'zs': (zs_d, zs_g), "zs_xd": deepcopy(zs_xd)})
                zs_xd = deepcopy(k_xd[i - 2:i + 1])
            elif xd_p['fx_mark'] == "g" and xd_p['xd'] < zs_d:
                # 线段在中枢下方结束，形成三卖
                # print(i, "三卖")
                k_zs.append({'zs': (zs_d, zs_g), "zs_xd": deepcopy(zs_xd)})
                zs_xd = deepcopy(k_xd[i - 2:i + 1])
            else:
                # print(i, "延伸")
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
                # k.update(k1)

    def cal_bei_chi(self, zs1, zs2, direction="down", mode="bi"):
        """判断 zs1 对 zs2 是否有背驰

        :param direction: str
            default `down`, optional value [`up`, 'down']
        :param zs1: list of datetime
        :param zs2: list of datetime
        :param mode: str
            default `bi`, optional value [`xd`, `bi`]
        :return:
        """
        df = pd.DataFrame(self.kline)
        df = macd(df)
        k1 = df[(df['dt'] >= zs1[0]) & (df['dt'] <= zs1[1])]
        k2 = df[(df['dt'] >= zs2[0]) & (df['dt'] <= zs2[1])]

        if direction == "up" and k1.iloc[-1]['fx'] < k2.iloc[-1]['fx']:
            return "没有背驰"

        if direction == "down" and k1.iloc[-1]['fx'] > k2.iloc[-1]['fx']:
            return "没有背驰"

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

            if macd_sum1 < macd_sum2 and abs(k1.dea.iloc[-1]) < abs(k2.dea.iloc[-1]):
                bc = True
        else:
            raise ValueError("mode value error")

        if bc:
            return "背驰"
        else:
            return "没有背驰"

    def show(self):
        pass

    def xd_end_potential(self):
        """最后一个线段结束的概率"""
        k_xd = self.xd
        k_bi = self.bi
        fx_mark = k_xd[-1]['fx_mark']
        if fx_mark == 'd':
            direction = "up"
            last_bi = [x for x in self.bi if x['fx_mark'] == 'g'][-1]
        elif fx_mark == 'g':
            direction = "down"
            last_bi = [x for x in self.bi if x['fx_mark'] == 'd'][-1]
        else:
            raise ValueError

        potential_xd = {
            'dt': last_bi['dt'],
            'fx_mark': last_bi['fx_mark'],
            'xd': last_bi['bi'],
            'prob': 0
        }

        # 围绕最后一个中枢，判断是否有线段背驰
        zs1 = [k_xd[-1]['dt'], k_bi[-1]['dt']]  # 走势1：尚未完成的线段
        zs2 = [k_xd[-3]['dt'], k_xd[-2]['dt']]  # 走势2：上一根同向线段
        if direction == 'up':
            if potential_xd['xd'] >= k_xd[-2]['xd']:
                bc = self.cal_bei_chi(zs1, zs2, direction, mode='xd')
                if bc == "背驰":
                    potential_xd['prob'] += 0.5
            if self.bi[-1]['fx_mark'] == 'g' and "向上笔新高背驰" in self.status_bi.keys():
                potential_xd['prob'] += 0.5
        elif direction == 'down':
            if potential_xd['xd'] <= k_xd[-2]['xd']:
                bc = self.cal_bei_chi(zs1, zs2, direction, mode='xd')
                if bc == "背驰":
                    potential_xd['prob'] += 0.5
            if self.bi[-1]['fx_mark'] == 'd' and "向下笔新低背驰" in self.status_bi.keys():
                potential_xd['prob'] += 0.5
        else:
            raise ValueError
        return potential_xd

    @property
    def chan_result(self):
        return pd.DataFrame(self.kline)

    @property
    def status_fx(self):
        """分型状态"""
        try:
            table = dict()
            fx = self.fx
            if fx[-1]['fx_mark'] == "d":
                table['最近一个分型为底分型'] = {"price": fx[-1]['fx'], "dt": fx[-1]['dt'], "kind": "买"}

            elif fx[-1]['fx_mark'] == "g":
                table['最近一个分型为顶分型'] = {"price": fx[-1]['fx'], "dt": fx[-1]['dt'], "kind": "卖"}
            else:
                raise ValueError

            fx_d = [x for x in fx if x['fx_mark'] == 'd']
            if fx_d[-1]['fx'] > fx_d[-2]['fx']:
                table['最近两个底分型趋势向上'] = {"price": fx_d[-1]['fx'], "dt": fx_d[-1]['dt'], "kind": "买"}

            fx_g = [x for x in fx if x['fx_mark'] == 'g']
            if fx_g[-1]['fx'] < fx_g[-2]['fx']:
                table['最近两个顶分型趋势向下'] = {"price": fx_g[-1]['fx'], "dt": fx_g[-1]['dt'], "kind": "卖"}

            return table
        except:
            return None

    @property
    def status_bi(self):
        """笔状态"""
        try:
            table = dict()
            k_bi = self.bi
            if k_bi[-1]['fx_mark'] == 'g' and k_bi[-3]['fx_mark'] == 'g':
                if k_bi[-1]['bi'] < k_bi[-3]['bi']:
                    s = '向上笔不创新高'
                    if k_bi[-2]['bi'] < k_bi[-5]['bi']:
                        s += "，且最近完成的两个向下笔之间有重叠"
                        if k_bi[-1]['bi'] < k_bi[-4]['bi']:
                            s += "，且不升破前一向上笔的低点"
                    table[s] = {"price": k_bi[-1]['bi'], "dt": k_bi[-1]['dt'], "kind": "卖"}
                else:
                    zs1 = [k_bi[-2]['dt'], k_bi[-1]['dt']]
                    zs2 = [k_bi[-4]['dt'], k_bi[-3]['dt']]
                    direction = "up"
                    bc = self.cal_bei_chi(zs1, zs2, direction, mode='bi')
                    if bc == "背驰" and direction == "up":
                        table['向上笔新高背驰'] = {"price": k_bi[-1]['bi'], "dt": k_bi[-1]['dt'], "kind": "卖"}

            elif k_bi[-1]['fx_mark'] == 'd' and k_bi[-3]['fx_mark'] == 'd':
                if k_bi[-1]['bi'] > k_bi[-3]['bi']:
                    s = '向下笔不创新低'
                    if k_bi[-2]['bi'] > k_bi[-5]['bi']:
                        s += "，且最近完成的两个向上笔之间有重叠"
                        if k_bi[-1]['bi'] > k_bi[-4]['bi']:
                            s += "，且不跌破前一向下笔的高点"
                    table[s] = {"price": k_bi[-1]['bi'], "dt": k_bi[-1]['dt'], "kind": "买"}
                else:
                    zs1 = [k_bi[-2]['dt'], k_bi[-1]['dt']]
                    zs2 = [k_bi[-4]['dt'], k_bi[-3]['dt']]
                    direction = "down"
                    bc = self.cal_bei_chi(zs1, zs2, direction, mode='bi')
                    if bc == "背驰" and direction == "down":
                        table['向下笔新低背驰'] = {"price": k_bi[-1]['bi'], "dt": k_bi[-1]['dt'], "kind": "买"}
            else:
                raise ValueError("笔分型识别错误")
            return table
        except:
            return None

    @property
    def status_xd(self):
        """线段状态"""
        try:
            table = dict()
            if len(self.xd) >= 5:
                k_xd = self.xd
                price = k_xd[-1]['xd']
                dt = k_xd[-1]['dt']
                if k_xd[-1]['fx_mark'] == "g" and k_xd[-3]['fx_mark'] == "g":
                    if k_xd[-1]['xd'] < k_xd[-3]['xd']:
                        table["向上线段不创新高"] = {"price": price, "dt": dt, "kind": "卖"}
                    else:
                        direction = "up"
                        zs1 = [k_xd[-2]['dt'], k_xd[-1]['dt']]
                        zs2 = [k_xd[-4]['dt'], k_xd[-3]['dt']]
                        bc = self.cal_bei_chi(zs1, zs2, direction, mode='xd')
                        if bc == "背驰" and direction == "up":
                            table['向上线段新高背驰'] = {"price": price, "dt": dt, "kind": "卖"}

                elif k_xd[-1]['fx_mark'] == "d" and k_xd[-3]['fx_mark'] == "d":
                    if k_xd[-1]['xd'] > k_xd[-3]['xd']:
                        table["向下线段不创新低"] = {"price": price, "dt": dt, "kind": "买"}
                    else:
                        direction = "down"
                        zs1 = [k_xd[-2]['dt'], k_xd[-1]['dt']]
                        zs2 = [k_xd[-4]['dt'], k_xd[-3]['dt']]
                        bc = self.cal_bei_chi(zs1, zs2, direction, mode='xd')
                        if bc == "背驰" and direction == "down":
                            table['向下线段新低背驰'] = {"price": price, "dt": dt, "kind": "买"}

                else:
                    raise ValueError("线段分型识别错误")
            return table
        except:
            return None

    @property
    def status_zs(self):
        """中枢状态"""
        try:
            table = dict()
            xds = self.xd[-5:]
            price = xds[-1]['xd']
            dt = xds[-1]['dt']

            zs_g = min([x['xd'] for x in xds[:4] if x['fx_mark'] == 'g'])
            zs_d = max([x['xd'] for x in xds[:4] if x['fx_mark'] == 'd'])

            if xds[-1]['fx_mark'] == "g" and xds[-1]['xd'] < zs_d:
                # 找第三卖点是否形成
                table['中枢下移'] = {"price": price, "dt": dt, "kind": "卖"}
            elif xds[-1]['fx_mark'] == "d" and xds[-1]['xd'] > zs_g:
                # 找第三买点是否形成
                table['中枢上移'] = {"price": price, "dt": dt, "kind": "买"}
            else:
                table['中枢震荡'] = {"price": price, "dt": dt, "kind": "买"}

            return table
        except:
            return None

    @property
    def status(self):
        table = dict()
        if self.status_fx:
            table.update(self.status_fx)

        if self.status_bi:
            table.update(self.status_bi)

        if self.status_xd:
            table.update(self.status_xd)

        if self.status_zs:
            table.update(self.status_zs)

        return table

    def is_third_buy(self):
        """判断当下是否是三买"""
        status_zs = self.status_zs
        if status_zs and status_zs.get("中枢上移", None):
            return True
        else:
            return False

    def is_potential_third_buy(self):
        """判断当下是否是潜在的三买"""
        try:
            potential_xd = self.xd_end_potential()
            if potential_xd['fx_mark'] == 'd' and potential_xd['prob'] == 1:
                zs_g = min([x['xd'] for x in self.xd[-5:] if x['fx_mark'] == 'g'])
                if potential_xd['xd'] > zs_g:
                    return True
            return False
        except:
            return False

    def is_third_sell(self):
        """判断当下是否是三卖"""
        status_zs = self.status_zs
        if status_zs and status_zs.get("中枢下移", None):
            return True
        else:
            return False

    def is_potential_third_sell(self):
        """判断当下是否是潜在的三卖"""
        try:
            potential_xd = self.xd_end_potential()
            if potential_xd['fx_mark'] == 'g' and potential_xd['prob'] == 1:
                zs_d = max([x['xd'] for x in self.xd[-5:] if x['fx_mark'] == 'd'])
                if potential_xd['xd'] < zs_d:
                    return True
            return False
        except:
            return False

    def is_xd_buy(self):
        """判断当下是否是线段买点（即同级别分解买点）"""
        status_xd = self.status_xd
        names = ["向下线段不创新低", '向下线段新低背驰']
        if status_xd and (status_xd.get(names[0], None) or status_xd.get(names[1], None)):
            return True
        else:
            return False

    def is_potential_xd_buy(self):
        """判断当下是否是潜在的线段买点（即同级别分解买点）"""
        try:
            potential_xd = self.xd_end_potential()
            if potential_xd['fx_mark'] == 'd' and potential_xd['prob'] == 1:
                k_xd = self.xd
                direction = "down"
                zs1 = [k_xd[-1]['dt'], potential_xd['dt']]
                zs2 = [k_xd[-3]['dt'], k_xd[-2]['dt']]
                bc = self.cal_bei_chi(zs1, zs2, direction, mode='xd')
                if bc == "背驰" or potential_xd['xd'] >= self.xd[-2]['xd']:
                    return True
            return False
        except:
            return False

    def is_xd_sell(self):
        """判断当下是否是线段卖点（即同级别分解卖点）"""
        status_xd = self.status_xd
        names = ["向上线段不创新高", '向上线段新高背驰']
        if status_xd and (status_xd.get(names[0], None) or status_xd.get(names[1], None)):
            return True
        else:
            return False

    def is_potential_xd_sell(self):
        """判断当下是否是潜在的线段卖点（即同级别分解卖点）"""
        try:
            potential_xd = self.xd_end_potential()
            if potential_xd['fx_mark'] == 'g' or potential_xd['prob'] == 1:
                k_xd = self.xd
                direction = "up"
                zs1 = [k_xd[-1]['dt'], potential_xd['dt']]
                zs2 = [k_xd[-3]['dt'], k_xd[-2]['dt']]
                bc = self.cal_bei_chi(zs1, zs2, direction, mode='xd')
                if bc == "背驰" or potential_xd['xd'] <= self.xd[-2]['xd']:
                    return True
            return False
        except:
            return False


class SolidAnalyze:
    """多级别（日线、30分钟、5分钟、1分钟）K线联合分析"""

    def __init__(self, klines):
        """

        :param klines: dict
            key 为K线级别名称；value 为对应的K线数据，K线数据基本格式参考 KlineAnalyze
            example: {"日线": df, "30分钟": df, "5分钟": df, "1分钟": df,}
        """
        self.kas = dict()
        self.freqs = list(klines.keys())
        for freq, kline in klines.items():
            ka = KlineAnalyze(kline)
            self.kas[freq] = ka

    def _validate_freq(self, freq):
        assert freq in self.freqs, "‘%s’不在级别列表（%s）中" % (freq, "|".join(self.freqs))

    @property
    def signals(self):
        signals = []
        for freq, ka in self.kas.items():
            for k, v in ka.status.items():
                v["name"] = freq + k
                signals.append(v)
        return signals

    @staticmethod
    def up_zs_number(ka):
        # 检查三买前面的连续向上中枢数量
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

    def is_potential_third_buy(self, freq):
        """判断某一级别是否有潜力形成三买信号"""
        self._validate_freq(freq)
        ka = self.kas[freq]

        if ka.is_potential_third_buy():
            n = self.up_zs_number(ka)
            p_xd = ka.xd_end_potential()
            res = {
                "操作提示": freq + "三买（潜力股）",
                "出现时间": p_xd['dt'],
                "确认时间": p_xd['dt'],
                "其他信息": f"向上中枢数量为{n}，三买潜力为{p_xd['prob']}"
            }
        else:
            res = None
        return res

    def is_third_buy(self, freq):
        """判断某一级别是否有三买信号

        一个第三类买点，至少需要有5段次级别的走势，前三段构成中枢，第四段离开中枢，第5段构成第三类买点。
        """
        self._validate_freq(freq)
        signals = self.signals
        core = freq + "中枢上移"
        ka = self.kas[freq]
        if len(ka.xd) < 3:
            return None
        if core in [x['name'] for x in signals]:
            dt2 = [x for x in ka.bi if x['dt'] >= ka.xd[-1]['dt']][2]['dt']
            n = self.up_zs_number(ka)
            res = {
                "操作提示": freq + "三买",
                "出现时间": ka.xd[-1]['dt'],
                "确认时间": dt2,
                "其他信息": "向上中枢数量为%i" % n
            }
        else:
            res = None
        return res

    def check_third_buy(self, freqs):
        """在多个级别中分别检查三买和潜在三买信号

        :param freqs: list of str
            级别名称列表，如 ['5分钟', '30分钟', '日线']
        :return: list of dict
        """
        tb = []
        for freq in freqs:
            b1 = self.is_third_buy(freq)
            b2 = self.is_potential_third_buy(freq)
            if b1:
                tb.append(b1)
            if b2:
                tb.append(b2)
        return tb

    @staticmethod
    def down_zs_number(ka):
        """检查三卖前面的连续向下中枢数量"""
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

    def is_potential_third_sell(self, freq):
        """判断某一级别是否有潜在三卖信号

        一个第三类卖点，至少需要有5段次级别的走势，前三段构成中枢，第四段离开中枢，第5段构成第三类卖点。
        """
        self._validate_freq(freq)
        ka = self.kas[freq]

        if ka.is_potential_third_sell():
            n = self.down_zs_number(ka)
            p_xd = ka.xd_end_potential()
            res = {
                "操作提示": freq + "三卖（潜力股）",
                "出现时间": p_xd['dt'],
                "确认时间": p_xd['dt'],
                "其他信息": f"向下中枢数量为{n}，三卖潜力为{p_xd['prob']}"
            }
        else:
            res = None
        return res

    def is_third_sell(self, freq):
        """判断某一级别是否有三卖信号

        一个第三类卖点，至少需要有5段次级别的走势，前三段构成中枢，第四段离开中枢，第5段构成第三类卖点。
        """
        self._validate_freq(freq)
        signals = self.signals
        core = freq + "中枢下移"
        ka = self.kas[freq]
        if len(ka.xd) < 3:
            return None
        if core in [x['name'] for x in signals]:
            dt2 = [x for x in ka.bi if x['dt'] >= ka.xd[-1]['dt']][2]['dt']
            n = self.down_zs_number(ka)
            res = {
                "操作提示": freq + "三卖",
                "出现时间": ka.xd[-1]['dt'],
                "确认时间": dt2,
                "其他信息": "向下中枢数量为%i" % n
            }
        else:
            res = None
        return res

    def check_third_sell(self, freqs):
        """在多个级别中分别检查三卖信号

        :param freqs: list of str
            级别名称列表，如 ['5分钟', '30分钟', '日线']
        :return: list of dict
        """
        ts = []
        for freq in freqs:
            s1 = self.is_third_sell(freq)
            if s1:
                ts.append(s1)
        return ts

    def is_xd_buy(self, freq):
        """判断线段买点

        逻辑：中枢震荡和中枢上移过程中的“向下线段不创新低”和“向下线段新低背驰信号”有交易价值。

        :param freq:
        :return:
        """
        ka = self.kas[freq]
        signals = self.signals
        if [x for x in signals if x['name'] in [freq+"中枢震荡", freq+"中枢上移"]]:
            cons = [freq+"向下线段不创新低", freq+"向下线段新低背驰"]
            signal = [x for x in signals if x['name'] in cons]
            if signal:
                assert len(signal) == 1, "线段买点信号错误，%s" % str(signal)
                signal = signal[0]
                dt2 = [x for x in ka.bi if x['dt'] >= ka.xd[-1]['dt']][2]['dt']
                res = {
                    "操作提示": freq + "线买",
                    "出现时间": signal['dt'],
                    "确认时间": dt2,
                    "其他信息": signal['name']
                }
                return res
        return None

    def check_xd_buy(self, freqs):
        """在多个级别中检查线段买点信号

        :param freqs: list of str
            级别名称列表，如 ['5分钟', '30分钟', '日线']
        :return: list of dict
        """
        xb = []
        for freq in freqs:
            b1 = self.is_xd_buy(freq)
            if b1:
                xb.append(b1)
        return xb

    def is_xd_sell(self, freq):
        """判断线段卖点

        逻辑：中枢震荡和中枢下移过程中的“向上线段不创新高”和“向上线段新高背驰”是卖点。

        :param freq:
        :return:
        """
        ka = self.kas[freq]
        signals = self.signals
        if [x for x in signals if x['name'] in [freq+"中枢震荡", freq+"中枢下移"]]:
            cons = [freq+"向上线段不创新高", freq+"向上线段新高背驰"]
            signal = [x for x in signals if x['name'] in cons]
            if signal:
                assert len(signal) == 1, "线段卖点信号错误，%s" % str(signal)
                signal = signal[0]
                dt2 = [x for x in ka.bi if x['dt'] >= ka.xd[-1]['dt']][2]['dt']
                res = {
                    "操作提示": freq + "线卖",
                    "出现时间": signal['dt'],
                    "确认时间": dt2,
                    "其他信息": signal['name']
                }
                return res
        return None

    def check_xd_sell(self, freqs):
        """在多个级别中检查线段卖点信号

        :param freqs: list of str
            级别名称列表，如 ['5分钟', '30分钟', '日线']
        :return: list of dict
        """
        xs = []
        for freq in freqs:
            b1 = self.is_xd_sell(freq)
            if b1:
                xs.append(b1)
        return xs


