# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/10/30 20:18
describe: A股市场感应器若干，主要作为编写感应器的示例
"""
import os
import os.path
import traceback
import inspect
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import timedelta, datetime
from collections import OrderedDict, Counter
from tqdm import tqdm
from typing import Callable
from czsc.objects import Event
from czsc.utils import io
from czsc.data.ts_cache import TsDataCache, Freq
from czsc.sensors.utils import get_index_beta, generate_signals, max_draw_down, turn_over_rate
from czsc.utils import WordWriter


plt.style.use('ggplot')
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False


class StocksDaySensor:
    """以日线为基础周期的强势股票感应器

    输入：市场个股全部行情、概念板块成分信息
    输出：强势个股列表以及概念板块分布
    """

    def __init__(self,
                 results_path: str,
                 sdt: str,
                 edt: str,
                 dc: TsDataCache,
                 get_signals: Callable,
                 get_event: Callable):
        """

        :param results_path: 结果保存路径
        :param sdt: 开始日期
        :param edt: 结束日期
        :param dc: 数据缓存对象
        :param get_signals: 信号计算函数
        :param get_event: 事件定义函数
        """
        self.name = self.__class__.__name__
        self.version = "V20211213"
        os.makedirs(results_path, exist_ok=True)
        self.results_path = results_path
        self.sdt = sdt
        self.edt = edt

        self.get_signals = get_signals
        self.get_event = get_event
        self.event: Event = get_event()
        self.base_freq = Freq.D.value
        self.freqs = [Freq.W.value, Freq.M.value]

        self.file_docx = os.path.join(results_path, f'{self.event.name}_{sdt}_{edt}.docx')
        writer = WordWriter(self.file_docx)
        if not os.path.exists(self.file_docx):
            writer.add_title("股票选股强度验证")
            writer.add_page_break()
            writer.add_heading(f"{datetime.now().strftime('%Y-%m-%d %H:%M')} {self.event.name}", level=1)

            writer.add_heading("参数配置", level=2)
            writer.add_paragraph(f"测试方法描述：{self.event.name}")
            writer.add_paragraph(f"测试起止日期：{sdt} ~ {edt}")
            writer.add_paragraph(f"信号计算函数：\n{inspect.getsource(self.get_signals)}")
            writer.add_paragraph(f"事件具体描述：\n{inspect.getsource(self.get_event)}")
            writer.save()
        self.writer = writer

        self.dc = dc
        self.betas = ['000905.SH', '000300.SH', '399006.SZ']
        self.all_cache = dict()
        self.res_cache = dict()
        self.file_ssd = os.path.join(results_path, 'stocks_strong_days.pkl')
        if os.path.exists(self.file_ssd):
            self.ssd = io.read_pkl(self.file_ssd)
        else:
            self.ssd = self.get_stocks_strong_days()      # ssd 是 stocks_strong_days 的缩写，表示全市场股票的强势日期
            io.save_pkl(self.ssd, self.file_ssd)

    def get_share_strong_days(self, ts_code: str, name: str):
        """获取单个标的全部强势信号日期"""
        dc = self.dc
        event = self.event
        sdt = self.sdt
        edt = self.edt

        start_date = pd.to_datetime(self.sdt) - timedelta(days=3000)
        bars = dc.pro_bar(ts_code=ts_code, start_date=start_date, end_date=edt, freq='D', asset="E", raw_bar=True)
        n_bars = dc.pro_bar(ts_code=ts_code, start_date=sdt, end_date=edt, freq='D', asset="E", raw_bar=False)
        nb_dicts = {row['trade_date'].strftime("%Y%m%d"): row for row in n_bars.to_dict("records")}
        signals = generate_signals(bars, sdt, self.base_freq, self.freqs, self.get_signals)

        results = []
        for s in signals:
            m, f = event.is_match(s)
            if m:
                res = {
                    'ts_code': ts_code,
                    'name': name,
                    'reason': f,
                }
                nb_info = nb_dicts.get(s['dt'].strftime("%Y%m%d"), None)
                if not nb_info:
                    print(f"not match nb info: {nb_info}")

                res.update(nb_info)
                results.append(res)

        df_res = pd.DataFrame(results)
        if df_res.empty:
            print(f"{ts_code} - {name} - empty")
        else:
            df_res = df_res[pd.to_datetime(sdt) <= df_res['trade_date']]
            df_res = df_res[df_res['trade_date'] <= pd.to_datetime(edt)]

            print(f"{ts_code} - {name} 强势: {len(df_res)}, mean={df_res.n1b.mean()}, sum={df_res.n1b.sum()}")
            print(f"{ts_code} - {name} 基准: {len(n_bars)}, mean={n_bars.n1b.mean()}, sum={n_bars.n1b.sum()}")

            # 加入总市值
            df_ = dc.daily_basic(ts_code, sdt, dc.edt)
            df_['trade_date'] = pd.to_datetime(df_['trade_date'])
            df_res = df_res.merge(df_[['trade_date', 'total_mv']], on='trade_date', how='left')

        self.all_cache[ts_code] = df_res

    def get_stocks_strong_days(self):
        """获取全部股票的强势日期"""
        stocks = self.dc.stock_basic()

        for row in tqdm(stocks.to_dict('records'), desc="validate"):
            ts_code = row['ts_code']
            name = row['name']
            try:
                self.get_share_strong_days(ts_code, name)
            except:
                print(f"get_share_strong_days error: {ts_code}, {name}")
                traceback.print_exc()

        res = []
        for ts_code, x in self.all_cache.items():
            if x.empty:
                continue
            res.append(x)

        df = pd.concat(res, ignore_index=True)
        return df

    def filter_by_index(self, dfg, index_code=None):
        """使用指数成分过滤

        :param dfg: 单个交易日的强势股选股结果
        :param index_code: 指数代码
        :return: 过滤后的选股结果
        """
        if not index_code or dfg.empty:
            return dfg

        dc = self.dc
        assert dfg['trade_date'].nunique() == 1
        trade_date = dfg['trade_date'].max()

        index_members = dc.index_weight(index_code, trade_date)
        ts_codes = list(index_members['con_code'].unique())
        return dfg[dfg.ts_code.isin(ts_codes)]

    def filter_by_concepts(self, dfg, top_n=20, min_n=3, method='v1'):
        """使用板块效应过滤

        :param dfg: 单个交易日的强势股选股结果
        :param top_n: 选取前 n 个密集概念
        :param min_n: 单股票至少要有 n 个概念在 top_n 中
        :param method: 打分计算方法
            v1  直接取板块中的强势股数量作为分数
            v2  板块内强势股数 / 板块内股数
        :return: 过滤后的选股结果
        """
        if dfg.empty or not top_n or not min_n:
            return dfg, []

        dc = self.dc
        ths_members = dc.get_all_ths_members(exchange="A", type_="N")
        ths_members = ths_members[~ths_members['概念名称'].isin([
            'MSCI概念', '沪股通', '深股通', '融资融券', '上证180成份股', '央企国资改革',
            '标普道琼斯A股', '中证500成份股', '上证380成份股', '沪深300样本股',
        ])]

        ths_concepts = ths_members[ths_members.code.isin(dfg.ts_code)]
        if method == 'v1':
            key_concepts = [k for k, v in Counter(ths_concepts['概念名称'].to_list()).most_common(top_n)]
        elif method == 'v2':
            all_count = Counter(ths_members['概念名称'].to_list())
            sel_count = Counter(ths_concepts['概念名称'].to_list())
            df_scores = pd.DataFrame([{"concept": k, 'score': sel_count[k] / all_count[k]}
                                      for k in sel_count.keys()])
            key_concepts = df_scores.sort_values('score', ascending=False).head(top_n)['concept'].to_list()
        else:
            raise ValueError(f"method value error")

        sel = ths_concepts[ths_concepts['概念名称'].isin(key_concepts)]
        ts_codes = [k for k, v in Counter(sel.code).most_common() if v >= min_n]
        dfg = dfg[dfg.ts_code.isin(ts_codes)]
        dfg.loc[:, '概念板块'] = dfg.ts_code.apply(lambda x: ths_concepts[ths_concepts.code == x]['概念名称'].to_list())
        dfg.loc[:, '概念数量'] = dfg['概念板块'].apply(len)

        return dfg, key_concepts

    @staticmethod
    def filter_by_market_value(dfg, min_total_mv=None):
        """使用总市值过滤

        :param dfg: 单个交易日的强势股选股结果
        :param min_total_mv: 最小总市值，单位为万元，1e6万元 = 100亿
        :return: 过滤后的选股结果
        """
        if dfg.empty or not min_total_mv:
            return dfg

        return dfg[dfg['total_mv'] >= min_total_mv]

    @staticmethod
    def filter_by_b20b(dfg, max_count=-1):
        """使用b20b过滤，b20b 表示前20个交易日的涨跌幅

        :param dfg: 单个交易日的强势股选股结果
        :param max_count: 最多保留结果数量
        :return: 过滤后的选股结果
        """
        if dfg.empty or (not max_count) or len(dfg) < max_count:
            return dfg

        split = 0.8
        dfg = dfg.sort_values("b20b", ascending=True)
        head_i = int((len(dfg) - max_count) * split) + 1
        tail_i = len(dfg) - int((len(dfg) - max_count) * (1 - split))

        return dfg.iloc[head_i: tail_i]

    def create_next_positions(self, dfg):
        """构建某天选股结果对应的下一交易日持仓明细

        :param dfg: 单个交易日的强势股选股结果
        :return: 下一交易日持仓明细
        """
        if dfg.empty:
            return dfg

        trade_cal = self.dc.trade_cal()
        trade_cal = trade_cal[trade_cal.is_open == 1]
        trade_dates = trade_cal.cal_date.to_list()
        trade_date = dfg['trade_date'].iloc[0]

        hold = dfg.copy()
        hold['成分日期'] = trade_dates[trade_dates.index(trade_date.strftime("%Y%m%d")) + 1]
        hold['持仓权重'] = 0.98 / len(dfg)
        hold.rename({'ts_code': "证券代码", "close": "交易价格"}, inplace=True, axis=1)
        hold = hold[['证券代码', '持仓权重', '交易价格', '成分日期']]
        hold['成分日期'] = pd.to_datetime(hold['成分日期']).apply(lambda x: x.strftime("%Y/%m/%d"))
        return hold

    def get_latest_strong(self, fc_top_n=20, fc_min_n=2, min_total_mv=1e6):
        """获取最近一个交易日的选股结果"""
        df = self.ssd.copy()
        trade_date = df['trade_date'].max()
        dfg = df[df['trade_date'] == trade_date]
        dfg, key_concepts = self.filter_by_concepts(dfg, fc_top_n, fc_min_n)
        dfg = self.filter_by_market_value(dfg, min_total_mv)
        holds = self.create_next_positions(dfg)
        return dfg, holds

    def validate_performance(self,
                             index_code=None,
                             fc_top_n=None,
                             fc_min_n=None,
                             min_total_mv=None,
                             max_count=None,
                             file_output=None):
        """验证传感器在一组过滤参数下的表现

        :param index_code: 指数成分过滤
        :param fc_top_n: 板块效应过滤参数1
        :param fc_min_n: 板块效应过滤参数2
        :param min_total_mv: 市值效应过滤参数
        :param max_count: b20b过滤参数，控制最大选出数量
        :param file_output: 输出结果文件
        :return:
        """
        dc = self.dc
        sdt = self.sdt
        edt = self.edt
        df = self.ssd.copy()

        results = []
        detail = []
        holds = []

        for trade_date, dfg in df.groupby('trade_date'):
            try:
                if dfg.empty:
                    print(f"{trade_date} 选股结果为空")
                    continue
                dfg, key_concepts = self.filter_by_concepts(dfg, top_n=fc_top_n, min_n=fc_min_n)
                dfg = self.filter_by_market_value(dfg, min_total_mv)
                dfg = self.filter_by_index(dfg, index_code)
                dfg = self.filter_by_b20b(dfg, max_count)

                res = {'trade_date': trade_date, "key_concepts": key_concepts, 'number': len(dfg)}
                res.update(dfg[['n1b', 'n2b', 'n3b', 'n5b', 'n10b', 'n20b']].mean().to_dict())
                results.append(res)
                detail.append(dfg)
                holds.append(self.create_next_positions(dfg))
            except:
                traceback.print_exc()

        df_detail = pd.concat(detail)
        df_holds = pd.concat(holds, ignore_index=True)
        df_turns, tor = turn_over_rate(df_holds)
        df_merged = pd.DataFrame(results)
        df_merged['trade_date'] = pd.to_datetime(df_merged['trade_date'])

        beta = get_index_beta(dc, sdt, edt, freq='D', file_xlsx=None, indices=self.betas)
        df_n1b = pd.DataFrame()
        for name, df_ in beta.items():
            if name in self.betas:
                df_n1b['trade_date'] = pd.to_datetime(df_.trade_date.to_list())
                df_n1b[name] = df_.n1b.to_list()

        df_ = df_merged[['trade_date', 'number', 'n1b']]
        df_.rename({'n1b': 'selector'}, axis=1, inplace=True)
        df_.reset_index(drop=True, inplace=True)
        df_n1b = df_n1b.merge(df_, on='trade_date', how='left')
        df_n1b.fillna(0, inplace=True)

        mdd_info = []
        for col in self.betas + ['selector']:
            df_n1b[f"{col}_curve"] = df_n1b[col].cumsum()
            df_n1b[f"{col}_curve"] += 10000
            start_i, end_i, mdd = max_draw_down(df_n1b[col].to_list())
            start_dt = df_n1b.iloc[start_i]['trade_date']
            end_dt = df_n1b.iloc[end_i]['trade_date']
            row = {
                '标的': col,
                "开始日期": sdt,
                "结束日期": edt,
                "累计收益": round(df_n1b[col].sum(), 4),
                "单笔收益": round(df_n1b[col].mean(), 4),
                "最大回撤": mdd,
                "回撤开始日期": start_dt,
                "回撤结束日期": end_dt,
            }
            mdd_info.append(row)

        df_mdd = pd.DataFrame(mdd_info)

        if file_output:
            f = pd.ExcelWriter(file_output)
            for name, df_ in beta.items():
                df_.to_excel(f, index=False, sheet_name=name)

            df_detail.to_excel(f, sheet_name="选股结果", index=False)
            df_turns.to_excel(f, sheet_name="每日换手", index=False)
            df_holds.to_excel(f, sheet_name="持仓明细", index=False)
            df_merged.to_excel(f, sheet_name="每日统计", index=False)
            df_n1b.to_excel(f, sheet_name="资金曲线", index=False)
            df_mdd.to_excel(f, sheet_name="性能对比", index=False)
            f.close()

        return df_detail, df_merged, df_holds, df_n1b, df_mdd, tor

    def grip_search(self, grid_params=None):
        """网格搜索超参数

        :param grid_params: 网格参数
        :return:
        """
        if not grid_params:
            grid_params = {
                "fc_top_n": list(range(10, 160, 10)),
                "fc_min_n": list(range(1, 7, 1)),
                "min_total_mv": [5e5, 10e5, 20e5],
                "max_count": list(range(100, 300, 100)),
            }

        filter_params = [{
            'fc_top_n': None,
            'fc_min_n': None,
            'min_total_mv': None,
            'max_count': None,
        }]
        for i in grid_params['fc_top_n']:
            for j in grid_params['fc_min_n']:
                for k in grid_params['min_total_mv']:
                    for m in grid_params['max_count']:
                        filter_params.append({
                            'fc_top_n': i,
                            'fc_min_n': j,
                            'min_total_mv': k,
                            'max_count': m,
                        })

        results = []
        for conf in tqdm(filter_params):
            index_code = None
            fc_top_n = conf['fc_top_n']
            fc_min_n = conf['fc_min_n']
            min_total_mv = conf['min_total_mv']
            max_count = conf['max_count']
            file_output = None
            try:
                output = self.validate_performance(index_code, fc_top_n, fc_min_n,
                                                   min_total_mv, max_count, file_output)
                df_detail, df_merged, df_holds, df_n1b, df_mdd, tor = output
                res = dict(conf)
                for n in ['n1b', 'n2b', 'n3b', 'n5b', 'n10b', 'n20b']:
                    res[n] = round(df_merged[n].mean(), 4)

                # max_count	min_count	avg_count
                res['max_count'] = df_merged['number'].max()
                res['min_count'] = df_merged['number'].min()
                res['avg_count'] = int(df_merged['number'].mean())
                res['turn_over'] = tor

                results.append(res)

                df = pd.DataFrame(results)
                file_grid_res = os.path.join(self.results_path, f'{self.event.name}_grid_search_results.xlsx')
                df.to_excel(file_grid_res, index=False)
                print(f"grid search results saved into {file_grid_res}")
            except:
                traceback.print_exc()

    def write_validate_report(self, title, conf):
        """编写试验报告到 Word 文件

        :param title: 试验组别的标题
        :param conf: 验证的参数
        :return: None
        """
        results_path = self.results_path
        writer = self.writer
        index_code = conf.get('index_code', None)
        fc_top_n = conf.get('fc_top_n', None)
        fc_min_n = conf.get('fc_min_n', None)
        min_total_mv = conf.get('min_total_mv', None)
        max_count = conf.get('max_count', None)
        file_output = os.path.join(results_path,
                                   f"{self.event.name}_{index_code}_{fc_top_n}"
                                   f"_{fc_min_n}_{min_total_mv}_{max_count}.xlsx")
        output = self.validate_performance(index_code, fc_top_n, fc_min_n, min_total_mv, max_count, file_output)
        df_detail, df_merged, df_holds, df_n1b, df_mdd, tor = output

        writer.add_page_break()
        writer.add_heading(title, level=1)
        writer.add_df_table(pd.DataFrame({"参数名称": list(conf.keys()), '参数值': list(conf.values())}))
        writer.add_paragraph('结果对比：')
        writer.add_df_table(df_mdd)
        writer.save()

        # 绘制曲线对比图
        x_col = 'trade_date'
        y_col = 'selector_curve'
        beta_cols = [x for x in df_n1b.columns if x.endswith('_curve') and not x.startswith('selector')]

        for beta_col in beta_cols:
            writer.add_heading(f"与{beta_col.replace('_curve', '')}进行对比", level=2)
            plt.close()
            fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(9, 5*3))

            df_ = df_n1b[[x_col, y_col, beta_col]].copy()
            df_['alpha'] = df_[y_col] - df_[beta_col]
            df_.rename({x_col: 'date', y_col: y_col.replace('_curve', ''),
                        beta_col: beta_col.replace('_curve', '')}, inplace=True, axis=1)
            for i, col in enumerate([y_col.replace('_curve', ''), 'alpha', beta_col.replace('_curve', '')], 0):
                ax = axes[i]
                sns.lineplot(x='date', y=col, data=df_, ax=ax)
                ax.text(x=df_['date'].iloc[0], y=int(df_[col].mean()), s=f"{col}：{int(df_[col].iloc[-1])}", fontsize=12)
                ax.set_title(f"{col}", loc='center')
                ax.set_xlabel("")

            file_png = os.path.join(results_path, f"{y_col}_{beta_col}.png")
            plt.savefig(file_png, bbox_inches='tight', dpi=100)
            plt.close()
            writer.add_picture(file_png, width=15, height=21)
            writer.save()
            os.remove(file_png)

    def report_performance(self, filter_params=None):
        """撰写报告"""
        if not filter_params:
            # "min_total_mv": 1e6,    # 最小总市值，单位为万元，1e6万元 = 100亿
            # "fc_top_n": 40,         # 板块效应 - 选择出现数量最多的 top_n 概念
            # 'fc_min_n': 4           # 单股票至少有 min_n 概念在 top_n 中
            filter_params = [
                # 不加任何过滤
                {"index_code": None, "fc_top_n": None, 'fc_min_n': None, "min_total_mv": None},

                # 验证指数过滤
                {"index_code": "000905.SH", "fc_top_n": None, 'fc_min_n': None, "min_total_mv": None},
                {"index_code": '000300.SH', "fc_top_n": None, 'fc_min_n': None, "min_total_mv": None},

                # 验证市值效应
                {"index_code": None, "fc_top_n": None, 'fc_min_n': None, "min_total_mv": 3e5},
                {"index_code": None, "fc_top_n": None, 'fc_min_n': None, "min_total_mv": 5e5},
                {"index_code": None, "fc_top_n": None, 'fc_min_n': None, "min_total_mv": 10e5},
                {"index_code": None, "fc_top_n": None, 'fc_min_n': None, "min_total_mv": 15e5},
                {"index_code": None, "fc_top_n": None, 'fc_min_n': None, "min_total_mv": 20e5},

                # 验证板块效应
                {"index_code": None, "fc_top_n": 50, 'fc_min_n': 3, "min_total_mv": 1e6},
                {"index_code": None, "fc_top_n": 50, 'fc_min_n': 2, "min_total_mv": 1e6},
                {"index_code": None, "fc_top_n": 30, 'fc_min_n': 3, "min_total_mv": 1e6},
                {"index_code": None, "fc_top_n": 30, 'fc_min_n': 2, "min_total_mv": 1e6},
                {"index_code": None, "fc_top_n": 20, 'fc_min_n': 2, "min_total_mv": 1e6},
                {"index_code": None, "fc_top_n": 10, 'fc_min_n': 1, "min_total_mv": 1e6},
            ]

        for i, row in enumerate(filter_params, 1):
            self.write_validate_report(f"第{i}组测试结果", row)
        return self.file_docx

