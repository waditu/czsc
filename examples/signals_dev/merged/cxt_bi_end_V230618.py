import talib as ta
import numpy as np
from czsc import CZSC, Direction
from collections import OrderedDict
from czsc.utils import create_single_signal, get_sub_elements


def cxt_bi_end_V230618(c: CZSC, **kwargs) -> OrderedDict:
    """笔结束辅助判断

    参数模板："{freq}_D{di}MO{max_overlap}_BE辅助V230618"

    **信号逻辑：**

    以向下笔为例，判断笔内是否有小级别中枢，如果有则看多：

    1. 笔内任意两根k线的重叠使该价格位的计数加1，计算从笔.high到笔.low之间各价格位的重叠次数
    2. 通过各价格位的重叠可以得到横轴价格，纵轴重叠次数的图，通过计算途中波峰的个数来得到近似的小中枢个数
        例子：横轴从小到大对应的重叠次数为 1112233211112133334445553321，则可以通过计算从n变为1的次数来得到波峰个数
        这里2-1，2-1，2-1，得到波峰数为3

    **信号列表：**

    - Signal('日线_D1MO1_BE辅助V230618_看多_1小中枢_任意_0')
    - Signal('日线_D1MO1_BE辅助V230618_看空_3小中枢_任意_0')
    - Signal('日线_D1MO1_BE辅助V230618_看空_2小中枢_任意_0')
    - Signal('日线_D1MO1_BE辅助V230618_看空_1小中枢_任意_0')
    - Signal('日线_D1MO1_BE辅助V230618_看多_2小中枢_任意_0')
    - Signal('日线_D1MO1_BE辅助V230618_看空_5小中枢_任意_0')
    - Signal('日线_D1MO1_BE辅助V230618_看空_4小中枢_任意_0')
    - Signal('日线_D1MO1_BE辅助V230618_看多_3小中枢_任意_0')

    **信号说明：**

    类似 cxt_third_bs_V230318 信号，但增加了笔内有无小级别中枢的判断。用k线重叠来近似小级别中枢的判断

    :param c: CZSC对象
    :param kwargs: 

        - di: int, 默认1，表示取倒数第几笔
        - max_overlap: int, 默认3，表示笔内最多允许有几个信号重叠

    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    max_overlap = int(kwargs.get("max_overlap", 3))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}MO{max_overlap}_BE辅助V230618".split('_')
    v1 = "其他"
    if len(c.bi_list) < di + 6 or len(c.bars_ubi) > 3 + max_overlap - 1:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    def __cal_zs_number(raw_bars):
        """计算笔内的小中枢数量

        **信号逻辑：**

        1. 笔内任意两根k线的重叠使该价格位的计数加1，计算从笔.high到笔.low之间各价格位的重叠次数
        2. 通过各价格位的重叠可以得到横轴价格，纵轴重叠次数的图，通过计算途中波峰的个数来得到近似的小中枢个数
        例子：横轴从小到大对应的重叠次数为 1112233211112133334445553321，则可以通过计算从n变为1的次数来得到波峰个数
        这里2-1，2-1，2-1，得到波峰数为3

        :param raw_bars: 构成笔的bar
        :return: 小中枢数量
        """
        # 用笔内价格极值取得笔内价格范围
        max_price = max(bar.high for bar in raw_bars[:-1])
        min_price = min(bar.low for bar in raw_bars[:-1])
        price_range = max_price - min_price

        # 计算当前k线所覆盖的笔内价格范围，并用百分比表示
        for bar in raw_bars[:-1]:
            bar_high_pct = int((100 * (bar.high - min_price) / price_range))
            bar_low_pct = int((100 * (bar.low - min_price) / price_range))
            bar.dt_high_pct = bar_high_pct
            bar.dt_low_pct = bar_low_pct

        # 用这个list保存每个价格的重叠次数，把每个价格映射到100以内的区间内
        df_chengjiaoqu = [[i, 0] for i in range(101)]

        # 对每个k线进行映射，把该k线的价格范围映射到df_chengjiaoqu
        for bar in raw_bars[:-1]:
            range_max = bar.dt_high_pct
            range_min = bar.dt_low_pct

            if range_max == range_min:
                df_chengjiaoqu[range_max][1] += 1
            else:
                for i in range(range_min, range_max + 1):
                    df_chengjiaoqu[i][1] += 1

        # 计算波峰个数，相当于有多少个小中枢
        # 每个波峰结束后价格重叠区域必然会回到1
        peak_count = 0
        for i in range(1, len(df_chengjiaoqu) - 1):
            if df_chengjiaoqu[i][1] == 1 and df_chengjiaoqu[i][1] < df_chengjiaoqu[i - 1][1]:
                peak_count += 1
        return peak_count

    bi = c.bi_list[-di]
    zs_count = __cal_zs_number(bi.raw_bars)
    v1 = '看多' if bi.direction == Direction.Down else '看空'
    # 为了增加稳定性，要确保笔内有小中枢，并且要确保笔内有至少2个分型存在，保证从上往下的分型12的长度比分型34的长度大，来确认背驰
    if len(bi.fxs) >= 4 and zs_count >= 1 and (bi.fxs[-4].fx - bi.fxs[-3].fx) - (bi.fxs[-2].fx - bi.fxs[-1].fx) > 0:
        v2 = f"{zs_count}小中枢"
    else:
        v2 = "其他"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)



def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20181101', '20210101', fq='前复权')

    signals_config = [{'name': cxt_bi_end_V230618, 'freq': '日线', 'di': 1, 'max_overlap': 1}]
    check_signals_acc(bars, signals_config=signals_config, height='780px') # type: ignore


if __name__ == '__main__':
    check()
