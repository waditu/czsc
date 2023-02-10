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
import json
import random
import pandas as pd
from flask import Flask, render_template, request, jsonify
from czsc import home_path
from czsc.traders.base import CzscSignals, BarGenerator
from czsc.data import TsDataCache, get_symbols
from czsc.utils import freqs_sorted

app = Flask(__name__, static_folder="templates")
dc = TsDataCache(home_path)

symbols = get_symbols(dc, step='train')
randoms = get_symbols(dc, step='train') + get_symbols(dc, step='index') + get_symbols(dc, step='etfs')


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
    counts += 10
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

    freqs = request.args.get("freqs", '1分钟,5分钟,15分钟,30分钟,60分钟,日线,周线,月线')
    freqs = freqs_sorted([f.strip() for f in freqs.split(',')])
    print(freqs)
    counts = int(request.args.get("counts", 300))
    symbol = request.args.get("symbol", random.choice(randoms))
    if symbol.lower() == 'random':
        symbol = random.choice(randoms)
    cs, remain_bars = init_czsc_signals(freqs, counts, symbol)
    return render_template("index_human_replay.html")


@app.route("/next_bar")
def next_bar():
    bar_base()
    tabs = [cs.kas[freq].to_echarts().dump_options_with_quotes() for freq in freqs]
    return jsonify({"tabs": tabs})


@app.route("/symbols")
def get_symbols():
    return jsonify({"symbols": ['random'] + symbols})


@app.route("/evaluates", methods=['POST'])
def evaluates():
    from pprint import pprint
    data = json.loads(request.get_data(as_text=True))
    pprint(data)

    def make_pair(op1, op2):
        assert op1['op'] in ["BL", "BS"] and op2['op'] in ["SL", "SS"]
        pair = {
            '交易方向': "多头" if op1['op'] == 'BL' else "空头",
            '开仓时间': op1['dt'],
            '平仓时间': op2['dt'],
            '开仓价格': op1['price'],
            '平仓价格': op2['price'],
            '持仓天数': (op2['dt'] - op1['dt']).total_seconds() / (24 * 3600),
            '盈亏比例': op2['price'] / op1['price'] - 1 if op1['op'] == 'BL' else 1 - op2['price'] / op1['price'],
        }
        # 盈亏比例 转换成以 BP 为单位的收益，1BP = 0.0001
        pair['盈亏比例'] = round(pair['盈亏比例'] * 10000, 2)
        return pair

    # k_data = [[x['open'], x['close'], x['low'], x['high']] for x in kline]
    ops = data['ops']
    operates = []
    last_op = None
    for op in ops:
        if not last_op:
            operates.append({'dt': pd.to_datetime(op['date']), 'price': op['kline']['value'][1], 'op': op['type']})
            last_op = op['type']
            continue

        if op['type'] != last_op:
            if op['type'] in ['SL', 'SS']:
                operates.append({'dt': pd.to_datetime(op['date']), 'price': op['kline']['value'][1], 'op': op['type']})

            # 开多 -> 开空，增加两条记录，先平多，再开空
            if op['type'] == 'BS':
                if last_op == 'BL':
                    operates.append({'dt': pd.to_datetime(op['date']), 'price': op['kline']['value'][1], 'op': "SL"})
                operates.append({'dt': pd.to_datetime(op['date']), 'price': op['kline']['value'][1], 'op': "BS"})

            # 开空 -> 开多，增加两条记录，先平空，再开多
            if op['type'] == 'BL':
                if last_op == 'BS':
                    operates.append({'dt': pd.to_datetime(op['date']), 'price': op['kline']['value'][1], 'op': "SS"})
                operates.append({'dt': pd.to_datetime(op['date']), 'price': op['kline']['value'][1], 'op': "BL"})

            last_op = op['type']

    pprint(operates)

    # 构成交易对
    pairs = []
    if len(operates) > 1:
        if len(operates) % 2 != 0:
            operates.pop()
        for _op1, _op2 in zip(operates[::2], operates[1::2]):
            pairs.append(make_pair(_op1, _op2))

    pprint(pairs)

    # 计算评价指标
    p = {"交易次数": len(pairs), '累计收益': 0, '单笔收益': 0,
         '盈利次数': 0, '累计盈利': 0, '单笔盈利': 0,
         '亏损次数': 0, '累计亏损': 0, '单笔亏损': 0,
         '平均持仓天数': 0, '胜率': 0, "累计盈亏比": 0, "单笔盈亏比": 0, "盈亏平衡点": 1}

    if len(pairs) > 0:
        p['累计收益'] = round(sum([x['盈亏比例'] for x in pairs]), 2)
        p['单笔收益'] = round(p['累计收益'] / p['交易次数'], 2)
        p['平均持仓天数'] = round(sum([x['持仓天数'] for x in pairs]) / len(pairs), 2)

        win_ = [x for x in pairs if x['盈亏比例'] >= 0]
        if len(win_) > 0:
            p['盈利次数'] = len(win_)
            p['累计盈利'] = sum([x['盈亏比例'] for x in win_])
            p['单笔盈利'] = round(p['累计盈利'] / p['盈利次数'], 4)
            p['胜率'] = round(p['盈利次数'] / p['交易次数'], 4)

        loss_ = [x for x in pairs if x['盈亏比例'] < 0]
        if len(loss_) > 0:
            p['亏损次数'] = len(loss_)
            p['累计亏损'] = sum([x['盈亏比例'] for x in loss_])
            p['单笔亏损'] = round(p['累计亏损'] / p['亏损次数'], 4)

            p['累计盈亏比'] = round(p['累计盈利'] / abs(p['累计亏损']), 4)
            p['单笔盈亏比'] = round(p['单笔盈利'] / abs(p['单笔亏损']), 4)

    p = {k: v for k, v in p.items() if k in ['交易次数', '累计收益', '单笔收益', '平均持仓天数', '胜率', '累计盈亏比', '单笔盈亏比', '盈亏平衡点']}
    return jsonify({"status": "ok", "evaluates": p, 'pairs': pairs, 'operates': operates})


if __name__ == "__main__":
    app.jinja_env.auto_reload = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(debug=True)
