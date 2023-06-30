import sys

sys.path.insert(0, '.')
sys.path.insert(0, '..')
sys.path.insert(0, '../..')
sys.path.insert(0, '../../..')
import math
from collections import OrderedDict
from czsc import CZSC
from loguru import logger
from czsc.signals.tas import update_atr_cache
from czsc.utils import create_single_signal


# 定义信号函数
# ----------------------------------------------------------------------------------------------------------------------
def tas_atr_V230630(c: CZSC, **kwargs) -> OrderedDict:
    """ATR波动强弱

    参数模板："{freq}_D{di}ATR{timeperiod}_波动V230630"

    **信号逻辑：**

    ATR与收盘价的比值衡量了价格振幅比率的大小，
    如果二者比值小于0.5%，则说明此时开仓杠杆率LEV > 1，此时波动较小，开仓信号较强；
    如果二者比值大于0.5%，则说明开仓杠杆率LEV < 1，此时波动较大，开仓信号较弱。
    
    **信号列表：**

    - Signal('15分钟_D1ATR14_波动V230630_波动较大_任意_任意_0')
    - Signal('15分钟_D1ATR14_波动V230630_波动较小_任意_任意_0')
    
    :param c:  czsc对象
    :param kwargs:

        - di: 倒数第i根K线
        - timeperiod: ATR指标的参数

    :return: 信号字典
    """
    di = int(kwargs.get('di', 1))
    timeperiod = int(kwargs.get('timeperiod', 14))
    freq = c.freq.value
    cache_key = update_atr_cache(c, timeperiod=timeperiod)

    k1, k2, k3 = f"{freq}_D{di}ATR{timeperiod}_波动V230630".split('_')
    v1 = "其他"
    if len(c.bars_raw) < di + timeperiod + 8:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bar = c.bars_raw[di]
    atr = bar.cache[cache_key]
    if math.isnan(atr):
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)
    
    lev =  0.005 / atr * bar.close
    v1 = "波动较大" if lev < 1 else "波动较小"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)



def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols('中证500成分股')
    symbol = symbols[10]
    bars = research.get_raw_bars(symbol, '15分钟', '20181101', '20210101', fq='前复权')
    signals_config = [{'name': tas_atr_V230630, 'freq': '15分钟', 'di': 1}]
    check_signals_acc(bars, signals_config=signals_config, height='780px')  # type: ignore


if __name__ == '__main__':
    check()
