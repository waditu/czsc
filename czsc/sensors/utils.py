# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/11/17 18:50
"""
import os
import glob
import warnings
import traceback
import pandas as pd
import numpy as np
from tqdm import tqdm
from deprecated import deprecated
from datetime import datetime, timedelta
from typing import Callable, List, AnyStr
from sklearn.preprocessing import KBinsDiscretizer

from .. import envs
from ..traders.advanced import CzscAdvancedTrader, BarGenerator
from ..data import TsDataCache, freq_cn2ts
from ..objects import RawBar, Signal
from ..utils.cache import home_path


def discretizer(df: pd.DataFrame, col: str, n_bins=20, encode='ordinal', strategy='quantile'):
    """使用 KBinsDiscretizer 对连续变量在时间截面上进行离散化

    :param df: 数据对象
    :param col: 连续变量列名
    :param n_bins: 参见 KBinsDiscretizer 文档
        https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.KBinsDiscretizer.html
    :param encode: 参见 KBinsDiscretizer 文档
    :param strategy: 参见 KBinsDiscretizer 文档
    :return:
    """
    assert col in df.columns, f'{col} not in {df.columns}'
    assert 'dt' in df.columns

    new_col = f'{col}_bins{n_bins}'
    results = []
    for dt, dfg in tqdm(df.groupby('dt'), desc=f"{col}_bins{n_bins}"):
        kb = KBinsDiscretizer(n_bins=n_bins, encode=encode, strategy=strategy)
        # 加1，使分组从1开始
        dfg[new_col] = kb.fit_transform(dfg[col].values.reshape(-1, 1)).ravel() + 1
        results.append(dfg)
    df = pd.concat(results, ignore_index=True)
    return df


def get_index_beta(dc: TsDataCache, sdt: str, edt: str, freq='D', file_xlsx=None, indices=None):
    """获取基准指数的Beta

    :param dc: 数据缓存对象
    :param sdt: 开始日期
    :param edt: 结束日期
    :param freq: K线周期，D 日线，W 周线，M 月线
    :param file_xlsx: 结果保存文件
    :param indices: 定义指数列表
    :return:
    """
    if not indices:
        indices = ['000001.SH', '000016.SH', '000905.SH', '000300.SH', '399001.SZ', '399006.SZ']

    beta = {}
    p = []
    for ts_code in indices:
        df = dc.pro_bar(ts_code=ts_code, start_date=sdt, end_date=edt, freq=freq, asset="I", raw_bar=False)
        beta[ts_code] = df
        df = df.fillna(0)
        start_i, end_i, mdd = max_draw_down(df['n1b'].to_list())
        start_dt = df.iloc[start_i]['trade_date']
        end_dt = df.iloc[end_i]['trade_date']
        row = {
            '标的': ts_code,
            "开始日期": sdt,
            "结束日期": edt,
            "最大回撤": mdd,
            "回撤开始": start_dt,
            "回撤结束": end_dt,
            "交易次数": len(df),
            "交易胜率": round(len(df[df.n1b > 0]) / len(df), 4),
            "累计收益": round(df.n1b.sum(), 4),
        }
        cols = [x for x in df.columns if x[0] == 'n' and x[-1] == 'b']
        row.update({x: round(df[x].mean(), 4) for x in cols})
        p.append(row)

    dfp = pd.DataFrame(p)
    if file_xlsx:
        f = pd.ExcelWriter(file_xlsx)
        dfp.to_excel(f, index=False, sheet_name="指数表现")
        for name, df_ in beta.items():
            df_.to_excel(f, index=False, sheet_name=name)
        f.close()
    else:
        beta['dfp'] = dfp
        return beta


def generate_signals(bars: List[RawBar],
                     sdt: AnyStr,
                     strategy: Callable,
                     ):
    """获取历史信号

    :param bars: 日线
    :param sdt: 信号计算开始时间
    :param strategy: 单级别信号计算函数
    :return: signals
    """
    sdt = pd.to_datetime(sdt)
    bars_left = [x for x in bars if x.dt < sdt]
    if len(bars_left) <= 500:
        bars_left = bars[:500]
        bars_right = bars[500:]
    else:
        bars_right = [x for x in bars if x.dt >= sdt]

    if len(bars_right) == 0:
        warnings.warn("右侧K线为空，无法进行信号生成", category=RuntimeWarning)
        return []

    tactic = strategy(bars[0].symbol)
    base_freq = tactic['base_freq']
    freqs = tactic['freqs']
    bg = BarGenerator(base_freq=base_freq, freqs=freqs, max_count=5000)
    for bar in bars_left:
        bg.update(bar)

    signals = []
    ct = CzscAdvancedTrader(bg, strategy)
    for bar in tqdm(bars_right, desc=f'generate signals of {bg.symbol}'):
        ct.update(bar)
        signals.append(dict(ct.s))
    return signals


def check_signals_acc(bars: List[RawBar],
                      signals: List[Signal] = None,
                      strategy: Callable = None,
                      delta_days: int = 5) -> None:
    """人工验证形态信号识别的准确性的辅助工具：

    输入基础周期K线和想要验证的信号，输出信号识别结果的快照

    :param bars: 原始K线
    :param signals: 需要验证的信号列表
    :param strategy: 含有信号函数的伪交易策略
    :param delta_days: 两次相同信号之间的间隔天数
    :return:
    """
    verbose = envs.get_verbose()
    base_freq = bars[-1].freq.value
    assert bars[2].dt > bars[1].dt > bars[0].dt and bars[2].id > bars[1].id, "bars 中的K线元素必须按时间升序"
    if len(bars) < 600:
        return

    sorted_freqs = ['1分钟', '5分钟', '15分钟', '30分钟', '60分钟', '日线', '周线', '月线', '季线', '年线']
    freqs = sorted_freqs[sorted_freqs.index(base_freq) + 1:]

    if not signals:
        signals_ = generate_signals(bars, bars[500].dt.strftime("%Y%m%d"), strategy)
        df = pd.DataFrame(signals_)
        s_cols = [x for x in df.columns if len(x.split("_")) == 3]
        signals = []
        for col in s_cols:
            signals.extend([Signal(f"{col}_{v}") for v in df[col].unique() if "其他" not in v])

    if verbose:
        print(f"signals: {signals}")

    bars_left = bars[:500]
    bars_right = bars[500:]
    bg = BarGenerator(base_freq=base_freq, freqs=freqs, max_count=5000)
    for bar in bars_left:
        bg.update(bar)

    ct = CzscAdvancedTrader(bg, strategy)
    last_dt = {signal.key: ct.end_dt for signal in signals}

    for bar in tqdm(bars_right, desc=f'generate snapshots of {bg.symbol}'):
        ct.update(bar)

        for signal in signals:
            html_path = os.path.join(home_path, signal.key)
            os.makedirs(html_path, exist_ok=True)
            if bar.dt - last_dt[signal.key] > timedelta(days=delta_days) and signal.is_match(ct.s):
                file_html = f"{bar.symbol}_{signal.key}_{ct.s[signal.key]}_{bar.dt.strftime('%Y%m%d_%H%M')}.html"
                file_html = os.path.join(html_path, file_html)
                print(file_html)
                ct.take_snapshot(file_html)
                last_dt[signal.key] = bar.dt


def max_draw_down(n1b: List):
    """最大回撤

    参考：https://blog.csdn.net/weixin_38997425/article/details/82915386

    :param n1b: 逐个结算周期的收益列表，单位：BP，换算关系是 10000BP = 100%
        如，n1b = [100.1, -90.5, 212.6]，表示第一个结算周期收益为100.1BP，也就是1.001%，以此类推。
    :return: 最大回撤起止位置和最大回撤
    """
    curve = np.cumsum(n1b)
    curve += 10000
    # 获取结束位置
    i = np.argmax((np.maximum.accumulate(curve) - curve) / np.maximum.accumulate(curve))
    if i == 0:
        return 0, 0, 0

    # 获取开始位置
    j = np.argmax(curve[:i])
    mdd = int((curve[j] - curve[i]) / curve[j] * 10000) / 10000
    return j, i, mdd


def turn_over_rate(df_holds: pd.DataFrame) -> [pd.DataFrame, float]:
    """计算持仓明细对应的组合换手率

    :param df_holds: 每个交易日的持仓明细，数据样例如下
                证券代码    成分日期    持仓权重
            0  000576.SZ  2020-01-02  0.0099
            1  000639.SZ  2020-01-02  0.0099
            2  000803.SZ  2020-01-02  0.0099
            3  000811.SZ  2020-01-02  0.0099
            4  000829.SZ  2020-01-02  0.0099
    :return: 组合换手率
    """
    trade_dates = sorted(df_holds['成分日期'].unique().tolist())
    daily_holds = {date: dfg for date, dfg in df_holds.groupby('成分日期')}

    turns = []
    for date_i, date in tqdm(enumerate(trade_dates), desc='turn_over_rate'):
        if date_i == 0:
            turns.append({'date': date, 'change': 1})
            continue

        dfg = daily_holds[date]
        dfg_last = daily_holds[trade_dates[date_i-1]]
        com_symbols = list(set(dfg['证券代码'].to_list()).intersection(dfg_last['证券代码'].to_list()))

        dfg_pos = {row['证券代码']: row['持仓权重'] for _, row in dfg.iterrows()}
        dfg_last_pos = {row['证券代码']: row['持仓权重'] for _, row in dfg_last.iterrows()}

        change = 0
        change += sum([abs(dfg_pos[symbol] - dfg_last_pos[symbol]) for symbol in com_symbols])
        change += sum([v for symbol, v in dfg_pos.items() if symbol not in com_symbols])
        change += sum([v for symbol, v in dfg_last_pos.items() if symbol not in com_symbols])
        turns.append({'date': date, 'change': change})

    df_turns = pd.DataFrame(turns)
    return df_turns, round(df_turns.change.sum() / 2, 4)


def compound_returns(n1b: List):
    """复利收益计算

    :param n1b: 逐个结算周期的收益列表，单位：BP，换算关系是 10000BP = 100%
        如，n1b = [100.1, -90.5, 212.6]，表示第一个结算周期收益为100.1BP，也就是1.001%，以此类推。
    :return: 累计复利收益，逐个结算周期的复利收益
    """
    v = 10000
    detail = []
    for n in n1b:
        v = v * (1 + n / 10000)
        detail.append(v-10000)
    return v-10000, detail


def read_cached_signals(file_output: str, path_pat=None, sdt=None, edt=None, keys=None) -> pd.DataFrame:
    """读取缓存信号

    :param file_output: 读取后保存结果
    :param path_pat: 缓存信号文件路径模板，用于glob获取文件列表
    :param keys: 需要读取的信号名称列表
    :param sdt: 开始时间
    :param edt: 结束时间
    :return: 信号
    """
    verbose = envs.get_verbose()

    if os.path.exists(file_output):
        sf = pd.read_pickle(file_output)
        if verbose:
            print(f"read_cached_signals: read from {file_output}, 数据占用内存大小"
                  f"：{int(sf.memory_usage(deep=True).sum() / (1024 * 1024))} MB")
        return sf

    files = glob.glob(path_pat, recursive=False)
    results = []
    for file in tqdm(files, desc="read_cached_signals"):
        df = pd.read_pickle(file)
        if not df.empty:
            if keys:
                base_cols = [x for x in df.columns if len(x.split("_")) != 3]
                df = df[base_cols + keys]
            if sdt:
                df = df[df['dt'] >= pd.to_datetime(sdt)]
            if edt:
                df = df[df['dt'] <= pd.to_datetime(edt)]
            results.append(df)
        else:
            print(f"read_cached_signals: {file} is empty")

    sf = pd.concat(results, ignore_index=True)
    if verbose:
        print(f"read_cached_signals: 原始数据占用内存大小：{int(sf.memory_usage(deep=True).sum() / (1024 * 1024))} MB")

    c_cols = [k for k, v in sf.dtypes.to_dict().items() if v.name.startswith('object')]
    sf[c_cols] = sf[c_cols].astype('category')

    float_cols = [k for k, v in sf.dtypes.to_dict().items() if v.name.startswith('float')]
    sf[float_cols] = sf[float_cols].astype('float32')
    if verbose:
        print(f"read_cached_signals: 转类型后占用内存大小：{int(sf.memory_usage(deep=True).sum() / (1024 * 1024))} MB")

    sf.to_pickle(file_output, protocol=4)
    return sf


def generate_symbol_signals(dc: TsDataCache,
                            ts_code: str,
                            asset: str,
                            sdt: str,
                            edt: str,
                            strategy: Callable,
                            adj: str = 'hfq',
                            ):
    """使用 Tushare 数据生产某个标的的信号

    :param dc:
    :param ts_code:
    :param asset:
    :param sdt:
    :param edt:
    :param strategy:
    :param adj: 复权方式
    :return:
    """
    tactic = strategy(ts_code)
    base_freq = tactic['base_freq']

    sdt_ = pd.to_datetime(sdt) - timedelta(days=3000)
    if "分钟" in base_freq:
        bars = dc.pro_bar_minutes(ts_code, sdt_, edt, freq=freq_cn2ts[base_freq],
                                  asset=asset, adj=adj, raw_bar=True)
        n_bars = dc.pro_bar_minutes(ts_code, sdt_, edt, freq=freq_cn2ts[base_freq],
                                    asset=asset, adj=adj, raw_bar=False)
        n_bars['dt'] = pd.to_datetime(n_bars['trade_time'])

    else:
        bars = dc.pro_bar(ts_code, sdt_, edt, freq=freq_cn2ts[base_freq],
                          asset=asset, adj=adj, raw_bar=True)
        n_bars = dc.pro_bar(ts_code, sdt_, edt, freq=freq_cn2ts[base_freq],
                            asset=asset, adj=adj, raw_bar=False)
        n_bars['dt'] = pd.to_datetime(n_bars['trade_date'])

    dt_fmt = "%Y-%m-%d %H:%M:%S"
    nb_dicts = {row['dt'].strftime(dt_fmt): row for row in n_bars.to_dict("records")}
    signals = generate_signals(bars, sdt, strategy)

    for s in signals:
        s.update(nb_dicts[s['dt'].strftime(dt_fmt)])

    df = pd.DataFrame(signals)

    c_cols = [k for k, v in df.dtypes.to_dict().items() if v.name.startswith('object')]
    df[c_cols] = df[c_cols].astype('category')

    float_cols = [k for k, v in df.dtypes.to_dict().items() if v.name.startswith('float')]
    df[float_cols] = df[float_cols].astype('float32')
    return df


def generate_stocks_signals(dc: TsDataCache,
                            signals_path: str,
                            sdt: str,
                            edt: str,
                            strategy: Callable,
                            adj: str = 'hfq',
                            ):
    """使用 Tushare 数据获取股票市场全部股票的信号

    :param dc:
    :param signals_path:
    :param sdt:
    :param edt:
    :param strategy:
    :param adj:
    :return:
    """
    os.makedirs(signals_path, exist_ok=True)
    stocks = dc.stock_basic()

    for row in tqdm(stocks.to_dict('records'), desc="generate_stocks_signals"):
        ts_code = row['ts_code']
        name = row['name']
        try:
            file_signals = os.path.join(signals_path, f"{ts_code}_signals.pkl")
            if os.path.exists(file_signals):
                print(f"file exists: {file_signals}")
                continue
            df = generate_symbol_signals(dc, ts_code, "E", sdt, edt, strategy, adj)
            df.to_pickle(file_signals)
        except:
            print(f"generate_stocks_signals error: {ts_code}, {name}")
            traceback.print_exc()


class SignalsPerformance:
    """信号表现分析"""

    def __init__(self, dfs: pd.DataFrame, keys: List[AnyStr], dc: TsDataCache = None, base_freq="日线"):
        """

        :param dfs: 信号表
        :param keys: 信号列，支持一个或多个信号列组合分析
        :param dc: Tushare 数据缓存对象
        :param base_freq: 信号对应的K线基础周期
        """
        if 'year' not in dfs.columns:
            dfs['year'] = dfs['dt'].apply(lambda x: x.year)

        self.dfs = dfs
        self.keys = keys
        self.dc = dc
        self.base_freq = base_freq
        self.b_cols = [x for x in dfs.columns if x[0] == 'b' and x[-1] == 'b']
        self.n_cols = [x for x in dfs.columns if x[0] == 'n' and x[-1] == 'b']

    def __return_performance(self, dfs: pd.DataFrame, mode: str = '1b') -> pd.DataFrame:
        """分析信号组合的分类能力，也就是信号出现前后的收益情况

        :param dfs: 信号数据表，
        :param mode: 分析模式，
            0b 截面向前看
            0n 截面向后看
            1b 时序向前看
            1n 时序向后看
        :return:
        """
        mode = mode.lower()
        assert mode in ['0b', '0n', '1b', '1n']
        keys = self.keys
        len_dfs = len(dfs)
        cols = self.b_cols if mode.endswith('b') else self.n_cols

        sdt = dfs['dt'].min().strftime("%Y%m%d")
        edt = dfs['dt'].max().strftime("%Y%m%d")

        def __static(_df, _name):
            _res = {"name": _name, "sdt": sdt, "edt": edt,
                    "count": len(_df), "cover": round(len(_df) / len_dfs, 4)}
            if mode.startswith('0'):
                _r = _df.groupby('dt')[cols].mean().mean().to_dict()
            else:
                _r = _df[cols].mean().to_dict()
            _res.update(_r)
            return _res

        results = [__static(dfs, "基准")]

        for values, dfg in dfs.groupby(keys):
            if isinstance(values, str):
                values = [values]
            assert len(keys) == len(values)

            name = "#".join([f"{key1}_{name1}" for key1, name1 in zip(keys, values)])
            results.append(__static(dfg, name))

        dfr = pd.DataFrame(results)
        dfr[cols] = dfr[cols].round(2)
        return dfr

    def analyze_return(self, mode='0b') -> pd.DataFrame:
        """分析信号出现前后的收益情况

        :param mode: 分析模式，
            0b 截面向前看
            0n 截面向后看
            1b 时序向前看
            1n 时序向后看
        :return:
        """
        dfr = self.__return_performance(self.dfs, mode)
        results = [dfr]
        for year, df_ in self.dfs.groupby('year'):
            dfr_ = self.__return_performance(df_, mode)
            results.append(dfr_)
        dfr = pd.concat(results, ignore_index=True)
        return dfr

    def __corr_index(self,  dfs: pd.DataFrame, index: str):
        """分析信号每天出现的次数与指数的相关性"""
        dc = self.dc
        base_freq = self.base_freq
        keys = self.keys
        n_cols = self.n_cols
        freq = freq_cn2ts[base_freq]
        sdt = dfs['dt'].min().strftime("%Y%m%d")
        edt = dfs['dt'].max().strftime("%Y%m%d")
        adj = 'hfq'
        asset = "I"

        if "分钟" in base_freq:
            dfi = dc.pro_bar_minutes(index, sdt, edt, freq, asset, adj, raw_bar=False)
            dfi['dt'] = pd.to_datetime(dfi['trade_time'])
        else:
            dfi = dc.pro_bar(index, sdt, edt, freq, asset, adj, raw_bar=False)
            dfi['dt'] = pd.to_datetime(dfi['trade_date'])

        results = []
        for values, dfg in dfs.groupby(keys):
            if isinstance(values, str):
                values = [values]
            assert len(keys) == len(values)
            name = "#".join([f"{key1}_{name1}" for key1, name1 in zip(keys, values)])
            c = dfg.groupby("dt")['symbol'].count()
            c_col = f'{name}_count'
            dfc = pd.DataFrame({'dt': c.index, c_col: c.values})
            df_ = dfi.merge(dfc, on=['dt'], how='left')
            df_[c_col] = df_[c_col].fillna(0)

            res = {"name": name, 'sdt': sdt, 'edt': edt, 'index': index}
            corr_ = df_[[c_col] + n_cols].corr(method='spearman').iloc[0][n_cols].round(4).to_dict()
            res.update(corr_)
            results.append(res)
        df_corr = pd.DataFrame(results)
        return df_corr

    def analyze_corr_index(self, index: str) -> pd.DataFrame:
        """分析信号出现前后的收益情况

        :param index: Tushare 指数代码，如 000905.SH 表示中证500
        :return:
        """
        dfr = self.__corr_index(self.dfs, index)
        results = [dfr]
        for year, df_ in self.dfs.groupby('year'):
            dfr_ = self.__corr_index(df_, index)
            results.append(dfr_)
        dfr = pd.concat(results, ignore_index=True)
        return dfr

    def __ar_counts(self,  dfs: pd.DataFrame):
        """分析信号每天出现的次数与自身收益的相关性"""
        keys = self.keys
        n_cols = self.n_cols
        sdt = dfs['dt'].min().strftime("%Y%m%d")
        edt = dfs['dt'].max().strftime("%Y%m%d")

        results = []
        for values, dfg in dfs.groupby(keys):
            if isinstance(values, str):
                values = [values]
            assert len(keys) == len(values)
            name = "#".join([f"{key1}_{name1}" for key1, name1 in zip(keys, values)])
            c = dfg.groupby("dt")['symbol'].count()
            n_bars = dfg.groupby("dt")[n_cols].mean()
            n_bars['count'] = c
            res_ = {"name": name, 'sdt': sdt, 'edt': edt}
            corr_ = n_bars[['count'] + n_cols].corr(method='spearman').iloc[0][n_cols].round(4).to_dict()
            res_.update(corr_)
            results.append(res_)
        dfr = pd.DataFrame(results)
        return dfr

    def analyze_ar_counts(self) -> pd.DataFrame:
        """分析信号每天出现的次数与自身收益的相关性"""
        dfr = self.__ar_counts(self.dfs)
        results = [dfr]
        for year, df_ in self.dfs.groupby('year'):
            dfr_ = self.__ar_counts(df_)
            results.append(dfr_)
        dfr = pd.concat(results, ignore_index=True)
        return dfr

    def __b_bar(self,  dfs: pd.DataFrame, b_col='b21b'):
        """分析信号出现前的收益与出现后收益的相关性"""
        keys = self.keys
        n_cols = self.n_cols
        sdt = dfs['dt'].min().strftime("%Y%m%d")
        edt = dfs['dt'].max().strftime("%Y%m%d")

        results = []
        for values, dfg in dfs.groupby(keys):
            if isinstance(values, str):
                values = [values]
            assert len(keys) == len(values)
            name = "#".join([f"{key1}_{name1}" for key1, name1 in zip(keys, values)])
            n_bars = dfg.groupby("dt")[[b_col] + n_cols].mean()
            res_ = {"name": name, 'sdt': sdt, 'edt': edt, 'b_col': b_col}
            corr_ = n_bars[[b_col] + n_cols].corr(method='spearman').iloc[0][n_cols].round(4).to_dict()
            res_.update(corr_)
            results.append(res_)
        dfr = pd.DataFrame(results)
        return dfr

    def analyze_b_bar(self, b_col='b21b') -> pd.DataFrame:
        """分析信号出现前的收益与出现后收益的相关性"""
        dfr = self.__b_bar(self.dfs, b_col)
        results = [dfr]
        for year, df_ in self.dfs.groupby('year'):
            dfr_ = self.__b_bar(df_, b_col)
            results.append(dfr_)
        dfr = pd.concat(results, ignore_index=True)
        return dfr

    def report(self, file_xlsx=None):
        res = {
            '向前看截面': self.analyze_return('0b'),
            '向后看截面': self.analyze_return('0n'),
            '向前看时序': self.analyze_return('1b'),
            '向后看时序': self.analyze_return('1n'),

            '信号数量与自身收益相关性': self.analyze_ar_counts(),
        }

        if self.dc:
            res.update({
                '信号数量与上证50相关性': self.analyze_corr_index('000016.SH'),
                '信号数量与中证500相关性': self.analyze_corr_index('000905.SH'),
                '信号数量与沪深300相关性': self.analyze_corr_index('000300.SH'),
            })
        if file_xlsx:
            writer = pd.ExcelWriter(file_xlsx)
            for sn, df_ in res.items():
                df_.to_excel(writer, sheet_name=sn, index=False)
            writer.close()
        return res
