from collections import OrderedDict
import pandas as pd
import tushare as ts
import numpy as np
from tqdm import tqdm
from czsc.connectors import research
from czsc import CZSC, check_signals_acc, get_sub_elements
from czsc.utils import create_single_signal


def lverage_up_dw_line_V230824(c: CZSC, **kwargs) -> OrderedDict:
    """.....，贡献者：琅盎

    参数模板："{freq}_D{di}N{n}_V230604dc"

    信号逻辑：**

    

    信号列表：

    - Signal('日线_D1N10_V230604dc_看空_任意_任意_0')
    - Signal('日线_D1N10_V230604dc_看多_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
        - :param di: 信号计算截止倒数第i根K线
        - :param n: 获取K线的根数，默认为105
        - :param start_date: 获取tushare备用行情的开始日期－－>  调用函数时需要和主数据开始日期保持一致
        - :param end_date: 获取tushare备用行情的结束日期－－>  调用函数时需要和主数据结束日期保持一致

    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    n = int(kwargs.get("n", 10))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{n}_V230604dc".split('_')
    assert freq == "日线", "该信号只能在日线上使用"

    # 从外部获取数据进行缓存
    cache_key = "lverage_up_dw_line_V230824_volume_ratio"
    if cache_key not in c.cache.keys():
        pro = ts.pro_api()
        _df = pro.daily_basic(ts_code=c.symbol, start_date='20100101', end_date='20240101', fields='trade_date,volume_ratio')
        c.cache[cache_key] = _df.set_index('trade_date')['volume_ratio'].to_dict()
    map_volume_ratio = c.cache[cache_key]

    v1 = "其他"
    if len(c.bars_raw) < di + 10:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)
    
    _bars = get_sub_elements(c.bars_raw, di=di, n=n)  # 取n根K线
    max_high = max([x.high for x in _bars])  
    min_low = min([x.low for x in _bars])  
    ratio = [map_volume_ratio.get(x.dt.strftime("%Y%m%d"), 1) for x in _bars]
    max_ratio = max(ratio) 
    min_ratio = min(ratio)  

    dc = (max_high + min_low) / 2
    ra = (max_ratio + min_ratio) / 2 # type: ignore

    if _bars[-1].close > dc and ratio[-1] < ra:
        v1 = "看多"
    if _bars[-1].close < dc and ratio[-1] > ra:
        v1 = "看空"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols('中证500成分股')
    symbol = symbols[0]
    # for symbol in symbols[:10]:
    bars = research.get_raw_bars(symbol, '日线', '20101101', '20230101', fq='前复权')
    signals_config = [{'name': lverage_up_dw_line_V230824, 'freq': '日线', 'di': 1, 'n': 10}]
    check_signals_acc(bars, signals_config=signals_config, height='780px')  # type: ignore


if __name__ == '__main__':
    check()
