# coding: utf-8
import webbrowser
import pandas as pd
from pyecharts.charts import Page
from tqdm import tqdm
from typing import List, Callable
from ..analyze import KlineAnalyze
from ..utils.echarts_plot import kline_pro, heat_map
from ..utils.kline_generator import KlineGeneratorBy1Min, get_next_end_time
from ..factors import KlineFactors


def cal_nbar_percentile(k: dict, kn: List[dict], n: int) -> float:
    """计算 N 周期区间百分位

    假设选股策略确认选股时间为 T，股价为 P，T+N 区间内的K线最高价为 MAX_P，最低价为 MIN_P，则
    N周期区间百分位 = (MAX_P - P) / (MAX_P - MIN_P) * 100;
    N周期区间百分位值域为(0, 100)，值越大，说明离区间最大值越远，对于做多交易而言有更高的安全性。

    :param k: dict
        信号出现时的 K 线，如：
        {'symbol': '000001.SH',
         'dt': '2007-04-05 15:00:00',
         'open': 3286.16,
         'close': 3319.14,
         'high': 3326.92,
         'low': 3259.63,
         'vol': 114528051.0}

    :param kn: List[dict]
        信号出现后的 N 根 K 线，如：
        [{'symbol': '000001.SH',
          'dt': '2007-04-06 15:00:00',
          'open': 3287.68,
          'close': 3323.59,
          'high': 3334.22,
          'low': 3273.86,
          'vol': 119644881.0},
         {'symbol': '000001.SH',
          'dt': '2007-04-09 15:00:00',
          'open': 3333.42,
          'close': 3398.95,
          'high': 3399.51,
          'low': 3333.26,
          'vol': 137314104.0}]

    :param n: int
        周期数 N

    :return: float
    """
    assert len(kn) == n, "计算 {} 周期区间百分位时传入的 kn 数量为 {}".format(n, len(kn))
    c = k['close']
    min_p = min([x['low'] for x in kn] + [c])
    max_p = max([x['high'] for x in kn] + [c])

    if max_p == min_p:
        return 0
    else:
        percentile = round((max_p - c) / (max_p - min_p) * 100, 2)
        return percentile


def cal_nbar_income(k: dict, kn: List[dict], n: int) -> float:
    """计算 N 周期区间收益

    假设选股策略确认选股时间为 T，股价为 P，第 T+N 根K线收盘价为 C，则
    N周期绝对收益 = (C - P) / P * 10000;
    N周期绝对收益值域为(-10000, +inf)，值越大，说明绝对收益越大，对于做多交易而言有更高的收益率。

    :param k: dict
        信号出现时的 K 线，如：
        {'symbol': '000001.SH',
         'dt': '2007-04-05 15:00:00',
         'open': 3286.16,
         'close': 3319.14,
         'high': 3326.92,
         'low': 3259.63,
         'vol': 114528051.0}

    :param kn: List[dict]
        信号出现后的 N 根 K 线，如：
        [{'symbol': '000001.SH',
          'dt': '2007-04-06 15:00:00',
          'open': 3287.68,
          'close': 3323.59,
          'high': 3334.22,
          'low': 3273.86,
          'vol': 119644881.0},
         {'symbol': '000001.SH',
          'dt': '2007-04-09 15:00:00',
          'open': 3333.42,
          'close': 3398.95,
          'high': 3399.51,
          'low': 3333.26,
          'vol': 137314104.0}]

    :param n: int
        周期数 N

    :return: float
    """
    assert len(kn) == n, "计算 {} 周期区间收益时传入的 kn 数量为 {}".format(n, len(kn))
    c = k['close']
    last_c = kn[-1]['close']

    income = round((last_c - c) / c * 10000, 2)
    return income


class FactorsResearcher:
    """因子研究员"""

    def __init__(self, factors, n_list=None):
        self.factors = factors
        self.performance = None
        if not n_list:
            self.n_list = (8, 13, 21, 34, 55, 89, 144, 233, 377, 610)
        else:
            self.n_list = n_list

        # 使用 kg 合成各级别K线
        self.kg = KlineGeneratorBy1Min()
        for row in factors:
            self.kg.update({
                "symbol": row['symbol'],
                "dt": row['dt'],
                "open": row['open'],
                "close": row['close'],
                "high": row['high'],
                "low": row['low'],
                "vol": row['vol'],
            })
        self.calculate_nbar()
        # self.da = pd.DataFrame(self.factors)

    def remove_duplicates(self, name, replace_value=False):
        """清理指定因子的连续信号

        :param replace_value:
        :param name: 因子名
        :return:
        """
        for i in range(len(self.factors)):
            if i < 5:
                self.factors[i]['{}_duplicated'.format(name)] = replace_value
            else:
                rows = self.factors[i-4: i]
                if rows[-1][name] in [x[name] for x in rows[:-1]]:
                    self.factors[i]['{}_duplicated'.format(name)] = replace_value
                else:
                    self.factors[i]['{}_duplicated'.format(name)] = rows[-1][name]

    def show_klines(self, file_html, open_in_browser=True):
        kf = KlineFactors(self.kg, bi_mode='new', max_count=100000000)
        kf.take_snapshot(file_html)
        if open_in_browser:
            webbrowser.open(file_html)

    def calculate_nbar(self):
        """计算 nbar 相关特征"""
        max_len = len(self.factors)
        for i, k in tqdm(enumerate(self.factors), desc="calculate_nbar"):
            k['base'] = 1
            for n in self.n_list:
                if i + n + 1 < max_len:
                    kn = self.factors[i + 1: i + n + 1]
                    k['n{}b_均收益'.format(n)] = cal_nbar_income(k, kn, n)
                    k['n{}b_百分位'.format(n)] = cal_nbar_percentile(k, kn, n)
                else:
                    k['n{}b_均收益'.format(n)] = 0
                    k['n{}b_百分位'.format(n)] = 0

    def factors_performance(self, file_xlsx, factors_col):
        """查看所有因子的表现"""
        if 'base' not in factors_col:
            factors_col = ['base'] + factors_col

        results = []
        for factor_name in tqdm(factors_col, desc="factors_performance"):
            groups = dict()
            for row in self.factors:
                v = groups.get(row[factor_name], [])
                v.append(row)
                groups[row[factor_name]] = v

            for v, samples in groups.items():
                res = {"factor_name": factor_name, "factor_value": v,
                       "count": len(samples), "pct": len(samples) / len(self.factors)}
                for n in self.n_list:
                    k1 = 'n{}b_均收益'.format(n)
                    res[k1] = sum([x[k1] for x in samples]) / len(samples)
                    k2 = 'n{}b_百分位'.format(n)
                    res[k2] = sum([x[k2] for x in samples]) / len(samples)
                    s1 = [x for x in samples if x[k1] > 0]
                    s2 = [x for x in samples if x[k1] < 0]
                    res[k1.replace("均收益", "胜率")] = len(s1) / len(samples)
                    s1_mean = sum([x[k1] for x in s1]) / len(s1)
                    s2_mean = sum([abs(x[k1]) for x in s2]) / len(s2)
                    res[k1.replace("均收益", "盈亏比")] = s1_mean / s2_mean
                results.append(res)

        df = pd.DataFrame(results)
        cols = ['factor_name', 'factor_value', 'count', 'pct']
        for n in self.n_list:
            cols.append('n{}b_均收益'.format(n))
            cols.append('n{}b_百分位'.format(n))
            cols.append('n{}b_胜率'.format(n))
            cols.append('n{}b_盈亏比'.format(n))

        for col in cols[3:]:
            df[col] = df[col].apply(lambda x: round(x, 2))
        df[cols].to_excel(file_xlsx, index=False)
        print("factors performance saved into {}".format(file_xlsx))
        self.performance = df[cols]

    def show_bs(self, bs, freq="30分钟", file_html=None, open_in_browser=True, width="1400px", height='580px'):
        """在K线图上将 factor 标记出来

        :param height:
        :param width:
        :param open_in_browser:
        :param file_html:
        :param bs: list of dict
            [{"dt": dt, "mark": buy or sell, "price": 0}]
        :param freq: str
            指定K线图级别
        :return:
        """
        kline = self.kg.get_kline(freq, count=100000000)
        ka = KlineAnalyze(kline, name=freq, bi_mode="new", max_count=100000000, use_xd=False, use_ta=False)
        chart = kline_pro(ka.kline_raw, fx=ka.fx_list, bi=ka.bi_list, xd=ka.xd_list,
                          bs=bs, width=width, height=height)
        if file_html:
            chart.render(file_html)
            if open_in_browser:
                webbrowser.open(file_html)
        return chart

    def show_factor(self, name, value, file_html, freq="30分钟", open_in_browser=True):
        """查看因子某个值的结果

        :param freq:
        :param name: str
            因子名
        :param value: any
            因子值
        :param file_html: str
        :param open_in_browser: bool
        :return:
        """
        rows = [x for x in self.factors if x[name] == value]
        value1 = [{"x": s['dt'], "y": k, "heat": v} for s in rows for k, v in s.items() if "百分位" in k]
        value2 = [{"x": s['dt'], "y": k, "heat": v} for s in rows for k, v in s.items() if "均收益" in k]
        x_label = [s['dt'] for s in rows]
        y_label1 = [k for k, _ in rows[0].items() if "百分位" in k]
        y_label2 = [k for k, _ in rows[0].items() if "均收益" in k]

        hm1 = heat_map(value1, x_label=x_label, y_label=y_label1,
                       title="{}历史表现评估（N周期区间百分位）".format(name), width="1400px", height="480px")
        hm2 = heat_map(value2, x_label=x_label, y_label=y_label2,
                       title="{}历史表现评估（N周期区间收益）".format(name), width="1400px", height="480px")

        bs = [{"dt": get_next_end_time(s['dt'], m=30), "mark": "buy", "price": round(s['close'], 2)} for s in rows]
        chart_kline = self.show_bs(bs, freq=freq, width="1400px", height='480px')
        page = Page(layout=Page.DraggablePageLayout, page_title="{}".format(name))
        page.add(hm1, hm2, chart_kline)

        if file_html:
            page.render(file_html)
            if open_in_browser:
                webbrowser.open(file_html)
        return page

    def add_temp_factors(self, functions: List[Callable]) -> None:
        """新增因子，用于快速研究

        :param functions:
        :return: None
        """
        for factor in functions:
            name = factor.__doc__
            for row in tqdm(self.factors, desc="add {}".format(name)):
                row[name] = factor(row)
        # self.da = pd.DataFrame(self.factors)



