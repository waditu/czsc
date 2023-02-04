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
from flask import Flask, render_template, request, jsonify
from czsc import home_path
from czsc.traders.base import CzscSignals, BarGenerator
from czsc.data import TsDataCache, get_symbols
from czsc.utils import freqs_sorted


app = Flask(__name__, static_folder="templates")
dc = TsDataCache(home_path)

symbols = get_symbols(dc, step='train')


def init_czsc_signals(freqs, counts, symbol):
    freq_map = {"1分钟": "1min", "5分钟": '5min', "15分钟": "15min", "30分钟": '30min',
                "60分钟": "60min", "日线": 'D', "周线": 'W', "月线": 'M'}
    freq = freqs[0]
    ts_code, asset = symbol.split('#')

    if freq in ['日线', '周线', '月线']:
        bars = dc.pro_bar(ts_code, start_date="20100101", end_date="20230101", freq=freq_map[freq],
                          asset=asset, adj='hfq', raw_bar=True)
    else:
        bars = dc.pro_bar_minutes(ts_code, sdt="20150101", edt="20230101", freq=freq_map[freq],
                                  asset=asset, adj='hfq', raw_bar=True)

    bg = BarGenerator(base_freq=freqs[0], freqs=freqs[1:], max_count=1000)
    for bar in bars[:-counts]:
        bg.update(bar)
    return CzscSignals(bg), bars[-counts:]


cs: CzscSignals = None
freqs: list = None
remain_bars: list = None


def bar_base():
    global cs, remain_bars
    bar = remain_bars.pop(0)
    cs.update_signals(bar)


@app.route("/")
def index():
    global cs, remain_bars, freqs

    freqs = request.args.get("freqs", '15分钟,60分钟,日线')
    freqs = freqs_sorted([f.strip() for f in freqs.split(',')])
    counts = int(request.args.get("counts", 300))
    symbol = request.args.get("symbol", symbols[0])
    cs, remain_bars = init_czsc_signals(freqs, counts, symbol)
    return render_template("index_human_replay.html")


@app.route("/next_bar")
def next_bar():
    bar_base()
    tabs = [cs.kas[freq].to_echarts().dump_options_with_quotes() for freq in freqs]
    return jsonify({"tabs": tabs})


@app.route("/barChart")
def get_bar_chart():
    # 这是一个测试，不要在生产环境使用
    bar_base()
    tabs = [cs.kas[freq].to_echarts().dump_options_with_quotes() for freq in freqs]
    return tabs[0]


@app.route("/symbols")
def get_symbols():
    return jsonify({"symbols": symbols})


@app.route("/evaluates", methods=['POST'])
def evaluates():
    # 暂时没有实现
    return jsonify({"tabs": []})


if __name__ == "__main__":
    app.jinja_env.auto_reload = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run()


