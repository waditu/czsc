from collections import OrderedDict
from czsc.analyze import CZSC
from czsc.utils import create_single_signal


def bar_classify_V240606(c: CZSC, **kwargs) -> OrderedDict:
    """单根K线收盘位置分类

    飞书文档：https://s0cqcxuy3p.feishu.cn/wiki/P79fwVE19i7vw4keDuac4tFRnMf

    参数模板："{freq}_D{di}收盘位置_分类V240606"

    **信号逻辑：**

    1. 高收盘蜡烛是指收盘价在蜡烛范围的上三分之一内的蜡烛。
    2. 中间收盘价是指收盘价在蜡烛范围的中间三分之一以内。
    3. 中间收盘价是指收盘价在蜡烛范围的中间三分之一以内。

    **信号列表：**

    - Signal('60分钟_D1收盘位置_分类V240606_低位_任意_任意_0')
    - Signal('60分钟_D1收盘位置_分类V240606_中间_任意_任意_0')
    - Signal('60分钟_D1收盘位置_分类V240606_高位_任意_任意_0')

    :param c: CZSC对象
    :param kwargs:

        - di: int, default 1, 周期偏移量

    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    assert di > 0, "参数 di 必须大于 0"

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}收盘位置_分类V240606".split("_")
    v1 = "其他"
    if len(c.bars_raw) < 7 + di:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bar = c.bars_raw[-di]
    close, high, low = bar.close, bar.high, bar.low
    gap_unit = (high - low) / 3
    if close > (high - gap_unit):
        v1 = "高位"
    elif close < (low + gap_unit):
        v1 = "低位"
    else:
        v1 = "中间"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols("A股主要指数")
    bars = research.get_raw_bars(symbols[0], "15分钟", "20181101", "20210101", fq="前复权")

    signals_config = [
        {"name": bar_classify_V240606, "freq": "60分钟"},
        # {"name": bar_plr_V240427, "freq": "60分钟", "m": "空头"},
    ]
    check_signals_acc(bars, signals_config=signals_config, height="780px", delta_days=5)  # type: ignore


if __name__ == "__main__":
    check()
