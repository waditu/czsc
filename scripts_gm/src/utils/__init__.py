# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/8/3 17:09
"""
import pandas as pd


def ths_symbol_to_gm(ths_symbol: str) -> str:
    """同花顺代码转掘金代码

    :param ths_symbol: 聚宽代码
    :return: gm_symbol
    """
    code, exchange = ths_symbol.split(".")
    if exchange == 'SH':
        gm_symbol = "SHSE." + code
    elif exchange == 'SZ':
        gm_symbol = "SZSE." + code
    else:
        raise ValueError
    return gm_symbol


def read_ths_zx(file_ths_zx: str) -> pd.DataFrame:
    """

    :param file_ths_zx: i问财导出的同花顺标的文件
    :return:
    """
    df = pd.read_excel(file_ths_zx)
    df = df.head(len(df)-1)
    df['掘金代码'] = df['股票代码'].apply(ths_symbol_to_gm)
    return df


def jq_symbol_to_gm(jq_symbol: str) -> str:
    """聚宽代码转掘金代码

    :param jq_symbol: 聚宽代码
    :return: gm_symbol
    """
    code, exchange = jq_symbol.split(".")
    if exchange == 'XSHG':
        gm_symbol = "SHSE." + code
    elif exchange == 'XSHE':
        gm_symbol = "SZSE." + code
    else:
        raise ValueError
    return gm_symbol


def gm_symbol_to_jq(gm_symbol: str) -> str:
    """掘金代码转聚宽代码

    :param gm_symbol: 掘金代码
    :return: jq_symbol
    """
    exchange, code = gm_symbol.split(".")
    if exchange == 'SHSE':
        jq_symbol = code + ".XSHG"
    elif exchange == 'SZSE':
        jq_symbol = code + ".XSHE"
    else:
        raise ValueError
    return jq_symbol


def gm_symbol_to_ts(gm_symbol: str) -> str:
    """掘金代码转Tushare代码

    :param gm_symbol: 掘金代码
    :return: ts_symbol
    """
    exchange, code = gm_symbol.split(".")
    if exchange == 'SHSE':
        ts_symbol = code + ".SH"
    elif exchange == 'SZSE':
        ts_symbol = code + ".SZ"
    else:
        raise ValueError
    return ts_symbol


def tdx_symbol_to_jq(tdx_symbol):
    """将通达信的代码转成聚宽代码"""
    exchange, code = tdx_symbol[0], tdx_symbol[1:]
    if exchange == '0':
        jq_symbol = code + ".XSHE"
    elif exchange == '1':
        jq_symbol = code + ".XSHG"
    else:
        print(f"{exchange} - {code} is not supported.")
        return None
    return jq_symbol


def jq_symbol_to_tdx(jq_symbol):
    """将聚宽的代码转成通达信代码"""
    code, exchange = jq_symbol.split(".")
    if exchange == 'XSHE':
        tdx_symbol = "0" + code
    elif exchange == 'XSHG':
        tdx_symbol = "1" + code
    else:
        print(f"{exchange} - {code} is not supported.")
        return None
    return tdx_symbol
