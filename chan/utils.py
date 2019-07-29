# coding: utf-8

from collections import OrderedDict


class OrderedAttrDict(OrderedDict):
    """OrderedDict that can get attribute by dot"""

    def __init__(self, *args, **kwargs):
        super(OrderedAttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


def preprocess(kline):
    """去除包含关系"""
    kline['high_m'] = None
    kline['low_m'] = None

    # 首行处理
    last_h = kline.loc[0, 'high']
    last_l = kline.loc[0, 'low']

    if last_h >= kline.loc[1, 'high']:
        direction = 0    # 下跌
    else:
        direction = 1    # 上涨

    for i, row in kline.iterrows():
        cur_h, cur_l = row['high'], row['low']

        # 左包含 or 右包含
        if (cur_h <= last_h and cur_l >= last_l) or (cur_h >= last_h and cur_l <= last_l):
            if direction == 0:
                last_h = min(last_h, cur_h)
                last_l = min(last_l, cur_l)
            elif direction == 1:
                last_h = max(last_h, cur_h)
                last_l = max(last_l, cur_l)
            else:
                raise ValueError

            # 尾行更新 high low
            if i == len(kline) - 1:
                kline.loc[i, 'high_m'] = last_h
                kline.loc[i, 'low_m'] = last_l
            continue

        # 当期行与上一行之间无包含关系，更新上一行 high low
        kline.loc[i-1, 'high_m'] = last_h
        kline.loc[i-1, 'low_m'] = last_l

        # 更新 direction, last_h, last_l
        if last_h >= cur_h:
            direction = 0  # 下跌
        else:
            direction = 1  # 上涨

        last_h = cur_h
        last_l = cur_l

    # 根据包含关系的检查结果，生成新的 K 线数据
    kline_new = kline[['symbol', 'dt', 'open', 'close', 'high_m', 'low_m']]
    kline_new = kline_new.rename({"high_m": "high", "low_m": "low"}, axis='columns')
    kline_new = kline_new.dropna(subset=['high', 'low'])
    kline_new = kline_new.reset_index(drop=True)

    return kline_new


def find_fx(kline):
    """找出全部分型，并验证有效性

    0 - 顶分型
    1 - 底分型
    2 - 无效分型

    :param kline: pd.DataFrame
        经过预处理，去除了包含关系的 K 线
    :return: kline: pd.DataFrame
    """
    kline['fx'] = None

    for i in range(1, len(kline) - 1):
        data = kline.iloc[i - 1: i + 2]
        row = kline.iloc[i]

        if max(data['high']) == row['high']:
            kline.loc[row.name, 'fx'] = 0
        elif min(data['low']) == row['low']:
            kline.loc[row.name, 'fx'] = 1
        else:
            continue

    # 确定分型的有效性：满足结合律；实现方式：从后往前，不满足结合律就处理成无效分型
    last_index = None

    for i in kline.index[::-1]:
        if kline.loc[i, 'fx'] not in [0, 1]:
            continue

        if kline.loc[i, 'fx'] in [0, 1]:
            if last_index is None:
                last_index = i
            else:
                curr_index = i
                if last_index - curr_index < 3:
                    kline.loc[last_index, 'fx'] = 2
                    kline.loc[curr_index, 'fx'] = 2
                    last_index = None
                else:
                    last_index = curr_index

    # 添加 笔标记 - 从第一个有效顶分型开始标记
    kline['bi_mark'] = None
    mark = 0
    for i, row in kline.iterrows():
        if mark == 0 and row['fx'] == 0:
            kline.loc[i, 'bi_mark'] = mark
            mark += 1
            continue

        if mark > 0 and row['fx'] in [0, 1]:
            kline.loc[i, 'bi_mark'] = mark
            mark += 1

    return kline


