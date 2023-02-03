# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/7/12 14:22
describe: CZSC 逐K线播放
https://pyecharts.org/#/zh-cn/web_flask
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '..')
from tqdm import tqdm
from flask import Flask, render_template, request, jsonify
from czsc import home_path
from czsc.traders.base import CzscSignals, BarGenerator
from czsc.data import TsDataCache, get_symbols
from czsc.utils import freqs_sorted


app = Flask(__name__, static_folder="templates")
dc = TsDataCache(home_path)

symbols = get_symbols(dc, step='train')


def init_czsc_signals(freqs, counts, symbol):

    def __get_freq_bars(freq):
        ts_code, asset = symbol.split('#')
        bars = dc.pro_bar_minutes(ts_code, sdt="20150101", edt="20220712", freq='5min',
                                  asset=asset, adj='qfq', raw_bar=True)
        _bg = BarGenerator(base_freq='5分钟', freqs=[freq], max_count=100000)
        for _bar in tqdm(bars[:-1]):
            _bg.update(_bar)
        return _bg.bars[freq]

    _bars = __get_freq_bars(freqs[0])
    bg = BarGenerator(base_freq=freqs[0], freqs=freqs[1:], max_count=1000)
    for bar in _bars[:-counts]:
        bg.update(bar)
    return CzscSignals(bg), _bars[-counts:]


cs: CzscSignals = None
remain_bars: list = None


def bar_base():
    global cs, remain_bars
    bar = remain_bars.pop(0)
    cs.update_signals(bar)


@app.route("/")
def index():
    freqs = request.args.get("freqs", '15分钟，60分钟，日线')
    freqs = freqs_sorted([f.strip() for f in freqs.split('，')])
    counts = request.args.get("counts", 300)
    symbol = symbols[0]
    global cs, remain_bars
    cs, remain_bars = init_czsc_signals(freqs, counts, symbol)
    return render_template("index.html")


@app.route("/next_bar")
def next_bar():
    bar_base()
    tabs = [cs.kas[freq].to_echarts().dump_options_with_quotes() for freq in cs.freqs]
    return jsonify({"tabs": tabs})


@app.route("/barChart")
def get_bar_chart():
    # 这是一个测试，不要在生产环境使用
    bar_base()
    tabs = [cs.kas[freq].to_echarts().dump_options_with_quotes() for freq in cs.freqs]
    return tabs[0]


@app.route("/symbols")
def get_symbols():
    return jsonify({"symbols": symbols})


@app.route("/evaluates", methods=['POST'])
def evaluates():
    # 暂时没有实现
    return jsonify({"tabs": []})


if __name__ == "__main__":
    app.run()


