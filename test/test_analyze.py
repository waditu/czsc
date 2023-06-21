# coding: utf-8
import os
import zipfile
from tqdm import tqdm
import pandas as pd
from czsc.analyze import CZSC, RawBar, NewBar, remove_include, FX, check_fx, Direction, kline_pro
from czsc.enum import Freq
from collections import OrderedDict


cur_path = os.path.split(os.path.realpath(__file__))[0]


def read_1min():
    with zipfile.ZipFile(os.path.join(cur_path, 'data/000001.XSHG_1min.zip'), 'r') as z:
        f = z.open('000001.XSHG_1min.csv')
        data = pd.read_csv(f, encoding='utf-8')

    data['dt'] = pd.to_datetime(data['dt'])
    data['amount'] = data['close'] * data['vol']
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
    kline['amount'] = kline['close'] * kline['vol']

    kline.loc[:, "dt"] = pd.to_datetime(kline.dt)
    bars = [RawBar(symbol=row['symbol'], id=i, freq=Freq.D, open=row['open'], dt=row['dt'],
                   close=row['close'], high=row['high'], low=row['low'], vol=row['vol'], amount=row['amount'])
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
                                vol=bar.vol, amount=bar.amount, elements=[bar]))
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


def test_czsc_update():
    bars = read_daily()
    # 不计算任何信号
    c = CZSC(bars)
    assert not c.signals

    # 测试 ubi 属性
    ubi = c.ubi
    assert ubi['direction'] == Direction.Down
    assert ubi['high_bar'].dt < ubi['low_bar'].dt
    # 测试自定义信号
    c = CZSC(bars, get_signals=None)

    kline = [x.__dict__ for x in c.bars_raw]
    bi = [{'dt': x.fx_a.dt, "bi": x.fx_a.fx} for x in c.bi_list] + \
         [{'dt': c.bi_list[-1].fx_b.dt, "bi": c.bi_list[-1].fx_b.fx}]
    chart = kline_pro(kline, bi=bi, title="{} - {}".format(c.symbol, c.freq))
    file_html = "x.html"
    chart.render(file_html)
    os.remove(file_html)
