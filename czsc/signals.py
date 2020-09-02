# coding: utf-8
from .analyze import KlineAnalyze, find_zs

def check_jing(fd1, fd2, fd3, fd4, fd5):
    """检查最近5个分段走势是否构成井

    井的定义：
        12345，五段，是构造井的基本形态，形成井的位置肯定是5，而5出井的
        前提条件是对于向上5至少比3和1其中之一高，向下反过来; 并且，234
        构成一个中枢。

        井只有两类，大井和小井（以向上为例）：
        大井对应的形式是：12345向上，5最高3次之1最低，力度上1大于3，3大于5；
        小井对应的形式是：
            1：12345向上，3最高5次之1最低，力度上5的力度比1小，注意这时候
               不需要再考虑5和3的关系了，因为5比3低，所以不需要考虑力度。
            2：12345向上，5最高3次之1最低，力度上1大于5，5大于3。

        小井的构造，关键是满足5一定至少大于1、3中的一个。
        注意有一种情况不归为井：就是12345向上，1的力度最小，5的力度次之，3的力度最大此类不算井，
        因为345后面必然还有走势在67的时候才能再判断，个中道理各位好好体会。


    fd 为 dict 对象，表示一段走势，可以是笔、线段，样例如下：

    fd = {
        "start_dt": "",
        "end_dt": "",
        "power": 0,         # 力度
        "direction": "up",
        "high": 0,
        "low": 0,
        "mode": "bi"
    }

    """
    assert fd1['direction'] == fd3['direction'] == fd5['direction']
    assert fd2['direction'] == fd4['direction']
    direction = fd1['direction']

    zs_g = min(fd2['high'], fd3['high'], fd4['high'])
    zs_d = max(fd2['low'], fd3['low'], fd4['low'])

    jing = "没有出井"
    if zs_d < zs_g:
        if direction == 'up' and fd5["high"] > min(fd3['high'], fd1['high']):

            # 大井对应的形式是：12345向上，5最高3次之1最低，力度上1大于3，3大于5
            if fd5["high"] > fd3['high'] > fd1['high'] and fd5['power'] < fd3['power'] < fd1['power']:
                jing = "向上大井"

            # 第一种小井：12345向上，3最高5次之1最低，力度上5的力度比1小
            if fd1['high'] < fd5['high'] < fd3['high'] and fd5['power'] < fd1['power']:
                jing = "向上小井"

            # 第二种小井：12345向上，5最高3次之1最低，力度上1大于5，5大于3
            if fd5["high"] > fd3['high'] > fd1['high'] and fd1['power'] > fd5['power'] > fd3['power']:
                jing = "向上小井"

        if direction == 'down' and fd5["low"] < max(fd3['low'], fd1['low']):

            # 大井对应的形式是：12345向下，5最低3次之1最高，力度上1大于3，3大于5；
            if fd5['low'] < fd3['low'] < fd1['low'] and fd5['power'] < fd3['power'] < fd1['power']:
                jing = "向下大井"

            # 第一种小井：12345向下，3最低5次之1最高，力度上5的力度比1小
            if fd1["low"] > fd5['low'] > fd3['low'] and fd5['power'] < fd1['power']:
                jing = "向下小井"

            # 第二种小井：12345向下，5最低3次之1最高，力度上1大于5，5大于3
            if fd3["low"] > fd5['low'] > fd1['low'] and fd1['power'] > fd5['power'] > fd3['power']:
                jing = "向下小井"

    return jing


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


def get_fx_signals_v1(ka):
    """计算分型特征"""
    s = {
        "SFX01_收于MA5上方": None,
        "SFX02_收于MA20上方": None,
        "SFX03_收于MA120上方": None,
        "SFX04_最近一个分型类型": None,
        "SFX05_有效跌破MA5": None,
        "SFX06_有效升破MA5": None,
    }

    last_klines_ = [dict(x) for x in ka.kline_raw[-10:]]
    last_ma_ = ka.ma[-10:]
    for i, x in enumerate(last_klines_):
        assert last_ma_[i]['dt'] == x['dt'], "{}：计算均线错误".format(ka.name)
        last_klines_[i].update(last_ma_[i])

    last_k = last_klines_[-1]
    s["SFX01_收于MA5上方"] = True if last_k['close'] >= last_k['ma5'] > 0 else False
    s["SFX02_收于MA20上方"] = True if last_k['close'] >= last_k['ma20'] > 0 else False
    s["SFX03_收于MA120上方"] = True if last_k['close'] >= last_k['ma120'] > 0 else False
    s["SFX04_最近一个分型类型"] = ka.fx_list[-1]['fx_mark']

    if sum([1 for x in last_klines_[-5:] if x['low'] < x['ma5']]) >= 5 \
            or sum([1 for x in last_klines_[-3:] if x['close'] < x['ma5']]) >= 3:
        s["SFX05_有效跌破MA5"] = True

    if sum([1 for x in last_klines_[-5:] if x['high'] > x['ma5']]) >= 5 \
            or sum([1 for x in last_klines_[-3:] if x['close'] > x['ma5']]) >= 3:
        s["SFX06_有效升破MA5"] = True

    freq = ka.name
    return {freq + "_" + k: v for k, v in s.items()}


def get_bi_signals_v1(ka):
    """计算笔信号"""
    s = {
        "SBI01_最近一个未确认的笔标记类型": None,
        "SBI02_最近一个已确认的笔标记类型": None,
        "SBI03_最近一笔不创新高": False,
        "SBI04_最近一笔不创新低": False,

        'SBI05_最近一笔进入类盘整顶背驰段': None,
        'SBI06_最近一笔进入类盘整底背驰段': None,
        'SBI07_最近一笔进入类趋势顶背驰段': None,
        'SBI08_最近一笔进入类趋势底背驰段': None,

        "SBI09_收盘价相对于最近笔中枢位置": None,  # 上面（1）、内部（0）、下面（-1）
        "SBI10_最近笔中枢出现三买": False,
        "SBI11_最近笔中枢出现三卖": False,
    }

    # ------------------------------------------------------------------------------------------------------------------
    if len(ka.bi_list) > 3:
        s["SBI01_最近一个未确认的笔标记类型"] = ka.bi_list[-1]['fx_mark']
        s["SBI02_最近一个已确认的笔标记类型"] = ka.bi_list[-2]['fx_mark']
        if ka.bi_list[-1]['fx_mark'] == 'g' and ka.bi_list[-1]['bi'] < ka.bi_list[-3]['bi']:
            s["SBI03_最近一笔不创新高"] = True

        if ka.bi_list[-1]['fx_mark'] == 'd' and ka.bi_list[-1]['bi'] > ka.bi_list[-3]['bi']:
            s["SBI04_最近一笔不创新低"] = True

    # ------------------------------------------------------------------------------------------------------------------
    bis = ka.bi_list[-30:]
    if len(bis) >= 6:
        if bis[-1]['fx_mark'] == 'd' and bis[-1]['bi'] < bis[-3]['bi'] and bis[-2]['bi'] < bis[-4]['bi']:
            zs1 = {"start_dt": bis[-2]['dt'], "end_dt": bis[-1]['dt'], "direction": "down"}
            zs2 = {"start_dt": bis[-4]['dt'], "end_dt": bis[-3]['dt'], "direction": "down"}
            if ka.is_bei_chi(zs1, zs2, mode="bi", adjust=0.9):
                # 类趋势
                if bis[-2]['bi'] < bis[-5]['bi']:
                    s['SBI08_最近一笔进入类趋势底背驰段'] = True
                else:
                    s['SBI06_最近一笔进入类盘整底背驰段'] = True

        if bis[-1]['fx_mark'] == 'g' and bis[-1]['bi'] > bis[-3]['bi'] and bis[-2]['bi'] > bis[-4]['bi']:
            zs1 = {"start_dt": bis[-2]['dt'], "end_dt": bis[-1]['dt'], "direction": "up"}
            zs2 = {"start_dt": bis[-4]['dt'], "end_dt": bis[-3]['dt'], "direction": "up"}
            if ka.is_bei_chi(zs1, zs2, mode="bi", adjust=0.9):
                # 类趋势
                if bis[-2]['bi'] > bis[-5]['bi']:
                    s['SBI07_最近一笔进入类趋势顶背驰段'] = True
                else:
                    s['SBI05_最近一笔进入类盘整顶背驰段'] = True

        bi_zs = find_zs(bis)
        if bi_zs:
            last_bi_zs = bi_zs[-1]
            last_k = ka.kline_new[-1]
            if last_k['close'] > last_bi_zs['ZG']:
                s['SBI09_收盘价相对于最近笔中枢位置'] = 1
            elif last_k['close'] < last_bi_zs['ZD']:
                s['SBI09_收盘价相对于最近笔中枢位置'] = -1
            else:
                s['SBI09_收盘价相对于最近笔中枢位置'] = 0

            if bis[-1]['fx_mark'] == 'd' and bis[-1]['bi'] > last_bi_zs['ZG']:
                s["SBI10_最近笔中枢出现三买"] = True

            if bis[-1]['fx_mark'] == 'g' and bis[-1]['bi'] < last_bi_zs['ZD']:
                s["SBI11_最近笔中枢出现三卖"] = True

    freq = ka.name
    return {freq + "_" + k: v for k, v in s.items()}


def get_xd_signals_v1(ka, use_zs=False):
    """计算线段方向特征"""
    s = {
        "SXD01_最近一个未确认的线段标记类型": None,
        "SXD02_最近一个已确认的线段标记类型": None,

        "SXD03_最近一个线段内部笔标记数量": 0,
        "SXD04_最近上一线段内部笔标记数量": 0,

        'SXD05_最近一个线段进入类趋势顶背驰段': False,
        'SXD06_最近一个线段进入类趋势底背驰段': False,
        'SXD07_最近一个线段进入类盘整顶背驰段': False,
        'SXD08_最近一个线段进入类盘整底背驰段': False,

        "SXD09_最近向下线段不创新低": False,
        "SXD10_最近向上线段不创新高": False,
        "SXD11_最近两个向下线段有价格重叠区间": False,
        "SXD12_最近两个向上线段有价格重叠区间": False,
    }

    # ------------------------------------------------------------------------------------------------------------------
    if len(ka.xd_list) >= 2:
        s["SXD01_最近一个未确认的线段标记类型"] = ka.xd_list[-1]['fx_mark']
        s["SXD02_最近一个已确认的线段标记类型"] = ka.xd_list[-2]['fx_mark']

        bi1_ = [x for x in ka.bi_list[-30:] if x['dt'] >= ka.xd_list[-1]['dt']]
        s["SXD03_最近一个线段内部笔标记数量"] = len(bi1_)
        bi2_ = [x for x in ka.bi_list[-60:] if ka.xd_list[-2]['dt'] <= x['dt'] <= ka.xd_list[-1]['dt']]
        s["SXD04_最近上一线段内部笔标记数量"] = len(bi2_)

    # ------------------------------------------------------------------------------------------------------------------
    xds = ka.xd_list[-50:]
    if len(xds) >= 6:
        if xds[-1]['fx_mark'] == 'd' and xds[-1]['xd'] < xds[-3]['xd'] and xds[-2]['xd'] < xds[-4]['xd']:
            zs1 = {"start_dt": xds[-2]['dt'], "end_dt": xds[-1]['dt'], "direction": "down"}
            zs2 = {"start_dt": xds[-4]['dt'], "end_dt": xds[-3]['dt'], "direction": "down"}
            if ka.is_bei_chi(zs1, zs2, mode="xd", adjust=0.9):
                # 类趋势
                if xds[-2]['xd'] < xds[-5]['xd']:
                    s['SXD06_最近一个线段进入类趋势底背驰段'] = True
                else:
                    s['SXD08_最近一个线段进入类盘整底背驰段'] = True

        if xds[-1]['fx_mark'] == 'g' and xds[-1]['xd'] > xds[-3]['xd'] and xds[-2]['xd'] > xds[-4]['xd']:
            zs1 = {"start_dt": xds[-2]['dt'], "end_dt": xds[-1]['dt'], "direction": "up"}
            zs2 = {"start_dt": xds[-4]['dt'], "end_dt": xds[-3]['dt'], "direction": "up"}
            if ka.is_bei_chi(zs1, zs2, mode="xd", adjust=0.9):
                # 类趋势
                if xds[-2]['xd'] > xds[-5]['xd']:
                    s['SXD05_最近一个线段进入类趋势顶背驰段'] = True
                else:
                    s['SXD07_最近一个线段进入类盘整顶背驰段'] = True

    # ------------------------------------------------------------------------------------------------------------------
    last_xd_inside = [x for x in ka.bi_list[-60:] if x['dt'] >= xds[-1]['dt']]
    if len(xds) >= 6 and len(last_xd_inside) >= 4:
        if xds[-1]['fx_mark'] == 'g':
            min_bi = min(x['bi'] for x in last_xd_inside if x['fx_mark'] == 'd')
            if min_bi > xds[-2]['xd']:
                s["SXD09_最近向下线段不创新低"] = True
            if xds[-1]['xd'] > xds[-4]['xd']:
                s['SXD12_最近两个向上线段有价格重叠区间'] = True

        if xds[-1]['fx_mark'] == 'd':
            max_bi = max(x['bi'] for x in last_xd_inside if x['fx_mark'] == 'g')
            if max_bi < xds[-2]['xd']:
                s["SXD10_最近向上线段不创新高"] = True
            if xds[-1]['xd'] < xds[-4]['xd']:
                s["SXD11_最近两个向下线段有价格重叠区间"] = True

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
        self.kas = {k: KlineAnalyze(self.klines[k], name=k, min_bi_k=5,
                                    ma_params=(5, 20, 120),
                                    max_raw_len=5000, verbose=False)
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
