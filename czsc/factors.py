# coding: utf-8
from collections import OrderedDict
from pyecharts.charts import Tab
from pyecharts.components import Table
from pyecharts.options import ComponentTitleOpts
from .signals import KlineSignals
from .utils.kline_generator import KlineGeneratorBy1Min, KlineGeneratorByTick
from .utils.plot import ka_to_echarts


class KlineFactors:
    """缠中说禅技术分析理论之多级别联立因子"""
    freqs = ['1分钟', '5分钟', '30分钟', '日线']

    def __init__(self, kg: [KlineGeneratorByTick, KlineGeneratorBy1Min], bi_mode="new", max_count=1000):
        """

        :param kg: 基于tick或1分钟的K线合成器
        :param bi_mode: 使用的笔计算模式，new 表示新笔，old 表示老笔
        :param max_count: 单个级别最大K线数量
        """
        assert max_count >= 1000, "为了保证因子能够顺利计算，max_count 不允许设置小于1000"
        self.kg = kg
        klines = self.kg.get_klines({k: max_count for k in self.freqs})
        self.kas = {k: KlineSignals(klines[k], name=k, bi_mode=bi_mode,  max_count=max_count,
                                    use_xd=False, use_ta=False) for k in klines.keys()}
        self.symbol = self.kas["1分钟"].symbol
        self.end_dt = self.kas["1分钟"].end_dt
        self.latest_price = self.kas["1分钟"].latest_price
        self.s = self._calculate_factors()
        self.cache = OrderedDict()

    def take_snapshot(self, file_html=None, width="1400px", height="580px"):
        """获取快照

        :param file_html: str
            交易快照保存的 html 文件名
        :param width: str
            图表宽度
        :param height: str
            图表高度
        :return:
        """
        tab = Tab(page_title="{}@{}".format(self.symbol, self.end_dt.strftime("%Y-%m-%d %H:%M")))
        for freq in self.freqs:
            chart = ka_to_echarts(self.kas[freq], width, height)
            tab.add(chart, freq)

        t1 = Table()
        t1.add(["名称", "数据"], [[k, v] for k, v in self.s.items() if "_" in k])
        t1.set_global_opts(title_opts=ComponentTitleOpts(title="缠中说禅信号表", subtitle=""))
        tab.add(t1, "信号表")

        t2 = Table()
        t2.add(["名称", "数据"], [[k, v] for k, v in self.s.items() if "_" not in k])
        t2.set_global_opts(title_opts=ComponentTitleOpts(title="缠中说禅因子表", subtitle=""))
        tab.add(t2, "因子表")

        if file_html:
            tab.render(file_html)
        else:
            return tab

    def _calculate_signals(self):
        """计算信号"""
        s = OrderedDict(self.kas['1分钟'].kline_raw[-1])

        for freq, ks in self.kas.items():
            if freq in ["日线", '30分钟', '15分钟', '5分钟', '1分钟']:
                s.update(ks.get_signals())
        return s

    def _calculate_factors(self):
        """计算因子"""
        s = self._calculate_signals()
        if "5分钟" in self.freqs and "1分钟" in self.freqs:
            s.update({
                "1分钟最近三根K线站稳5分钟第N笔上沿": False,
                "1分钟最近三根K线跌破5分钟第N笔下沿": False,

                "5分钟笔多头右侧开仓A": False,
                "5分钟笔多头右侧开仓B": False,
                "5分钟笔多头右侧开仓C": False,
                "5分钟笔多头右侧开仓D": False,

                "5分钟笔多头左侧平仓A": False,
                "5分钟笔多头左侧平仓B": False,

                "5分钟笔多头右侧平仓A": False,
                "5分钟笔多头右侧平仓B": False,
                "5分钟笔多头右侧平仓C": False,
            })

            if sum([x['low'] > s['5分钟_第N笔结束标记的上边沿'] for x in self.kas['1分钟'].kline_raw[-3:]]) == 3:
                s['1分钟最近三根K线站稳5分钟第N笔上沿'] = True

            if sum([x['high'] < s['5分钟_第N笔结束标记的下边沿'] for x in self.kas['1分钟'].kline_raw[-3:]]) == 3:
                s['1分钟最近三根K线跌破5分钟第N笔下沿'] = True

            # 笔多头开仓 ABCD
            long_open_right_a = s['1分钟最近三根K线站稳5分钟第N笔上沿'] or s['5分钟_第N笔结束标记的分型强弱'] == 'strong'
            long_open_right_b = s['1分钟_当下笔多头两重有效阻击'] or s['1分钟_当下笔多头三重有效阻击']
            long_open_must = (not s['5分钟_第N笔向下发生破坏']) and s['dt'].minute % 1 == 0
            if long_open_must:
                if s['5分钟_当下笔多头两重有效阻击']:
                    if long_open_right_a:
                        s['5分钟笔多头右侧开仓A'] = True
                    if long_open_right_b:
                        s['5分钟笔多头右侧开仓B'] = True

                if s['5分钟_当下笔多头三重有效阻击']:
                    if long_open_right_a:
                        s['5分钟笔多头右侧开仓C'] = True
                    if long_open_right_b:
                        s['5分钟笔多头右侧开仓D'] = True

            # 笔多头平仓 ABCD
            long_close_left_a = (s['1分钟_第N笔出井'] == '向上大井' or s['1分钟_五笔趋势类背驰'] == 'up') \
                                and s['1分钟_第N笔结束标记的分型强弱'] == 'strong'
            long_close_left_b = s['1分钟_第N笔涨跌力度'] == '向上笔新高盘背' and s['1分钟_第N笔结束标记的分型强弱'] == 'strong'

            long_close_right_a = s['1分钟最近三根K线跌破5分钟第N笔下沿'] and s['5分钟_第N笔结束标记的分型强弱'] == 'strong'
            long_close_right_b = s['1分钟_第N笔结束标记的上边沿'] < s['5分钟_第N笔结束标记的下边沿'] and "向上" in s['1分钟_第N笔涨跌力度']
            long_close_right_c = s['1分钟_当下笔空头两重有效阻击'] or s['1分钟_当下笔空头三重有效阻击']

            long_close_must = (not s['5分钟_第N笔向上发生破坏']) and s['dt'].minute % 5 == 0
            if long_close_must:
                if s['5分钟_第N笔涨跌力度'] in ['向上笔不创新高', "向上笔新高盘背"]:
                    if long_close_left_a:
                        s['5分钟笔多头左侧平仓A'] = True
                    if long_close_left_b:
                        s['5分钟笔多头左侧平仓B'] = True

                    if long_close_right_a:
                        s['5分钟笔多头右侧平仓A'] = True
                    if long_close_right_b:
                        s['5分钟笔多头右侧平仓B'] = True
                    if long_close_right_c:
                        s['5分钟笔多头右侧平仓C'] = True

        if "30分钟" in self.freqs and "5分钟" in self.freqs and "1分钟" in self.freqs:
            s.update({
                "5分钟最近三根K线站稳30分钟第N笔上沿": False,
                "5分钟最近三根K线跌破30分钟第N笔下沿": False,

                "30分钟笔多头右侧开仓A": False,
                "30分钟笔多头右侧开仓B": False,
                "30分钟笔多头右侧开仓C": False,
                "30分钟笔多头右侧开仓D": False,

                "30分钟笔多头左侧平仓A": False,
                "30分钟笔多头左侧平仓B": False,

                "30分钟笔多头右侧平仓A": False,
                "30分钟笔多头右侧平仓B": False,
                "30分钟笔多头右侧平仓C": False,
            })

            if sum([x['low'] > s['30分钟_第N笔结束标记的上边沿'] for x in self.kas['5分钟'].kline_raw[-3:]]) == 3:
                s['5分钟最近三根K线站稳30分钟第N笔上沿'] = True

            if sum([x['high'] < s['30分钟_第N笔结束标记的下边沿'] for x in self.kas['5分钟'].kline_raw[-3:]]) == 3:
                s['5分钟最近三根K线跌破30分钟第N笔下沿'] = True

            # 笔多头开仓 ABCD
            long_open_right_a = s['5分钟最近三根K线站稳30分钟第N笔上沿'] or s['30分钟_第N笔结束标记的分型强弱'] == 'strong'
            long_open_right_b = s['5分钟_当下笔多头两重有效阻击'] or s['5分钟_当下笔多头三重有效阻击']
            long_open_must = (not s['30分钟_第N笔向下发生破坏']) and s['dt'].minute % 5 == 0
            if long_open_must:
                if s['30分钟_当下笔多头两重有效阻击']:
                    if long_open_right_a:
                        s['30分钟笔多头右侧开仓A'] = True
                    if long_open_right_b:
                        s['30分钟笔多头右侧开仓B'] = True

                if s['30分钟_当下笔多头三重有效阻击']:
                    if long_open_right_a:
                        s['30分钟笔多头右侧开仓C'] = True
                    if long_open_right_b:
                        s['30分钟笔多头右侧开仓D'] = True

            # 笔多头平仓 ABCD
            long_close_left_a = (s['5分钟_第N笔出井'] == '向上大井' or s['5分钟_五笔趋势类背驰'] == 'up') \
                                and s['5分钟_第N笔结束标记的分型强弱'] == 'strong'
            long_close_left_b = s['5分钟_第N笔涨跌力度'] == '向上笔新高盘背' and s['5分钟_第N笔结束标记的分型强弱'] == 'strong'

            long_close_right_a = s['5分钟最近三根K线跌破30分钟第N笔下沿'] and s['30分钟_第N笔结束标记的分型强弱'] == 'strong'
            long_close_right_b = s['5分钟_第N笔结束标记的上边沿'] < s['30分钟_第N笔结束标记的下边沿'] \
                                 and "向上" in s['5分钟_第N笔涨跌力度']
            long_close_right_c = s['5分钟_当下笔空头两重有效阻击'] or s['5分钟_当下笔空头三重有效阻击']

            long_close_must = (not s['30分钟_第N笔向上发生破坏']) and s['dt'].minute % 5 == 0
            if long_close_must:
                if s['30分钟_第N笔涨跌力度'] in ['向上笔不创新高', "向上笔新高盘背"]:
                    if long_close_left_a:
                        s['30分钟笔多头左侧平仓A'] = True
                    if long_close_left_b:
                        s['30分钟笔多头左侧平仓B'] = True

                    if long_close_right_a:
                        s['30分钟笔多头右侧平仓A'] = True
                    if long_close_right_b:
                        s['30分钟笔多头右侧平仓B'] = True
                    if long_close_right_c:
                        s['30分钟笔多头右侧平仓C'] = True

        if "日线" in self.freqs and "30分钟" in self.freqs and "5分钟" in self.freqs:
            s.update({
                "30分钟最近三根K线站稳日线第N笔上沿": False,
                "30分钟最近三根K线跌破日线第N笔下沿": False,

                "日线笔多头右侧开仓A": False,
                "日线笔多头右侧开仓B": False,
                "日线笔多头右侧开仓C": False,
                "日线笔多头右侧开仓D": False,

                "日线笔多头左侧平仓A": False,
                "日线笔多头左侧平仓B": False,

                "日线笔多头右侧平仓A": False,
                "日线笔多头右侧平仓B": False,
                "日线笔多头右侧平仓C": False,
            })

            if sum([x['low'] > s['日线_第N笔结束标记的上边沿'] for x in self.kas['30分钟'].kline_raw[-3:]]) == 3 \
                    and "向下" in s['日线_第N笔涨跌力度']:
                s['30分钟最近三根K线站稳日线第N笔上沿'] = True

            if sum([x['high'] < s['日线_第N笔结束标记的下边沿'] for x in self.kas['30分钟'].kline_raw[-3:]]) == 3 \
                    and "向上" in s['日线_第N笔涨跌力度']:
                s['30分钟最近三根K线跌破日线第N笔下沿'] = True

            # 笔多头开仓 ABCD
            long_open_right_a = s['日线_第N笔结束标记的分型强弱'] == 'strong' and s['30分钟最近三根K线站稳日线第N笔上沿']
            long_open_right_b = s['5分钟_第N笔出井'] == '向下大井' \
                                or ("向下小井" in s['5分钟_第N笔出井'] and "向下小井" in s['5分钟_第N-2笔出井']) \
                                or ((s['5分钟_当下笔多头两重有效阻击'] or s['5分钟_当下笔多头三重有效阻击'])
                                    and s['5分钟_第N笔涨跌力度'] == "向下笔新低盘背")
            long_open_right_c = s['日线_最近一个分型类型'] == 'd' \
                                 and (s['5分钟_当下笔多头三重有效阻击'] or s['5分钟_当下笔多头两重有效阻击']) \
                                 and s['5分钟_第N笔涨跌力度'] == "向下笔不创新低"
            long_open_right_d = s['5分钟_最近两个笔中枢状态'] == '向下' \
                                and (s['5分钟_当下笔多头三重有效阻击'] or s['5分钟_当下笔多头两重有效阻击'])

            long_open_must = (not s['日线_第N笔向下发生破坏']) \
                             and (s['日线_当下笔多头两重有效阻击'] or s['日线_当下笔多头三重有效阻击'])
            if long_open_must:
                if long_open_right_a:
                    s['日线笔多头右侧开仓A'] = True
                if long_open_right_b:
                    s['日线笔多头右侧开仓B'] = True
                if long_open_right_c:
                    s['日线笔多头右侧开仓C'] = True
                if long_open_right_d:
                    s['日线笔多头右侧开仓D'] = True

            # 笔多头平仓 ABCD
            long_close_left_a = (s['30分钟_第N笔出井'] == '向上大井' or s['30分钟_五笔趋势类背驰'] == 'up') \
                                and s['30分钟_第N笔结束标记的分型强弱'] == 'strong'
            long_close_left_b = s['30分钟_第N笔涨跌力度'] == '向上笔新高盘背' and s['30分钟_第N笔结束标记的分型强弱'] == 'strong'

            long_close_right_a = s['30分钟最近三根K线跌破日线第N笔下沿'] and s['日线_第N笔结束标记的分型强弱'] == 'strong'
            long_close_right_b = s['30分钟_第N笔结束标记的上边沿'] < s['日线_第N笔结束标记的下边沿'] and "向上" in s['30分钟_第N笔涨跌力度']
            long_close_right_c = s['30分钟_当下笔空头两重有效阻击'] or s['30分钟_当下笔空头三重有效阻击']

            long_close_must = (not s['日线_第N笔向上发生破坏']) and s['dt'].minute % 30 == 0
            if long_close_must:
                if s['日线_第N笔涨跌力度'] in ['向上笔不创新高', "向上笔新高盘背"]:
                    if long_close_left_a:
                        s['日线笔多头左侧平仓A'] = True
                    if long_close_left_b:
                        s['日线笔多头左侧平仓B'] = True

                    if long_close_right_a:
                        s['日线笔多头右侧平仓A'] = True
                    if long_close_right_b:
                        s['日线笔多头右侧平仓B'] = True
                    if long_close_right_c:
                        s['日线笔多头右侧平仓C'] = True
        return s

    def update_factors(self, data):
        """更新多级别联立因子"""
        for row in data:
            self.kg.update(row)
        klines_one = self.kg.get_klines({k: 1 for k in self.freqs})
        for freq, klines_ in klines_one.items():
            k = klines_[-1]
            self.kas[freq].update(k)

        self.symbol = self.kas["1分钟"].symbol
        self.end_dt = self.kas["1分钟"].end_dt
        self.latest_price = self.kas["1分钟"].latest_price
        self.s = self._calculate_factors()

