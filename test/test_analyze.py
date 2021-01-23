# coding: utf-8
import os
from czsc.analyze import *
from czsc.utils.echarts_plot import kline_pro

cur_path = os.path.split(os.path.realpath(__file__))[0]
# cur_path = r"D:\git_repo\offline\dealer\test\czsc"

def test_find_bi():
    file_kline = os.path.join(cur_path, "data/000001.SH_D.csv")
    kline = pd.read_csv(file_kline, encoding="utf-8")
    kline.loc[:, "dt"] = pd.to_datetime(kline.dt)
    bars = [RawBar(symbol=row['symbol'], open=row['open'], dt=row['dt'],
                   close=row['close'], high=row['high'], low=row['low'], vol=row['vol'])
            for _, row in kline.iterrows()]

    # 去除包含关系
    bars1 = []
    for bar in bars:
        if len(bars1) < 2:
            bars1.append(NewBar(symbol=bar.symbol, dt=bar.dt, open=bar.open,
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
    for i in range(1, len(bars1)-1):
        fx = check_fx(bars1[i-1], bars1[i], bars1[i+1])
        if isinstance(fx, FX):
            fxs.append(fx)

def test_ka_update():
    file_kline = os.path.join(cur_path, "data/000001.SH_D.csv")
    kline = pd.read_csv(file_kline, encoding="utf-8")
    kline.loc[:, "dt"] = pd.to_datetime(kline.dt)
    bars = [RawBar(symbol=row['symbol'], open=row['open'], dt=row['dt'],
                   close=row['close'], high=row['high'], low=row['low'], vol=row['vol'])
            for _, row in kline.iterrows()]
    c = CZSC(bars, freq="日线", max_count=1000)

    kline = [x.__dict__ for x in c.bars_raw]
    bi = [{'dt': x.fx_a.dt, "bi": x.fx_a.fx} for x in c.bi_list] + \
         [{'dt': c.bi_list[-1].fx_b.dt, "bi": c.bi_list[-1].fx_b.fx}]
    chart = kline_pro(kline, bi=bi, title="{} - {}".format(c.symbol, c.freq))
    chart.render("x.html")
