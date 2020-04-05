# coding: utf-8

import pandas as pd
import traceback
from copy import deepcopy
from .ta import macd, ma
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


def is_macd_cross(ka, direction="up"):
    """判断macd的向上金叉、向下死叉"""
    df = pd.DataFrame(ka.kline)
    df = macd(df)
    if (direction == "up" and df.iloc[-1]['diff'] > df.iloc[-1]['dea']) \
            or (direction == "down" and df.iloc[-1]['diff'] < df.iloc[-1]['dea']):
        return True
    return False


def is_first_buy(ka, ka1, ka2=None, tolerance=0.03):
    """确定某一级别一买
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
    """确定某一级别一卖

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
    if len(ka.xd) < 6 or not ka1.xd or ka1.xd[-1]['fx_mark'] == 'g':
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
    if len(ka.xd) < 6 or not ka1.xd or ka1.xd[-1]['fx_mark'] == 'd':
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


def is_third_buy(ka, ka1=None, ka2=None, tolerance=0.03, max_num=4):
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
    :param max_num: int
        前面的最大中枢数量
    :return:
    """
    if len(ka.xd) < 6 or ka.xd[-1]['fx_mark'] == 'g':
        return False, None

    uz = up_zs_number(ka)
    zs_g = min([x['xd'] for x in ka.xd[-6:-1] if x['fx_mark'] == "g"])
    zs_d = max([x['xd'] for x in ka.xd[-6:-1] if x['fx_mark'] == "d"])
    if zs_d > zs_g or uz >= max_num:
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


def is_third_sell(ka, ka1=None, ka2=None, tolerance=0.03, max_num=4):
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
    :param max_num: int
        前面的最大中枢数量
    :return:
    """
    if not isinstance(ka, KlineAnalyze) or len(ka.xd) < 6 or ka.xd[-1]['fx_mark'] == 'd':
        return False, None

    dz = down_zs_number(ka)
    zs_g = min([x['xd'] for x in ka.xd[-6:-1] if x['fx_mark'] == "g"])
    zs_d = max([x['xd'] for x in ka.xd[-6:-1] if x['fx_mark'] == "d"])
    if zs_d > zs_g or dz >= max_num:
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

    def _m_detail(self, detail, freq):
        detail['交易级别'] = freq
        ka = self.kas['1分钟']
        detail['最新时间'] = ka.end_dt
        detail['最新价格'] = ka.latest_price
        return detail

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
        b, detail = is_first_buy(ka, ka1, ka2, tolerance)
        if b:
            detail = self._m_detail(detail, freq)
        return b, detail

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
        b, detail = is_first_sell(ka, ka1, ka2, tolerance)
        if b:
            detail = self._m_detail(detail, freq)
        return b, detail

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
        b, detail = is_second_buy(ka, ka1, ka2, tolerance)
        if b:
            detail = self._m_detail(detail, freq)
        return b, detail

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
        b, detail = is_second_sell(ka, ka1, ka2, tolerance)
        if b:
            detail = self._m_detail(detail, freq)
        return b, detail

    def is_third_buy(self, freq, tolerance=0.03):
        """确定某一级别三买

        :param freq: str
            K线级别，如 1分钟；这个级别可以是你定义的任何名称
        :param tolerance: float
            相对于基准价格的操作容差，默认为 0.03，表示在基准价格附近上下3个点的波动范围内都是允许操作的
        :return:
        """
        ka, ka1, ka2 = self._get_ka(freq)
        b, detail = is_third_buy(ka, ka1, ka2, tolerance)
        if b:
            detail = self._m_detail(detail, freq)
        return b, detail

    def is_third_sell(self, freq, tolerance=0.03):
        """确定某一级别三卖

        :param freq: str
            K线级别，如 1分钟；这个级别可以是你定义的任何名称
        :param tolerance: float
            相对于基准价格的操作容差，默认为 0.03，表示在基准价格附近上下3个点的波动范围内都是允许操作的
        :return:
        """
        ka, ka1, ka2 = self._get_ka(freq)
        b, detail = is_third_sell(ka, ka1, ka2, tolerance)
        if b:
            detail = self._m_detail(detail, freq)
        return b, detail

    def is_xd_buy(self, freq, tolerance=0.03):
        """同级别分解买点，我称之为线买，即线段买点

        :param freq: str
            K线级别，如 1分钟；这个级别可以是你定义的任何名称
        :param tolerance: float
            相对于基准价格的操作容差，默认为 0.03，表示在基准价格附近上下3个点的波动范围内都是允许操作的
        :return:
        """
        ka, ka1, ka2 = self._get_ka(freq)
        b, detail = is_xd_buy(ka, ka1, ka2, tolerance)
        if b:
            detail = self._m_detail(detail, freq)
        return b, detail

    def is_xd_sell(self, freq, tolerance=0.03):
        """同级别分解卖点，我称之为线卖，即线段卖点

        :param freq: str
            K线级别，如 1分钟；这个级别可以是你定义的任何名称
        :param tolerance: float
            相对于基准价格的操作容差，默认为 0.03，表示在基准价格附近上下3个点的波动范围内都是允许操作的
        :return:
        """
        ka, ka1, ka2 = self._get_ka(freq)
        b, detail = is_xd_sell(ka, ka1, ka2, tolerance)
        if b:
            detail = self._m_detail(detail, freq)
        return b, detail


def is_single_ma_buy(kline, p=5, max_distant=0.1):
    """单均线买点"""
    kline = deepcopy(kline)
    kline = ma(kline, params=(p,))
    ma_col = "ma%i" % p
    kline['d'] = kline[ma_col].diff(1)

    b = False
    detail = {
        "标的代码": kline.iloc[0]['symbol'],
        "操作提示": "单均线买",
        "出现时间": kline.iloc[-1]['dt'],
        "基准价格": kline.iloc[-1]['close'],
        "其他信息": ""
    }

    distant = (kline.iloc[-1]['close'] - kline.iloc[-1][ma_col]) / kline.iloc[-1][ma_col]

    # 在均线下出现的买点
    if distant < 0:
        if kline.iloc[-1]['d'] > kline.iloc[-2]['d'] * 1.2 \
                and kline.iloc[-2]['d'] > kline.iloc[-3]['d'] * 1.2 \
                and kline.iloc[-3]['d'] > 0:
            b = True
            detail['其他信息'] = "买点一：价格跌破均线，但均线仍维持上行"
            return b, detail

        if abs(kline.iloc[-1]['d']) > abs(kline.iloc[-2]['d'] * 1.5) \
                and abs(kline.iloc[-2]['d']) > abs(kline.iloc[-3]['d'] * 1.5) \
                and abs(distant) > max_distant \
                and kline.iloc[-3]['d'] < 0:
            b = True
            detail['其他信息'] = "买点二：价格在连续的暴跌走势中远离均线"
            return b, detail

    # 在均线上出现的买点
    if distant > 0:
        if kline.iloc[-1]['d'] > kline.iloc[-2]['d'] > kline.iloc[-3]['d'] > 0 > kline.iloc[-4]['d']:
            b = True
            detail['其他信息'] = "买点三：均线从前期的下行逐渐走平，此时价格突破均线，在均线上运行"
            return b, detail

        if kline.iloc[-2]['close'] < kline.iloc[-3]['close'] < kline.iloc[-4]['close'] \
                and kline.iloc[-1]['close'] > kline.iloc[-2]['close'] \
                and abs(kline.iloc[-1]['d']) > abs(kline.iloc[-2]['d'] * 1.2) \
                and abs(kline.iloc[-2]['d']) > abs(kline.iloc[-3]['d'] * 1.2) \
                and kline.iloc[-3]['d'] > 0:
            b = True
            detail['其他信息'] = "买点四：价格上升过程中突然下跌靠近均线，在未跌破均线的时候再次上涨"
            return b, detail

    return b, detail


def is_single_ma_sell(kline, p=5, max_distant=0.1):
    """单均线卖点"""
    kline = ma(kline, params=(p,))
    ma_col = "ma%i" % p
    kline['d'] = kline[ma_col].diff(1)

    b = False
    detail = {
        "标的代码": kline.iloc[0]['symbol'],
        "操作提示": "单均线卖",
        "出现时间": kline.iloc[-1]['dt'],
        "基准价格": kline.iloc[-1]['close'],
        "其他信息": ""
    }

    distant = (kline.iloc[-1]['close'] - kline.iloc[-1][ma_col]) / kline.iloc[-1][ma_col]

    # 在均线下形成卖点
    if distant < 0:
        if abs(kline.iloc[-1]['d']) > abs(kline.iloc[-2]['d']) \
                and kline.iloc[-2]['d'] < 0 \
                and kline.iloc[-3]['d'] > 0:
            b = True
            detail['其他信息'] = "卖点一：价格跌破均线，并且均线转向下行"
            return b, detail

        if kline.iloc[-2]['close'] > kline.iloc[-3]['close'] \
                and kline.iloc[-1]['close'] < kline.iloc[-2]['close']:
            b = True
            detail['其他信息'] = "卖点二：价格在均线之下试图突破均线，但未成功，之后继续下跌"
            return b, detail

    # 在均线上形成卖点
    if distant > 0:
        if abs(distant) > max_distant \
                and abs(kline.iloc[-1]['d']) > abs(kline.iloc[-2]['d'] * 2) \
                and abs(kline.iloc[-2]['d']) > abs(kline.iloc[-3]['d'] * 2):
            b = True
            detail['其他信息'] = "卖点三：价格在不断的暴涨中逐渐远离均线"
            return b, detail

        if kline.iloc[-1]['close'] < kline.iloc[-2]['close'] < kline.iloc[-3]['close'] \
                and kline.iloc[-1]['d'] < 0:
            b = True
            detail['其他信息'] = "卖点四：价格短期突破均线，之后立即跌回"
            return b, detail

    return b, detail


def __macd_cross_bs(kline):
    kline = deepcopy(kline)
    kline = macd(kline)
    kline.loc[:, "macd_cross"] = kline.apply(lambda x: "金叉" if x['diff'] >= x['dea'] else "死叉", axis=1)

    kline['m_'] = kline['macd_cross'].shift(1)
    idx = kline[kline['m_'] != kline['macd_cross']].index.tolist()

    g_max = []  # 金叉的最大值序列
    d_min = []  # 死叉的最小值序列
    for i in range(len(idx)):
        if i == len(idx)-1:
            k = kline.iloc[idx[i]:]
        else:
            k = kline.iloc[idx[i]:idx[i+1]]

        if k.iloc[0]['macd_cross'] == '金叉':
            g_max.append(max(k.high))
        elif k.iloc[0]['macd_cross'] == '死叉':
            d_min.append(min(k.low))
        else:
            raise ValueError

    # if kline.iloc[-1]['macd_cross'] == '金叉' and d_min[-1] > d_min[-2]:
    #     return "buy"
    #
    # if kline.iloc[-1]['macd_cross'] == '死叉' and g_max[-1] < g_max[-2]:
    #     return "sell"
    #
    # return None
    m1, m2, m3 = kline['macd'][-3:]
    if kline.iloc[-1]['macd_cross'] == '死叉' and d_min[-1] > d_min[-2] and m1 > m2 < m3:
        return "buy"

    if kline.iloc[-1]['macd_cross'] == '金叉' and g_max[-1] < g_max[-2] and m1 < m2 > m3:
        return "sell"

    return None


def is_macd_buy(kline):
    """当下是金叉，前一个死叉不创新低，做多

    :param kline:
    :return:
    """
    b = False
    detail = {
        "标的代码": kline.iloc[0]['symbol'],
        "操作提示": "MACD买",
        "出现时间": kline.iloc[-1]['dt'],
        "基准价格": kline.iloc[-1]['close'],
        "其他信息": ""
    }
    bs = __macd_cross_bs(kline)
    if bs == "buy":
        b = True
        detail['其他信息'] = "MACD当下金叉，前一个死叉不创新低，做多"
    return b, detail


def is_macd_sell(kline):
    """当下是死叉，前一个金叉不创新高，做空

    :param kline:
    :return:
    """
    b = False
    detail = {
        "标的代码": kline.iloc[0]['symbol'],
        "操作提示": "MACD卖",
        "出现时间": kline.iloc[-1]['dt'],
        "基准价格": kline.iloc[-1]['close'],
        "其他信息": ""
    }
    bs = __macd_cross_bs(kline)
    if bs == "sell":
        b = True
        detail['其他信息'] = "MACD当下死叉，前一个金叉不创新高，做空"
    return b, detail
