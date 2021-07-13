# coding: utf-8
import numpy as np
from tqdm import tqdm
from czsc.utils.ta import SMA
from czsc.analyze import *
from scripts_gm.gm_utils import *


def is_up_gap(bars: List[RawBar]):
    """判断 bars 中是否有向上跳空缺口不补事件出现

    :param bars:
    :return:
    """
    ma5 = SMA(np.array([x.close for x in bars]), timeperiod=5)

    # 收盘价跌破 MA5 是不允许的
    if bars[-1].close < ma5[-1]:
        return False

    max_id = bars[-1].id
    for i in [4, 3, 2, 1]:   # 近五个K线中找缺口
        bar1 = bars[max_id-i-1]
        bar2 = bars[max_id-i]
        max_high = max([x.high for x in bars[:max_id-i-1]])

        # 缺口创新高
        if bar2.high > max_high > bar1.high and bar2.low > bar1.high:
            qid = max_id - i
            p_high = bar1.high
            after_q = [x for x in bars if x.id >= qid]

            if min([x.low for x in after_q]) > p_high \
                    and after_q[0].close > after_q[-1].low:
                return True
            else:
                return False

    return False

def is_up_big(bars: List[RawBar]):
    """判断 bars 中是否有光头阳线突破不补事件出现

    :param bars:
    :return:
    """
    ma5 = SMA(np.array([x.close for x in bars]), timeperiod=5)

    # 收盘价跌破 MA5 是不允许的
    if bars[-1].close < ma5[-1]:
        return False

    max_id = bars[-1].id
    for i in [5, 4, 3, 2]:   # 最近K线中找光头阳线
        bar = bars[max_id - i]
        max_high = max([x.high for x in bars[:max_id-i-1]])
        # 光头大阳线定义：1）涨幅超过7个点；2）开盘价不高于最低价一个点；3）收盘价不低于最高价0.5个点
        if bar.open < bar.low * 1.01 and bar.close < bar.high * 0.995 and (bar.close - bar.open) / bar.open > 0.07:
            qid = max_id - i
            after_q = [x for x in bars if x.id > qid]

            # 三买验证：1）光头阳线创新高；2）新高后的走势不跌破光头阳线的实体中部；3）在光头阳线后一根K线价格范围盘整
            if bar.high > max_high \
                    and min([x.low for x in after_q]) > bar.open + (bar.close - bar.open) / 2 \
                    and after_q[0].close > after_q[-1].low:
                return True
            else:
                return False

    return False


def run_selector(context=None, end_date: [str, datetime] = datetime.now()):
    key = context.wx_key
    symbols = get_index_shares('上证指数')
    if isinstance(end_date, str):
        end_date = pd.to_datetime(end_date)
    push_text(content="start running selector", key=key)
    for symbol in tqdm(symbols, desc=f"{end_date}"):
        try:
            count = 30
            k0 = get_kline(symbol, end_time=end_date, freq='1d', count=count, adjust=ADJUST_PREV)
            print("\n", k0[-1])
            if len(k0) != count:
                continue

            last_vols = [k_.open * k_.vol for k_ in k0[-10:]]
            if sum(last_vols) < 1e9:
                print(f"{symbol} 近10个交易日累计成交金额小于10亿")
                continue
            if min(last_vols) < 5e7:
                print(f"{symbol} 近10个交易日最低成交额小于5000万")
                continue

            if is_up_gap(k0):
                msg = f"symbol: {symbol}\nreason: 日线跳空创新高"
                push_text(content=msg, key=key)
            elif is_up_big(k0):
                msg = f"symbol: {symbol}\nreason: 日线光大阳突破"
                push_text(content=msg, key=key)
        except:
            print("fail on {}".format(symbol))
            traceback.print_exc()
    push_text(content="end running selector", key=key)


if __name__ == '__main__':
    run_selector()


