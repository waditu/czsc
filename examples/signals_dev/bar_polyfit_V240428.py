import numpy as np
from collections import OrderedDict
from czsc.analyze import CZSC
from czsc.objects import Direction, ZS
from czsc.signals.tas import update_macd_cache
from czsc.utils import create_single_signal, get_sub_elements


def bar_polyfit_V240428(c: CZSC, **kwargs) -> OrderedDict:
    """一阶、二阶多项式拟合

    参考资料：
    1. [基于低阶多项式拟合的日内趋势策略](https://zhuanlan.zhihu.com/p/391605615)
    2. 罗军，广发证券，2011，《基于低阶多项式拟合的股指期货趋势交易(LPTT)策略》

    参数模板："{freq}_D{di}W{w}_分类V240428"

    **信号逻辑：**

    若对一阶线性函数求一阶导数，也就是平常所说的斜率，若导数dy/dt>0，说明价格正处于上升趋势；若导数dy/dt<0，则为下跌趋势。
    若对二阶线性函数求二阶导数，若二阶导数d2y/dt2>0，价格曲线为凹（开口向上）；若二阶导数d2y/dt2<0，价格曲线为凸（开口向下）。

    做个类比，价格曲线就像汽车行走的距离轨迹，对距离（位移）求一阶导数就是速度，速度大于0说明朝正方向开，小于0说明朝反方向开。
    求二阶导数就是加速度，假设此时汽车为正向行驶，加速度大于0说明在汽车速度还在增加的状态当中，在不断加速，反之则是处在减速的过程当中。

    **信号列表：**

    - Signal('60分钟_D1W20_分类V240428_加速上涨_任意_任意_0')
    - Signal('60分钟_D1W20_分类V240428_减速上涨_任意_任意_0')
    - Signal('60分钟_D1W20_分类V240428_加速下跌_任意_任意_0')
    - Signal('60分钟_D1W20_分类V240428_减速下跌_任意_任意_0')

    :param c: CZSC对象
    :param kwargs:

        - di: int, default 1, 周期偏移量
        - w: int, default 60, 计算多项式拟合的K线数量

    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    w = int(kwargs.get("w", 20))

    assert di > 0, "参数 di 必须大于 0"
    assert w >= 10, "参数 w 必须大于等于 10"

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}W{w}_分类V240428".split("_")
    v1 = "其他"
    if len(c.bars_raw) < 7 + w:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=di, n=w)
    close = np.array([x.close for x in bars])
    p1 = np.polyfit(np.arange(len(close)), close, 1)[0]
    p2 = np.polyfit(np.arange(len(close)), close, 2)[0]

    if p1 > 0 and p2 > 0:
        v1 = "加速上涨"
    elif p1 < 0 and p2 < 0:
        v1 = "加速下跌"
    elif p1 > 0 and p2 < 0:
        v1 = "减速上涨"
    elif p1 < 0 and p2 > 0:
        v1 = "减速下跌"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols("A股主要指数")
    bars = research.get_raw_bars(symbols[0], "15分钟", "20181101", "20210101", fq="前复权")

    signals_config = [
        {"name": bar_polyfit_V240428, "freq": "60分钟"},
        # {"name": bar_plr_V240427, "freq": "60分钟", "m": "空头"},
    ]
    check_signals_acc(bars, signals_config=signals_config, height="780px", delta_days=5)  # type: ignore


if __name__ == "__main__":
    check()
