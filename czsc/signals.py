# coding: utf-8
from .analyze import KlineAnalyze, find_zs

def get_fx_signals(ka):
    """计算分型特征"""
    s = {
        "收于MA5上方": False,
        "收于MA5下方": False,
        "收于MA20上方": False,
        "收于MA20下方": False,
        "收于MA120上方": False,
        "收于MA120下方": False,
        "最后一个分型为顶": False,
        "最后一个分型为底": False,
        "顶分型后有效跌破MA5": False,
        "底分型后有效升破MA5": False,
        "最近三K线形态": None,
    }

    last_tri = ka.kline_new[-3:]
    if len(last_tri) == 3:
        if last_tri[-3]['high'] < last_tri[-2]['high'] > last_tri[-1]['high']:
            s["最近三K线形态"] = "g"
        elif last_tri[-3]['low'] > last_tri[-2]['low'] < last_tri[-1]['low']:
            s["最近三K线形态"] = "d"
        elif last_tri[-3]['low'] > last_tri[-2]['low'] > last_tri[-1]['low']:
            s["最近三K线形态"] = "down"
        elif last_tri[-3]['high'] < last_tri[-2]['high'] < last_tri[-1]['high']:
            s["最近三K线形态"] = "up"

    last_klines_ = [dict(x) for x in ka.kline_raw[-10:]]
    if len(last_klines_) != 10:
        return s

    last_ma_ = ka.ma[-10:]
    for i, x in enumerate(last_klines_):
        assert last_ma_[i]['dt'] == x['dt'], "{}：计算均线错误".format(ka.name)
        last_klines_[i].update(last_ma_[i])

    last_k = last_klines_[-1]
    if last_k['close'] >= last_k['ma5']:
        s["收于MA5上方"] = True
    else:
        s["收于MA5下方"] = True

    if last_k['close'] >= last_k['ma20']:
        s["收于MA20上方"] = True
    else:
        s["收于MA20下方"] = True

    if last_k['close'] >= last_k['ma120']:
        s["收于MA120上方"] = True
    else:
        s["收于MA120下方"] = True

    last_fx = ka.fx_list[-1]
    after_klines = [x for x in last_klines_ if x['dt'] >= last_fx['dt']]
    if last_fx['fx_mark'] == 'g':
        s["最后一个分型为顶"] = True
        # 顶分型有效跌破MA5的三种情况：1）分型右侧第一根K线收于MA5下方；2）连续5根K线最低价下穿MA5；3）连续3根K线收盘价收于MA5下方
        if after_klines[1]['close'] < after_klines[1]['ma5'] \
                or sum([1 for x in after_klines[-5:] if x['low'] < x['ma5']]) >= 5 \
                or sum([1 for x in after_klines[-3:] if x['close'] < x['ma5']]) >= 3:
            s['顶分型后有效跌破MA5'] = True

    if last_fx['fx_mark'] == 'd':
        s["最后一个分型为底"] = True
        # 底分型后有效升破MA5的三种情况：1）分型右侧第一根K线收于MA5上方；2）连续5根K线最高价上穿MA5；3）连续3根K线收盘价收于MA5上方
        if after_klines[1]['close'] > after_klines[1]['ma5'] \
                or sum([1 for x in after_klines[-5:] if x['high'] > x['ma5']]) >= 5 \
                or sum([1 for x in after_klines[-3:] if x['close'] > x['ma5']]) >= 3:
            s['底分型后有效升破MA5'] = True
    freq = ka.name
    return {freq + k: v for k, v in s.items()}


def get_bi_signals(ka):
    """计算笔信号"""
    s = {
        "最后一个未确认的笔标记为底": False,
        "最后一个未确认的笔标记为顶": False,
        "最后一个已确认的笔标记为底": False,
        "最后一个已确认的笔标记为顶": False,
        "向上笔走势延伸": False,
        "向上笔现顶分型": False,
        "向下笔走势延伸": False,
        "向下笔现底分型": False,

        "最后一个笔中枢上沿": 0,
        "最后一个笔中枢下沿": 0,
        "收于笔中枢上方且有三买": False,
        "收于笔中枢上方且无三买": False,
        "收于笔中枢下方且有三卖": False,
        "收于笔中枢下方且无三卖": False,

        '笔同级别分解买': False,
        '笔同级别分解卖': False,

        '类趋势顶背驰（笔）': False,
        '类趋势底背驰（笔）': False,
        '类盘整顶背驰（笔）': False,
        '类盘整底背驰（笔）': False,

        # '趋势顶背驰（笔）': False,
        # '趋势底背驰（笔）': False,
        # '盘整顶背驰（笔）': False,
        # '盘整底背驰（笔）': False,
    }

    # ------------------------------------------------------------------------------------------------------------------
    if len(ka.bi_list) > 2:
        assert ka.bi_list[-1]['fx_mark'] in ['d', 'g']
        if ka.bi_list[-1]['fx_mark'] == 'd':
            s["最后一个未确认的笔标记为底"] = True
        else:
            s["最后一个未确认的笔标记为顶"] = True

        assert ka.bi_list[-2]['fx_mark'] in ['d', 'g']
        if ka.bi_list[-2]['fx_mark'] == 'd':
            s["最后一个已确认的笔标记为底"] = True
        else:
            s["最后一个已确认的笔标记为顶"] = True

    # ------------------------------------------------------------------------------------------------------------------
    last_bi = ka.bi_list[-1]
    if last_bi['fx_mark'] == 'd' and ka.fx_list[-1]['fx_mark'] == 'd':
        s["向上笔走势延伸"] = True
    elif last_bi['fx_mark'] == 'd' and ka.fx_list[-1]['fx_mark'] == 'g':
        s["向上笔现顶分型"] = True
    elif last_bi['fx_mark'] == 'g' and ka.fx_list[-1]['fx_mark'] == 'g':
        s['向下笔走势延伸'] = True
    elif last_bi['fx_mark'] == 'g' and ka.fx_list[-1]['fx_mark'] == 'd':
        s['向下笔现底分型'] = True
    else:
        raise ValueError("笔状态识别错误，最后一个笔标记：%s，"
                         "最后一个分型标记%s" % (str(last_bi), str(ka.fx_list[-1])))

    # ------------------------------------------------------------------------------------------------------------------
    bis = ka.bi_list[-30:]
    if len(bis) >= 6:
        if bis[-1]['fx_mark'] == 'd' and bis[-1]['bi'] < bis[-3]['bi'] and bis[-2]['bi'] < bis[-4]['bi']:
            zs1 = {"start_dt": bis[-2]['dt'], "end_dt": bis[-1]['dt'], "direction": "down"}
            zs2 = {"start_dt": bis[-4]['dt'], "end_dt": bis[-3]['dt'], "direction": "down"}
            if ka.is_bei_chi(zs1, zs2, mode="bi", adjust=0.9):
                # 类趋势
                if bis[-2]['bi'] < bis[-5]['bi']:
                    s['类趋势底背驰（笔）'] = True
                else:
                    s['类盘整底背驰（笔）'] = True

        if bis[-1]['fx_mark'] == 'g' and bis[-1]['bi'] > bis[-3]['bi'] and bis[-2]['bi'] > bis[-4]['bi']:
            zs1 = {"start_dt": bis[-2]['dt'], "end_dt": bis[-1]['dt'], "direction": "up"}
            zs2 = {"start_dt": bis[-4]['dt'], "end_dt": bis[-3]['dt'], "direction": "up"}
            if ka.is_bei_chi(zs1, zs2, mode="bi", adjust=0.9):
                # 类趋势
                if bis[-2]['bi'] > bis[-5]['bi']:
                    s['类趋势顶背驰（笔）'] = True
                else:
                    s['类盘整顶背驰（笔）'] = True

    # ------------------------------------------------------------------------------------------------------------------
    bi_zs = find_zs(bis)
    if bi_zs:
        last_bi_zs = bi_zs[-1]
        s["最后一个笔中枢上沿"] = last_bi_zs['ZG']
        s["最后一个笔中枢下沿"] = last_bi_zs['ZD']

        last_k = ka.kline_new[-1]
        if last_k['close'] > last_bi_zs['ZG']:
            if last_bi_zs.get("third_buy", 0):
                s["收于笔中枢上方且有三买"] = True
            else:
                s["收于笔中枢上方且无三买"] = True

        if last_k['close'] < last_bi_zs['ZD']:
            if last_bi_zs.get("third_sell", 0):
                s["收于笔中枢下方且有三卖"] = True
            else:
                s["收于笔中枢下方且无三卖"] = True

    # ------------------------------------------------------------------------------------------------------------------
    if len(bis) >= 6:
        if bis[-1]['fx_mark'] == 'd' and bis[-2]['bi'] > bis[-5]['bi']:
            if bis[-1]['bi'] > bis[-3]['bi'] or s['类盘整底背驰（笔）']:
                s['笔同级别分解买'] = True

        if bis[-1]['fx_mark'] == 'g' and bis[-2]['bi'] < bis[-5]['bi']:
            if bis[-1]['bi'] < bis[-3]['bi'] or s['类盘整顶背驰（笔）']:
                s['笔同级别分解卖'] = True

    freq = ka.name
    return {freq + k: v for k, v in s.items()}


def get_xd_signals(ka, use_zs=False):
    """计算线段方向特征"""
    s = {
        "最后一个未确认的线段标记为底": False,
        "最后一个未确认的线段标记为顶": False,
        "最后一个已确认的线段标记为底": False,
        "最后一个已确认的线段标记为顶": False,

        "最后一个线段内部笔标记数量": 0,
        "最近上一线段内部笔标记数量": 0,

        '类趋势顶背驰（段）': False,
        '类趋势底背驰（段）': False,
        '类盘整顶背驰（段）': False,
        '类盘整底背驰（段）': False,

        "同级别分解买": False,
        "同级别分解卖": False,

        # '趋势顶背驰（段）': False,
        # '趋势底背驰（段）': False,
        # '盘整顶背驰（段）': False,
        # '盘整底背驰（段）': False,
        # "最后一个中枢上沿": 0,
        # "最后一个中枢下沿": 0,
    }

    # ------------------------------------------------------------------------------------------------------------------
    assert ka.xd_list[-1]['fx_mark'] in ['g', 'd']
    if ka.xd_list[-1]['fx_mark'] == 'd':
        s["最后一个未确认的线段标记为底"] = True
    else:
        s["最后一个未确认的线段标记为顶"] = True

    assert ka.xd_list[-2]['fx_mark'] in ['g', 'd']
    if ka.xd_list[-2]['fx_mark'] == 'd':
        s["最后一个已确认的线段标记为底"] = True
    else:
        s["最后一个已确认的线段标记为顶"] = True

    # ------------------------------------------------------------------------------------------------------------------
    bi_after = [x for x in ka.bi_list[-60:] if x['dt'] >= ka.xd_list[-1]['dt']]
    s["最后一个线段内部笔标记数量"] = len(bi_after)
    s["最近上一线段内部笔标记数量"] = len([x for x in ka.bi_list[-100:]
                              if ka.xd_list[-2]['dt'] <= x['dt'] <= ka.xd_list[-1]['dt']])

    # ------------------------------------------------------------------------------------------------------------------
    xds = ka.xd_list[-50:]
    if len(xds) >= 6:
        if xds[-1]['fx_mark'] == 'd' and xds[-1]['xd'] < xds[-3]['xd'] and xds[-2]['xd'] < xds[-4]['xd']:
            zs1 = {"start_dt": xds[-2]['dt'], "end_dt": xds[-1]['dt'], "direction": "down"}
            zs2 = {"start_dt": xds[-4]['dt'], "end_dt": xds[-3]['dt'], "direction": "down"}
            if ka.is_bei_chi(zs1, zs2, mode="xd", adjust=0.9):
                # 类趋势
                if xds[-2]['xd'] < xds[-5]['xd']:
                    s['类趋势底背驰（段）'] = True
                else:
                    s['类盘整底背驰（段）'] = True

        if xds[-1]['fx_mark'] == 'g' and xds[-1]['xd'] > xds[-3]['xd'] and xds[-2]['xd'] > xds[-4]['xd']:
            zs1 = {"start_dt": xds[-2]['dt'], "end_dt": xds[-1]['dt'], "direction": "up"}
            zs2 = {"start_dt": xds[-4]['dt'], "end_dt": xds[-3]['dt'], "direction": "up"}
            if ka.is_bei_chi(zs1, zs2, mode="xd", adjust=0.9):
                # 类趋势
                if xds[-2]['xd'] > xds[-5]['xd']:
                    s['类趋势顶背驰（段）'] = True
                else:
                    s['类盘整顶背驰（段）'] = True

    # ------------------------------------------------------------------------------------------------------------------
    last_xd_inside = [x for x in ka.bi_list[-60:] if x['dt'] >= xds[-1]['dt']]
    if len(xds) >= 6 and len(last_xd_inside) >= 6:
        if xds[-1]['fx_mark'] == 'g' and xds[-2]['xd'] < xds[-5]['xd']:
            if xds[-1]['xd'] < xds[-3]['xd'] or s['类盘整底背驰（段）']:
                s['同级别分解买'] = True

        if xds[-1]['fx_mark'] == 'd' and xds[-2]['xd'] > xds[-5]['xd']:
            if xds[-1]['xd'] > xds[-3]['xd'] or s['类盘整顶背驰（段）']:
                s['同级别分解卖'] = True

    # ------------------------------------------------------------------------------------------------------------------
    freq = ka.name
    return {freq + k: v for k, v in s.items()}


class Signals:
    def __init__(self, klines):
        """
        :param klines: dict
            K线数据
        """
        self.klines = klines
        self.kas = {k: KlineAnalyze(self.klines[k], name=k, ma_params=(5, 20, 120), max_xd_len=20, verbose=False)
                    for k in self.klines.keys()}
        self.symbol = self.kas["1分钟"].symbol
        self.end_dt = self.kas["1分钟"].end_dt
        self.latest_price = self.kas["1分钟"].latest_price

    def __repr__(self):
        return "<Signals of {}>".format(self.symbol)

    def signals(self):
        """计算交易决策需要的状态信息"""
        s = {"symbol": self.symbol}

        for k in self.kas.keys():
            if k in ['周线', '日线', '60分钟', '30分钟', '15分钟', '5分钟', '1分钟']:
                s.update(get_fx_signals(self.kas[k]))

            if k in ['周线', '日线', '60分钟', '30分钟', '15分钟', '5分钟', '1分钟']:
                s.update(get_bi_signals(self.kas[k]))

            if k in ['日线', '60分钟', '30分钟', '15分钟', '5分钟', '1分钟']:
                s.update(get_xd_signals(self.kas[k]))
        return s

    def update_kas(self, klines_one):
        for freq, klines_ in klines_one.items():
            k = klines_[-1]
            self.kas[freq].update(k)

        self.symbol = self.kas["1分钟"].symbol
        self.end_dt = self.kas["1分钟"].end_dt
        self.latest_price = self.kas["1分钟"].latest_price
