# coding: utf-8


def find_xd(kline):
    """线段查找。输入：确定了分型的 K 线；输出：加入线段查找结果的 K 线"""

    # 找出所有可能的线段终点
    gd1 = kline[kline['bi_mark'] == 0].iloc[0]
    gd2 = kline[kline['bi_mark'] == 2].iloc[0]

    if gd1['high'] < gd2['high']:
        direction = "向上"
    else:
        direction = "向下"

    i = 4
    mark = 0
    kline['xd_mark'] = None

    while i <= kline['bi_mark'].max():
        gd1 = kline[kline['bi_mark'] == i-3].iloc[0]
        dd1 = kline[kline['bi_mark'] == i-2].iloc[0]
        gd2 = kline[kline['bi_mark'] == i-1].iloc[0]
        dd2 = kline[kline['bi_mark'] == i].iloc[0]

        # 第二个顶分型的最高价小于或等于第一个顶分型的最高价，向上过程有可能结束
        if direction == "向上" and gd2['high'] <= gd1['high']:
            kline.loc[gd1.name, 'xd_mark'] = mark
            mark += 1
            direction = "向下"

        # 第二个底分型的最低价大于或等于第一个底分型的最低价，向下过程有可能结束
        elif direction == "向下" and dd2['low'] >= dd1['low']:
            kline.loc[dd1.name, 'xd_mark'] = mark
            mark += 1
            direction = "向上"

        i += 2

    # TODO(zengbin): 检查线段的有效性

    return kline

