# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/7/15 13:42
describe: 特征分析相关的传感器
"""
import os
import pandas as pd
from tqdm import tqdm
from loguru import logger
from czsc.utils.corr import cross_sectional_ic
from czsc.utils.stats import daily_performance
from czsc.utils.trade import update_nbars
from concurrent.futures import ProcessPoolExecutor, as_completed


class FeatureAnalyzeBase:
    """【基类】特征计算与分析，适用于时序量价类因子"""

    def __init__(self, symbols, read_bars, **kwargs) -> None:
        """初始化函数

        :param symbols: list，需要获取特征的品种列表
        :param read_bars: function，获取品种K线数据的函数
        :param kwargs: dict，其他参数

            - freq: str，K线周期，可选值：日线、60分钟、30分钟、15分钟、5分钟、1分钟
            - sdt: str，开始日期
            - edt: str，结束日期
            - fq: str，复权方式，可选值：前复权、后复权，默认为后复权
            - max_workers: int，多进程获取特征的最大进程数
        """
        self.symbols = symbols
        self.read_bars = read_bars
        self.kwargs = kwargs
        self.dfs = self.get_features()
        self.report()

    @property
    def new_features(self):
        """list，新增的特征列表"""
        raise NotImplementedError

    def add_features(self, df):
        """向df中添加特征

        df 包含以下列：

        - dt: 日期
        - open: 开盘价
        - close: 收盘价
        - high: 最高价
        - low: 最低价
        - vol: 成交量
        - amount: 成交额
        """
        raise NotImplementedError

    def _one_symbol_features(self, symbol):
        """获取单个品种的特征"""
        freq = self.kwargs.get('freq', '日线')
        sdt = self.kwargs.get('sdt', '2010-01-01')
        edt = self.kwargs.get('edt', '2023-01-01')
        fq = self.kwargs.get('fq', "后复权")
        nbars_seq = self.kwargs.get('nbars_seq', (1, 2, 5))
        try:
            bars = self.read_bars(symbol=symbol, freq=freq, sdt=sdt, edt=edt, fq=fq)
            _df = pd.DataFrame(bars)
            update_nbars(_df, numbers=nbars_seq, price_col='open', move=1)
            _df = self.add_features(_df)
            return _df
        except Exception as e:
            logger.error(f"{symbol} error: {e}")
            return pd.DataFrame()

    def get_features(self) -> pd.DataFrame:
        """
        此方法检索self.symbols中每个符号的K线数据，
        使用add_features方法向数据添加特征

        :return: 包含所有K线和特征的DataFrame
        """
        max_workers = self.kwargs.get('max_workers', 1)
        if max_workers == 1:
            res = []
            for symbol in tqdm(self.symbols, desc="获取特征"):
                df = self._one_symbol_features(symbol)
                res.append(df)
        else:
            res = []
            with ProcessPoolExecutor(max_workers) as executor:
                tasks = [executor.submit(self._one_symbol_features, symbol) for symbol in self.symbols]
                for future in tqdm(as_completed(tasks), desc="获取特征", total=len(tasks)):
                    df = future.result()
                    res.append(df)

        return pd.concat(res, ignore_index=True)

    def layering(self, feature, min_q, max_q):
        """分层回测"""
        df = self.dfs.copy()
        # q 是截面排序，按照特征值从大到小排序，q的取值范围是[0, 1]
        df['q'] = df.groupby('dt')[feature].transform(lambda x: x.rank(pct=True))
        df1 = df[(df['q'] >= min_q) & (df['q'] <= max_q)]
        dfm = df1.groupby('dt').agg({'n1b': 'mean'}).fillna(0)
        logger.info(f"分层累计收益 {feature} {min_q}-{max_q}：{dfm['n1b'].sum():.4f}; {daily_performance((dfm['n1b'] / 10000).to_list())}")
        return dfm

    def report(self):
        """打印特征分析报告"""
        results_path = self.kwargs.get('results_path', None)
        if results_path:
            os.makedirs(results_path, exist_ok=True)
            dfs = self.dfs.copy()
            dfs['freq'] = dfs['freq'].apply(lambda x: x.value)
            dfs.drop(['cache'], axis=1, inplace=True)
            logger.add(os.path.join(results_path, "feature.log"), rotation="1 week", encoding='utf-8')
            dfs.to_feather(os.path.join(results_path, "features.feather"))

        logger.info(f"新增特征：{self.new_features}")
        corr_method = self.kwargs.get('corr_method', 'pearson')
        logger.info(f"相关系数计算方法：{corr_method}")

        for feature in self.new_features:
            logger.info(f"特征 {feature} 的取值范围：{self.dfs[feature].describe().round(4).to_dict()}")
            df1, res1 = cross_sectional_ic(self.dfs, x_col=feature, y_col='n1b', method=corr_method, dt_col='dt')
            logger.info(f"特征 {feature} 与未来1日收益的相关系数：{res1}")
            _ = self.layering(feature, 0.95, 1)
            _ = self.layering(feature, 0.9, 1)
            _ = self.layering(feature, 0, 0.1)
            _ = self.layering(feature, 0, 0.05)

            df1['年月'] = df1['dt'].apply(lambda x: x.strftime("%Y年%m月"))
            dfm = df1.groupby('年月').agg({'ic': 'mean'})
            logger.info(f"特征 {feature} 与未来1日收益的相关系数月度描述：{dfm.describe().round(4).to_dict()}")
            logger.info(f"特征 {feature} 与未来1日收益的相关系数月度胜率：{len(dfm[dfm['ic'] > 0])/len(dfm):.4f}")


class FixedNumberSelector:
    """选择固定数量（等权）的交易品种

    可优化项：
    1. 传入 res_path, 将分析过程和分析结果保存下来
    2. 支持传入大盘择时信号，例如：大盘择时信号为空头时，多头只平不开
    """

    def __init__(self, dfs, k, d, **kwargs):
        """

        :param dfs: pd.DataFrame，所有交易品种的特征打分数据，必须包含以下列：dt, open, close, high, low, vol, amount, score；数据样例：

            ===================  =========  =======  =======  =======  =======  ========  =========  ========  =============
            dt                   symbol        open    close     high      low       vol     amount       n1b          score
            ===================  =========  =======  =======  =======  =======  ========  =========  ========  =============
            2017-01-03 00:00:00  000001.SZ  954.345  959.583  961.678  952.25   45984049  420595176   21.8583  nan
            2017-01-04 00:00:00  000001.SZ  958.536  959.583  961.678  957.488  44932953  411503444    0         0
            2017-01-05 00:00:00  000001.SZ  960.631  960.631  961.678  958.536  34437291  315769693  -43.6213    3.17018e-11
            2017-01-06 00:00:00  000001.SZ  960.631  956.441  960.631  954.345  35815420  327176433   21.9062   -1.21795e-10
            2017-01-09 00:00:00  000001.SZ  956.441  958.536  960.631  954.345  36108157  329994604  -10.9292    6.06684e-11
            2017-01-10 00:00:00  000001.SZ  958.536  958.536  959.583  957.488  24105395  220575131  -10.9411    0
            2017-01-11 00:00:00  000001.SZ  957.488  957.488  960.631  956.441  30343089  277553207   10.9531   -3.60186e-11
            2017-01-12 00:00:00  000001.SZ  956.441  958.536  960.631  956.441  42800677  391869402   10.9411    2.5563e-11
            2017-01-13 00:00:00  000001.SZ  957.488  959.583  962.726  955.393  43430137  397601906  -32.7865    2.51649e-11
            2017-01-16 00:00:00  000001.SZ  958.536  957.488  959.583  950.155  68316586  623025820   21.9292   -3.19607e-11
            ===================  =========  =======  =======  =======  =======  ========  =========  ========  =============

        :param k: int，每期固定选择的数量
        :param d: int，每期允许变动的数量
        """
        logger.info(f"选择固定数量的交易品种，k={k}，d={d}, dfs.shape={dfs.shape}, kwargs={kwargs}")
        self.dfs = dfs   # 所有交易品种的特征打分数据，必须包含以下列：dt, open, close, high, low, vol, amount, score
        self.k = k       # 每期固定选择的数量
        self.d = d       # 每期允许变动的数量
        self.kwargs = kwargs
        self.is_stocks = kwargs.get('is_stocks', False)  # 是否是A股，如果是A股，需要考虑涨跌停的情况
        self.__preprocess()

        self.operate_fee = kwargs.get('operate_fee', 15)  # 单边手续费+交易滑点，单位：BP
        self.holds = {}  # 每期持有的品种
        self.operates = {}  # 每期操作的品种
        for dt in self.dts:
            self.__deal_one_time(dt)

    def __preprocess(self):
        assert 'dt' in self.dfs.columns, "必须包含dt列"
        assert 'n1b' in self.dfs.columns, "必须包含n1b列"
        assert 'symbol' in self.dfs.columns, "必须包含symbol列"
        assert 'score' in self.dfs.columns, "必须包含score列, 这是选择交易品种的依据"

        self.dfs['dt'] = pd.to_datetime(self.dfs['dt']).dt.strftime("%Y-%m-%d %H:%M:%S")
        dts = sorted(self.dfs['dt'].unique())
        last_dt_map = {dt: dts[i-1] for i, dt in enumerate(dts)}
        self.dts, self.last_dt_map = dts, last_dt_map
        self.score_map = {dt: dfg[['symbol', 'dt', 'open', 'close', 'high', 'low', 'score', 'n1b']].copy() for dt, dfg in self.dfs.groupby('dt')}

    def __deal_one_time(self, dt):
        """单次调整记录"""
        k, d, is_stocks = self.k, self.d, self.is_stocks

        score = self.score_map[dt]
        if is_stocks:
            zt_symbols = [x['symbol'] for _, x in score.iterrows() if x['close'] == x['high'] >= x['open']]
            dt_symbols = [x['symbol'] for _, x in score.iterrows() if x['close'] == x['low'] <= x['open']]
            score_a = score[~score.symbol.isin(zt_symbols + dt_symbols)].copy()
            logger.info(f"A股今日{dt}涨停{len(zt_symbols)}个品种，跌停{len(dt_symbols)}个品种，已跳过")
        else:
            score_a = score.copy()

        if not self.holds:
            logger.info(f"当前持仓为空，选择前{k}个品种")
            assert not self.operates, "当holds是空的时候，操作记录必须为空"

            _df = score_a.sort_values(by='score', ascending=False).head(k)
            _df['edge'] = _df['n1b'] - self.operate_fee
            self.holds[dt] = _df

            _df_operates = [{'symbol': row['symbol'], 'dt': dt, 'action': 'buy', 'price': row['close']} for _, row in _df.iterrows()]
            self.operates[dt] = pd.DataFrame(_df_operates)
            return

        # 有持仓的情况
        score = self.score_map[dt]
        last_dt = self.last_dt_map[dt]
        last_holds = self.holds[last_dt].copy()
        last_symbols = last_holds['symbol'].tolist()
        skip_symbols = [x for x in last_symbols if x not in score['symbol'].tolist()]
        if skip_symbols:
            logger.warning(f"【数据缺陷提示】上一期持仓中，有{len(skip_symbols)}个品种，本期{dt}不在交易品种中，已跳过: {skip_symbols}")

        topk_symbols = score_a.sort_values(by='score', ascending=False).head(k)['symbol'].tolist()
        sell_symbols = score_a[score_a.symbol.isin(last_symbols)].sort_values(by='score', ascending=False).tail(d)['symbol'].tolist()
        sell_symbols = [x for x in sell_symbols if x not in topk_symbols] + skip_symbols
        keep_symbols = [x for x in last_symbols if x not in sell_symbols]
        if len(keep_symbols) != k - len(sell_symbols):
            logger.warning(f"保持品种数量不对，当前只有{len(keep_symbols)}个品种")

        buy_symbols = score_a[~score_a.symbol.isin(keep_symbols)].sort_values(by='score', ascending=False).head(len(sell_symbols))['symbol'].tolist()
        assert len(buy_symbols) == len(sell_symbols), "买入品种数量必须等于卖出品种数量"
        assert len(keep_symbols + buy_symbols) == k, "保持品种数量+买入品种数量必须等于k"
        _df = score[score.symbol.isin(keep_symbols + buy_symbols)].sort_values(by='score', ascending=False)

        if len(_df) != k:
            logger.warning(f"选择的品种数量不等于{k}，当前只有{len(_df)}个品种")

        _df['edge'] = _df.apply(lambda row: row['n1b'] - self.operate_fee if row['symbol'] in buy_symbols else row['n1b'], axis=1)
        self.holds[dt] = _df

        # 平仓扣费，在上一期的持仓中，卖出的品种，需要扣除手续费
        last_holds['edge'] = last_holds.apply(lambda row: row['edge'] - self.operate_fee if row['symbol'] in sell_symbols else row['edge'], axis=1)
        self.holds[last_dt] = last_holds

        _sell_operates = [{'symbol': row['symbol'], 'dt': dt, 'action': 'sell', 'price': row['close']}
                          for _, row in score[score.symbol.isin(sell_symbols)].iterrows()]
        _buy_operates = [{'symbol': row['symbol'], 'dt': dt, 'action': 'buy', 'price': row['close']}
                         for _, row in score[score.symbol.isin(buy_symbols)].iterrows()]
        _df_operates = pd.DataFrame(_sell_operates + _buy_operates)
        self.operates[dt] = _df_operates
