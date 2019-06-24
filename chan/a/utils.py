# coding: utf-8

import tushare as ts


def get_kline(ts_code, start_date, end_date, freq='30min'):
    """获取指定级别的前复权K线

    :param ts_code: str
        股票代码，如 600122.SH
    :param freq: str
        K线级别，可选值 [1min, 5min, 15min, 30min, D, M, Y]
    :param start_date: str
        日期，如 20190601
    :param end_date: str
        日期，如 20190610
    :return: pd.DataFrame
        columns = ["symbol", "dt", "open", "close", "high", "low", "vr"]

    example:
    >>> get_kline(ts_code='600122.SH', start_date='20190601', end_date='20190610', freq='30min')
    """
    # https://tushare.pro/document/2?doc_id=109
    df = ts.pro_bar(ts_code=ts_code, freq=freq,
                    start_date=start_date, end_date=end_date,
                    adj='qfq', asset='E')

    # 统一 k 线数据格式为 6 列，分别是 ["symbol", "dt", "open", "close", "high", "low", "vr"]
    if "min" in freq:
        df.rename(columns={'ts_code': "symbol", "trade_time": "dt"}, inplace=True)
    else:
        df.rename(columns={'ts_code': "symbol", "trade_date": "dt"}, inplace=True)

    df.sort_values('dt', inplace=True)
    df.reset_index(drop=True, inplace=True)
    df['vr'] = 0
    for i in range(5, len(df)):
        df.loc[i, 'vr'] = round(df.loc[i, 'vol'] / df.loc[i-5:i-1, 'vol'].mean(), 4)

    return df[['symbol', 'dt', 'open', 'close', 'high', 'low', 'vr']]


