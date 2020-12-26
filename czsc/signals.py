# coding: utf-8
from collections import OrderedDict
from .analyze import KlineAnalyze

def find_zs(points):
    """输入笔或线段标记点，输出中枢识别结果"""
    if len(points) < 5:
        return []

    # 当输入为笔的标记点时，新增 xd 值
    for j, x in enumerate(points):
        if x.get("bi", 0):
            points[j]['xd'] = x["bi"]

    def __get_zn(zn_points_):
        """把与中枢方向一致的次级别走势类型称为Z走势段，按中枢中的时间顺序，
        分别记为Zn等，而相应的高、低点分别记为gn、dn"""
        if len(zn_points_) % 2 != 0:
            zn_points_ = zn_points_[:-1]

        if zn_points_[0]['fx_mark'] == "d":
            z_direction = "up"
        else:
            z_direction = "down"

        zn = []
        for i in range(0, len(zn_points_), 2):
            zn_ = {
                "start_dt": zn_points_[i]['dt'],
                "end_dt": zn_points_[i + 1]['dt'],
                "high": max(zn_points_[i]['xd'], zn_points_[i + 1]['xd']),
                "low": min(zn_points_[i]['xd'], zn_points_[i + 1]['xd']),
                "direction": z_direction
            }
            zn_['mid'] = zn_['low'] + (zn_['high'] - zn_['low']) / 2
            zn.append(zn_)
        return zn

    k_xd = points
    k_zs = []
    zs_xd = []

    for i in range(len(k_xd)):
        if len(zs_xd) < 5:
            zs_xd.append(k_xd[i])
            continue
        xd_p = k_xd[i]
        zs_d = max([x['xd'] for x in zs_xd[:4] if x['fx_mark'] == 'd'])
        zs_g = min([x['xd'] for x in zs_xd[:4] if x['fx_mark'] == 'g'])
        if zs_g <= zs_d:
            zs_xd.append(k_xd[i])
            zs_xd.pop(0)
            continue

        # 定义四个指标,GG=max(gn),G=min(gn),D=max(dn),DD=min(dn)，n遍历中枢中所有Zn。
        # 定义ZG=min(g1、g2), ZD=max(d1、d2)，显然，[ZD，ZG]就是缠中说禅走势中枢的区间
        if xd_p['fx_mark'] == "d" and xd_p['xd'] > zs_g:
            zn_points = zs_xd[3:]
            # 线段在中枢上方结束，形成三买
            k_zs.append({
                'ZD': zs_d,
                "ZG": zs_g,
                'G': min([x['xd'] for x in zs_xd if x['fx_mark'] == 'g']),
                'GG': max([x['xd'] for x in zs_xd if x['fx_mark'] == 'g']),
                'D': max([x['xd'] for x in zs_xd if x['fx_mark'] == 'd']),
                'DD': min([x['xd'] for x in zs_xd if x['fx_mark'] == 'd']),
                'start_point': zs_xd[1],
                'end_point': zs_xd[-2],
                "zn": __get_zn(zn_points),
                "points": zs_xd,
                "third_buy": xd_p
            })
            zs_xd = []
        elif xd_p['fx_mark'] == "g" and xd_p['xd'] < zs_d:
            zn_points = zs_xd[3:]
            # 线段在中枢下方结束，形成三卖
            k_zs.append({
                'ZD': zs_d,
                "ZG": zs_g,
                'G': min([x['xd'] for x in zs_xd if x['fx_mark'] == 'g']),
                'GG': max([x['xd'] for x in zs_xd if x['fx_mark'] == 'g']),
                'D': max([x['xd'] for x in zs_xd if x['fx_mark'] == 'd']),
                'DD': min([x['xd'] for x in zs_xd if x['fx_mark'] == 'd']),
                'start_point': zs_xd[1],
                'end_point': zs_xd[-2],
                "points": zs_xd,
                "zn": __get_zn(zn_points),
                "third_sell": xd_p
            })
            zs_xd = []
        else:
            zs_xd.append(xd_p)

    if len(zs_xd) >= 5:
        zs_d = max([x['xd'] for x in zs_xd[:4] if x['fx_mark'] == 'd'])
        zs_g = min([x['xd'] for x in zs_xd[:4] if x['fx_mark'] == 'g'])
        if zs_g > zs_d:
            zn_points = zs_xd[3:]
            k_zs.append({
                'ZD': zs_d,
                "ZG": zs_g,
                'G': min([x['xd'] for x in zs_xd if x['fx_mark'] == 'g']),
                'GG': max([x['xd'] for x in zs_xd if x['fx_mark'] == 'g']),
                'D': max([x['xd'] for x in zs_xd if x['fx_mark'] == 'd']),
                'DD': min([x['xd'] for x in zs_xd if x['fx_mark'] == 'd']),
                'start_point': zs_xd[1],
                'end_point': None,
                "zn": __get_zn(zn_points),
                "points": zs_xd,
            })
    return k_zs

def check_jing(fd1, fd2, fd3, fd4, fd5) -> str:
    """检查最近5个分段走势是否构成井

    井的主要用途和背驰是一样的，用来判断趋势的结束。用在盘整也可以，但效果稍差点。

    井的定义：
        12345，五段，是构造井的基本形态，形成井的位置肯定是5，而5出井的
        前提条件是对于向上5至少比3和1其中之一高，向下反过来; 并且，234
        构成一个中枢。

        井只有两类，大井和小井（以向上为例）：
        大井对应的形式是：12345向上，5最高3次之1最低，力度上1大于3，3大于5；
        小井对应的形式是：
            1：12345向上，3最高5次之1最低，力度上5的力度比1小，注意这时候
               不需要再考虑5和3的关系了，因为5比3低，所以不需要考虑力度。
            2：12345向上，5最高3次之1最低，力度上1大于5，5大于3。

        小井的构造，关键是满足5一定至少大于1、3中的一个。
        注意有一种情况不归为井：就是12345向上，1的力度最小，5的力度次之，3的力度最大此类不算井，
        因为345后面必然还有走势在67的时候才能再判断，个中道理各位好好体会。


    fd 为 dict 对象，表示一段走势，可以是笔、线段。

    假定最近一段走势为第N段；则 fd1 为第N-4段走势, fd2为第N-3段走势,
    fd3为第N-2段走势, fd4为第N-1段走势, fd5为第N段走势

    :param fd1: 第N-4段
    :param fd2: 第N-3段
    :param fd3: 第N-2段
    :param fd4: 第N-1段
    :param fd5: 第N段
    :return:
    """
    assert fd1['direction'] == fd3['direction'] == fd5['direction']
    assert fd2['direction'] == fd4['direction']
    direction = fd1['direction']

    zs_g = min(fd2['high'], fd3['high'], fd4['high'])
    zs_d = max(fd2['low'], fd3['low'], fd4['low'])

    jing = "other"

    if fd1['price_power'] < fd5['price_power'] < fd3['price_power'] \
            and fd1['vol_power'] < fd5['vol_power'] < fd3['vol_power']:
        # 1的力度最小，5的力度次之，3的力度最大，此类不算井
        return jing

    if zs_d < zs_g:  # 234有中枢的情况
        if direction == 'up' and fd5["high"] > min(fd3['high'], fd1['high']):
            # 大井: 12345向上，5最高3次之1最低，力度上1大于3，3大于5
            if fd5["high"] > fd3['high'] > fd1['high'] \
                    and fd5['price_power'] < fd3['price_power'] < fd1['price_power'] \
                    and fd5['vol_power'] < fd3['vol_power'] < fd1['vol_power']:
                jing = "向上大井"

            # 第一种小井: 12345向上，3最高5次之1最低，力度上5的力度比1小
            if fd1['high'] < fd5['high'] < fd3['high'] \
                    and fd5['price_power'] < fd1['price_power'] \
                    and fd5['vol_power'] < fd1['vol_power']:
                jing = "向上小井A"

            # 第二种小井: 12345向上，5最高3次之1最低，力度上1大于5，5大于3
            if fd5["high"] > fd3['high'] > fd1['high'] \
                    and fd1['price_power'] > fd5['price_power'] > fd3['price_power'] \
                    and fd1['vol_power'] > fd5['vol_power'] > fd3['vol_power']:
                jing = "向上小井B"

        if direction == 'down' and fd5["low"] < max(fd3['low'], fd1['low']):

            # 大井: 12345向下，5最低3次之1最高，力度上1大于3，3大于5
            if fd5['low'] < fd3['low'] < fd1['low'] \
                    and fd5['price_power'] < fd3['price_power'] < fd1['price_power'] \
                    and fd5['vol_power'] < fd3['vol_power'] < fd1['vol_power']:
                jing = "向下大井"

            # 第一种小井: 12345向下，3最低5次之1最高，力度上5的力度比1小
            if fd1["low"] > fd5['low'] > fd3['low'] \
                    and fd5['price_power'] < fd1['price_power'] \
                    and fd5['vol_power'] < fd1['vol_power']:
                jing = "向下小井A"

            # 第二种小井: 12345向下，5最低3次之1最高，力度上1大于5，5大于3
            if fd5['low'] < fd3['low'] < fd1['low'] \
                    and fd1['price_power'] > fd5['price_power'] > fd3['price_power'] \
                    and fd1['vol_power'] > fd5['vol_power'] > fd3['vol_power']:
                jing = "向下小井B"
    return jing

def check_third_bs(fd1, fd2, fd3, fd4, fd5) -> str:
    """输入5段走势，判断是否存在第三类买卖点

    :param fd1: 第N-4段
    :param fd2: 第N-3段
    :param fd3: 第N-2段
    :param fd4: 第N-1段
    :param fd5: 第N段
    :return:
    """
    zs_d = max(fd1['low'], fd2['low'], fd3['low'])
    zs_g = min(fd1['high'], fd2['high'], fd3['high'])

    third_bs = "other"

    if fd5['high'] < zs_d < zs_g and fd4['low'] < min(fd1['low'], fd3['low']):
        third_bs = "三卖"

    if fd5['low'] > zs_g > zs_d and fd4['high'] > max(fd1['high'], fd3['high']):
        third_bs = "三买"

    return third_bs

def check_dynamic(fd1, fd3, fd5):
    """计算第N段走势的涨跌力度

    向上笔不创新高，向上笔新高盘背，向上笔新高无背
    向下笔不创新低，向下笔新低盘背，向下笔新低无背

    :param fd1: 第N-4段走势
    :param fd3: 第N-2段走势
    :param fd5: 第N段走势
    :return: str
    """
    if fd5['direction'] == "up":
        if fd5['high'] < fd3['high'] or fd5['high'] < fd1['high']:
            v = "向上笔不创新高"
        else:
            if fd5['price_power'] > fd3['price_power'] and fd5['price_power'] > fd1['price_power'] \
                    and fd5['vol_power'] > fd3['vol_power'] and fd5['vol_power'] > fd1['vol_power']:
                v = "向上笔新高无背"
            else:
                v = "向上笔新高盘背"
    elif fd5['direction'] == "down":
        if fd5['low'] > fd3['low'] or fd5['low'] > fd1['low']:
            v = "向下笔不创新低"
        else:
            if fd5['price_power'] > fd3['price_power'] and fd5['price_power'] > fd1['price_power'] \
                    and fd5['vol_power'] > fd3['vol_power'] and fd5['vol_power'] > fd1['vol_power']:
                v = "向下笔新低无背"
            else:
                v = "向下笔新低盘背"
    else:
        raise ValueError
    return v


class KlineSignals(KlineAnalyze):
    """缠中说禅技术分析理论之单级别信号计算"""

    def __init__(self, kline, name="本级别", bi_mode="new", max_count=500, use_xd=False, use_ta=False):
        super().__init__(kline, name, bi_mode, max_count, use_xd, use_ta,
                         ma_params=(5, 13, 21, 34, 55, 89, 144, 233), verbose=False)

    def get_signals(self):
        """获取单级别信号"""
        methods = [self.fx_signals, self.bi_signals, self.bd_signals]
        signals = OrderedDict()
        for method in methods:
            signals.update(method())
        return signals

    def fx_signals(self):
        """辅助判断的信号"""
        s = OrderedDict({
            "最近一个分型类型": "other",
            "最近一个分型强弱": "other",
            "最近三根无包含K线形态": "other",
            "最近一个底分型上边沿": 0,
            "最近一个顶分型下边沿": 0,
            "最近两个笔中枢状态": "other"    # 三种状态：1）重叠；2）向上；3）向下
        })
        # TODO: 大阳线和大阴线的一半位置，构成强支撑和强阻力
        if len(self.fx_list) > 2:
            s['最近一个分型类型'] = self.fx_list[-1]['fx_mark']
            s['最近一个分型强弱'] = self.fx_list[-1]['fx_power']
            last_d = [x for x in self.fx_list[-4:] if x['fx_mark'] == 'd'][-1]
            last_g = [x for x in self.fx_list[-4:] if x['fx_mark'] == 'g'][-1]
            s['最近一个底分型上边沿'] = last_d['fx_high']
            s['最近一个顶分型下边沿'] = last_g['fx_low']

        def __tri_mark(x1, x2, x3):
            if x1 < x2 > x3:
                v = "g"
            elif x1 > x2 < x3:
                v = "d"
            elif x1 > x2 > x3:
                v = "down"
            elif x1 < x2 < x3:
                v = "up"
            else:
                v = 'other'
            return v

        if len(self.kline_new) > 6:
            k3 = self.kline_new[-3:]
            assert len(k3) == 3
            s['最近三根无包含K线形态'] = __tri_mark(k3[-3]['high'], k3[-2]['high'], k3[-1]['high'])

        if len(self.bi_list) > 20:
            zss = find_zs(self.bi_list[-20:])
            if len(zss) >= 2:
                zs1, zs2 = zss[-2:]
                if zs2['DD'] > zs1['GG']:
                    s['最近两个笔中枢状态'] = "向上"
                elif zs2['GG'] < zs1['DD']:
                    s['最近两个笔中枢状态'] = "向下"
                else:
                    s['最近两个笔中枢状态'] = "重叠"

        return {"{}_{}".format(self.name, k): v for k, v in s.items()}

    def bi_signals(self):
        """笔相关信号"""
        s = OrderedDict({
            "五笔趋势类背驰": "other",  # other 表示默认值， up 表示向上五笔类趋势背驰， down 表示向下
            "第N笔向上发生破坏": False,
            "第N笔向下发生破坏": False,
            "第N笔涨跌力度": "other",  # other 表示默认值

            "第N笔结束标记的上边沿": 0,
            "第N笔结束标记的下边沿": 0,
            "第N笔结束标记的分型强弱": 0,
            "第N-1笔结束标记的上边沿": 0,
            "第N-1笔结束标记的下边沿": 0,

            "第N-1笔涨跌力度": "other",
            "第N-2笔涨跌力度": "other",
            "第N-3笔涨跌力度": "other",
            "第N-4笔涨跌力度": "other",
            "第N-5笔涨跌力度": "other",
            "第N-6笔涨跌力度": "other",

            "第N笔第三买卖": "other",  # other 表示默认值
            "第N-2笔第三买卖": "other",

            "最近一个笔中枢ZD": 0,
            "最近一个笔中枢ZG": 0,

            "第N笔出井": "other",
            "第N-1笔出井": "other",
            "第N-2笔出井": "other",

            # 过程描述
            "第N笔的力度比第N-1笔的力度": 0,
            "第N-1笔的力度比第N-2笔的力度": 0,
            "第N-2笔的力度比第N-3笔的力度": 0,

            # 单级别组合信号
            # 多头有效阻击：向下笔出现 '向下笔不创新低' / "向下笔新低盘背"，
            "当下笔多头两重有效阻击": False,
            "上一笔多头两重有效阻击": False,

            "当下笔多头三重有效阻击": False,
            "上一笔多头三重有效阻击": False,

            # 空头有效阻击：向下笔出现 '向上笔不创新高' / "向上笔新高盘背"
            "当下笔空头两重有效阻击": False,
            "上一笔空头两重有效阻击": False,

            "当下笔空头三重有效阻击": False,
            "上一笔空头三重有效阻击": False,

            # 小转大后不创新高/低
            "小转大后不创新高": False,
            "小转大后不创新低": False,
        })

        if len(self.bi_list) > 13:
            bis = self.get_bi_fd(n=12)
            s['第N笔结束标记的上边沿'] = bis[-1]['end_mark']['fx_high']
            s['第N笔结束标记的下边沿'] = bis[-1]['end_mark']['fx_low']
            s['第N笔结束标记的分型强弱'] = bis[-1]['end_mark']['fx_power']
            s['第N-1笔结束标记的上边沿'] = bis[-2]['end_mark']['fx_high']
            s['第N-1笔结束标记的下边沿'] = bis[-2]['end_mark']['fx_low']

            last_k = self.kline_new[-1]
            if bis[-1]['price_power'] < bis[-3]['price_power'] and bis[-1]['vol_power'] < bis[-3]['vol_power']:
                if bis[-5]['low'] > bis[-3]['low'] > bis[-1]['low'] \
                        and bis[-5]['high'] > bis[-3]['high'] > bis[-1]['high'] \
                        and bis[-1]['direction'] == 'down' and bis[-2]['high'] < bis[-4]['low']:
                    s['五笔趋势类背驰'] = 'down'

                if bis[-5]['low'] < bis[-3]['low'] < bis[-1]['low'] \
                        and bis[-5]['high'] < bis[-3]['high'] < bis[-1]['high'] \
                        and bis[-1]['direction'] == 'up' and bis[-2]['low'] > bis[-4]['high']:
                    s['五笔趋势类背驰'] = 'up'

            if bis[-1]['direction'] == 'down' and last_k['low'] < bis[-1]['low']:
                s['第N笔向下发生破坏'] = True

            if bis[-1]['direction'] == 'up' and last_k['high'] > bis[-1]['high']:
                s['第N笔向上发生破坏'] = True

            s['第N笔涨跌力度'] = check_dynamic(bis[-5], bis[-3], bis[-1])
            s['第N-1笔涨跌力度'] = check_dynamic(bis[-6], bis[-4], bis[-2])
            s['第N-2笔涨跌力度'] = check_dynamic(bis[-7], bis[-5], bis[-3])
            s['第N-3笔涨跌力度'] = check_dynamic(bis[-8], bis[-6], bis[-4])
            s['第N-4笔涨跌力度'] = check_dynamic(bis[-9], bis[-7], bis[-5])
            s['第N-5笔涨跌力度'] = check_dynamic(bis[-10], bis[-8], bis[-6])
            s['第N-6笔涨跌力度'] = check_dynamic(bis[-11], bis[-9], bis[-7])

            s['第N笔第三买卖'] = check_third_bs(bis[-5], bis[-4], bis[-3], bis[-2], bis[-1])
            s['第N-2笔第三买卖'] = check_third_bs(bis[-7], bis[-6], bis[-5], bis[-4], bis[-3])

            s['第N笔出井'] = check_jing(bis[-5], bis[-4], bis[-3], bis[-2], bis[-1])
            s['第N-1笔出井'] = check_jing(bis[-6], bis[-5], bis[-4], bis[-3], bis[-2])
            s['第N-2笔出井'] = check_jing(bis[-7], bis[-6], bis[-5], bis[-4], bis[-3])

            zd = max(bis[-5]['low'], bis[-4]['low'], bis[-3]['low'])
            zg = min(bis[-5]['high'], bis[-4]['high'], bis[-3]['high'])
            if zg < zd:
                zd = max(bis[-4]['low'], bis[-3]['low'], bis[-2]['low'])
                zg = min(bis[-4]['high'], bis[-3]['high'], bis[-2]['high'])

            s['最近一个笔中枢ZD'] = zd
            s['最近一个笔中枢ZG'] = zg

            s["第N笔的力度比第N-1笔的力度"] = min(
                round(bis[-1]["price_power"] / bis[-2]["price_power"], 2),
                round(bis[-1]["vol_power"] / bis[-2]["vol_power"], 2)
            )

            s["第N-1笔的力度比第N-2笔的力度"] = min(
                round(bis[-2]["price_power"] / bis[-3]["price_power"], 2),
                round(bis[-2]["vol_power"] / bis[-3]["vol_power"], 2)
            )

            s["第N-2笔的力度比第N-3笔的力度"] = min(
                round(bis[-3]["price_power"] / bis[-4]["price_power"], 2),
                round(bis[-3]["vol_power"] / bis[-4]["vol_power"], 2)
            )

            if s['第N-2笔涨跌力度'] == '向上笔新高无背' and bis[-2]['low'] < max(bis[-4]['high'], bis[-6]['high']) \
                    and s['第N笔涨跌力度'] == '向上笔不创新高':
                s['小转大后不创新高'] = True

            if s['第N-2笔涨跌力度'] == '向下笔新低无背' and bis[-2]['high'] < min(bis[-4]['low'], bis[-6]['low']) \
                    and s['第N笔涨跌力度'] == '向下笔不创新低':
                s['小转大后不创新低'] = True

        bi_down_two = ['向下笔不创新低', "向下笔新低盘背"]
        if s['第N笔涨跌力度'] in bi_down_two and s['第N-2笔涨跌力度'] in bi_down_two:
            if s['第N-4笔涨跌力度'] == "向下笔新低无背":
                s['当下笔多头两重有效阻击'] = True
            if s['第N-4笔涨跌力度'] in bi_down_two:
                s['当下笔多头三重有效阻击'] = True

        if s['第N-1笔涨跌力度'] in bi_down_two and s['第N-3笔涨跌力度'] in bi_down_two:
            if s['第N-5笔涨跌力度'] == "向下笔新低无背":
                s['上一笔多头两重有效阻击'] = True
            if s['第N-5笔涨跌力度'] in bi_down_two:
                s['上一笔多头三重有效阻击'] = True

        bi_up_two = ['向上笔不创新高', "向上笔新高盘背"]
        if s['第N笔涨跌力度'] in bi_up_two and s['第N-2笔涨跌力度'] in bi_up_two:
            if s['第N-4笔涨跌力度'] == "向上笔新高无背":
                s['当下笔空头两重有效阻击'] = True
            if s['第N-4笔涨跌力度'] in bi_up_two:
                s['当下笔空头三重有效阻击'] = True

        if s['第N-1笔涨跌力度'] in bi_up_two and s['第N-3笔涨跌力度'] in bi_up_two:
            if s['第N-5笔涨跌力度'] == "向上笔新高无背":
                s['上一笔空头两重有效阻击'] = True
            if s['第N-5笔涨跌力度'] in bi_up_two:
                s['上一笔空头三重有效阻击'] = True

        return {"{}_{}".format(self.name, k): v for k, v in s.items()}

    def bd_signals(self):
        """由笔进行同级别分解的信号"""
        s = OrderedDict({
            "三笔回调构成第三买卖点": "other",
        })
        if len(self.bi_list) > 16 and self.bi_list[-1]['fx_mark'] == 'd':
            points = self.bi_list[-16:]
            fd1_points = [x['bi'] for x in points[0: 4]]
            fd2_points = [x['bi'] for x in points[3: 7]]
            fd3_points = [x['bi'] for x in points[6: 10]]
            fd4_points = [x['bi'] for x in points[9: 13]]
            fd5_points = [x['bi'] for x in points[12: 16]]
            fd1 = {"high": max(fd1_points), "low": min(fd1_points)}
            fd2 = {"high": max(fd2_points), "low": min(fd2_points)}
            fd3 = {"high": max(fd3_points), "low": min(fd3_points)}
            fd4 = {"high": max(fd4_points), "low": min(fd4_points)}
            fd5 = {"high": max(fd5_points), "low": min(fd5_points)}

            s['三笔回调构成第三买卖点'] = check_third_bs(fd1, fd2, fd3, fd4, fd5)
        return {"{}_{}".format(self.name, k): v for k, v in s.items()}

