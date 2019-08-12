# coding: utf-8
import pandas as pd


def preprocess(kline):
    """去除包含关系

    :param kline: pd.DataFrame
        K线，columns = ["symbol", "dt", "open", "close", "high", "low", "vol"]
    :return: pd.DataFrame
    """
    kline['high_m'] = None
    kline['low_m'] = None

    # 首行处理
    last_h = kline.loc[0, 'high']
    last_l = kline.loc[0, 'low']

    if last_h >= kline.loc[1, 'high']:
        direction = 0  # 下跌
    else:
        direction = 1  # 上涨

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

        # 当前行与上一行之间无包含关系，更新上一行 high low
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
    kline_new = kline[['symbol', 'dt', 'open', 'close', 'high_m', 'low_m', 'vol']]
    kline_new = kline_new.rename({"high_m": "high", "low_m": "low"}, axis='columns')
    kline_new = kline_new.dropna(subset=['high', 'low'])
    kline_new = kline_new.reset_index(drop=True)

    return kline_new


def find_fx(kline):
    """找出全部分型

    0 - 顶分型
    1 - 底分型

    一个分型能否成为笔的一部分，至少需要看到后面两个分型的情况才能确定。

    :param kline: pd.DataFrame
        经过预处理，去除了包含关系的 K 线，
        columns = ["symbol", "dt", "open", "close", "high", "low", "vol"]
    :return: kline: pd.DataFrame
    """
    kline['fx'] = None
    kline['fx_mark'] = None
    last_fx_mark = 0

    for i in range(1, len(kline) - 1):
        data = kline.iloc[i-1: i+2]
        row = kline.iloc[i]
        if max(data['high']) == row['high'] and last_fx_mark == 1:
            kline.loc[row.name, 'fx_mark'] = 0
            kline.loc[row.name, 'fx'] = kline.loc[i, 'high']
            last_fx_mark = 0
        elif min(data['low']) == row['low'] and last_fx_mark == 0:
            kline.loc[row.name, 'fx_mark'] = 1
            kline.loc[row.name, 'fx'] = kline.loc[i, 'low']
            last_fx_mark = 1
        else:
            continue
    return kline


def find_bi(kline):
    """笔标记：确定哪些分型能够成为笔的一部分

    一个分型能否成为笔的一部分，至少需要看到后面两个分型的情况才能确定。

    0 - 顶分型
    1 - 底分型

    :param kline: pd.DataFrame
        经过预处理，去除了包含关系，并标记出所有分型的K线
        columns = ["symbol", "dt", "open", "close", "high", "low", "vol", 'fx]
    :return: kline: pd.DataFrame
    """

    fx_list = []
    for i, row in kline.iterrows():
        if row['fx_mark'] in [0, 1]:
            row_dict = row.to_dict()
            row_dict['id'] = i
            fx_list.append(row_dict)

    if fx_list[0]['fx_mark'] != 1:
        fx_list.pop(0)

    assert fx_list[0]['fx_mark'] == 1, "第一个分型标记不是0"

    valid_fx_list = []
    potential_valid = None

    i = 0
    # 一旦确定一个有效的分型，则一个不同类型的潜在有效分型也得到确认
    while i < len(fx_list)-1:
        if len(valid_fx_list) == 0:
            # 查找第一个有效的底分型
            if fx_list[i]['fx_mark'] == 1 and fx_list[i+1]['id'] - fx_list[i]['id'] > 3:
                valid_fx_list.append(fx_list[i])
                potential_valid = fx_list[i+1]
        else:
            # 对每一个潜在有效分型，只有当一个相距至少4根K线的不同类型分型出现后，才能确认其有效性
            if fx_list[i]['fx_mark'] == potential_valid['fx_mark']:
                # 更新 potential valid
                if potential_valid['fx_mark'] == 0 and fx_list[i]['fx'] > potential_valid['fx']:
                    potential_valid = fx_list[i]
                elif potential_valid['fx_mark'] == 1 and fx_list[i]['fx'] < potential_valid['fx']:
                    potential_valid = fx_list[i]
            else:
                # 确认 potential valid
                if fx_list[i]['id'] - potential_valid['id'] > 3:
                    valid_fx_list.append(potential_valid)
                    potential_valid = fx_list[i]
        i += 1

    # 整理结果输出
    for i, fx in enumerate(valid_fx_list):
        fx['bi_mark'] = int(i)
        if fx['fx_mark'] == 0:
            fx['bi'] = fx['high']
        else:
            fx['bi'] = fx['low']

    fx_df = pd.DataFrame(valid_fx_list)
    fx_df = fx_df[['dt', 'bi', 'bi_mark']]
    kline = kline.merge(fx_df, how='left', on='dt')
    return kline


def find_xd(kline):
    """线段查找。输入：确定了分型的 K 线；输出：加入线段查找结果的 K 线

    :param kline: pd.DataFrame
        K线，columns = ["symbol", "dt", "open", "close", "high", "low", "vol", 'bi', 'bi_mark', 'fx', 'fx_mark']
    :return: pd.DataFrame
        K线，columns = ['symbol', 'dt', 'open', 'close', 'high', 'low', 'vol', 'fx', 'fx_mark', 'bi', 'bi_mark',
                       'xd', 'xd_mark']
    """
    kline_new = kline[["dt", 'bi', 'bi_mark', 'fx', 'fx_mark']]
    kline_new = kline_new.dropna()
    kline_new = kline_new.reset_index(drop=True)
    assert kline_new.iloc[0]['fx_mark'] == 1, "分型标记必选从 1 开始"

    # 利用向上笔查找潜在的线段顶分型，利用向下笔查找潜在的线段底分型
    kline_new['xd_fx'] = None
    kline_new['xd'] = None
    for i in range(1, len(kline_new)-2):
        last = kline_new.iloc[i-2]['bi']
        cur = kline_new.iloc[i]['bi']
        next_ = kline_new.iloc[i+2]['bi']
        if i % 2 == 0:
            if min([last, cur, next_]) == cur:
                kline_new.loc[i, 'xd_fx'] = 1
                kline_new.loc[i, 'xd'] = cur
        else:
            if max([last, cur, next_]) == cur:
                kline_new.loc[i, 'xd_fx'] = 0
                kline_new.loc[i, 'xd'] = cur

    # 确认线段分型的有效性：至少存在一个反方向的一笔
    potential_valid = None
    valid_list = []

    for i, row in kline_new.iterrows():
        if row['xd_fx'] not in [0, 1]:
            continue

        if not potential_valid:
            # 找到第一个潜在的有效线段分型
            potential_valid = row.to_dict()
            potential_valid['id'] = i
        else:
            # 对潜在分型进行相应的判断
            if row['xd_fx'] == potential_valid['xd_fx']:
                # update 潜在顶分型
                if potential_valid['xd_fx'] == 0 and row['xd'] > potential_valid['xd']:
                    potential_valid = row.to_dict()
                    potential_valid['id'] = i
                # update 潜在底分型
                if potential_valid['xd_fx'] == 1 and row['xd'] < potential_valid['xd']:
                    potential_valid = row.to_dict()
                    potential_valid['id'] = i
            else:
                # 判断潜在分型的有效性
                # 取两个不同类型分型之间的数据，不包括两个分型点
                bi_part = kline_new.iloc[potential_valid['id']+1:i]
                if sum(bi_part['fx_mark']) >= 1:  # 两个有效线段分型之间至少存在一笔
                    valid_list.append(potential_valid)

                potential_valid = row.to_dict()
                potential_valid['id'] = i

    valid_df = pd.DataFrame(valid_list)
    valid_df['xd_mark'] = [x for x in range(len(valid_df))]

    valid_df = valid_df[['dt', 'xd', 'xd_mark']]
    kline = kline.merge(valid_df, how='left', on='dt')
    print(kline.columns)
    return kline



