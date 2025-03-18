# -*- coding: utf-8 -*-
import pandas as pd
import loguru


def mark_periods(df: pd.DataFrame, **kwargs):
    """【后验，有未来信息，不能用于实盘】标记CTA最容易/最难赚钱的N个时间段

    最容易赚钱：笔走势的绝对收益、SNR、波动率排序，取这三个指标的均值，保留 top n 个均值最大的笔，在标准K线上新增一列，标记这些笔的起止时间
    最难赚钱：笔走势的绝对收益、SNR、波动率排序，取这三个指标的均值，保留 bottom n 个均值最小的笔，在标准K线上新增一列，标记这些笔的起止时间

    :param df: 标准K线数据，必须包含 dt, symbol, open, close, high, low, vol, amount 列
    :param percent: 需要返回的最佳/最差时间段数量占比
    :return: 带有标记的K线数据，新增列 'is_best_period', 'is_worst_period'
    """
    from czsc.analyze import CZSC
    from czsc.utils.bar_generator import format_standard_kline

    freq = kwargs.get('freq', '日线') # 可选值：1分钟、5分钟、15分钟、30分钟、60分钟、日线、周线、月线

    if kwargs.get("copy", True):
        df = df.copy()
    
    verbose = kwargs.get("verbose", False)
    logger = kwargs.get("logger", loguru.logger)

    rows = []
    for symbol, dfg in df.groupby('symbol'):
        if verbose:
            logger.info(f"正在处理 {symbol} 数据，共 {len(dfg)} 根K线；时间范围：{dfg['dt'].min()} - {dfg['dt'].max()}")

        dfg = dfg.sort_values('dt').copy().reset_index(drop=True)
        bars = format_standard_kline(dfg, freq)
        c = CZSC(bars, max_bi_num=len(bars))

        bi_stats = []
        for bi in c.bi_list:
            bi_stats.append({
                'symbol': symbol,
                'sdt': bi.sdt,
                'edt': bi.edt,
                'direction': bi.direction.value,
                'power_price': bi.power_price,
                'power_snr': bi.power_snr,
                'power_volume': bi.power_volume,
            })
        bi_stats = pd.DataFrame(bi_stats)
        bi_stats['power_price_rank'] = bi_stats['power_price'].rank(method='min', ascending=True, pct=True)
        bi_stats['power_snr_rank'] = bi_stats['power_snr'].rank(method='min', ascending=True, pct=True)
        bi_stats['power_volume_rank'] = bi_stats['power_volume'].rank(method='min', ascending=True, pct=True)
        bi_stats['score'] = bi_stats['power_price_rank'] + bi_stats['power_snr_rank'] + bi_stats['power_volume_rank']
        bi_stats['rank'] = bi_stats['score'].rank(method='min', ascending=False, pct=True)

        best_periods = bi_stats[bi_stats['rank'] <= 0.15]
        worst_periods = bi_stats[bi_stats['rank'] > 0.6]

        if verbose:
            logger.info(f"最容易赚钱的笔：{len(best_periods)} 个，详情：\n{best_periods}")
            logger.info(f"最难赚钱的笔：{len(worst_periods)} 个，详情：\n{worst_periods}")

        # 用 best_periods 的 sdt 和 edt 标记 is_best_period 为 True
        dfg['is_best_period'] = 0
        for _, row in best_periods.iterrows():
            dfg.loc[(dfg['dt'] >= row['sdt']) & (dfg['dt'] <= row['edt']), 'is_best_period'] = 1

        # 用 worst_periods 的 sdt 和 edt 标记 is_worst_period 为 True`
        dfg['is_worst_period'] = 0
        for _, row in worst_periods.iterrows():
            dfg.loc[(dfg['dt'] >= row['sdt']) & (dfg['dt'] <= row['edt']), 'is_worst_period'] = 1

        rows.append(dfg)


    dfr = pd.concat(rows, ignore_index=True)
    if verbose:
        logger.info(f"处理完成，最易赚钱时间覆盖率：{dfr['is_best_period'].value_counts()[1] / len(dfr):.2%}, "
                    f"最难赚钱时间覆盖率：{dfr['is_worst_period'].value_counts()[1] / len(dfr):.2%}")

    return dfr


if __name__ == '__main__':
    from czsc.connectors import research

    df1 = research.get_raw_bars('000905.SH', '日线', '20170101', '20230101', fq='前复权', raw_bars=False)
    df2 = research.get_raw_bars('000001.SH', '日线', '20170101', '20230101', fq='前复权', raw_bars=False)

    df = pd.concat([df1, df2], ignore_index=True)

    dfs = mark_periods(df.copy(), freq='日线', verbose=True)
