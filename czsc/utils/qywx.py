# coding: utf-8
"""
企业微信工具
"""
import os
import requests


def push_text(content: str, key: str) -> None:
    """推送文本消息到企业微信群

    API介绍： https://work.weixin.qq.com/api/doc/90000/90136/91770

    :param content: 文本内容
    :param key: 企业微信群聊机器人的key
    :return: None
    """
    api_send = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={}".format(key)
    data = {"msgtype": "text", "text": {"content": content}}
    try:
        response = requests.post(api_send, json=data)
        assert response.json()['errmsg'] == 'ok'
    except:
        print(f"{data} - 文本消息推送失败")


def push_markdown(content: str, key: str) -> None:
    """推送 Markdown 消息到企业微信群

    API介绍： https://work.weixin.qq.com/api/doc/90000/90136/91770

    :param content: Markdown 内容
    :param key: 企业微信群聊机器人的key
    :return: None
    """
    api_send = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={}".format(key)
    data = {"msgtype": "markdown", "markdown": {"content": content}}
    try:
        response = requests.post(api_send, json=data)
        assert response.json()['errmsg'] == 'ok'
    except:
        print(f"{data} - Markdown 消息推送失败")


def push_file(file: str, key: str):
    """推送文件到企业微信群聊

    :param file: 文件路径，不能包含中文
    :param key: 群聊机器人的key
    :return:
    """
    api_upload = "https://qyapi.weixin.qq.com/cgi-bin/webhook/upload_media?key={}&type=file".format(key)
    api_send = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={}".format(key)
    file_name = os.path.split(file)[1]
    try:
        files = {file_name: open(file, 'rb').read()}
        r1 = requests.post(api_upload, files=files)
        mid = r1.json()['media_id']
        assert r1.json()['errmsg'] == 'ok', str(r1.json())

        data = {"msgtype": "file", "file": {"media_id": mid}}
        r2 = requests.post(api_send, json=data)
        assert r2.json()['errmsg'] == 'ok', str(r2.json())
    except:
        print(f"推送文件{file_name}到企业微信群失败")


def push_msg(msg_type, content, key):
    """推送消息到企业微信群

    content格式参考： https://work.weixin.qq.com/api/doc/90000/90136/91770
    """
    api_send = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={}".format(key)
    data = {"msgtype": msg_type, msg_type: content}
    try:
        response = requests.post(api_send, json=data)
        assert response.json()['errmsg'] == 'ok'
    except:
        print("消息推送失败")

