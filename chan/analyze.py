# coding: utf-8

import pandas as pd
from copy import deepcopy


def preprocess(kline):
    """去除包含关系

    :param kline: pd.DataFrame
        K线，columns = ["symbol", "dt", "open", "close", "high", "low", "vol"]
    :return: list of dict

    """
    k_new = []

    first_row = kline.iloc[0].to_dict()
    last = deepcopy(first_row)
    k_new.append(first_row)

    for i, row in kline.iterrows():
        # first row
        if i == 0:
            continue

        # update direction
        if last['high'] >= k_new[-1]['high']:
            direction = 'up'
        else:
            direction = 'down'

        # 包含关系处理
        row = row.to_dict()
        cur_h, cur_l = row['high'], row['low']
        last_h, last_l = last['high'], last['low']

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

            last = deepcopy(row)
            last['high'] = last_h
            last['low'] = last_l
        else:
            # 无包含关系，更新 K 线
            k_new.append(last)
            last = deepcopy(row)

        if i == len(kline):
            k_new.append(last)

    # print('k_new nums:', len(k_new))
    return k_new


def find_fx(k_new):
    """查找顶分型和底分型"""
    k1 = k_new[0]
    k2 = k_new[1]

    k_fx = []
    for k in k_new[2:]:
        if k2['high'] > k1['high'] and k2['high'] > k['high']:
            k2['fx_mark'] = 'g'
            k2['fx'] = k2['high']
        elif k2['low'] < k1['low'] and k2['low'] < k['low']:
            k2['fx_mark'] = 'd'
            k2['fx'] = k2['low']

        k_fx.append(k2)
        k1, k2, = k2, k

    # print("fx nums:", len(k_fx))
    return k_fx


def find_bi(k_fx):
    """查找分型标记"""
    k_bi = []

    potential = None
    k_count = 0

    for k in k_fx:
        # print(k)
        if not potential:
            # 查找第一个潜在笔分型点
            if "fx_mark" in k.keys():
                potential = deepcopy(k)
            else:
                continue

        # 验证各分型点是否能够作为笔分型点
        if "fx_mark" in k.keys():
            if k['fx_mark'] == potential['fx_mark']:
                if k['fx_mark'] == "g" and k['fx'] > potential['fx']:
                    potential = deepcopy(k)
                elif k['fx_mark'] == "d" and k['fx'] < potential['fx']:
                    potential = deepcopy(k)
                else:
                    continue
                k_count = 0
            else:
                if k_count >= 3:
                    potential['bi'] = potential['fx']
                    k_bi.append(potential)
                    # print("potential old: ", k_count, potential)
                    k_count = 0
                    potential = deepcopy(k)
                    # print("potential new: ", k_count, potential)
                # k_count = 0
        else:
            # print(k_count, k)
            k_count += 1

    potential['bi'] = potential['fx']
    k_bi.append(potential)
    # print("bi nums:", len(k_bi))
    return k_bi


def find_xd(k_bi):
    """查找线段标记"""
    k_xd = []
    i = 0
    potential = deepcopy(k_bi[i])

    while i < len(k_bi)-3:
        k1, k2, k3 = k_bi[i+1], k_bi[i+2], k_bi[i+3]

        if potential['fx_mark'] == "d":
            assert k2['fx_mark'] == 'd'
            if k3['bi'] < k1['bi']:
                potential['xd'] = potential['bi']
                k_xd.append(potential)
                i += 1
                potential = deepcopy(k_bi[i])
            else:
                i += 2

        elif potential['fx_mark'] == "g":
            assert k2['fx_mark'] == 'g'
            if k3['bi'] > k1['bi']:
                potential['xd'] = potential['bi']
                k_xd.append(potential)
                i += 1
                potential = deepcopy(k_bi[i])
            else:
                i += 2

        else:
            raise ValueError

    potential['xd'] = potential['bi']
    k_xd.append(potential)
    # print("xd nums:", len(k_xd))
    # 待完善：如果两个线段标记之间无有效笔标记，则这两个线段标记无效。

    return k_xd


def find_zs(k_xd):
    """查找中枢"""
    k_zs = []
    zs_xd = []

    for i in range(len(k_xd)-1):
        if len(zs_xd) < 4:
            zs_xd.append(k_xd[i])
            continue

        zs_d = max([x['xd'] for x in zs_xd if x['fx_mark'] == 'd'])
        zs_g = min([x['xd'] for x in zs_xd if x['fx_mark'] == 'g'])
        # zs = (zs_d, zs_g)
        xd_p1 = zs_xd[-1]['xd']
        xd_p2 = k_xd[i]['xd']
        if zs_g > xd_p2 > zs_d:
            zs_xd.append(k_xd[i])
        else:
            if xd_p1 > zs_g and xd_p2 > zs_g:
                # 线段在中枢上方结束，形成三买
                k_zs.append({'zs': (zs_d, zs_g), "zs_xd": deepcopy(zs_xd)})
                zs_xd = [k_xd[i]]
            elif xd_p1 < zs_g and xd_p2 < zs_g:
                # 线段在中枢下方结束，形成三卖
                k_zs.append({'zs': (zs_d, zs_g), "zs_xd": deepcopy(zs_xd)})
                zs_xd = [k_xd[i]]
            else:
                zs_xd.append(k_xd[i])

    return k_zs


def kline_analyze(kline):
    """使用缠论分析 K 线"""
    k_new = preprocess(kline)
    k_fx = find_fx(k_new)
    k_bi = find_bi(k_fx)
    k_xd = find_xd(k_bi)

    df_fx = pd.DataFrame(k_fx)[['dt', 'fx_mark', 'fx']]
    kline = kline.merge(df_fx, how='left', on='dt')

    df_bi = pd.DataFrame(k_bi)[['dt', 'bi']]
    kline = kline.merge(df_bi, how='left', on='dt')

    df_xd = pd.DataFrame(k_xd)[['dt', 'xd']]
    kline = kline.merge(df_xd, how='left', on='dt')
    return kline


class KlineAnalyze(object):
    def __init__(self, kline):
        self.kline = kline
        self.k_new = preprocess(self.kline)
        self.k_fx = find_fx(self.k_new)
        self.k_bi = find_bi(self.k_fx)
        self.k_xd = find_xd(self.k_bi)

    @property
    def chan_result(self):
        k = deepcopy(self.kline)
        df_fx = pd.DataFrame(self.k_fx)[['dt', 'fx_mark', 'fx']]
        k = k.merge(df_fx, how='left', on='dt')

        df_bi = pd.DataFrame(self.k_bi)[['dt', 'bi']]
        k = k.merge(df_bi, how='left', on='dt')

        df_xd = pd.DataFrame(self.k_xd)[['dt', 'xd']]
        k = k.merge(df_xd, how='left', on='dt')
        return k

    @property
    def status_bi(self):
        k1, k2, k3 = self.k_new[-1], self.k_new[-2], self.k_new[-3]
        if k1['high'] > k2['high'] > k3['high']:
            s = "向上笔延伸中"
        elif k1['low'] < k2['low'] < k3['low']:
            s = "向下笔延伸中"
        elif max([k1['high'], k2['high'], k3['high']]) == k2['high']:
            s = "顶分型构造中"
        elif min([k1['low'], k2['low'], k3['low']]) == k2['low']:
            s = "底分型构造中"
        else:
            raise ValueError
        return s

    @property
    def status_xd(self):
        last = self.k_xd[-1]
        if last['fx_mark'] == 'g':
            s = "向下线段延伸中"
        elif last['fx_mark'] == 'd':
            s = "向上线段延伸中"
        else:
            raise ValueError
        return s

    @property
    def status_zs(self):
        if len(self.k_xd) < 5:
            return "没有中枢"

        xd1 = (self.k_xd[-5], self.k_xd[-4])
        xd2 = (self.k_xd[-4], self.k_xd[-3])
        # xd3 = (self.k_xd[-3], self.k_xd[-2])
        xd4 = (self.k_xd[-2], self.k_xd[-1])
        zs = (min([xd2[0]['fx'], xd2[1]['fx']]), max([xd2[0]['fx'], xd2[1]['fx']]))

        if xd1[0]['fx_mark'] == "g" and xd4[1]['fx'] < zs[0]:
            # 找第三卖点是否形成
            s = '中枢下移'
        elif xd1[0]['fx_mark'] == "d" and xd4[1]['fx'] > zs[1]:
            s = '中枢上移'
        else:
            s = '中枢震荡'
        return s





