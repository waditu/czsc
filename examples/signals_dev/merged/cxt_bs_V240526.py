import numpy as np
from collections import OrderedDict
from czsc.analyze import CZSC, BI, Direction
from czsc.utils import create_single_signal, get_sub_elements
from loguru import logger as log


def cxt_bs_V240526(c: CZSC, **kwargs) -> OrderedDict:
    """快速走势之后的减速反弹，形成第反弹买点

    参数模板："{freq}_趋势跟随_BS辅助V240526"

    **信号逻辑：**

    1. 取最近 7 笔；
    2. 如果倒数第二笔的 SNR 小于 0.7，或者倒数第二笔的力度小于前 7 笔的最大值，不考虑信号；
    3. 如果倒数第二笔是向上笔，倒数第一笔是向下笔，且倒数第一笔的力度在倒数第二笔的 10% ~ 70% 之间，形成买点；
    4. 如果倒数第二笔是向下笔，倒数第一笔是向上笔，且倒数第一笔的力度在倒数第二笔的 30% ~ 70% 之间，形成卖点。

    **信号列表：**

    - Signal('15分钟_趋势跟随_BS辅助V240526_买点_任意_任意_0')
    - Signal('15分钟_趋势跟随_BS辅助V240526_卖点_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 无
    :return: 信号识别结果
    """
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_趋势跟随_BS辅助V240526".split("_")
    v1 = "其他"
    if len(c.bi_list) < 11:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bis = get_sub_elements(c.bi_list, di=1, n=7)
    b2, b1 = bis[-2:]
    power_price_seq = [x.power_price for x in bis]
    power_volume_seq = [x.power_volume for x in bis]
    slope_seq = [abs(x.slope) for x in bis]

    # 如果倒数第二笔的 SNR 小于 0.7，或者倒数第二笔的价格、量比最大值小于前 7 笔的最大值，不考虑信号
    if b2.SNR < 0.7 or (b2.power_price < np.max(power_price_seq)
                        and b2.power_volume < np.max(power_volume_seq)
                        and b2.slope < np.max(slope_seq)):
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    if b2.direction == Direction.Up and b1.direction == Direction.Down:
        # 买点：倒数第二笔是向上笔，倒数第一笔是向下笔，且倒数第一笔的力度在倒数第二笔的 10% ~ 70% 之间
        if 0.1 * b2.power_price < b1.power_price < 0.7 * b2.power_price:
            v1 = "买点"

    if b2.direction == Direction.Down and b1.direction == Direction.Up:
        # 卖点：倒数第二笔是向下笔，倒数第一笔是向上笔，且倒数第一笔的力度在倒数第二笔的 30% ~ 70% 之间
        if 0.2 * b2.power_price < b1.power_price < 0.7 * b2.power_price:
            v1 = "卖点"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols("A股主要指数")
    bars = research.get_raw_bars(symbols[0], "5分钟", "20181101", "20210101", fq="前复权")

    signals_config = [{"name": cxt_bs_V240526, "freq": "5分钟"}]
    check_signals_acc(bars, signals_config=signals_config, height="780px", delta_days=5)  # type: ignore


if __name__ == "__main__":
    check()
