# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/11/4 17:39
describe: A股强势股票传感器
"""
import os
import os.path
import traceback
import inspect
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import timedelta, datetime
from collections import Counter
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


def selected_filter_by_index(dc: TsDataCache, dfg: pd.DataFrame, index_code=None):
    """使用指数成分过滤

    :param dc: 数据缓存对象
    :param dfg: 单个交易日的强势股选股结果
    :param index_code: 指数代码
    :return: 过滤后的选股结果
    """
    if not index_code or dfg.empty:
        return dfg

    assert dfg['trade_date'].nunique() == 1
    trade_date = dfg['trade_date'].max()

    index_members = dc.index_weight(index_code, trade_date)
    ts_codes = list(index_members['con_code'].unique())
    return dfg[dfg.ts_code.isin(ts_codes)]


def selected_filter_by_concepts(dc, dfg, top_n=20, min_n=3, method='v1'):
    """使用板块效应过滤

    :param dc: 数据缓存对象
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


def selected_filter_by_market_value(dfg, min_total_mv=None):
    """使用总市值过滤

    :param dfg: 单个交易日的强势股选股结果
    :param min_total_mv: 最小总市值，单位为万元，1e6万元 = 100亿
    :return: 过滤后的选股结果
    """
    if dfg.empty or not min_total_mv:
        return dfg

    return dfg[dfg['total_mv'] >= min_total_mv]


def selected_filter_by_rps(dfg, n=21, v_range=(0.2, 0.8), max_count=-1):
    """使用b20b过滤，b20b 表示前20个交易日的涨跌幅

    :param dfg: 单个交易日的强势股选股结果
    :param n: RPS的计算区间
    :param v_range: RPS值按从大到小排序后的可选区间
        默认为 0.2 ~ 0.8，表示可选区间为排序位置在 20% ~ 80% 区间的股票
    :param max_count: 最多保留结果数量
    :return: 过滤后的选股结果
    """
    if dfg.empty or (not max_count) or len(dfg) < max_count:
        return dfg
    rps_col = f"b{n}b"
    # dfg = dfg.sort_values(rps_col, ascending=True)
    # dfg = dfg.reset_index(drop=True)
    # dfg = dfg.iloc[int(len(dfg) * v_range[0]): int(len(dfg) * v_range[1])]
    # return dfg.tail(max_count)

    split = v_range[1]
    dfg = dfg.sort_values(rps_col, ascending=True)
    head_i = int((len(dfg) - max_count) * split) + 1
    tail_i = len(dfg) - int((len(dfg) - max_count) * (1 - split))

    return dfg.iloc[head_i: tail_i]


def create_next_positions(dc: TsDataCache, dfg: pd.DataFrame):
    """构建某天选股结果对应的下一交易日持仓明细

    :param dc: 数据缓存对象
    :param dfg: 单个交易日的强势股选股结果
    :return: 下一交易日持仓明细
    """
    if dfg.empty:
        return dfg

    trade_cal = dc.trade_cal()
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


def plot_alpha_v1(beta_name, df_alpha, file_png) -> None:
    """用三个并列线图来绘制 alpha 信息

    :param beta_name: 基准指数名称
    :param df_alpha: 包含 ['trade_date', 'beta', 'selector']
          trade_date     beta    selector
        0 2018-01-02  88.4782   93.471190
        1 2018-01-03  45.8368   41.008785
        2 2018-01-04  -0.4383 -132.660895
        3 2018-01-05  45.0786  120.726060
        4 2018-01-08  -0.6757  -17.231665
    :param file_png: 图片保存文件名
    :return: None
    """
    plt.close()
    fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(9, 5*3))
    df_alpha['beta_curve'] = df_alpha['beta'].cumsum()
    df_alpha['selector_curve'] = df_alpha['selector'].cumsum()
    df_alpha['alpha_curve'] = df_alpha['selector_curve'] - df_alpha['beta_curve']

    df_alpha.rename({'trade_date': 'date', 'beta_curve': f"beta_curve:{beta_name}"}, inplace=True, axis=1)
    for i, col in enumerate(['alpha_curve', 'selector_curve', f"beta_curve:{beta_name}"], 0):
        ax = axes[i]
        sns.lineplot(x='date', y=col, data=df_alpha, ax=ax)
        ax.text(x=df_alpha['date'].iloc[0], y=int(df_alpha[col].mean()),
                s=f"{col}：{int(df_alpha[col].iloc[-1])}", fontsize=12)
        ax.set_title(f"{col}", loc='center')
        ax.set_xlabel("")
    plt.savefig(file_png, bbox_inches='tight', dpi=100)
    plt.close()


def plot_alpha_v2(beta_name, df_alpha, file_png) -> None:
    """用线图来绘制 alpha 信息

    :param beta_name: 基准指数名称
    :param df_alpha: 包含 ['trade_date', 'beta', 'selector']
          trade_date     beta    selector
        0 2018-01-02  88.4782   93.471190
        1 2018-01-03  45.8368   41.008785
        2 2018-01-04  -0.4383 -132.660895
        3 2018-01-05  45.0786  120.726060
        4 2018-01-08  -0.6757  -17.231665
    :param file_png: 图片保存文件名
    :return: None
    """
    df_alpha['beta_curve'] = df_alpha['beta'].cumsum()
    df_alpha['selector_curve'] = df_alpha['selector'].cumsum()
    df_alpha['alpha_curve'] = df_alpha['selector_curve'] - df_alpha['beta_curve']
    df_alpha.rename({'trade_date': 'date', 'beta_curve': f"beta_curve:{beta_name}"}, inplace=True, axis=1)

    plt.close()
    plt.figure(figsize=(9, 5))
    sns.lineplot(x='date', y='alpha_curve', data=df_alpha)
    sns.lineplot(x='date', y='selector_curve', data=df_alpha)
    sns.lineplot(x='date', y=f"beta_curve:{beta_name}", data=df_alpha)
    plt.legend(labels=['超额', '选股', f"基准{beta_name}"])
    plt.savefig(file_png, bbox_inches='tight', dpi=100)


def plot_alpha_v3(beta_name, df_alpha, file_png) -> None:
    """用类似MACD图来绘制 alpha 信息

    :param beta_name: 基准指数名称
    :param df_alpha: 包含 ['trade_date', 'beta', 'selector']
          trade_date     beta    selector
        0 2018-01-02  88.4782   93.471190
        1 2018-01-03  45.8368   41.008785
        2 2018-01-04  -0.4383 -132.660895
        3 2018-01-05  45.0786  120.726060
        4 2018-01-08  -0.6757  -17.231665
    :param file_png: 图片保存文件名
    :return: None
    """
    df_alpha['beta_curve'] = df_alpha['beta'].cumsum()
    df_alpha['selector_curve'] = df_alpha['selector'].cumsum()
    df_alpha['alpha'] = df_alpha['selector'] - df_alpha['beta']
    df_alpha['alpha_curve'] = df_alpha['selector_curve'] - df_alpha['beta_curve']
    df_alpha.rename({'trade_date': 'date', 'beta_curve': f"beta_curve:{beta_name}"}, inplace=True, axis=1)

    plt.close()
    plt.figure(figsize=(9, 5))
    x = df_alpha['date']
    plt.bar(x, height=df_alpha['alpha'], width=0.01, color='blue', label='alpha')
    plt.plot(x, df_alpha['alpha_curve'], label='alpha_curve')
    plt.plot(x, df_alpha['selector_curve'], label='selector_curve')
    plt.plot(x, df_alpha[f"beta_curve:{beta_name}"], label=f"beta_curve:{beta_name}")
    plt.legend()
    plt.savefig(file_png, bbox_inches='tight', dpi=100)


class StocksDaySensor:
    """以日线为基础周期的强势股票感应器

    输入：市场个股全部行情、概念板块成分信息
    输出：强势个股列表以及概念板块分布
    """

    def __init__(self,
                 experiment_path: str,
                 sdt: str,
                 edt: str,
                 dc: TsDataCache,
                 strategy: Callable,
                 signals_n: int = 0,
                 ):

        self.name = self.__class__.__name__
        self.version = "V20220404"
        self.strategy = strategy
        self.tactic = strategy('000001')
        self.signals_n = signals_n
        self.get_signals, self.get_event = self.tactic['get_signals'], self.tactic['get_event']
        self.event: Event = self.get_event()
        self.base_freq = Freq.D.value
        self.freqs = [Freq.W.value, Freq.M.value]

        self.experiment_path = experiment_path
        self.results_path = os.path.join(experiment_path, f"{self.event.name}_{sdt}_{edt}")
        self.signals_path = os.path.join(experiment_path, 'signals')
        os.makedirs(self.experiment_path, exist_ok=True)
        os.makedirs(self.results_path, exist_ok=True)
        os.makedirs(self.signals_path, exist_ok=True)

        self.sdt = sdt
        self.edt = edt
        self.verbose = os.environ.get('verbose', False)

        self.file_docx = os.path.join(self.results_path, f'{self.event.name}_{sdt}_{edt}.docx')
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

            with open(os.path.join(self.results_path, f"{strategy.__name__}.txt"), mode='w') as f:
                f.write(inspect.getsource(strategy))

        self.writer = writer
        self.dc = dc
        self.betas = ['000905.SH', '000300.SH', '399006.SZ']
        get_index_beta(dc, sdt, edt, freq='D', indices=self.betas,
                       file_xlsx=os.path.join(self.results_path, 'betas.xlsx'))
        file_dfm = os.path.join(self.results_path, f'df_event_matched_{sdt}_{edt}.pkl')
        file_dfb = os.path.join(self.experiment_path, f'df_all_bars_{sdt}_{edt}.pkl')
        if os.path.exists(file_dfm):
            self.dfm = io.read_pkl(file_dfm)
            self.dfb = io.read_pkl(file_dfb)
        else:
            self.dfm, self.dfb = self.get_stock_strong_days()
            io.save_pkl(self.dfm, file_dfm)
            io.save_pkl(self.dfb, file_dfb)
        self.nb_cols = [x for x in self.dfb.columns if x[0] == 'n' and x[-1] == 'b']

    def get_share_strong_days(self, ts_code: str, name: str):
        """获取单个标的全部强势信号日期"""
        dc = self.dc
        event = self.event
        sdt = self.sdt
        edt = self.edt
        file_signals = os.path.join(self.signals_path, f"{ts_code}.pkl")

        if os.path.exists(file_signals):
            signals, n_bars = io.read_pkl(file_signals)
            if self.verbose:
                print(f"get_share_strong_days: load signals from {file_signals}")
        else:
            start_date = pd.to_datetime(self.sdt) - timedelta(days=3000)
            bars = dc.pro_bar(ts_code=ts_code, start_date=start_date, end_date=edt, freq='D', asset="E", raw_bar=True)
            n_bars = dc.pro_bar(ts_code=ts_code, start_date=sdt, end_date=edt, freq='D', asset="E", raw_bar=False)
            signals = generate_signals(bars, sdt, self.strategy)
            io.save_pkl([signals, n_bars], file_signals)

        nb_dicts = {row['trade_date'].strftime("%Y%m%d"): row for row in n_bars.to_dict("records")}
        event_matched = []
        for s in signals:
            m, f = event.is_match(s)
            if m:
                nb_info = nb_dicts.get(s['dt'].strftime("%Y%m%d"), None)
                r = {'name': name, 'event_match': True, 'factor_match': f}
                if nb_info:
                    r.update(nb_info)
                    event_matched.append(r)

        dfs = pd.DataFrame(event_matched)
        if event_matched:
            df_ = dc.daily_basic(ts_code, sdt, dc.edt)
            df_['trade_date'] = pd.to_datetime(df_['trade_date'])
            dfs = dfs.merge(df_[['trade_date', 'total_mv']], on='trade_date', how='left')
            dfs = dfs[pd.to_datetime(sdt) <= dfs['trade_date']]
            dfs = dfs[dfs['trade_date'] <= pd.to_datetime(edt)]
        print(f"{ts_code} - {name}: {len(dfs)}")
        return dfs, n_bars

    def get_stock_strong_days(self):
        """获取全部股票的强势日期"""
        stocks = self.dc.stock_basic()

        all_matched = []
        all_bars = []
        for row in tqdm(stocks.to_dict('records'), desc="get_stock_strong_days"):
            ts_code = row['ts_code']
            name = row['name']
            try:
                dfs, n_bars = self.get_share_strong_days(ts_code, name)
                all_matched.append(dfs)
                all_bars.append(n_bars)
            except:
                print(f"get_share_strong_days error: {ts_code}, {name}")
                traceback.print_exc()

        dfm = pd.concat(all_matched, ignore_index=True)
        dfb = pd.concat(all_bars, ignore_index=True)
        return dfm, dfb

    def get_selected(self,
                     index_code=None,
                     fc_top_n=None,
                     fc_min_n=None,
                     min_total_mv=None,
                     max_count=None):
        """验证传感器在一组过滤参数下的表现

        :param index_code: 指数成分过滤
        :param fc_top_n: 板块效应过滤参数1
        :param fc_min_n: 板块效应过滤参数2
        :param min_total_mv: 市值效应过滤参数
        :param max_count: 控制最大选出数量
        :return:
        """
        dc = self.dc
        df = self.dfm

        selected_dfg = {}
        for trade_date, dfg in df.groupby('trade_date'):
            try:
                if dfg.empty:
                    print(f"{trade_date} 选股结果为空")
                    continue
                dfg, key_concepts = selected_filter_by_concepts(dc, dfg, top_n=fc_top_n, min_n=fc_min_n)
                dfg = selected_filter_by_market_value(dfg, min_total_mv)
                dfg = selected_filter_by_index(dc, dfg, index_code)
                dfg = selected_filter_by_rps(dfg, n=21, v_range=(0.1, 0.8), max_count=max_count)
                selected_dfg[trade_date] = {'dfg': dfg, 'key_concepts': key_concepts}
            except:
                traceback.print_exc()

        return selected_dfg

    def get_agg_selected(self, selected_dfg, window_size: int = 1):
        """滑动窗口聚合选股结果

        :param selected_dfg: get_selected 输出的结果
        :param window_size: 聚合窗口大小
        :return:
        """
        dc = self.dc
        dfb = self.dfb
        assert window_size > 0
        if window_size > 1:
            trade_cal = dc.trade_cal()
            trade_cal = trade_cal[trade_cal['is_open'] == 1].cal_date.to_list()
            trade_cal = [pd.to_datetime(x) for x in trade_cal]

            selected_agg = {}
            for td, dfg in tqdm(selected_dfg.items(), desc='agg_by_window'):
                i = trade_cal.index(td)
                windows = trade_cal[i-window_size+1: i+1]
                res = []
                for td_ in windows:
                    dfg = selected_dfg.get(td_, None)
                    if dfg:
                        df = dfg['dfg']
                        df['trade_date'] = td
                        res.append(dfg['dfg'])
                dfd = pd.concat(res, ignore_index=True)
                dfd_cols = ['name', 'event_match', 'factor_match', 'ts_code', 'trade_date',
                            'total_mv', '概念板块', '概念数量']
                dfd = dfd.drop_duplicates('ts_code', ignore_index=True)[dfd_cols]
                dfd = dfd.merge(dfb, on=['ts_code', 'trade_date'], how='left')
                selected_agg[td] = dfd
        else:
            selected_agg = {dt: x['dfg'] for dt, x in selected_dfg.items()}

        return selected_agg

    def validate_performance(self,
                             index_code=None,
                             fc_top_n=None,
                             fc_min_n=None,
                             min_total_mv=None,
                             max_count=None,
                             window_size=1,
                             save: bool = False,
                             ):
        """验证传感器在一组过滤参数下的表现

        :param index_code: 指数成分过滤
        :param fc_top_n: 板块效应过滤参数1
        :param fc_min_n: 板块效应过滤参数2
        :param min_total_mv: 市值效应过滤参数
        :param max_count: b20b过滤参数，控制最大选出数量
        :param window_size: 按 window_size 聚合多天的结果到一天
        :param save: 是否保存结果到本地
        :return:
        """
        dc = self.dc
        sdt = self.sdt
        edt = self.edt
        selected_dfg = self.get_selected(index_code, fc_top_n, fc_min_n, min_total_mv, max_count)
        selected_agg = self.get_agg_selected(selected_dfg, window_size)

        # 分析
        performances = []
        for td, df in selected_agg.items():
            p = {'trade_date': td, "number": len(df)}
            if df.empty:
                p.update({x: 0 for x in self.nb_cols})
            else:
                p.update(df[self.nb_cols].mean().to_dict())
            performances.append(p)

        df_p = pd.DataFrame(performances)
        df_detail = pd.concat([v for k, v in selected_agg.items()])
        df_holds = pd.concat([create_next_positions(dc, v) for k, v in selected_agg.items()], ignore_index=True)
        df_turns, tor = turn_over_rate(df_holds)

        beta = get_index_beta(dc, sdt, edt, freq='D', file_xlsx=None, indices=self.betas)
        df_n1b = pd.DataFrame({"trade_date": pd.to_datetime(dc.get_dates_span(sdt, edt))})
        for name, df_ in beta.items():
            if name in self.betas:
                n1b_map = {row['trade_date']: row['n1b'] for _, row in df_.iterrows()}
                df_n1b[name] = df_n1b.apply(lambda x: n1b_map.get(x['trade_date'], 0), axis=1)

        df_ = df_p[['trade_date', 'number', 'n1b']]
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
                "交易胜率": round(len(df_n1b[df_n1b[col] >= 0]) / len(df_n1b), 4),
                "最大回撤": mdd,
                "回撤开始日期": start_dt,
                "回撤结束日期": end_dt,
            }
            mdd_info.append(row)

        df_mdd = pd.DataFrame(mdd_info)

        if save:
            output_path = os.path.join(self.results_path,
                                       f"{index_code}_{fc_top_n}_{fc_min_n}_{min_total_mv}_{max_count}_{window_size}")
            os.makedirs(output_path, exist_ok=True)
            f = pd.ExcelWriter(os.path.join(output_path, 'performances.xlsx'))
            df_turns.to_excel(f, sheet_name="每日换手", index=False)
            df_p.to_excel(f, sheet_name="每日统计", index=False)
            df_n1b.to_excel(f, sheet_name="资金曲线", index=False)
            df_mdd.to_excel(f, sheet_name="性能对比", index=False)
            f.close()

            df_detail.to_csv(os.path.join(output_path, 'selected_details.csv'), index=False)
            df_holds.to_csv(os.path.join(output_path, 'holds.csv'), index=False)

        return df_detail, df_p, df_holds, df_n1b, df_mdd, tor

    def get_latest_selected(self,
                            index_code=None,
                            fc_top_n=None,
                            fc_min_n=None,
                            min_total_mv=None,
                            max_count=None,
                            window_size=1,
                            ):
        """获取下一个交易日的强势股列表

        :param index_code:
        :param fc_top_n:
        :param fc_min_n:
        :param min_total_mv:
        :param max_count:
        :param window_size:
        :return:
        """
        output = self.validate_performance(index_code, fc_top_n, fc_min_n, min_total_mv, max_count, window_size)
        df_detail, df_p, df_holds, df_n1b, df_mdd, tor = output
        df_holds['成分日期'] = pd.to_datetime(df_holds['成分日期'])
        max_date = df_holds['成分日期'].max()
        df_latest = df_holds[df_holds['成分日期'] == max_date]
        return df_latest

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
        window_size = 1

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
            try:
                output = self.validate_performance(index_code, fc_top_n, fc_min_n,
                                                   min_total_mv, max_count, window_size, save=False)
                df_detail, df_merged, df_holds, df_n1b, df_mdd, tor = output
                res = dict(conf)
                nb_keys = [x for x in df_merged.columns if x[0] == 'n' and x[-1] == 'b']
                for n in nb_keys:
                    res[n] = round(df_merged[n].mean(), 2)

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
        window_size = conf.get('window_size', 1)

        output = self.validate_performance(index_code, fc_top_n, fc_min_n,
                                           min_total_mv, max_count, window_size, save=True)
        df_detail, df_merged, df_holds, df_n1b, df_mdd, tor = output

        writer.add_page_break()
        writer.add_heading(title, level=1)
        writer.add_df_table(pd.DataFrame({"参数名称": list(conf.keys()), '参数值': list(conf.values())}))
        writer.add_paragraph('结果对比：')
        writer.add_df_table(df_mdd)
        msg = f"组合换手率：{tor}；最大持仓数：{df_merged['number'].max()}；" \
              f"平均持仓数：{int(df_merged['number'].mean())}；最小持仓数：{df_merged['number'].min()}"
        writer.add_paragraph(msg)
        writer.save()

        # 绘制曲线对比图
        for beta_name in self.betas:
            df_alpha = df_n1b[['trade_date', beta_name, 'selector']]
            df_alpha.rename({beta_name: 'beta'}, axis=1, inplace=True)
            file_png = os.path.join(results_path, f"{beta_name}_alpha.png")
            plot_alpha_v2(beta_name, df_alpha, file_png)

            writer.add_heading(f"与{beta_name}进行对比", level=2)
            writer.add_picture(file_png, width=15, height=9)
            writer.save()
            os.remove(file_png)

