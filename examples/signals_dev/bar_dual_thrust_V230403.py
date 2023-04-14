from czsc import CZSC
from czsc.utils import create_single_signal, get_sub_elements


def bar_dual_thrust_V230403(c: CZSC, **kwargs):
    """Dual Thrust 通道突破

    参数模板："{freq}_D{di}通道突破#{N}#{K1}#{K2}_BS辅助V230403"

    **信号逻辑：**

    参见：https://www.myquant.cn/docs/python_strategyies/424

    其核心思想是定义一个区间，区间的上界和下界分别为支撑线和阻力线。当价格超过上界时，看多，跌破下界，看空。

    **信号列表：**

    - Signal('日线_D1通道突破#5#20#20_BS辅助V230403_看空_任意_任意_0')
    - Signal('日线_D1通道突破#5#20#20_BS辅助V230403_看多_任意_任意_0')

    :param c: 基础周期的 CZSC 对象
    :param kwargs: 其他参数
        - di: 倒数第 di 根 K 线
        - N: 前N天的数据
        - K1: 参数，根据经验优化
        - K2: 参数，根据经验优化
    :return: 信号字典
    """
    di = int(kwargs.get('di', 1))
    N = int(kwargs.get('N', 5))
    K1 = int(kwargs.get('K1', 20))
    K2 = int(kwargs.get('K2', 20))

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}通道突破#{N}#{K1}#{K2}_BS辅助V230403".split('_')
    if len(c.bars_raw) < 3:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1='其他')

    bars = get_sub_elements(c.bars_raw, di=di+1, n=N+1)
    HH = max([i.high for i in bars])
    HC = max([i.close for i in bars])
    LC = min([i.close for i in bars])
    LL = min([i.low for i in bars])
    Range = max(HH - LC, HC - LL)

    current_bar = c.bars_raw[-di]
    buy_line = current_bar.open + Range * K1 / 100    # 上轨
    sell_line = current_bar.open - Range * K2 / 100   # 下轨

    # 根据价格位置判断信号
    if current_bar.close > buy_line:
        v1 = '看多'
    elif current_bar.close < sell_line:
        v1 = '看空'
    else:
        v1 = '其他'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20181101', '20210101', fq='前复权')

    signals_config = [{'name': bar_dual_thrust_V230403, 'freq': '日线'}]
    check_signals_acc(bars, signals_config=signals_config, height='780px')


if __name__ == '__main__':
    check()
