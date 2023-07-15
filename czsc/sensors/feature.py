# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/7/15 13:42
describe: 特征分析相关的传感器
"""
import pandas as pd
from tqdm import tqdm
from loguru import logger
from czsc.utils.corr import cross_sectional_ic
from czsc.utils.stats import daily_performance
from czsc.utils.trade import update_nbars
from concurrent.futures import ProcessPoolExecutor, as_completed


class FeatureAnalyzeBase:
    """【基类】特征计算与分析"""

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
        logger.info(f"新增特征：{self.new_features}")
        corr_method = self.kwargs.get('corr_method', 'pearson')
        logger.info(f"相关系数计算方法：{corr_method}")

        for feature in self.new_features:
            logger.info(f"特征 {feature} 的取值范围：{self.dfs[feature].describe().round(4).to_dict()}")
            df1, res1 = cross_sectional_ic(self.dfs,  x_col=feature, y_col='n1b', method=corr_method, dt_col='dt')
            logger.info(f"特征 {feature} 与未来1日收益的相关系数：{res1}")
            _ = self.layering(feature, 0.95, 1)
            _ = self.layering(feature, 0.9, 1)
            _ = self.layering(feature, 0, 0.1)
            _ = self.layering(feature, 0, 0.05)
            
            df1['年月'] = df1['dt'].apply(lambda x: x.strftime("%Y年%m月"))
            dfm = df1.groupby('年月').agg({'ic': 'mean'})
            logger.info(f"特征 {feature} 与未来1日收益的相关系数月度描述：{dfm.describe().round(4).to_dict()}")
            logger.info(f"特征 {feature} 与未来1日收益的相关系数月度胜率：{len(dfm[dfm['ic'] > 0])/len(dfm):.4f}")


