# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/7/15 13:42
describe: 特征分析相关的传感器
"""
import pandas as pd
from loguru import logger


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
        self.dfs = dfs  # 所有交易品种的特征打分数据，必须包含以下列：dt, open, close, high, low, vol, amount, score
        self.k = k  # 每期固定选择的数量
        self.d = d  # 每期允许变动的数量
        self.kwargs = kwargs
        self.is_stocks = kwargs.get("is_stocks", False)  # 是否是A股，如果是A股，需要考虑涨跌停的情况
        self.__preprocess()

        self.operate_fee = kwargs.get("operate_fee", 15)  # 单边手续费+交易滑点，单位：BP
        self.holds = {}  # 每期持有的品种
        self.operates = {}  # 每期操作的品种
        for dt in self.dts:
            self.__deal_one_time(dt)

    def __preprocess(self):
        assert "dt" in self.dfs.columns, "必须包含dt列"
        assert "n1b" in self.dfs.columns, "必须包含n1b列"
        assert "symbol" in self.dfs.columns, "必须包含symbol列"
        assert "score" in self.dfs.columns, "必须包含score列, 这是选择交易品种的依据"

        self.dfs["dt"] = pd.to_datetime(self.dfs["dt"]).dt.strftime("%Y-%m-%d %H:%M:%S")
        dts = sorted(self.dfs["dt"].unique())
        last_dt_map = {dt: dts[i - 1] for i, dt in enumerate(dts)}
        self.dts, self.last_dt_map = dts, last_dt_map
        self.score_map = {
            dt: dfg[["symbol", "dt", "open", "close", "high", "low", "score", "n1b"]].copy()
            for dt, dfg in self.dfs.groupby("dt")
        }

    def __deal_one_time(self, dt):
        """单次调整记录"""
        k, d, is_stocks = self.k, self.d, self.is_stocks

        score = self.score_map[dt]
        if is_stocks:
            zt_symbols = [x["symbol"] for _, x in score.iterrows() if x["close"] == x["high"] >= x["open"]]
            dt_symbols = [x["symbol"] for _, x in score.iterrows() if x["close"] == x["low"] <= x["open"]]
            score_a = score[~score.symbol.isin(zt_symbols + dt_symbols)].copy()
            logger.info(f"A股今日{dt}涨停{len(zt_symbols)}个品种，跌停{len(dt_symbols)}个品种，已跳过")
        else:
            score_a = score.copy()

        if not self.holds:
            logger.info(f"当前持仓为空，选择前{k}个品种")
            assert not self.operates, "当holds是空的时候，操作记录必须为空"

            _df = score_a.sort_values(by="score", ascending=False).head(k)
            _df["edge"] = _df["n1b"] - self.operate_fee
            self.holds[dt] = _df

            _df_operates = [
                {"symbol": row["symbol"], "dt": dt, "action": "buy", "price": row["close"]} for _, row in _df.iterrows()
            ]
            self.operates[dt] = pd.DataFrame(_df_operates)
            return

        # 有持仓的情况
        score = self.score_map[dt]
        last_dt = self.last_dt_map[dt]
        last_holds = self.holds[last_dt].copy()
        last_symbols = last_holds["symbol"].tolist()
        skip_symbols = [x for x in last_symbols if x not in score["symbol"].tolist()]
        if skip_symbols:
            logger.warning(
                f"【数据缺陷提示】上一期持仓中，有{len(skip_symbols)}个品种，本期{dt}不在交易品种中，已跳过: {skip_symbols}"
            )

        topk_symbols = score_a.sort_values(by="score", ascending=False).head(k)["symbol"].tolist()
        sell_symbols = (
            score_a[score_a.symbol.isin(last_symbols)]
            .sort_values(by="score", ascending=False)
            .tail(d)["symbol"]
            .tolist()
        )
        sell_symbols = [x for x in sell_symbols if x not in topk_symbols] + skip_symbols
        keep_symbols = [x for x in last_symbols if x not in sell_symbols]
        if len(keep_symbols) != k - len(sell_symbols):
            logger.warning(f"保持品种数量不对，当前只有{len(keep_symbols)}个品种")

        buy_symbols = (
            score_a[~score_a.symbol.isin(keep_symbols)]
            .sort_values(by="score", ascending=False)
            .head(len(sell_symbols))["symbol"]
            .tolist()
        )
        assert len(buy_symbols) == len(sell_symbols), "买入品种数量必须等于卖出品种数量"
        assert len(keep_symbols + buy_symbols) == k, "保持品种数量+买入品种数量必须等于k"
        _df = score[score.symbol.isin(keep_symbols + buy_symbols)].sort_values(by="score", ascending=False)

        if len(_df) != k:
            logger.warning(f"选择的品种数量不等于{k}，当前只有{len(_df)}个品种")

        _df["edge"] = _df.apply(
            lambda row: row["n1b"] - self.operate_fee if row["symbol"] in buy_symbols else row["n1b"], axis=1
        )
        self.holds[dt] = _df

        # 平仓扣费，在上一期的持仓中，卖出的品种，需要扣除手续费
        last_holds["edge"] = last_holds.apply(
            lambda row: row["edge"] - self.operate_fee if row["symbol"] in sell_symbols else row["edge"], axis=1
        )
        self.holds[last_dt] = last_holds

        _sell_operates = [
            {"symbol": row["symbol"], "dt": dt, "action": "sell", "price": row["close"]}
            for _, row in score[score.symbol.isin(sell_symbols)].iterrows()
        ]
        _buy_operates = [
            {"symbol": row["symbol"], "dt": dt, "action": "buy", "price": row["close"]}
            for _, row in score[score.symbol.isin(buy_symbols)].iterrows()
        ]
        _df_operates = pd.DataFrame(_sell_operates + _buy_operates)
        self.operates[dt] = _df_operates
