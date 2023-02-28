# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/12/13 21:43
describe: 概念、行业、指数等股票聚类板块感应器

三个问题：
1）如何找出引领大盘的概念、行业、指数
2）板块内股票相比于板块走势，划分强中弱
3）根据指数强弱进行账户总仓位控制
"""
import os
import traceback
import inspect
from datetime import timedelta, datetime
import pandas as pd
from tqdm import tqdm
from typing import Callable
from czsc import envs
from czsc.utils import WordWriter, io
from czsc.utils.plt_plot import plot_bins_return
from czsc.data.ts_cache import TsDataCache, Freq
from czsc.traders import generate_czsc_signals
from czsc.sensors.utils import get_index_beta, turn_over_rate, max_draw_down, discretizer


class ThsConceptsSensor:
    """
    输入：同花顺概念列表；同花顺概念日线行情
    输出：每一个交易日的同花顺强势概念
    """
    def __init__(self,
                 results_path: str,
                 sdt: str,
                 edt: str,
                 dc: TsDataCache,
                 get_signals: Callable,
                 get_event: Callable,
                 ths_index_type='N'):
        """

        :param results_path: 结果保存路径
        :param sdt: 开始日期
        :param edt: 结束日期
        :param dc: 数据缓存对象
        :param get_signals: 信号获取函数
        :param get_event: 事件定义函数
        :param ths_index_type: 同花顺指数类型 N-板块指数 I-行业指数 S-同花顺特色指数
        """
        self.name = self.__class__.__name__
        self.dc = dc
        self.get_signals = get_signals
        self.get_event = get_event
        self.event = get_event()
        self.base_freq = Freq.D.value
        self.freqs = [Freq.W.value, Freq.M.value]
        self.dc = dc
        self.ths_index_type = ths_index_type
        self.verbose = envs.get_verbose()
        self.cache = dict()
        self.results_path = results_path
        os.makedirs(self.results_path, exist_ok=True)

        self.sdt = sdt
        self.edt = edt
        self.file_docx = os.path.join(results_path, f'{self.event.name}_{self.ths_index_type}_{sdt}_{edt}.docx')
        writer = WordWriter(self.file_docx)
        if not os.path.exists(self.file_docx):
            writer.add_title(f"同花顺指数（{self.ths_index_type}）感应器报告")
            writer.add_page_break()
            writer.add_heading(f"{datetime.now().strftime('%Y-%m-%d %H:%M')} {self.event.name}", level=1)

            writer.add_heading("参数配置", level=2)
            writer.add_paragraph(f"测试方法描述：{self.event.name}")
            writer.add_paragraph(f"测试起止日期：{sdt} ~ {edt}")
            writer.add_paragraph(f"信号计算函数：\n{inspect.getsource(self.get_signals)}")
            writer.add_paragraph(f"事件具体描述：\n{inspect.getsource(self.get_event)}")
            writer.save()
        self.writer = writer
        self.file_ssd = os.path.join(results_path, f'ths_all_strong_days_{self.ths_index_type}.pkl')
        if os.path.exists(self.file_ssd):
            self.ssd, self.cache = io.read_pkl(self.file_ssd)
        else:
            self.ssd = self.get_all_strong_days()
            io.save_pkl([self.ssd, self.cache], self.file_ssd)

        self.betas = get_index_beta(dc, sdt, edt, freq='D',
                                    indices=['000001.SH', '000016.SH', '000905.SH',
                                             '000300.SH', '399001.SZ', '399006.SZ'])

    def get_strong_days(self, ts_code, name):
        """获取单个概念的强势日期

        :param ts_code: 同花顺概念代码
        :param name: 同花顺概念名称
        :return:
        """
        dc = self.dc
        event = self.event
        sdt = self.sdt
        edt = self.edt
        start_date = pd.to_datetime(sdt) - timedelta(days=3000)
        bars = dc.ths_daily(ts_code=ts_code, start_date=start_date, end_date=edt, raw_bar=True)
        n_bars = dc.ths_daily(ts_code=ts_code, start_date=start_date, end_date=edt, raw_bar=False)
        nb_dicts = {row['trade_date'].strftime("%Y%m%d"): row for row in n_bars.to_dict("records")}

        signals = generate_czsc_signals(bars, self.get_signals, sdt=sdt, df=False, freqs=self.freqs)
        results = []
        for s in signals:
            m, f = event.is_match(s)
            if m:
                res = {'ts_code': ts_code, 'name': name, 'reason': f}
                nb_info = nb_dicts.get(s['dt'].strftime("%Y%m%d"), None)
                if not nb_info:
                    print(f"not match nb info: {nb_info}")

                res.update(nb_info)
                results.append(res)

        df_res = pd.DataFrame(results)
        if not df_res.empty:
            df_res = df_res[pd.to_datetime(sdt) <= df_res['trade_date']]
            df_res = df_res[df_res['trade_date'] <= pd.to_datetime(edt)]

            n_bars = n_bars[pd.to_datetime(sdt) <= n_bars['trade_date']]
            n_bars = n_bars[n_bars['trade_date'] <= pd.to_datetime(edt)]

            print(f"{ts_code} - {name} 强势: {len(df_res)}, mean={df_res.n1b.mean()}, sum={df_res.n1b.sum()}")
            print(f"{ts_code} - {name} 基准: {len(n_bars)}, mean={n_bars.n1b.mean()}, sum={n_bars.n1b.sum()}")

        self.cache[ts_code] = {"signals": signals, "n_bars": n_bars, 'df_res': df_res}

    def get_all_strong_days(self):
        """获取所有指数的强势日期"""
        dc = self.dc
        concepts = dc.ths_index(exchange='A', type_=self.ths_index_type)
        concepts = concepts.to_dict('records')
        results = []
        for row in tqdm(concepts, desc="validate"):
            ts_code = row['ts_code']
            name = row['name']
            try:
                self.get_strong_days(ts_code, name)
                results.append(self.cache[ts_code]['df_res'])
            except:
                print(f"get_strong_days error: {ts_code}, {name}")
                traceback.print_exc()

        df = pd.concat(results, ignore_index=True)
        return df

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

    def validate(self):
        """验证传感器在一段时间内的表现"""
        dc = self.dc
        daily = []
        detail = []
        trade_cal = dc.trade_cal()
        trade_cal = trade_cal[trade_cal.is_open == 1]
        trade_dates = trade_cal[(trade_cal['cal_date'] >= self.sdt)
                                & (trade_cal['cal_date'] <= self.edt)].cal_date.to_list()
        n_cols = [x for x in self.ssd.columns if x[0] == 'n' and x[-1] == 'b']

        holds = []
        dfg_map = {trade_date.strftime("%Y%m%d"): dfg for trade_date, dfg in self.ssd.groupby('trade_date')}
        for trade_date in trade_dates:
            dfg = dfg_map.get(trade_date, pd.DataFrame())
            if dfg.empty:
                if self.verbose:
                    print(f"{trade_date} 结果为空")
                row = {'trade_date': trade_date, 'number': 0}
                row.update({k: 0 for k in n_cols})
            else:
                detail.append(dfg)
                row = {'trade_date': trade_date, 'number': len(dfg)}
                row.update(dfg[n_cols].mean().to_dict())
            daily.append(row)
            holds.append(self.create_next_positions(dfg))

        df_daily = pd.DataFrame(daily)
        df_detail = pd.concat(detail, ignore_index=True)
        df_holds = pd.concat(holds, ignore_index=True)
        df_turns, tor = turn_over_rate(df_holds)
        j, i, mdd = max_draw_down(df_daily['n1b'])
        p = {"名称": "板块轮动", '最大回撤': mdd,
             "回撤开始": df_daily.iloc[j]['trade_date'],
             "回撤结束": df_daily.iloc[i]['trade_date'],
             "组合换手": tor,
             "平均数量": df_daily['number'].mean(),
             }
        p.update(df_daily[n_cols].mean().to_dict())

        f = pd.ExcelWriter(os.path.join(self.results_path, "selected.xlsx"))
        df_detail.to_excel(f, index=False, sheet_name="强势板块")
        df_turns.to_excel(f, index=False, sheet_name="每日换手")
        pd.DataFrame([p]).to_excel(f, index=False, sheet_name="组合表现")
        df_daily.to_excel(f, index=False, sheet_name="每日统计")
        f.close()
        return df_daily, df_detail


class MeanPlatesSensor:
    """基于股票打分取平均的板块轮动观察

    数据要素：
    1. 全市场所有股票日线行情
    2. 板块列表，板块成分股，所有板块日线行情
    """
    def __init__(self,
                 dc: TsDataCache,
                 res_path,
                 sdt,
                 mean_col,
                 mean_col_bins,
                 sort_col,
                 sort_col_bins,
                 create_features: Callable,
                 get_plates: Callable,
                 max_num=100,
                 max_adj=10):
        """

        :param dc:
        :param res_path:
        :param sdt: 开始时间
        :param mean_col: 个股上用于计算板块均值的特征列
        :param mean_col_bins: 对mean_col按分位数分成20层，指定选中哪些分位数区间
        :param sort_col: 个股上用于排序约束组合换手率的特征列
        :param sort_col_bins: 对sort_col按分位数分成20层，指定选中哪些分位数区间
        :param create_features: 个股特征创建函数
        :param get_plates: 板块划分的数据获取函数
        """
        self.dc = dc
        self.sdt = sdt
        self.mean_col = mean_col
        self.mean_col_bins = mean_col_bins
        self.sort_col = sort_col
        self.sort_col_bins = sort_col_bins
        self.res_path = res_path
        self.create_features = create_features
        self.get_plates = get_plates
        os.makedirs(self.res_path, exist_ok=True)

        # 创建实验结果目录
        self.exp_path = os.path.join(res_path, f"{get_plates.__name__}_{mean_col}_{sdt}")
        os.makedirs(self.exp_path, exist_ok=True)

        # 获取全市场股票相关信息
        file_dfb = os.path.join(self.res_path, 'dfb.pkl')
        if os.path.exists(file_dfb):
            self.dfb = pd.read_pickle(file_dfb)
        else:
            # 统一用后复权数据处理，实盘跟踪过程也使用后复权
            dfb = dc.stocks_daily_bars(sdt=dc.sdt, edt=dc.edt, adj='hfq')
            dfb = self.create_features(dfb)
            # 去除ST，引入市值之类的指标
            dfc = dc.stocks_daily_basic_new(dc.sdt, dc.edt)
            dfb = dfb.merge(dfc, on=['ts_code', 'trade_date'], how='left', suffixes=("", "_drop"))
            dfb.drop([x for x in dfb.columns if x.endswith("_drop")], axis=1, inplace=True)
            self.dfb = dfb[(dfb['dt'] >= pd.to_datetime(sdt)) & (dfb['is_st'] == False)]
            self.dfb.to_pickle(file_dfb)

        self.n_cols = [x for x in self.dfb.columns if x[0] == 'n' and x[-1] == 'b']
        self.b_cols = [x for x in self.dfb.columns if x[0] == 'b' and x[-1] == 'b']

        # p 是 plates 的首字母，代表板块列表；p_bars 所有板块的日线行情；p_members 所有板块的成分股
        self.p, self.p_bars, self.p_members = self.get_plates()

        file_plates = os.path.join(self.res_path, f'plates_{mean_col}.pkl')
        if os.path.exists(file_plates):
            self.plates = pd.read_pickle(file_plates)
        else:
            self.plates = self.mean_by_plates()
            self.plates.to_pickle(file_plates)

        # 执行组合构建
        self.dfh1 = self.create_base_holds(mean_col, mean_col_bins)
        self.dfh2 = self.create_holds(mean_col, mean_col_bins, sort_col, sort_col_bins, max_num, max_adj)

    def mean_by_plates(self):
        """计算每个板块每天的打分"""
        sdt = self.dfb['dt'].min().strftime("%Y%m%d")
        mean_col = self.mean_col
        dc = self.dc
        # 全市场所有股票行情特征按 dt 聚合
        df_map = {dt_: dfg for dt_, dfg in self.dfb.dropna(subset=[mean_col]).groupby('dt')}

        # 按板块聚合成分股
        pm_map = {k: dfg for k, dfg in self.p_members.groupby('ts_code')}
        p = [x for x in self.p.to_dict('records') if x['ts_code'] in pm_map.keys()]

        _results = []
        for date in tqdm(dc.get_dates_span(sdt, dc.edt), desc=f"mean_by_plates | {mean_col}"):
            try:
                dft = df_map[pd.to_datetime(date)]
                for _row in p:
                    members = pm_map[_row['ts_code']]
                    dfm = dft[dft['ts_code'].isin(members['code'])]
                    _row[mean_col] = dfm[mean_col].mean() if len(dfm) > 0 else 0

                _df = pd.DataFrame(p).sort_values(mean_col, ascending=False).reset_index(drop=True)
                _df['dt'] = date
                _results.append(_df)
            except:
                print(f"fail on {date}")

        _df_plates = pd.concat(_results, ignore_index=True)
        _df_plates['trade_date'] = pd.to_datetime(_df_plates['dt'])
        df_plates = _df_plates.merge(self.p_bars, on=['ts_code', 'trade_date'], how='left')
        df_plates['dt'] = pd.to_datetime(df_plates['trade_date'])

        df_plates = discretizer(df_plates, mean_col, n_bins=20)
        file_png = os.path.join(self.res_path, f"{mean_col}_bins20_plates.png")
        plot_bins_return(df_plates, f"{mean_col}_bins20", file_png)
        return df_plates

    def get_base_stocks(self, mean_col, mean_col_bins, sort_col=None, sort_col_bins=None):
        """结合板块轮动和个股RPS打分构建基础持仓组合"""
        df_plates = self.plates
        dfb = self.dfb
        p_members = self.p_members
        df_sp = df_plates[df_plates[f"{mean_col}_bins20"].isin(mean_col_bins)]

        _results = []
        for dt, dfg in df_sp.groupby('dt'):
            # 获取 dfg 中给定板块的所有成分股
            df_tm = p_members[p_members['ts_code'].isin(dfg['ts_code'])]
            # 暂时不选北交所股票
            selected = [x for x in df_tm['code'].unique().tolist() if x.split('.')[1] in ['SH', 'SZ']]
            _dfs = pd.DataFrame({'dt': dt, 'ts_code': selected})
            _results.append(_dfs)
        dfs = pd.concat(_results)
        dfs = dfs.merge(dfb, on=['dt', 'ts_code'], how='left')
        dfs['下期一字板'] = dfs['下期一字板'].fillna(0)
        dfs = dfs[(dfs['下期一字板'] == 0) & (dfs['is_st'] != True)]

        # dt 后延一期，因为 T 时刻选出的股票是 T+1 时刻的持仓
        dts = list(pd.to_datetime(self.dc.get_dates_span(df_sp['dt'].min(), '20300101')))
        next_dt = {dts[i]: dts[i+1] for i in range(len(dts)-1)}
        dfs['dt'] = dfs['dt'].apply(lambda x: next_dt[x])

        if sort_col and sort_col_bins:
            dfs = dfs[dfs[f"{sort_col}_bins20"].isin(sort_col_bins)]
        return dfs

    def create_base_holds(self, mean_col, mean_col_bins):
        """选取板块轮动的所有成分股构建持仓基础持仓组合"""
        dfs = self.get_base_stocks(mean_col, mean_col_bins, sort_col=None, sort_col_bins=None)
        holds = []
        dfs_map = {date: dfg for date, dfg in dfs.groupby('trade_date')}
        dates = sorted(dfs_map.keys())

        for date in tqdm(dates, desc=f"create_base_holds"):
            _df = dfs_map[date]
            _dfh = _df[['dt', 'ts_code', 'n1b']].reset_index(drop=True)
            _dfh['持仓权重'] = 1 / len(_dfh)
            _dfh.rename({'dt': '成分日期', 'ts_code': '证券代码'}, axis=1, inplace=True)
            holds.append(_dfh)

        dfh = pd.concat(holds, ignore_index=True)
        dfh['成分日期'] = dfh['成分日期'].apply(lambda x: x.strftime("%Y-%m-%d"))

        exp_name = f"P{'#'.join([str(x) for x in mean_col_bins])}"
        res_path = os.path.join(self.exp_path, exp_name)

        from czsc.traders.performance import stock_holds_performance
        stock_holds_performance(self.dc, dfh, res_path)
        return dfh

    def create_holds(self, mean_col, mean_col_bins, sort_col, sort_col_bins, max_num=100, max_adj=10):
        """结合板块轮动和个股RPS打分构建持仓组合

        :param mean_col: 板块轮动列
        :param mean_col_bins: 板块轮动列分层可取值
        :param sort_col: 个股RPS打分列
        :param sort_col_bins: 个股RPS打分列分层可取值
        :param max_num: 组合最大持仓数量约束
        :param max_adj: 组合每期可调整数量约束
        :return:
        """
        dfs = self.get_base_stocks(mean_col, mean_col_bins, sort_col, sort_col_bins)
        dfb = self.dfb

        # 约束最大持仓数量和每天最多换仓比例
        holds = []
        last = pd.DataFrame()
        dfs_map = {date: dfg for date, dfg in dfs.groupby('trade_date')}
        dates = sorted(dfs_map.keys())
        weight = 1 / max_num

        for date in tqdm(dates, desc=f"create_holds | {sort_col}"):
            _df = dfs_map[date]

            if last.empty:
                # 交易第一天直接买满 max_num
                assert not holds
                _df = _df.sort_values([sort_col], ascending=False).head(max_num)
            else:
                # 删掉已经有的持仓股
                _df = _df[~_df['ts_code'].isin(last['证券代码'])]

                # 获取可以加入组合的 max_adj 只股票
                _df = _df.sort_values([sort_col], ascending=False).head(max_adj)

            _dfh = _df[['dt', 'ts_code', 'n1b']].reset_index(drop=True)
            _dfh['持仓权重'] = weight
            _dfh.rename({'dt': '成分日期', 'ts_code': '证券代码'}, axis=1, inplace=True)

            if last.empty:
                hold = _dfh.copy(deep=True)
            else:
                # 根据 RPS 删掉 max_adj 只原有持仓
                last['成分日期'] = date
                last = last[['成分日期', '证券代码', '持仓权重']]
                last = last.merge(dfb[['dt', 'ts_code', sort_col, 'n1b']],
                                  left_on=['成分日期', '证券代码'], right_on=['dt', 'ts_code'], how='left')
                last = last.sort_values([sort_col], ascending=False).head(max_num - max_adj)
                last = last[['成分日期', '证券代码', '持仓权重', 'n1b']]

                # 更新持仓
                hold = pd.concat([last, _dfh], ignore_index=True)

            holds.append(hold)
            last = hold.copy(deep=True)
        dfh = pd.concat(holds, ignore_index=True)
        dfh['成分日期'] = dfh['成分日期'].apply(lambda x: x.strftime("%Y-%m-%d"))

        exp_name = f"P{'#'.join([str(x) for x in mean_col_bins])}_" \
                   f"{sort_col}{'#'.join([str(x) for x in sort_col_bins])}_{max_num}_{max_adj}"
        res_path = os.path.join(self.exp_path, exp_name)
        from czsc.traders.performance import stock_holds_performance
        stock_holds_performance(self.dc, dfh, res_path=res_path)
        return dfh

