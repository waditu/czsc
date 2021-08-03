# coding: utf-8
import zipfile
from tqdm import tqdm
from czsc.analyze import *
from czsc.enum import Freq
from czsc.signals import get_default_signals, get_s_three_bi

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
    s = OrderedDict({"symbol": c.symbol, "dt": c.bars_raw[-1].dt, "close": c.bars_raw[-1].close})
    # 倒0，特指未确认完成笔
    # 倒1，倒数第1笔的缩写，表示第N笔
    # 倒2，倒数第2笔的缩写，表示第N-1笔
    # 倒3，倒数第3笔的缩写，表示第N-2笔
    # 以此类推
    for i in range(1, 8):
        s.update(get_s_three_bi(c, i))
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
    assert isinstance(c.signals, OrderedDict) and len(c.signals) == 31

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
    bars = read_1min()
    kg = KlineGenerator(max_count=3000, freqs=['1分钟', '5分钟', '15分钟', '30分钟', '60分钟', '日线'])
    for row in tqdm(bars[:-100], desc='init kg'):
        kg.update(row)

    ct = CzscTrader(kg, get_signals=get_default_signals, events=[])
    assert len(ct.s) == 177
    for row in tqdm(bars[-100:]):
        op = ct.check_operate(row)
        print(op)
    assert len(ct.s) == 177




