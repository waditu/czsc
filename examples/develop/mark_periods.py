# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"A:\ZB\git_repo\waditu\czsc")
import pandas as pd
import loguru
import numpy as np
import streamlit as st

st.set_page_config(layout="wide")



# def mark_cta_periods(df: pd.DataFrame, **kwargs):
#     """【后验，有未来信息，不能用于实盘】标记CTA最容易/最难赚钱的N个时间段

#     最容易赚钱：笔走势的绝对收益、R平方、波动率排序，取这三个指标的均值，保留 top n 个均值最大的笔，在标准K线上新增一列，标记这些笔的起止时间
#     最难赚钱：笔走势的绝对收益、R平方、波动率排序，取这三个指标的均值，保留 bottom n 个均值最小的笔，在标准K线上新增一列，标记这些笔的起止时间

#     :param df: 标准K线数据，必须包含 dt, symbol, open, close, high, low, vol, amount 列
#     :param kwargs: 

#         - copy: 是否复制数据
#         - verbose: 是否打印日志
#         - logger: 日志记录器
#         - q1: 最容易赚钱的笔的占比
#         - q2: 最难赚钱的笔的占比

#     :return: 带有标记的K线数据，新增列 'is_best_period', 'is_worst_period'
#     """
#     from czsc.analyze import CZSC
#     from czsc.utils.bar_generator import format_standard_kline

#     q1 = kwargs.get("q1", 0.15)
#     q2 = kwargs.get("q2", 0.4)
#     assert 0.3 >= q1 >= 0.0, "q1 必须在 0.3 和 0.0 之间"
#     assert 0.5 >= q2 >= 0.0, "q2 必须在 0.5 和 0.0 之间"

#     if kwargs.get("copy", True):
#         df = df.copy()
    
#     verbose = kwargs.get("verbose", False)
#     logger = kwargs.get("logger", loguru.logger)

#     rows = []
#     for symbol, dfg in df.groupby('symbol'):
#         if verbose:
#             logger.info(f"正在处理 {symbol} 数据，共 {len(dfg)} 根K线；时间范围：{dfg['dt'].min()} - {dfg['dt'].max()}")

#         dfg = dfg.sort_values('dt').copy().reset_index(drop=True)
#         bars = format_standard_kline(dfg, freq='30分钟')
#         c = CZSC(bars, max_bi_num=len(bars))

#         bi_stats = []
#         for bi in c.bi_list:
#             bi_stats.append({
#                 'symbol': symbol,
#                 'sdt': bi.sdt,
#                 'edt': bi.edt,
#                 'direction': bi.direction.value,
#                 'power_price': abs(bi.change),
#                 'length': bi.length,
#                 'rsq': bi.rsq,
#                 'power_volume': bi.power_volume,
#             })
#         bi_stats = pd.DataFrame(bi_stats)
#         bi_stats['power_price_rank'] = bi_stats['power_price'].rank(method='min', ascending=True, pct=True)
#         bi_stats['rsq_rank'] = bi_stats['rsq'].rank(method='min', ascending=True, pct=True)
#         bi_stats['power_volume_rank'] = bi_stats['power_volume'].rank(method='min', ascending=True, pct=True)
#         bi_stats['score'] = bi_stats['power_price_rank'] + bi_stats['rsq_rank'] + bi_stats['power_volume_rank']
#         bi_stats['rank'] = bi_stats['score'].rank(method='min', ascending=False, pct=True)

#         best_periods = bi_stats[bi_stats['rank'] <= q1]
#         worst_periods = bi_stats[bi_stats['rank'] > 1 - q2]

#         if verbose:
#             logger.info(f"最容易赚钱的笔：{len(best_periods)} 个，详情：\n{best_periods.sort_values('rank', ascending=False)}")
#             logger.info(f"最难赚钱的笔：{len(worst_periods)} 个，详情：\n{worst_periods.sort_values('rank', ascending=True)}")

#         # 用 best_periods 的 sdt 和 edt 标记 is_best_period 为 True
#         dfg['is_best_period'] = 0
#         for _, row in best_periods.iterrows():
#             dfg.loc[(dfg['dt'] >= row['sdt']) & (dfg['dt'] <= row['edt']), 'is_best_period'] = 1

#         # 用 worst_periods 的 sdt 和 edt 标记 is_worst_period 为 True`
#         dfg['is_worst_period'] = 0
#         for _, row in worst_periods.iterrows():
#             dfg.loc[(dfg['dt'] >= row['sdt']) & (dfg['dt'] <= row['edt']), 'is_worst_period'] = 1

#         rows.append(dfg)

#     dfr = pd.concat(rows, ignore_index=True)
#     if verbose:
#         logger.info(f"处理完成，最易赚钱时间覆盖率：{dfr['is_best_period'].value_counts()[1] / len(dfr):.2%}, "
#                     f"最难赚钱时间覆盖率：{dfr['is_worst_period'].value_counts()[1] / len(dfr):.2%}")

#     return dfr


@st.cache_data(ttl=60*60*24)
def prepare_data(**kwargs):
    from czsc.connectors import research

    df1 = research.get_raw_bars('000905.SH', '日线', '20170101', '20230101', fq='前复权', raw_bars=False)
    df2 = research.get_raw_bars('000001.SH', '日线', '20170101', '20230101', fq='前复权', raw_bars=False)

    df = pd.concat([df1, df2], ignore_index=True)
    
    # dfs = mark_cta_periods(df.copy(), freq='日线', verbose=True)
    dfs = df.copy()
    print(dfs.head())
    dfs = dfs.sort_values('dt').copy().reset_index(drop=True) 

    return dfs


# def show_cta_periods_classify(df: pd.DataFrame, **kwargs):
#     """展示不同市场环境下的策略表现

#     :param df: 标准K线数据，
#             必须包含 dt, symbol, open, close, high, low, vol, amount, weight, price 列; 
#             如果 price 列不存在，则使用 close 列
#     :param kwargs: 

#         - fee_rate: 手续费率
#         - digits: 小数位数
#         - weight_type: 权重类型
#         - q1: 最容易赚钱的笔的占比, mark_cta_periods 函数的参数
#         - q2: 最难赚钱的笔的占比, mark_cta_periods 函数的参数
#     """
#     from rs_czsc import WeightBacktest
#     from czsc.utils.st_components import show_daily_return, show_cumulative_returns

#     fee_rate = kwargs.get('fee_rate', 0.00)
#     digits = kwargs.get('digits', 1)
#     weight_type = kwargs.get('weight_type', 'ts')
#     q1 = kwargs.get('q1', 0.15)
#     q2 = kwargs.get('q2', 0.4)

#     dfs = mark_cta_periods(df.copy(), freq='日线', verbose=False, q1=q1, q2=q2)

#     if 'price' not in dfs.columns:
#         dfs['price'] = dfs['close']

#     p1 = dfs['is_best_period'].value_counts()[1] / len(dfs)
#     p2 = dfs['is_worst_period'].value_counts()[1] / len(dfs)
#     st.markdown(f"趋势行情占比：:red[{p1:.2%}]；震荡行情占比：:blue[{p2:.2%}]")

#     wb = WeightBacktest(dfs[['dt', 'symbol', 'weight', 'price']], fee_rate=fee_rate, digits=digits, weight_type=weight_type)

#     df1 = dfs.copy()
#     df1['weight'] = np.where(df1['is_best_period'], df1['weight'], 0)
#     df1 = df1[['dt', 'symbol', 'weight', 'price']].copy().reset_index(drop=True)
#     wb1 = WeightBacktest(df1, fee_rate=fee_rate, digits=digits, weight_type=weight_type)

#     df2 = dfs.copy()
#     df2['weight'] = np.where(df2['is_worst_period'], df2['weight'], 0)
#     df2 = df2[['dt', 'symbol', 'weight', 'price']].copy().reset_index(drop=True)
#     wb2 = WeightBacktest(df2, fee_rate=fee_rate, digits=digits, weight_type=weight_type)

#     classify = ['原始策略', '趋势行情', '震荡行情']
#     # stats = pd.DataFrame([wb.stats, wb1.stats, wb2.stats])
#     # stats['classify'] = classify
#     # st.dataframe(stats)

#     dailys = []
#     for wb_, classify_ in zip([wb, wb1, wb2], classify):
#         df_daily = wb_.daily_return.copy()
#         df_daily = df_daily[['date', 'total']].copy().reset_index(drop=True)
#         df_daily['classify'] = classify_
#         dailys.append(df_daily)
#     dailys = pd.concat(dailys, ignore_index=True)
#     dailys['date'] = pd.to_datetime(dailys['date'])
#     dailys = pd.pivot_table(dailys, index='date', columns='classify', values='total')
#     show_daily_return(dailys, stat_hold_days=False)
#     # show_cumulative_returns(dailys, fig_title="")


def main():
    from czsc.utils.st_components import show_cta_periods_classify
    df = prepare_data()
    df['weight'] = df.groupby('symbol')['close'].rolling(window=5, min_periods=1).apply(lambda x: np.sign(x.iloc[-1] - x.mean())).reset_index(0, drop=True)
    df['price'] = df['close']
    show_cta_periods_classify(df, verbose=True)


if __name__ == '__main__':
    main()
