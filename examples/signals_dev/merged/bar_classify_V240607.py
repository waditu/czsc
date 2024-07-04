from collections import OrderedDict
from czsc.analyze import CZSC
from czsc.utils import create_single_signal, get_sub_elements


def bar_classify_V240607(c: CZSC, **kwargs) -> OrderedDict:
    """两根K线收盘位置分类

    飞书文档：https://s0cqcxuy3p.feishu.cn/wiki/PNY8wB59xicCtVkTacvcrcQgnOh

    参数模板："{freq}_D{di}K2收盘位置_分类V240607"

    **信号逻辑：**

    1. 看多：第二根K线收盘价在第一根K线的最高价上方
    2. 看空：第二根K线收盘价在第一根K线的最低价下方
    3. 中性：其他情况

    **信号列表：**

    - Signal('60分钟_D1K2收盘位置_分类V240607_看空_任意_任意_0')
    - Signal('60分钟_D1K2收盘位置_分类V240607_中性_任意_任意_0')
    - Signal('60分钟_D1K2收盘位置_分类V240607_看多_任意_任意_0')

    :param c: CZSC对象
    :param kwargs:

        - di: int, default 1, 周期偏移量

    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    assert di > 0, "参数 di 必须大于 0"

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}K2收盘位置_分类V240607".split("_")
    v1 = "其他"
    if len(c.bars_raw) < 7 + di:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bar1, bar2 = get_sub_elements(c.bars_raw, di=di, n=2)
    h, l, c = bar1.high, bar1.low, bar2.close
    if c > h:
        v1 = "看多"
    elif c < l:
        v1 = "看空"
    else:
        v1 = "中性"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols("A股主要指数")
    bars = research.get_raw_bars(symbols[0], "15分钟", "20181101", "20210101", fq="前复权")

    signals_config = [
        {"name": bar_classify_V240607, "freq": "60分钟"},
    ]
    check_signals_acc(bars, signals_config=signals_config, height="780px", delta_days=5)  # type: ignore


if __name__ == "__main__":
    check()
