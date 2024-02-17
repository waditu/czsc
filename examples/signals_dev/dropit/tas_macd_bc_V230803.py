from loguru import logger

try:
    import talib as ta
except:
    logger.warning(
        f"ta-lib 没有正确安装，相关信号函数无法正常执行。" f"请参考安装教程 https://blog.csdn.net/qaz2134560/article/details/98484091")
from collections import OrderedDict
from czsc.analyze import CZSC
from czsc.objects import Direction, Mark
from czsc.signals.tas import update_macd_cache
from czsc.utils import create_single_signal


def tas_macd_bc_V230803(c: CZSC, **kwargs) -> OrderedDict:
    """MACD辅助背驰判断

    参数模板："{freq}_MACD双分型背驰_BS辅助V230803"

    **信号逻辑：**

    以向上笔为例，当出现两个顶分型时，当后一个顶分型中间K线的MACD柱子与前一个相比更低，认为是顶背驰。

    **信号列表：**

    - Signal('60分钟_MACD双分型背驰_BS辅助V230803_多头_任意_任意_0')
    - Signal('60分钟_MACD双分型背驰_BS辅助V230803_空头_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 无
    :return: 信号识别结果
    """
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_MACD双分型背驰_BS辅助V230803".split('_')
    v1 = '其他'
    cache_key = update_macd_cache(c)
    if len(c.bi_list) < 3 or len(c.bars_ubi) >= 7:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    b1 = c.bi_list[-1]
    if b1.direction == Direction.Up:
        fx1, fx2 = [fx for fx in c.fx_list[-10:] if fx.mark == Mark.G][-2:]
        macd1 = fx1.raw_bars[1].cache[cache_key]['macd']
        macd2 = fx2.raw_bars[1].cache[cache_key]['macd']
        if macd1 > macd2 > 0:
            v1 = '空头'
    else:
        fx1, fx2 = [fx for fx in c.fx_list[-10:] if fx.mark == Mark.D][-2:]
        macd1 = fx1.raw_bars[1].cache[cache_key]['macd']
        macd2 = fx2.raw_bars[1].cache[cache_key]['macd']
        if macd1 < macd2 < 0:
            v1 = '多头'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20181101', '20210101', fq='前复权')

    signals_config = [{'name': tas_macd_bc_V230803, 'freq': "60分钟"}]
    check_signals_acc(bars, signals_config=signals_config, height='780px', delta_days=5)  # type: ignore


if __name__ == '__main__':
    check()
