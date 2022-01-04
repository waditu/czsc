# coding: utf-8
import zipfile
from tqdm import tqdm
import pandas as pd
from czsc.analyze import *
from czsc.enum import Freq, Operate
from czsc.signals.signals import get_default_signals, get_s_three_bi, get_s_d0_bi
from czsc.objects import Event, Factor, Signal

cur_path = os.path.split(os.path.realpath(__file__))[0]


def read_1min():
    with zipfile.ZipFile(os.path.join(cur_path, 'data/000001.XSHG_1min.zip'), 'r') as z:
        f = z.open('000001.XSHG_1min.csv')
        data = pd.read_csv(f, encoding='utf-8')

    data['dt'] = pd.to_datetime(data['dt'])
    records = data.to_dict('records')

    bars = []
    for row in tqdm(records, desc='read_1min'):
        bar = RawBar(**row)
        bar.freq = Freq.F1
        bars.append(bar)
    return bars


def read_daily():
    file_kline = os.path.join(cur_path, "data/000001.SH_D.csv")
    kline = pd.read_csv(file_kline, encoding="utf-8")
    kline.loc[:, "dt"] = pd.to_datetime(kline.dt)
    bars = [RawBar(symbol=row['symbol'], id=i, freq=Freq.D, open=row['open'], dt=row['dt'],
                   close=row['close'], high=row['high'], low=row['low'], vol=row['vol'])
            for i, row in kline.iterrows()]
    return bars


def test_find_bi():
    bars = read_daily()
    # 去除包含关系
    bars1 = []
    for bar in bars:
        if len(bars1) < 2:
            bars1.append(NewBar(symbol=bar.symbol, id=bar.id, freq=bar.freq,
                                dt=bar.dt, open=bar.open,
                                close=bar.close, high=bar.high, low=bar.low,
                                vol=bar.vol, elements=[bar]))
        else:
            k1, k2 = bars1[-2:]
            has_include, k3 = remove_include(k1, k2, bar)
            if has_include:
                bars1[-1] = k3
            else:
                bars1.append(k3)

    fxs = []
    for i in range(1, len(bars1) - 1):
        fx = check_fx(bars1[i - 1], bars1[i], bars1[i + 1])
        if isinstance(fx, FX):
            fxs.append(fx)


def get_user_signals(c: CZSC) -> OrderedDict:
    """在 CZSC 对象上计算信号，这个是标准函数，主要用于研究。
    实盘时可以按照自己的需要自定义计算哪些信号

    :param c: CZSC 对象
    :return: 信号字典
    """
    s = OrderedDict({"symbol": c.symbol, "dt": c.bars_raw[-1].dt, "close": c.bars_raw[-1].close})
    # 倒0，特指未确认完成笔
    # 倒1，倒数第1笔的缩写，表示第N笔
    # 倒2，倒数第2笔的缩写，表示第N-1笔
    # 倒3，倒数第3笔的缩写，表示第N-2笔
    # 以此类推
    for i in range(1, 3):
        s.update(get_s_three_bi(c, i))
    s.update(get_s_d0_bi(c))
    return s


def test_czsc_update():
    bars = read_daily()
    # 不计算任何信号
    c = CZSC(bars, max_bi_count=50)
    assert not c.signals

    # 计算信号
    c = CZSC(bars, max_bi_count=50, get_signals=get_default_signals, verbose=True)
    assert len(c.bi_list) == 50 and not c.last_bi_extend
    assert isinstance(c.signals, OrderedDict) and len(c.signals) == 38

    last_bi = c.bi_list[-1]
    assert len(last_bi.raw_bars) == 32 and last_bi.power_price == last_bi.power
    assert len(last_bi.fake_bis) == 11
    assert last_bi.fake_bis[0].direction == last_bi.fake_bis[-1].direction == last_bi.direction
    # 测试自定义信号
    c = CZSC(bars, max_bi_count=50, get_signals=get_user_signals, signals_n=20)
    assert len(c.signals) == 11
    assert len(c.signals_list) == 20
    assert c.signals_list[-1] == c.signals

    kline = [x.__dict__ for x in c.bars_raw]
    bi = [{'dt': x.fx_a.dt, "bi": x.fx_a.fx} for x in c.bi_list] + \
         [{'dt': c.bi_list[-1].fx_b.dt, "bi": c.bi_list[-1].fx_b.fx}]
    chart = kline_pro(kline, bi=bi, title="{} - {}".format(c.symbol, c.freq))
    file_html = "x.html"
    chart.render(file_html)
    os.remove(file_html)


def test_get_signals():

    def get_test_signals(c: CZSC) -> OrderedDict:
        s = OrderedDict({"symbol": c.symbol, "dt": c.bars_raw[-1].dt, "close": c.bars_raw[-1].close})
        s.update(get_s_d0_bi(c))
        return s

    bars = read_daily()
    # 不计算任何信号
    c = CZSC(bars, max_bi_count=50, get_signals=get_test_signals)
    assert c.signals['日线_倒0笔_方向'] == '向下_任意_任意_0'
    assert c.signals['日线_倒0笔_长度'] == '5到9根K线_任意_任意_0'
