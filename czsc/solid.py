# coding: utf-8

import traceback
from .analyze import KlineAnalyze, is_bei_chi, down_zs_number, up_zs_number, get_ka_feature


def is_in_tolerance(base_price, latest_price, tolerance):
    """判断 latest_price 是否在 base_price 的买入容差范围（上下 tolerance）"""
    if (1 - tolerance) * base_price <= latest_price <= (1 + tolerance) * base_price:
        return True
    else:
        return False


def is_first_buy(ka, ka1, ka2=None, pf=False):
    """确定某一级别一买
    注意：如果本级别上一级别的 ka 不存在，无法识别本级别一买，返回 `无操作` !!!

    一买识别逻辑：
    1）必须：上级别最后一个线段标记和最后一个笔标记重合且为底分型；
    2）必须：上级别最后一个向下线段内部笔标记数量大于等于6，且本级别最后一个线段标记为底分型；
    3）必须：本级别向下线段背驰 或 本级别向下笔背驰；

    4）辅助：下级别向下线段背驰 或 下级别向下笔背驰。

    :param ka: KlineAnalyze
        本级别
    :param ka1: KlineAnalyze
        上级别
    :param ka2: KlineAnalyze
        下级别，默认为 None
    :param pf: bool
        pf 为 precision first 的缩写， 控制是否使用 `高精度优先模式` ，默认为 False ，即 `高召回优先模式`。
        在 `高精度优先模式` 下，会充分利用辅助判断条件提高识别准确率。

    :return: dict
    """
    detail = {
        "标的代码": ka.symbol,
        "操作提示": "无操作",
        "出现时间": None,
        "基准价格": None,
        "其他信息": None
    }

    if not isinstance(ka1, KlineAnalyze):
        return detail

    # 上级别最后一个线段标记和最后一个笔标记重合且为底分型；
    if len(ka1.xd) >= 2 and ka1.xd[-1]['xd'] == ka1.bi[-1]['bi'] \
            and ka1.xd[-1]['fx_mark'] == ka1.bi[-1]['fx_mark'] == 'd':
        bi_inside = [x for x in ka1.bi if ka1.xd[-2]['dt'] <= x['dt'] <= ka1.xd[-1]['dt']]

        # 上级别最后一个向下线段内部笔标记数量大于等于6，且本级别最后一个线段标记为底分型；
        if len(bi_inside) >= 6 and ka.xd[-1]['fx_mark'] == 'd':
            # 本级别向下线段背驰 或 本级别向下笔背驰；
            if (ka.xd_bei_chi() or
                    (ka.bi[-1]['fx_mark'] == 'd' and ka.bi_bei_chi())):
                detail['操作提示'] = "一买"
                detail['出现时间'] = ka.xd[-1]['dt']
                detail['基准价格'] = ka.xd[-1]['xd']

    if pf and detail["操作提示"] == "一买" and isinstance(ka2, KlineAnalyze):
        # 下级别线段背驰 或 下级别笔背驰
        if not ((ka2.xd[-1]['fx_mark'] == 'd' and ka2.xd_bei_chi()) or
                (ka2.bi[-1]['fx_mark'] == 'd' and ka2.bi_bei_chi())):
            detail['操作提示'] = "无操作"
    return detail


def is_first_sell(ka, ka1, ka2=None, pf=False):
    """确定某一级别一卖

    注意：如果本级别上一级别的 ka 不存在，无法识别本级别一卖，返回 `无操作` !!!

    一卖识别逻辑：
    1）必须：上级别最后一个线段标记和最后一个笔标记重合且为顶分型；
    2）必须：上级别最后一个向上线段内部笔标记数量大于等于6，且本级别最后一个线段标记为顶分型；
    3）必须：本级别向上线段背驰 或 本级别向上笔背驰；

    4）辅助：下级别向上线段背驰 或 下级别向上笔背驰。

    :param ka: KlineAnalyze
        本级别
    :param ka1: KlineAnalyze
        上级别
    :param ka2: KlineAnalyze
        下级别，默认为 None
    :param pf: bool
        pf 为 precision first 的缩写， 控制是否使用 `高精度优先模式` ，默认为 False ，即 `高召回优先模式`。
        在 `高精度优先模式` 下，会充分利用辅助判断条件提高识别准确率。

    :return: dict
    """
    detail = {
        "标的代码": ka.symbol,
        "操作提示": "无操作",
        "出现时间": None,
        "基准价格": None,
        "其他信息": None
    }

    if not isinstance(ka1, KlineAnalyze):
        return detail

    # 上级别最后一个线段标记和最后一个笔标记重合且为顶分型；
    if len(ka1.xd) >= 2 and ka1.xd[-1]['xd'] == ka1.bi[-1]['bi'] \
            and ka1.xd[-1]['fx_mark'] == ka1.bi[-1]['fx_mark'] == 'g':
        bi_inside = [x for x in ka1.bi if ka1.xd[-2]['dt'] <= x['dt'] <= ka1.xd[-1]['dt']]

        # 上级别最后一个向上线段内部笔标记数量大于等于6，且本级别最后一个线段标记为顶分型；
        if len(bi_inside) >= 6 and ka.xd[-1]['fx_mark'] == 'g':

            # 本级别向上线段背驰 或 本级别向上笔背驰
            if (ka.xd_bei_chi() or
                    (ka.bi[-1]['fx_mark'] == 'g' and ka.bi_bei_chi())):
                detail['操作提示'] = "一卖"
                detail['出现时间'] = ka.xd[-1]['dt']
                detail['基准价格'] = ka.xd[-1]['xd']

    if pf and detail["操作提示"] == "一卖" and isinstance(ka2, KlineAnalyze):
        # 下级别线段背驰 或 下级别笔背驰
        if not ((ka2.xd[-1]['fx_mark'] == 'g' and ka2.xd_bei_chi()) or
                (ka2.bi[-1]['fx_mark'] == 'g' and ka2.bi_bei_chi())):
            detail['操作提示'] = "无操作"
    return detail


def is_second_buy(ka, ka1, ka2=None, pf=False):
    """确定某一级别二买

    注意：如果本级别上一级别的 ka 不存在，无法识别本级别二买，返回 `无操作` !!!

    二买识别逻辑：
    1）必须：上级别最后一个线段标记和最后一个笔标记都是底分型；
    2）必须：上级别最后一个向下线段内部笔标记数量大于等于6，且本级别最后一个线段标记为底分型，不创新低；
    3）必须：上级别最后一个线段标记后有且只有三个笔标记，且上级别向下笔不创新低；

    4）辅助：下级别向下线段背驰 或 下级别向下笔背驰

    :param ka: KlineAnalyze
        本级别
    :param ka1: KlineAnalyze
        上级别
    :param ka2: KlineAnalyze
        下级别，默认为 None
    :param pf: bool
        pf 为 precision first 的缩写， 控制是否使用 `高精度优先模式` ，默认为 False ，即 `高召回优先模式`。
        在 `高精度优先模式` 下，会充分利用辅助判断条件提高识别准确率。

    :return: dict
    """
    detail = {
        "标的代码": ka.symbol,
        "操作提示": "无操作",
        "出现时间": None,
        "基准价格": None,
        "其他信息": None
    }

    if not isinstance(ka1, KlineAnalyze):
        return detail

    # 上级别最后一个线段标记和最后一个笔标记都是底分型；
    if len(ka1.xd) >= 2 and ka1.xd[-1]['fx_mark'] == ka1.bi[-1]['fx_mark'] == 'd':
        bi_inside = [x for x in ka1.bi if ka1.xd[-2]['dt'] <= x['dt'] <= ka1.xd[-1]['dt']]

        # 上级别最后一个向上线段内部笔标记数量大于等于6，且本级别最后一个线段标记为底分型，不创新低；
        if len(bi_inside) >= 6 and ka.xd[-1]['fx_mark'] == 'd' \
                and ka.xd[-1]["xd"] > ka.xd[-3]['xd']:

            # 上级别最后一个线段标记后有且只有三个笔标记，且上级别向下笔不创新低；
            bi_next = [x for x in ka1.bi if x['dt'] >= ka1.xd[-1]['dt']]
            if len(bi_next) == 3 and bi_next[-1]['fx_mark'] == 'd' \
                    and bi_next[-1]['bi'] > bi_next[-3]['bi']:
                detail['操作提示'] = "二买"
                detail['出现时间'] = ka.xd[-1]['dt']
                detail['基准价格'] = ka.xd[-1]['xd']

    if pf and detail["操作提示"] == "二买" and isinstance(ka2, KlineAnalyze):
        # 下级别向下线段背驰 或 下级别向下笔背驰
        if not ((ka2.xd[-1]['fx_mark'] == 'd' and ka2.xd_bei_chi()) or
                (ka2.bi[-1]['fx_mark'] == 'd' and ka2.bi_bei_chi())):
            detail['操作提示'] = "无操作"
    return detail


def is_second_sell(ka, ka1, ka2=None, pf=False):
    """确定某一级别二卖，包括类二卖

    注意：如果本级别上一级别的 ka 不存在，无法识别本级别一买，返回 `无操作` !!!

    二卖识别逻辑：
    1）必须：上级别最后一个线段标记和最后一个笔标记都是顶分型；
    2）必须：上级别最后一个向上线段内部笔标记数量大于等于6，且本级别最后一个线段标记为顶分型，不创新高；
    3）必须：上级别最后一个线段标记后有且只有三个笔标记，且上级别向上笔不创新低；

    4）辅助：下级别向上线段背驰 或 下级别向上笔背驰

    :param ka: KlineAnalyze
        本级别
    :param ka1: KlineAnalyze
        上级别
    :param ka2: KlineAnalyze
        下级别，默认为 None
    :param pf: bool
        pf 为 precision first 的缩写， 控制是否使用 `高精度优先模式` ，默认为 False ，即 `高召回优先模式`。
        在 `高精度优先模式` 下，会充分利用辅助判断条件提高识别准确率。

    :return: dict
    """
    detail = {
        "标的代码": ka.symbol,
        "操作提示": "无操作",
        "出现时间": None,
        "基准价格": None,
        "其他信息": None
    }

    if not isinstance(ka1, KlineAnalyze):
        return detail

    # 上级别最后一个线段标记和最后一个笔标记都是顶分型
    if len(ka1.xd) >= 2 and ka1.xd[-1]['fx_mark'] == ka1.bi[-1]['fx_mark'] == 'g':
        bi_inside = [x for x in ka1.bi if ka1.xd[-2]['dt'] <= x['dt'] <= ka1.xd[-1]['dt']]

        # 上级别最后一个向上线段内部笔标记数量大于等于6，且本级别最后一个线段标记为顶分型，不创新高
        if len(bi_inside) >= 6 and ka.xd[-1]['fx_mark'] == 'g' \
                and ka.xd[-1]["xd"] < ka.xd[-3]['xd']:

            # 上级别最后一个线段标记后有且只有三个笔标记，且上级别向上笔不创新低
            bi_next = [x for x in ka1.bi if x['dt'] >= ka1.xd[-1]['dt']]
            if len(bi_next) == 3 and bi_next[-1]['fx_mark'] == 'g' \
                    and bi_next[-1]['bi'] < bi_next[-3]['bi']:
                detail['操作提示'] = "二卖"
                detail['出现时间'] = ka.xd[-1]['dt']
                detail['基准价格'] = ka.xd[-1]['xd']

    if pf and detail["操作提示"] == "二卖" and isinstance(ka2, KlineAnalyze):
        # 下级别向上线段背驰 或 下级别向上笔背驰
        if not ((ka2.xd[-1]['fx_mark'] == 'g' and ka2.xd_bei_chi()) or
                (ka2.bi[-1]['fx_mark'] == 'g' and ka2.bi_bei_chi())):
            detail['操作提示'] = "无操作"
    return detail


def is_third_buy(ka, ka1=None, ka2=None, pf=False):
    """确定某一级别三买

    第三类买点: 一个第三类买点，至少需要有5段次级别的走势，前三段构成中枢，第四段离开中枢，第5段不跌回中枢。

    三买识别逻辑：
    1）必须：本级别有6个以上线段标记，且最后一个线段标记为底分型；
    2）必须：前三段有价格重叠部分，构成中枢；
    2）必须：第4段比第2段新高无背驰，第5段不跌回中枢；

    4）辅助：向上中枢数量小于等于3

    :param ka: KlineAnalyze
        本级别
    :param ka1: KlineAnalyze
        上级别
    :param ka2: KlineAnalyze
        下级别，默认为 None
    :param pf: bool
        pf 为 precision first 的缩写， 控制是否使用 `高精度优先模式` ，默认为 False ，即 `高召回优先模式`。
        在 `高精度优先模式` 下，会充分利用辅助判断条件提高识别准确率。

    :return: dict
    """
    detail = {
        "标的代码": ka.symbol,
        "操作提示": "无操作",
        "出现时间": None,
        "基准价格": None,
        "其他信息": None
    }

    # 本级别有6个以上线段标记，且最后一个线段标记为底分型；
    if len(ka.xd) >= 6 and ka.xd[-1]['fx_mark'] == 'd':

        # 前三段有价格重叠部分，构成中枢；
        zs_g = min([x['xd'] for x in ka.xd[-6:-2] if x['fx_mark'] == "g"])
        zs_d = max([x['xd'] for x in ka.xd[-6:-2] if x['fx_mark'] == "d"])
        if zs_g > zs_d:

            # 第4段比第2段有新高或新低，且无背驰，第5段不跌回中枢；
            zs1 = [ka.xd[-3]['dt'], ka.xd[-2]['dt']]
            zs2 = [ka.xd[-5]['dt'], ka.xd[-4]['dt']]
            if ka.xd[-2]['xd'] > ka.xd[-4]['xd'] \
                    and not is_bei_chi(ka, zs1, zs2, direction='up', mode='xd') \
                    and ka.xd[-1]['xd'] > zs_g:
                detail['操作提示'] = '三买'
                detail['出现时间'] = ka.xd[-1]['dt']
                detail['基准价格'] = ka.xd[-1]['xd']

    if pf and detail['操作提示'] == '三买':
        # 向上中枢数量小于等于3
        un = up_zs_number(ka)
        if un > 3:
            detail['操作提示'] = '无操作'

        if isinstance(ka1, KlineAnalyze):
            pass

        if isinstance(ka2, KlineAnalyze):
            pass
    return detail


def is_third_sell(ka, ka1=None, ka2=None, pf=False):
    """确定某一级别三卖

    第三类卖点: 一个第三类卖点，至少需要有5段次级别的走势，前三段构成中枢，第四段离开中枢，第5段不升破中枢的低点。

    三卖识别逻辑：
    1）必须：本级别有6个以上线段标记，且最后一个线段标记为顶分型；
    2）必须：前三段有价格重叠部分，构成中枢；
    2）必须：第4段比第2段新低无背驰，第5段不升回中枢；

    4）辅助：向下中枢数量小于等于3

    :param ka: KlineAnalyze
        本级别
    :param ka1: KlineAnalyze
        上级别
    :param ka2: KlineAnalyze
        下级别，默认为 None
    :param pf: bool
        pf 为 precision first 的缩写， 控制是否使用 `高精度优先模式` ，默认为 False ，即 `高召回优先模式`。
        在 `高精度优先模式` 下，会充分利用辅助判断条件提高识别准确率。

    :return: dict
    """
    detail = {
        "标的代码": ka.symbol,
        "操作提示": "无操作",
        "出现时间": None,
        "基准价格": None,
        "其他信息": None
    }

    # 本级别有6个以上线段标记，且最后一个线段标记为顶分型；
    if len(ka.xd) >= 6 and ka.xd[-1]['fx_mark'] == 'g':

        # 前三段有价格重叠部分，构成中枢；
        zs_g = min([x['xd'] for x in ka.xd[-6:-2] if x['fx_mark'] == "g"])
        zs_d = max([x['xd'] for x in ka.xd[-6:-2] if x['fx_mark'] == "d"])
        if zs_g > zs_d:

            # 第4段比第2段新低无背驰，第5段不升回中枢；
            zs1 = [ka.xd[-3]['dt'], ka.xd[-2]['dt']]
            zs2 = [ka.xd[-5]['dt'], ka.xd[-4]['dt']]
            if ka.xd[-2]['xd'] < ka.xd[-4]['xd'] \
                    and not is_bei_chi(ka, zs1, zs2, direction='down', mode='xd') \
                    and ka.xd[-1]['xd'] > zs_g:
                detail['操作提示'] = '三卖'
                detail['出现时间'] = ka.xd[-1]['dt']
                detail['基准价格'] = ka.xd[-1]['xd']

    if pf and detail['操作提示'] == '三卖':
        # 向下中枢数量小于等于3
        dn = down_zs_number(ka)
        if dn > 3:
            detail['操作提示'] = '无操作'

        if isinstance(ka1, KlineAnalyze):
            pass

        if isinstance(ka2, KlineAnalyze):
            pass
    return detail


def is_xd_buy(ka, ka1=None, ka2=None, pf=False):
    """同级别分解买点，我称之为线买，即线段买点

    线买识别逻辑：
    1） 必须：本级别至少有 3 个线段标记且最后一个线段标记为底分型；
    2） 必须：本级别向下线段背驰 或 本级别向下线段不创新低；

    3） 辅助：上级别向下笔背驰 或 上级别向下笔不创新低
    4） 辅助：下级别向下笔背驰

    :param ka: KlineAnalyze
        本级别
    :param ka1: KlineAnalyze
        上级别
    :param ka2: KlineAnalyze
        下级别，默认为 None
    :param pf: bool
        pf 为 precision first 的缩写， 控制是否使用 `高精度优先模式` ，默认为 False ，即 `高召回优先模式`。
        在 `高精度优先模式` 下，会充分利用辅助判断条件提高识别准确率。

    :return: dict
    """
    detail = {
        "标的代码": ka.symbol,
        "操作提示": "无操作",
        "出现时间": None,
        "基准价格": None,
        "其他信息": None
    }

    # 本级别至少有 3 个线段标记且最后一个线段标记为底分型；
    if len(ka.xd) > 3 and ka.xd[-1]['fx_mark'] == 'd':

        # 本级别向下线段背驰 或 本级别向下线段不创新低；
        if ka.xd_bei_chi() or ka.xd[-1]['xd'] > ka.xd[-3]['xd']:
            detail['操作提示'] = "线买"
            detail['出现时间'] = ka.xd[-1]['dt']
            detail['基准价格'] = ka.xd[-1]['xd']

    if pf and detail['操作提示'] == "线买":
        if isinstance(ka1, KlineAnalyze):
            # 上级别向下笔背驰 或 上级别向下笔不创新低
            if not (ka1.bi[-1]['fx_mark'] == 'd' and
                    (ka1.bi[-1]['bi'] > ka1.bi[-3]['bi'] or ka1.bi_bei_chi())):
                detail['操作提示'] = "无操作"

        if isinstance(ka2, KlineAnalyze):
            # 下级别向下笔背驰
            if not (ka2.bi[-1]['fx_mark'] == 'd' and ka2.bi_bei_chi()):
                detail['操作提示'] = "无操作"
    return detail


def is_xd_sell(ka, ka1=None, ka2=None, pf=False):
    """同级别分解卖点，我称之为线卖，即线段卖点

    线卖识别逻辑：
    1） 必须：本级别至少有 3 个线段标记且最后一个线段标记为顶分型；
    2） 必须：本级别向上线段背驰 或 本级别向上线段不创新高；

    3） 辅助：上级别向上笔背驰 或 上级别向上笔不创新高
    4） 辅助：下级别向上笔背驰

    :param ka: KlineAnalyze
        本级别
    :param ka1: KlineAnalyze
        上级别
    :param ka2: KlineAnalyze
        下级别，默认为 None
    :param pf: bool
        pf 为 precision first 的缩写， 控制是否使用 `高精度优先模式` ，默认为 False ，即 `高召回优先模式`。
        在 `高精度优先模式` 下，会充分利用辅助判断条件提高识别准确率。

    :return: dict
    """
    detail = {
        "标的代码": ka.symbol,
        "操作提示": "无操作",
        "出现时间": None,
        "基准价格": None,
        "其他信息": None
    }

    # 本级别至少有 3 个线段标记且最后一个线段标记为顶分型；
    if len(ka.xd) > 3 and ka.xd[-1]['fx_mark'] == 'g':

        # 本级别向上线段背驰 或 本级别向上线段不创新高
        if ka.xd_bei_chi() or ka.xd[-1]['xd'] < ka.xd[-3]['xd']:
            detail['操作提示'] = "线卖"
            detail['出现时间'] = ka.xd[-1]['dt']
            detail['基准价格'] = ka.xd[-1]['xd']

    if pf and detail['操作提示'] == "线卖":
        if isinstance(ka1, KlineAnalyze):
            # 上级别向上笔背驰 或 上级别向上笔不创新高
            if not (ka1.bi[-1]['fx_mark'] == 'g' and
                    (ka1.bi[-1]['bi'] < ka1.bi[-3]['bi'] or ka1.bi_bei_chi())):
                detail['操作提示'] = "无操作"

        if isinstance(ka2, KlineAnalyze):
            # 下级别向上笔背驰
            if not (ka2.bi[-1]['fx_mark'] == 'g' and ka2.bi_bei_chi()):
                detail['操作提示'] = "无操作"
    return detail


bs_func = {
            "一买": is_first_buy,
            "一卖": is_first_sell,

            "二买": is_second_buy,
            "二卖": is_second_sell,

            "三买": is_third_buy,
            "三卖": is_third_sell,

            "线买": is_xd_buy,
            "线卖": is_xd_sell,
        }


def get_sa_feature(sa):
    signals = {"交易标的": sa.symbol, "交易时间": sa.kas['1分钟'].end_dt, "chan_version": 0.3}
    for freq, ka in sa.kas.items():
        feature = get_ka_feature(ka)
        for k, v in feature.items():
            signals[freq+k] = v
    # print(signals)
    return signals


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
        self.end_dt = self.kas['1分钟'].end_dt
        self.latest_price = self.kas['1分钟'].latest_price
        self.bs_func = bs_func

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

    def check_bs(self, freq, name, pf=False, tolerance=0.03):
        """

        :param freq: str
            级别，可选值 1分钟、5分钟、30分钟、日线
        :param name: str
            买卖点名称，可选值 一买、一卖、二买、二卖、三买、三卖、线买、线卖
        :param pf: bool
            是否使用 `高精度优先模式`
        :param tolerance: float
            买卖点的价格容忍区间
        :return:dict
        """
        func = self.bs_func[name]
        ka, ka1, ka2 = self._get_ka(freq)
        detail = func(ka, ka1, ka2, pf)
        if detail['操作提示'] == name:
            detail = self._m_detail(detail, freq)
            base_price = detail["基准价格"]
            latest_price = detail['最新价格']

            if not is_in_tolerance(base_price, latest_price, tolerance):
                detail['操作提示'] = "无操作"
        return detail
