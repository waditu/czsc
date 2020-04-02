# coding: utf-8
import os
import json
import requests
import time
import pandas as pd
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from chan import SolidAnalyze

# 企业微信群聊机器人 web hook
hook = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=******"
mob = "***"  # mob是申请JQData时所填写的手机号
pwd = "***"  # Password为聚宽官网登录密码，新申请用户默认为手机号后6位

# 聚宽数据 API
url = "https://dataapi.joinquant.com/apis"


def get_token():
    """获取调用凭证"""
    body = {
        "method": "get_current_token",
        "mob": mob,  # mob是申请JQData时所填写的手机号
        "pwd": pwd,  # Password为聚宽官网登录密码，新申请用户默认为手机号后6位
    }
    response = requests.post(url, data=json.dumps(body))
    token = response.text
    return token


def push_msg(msg_type, content):
    """推送消息到企业微信群

    content格式参考： https://work.weixin.qq.com/api/doc/90000/90136/91770
    """
    data = {"msgtype": msg_type, msg_type: content}
    requests.post(hook, data=json.dumps(data))


def text2df(text):
    rows = [x.split(",") for x in text.strip().split('\n')]
    df = pd.DataFrame(rows[1:], columns=rows[0])
    return df


def get_kline(symbol, end_date, freq, count=3000):
    # 1m, 5m, 15m, 30m, 60m, 120m, 1d, 1w, 1M
    freq_convert = {"1min": "1m", "5min": '5m', '15min': '15m',
                    "30min": "30m", "60min": '60m', "D": "1d", "W": '1w'}
    if "-" not in end_date:
        end_date = datetime.strptime(end_date, "%Y%m%d").strftime("%Y-%m-%d")

    data = {
        "method": "get_price",
        "token": get_token(),
        "code": symbol,
        "count": count,
        "unit": freq_convert[freq],
        "end_date": end_date,
        "fq_ref_date": "2010-01-01"
    }
    r = requests.post(url, data=json.dumps(data))
    df = text2df(r.text)
    df['symbol'] = symbol
    df.rename({'date': 'dt', 'volume': 'vol'}, axis=1, inplace=True)
    df = df[['symbol', 'dt', 'open', 'close', 'high', 'low', 'vol']]
    for col in ['open', 'close', 'high', 'low']:
        df.loc[:, col] = df[col].apply(lambda x: round(float(x), 2))
    return df


def get_klines(symbol, end_date, freqs='1min,5min,30min,D', count=3000):
    freq_map = {'1min': '1分钟', '5min': '5分钟', '30min': '30分钟', 'D': '日线'}
    klines = dict()
    for freq in freqs.split(','):
        kline = get_kline(symbol, end_date, freq=freq, count=count)
        klines[freq_map[freq]] = kline
    return klines


def __send_event(event):
    """

    :param event: dict
        example
        {
        '标的代码': '000001.XSHG',
        '操作提示': '三卖',
        '出现时间': '2020-03-27 13:30',
        '基准价格': 2805.55,
        '其他信息': '向下中枢数量为2',
        '级别': '30分钟',
        '最新价格': 2734.52
        }
    :return:
    """
    file_events = "events_cache.json"
    if os.path.exists(file_events):
        events = json.load(open(file_events, 'r', encoding='utf-8'))
    else:
        events = dict()
    k = "|".join([event['标的代码'], event['级别'] + event['操作提示'], event['出现时间'], str(event['基准价格'])])

    if k in events.keys():
        return

    print("prepare to send: ", event)
    events[k] = event
    msg = f"**{event['标的代码']}【{event['级别'] + event['操作提示']}】**\n>\n"
    msg += f">**系统名称：** 缠论指数预警\n>\n"
    msg += f">**信号时间：** {event['出现时间']}\n>\n"
    msg += f">**预警时间：** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n>\n"
    msg += f">**信号价格：** {str(event['基准价格'])}\n>\n"
    msg += f">**最新价格：** {str(event['最新价格'])}\n>\n"
    msg_type = "markdown"
    content = {"content": msg}
    push_msg(msg_type, content)
    json.dump(events, open(file_events, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)


def monitor(symbol='000001.XSHG'):
    """单标的监控

    :param symbol:
    :return:
    """
    while 1:
        latest_dt = datetime.now().strftime('%Y-%m-%d %H:%M')
        end_date = latest_dt.split(" ")[0]
        klines = get_klines(symbol, end_date, freqs='1min,5min,30min,D', count=3000)
        sa = SolidAnalyze(klines)
        for freq in ['1分钟', '5分钟', '30分钟']:
            print(f"{latest_dt}: monitor {symbol} at {freq}")

            for func in [sa.is_first_buy, sa.is_first_sell,
                         sa.is_second_buy, sa.is_second_sell,
                         sa.is_third_buy, sa.is_third_sell,
                         sa.is_xd_buy, sa.is_xd_buy]:

                b1, event = func(freq, tolerance=0.1)
                if b1:
                    event['级别'] = freq
                    event['最新价格'] = sa.kas['1分钟'].latest_price
                    __send_event(event)

        t = latest_dt.split(' ')[1]
        if "13:00" > t > "11:30" or t > "15:00":
            break
        else:
            time.sleep(280)


if __name__ == '__main__':
    scheduler = BlockingScheduler()
    scheduler.add_job(monitor, 'cron', day_of_week='mon-fri', hour="9", minute="30", next_run_time=datetime.now())
    scheduler.add_job(monitor, 'cron', day_of_week='mon-fri', hour="13", minute="0")
    scheduler.start()


