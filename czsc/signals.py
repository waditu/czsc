# coding: utf-8
from .analyze import KlineAnalyze


def check_jing(fd1, fd2, fd3, fd4, fd5) -> str:
    """检查最近5个分段走势是否构成井

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
                jing = "向上小井"

            # 第二种小井: 12345向上，5最高3次之1最低，力度上1大于5，5大于3
            if fd5["high"] > fd3['high'] > fd1['high'] \
                    and fd1['price_power'] > fd5['price_power'] > fd3['price_power'] \
                    and fd1['vol_power'] > fd5['vol_power'] > fd3['vol_power']:
                jing = "向上小井"

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
                jing = "向下小井"

            # 第二种小井: 12345向下，5最低3次之1最高，力度上1大于5，5大于3
            if fd5['low'] < fd3['low'] < fd1['low'] \
                    and fd1['price_power'] > fd5['price_power'] > fd3['price_power'] \
                    and fd1['vol_power'] > fd5['vol_power'] > fd3['vol_power']:
                jing = "向下小井"
    else:
        # 第三种小井
        if fd1['price_power'] > fd3['price_power'] > fd5['price_power'] \
                and fd1['vol_power'] > fd3['vol_power'] > fd5['vol_power']:
            if direction == 'up' and fd5["high"] > fd3['high'] > fd1['high']:
                # 12345类上涨趋势，力度依次降低
                jing = "向上小井"

            if direction == 'down' and fd5["low"] < fd3['low'] < fd1['low']:
                # 12345类下跌趋势，力度依次降低
                jing = "向下小井"

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
    """适用于纯缠论逻辑推理的单级别信号计算"""

    def __init__(self, kline, name="本级别", bi_mode="new", max_count=300, use_xd=False, use_ta=False):
        super().__init__(kline, name, bi_mode, max_count, use_xd, use_ta,
                         ma_params=(5, 13, 21, 34, 55, 89, 144, 233), verbose=False)

    def get_signals(self):
        """获取单级别信号"""
        methods = [self.fx_signals, self.bi_signals, self.bd_signals]
        signals = dict()
        for method in methods:
            signals.update(method())
        return signals

    def fx_signals(self):
        """辅助判断的信号"""
        s = {
            "最近一个分型类型": "other",
            "最近三根无包含K线形态": "other",
            "最近一个底分型上边沿": 0,
            "最近一个顶分型下边沿": 0,
        }

        if len(self.fx_list) > 2:
            s['最近一个分型类型'] = self.fx_list[-1]['fx_mark']
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

        return {"{}_{}".format(self.name, k): v for k, v in s.items()}

    def bi_signals(self):
        """笔相关信号"""
        s = {
            "五笔趋势类背驰": "other",  # other 表示默认值， up 表示向上五笔类趋势背驰， down 表示向下

            "第N笔涨跌力度": "other",  # other 表示默认值
            "第N笔向下新低": False,
            "第N笔向上新高": False,
            "第N笔结束标记的上边沿": 0,
            "第N笔结束标记的下边沿": 0,

            "第N-1笔涨跌力度": "other",
            "第N-2笔涨跌力度": "other",

            "第N笔第三买卖": "other",  # other 表示默认值
            "第N-2笔第三买卖": "other",

            "最近一个笔中枢ZD": 0,
            "最近一个笔中枢ZG": 0,

            "第N笔出井": "other",
            "第N-1笔出井": "other",
            "第N-2笔出井": "other",
        }

        if len(self.bi_list) > 12:
            bis = self.get_bi_fd(n=10)
            s['第N笔结束标记的上边沿'] = bis[-1]['end_mark']['fx_high']
            s['第N笔结束标记的下边沿'] = bis[-1]['end_mark']['fx_low']

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
                s['第N笔向下新低'] = True

            if bis[-1]['direction'] == 'up' and last_k['high'] > bis[-1]['high']:
                s['第N笔向上新高'] = True

            s['第N笔涨跌力度'] = check_dynamic(bis[-5], bis[-3], bis[-1])
            s['第N-1笔涨跌力度'] = check_dynamic(bis[-6], bis[-4], bis[-2])
            s['第N-2笔涨跌力度'] = check_dynamic(bis[-7], bis[-5], bis[-3])

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
        return {"{}_{}".format(self.name, k): v for k, v in s.items()}

    def bd_signals(self):
        """由笔进行同级别分解的信号"""
        s = {
            "三笔回调构成第三买卖点": "other",
        }
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


class MachineKlineSignals(KlineAnalyze):
    """适用于训练机器学习（多因子）模型的单级别信号计算"""

    def __init__(self, kline, name="本级别", bi_mode="new", max_count=300, use_xd=False, use_ta=False):
        super().__init__(kline, name, bi_mode, max_count, use_xd, use_ta,
                         ma_params=(5, 13, 21, 34, 55, 89, 144, 233), verbose=False)

    def get_signals(self):
        """获取单级别信号"""
        methods = [self.fx_signals, self.bi_signals, self.bd_signals]
        signals = dict()
        for method in methods:
            signals.update(method())
        return signals

    def fx_signals(self):
        """分型相关信号"""
        s = {
            "最近一个分型类型": "other",
            "最近三根无包含K线形态": "other",
        }
        if len(self.fx_list) > 2:
            s['最近一个分型类型'] = self.fx_list[-1]['fx_mark']

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

        return {"{}_{}".format(self.name, k): v for k, v in s.items()}

    def bi_signals(self):
        """笔相关信号"""
        s = {
            "当下笔方向": "other",  # other 表示默认值
            "五笔趋势类背驰": "other",  # other 表示默认值， up 表示向上五笔类趋势背驰， down 表示向下

            "第N笔涨跌力度": "other",  # other 表示默认值
            "第N笔第三买卖": "other",  # other 表示默认值

            "第N-1笔涨跌力度": "other",
            "第N-1笔第三买卖": "other",

            "第N-2笔涨跌力度": "other",
            "第N-2笔第三买卖": "other",

            "第N-3笔涨跌力度": "other",
            "第N-3笔第三买卖": "other",

            "最近一个笔中枢ZD": 0,
            "最近一个笔中枢ZG": 0,

            "第N-1笔创近6笔新高": False,
            "第N-1笔创近6笔新低": False,

            # 止损信号
            "当下笔向下新低": -1,  # -1 表示默认值， 0 表示 False， 1 表示 True
            "当下笔向上新高": -1,  # -1 表示默认值， 0 表示 False， 1 表示 True
        }

        if len(self.bi_list) > 12:
            bis = self.get_bi_fd(n=10)
            s['当下笔方向'] = bis[-1]['direction']
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

            if bis[-1]['direction'] == 'down':
                s['当下笔向下新低'] = 1 if last_k['low'] < bis[-1]['low'] else 0

            if bis[-1]['direction'] == 'up':
                s['当下笔向上新高'] = 1 if last_k['high'] > bis[-1]['high'] else 0

            s['第N-1笔创近6笔新高'] = max([x['high'] for x in bis[-7:-1]]) == bis[-2]['high'] and bis[-2]['direction'] == 'up'
            s['第N-1笔创近6笔新低'] = min([x['low'] for x in bis[-7:-1]]) == bis[-2]['low'] and bis[-2]['direction'] == 'down'

            s['第N笔涨跌力度'] = check_dynamic(bis[-5], bis[-3], bis[-1])
            s['第N-1笔涨跌力度'] = check_dynamic(bis[-6], bis[-4], bis[-2])
            s['第N-2笔涨跌力度'] = check_dynamic(bis[-7], bis[-5], bis[-3])
            s['第N-3笔涨跌力度'] = check_dynamic(bis[-8], bis[-6], bis[-4])

            s['第N笔第三买卖'] = check_third_bs(bis[-5], bis[-4], bis[-3], bis[-2], bis[-1])
            s['第N-1笔第三买卖'] = check_third_bs(bis[-6], bis[-5], bis[-4], bis[-3], bis[-2])
            s['第N-2笔第三买卖'] = check_third_bs(bis[-7], bis[-6], bis[-5], bis[-4], bis[-3])
            s['第N-3笔第三买卖'] = check_third_bs(bis[-8], bis[-7], bis[-6], bis[-5], bis[-4])

            zd = max(bis[-5]['low'], bis[-4]['low'], bis[-3]['low'])
            zg = min(bis[-5]['high'], bis[-4]['high'], bis[-3]['high'])
            if zg < zd:
                zd = max(bis[-4]['low'], bis[-3]['low'], bis[-2]['low'])
                zg = min(bis[-4]['high'], bis[-3]['high'], bis[-2]['high'])

            s['最近一个笔中枢ZD'] = zd
            s['最近一个笔中枢ZG'] = zg
        return {"{}_{}".format(self.name, k): v for k, v in s.items()}

    def bd_signals(self):
        """由笔进行同级别分解的信号"""
        s = {
            "三笔回调构成第三买卖点": "other",
        }
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
