# coding: utf-8

import traceback
from .analyze import is_bei_chi, KlineAnalyze, down_zs_number, up_zs_number


def __in_tolerance(base_price, latest_price, tolerance=0.03):
    """判断 latest_price 是否在 base_price 的容差范围内"""
    if (1 - tolerance) * base_price <= latest_price <= (1 + tolerance) * base_price:
        return True
    else:
        return False


def __get_sub_xds(ka, ka1):
    """根据上级别线段标记获取本级别最后一个走势的线段"""
    xds_l = [x for x in ka.xd if x['dt'] <= ka1.xd[-1]['dt']]
    xds_r = [x for x in ka.xd if x['dt'] > ka1.xd[-1]['dt']]
    if not xds_r:
        xds = [xds_l[-1]]
        return xds

    if xds_r[0]['fx_mark'] != ka1.xd[-1]['fx_mark'] and len(xds_l) > 0:
        xds = [xds_l[-1]] + xds_r
    else:
        xds = xds_r
    return xds


def is_first_buy(ka, ka1, ka2=None, tolerance=0.03):
    """确定某一级别一买，包括由盘整背驰引发的类一买
    注意：如果本级别上一级别的 ka 不存在，默认返回 False !!!

    :param ka: KlineAnalyze
        本级别
    :param ka1: KlineAnalyze
        上级别
    :param ka2: KlineAnalyze
        下级别，默认为 None
    :param tolerance: float
        相对于基准价格的操作容差，默认为 0.03，表示在基准价格附近上下3个点的波动范围内都是允许操作的
    :return:
    """

    if len(ka.xd) < 6 or not ka1.xd or ka1.xd[-1]['fx_mark'] == 'g':
        return False, None

    if ka1.xd[-1]['xd'] == ka1.bi[-1]['bi']:
        ka1.xd.pop(-1)
    else:
        return False, None

    b = False
    detail = {
        "标的代码": ka.symbol,
        "操作提示": "一买",
        "出现时间": "",
        "基准价格": 0,
        "其他信息": ""
    }

    # 趋势至少有5段；底背驰一定要创新低
    xds = __get_sub_xds(ka, ka1)
    if len(xds) >= 6 and xds[-1]['fx_mark'] == 'd' \
            and ka1.bi[-1]['fx_mark'] == 'd' and xds[-1]['xd'] < xds[-3]['xd']:
        zs1 = [xds[-2]['dt'], xds[-1]['dt']]
        zs2 = [xds[-4]['dt'], xds[-3]['dt']]
        base_price = xds[-1]['xd']
        if is_bei_chi(ka, zs1, zs2, direction='down', mode='xd') \
                and __in_tolerance(base_price, ka.latest_price, tolerance):
            detail["出现时间"] = xds[-1]['dt']
            detail["基准价格"] = base_price
            b = True

    if isinstance(ka2, KlineAnalyze) and (ka2.xd[-1]['fx_mark'] == 'g' or ka2.bi[-1]['fx_mark'] == 'g'):
        b = False
    return b, detail


def is_first_sell(ka, ka1, ka2=None, tolerance=0.03):
    """确定某一级别一卖，包括由盘整背驰引发的类一卖

    注意：如果本级别上一级别的 ka 不存在，默认返回 False !!!

    :param ka: KlineAnalyze
        本级别
    :param ka1: KlineAnalyze
        上级别
    :param ka2: KlineAnalyze
        下级别，默认为 None
    :param tolerance: float
        相对于基准价格的操作容差，默认为 0.03，表示在基准价格附近上下3个点的波动范围内都是允许操作的
    :return:
    """
    if len(ka.xd) < 6 or not ka1.xd or ka1.xd[-1]['fx_mark'] == 'd':
        return False, None

    if ka1.xd[-1]['xd'] == ka1.bi[-1]['bi']:
        ka1.xd.pop(-1)
    else:
        return False, None

    b = False
    detail = {
        "标的代码": ka.symbol,
        "操作提示": "一卖",
        "出现时间": "",
        "基准价格": 0,
        "其他信息": ""
    }

    # 趋势至少有5段；顶背驰一定要创新高
    xds = __get_sub_xds(ka, ka1)
    if len(xds) >= 6 and xds[-1]['fx_mark'] == 'g' \
            and ka1.bi[-1]['fx_mark'] == 'g' and xds[-1]['xd'] > xds[-3]['xd']:
        zs1 = [xds[-2]['dt'], xds[-1]['dt']]
        zs2 = [xds[-4]['dt'], xds[-3]['dt']]
        base_price = xds[-1]['xd']
        if is_bei_chi(ka, zs1, zs2, direction='up', mode='xd') \
                and __in_tolerance(base_price, ka.latest_price, tolerance):
            detail["出现时间"] = xds[-1]['dt']
            detail["基准价格"] = base_price
            b = True

    if isinstance(ka2, KlineAnalyze) and (ka2.xd[-1]['fx_mark'] == 'd' or ka2.bi[-1]['fx_mark'] == 'd'):
        b = False
    return b, detail


def is_second_buy(ka, ka1, ka2=None, tolerance=0.03):
    """确定某一级别二买，包括类二买

    注意：如果本级别上一级别的 ka 不存在，默认返回 False !!!

    :param ka: KlineAnalyze
        本级别
    :param ka1: KlineAnalyze
        上级别
    :param ka2: KlineAnalyze
        下级别，默认为 None
    :param tolerance: float
        相对于基准价格的操作容差，默认为 0.03，表示在基准价格附近上下3个点的波动范围内都是允许操作的
    :return:
    """
    if (not isinstance(ka, KlineAnalyze)) \
            or len(ka.xd) < 6 \
            or (not isinstance(ka1, KlineAnalyze))\
            or (not ka1.xd) \
            or ka1.xd[-1]['fx_mark'] == 'g':
        return False, None

    b = False
    detail = {
        "标的代码": ka.symbol,
        "操作提示": "二买",
        "出现时间": "",
        "基准价格": 0,
        "其他信息": ""
    }

    xds = __get_sub_xds(ka, ka1)
    base_price = xds[-1]['xd']
    # 次级别向下走势不创新低，就认为是类二买，其中第一个是真正的二买；
    # 如果一个向上走势内部已经有5段次级别走势，则认为该走势随后不再有二买机会
    if 3 <= len(xds) <= 4 and xds[-1]['fx_mark'] == 'd' \
            and ka1.bi[-1]['fx_mark'] == 'd' and xds[-1]['xd'] > xds[-3]['xd'] \
            and __in_tolerance(base_price, ka.latest_price, tolerance):
        detail["出现时间"] = xds[-1]['dt']
        detail["基准价格"] = base_price
        b = True

    if isinstance(ka2, KlineAnalyze) and (ka2.xd[-1]['fx_mark'] == 'g' or ka2.bi[-1]['fx_mark'] == 'g'):
        b = False
    return b, detail


def is_second_sell(ka, ka1, ka2=None, tolerance=0.03):
    """确定某一级别二卖，包括类二卖

    注意：如果本级别上一级别的 ka 不存在，默认返回 False !!!

    :param ka: KlineAnalyze
        本级别
    :param ka1: KlineAnalyze
        上级别
    :param ka2: KlineAnalyze
        下级别，默认为 None
    :param tolerance: float
        相对于基准价格的操作容差，默认为 0.03，表示在基准价格附近上下3个点的波动范围内都是允许操作的
    :return:
    """
    if (not isinstance(ka, KlineAnalyze)) \
            or len(ka.xd) < 6 \
            or (not isinstance(ka1, KlineAnalyze))\
            or (not ka1.xd) \
            or ka1.xd[-1]['fx_mark'] == 'd':
        return False, None

    b = False
    detail = {
        "标的代码": ka.symbol,
        "操作提示": "二卖",
        "出现时间": "",
        "基准价格": 0,
        "其他信息": ""
    }

    xds = __get_sub_xds(ka, ka1)
    base_price = xds[-1]['xd']

    if 3 <= len(xds) <= 4 and xds[-1]['fx_mark'] == 'g' and ka1.bi[-1]['fx_mark'] == 'g' \
            and xds[-1]['xd'] < xds[-3]['xd'] \
            and __in_tolerance(base_price, ka.latest_price, tolerance):
        detail["出现时间"] = xds[-1]['dt']
        detail["基准价格"] = base_price
        b = True

    if isinstance(ka2, KlineAnalyze) and (ka2.xd[-1]['fx_mark'] == 'd' or ka2.bi[-1]['fx_mark'] == 'd'):
        b = False
    return b, detail


def is_third_buy(ka, ka1=None, ka2=None, tolerance=0.03):
    """确定某一级别三买

    第三类买点: 一个第三类买点，至少需要有5段次级别的走势，前三段构成中枢，第四段离开中枢，第5段不跌回中枢。

    :param ka: KlineAnalyze
        本级别
    :param ka1: KlineAnalyze
        上级别，默认为 None
    :param ka2: KlineAnalyze
        下级别，默认为 None
    :param tolerance: float
        相对于基准价格的操作容差，默认为 0.03，表示在基准价格附近上下3个点的波动范围内都是允许操作的
    :return:
    """
    if len(ka.xd) < 6 or ka.xd[-1]['fx_mark'] == 'g':
        return False, None

    uz = up_zs_number(ka)
    zs_g = min([x['xd'] for x in ka.xd[-6:-1] if x['fx_mark'] == "g"])
    zs_d = max([x['xd'] for x in ka.xd[-6:-1] if x['fx_mark'] == "d"])
    if zs_d > zs_g or uz >= 4:
        return False, None

    b = False
    detail = {
        "标的代码": ka.symbol,
        "操作提示": "三买",
        "出现时间": "",
        "基准价格": 0,
        "其他信息": "向上中枢数量为%i" % uz
    }
    last_xd = ka.xd[-1]
    base_price = last_xd['xd']
    if last_xd['xd'] > zs_g and __in_tolerance(base_price, ka.latest_price, tolerance):
        detail['出现时间'] = last_xd['dt']
        detail["基准价格"] = base_price
        b = True

    if isinstance(ka1, KlineAnalyze) and ka1.bi[-1]['fx_mark'] == 'g':
        b = False
    if isinstance(ka2, KlineAnalyze) and ka2.xd[-1]['fx_mark'] == 'g':
        b = False

    return b, detail


def is_third_sell(ka, ka1=None, ka2=None, tolerance=0.03):
    """确定某一级别三卖

    第三类卖点: 一个第三类卖点，至少需要有5段次级别的走势，前三段构成中枢，第四段离开中枢，第5段不升破中枢的低点。

    :param ka: KlineAnalyze
        本级别
    :param ka1: KlineAnalyze
        上级别，默认为 None
    :param ka2: KlineAnalyze
        下级别，默认为 None
    :param tolerance: float
        相对于基准价格的操作容差，默认为 0.03，表示在基准价格附近上下3个点的波动范围内都是允许操作的
    :return:
    """
    if not isinstance(ka, KlineAnalyze) or len(ka.xd) < 6 or ka.xd[-1]['fx_mark'] == 'd':
        return False, None

    dz = down_zs_number(ka)
    zs_g = min([x['xd'] for x in ka.xd[-6:-1] if x['fx_mark'] == "g"])
    zs_d = max([x['xd'] for x in ka.xd[-6:-1] if x['fx_mark'] == "d"])
    if zs_d > zs_g or dz >= 4:
        return False, None

    b = False
    detail = {
        "标的代码": ka.symbol,
        "操作提示": "三卖",
        "出现时间": "",
        "基准价格": 0,
        "其他信息": "向下中枢数量为%i" % dz
    }
    last_xd = ka.xd[-1]
    base_price = last_xd['xd']
    if last_xd['xd'] < zs_d and __in_tolerance(base_price, ka.latest_price, tolerance):
        detail['出现时间'] = last_xd['dt']
        detail["基准价格"] = base_price
        b = True

    if isinstance(ka1, KlineAnalyze) and ka1.bi[-1]['fx_mark'] == 'd':
        b = False
    if isinstance(ka2, KlineAnalyze) and ka2.xd[-1]['fx_mark'] == 'd':
        b = False

    return b, detail


def is_xd_buy(ka, ka1=None, ka2=None, tolerance=0.03):
    """同级别分解买点，我称之为线买，即线段买点

    :param ka: KlineAnalyze
        本级别
    :param ka1: KlineAnalyze
        上级别，默认为 None
    :param ka2: KlineAnalyze
        下级别，默认为 None
    :param tolerance: float
        相对于基准价格的操作容差，默认为 0.03，表示在基准价格附近上下3个点的波动范围内都是允许操作的
    :return:
    """
    if not isinstance(ka, KlineAnalyze) or len(ka.xd) < 4 or ka.xd[-1]['fx_mark'] == 'g':
        return False, None

    b = False
    detail = {
        "标的代码": ka.symbol,
        "操作提示": "线买",
        "出现时间": "",
        "基准价格": 0,
        "其他信息": ""
    }
    last_xd = ka.xd[-1]
    base_price = last_xd['xd']
    zs1 = [ka.xd[-2]['dt'], ka.xd[-1]['dt']]
    zs2 = [ka.xd[-4]['dt'], ka.xd[-3]['dt']]

    # 线买的两种情况：1）向下线段不创新低；2）向下线段新低背驰
    if (last_xd['xd'] >= ka.xd[-3]['xd'] or
        (last_xd['xd'] < ka.xd[-3]['xd'] and is_bei_chi(ka, zs1, zs2, direction='down', mode='xd'))) \
            and __in_tolerance(base_price, ka.latest_price, tolerance):
        detail['出现时间'] = last_xd['dt']
        detail["基准价格"] = base_price
        b = True

    if isinstance(ka1, KlineAnalyze) and ka1.bi[-1]['fx_mark'] == 'g':
        b = False
    if isinstance(ka2, KlineAnalyze) and ka2.xd[-1]['fx_mark'] == 'g':
        b = False
    return b, detail


def is_xd_sell(ka, ka1=None, ka2=None, tolerance=0.03):
    """同级别分解卖点，我称之为线卖，即线段卖点

    :param ka: KlineAnalyze
        本级别
    :param ka1: KlineAnalyze
        上级别，默认为 None
    :param ka2: KlineAnalyze
        下级别，默认为 None
    :param tolerance: float
        相对于基准价格的操作容差，默认为 0.03，表示在基准价格附近上下3个点的波动范围内都是允许操作的
    :return:
    """
    if not isinstance(ka, KlineAnalyze) or len(ka.xd) < 4 or ka.xd[-1]['fx_mark'] == 'd':
        return False, None

    b = False
    detail = {
        "标的代码": ka.symbol,
        "操作提示": "线卖",
        "出现时间": "",
        "基准价格": 0,
        "其他信息": ""
    }
    last_xd = ka.xd[-1]
    base_price = last_xd['xd']
    zs1 = [ka.xd[-2]['dt'], ka.xd[-1]['dt']]
    zs2 = [ka.xd[-4]['dt'], ka.xd[-3]['dt']]

    # 线卖的两种情况：1）向上线段不创新高；2）向上线段新高背驰
    if (last_xd['xd'] <= ka.xd[-3]['xd']
            or (last_xd['xd'] > ka.xd[-3]['xd'] and is_bei_chi(ka, zs1, zs2, direction='up', mode='xd'))) \
            and __in_tolerance(base_price, ka.latest_price, tolerance):
        detail['出现时间'] = last_xd['dt']
        detail["基准价格"] = base_price
        b = True

    if isinstance(ka1, KlineAnalyze) and ka1.bi[-1]['fx_mark'] == 'd':
        b = False
    if isinstance(ka2, KlineAnalyze) and ka2.xd[-1]['fx_mark'] == 'd':
        b = False
    return b, detail


class SolidAnalyze(object):
    """多级别（日线、30分钟、5分钟、1分钟）K线联合分析

    这只是一个样例，展示如何结合多个K线级别进行买卖点分析。
    你可以根据自己对缠论的理解，利用 KlineAnalyze 的分析结果在多个级别之间进行联合分析，找出符合自己要求的买卖点。
    """

    def __init__(self, klines):
        """

        :param klines: dict
            key 为K线级别名称；value 为对应的K线数据，K线数据基本格式参考 KlineAnalyze
            example: {"日线": df, "30分钟": df, "5分钟": df, "1分钟": df,}
        """
        self.kas = dict()
        self.freqs = list(klines.keys())
        for freq, kline in klines.items():
            try:
                ka = KlineAnalyze(kline)
                self.kas[freq] = ka
            except:
                self.kas[freq] = None
                traceback.print_exc()
        self.symbol = self.kas['1分钟'].symbol

    def _get_ka(self, freq):
        """输入级别，返回该级别 ka，以及上一级别 ka1，下一级别 ka2"""
        assert freq in self.freqs, "‘%s’不在级别列表（%s）中" % (freq, "|".join(self.freqs))
        if freq == '日线':
            ka, ka1, ka2 = self.kas['日线'], None, self.kas['30分钟']
        elif freq == '30分钟':
            ka, ka1, ka2 = self.kas['30分钟'], self.kas['日线'], self.kas['5分钟']
        elif freq == '5分钟':
            ka, ka1, ka2 = self.kas['5分钟'], self.kas['30分钟'], self.kas['1分钟']
        elif freq == '1分钟':
            ka, ka1, ka2 = self.kas['1分钟'], self.kas['5分钟'], None
        else:
            raise ValueError
        return ka, ka1, ka2

    def is_first_buy(self, freq, tolerance=0.03):
        """确定某一级别一买，包括由盘整背驰引发的类一买

        注意：如果本级别上一级别的 ka 不存在，默认返回 False !!!

        :param freq: str
            K线级别，如 1分钟；这个级别可以是你定义的任何名称
        :param tolerance: float
            相对于基准价格的操作容差，默认为 0.03，表示在基准价格附近上下3个点的波动范围内都是允许操作的
        :return:
        """
        ka, ka1, ka2 = self._get_ka(freq)
        assert freq != "日线", "日线级别不能识别一买"
        return is_first_buy(ka, ka1, ka2, tolerance)

    def is_first_sell(self, freq, tolerance=0.03):
        """确定某一级别一卖，包括由盘整背驰引发的类一卖

        注意：如果本级别上一级别的 ka 不存在，默认返回 False !!!

        :param freq: str
            K线级别，如 1分钟；这个级别可以是你定义的任何名称
        :param tolerance: float
            相对于基准价格的操作容差，默认为 0.03，表示在基准价格附近上下3个点的波动范围内都是允许操作的
        :return:
        """
        ka, ka1, ka2 = self._get_ka(freq)
        assert freq != "日线", "日线级别不能识别一卖"
        return is_first_sell(ka, ka1, ka2, tolerance)

    def is_second_buy(self, freq, tolerance=0.03):
        """确定某一级别二买，包括类二买

        注意：如果本级别上一级别的 ka 不存在，默认返回 False !!!

        :param freq: str
            K线级别，如 1分钟；这个级别可以是你定义的任何名称
        :param tolerance: float
            相对于基准价格的操作容差，默认为 0.03，表示在基准价格附近上下3个点的波动范围内都是允许操作的
        :return:
        """
        ka, ka1, ka2 = self._get_ka(freq)
        assert freq != "日线", "日线级别不能识别二买"
        return is_second_buy(ka, ka1, ka2, tolerance)

    def is_second_sell(self, freq, tolerance=0.03):
        """确定某一级别二卖，包括类二卖

        :param freq: str
            K线级别，如 1分钟；这个级别可以是你定义的任何名称
        :param tolerance: float
            相对于基准价格的操作容差，默认为 0.03，表示在基准价格附近上下3个点的波动范围内都是允许操作的
        :return:
        """
        ka, ka1, ka2 = self._get_ka(freq)
        assert freq != "日线", "日线级别不能识别二卖"
        return is_second_sell(ka, ka1, ka2, tolerance)

    def is_third_buy(self, freq, tolerance=0.03):
        """确定某一级别三买

        :param freq: str
            K线级别，如 1分钟；这个级别可以是你定义的任何名称
        :param tolerance: float
            相对于基准价格的操作容差，默认为 0.03，表示在基准价格附近上下3个点的波动范围内都是允许操作的
        :return:
        """
        ka, ka1, ka2 = self._get_ka(freq)
        return is_third_buy(ka, ka1, ka2, tolerance)

    def is_third_sell(self, freq, tolerance=0.03):
        """确定某一级别三卖

        :param freq: str
            K线级别，如 1分钟；这个级别可以是你定义的任何名称
        :param tolerance: float
            相对于基准价格的操作容差，默认为 0.03，表示在基准价格附近上下3个点的波动范围内都是允许操作的
        :return:
        """
        ka, ka1, ka2 = self._get_ka(freq)
        return is_third_sell(ka, ka1, ka2, tolerance)

    def is_xd_buy(self, freq, tolerance=0.03):
        """同级别分解买点，我称之为线买，即线段买点

        :param freq: str
            K线级别，如 1分钟；这个级别可以是你定义的任何名称
        :param tolerance: float
            相对于基准价格的操作容差，默认为 0.03，表示在基准价格附近上下3个点的波动范围内都是允许操作的
        :return:
        """
        ka, ka1, ka2 = self._get_ka(freq)
        return is_xd_buy(ka, ka1, ka2, tolerance)

    def is_xd_sell(self, freq, tolerance=0.03):
        """同级别分解卖点，我称之为线卖，即线段卖点

        :param freq: str
            K线级别，如 1分钟；这个级别可以是你定义的任何名称
        :param tolerance: float
            相对于基准价格的操作容差，默认为 0.03，表示在基准价格附近上下3个点的波动范围内都是允许操作的
        :return:
        """
        ka, ka1, ka2 = self._get_ka(freq)
        return is_xd_sell(ka, ka1, ka2, tolerance)

