# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/5/11 17:53
describe: CrossSectionalPerformance - 截面绩效分析
"""
import os
import time
import numpy as np
import pandas as pd
from loguru import logger
from czsc.utils import WordWriter
from czsc.utils.stats import net_value_stats
from czsc.utils.plt_plot import plot_net_value


class CrossSectionalPerformance:
    """根据截面持仓信息，计算截面绩效"""

    def __init__(self, dfh: pd.DataFrame, **kwargs):
        """计算截面绩效

        :param dfh: 截面持仓信息，包含以下字段
            symbol: 标的代码
            dt: 交易时间
            pos: 持仓方向，1 = 多头，-1 = 空头，0 = 平仓
            n1b: 持仓至下根K线结束的收益率，单位：BP
            weight: 持仓权重，可选，如果不输入，则默认等权

            数据示例：

                =========  ===================  =====  =====
                symbol     dt                     pos    n1b
                =========  ===================  =====  =====
                000008.SZ  2017-01-03 09:45:00      0   10.7
                000008.SZ  2017-01-03 10:00:00      1   10.7
                000008.SZ  2017-01-03 10:15:00      0  -10.7
                000008.SZ  2017-01-03 10:30:00      1   10.7
                000008.SZ  2017-01-03 10:45:00      0  -10.7
                =========  ===================  =====  =====

        :param kwargs: 其他参数
        """
        self.version = 'V230528'
        dfh = dfh.copy()
        dfh['dt'] = pd.to_datetime(dfh['dt'])
        dfh['date'] = dfh['dt'].apply(lambda x: x.date())
        self.dfh = dfh
        # self.dfh = self.__add_count(dfh)
        self.dfh = self.__add_equal_weight(self.dfh, max_total_weight=kwargs.get('max_total_weight', 1))
        self.dfh['edge'] = self.dfh['n1b'] * self.dfh['weight']
        self.kwargs = kwargs

    @staticmethod
    def __add_count(dfh):
        """添加连续持仓计数"""
        res = []
        for symbol, dfs in dfh.groupby('symbol'):
            dfs = dfs.sort_values('dt', ascending=True)
            dfs['count'] = dfs['pos'].groupby((dfs['pos'] != dfs['pos'].shift()).cumsum()).cumcount() + 1
            dfs['count'] = np.where(dfs['pos'] == 0, 0, dfs['count'])
            res.append(dfs)
        return pd.concat(res, ignore_index=True)

    @staticmethod
    def __add_equal_weight(dfh, max_total_weight=1):
        """添加等权重

        :param dfh:
        :param max_total_weight: 最大权重，如果某个截面的持仓权重超过该值，则按该值计算；
                1 表示 100% 权重，即 1 倍杠杆，2 表示 200% 权重，即 2 倍杠杆
        :return:
        """
        if 'weight' in dfh.columns:
            return dfh

        results = []
        for dt, dfg in dfh.groupby('dt'):
            dfg['weight'] = 0
            if dfg['pos'].abs().sum() != 0:
                symbol_weight = max_total_weight / dfg['pos'].abs().sum()
                dfg['weight'] = symbol_weight * dfg['pos']
            results.append(dfg)
        dfh = pd.concat(results, ignore_index=True)
        return dfh

    def cal_turnover(self):
        """计算换手率"""
        dfh = self.dfh.copy()
        dft = pd.pivot_table(dfh, index='dt', columns='symbol', values='weight', aggfunc='sum')
        dft = dft.fillna(0)

        dft1 = dft.diff().abs().sum(axis=1)
        # 由于是 diff 计算，第一个时刻的仓位变化被忽视了，修改一下
        dft1.iloc[0] = dfh[dfh['dt'] == dfh['dt'].min()]['pos'].sum()

        dft2 = dft.apply(lambda x: x[x != 0].count(), axis=1).fillna(0)
        dft = pd.concat([dft1, dft2], axis=1)
        dft.columns = ['换手率', '持仓数量']
        return dft

    def cross_net_value(self, by='dt', values='edge'):
        """计算截面等权净值

        :param by: 按什么字段计算截面等权净值，默认按交易时间
        :param values: 计算截面等权净值时，使用的字段，默认使用 edge，计算策略收益，可选值：edge, n1b
            输入 edge，计算策略收益
            输入 n1b，计算基准收益
        :return:
        """
        assert values in ['edge', 'n1b']
        dfh = self.dfh.copy()
        dfe = pd.pivot_table(dfh, index=by, columns='symbol', values=values, aggfunc='sum')
        if values == 'edge':
            dfe['截面收益'] = dfe.sum(axis=1).fillna(0)
        else:
            dfe['截面收益'] = dfe.mean(axis=1).fillna(0)

        dfe['累计净值'] = dfe['截面收益'].cumsum()
        dfe['动态回撤'] = ((dfe['累计净值'] + 10000) / (dfe['累计净值'] + 10000).cummax() - 1) * 10000 + 10000
        dfe['dt'] = dfe.index.values
        return dfe[['dt', '截面收益', '累计净值', '动态回撤']].fillna(0).reset_index(drop=True)

    def report(self, file_docx):
        if os.path.exists(file_docx):
            os.remove(file_docx)
            logger.warning(f"删除已存在的文件：{file_docx}")

        writer = WordWriter(file_docx)
        writer.add_title("截面绩效分析报告")
        writer.add_paragraph("本文档由 czsc 编写，用于分析截面绩效。"
                             "截面绩效分析，是指在某个时间点，对所有标的收益进行等权汇总，计算出截面等权收益。")

        dft = self.cal_turnover()
        writer.add_heading("换手率", level=1)
        writer.add_paragraph("换手率，是指在某个时间点，所有标的权重变化的绝对值之和。", first_line_indent=0)
        writer.add_paragraph(f"平均换手率：{round(dft['换手率'].mean(), 4)}; "
                             f"累计换手率：{round(dft['换手率'].sum(), 4)}", first_line_indent=0)

        for dt_col in ['dt', 'date']:

            writer.add_heading(f"按 {dt_col} 截面进行评价", level=1)
            dfe = self.cross_net_value(by=dt_col)
            nv = dfe[['dt', '截面收益']].copy()
            nv.columns = ['dt', 'edge']
            stats = net_value_stats(nv, sub_cost=False)
            stats_info = "\n".join([f"{k}: {v}" for k, v in stats.items()])
            writer.add_paragraph(f"截面等权净值，按 {dt_col} 截面进行评价，统计结果如下：\n{stats_info}", first_line_indent=0)

            # 绘制净值曲线
            writer.add_paragraph(f"按 {dt_col} 截面的策略净值曲线如下：", first_line_indent=0)
            dfe = self.cross_net_value(by=dt_col, values='edge')
            file_png = f"{time.time_ns()}.png"
            plot_net_value(dfe, file_png=file_png, figsize=(9, 5))
            writer.add_picture(file_png, width=15, height=9)
            os.remove(file_png)

            writer.add_paragraph(f"按 {dt_col} 截面的基准净值曲线如下：", first_line_indent=0)
            dfe = self.cross_net_value(by=dt_col, values='n1b')
            file_png = f"{time.time_ns()}.png"
            plot_net_value(dfe, file_png=file_png, figsize=(9, 5))
            writer.add_picture(file_png, width=15, height=9)
            os.remove(file_png)

            # 计算每个月的累计收益
            nv['month'] = nv['dt'].apply(lambda x: x.strftime("%Y-%m"))
            nvm = nv.groupby('month')['edge'].apply(sum).reset_index(drop=False)
            nvm[['year', 'month']] = nvm['month'].apply(lambda x: (x[:4], x[-2:])).values.tolist()
            ymr = pd.pivot_table(nvm, index='year', columns='month', values='edge', aggfunc='sum').fillna(0).round(1)

            writer.add_heading(f"按月进行收益汇总：月胜率 = {len(nvm[nvm['edge'] > 0]) / len(nvm) * 100:.2f}%", level=2)
            writer.add_df_table(ymr.reset_index(drop=False), style='Medium List 1 Accent 2', font_size=8)
            writer.save()
        logger.info(f"报告生成成功：{file_docx}")


def cross_sectional_ranker(df, x_cols, y_col, **kwargs):
    """截面打分排序

    :param df: 因子数据，必须包含日期、品种、因子值、预测列，且按日期升序排列，样例数据如下：
    :param x_cols: 因子列名
    :param y_col: 预测列名
    :param kwargs: 其他参数

        - model_params: dict, 模型参数，默认{'n_estimators': 40, 'learning_rate': 0.01}，可调整，参考lightgbm文档
        - n_splits: int, 时间拆分次数，默认5，即5段时间
        - rank_ascending: bool, 打分排序是否升序，默认False-降序
        - copy: bool, 是否拷贝df，True-拷贝，False-不拷贝

    :return: df, 包含预测分数和排序列
    """
    from lightgbm import LGBMRanker
    from sklearn.model_selection import TimeSeriesSplit

    assert "symbol" in df.columns, "df must have column 'symbol'"
    assert "dt" in df.columns, "df must have column 'dt'"

    if kwargs.get('copy', True):
        df = df.copy()
    df['dt'] = pd.to_datetime(df['dt'])
    df = df.sort_values(['dt', y_col], ascending=[True, False])

    model_params = kwargs.get('model_params', {'n_estimators': 40, 'learning_rate': 0.01})
    model = LGBMRanker(**model_params)

    dfd = pd.DataFrame({'dt': sorted(df['dt'].unique())}).values
    tss = TimeSeriesSplit(n_splits=kwargs.get('n_splits', 5))

    for train_index, test_index in tss.split(dfd):
        train_dts = dfd[train_index][:, 0]
        test_dts = dfd[test_index][:, 0]

        # 拆分训练集和测试集
        train, test = df[df['dt'].isin(train_dts)], df[df['dt'].isin(test_dts)]
        X_train, X_test, y_train = train[x_cols], test[x_cols], train[y_col]
        query_train = train.groupby('dt')['symbol'].count().values

        # 训练模型 & 预测
        model.fit(X_train, y_train, group=query_train)
        df.loc[X_test.index, 'score'] = model.predict(X_test)

    df['rank'] = df.groupby('dt')['score'].rank(ascending=kwargs.get('rank_ascending', False))
    return df
