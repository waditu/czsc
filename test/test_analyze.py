# coding: utf-8
from tqdm import tqdm
from czsc.analyze import *
from czsc.utils.io import read_pkl

cur_path = os.path.split(os.path.realpath(__file__))[0]


def test_find_bi():
    file_kline = os.path.join(cur_path, "data/000001.SH_D.csv")
    kline = pd.read_csv(file_kline, encoding="utf-8")
    kline.loc[:, "dt"] = pd.to_datetime(kline.dt)
    bars = [RawBar(symbol=row['symbol'], id=i, freq=Freq.F1, open=row['open'], dt=row['dt'],
                   close=row['close'], high=row['high'], low=row['low'], vol=row['vol'])
            for i, row in kline.iterrows()]

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
    for i in range(1, len(bars1)-1):
        fx = check_fx(bars1[i-1], bars1[i], bars1[i+1])
        if isinstance(fx, FX):
            fxs.append(fx)

def get_user_signals(c: CZSC) -> OrderedDict:
    """在 CZSC 对象上计算信号，这个是标准函数，主要用于研究。
    实盘时可以按照自己的需要自定义计算哪些信号

    :param c: CZSC 对象
    :return: 信号字典
    """
    freq: Freq = c.freq
    s = OrderedDict({"symbol": c.symbol, "dt": c.bars_raw[-1].dt, "close": c.bars_raw[-1].close})
    # 倒0，特指未确认完成笔
    # 倒1，倒数第1笔的缩写，表示第N笔
    # 倒2，倒数第2笔的缩写，表示第N-1笔
    # 倒3，倒数第3笔的缩写，表示第N-2笔
    # 以此类推

    default_signals = [
        Signal(k1=str(freq.value), k2="倒1笔", k3="三笔形态", v1="其他", v2='其他', v3='其他'),
        Signal(k1=str(freq.value), k2="倒2笔", k3="三笔形态", v1="其他", v2='其他', v3='其他'),
        Signal(k1=str(freq.value), k2="倒3笔", k3="三笔形态", v1="其他", v2='其他', v3='其他'),
        Signal(k1=str(freq.value), k2="倒4笔", k3="三笔形态", v1="其他", v2='其他', v3='其他'),
        Signal(k1=str(freq.value), k2="倒5笔", k3="三笔形态", v1="其他", v2='其他', v3='其他'),
        Signal(k1=str(freq.value), k2="倒6笔", k3="三笔形态", v1="其他", v2='其他', v3='其他'),
        Signal(k1=str(freq.value), k2="倒7笔", k3="三笔形态", v1="其他", v2='其他', v3='其他'),
    ]
    for signal in default_signals:
        s[signal.key] = signal.signal

    # 表里关系的定义参考：http://blog.sina.com.cn/s/blog_486e105c01007wc1.html
    min_ubi = min([x.low for x in c.bars_ubi])
    max_ubi = max([x.high for x in c.bars_ubi])
    if not c.bi_list:
        return s

    if (c.bi_list[-1].direction == Direction.Down and min_ubi >= c.bi_list[-1].low) \
            or (c.bi_list[-1].direction == Direction.Up and max_ubi <= c.bi_list[-1].high):
        bis = c.bi_list
    else:
        bis = c.bi_list[:-1]

    if not bis:
        return s

    signals = [
        check_three_bi(bis[-3:], freq, 1),
        check_three_bi(bis[-4:-1], freq, 2),
        check_three_bi(bis[-5:-2], freq, 3),
        check_three_bi(bis[-6:-3], freq, 4),
        check_three_bi(bis[-7:-4], freq, 5),
        check_three_bi(bis[-8:-5], freq, 6),
        check_three_bi(bis[-9:-6], freq, 7),
    ]

    for signal in signals:
        if "其他" in signal.signal:
            continue
        else:
            s[signal.key] = signal.value
    return s


def test_czsc_update():
    file_kline = os.path.join(cur_path, "data/000001.SH_D.csv")
    kline = pd.read_csv(file_kline, encoding="utf-8")
    kline.loc[:, "dt"] = pd.to_datetime(kline.dt)
    bars = [RawBar(symbol=row['symbol'], id=i, freq=Freq.D, open=row['open'], dt=row['dt'],
                   close=row['close'], high=row['high'], low=row['low'], vol=row['vol'])
            for i, row in kline.iterrows()]

    # 不计算任何信号
    c = CZSC(bars, max_bi_count=50)
    assert not c.signals

    # 计算信号
    c = CZSC(bars, max_bi_count=50, get_signals=get_default_signals)
    assert isinstance(c.signals, OrderedDict) and len(c.signals) == 30

    # 测试自定义信号
    c = CZSC(bars, max_bi_count=50, get_signals=get_user_signals)
    assert len(c.signals) == 10

    kline = [x.__dict__ for x in c.bars_raw]
    bi = [{'dt': x.fx_a.dt, "bi": x.fx_a.fx} for x in c.bi_list] + \
         [{'dt': c.bi_list[-1].fx_b.dt, "bi": c.bi_list[-1].fx_b.fx}]
    chart = kline_pro(kline, bi=bi, title="{} - {}".format(c.symbol, c.freq))
    file_html = "x.html"
    chart.render(file_html)
    os.remove(file_html)


def test_czsc_trader():
    bars = read_pkl(os.path.join(cur_path, "data/000001.XSHG_1MIN.pkl"))
    kg = KlineGenerator(max_count=3000, freqs=['1分钟', '5分钟', '15分钟', '30分钟', '60分钟', '日线'])
    for row in tqdm(bars[:-100], desc='init kg'):
        kg.update(row)

    ct = CzscTrader(kg, get_signals=get_default_signals, events=[])
    assert len(ct.s) == 171
    for row in tqdm(bars[-100:]):
        op = ct.check_operate(row)
        print(op)
    assert len(ct.s) == 171




