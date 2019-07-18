# coding: utf-8
"""

step 1. 去除包含关系
step 2. 找出全部分型，并验证有效性
step 3. 标记线段
step 4. 标记中枢
====================================================================
"""


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
            continue

        kline.loc[i-1, 'high_m'] = last_h
        kline.loc[i-1, 'low_m'] = last_l

        # 更新 direction, last_h, last_l
        if last_h >= cur_h:
            direction = 0  # 下跌
        else:
            direction = 1  # 上涨

        last_h = cur_h
        last_l = cur_l

    return kline


def find_fx(kline):
    """找出全部分型，并验证有效性

    0 - 顶分型
    1 - 底分型

    :param kline: pd.DataFrame
        经过预处理，去除了包含关系的 K 线
    :return:
    """

    kline_new = kline.dropna()
    kline['fx'] = None

    for i in range(1, len(kline_new)-1):
        data = kline_new.iloc[i-1: i+2]
        row = kline_new.iloc[i]

        if max(data['high_m']) == row['high_m']:
            kline.loc[row.name, 'fx'] = 0
        elif min(data['low_m']) == row['low_m']:
            kline.loc[row.name, 'fx'] = 1
        else:
            continue

    return kline


