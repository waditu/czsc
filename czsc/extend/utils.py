import json
import requests
import pandas as pd


def push_text(message, key=""):
    url = 'https://oapi.dingtalk.com/robot/send?access_token=62c9508c1f003065648f3767dfbf03fd290bdff8d50fa35519217152efdfe80f'
    HEADERS = {"Content-Type": "application/json ;charset=utf-8 "}
    message = message
    String_textMsg = {
        "msgtype": "text",
        "text": {
            "content": "哗啦啦:" + message
        },
        "at": {
            # "atMobiles": [
            #     "130xxxxxxxx"                                    #如果需要@某人，这里写他的手机号
            # ],
            "isAtAll": 1  # 如果需要@所有人，这些写1
        }
    }
    String_textMsg = json.dumps(String_textMsg)
    res = requests.post(url, data=String_textMsg, headers=HEADERS)


def read_csv_symbol(path):
    """
    读取通达信导出的文件
    :param path:
    :return:
    """
    data = pd.read_csv(path, encoding="GB2312")
    list = []
    dic = {}
    for index, row in data.iterrows():
        symbol = row.iloc[0]
        name = row.iloc[1]
        market = symbol[0:2]
        dic[symbol] = name
        if market == 'SZ':
            list.append('{}.XSHE'.format(symbol[2:]))
        else:
            list.append('{}.XSHG'.format(symbol[2:]))

    return list, dic
