from collections import OrderedDict
import numpy as np
from czsc.connectors import research
from czsc import CZSC, check_signals_acc, get_sub_elements
from czsc.utils import create_single_signal
from czsc.signals.tas import update_atr_cache


def kcatr_up_dw_line_V230823(c: CZSC, **kwargs) -> OrderedDict:
    """用atr波幅构造上下轨，收盘价突破判断多空  贡献者：琅盎

    参数模板："{freq}_D{di}N{n}M{m}T{th}_KCATR多空V230823"

    **信号逻辑：**

    与布林带类似，都是用价格的移动平均构造中轨，不同的是表示波幅
    的方法，这里用 atr 来作为波幅构造上下轨。价格突破上轨，
    可看成新的上升趋势，买入；价格突破下轨，

    **信号列表：**

    - Signal('日线_D1N30M16T2_KCATR多空V230823_看多_任意_任意_0')
    - Signal('日线_D1N30M16T2_KCATR多空V230823_看空_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典

        - :param di: 信号计算截止倒数第i根K线
        - :param n: 获取K线的根数进行ATR计算，默认为30
        - :param m: 获取K线的根数进行均价计算，默认为16
        - :param th: 突破ATR的倍数，默认为2

    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    n = int(kwargs.get("n", 30))
    m = int(kwargs.get("m", 16))
    th = int(kwargs.get("th", 2))  # 突破ATR的倍数

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{n}M{m}T{th}_KCATR多空V230823".split('_')
    v1 = "其他"
    if len(c.bars_raw) < di + max(m, n) + 10:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    n_bars = get_sub_elements(c.bars_raw, di=di, n=n)
    m_bars = get_sub_elements(c.bars_raw, di=di, n=m)
    atr = np.mean([
        max(
            abs(n_bars[i].high - n_bars[i].low),
            abs(n_bars[i].high - n_bars[i - 1].close),
            abs(n_bars[i - 1].close - n_bars[i - 1].low),
        )
        for i in range(1, len(n_bars))
    ])
    middle = np.mean([x.close for x in m_bars])

    if m_bars[-1].close > middle + atr * th:
        v1 = "看多"
    elif m_bars[-1].close < middle - atr * th:
        v1 = "看空"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def main():
    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20171101', '20210101', fq='前复权')

    signals_config = [{'name': kcatr_up_dw_line_V230823, 'freq': '日线', 'di': 1}]
    check_signals_acc(bars, signals_config=signals_config)


if __name__ == '__main__':
    main()
