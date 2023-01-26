# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/12/16 19:37
describe: 
"""
import requests
from czsc.fsa.base import request, FeishuApiBase
from czsc.fsa.spreed_sheets import SpreadSheets
from czsc.fsa.im import IM


def push_text(text: str, key: str) -> None:
    """使用自定义机器人推送文本消息到飞书群聊

    如何在群组中使用机器人: https://www.feishu.cn/hc/zh-CN/articles/360024984973

    :param text: 文本内容
    :param key: 机器人的key
    :return: None
    """
    api_send = f"https://open.feishu.cn/open-apis/bot/v2/hook/{key}"
    data = {"msg_type": "text", "content": {"text": text}}
    try:
        response = requests.post(api_send, json=data)
        assert response.json()['StatusMessage'] == 'success'
    except:
        print(f"{data} - 文本消息推送失败")

