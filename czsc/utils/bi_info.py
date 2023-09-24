# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/9/24 12:39
describe: K线的笔特征计算
"""
import pandas as pd
from tqdm import tqdm
from typing import List
from czsc.objects import RawBar
from czsc.analyze import CZSC


def calculate_bi_info(bars: List[RawBar], **kwargs) -> pd.DataFrame:
    """计算笔的特征

    :param bars: 原始K线数据
    :return: 笔的特征
    """
    c = CZSC(bars, max_bi_num=kwargs.get("max_bi_num", 10000))

    res = [
        {
            "symbol": c.symbol,
            "sdt": bi.fx_a.dt,
            "edt": bi.fx_b.dt,
            "方向": bi.direction.value,
            "长度": bi.length,
            "分型数": len(bi.fxs),
            "斜边长度": bi.hypotenuse,
            "斜边角度": bi.angle,
            "涨跌幅": (bi.fx_b.fx / bi.fx_a.fx - 1) * 10000,
            "R2": bi.rsq,
        } for bi in c.bi_list
    ]
    _df = pd.DataFrame(res)
    _df['未来第一笔涨跌幅'] = _df['涨跌幅'].shift(-1)
    _df['未来第二笔涨跌幅'] = _df['涨跌幅'].shift(-2)
    return _df


def symbols_bi_infos(symbols, read_bars, freq='5分钟', sdt='20130101', edt='20190101', **kwargs) -> pd.DataFrame:
    """计算多个标的的笔特征

    :param symbols: 品种代码列表
    :param read_bars: 读取K线数据的函数，要求返回 RawBar 对象列表
    :param freq: K线周期, defaults to '5分钟'
    :param sdt: 开始时间, defaults to '20130101'
    :param edt: 结束时间, defaults to '20190101'
    :return: 笔的特征
    """
    bis = []
    for symbol in tqdm(symbols, desc="计算笔的特征"):
        try:
            bars = read_bars(symbol=symbol, freq=freq, sdt=sdt, edt=edt, fq='后复权')
            dfr = calculate_bi_info(bars)
            bis.append(dfr)
        except Exception as e:
            print(f"{symbol} 计算失败: {e}")
    dfb = pd.concat(bis, ignore_index=True)
    return dfb
