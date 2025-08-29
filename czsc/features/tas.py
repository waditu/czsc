"""
技术指标因子
"""
import inspect
import hashlib
import pandas as pd


def CCF(df, **kwargs):
    """使用 CZSC 库中的 factor 识别因子，主要用于识别缠论/形态因子

    :param df: 标准K线数据，DataFrame结构
    :param kwargs: 其他参数

        - czsc_factor: dict, 缠论因子配置，样例：

            {
                "signals_all": ["日线_D1_表里关系V230101_向上_任意_任意_0"],
                "signals_any": [],
                "signals_not": ["日线_D1_涨跌停V230331_涨停_任意_任意_0"],
            }

        - freq: str, default '日线'，K线级别
        - tag: str, default None，标签，用于区分不同的因子

    :return: pd.DataFrame
    """
    from czsc.objects import Factor
    from czsc.utils import format_standard_kline
    from czsc.traders.base import generate_czsc_signals
    from czsc.traders.sig_parse import get_signals_config

    czsc_factor = kwargs.get('czsc_factor', None)
    freq = kwargs.get('freq', '日线')
    assert czsc_factor is not None and isinstance(czsc_factor, dict), "factor 参数必须指定"
    tag = kwargs.get('tag', hashlib.sha256(f"{czsc_factor}_{freq}".encode()).hexdigest().upper()[:6])

    factor_name = inspect.stack()[0][3]
    factor_col = f'F#{factor_name}#{tag}'

    czsc_factor = Factor.load(czsc_factor)
    signals_seq = czsc_factor.signals_all + czsc_factor.signals_any + czsc_factor.signals_not
    signals_config = get_signals_config([x.signal for x in signals_seq])

    bars = format_standard_kline(df, freq=freq)
    dfs = generate_czsc_signals(bars, signals_config, init_n=300, sdt=bars[0].dt, df=True)
    dfs[factor_col] = dfs.apply(czsc_factor.is_match, axis=1).astype(int)

    df = pd.merge(df, dfs[['dt', factor_col]], on='dt', how='left')
    df[factor_col] = df[factor_col].fillna(0)
    return df
