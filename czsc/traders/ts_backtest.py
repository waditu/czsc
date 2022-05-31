# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/2/14 17:25
describe: 基于 Tushare 分钟数据的择时策略快速回测
"""

import os
import inspect
import traceback
import pandas as pd
from tqdm import tqdm
from typing import Callable
from deprecated import deprecated
from czsc import envs
from czsc.data import TsDataCache, freq_cn2ts
from czsc.traders.utils import trader_fast_backtest
from czsc.traders.performance import PairsPerformance
from czsc.utils import x_round
from czsc.objects import cal_break_even_point


def read_raw_results(raw_path, trade_dir="long"):
    """读入指定路径下的回测原始结果

    :param raw_path: 原始结果路径
    :param trade_dir: 交易方向
    :return:
    """
    assert trade_dir in ['long', 'short']

    pairs, p = [], []
    for file in tqdm(os.listdir(raw_path)):
        if len(file) != 14:
            continue
        file = os.path.join(raw_path, file)
        try:
            pairs.append(pd.read_excel(file, sheet_name=f'{trade_dir}_pairs'))
            p.append(pd.read_excel(file, sheet_name=f'{trade_dir}_performance'))
        except:
            print(f"read_raw_results: fail on {file}")

    df_pairs = pd.concat(pairs, ignore_index=True)
    df_p = pd.concat(p, ignore_index=True)
    return df_pairs, df_p


@deprecated(reason="use czsc.traders.performance.PairsPerformance instead", version='0.9.0')
class TraderPerformance:
    """择时交易效果评估"""

    def __init__(self, df_pairs: pd.DataFrame, ):
        """

        :param df_pairs: 全部交易对
        """
        time_convert = lambda x: (x.strftime("%Y年"), x.strftime("%Y年%m月"), x.strftime("%Y-%m-%d"),
                                  f"{x.year}年第{x.weekofyear}周" if x.weekofyear >= 10 else f"{x.year}年第0{x.weekofyear}周",
                                  )
        df_pairs[['开仓年', '开仓月', '开仓日', '开仓周']] = list(df_pairs['开仓时间'].apply(time_convert))
        df_pairs[['平仓年', '平仓月', '平仓日', '平仓周']] = list(df_pairs['平仓时间'].apply(time_convert))

        self.df_pairs = df_pairs
        # 指定哪些列可以用来进行聚合分析
        self.agg_columns = ['标的代码', '交易方向', '平仓年', '平仓月', '平仓周', '平仓日']

    @staticmethod
    def get_pairs_statistics(df_pairs: pd.DataFrame):
        """统计一组交易的基本信息

        :param df_pairs:
        :return:
        """
        if len(df_pairs) == 0:
            info = {
                "开始时间": None,
                "结束时间": None,
                "交易标的数量": 0,
                "总体交易次数": 0,
                "平均持仓天数": 0,

                "平均单笔收益": 0,
                "最大单笔收益": 0,
                "最小单笔收益": 0,

                "交易胜率": 0,
                "累计盈亏比": 0,
                "交易得分": 0,
                "每自然日收益": 0,
                "盈亏平衡点": 0,
            }
            return info

        win_pct = x_round(len(df_pairs[df_pairs['盈亏比例'] > 0]) / len(df_pairs), 4)
        df_gain = df_pairs[df_pairs['盈亏比例'] > 0]
        df_loss = df_pairs[df_pairs['盈亏比例'] <= 0]
        gain = df_gain['盈亏比例'].sum()
        loss = abs(df_loss['盈亏比例'].sum())

        # 限制累计盈亏比最大有效值
        gain_loss_rate = min(x_round(gain / (loss + 0.000001), 2), 5)

        info = {
            "开始时间": df_pairs['开仓时间'].min(),
            "结束时间": df_pairs['平仓时间'].max(),

            "交易标的数量": df_pairs['标的代码'].nunique(),
            "总体交易次数": len(df_pairs),
            "平均持仓天数": x_round(df_pairs['持仓天数'].mean(), 2),

            "平均单笔收益": x_round(df_pairs['盈亏比例'].mean() * 10000, 2),
            "最大单笔收益": x_round(df_pairs['盈亏比例'].max() * 10000, 2),
            "最小单笔收益": x_round(df_pairs['盈亏比例'].min() * 10000, 2),

            "交易胜率": win_pct,
            "累计盈亏比": gain_loss_rate,
            "交易得分": x_round(gain_loss_rate * win_pct, 4),
            "盈亏平衡点": x_round(cal_break_even_point(df_pairs['盈亏比例'].to_list()), 4),
        }

        info['每自然日收益'] = x_round(info['平均单笔收益'] / info['平均持仓天数'], 2)
        return info

    def agg_statistics(self, col: str):
        """按列聚合进行交易对评价"""
        df_pairs = self.df_pairs.copy()
        assert col in self.agg_columns, f"{col} 不是支持聚合的列，参考：{self.agg_columns}"

        results = []
        for name, dfg in df_pairs.groupby(col):
            if dfg.empty:
                continue

            res = {col: name}
            res.update(self.get_pairs_statistics(dfg))
            results.append(res)
        df = pd.DataFrame(results)
        return df

    @property
    def basic_info(self):
        """写入基础信息"""
        df_pairs = self.df_pairs.copy()
        return self.get_pairs_statistics(df_pairs)

    def agg_to_excel(self, file_xlsx):
        """遍历聚合列，保存结果到 Excel 文件中"""
        f = pd.ExcelWriter(file_xlsx)
        for col in self.agg_columns:
            df_ = self.agg_statistics(col)
            df_.to_excel(f, sheet_name=f"{col}聚合", index=False)
        f.close()
        print(f"聚合分析结果文件：{file_xlsx}")


class TsStocksBacktest:
    """基于 Tushare 数据的择时回测系统（股票市场）"""

    def __init__(self,
                 dc: TsDataCache,
                 strategy: Callable,
                 init_n: int,
                 sdt: str,
                 edt: str,
                 ):
        """

        :param dc: Tushare 数据缓存对象
        :param strategy: 股票择时策略
        :param init_n: 初始化 Trader 需要的最少基础K线数量
        :param sdt: 开始回测时间
        :param edt: 结束回测时间
        """
        self.name = self.__class__.__name__
        self.strategy = strategy
        self.init_n = init_n
        self.data_path = dc.data_path
        self.res_path = os.path.join(self.data_path, f"{strategy.__name__}_mbl{envs.get_min_bi_len()}")
        os.makedirs(self.res_path, exist_ok=True)

        file_strategy = os.path.join(self.res_path, f'{strategy.__name__}_strategy.txt')
        with open(file_strategy, 'w', encoding='utf-8') as f:
            f.write(inspect.getsource(strategy))
        print(f"strategy saved into {file_strategy}")

        self.dc, self.sdt, self.edt = dc, sdt, edt
        stocks = self.dc.stock_basic()
        stocks_ = stocks[stocks['list_date'] < '2010-01-01'].ts_code.to_list()
        self.stocks_map = {
            "index": ['000905.SH', '000016.SH', '000300.SH', '000001.SH', '000852.SH',
                      '399001.SZ', '399006.SZ', '399376.SZ', '399377.SZ', '399317.SZ', '399303.SZ'],
            "stock": stocks.ts_code.to_list(),
            "check": ['000001.SZ'],
            "train": stocks_[:200],
            "valid": stocks_[200:600],
            "etfs": ['512880.SH', '518880.SH', '515880.SH', '513050.SH', '512690.SH',
                     '512660.SH', '512400.SH', '512010.SH', '512000.SH', '510900.SH',
                     '510300.SH', '510500.SH', '510050.SH', '159992.SZ', '159985.SZ',
                     '159981.SZ', '159949.SZ', '159915.SZ'],
        }

        self.asset_map = {
            "index": "I",
            "stock": "E",
            "check": "E",
            "train": "E",
            "valid": "E",
            "etfs": "FD"
        }

    def analyze_results(self, step, trade_dir="long"):
        res_path = self.res_path
        raw_path = os.path.join(res_path, f'raw_{step}')
        if not os.path.exists(raw_path):
            return

        df_pairs, df_p = read_raw_results(raw_path, trade_dir)
        s_name = self.strategy.__name__

        df_pairs.to_excel(os.path.join(res_path, f"{s_name}_{step}_{trade_dir}_pairs.xlsx"), index=False)
        f = pd.ExcelWriter(os.path.join(res_path, f"{s_name}_{step}_{trade_dir}_performance.xlsx"))
        df_p.to_excel(f, sheet_name="评估", index=False)
        tp = PairsPerformance(df_pairs)
        for col in tp.agg_columns:
            df_ = tp.agg_statistics(col)
            df_.to_excel(f, sheet_name=f"{col}聚合", index=False)
        f.close()
        print(f"{s_name} - {step} - {trade_dir}: {tp.basic_info}")

    def update_step(self, step: str, ts_codes: list):
        """更新指定阶段的批量回测标的

        :param step: 阶段名称
        :param ts_codes: 标的列表
        :return:
        """
        self.stocks_map[step] += ts_codes

    def batch_backtest(self, step):
        """批量回测

        :param step: 择时策略研究阶段
            check   在给定的股票上观察策略交易的准确性，输出交易快照
            index   在股票指数上评估策略表现
            train   在训练集上评估策略表现
            valid   在验证集上评估策略表现
            stock   用全市场所有股票评估策略表现
        :return:
        """
        assert step in self.stocks_map.keys(), f"step 参数输入错误，可选值：{list(self.stocks_map.keys())}"

        init_n = self.init_n
        save_html = True if step == 'check' else False
        ts_codes = self.stocks_map[step]
        dc, sdt, edt = self.dc, self.sdt, self.edt
        res_path = self.res_path
        strategy = self.strategy
        raw_path = os.path.join(res_path, f"raw_{step}")
        os.makedirs(raw_path, exist_ok=True)
        asset = self.asset_map[step]

        for ts_code in ts_codes:
            tactic = strategy(ts_code)
            base_freq = tactic['base_freq']
            if save_html:
                html_path = os.path.join(res_path, f"raw_{step}/{ts_code}")
                os.makedirs(html_path, exist_ok=True)
            else:
                html_path = None

            try:
                file_res = os.path.join(res_path, f"raw_{step}/{ts_code}.xlsx")
                file_signals = os.path.join(res_path, f"raw_{step}/{ts_code}_signals.pkl")
                if os.path.exists(file_res) and os.path.exists(file_signals):
                    print(f"exits: {file_res}")
                    continue

                if "分钟" in base_freq:
                    bars = dc.pro_bar_minutes(ts_code, sdt, edt, freq=freq_cn2ts[base_freq],
                                              asset=asset, adj='hfq', raw_bar=True)
                else:
                    bars = dc.pro_bar(ts_code, sdt, edt, freq=freq_cn2ts[base_freq],
                                      asset=asset, adj='hfq', raw_bar=True)
                res = trader_fast_backtest(bars, init_n, strategy, html_path)

                # 保存信号结果
                dfs = pd.DataFrame(res['signals'])
                c_cols = [k for k, v in dfs.dtypes.to_dict().items() if v.name.startswith('object')]
                dfs[c_cols] = dfs[c_cols].astype('category')
                float_cols = [k for k, v in dfs.dtypes.to_dict().items() if v.name.startswith('float')]
                dfs[float_cols] = dfs[float_cols].astype('float32')
                dfs.to_pickle(file_signals, protocol=4)

                f = pd.ExcelWriter(file_res)
                if res.get('long_performance', None):
                    print(f"{strategy.__name__} long_performance: {res['long_performance']}")
                    pd.DataFrame(res['long_holds']).to_excel(f, sheet_name="long_holds", index=False)
                    pd.DataFrame(res['long_operates']).to_excel(f, sheet_name="long_operates", index=False)
                    pd.DataFrame(res['long_pairs']).to_excel(f, sheet_name="long_pairs", index=False)
                    pd.DataFrame([res['long_performance']]).to_excel(f, sheet_name="long_performance", index=False)

                if res.get('short_performance', None):
                    print(f"{strategy.__name__} short_performance: {res['short_performance']}")
                    pd.DataFrame(res['short_holds']).to_excel(f, sheet_name="short_holds", index=False)
                    pd.DataFrame(res['short_operates']).to_excel(f, sheet_name="short_operates", index=False)
                    pd.DataFrame(res['short_pairs']).to_excel(f, sheet_name="short_pairs", index=False)
                    pd.DataFrame([res['short_performance']]).to_excel(f, sheet_name="short_performance", index=False)

                f.close()
            except:
                traceback.print_exc()

        # self.analyze_results(step, 'long')
        # self.analyze_results(step, 'short')
        # print(f"results saved into {self.res_path}")

    def analyze_signals(self, step: str):
        """分析策略中信号的基础表现

        :param step:
        :return:
        """
        dc = self.dc
        raw_path = os.path.join(self.res_path, f"raw_{step}")
        file_dfs = os.path.join(self.res_path, f"{step}_dfs.pkl")
        signals_pat = fr"{raw_path}\*_signals.pkl"
        freq = freq_cn2ts[self.strategy()['base_freq']]

        # 由于python存在循环导入的问题，只能把两个导入放到这里
        from ..sensors.utils import read_cached_signals, SignalsPerformance

        if not os.path.exists(file_dfs):
            dfs = read_cached_signals(file_dfs, signals_pat)
            asset = "I" if step == 'index' else "E"
            results = []
            for symbol, dfg in tqdm(dfs.groupby('symbol'), desc='add nbar'):
                dfk = dc.pro_bar_minutes(symbol, sdt=dfg['dt'].min(), edt=dfg['dt'].max(),
                                         freq=freq, asset=asset, adj='hfq', raw_bar=False)
                dfk_cols = ['dt'] + [x for x in dfk.columns if x not in dfs.columns]
                dfk = dfk[dfk_cols]
                dfs_ = dfg.merge(dfk, on='dt', how='left')
                results.append(dfs_)

            dfs = pd.concat(results, ignore_index=True)
            c_cols = [k for k, v in dfs.dtypes.to_dict().items() if v.name.startswith('object')]
            dfs[c_cols] = dfs[c_cols].astype('category')
            float_cols = [k for k, v in dfs.dtypes.to_dict().items() if v.name.startswith('float')]
            dfs[float_cols] = dfs[float_cols].astype('float32')
            dfs.to_pickle(file_dfs, protocol=4)
        else:
            dfs = pd.read_pickle(file_dfs)

        results_path = os.path.join(raw_path, 'signals_performance')
        if os.path.exists(results_path):
            return

        os.makedirs(results_path, exist_ok=True)
        signal_cols = [x for x in dfs.columns if len(x.split("_")) == 3]
        for key in signal_cols:
            file_xlsx = os.path.join(results_path, f"{key.replace(':', '')}.xlsx")
            sp = SignalsPerformance(dfs, keys=[key], dc=dc)
            sp.report(file_xlsx)
            print(f"{key} performance saved into {file_xlsx}")
