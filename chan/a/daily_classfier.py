# coding: utf-8

from datetime import datetime, timedelta
import tushare as ts

# 首次使用，需要设置token
# ts.set_token("******")


def daily_classifier(ts_code, trade_date, asset='E', return_central=False):
    """ A 股每日走势的分类

    asset 交易资产类型，可选值 E股票 I沪深指数

    使用该方法前，请仔细阅读：http://blog.sina.com.cn/s/blog_486e105c010009uy.html

    每个交易日产生 8 根 30 分钟 K 线，分别在前三根和最后三根中计算中枢，其结果分以下情况：
    1）没有中枢；
    2）仅有一个中枢，或计算得到的两个中枢区间有重叠；
    3）有两个中枢，且没有重叠。

    example:
    >>> kind, central = daily_classifier('600122.SH', "20190613", return_central=True)
    >>> print(kind, central)
    """

    start_date = datetime.strptime(trade_date, '%Y%m%d')
    end_date = start_date + timedelta(days=1)
    end_date = end_date.date().__str__().replace("-", "")

    df = ts.pro_bar(ts_code=ts_code, freq='30min', asset=asset,
                    start_date=trade_date, end_date=end_date)
    df.sort_values('trade_time', inplace=True)
    data = df[['ts_code', 'trade_time', 'high', 'low', 'close']].iloc[1:, :]
    data = data.reset_index(drop=True)
    assert len(data) == 8, "每个交易日，A股有且只有8跟30分钟K线"

    def _central(tri):
        c_low = max(tri['low'])
        c_high = min(tri['high'])
        if c_low >= c_high:
            # None means no central found
            central = None
        else:
            central = {
                "time_span": "%s - %s" % (tri.iloc[0, 1], tri.iloc[2, 1]),
                "price_span": (c_low, c_high)
            }
        return central

    first_central = _central(data.iloc[:3, :])
    last_central = _central(data.iloc[-3:, :])

    # 若两个中枢之间存在价格重叠部分，则第二个中枢不存在
    if first_central and last_central:
        fp = first_central['price_span']
        lp = last_central["price_span"]
        if fp[1] >= lp[0] >= fp[0] or fp[1] >= lp[1] >= fp[0]:
            last_central = None

    # 没有中枢的情况
    if first_central is None and last_central is None:
        kind = "最强单边走势"

    # 一个中枢的情况（平衡市）
    elif (first_central is None and last_central) or (first_central and last_central is None):
        max_p = max(data.iloc[:3, :]['close'])
        min_p = min(data.iloc[:3, :]['close'])

        # 1、在前三根30分钟K线出现当天高点
        if max(data['close']) == max_p:
            kind = "弱平衡市"

        # 2、在前三根30分钟K线出现当天低点
        elif min(data['close']) == min_p:
            kind = "强平衡市"

        # 3、在前三根30分钟K线不出现当天高低点
        else:
            kind = "转折平衡市"

    # 两个中枢的情况
    elif first_central and last_central:
        if first_central['price_span'][0] > last_central['price_span'][0]:
            kind = "向下两中枢走势"
        elif first_central['price_span'][0] < last_central['price_span'][0]:
            kind = "向上两中枢走势"
        else:
            raise ValueError("两中枢的最低价不可以相等")

    else:
        raise ValueError('中枢计算错误')

    if return_central:
        return kind, (first_central, last_central)
    else:
        return kind
