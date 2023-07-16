# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/12/16 19:37
describe: 
"""
import requests
from loguru import logger
from czsc.fsa.base import request, FeishuApiBase
from czsc.fsa.spreed_sheets import SpreadSheets, SingleSheet
from czsc.fsa.im import IM
from czsc.fsa.bi_table import BiTable


def push_text(text: str, key: str) -> None:
    """使用自定义机器人推送文本消息到飞书群聊

    如何在群组中使用机器人:

    - https://www.feishu.cn/hc/zh-CN/articles/360024984973
    - https://open.feishu.cn/document/ukTMukTMukTM/ucTM5YjL3ETO24yNxkjN

    :param text: 文本内容
    :param key: 机器人的key
    :return: None
    """
    api_send = f"https://open.feishu.cn/open-apis/bot/v2/hook/{key}"
    data = {"msg_type": "text", "content": {"text": text}}
    try:
        response = requests.post(api_send, json=data)
        assert response.json()['StatusMessage'] == 'success'
    except Exception as e:
        logger.error(f"推送消息失败: {e}")


def read_feishu_sheet(spread_sheet_token: str, sheet_id: str = None, **kwargs):
    """读取飞书电子表格

    id和token的获取，参考：https://open.feishu.cn/document/ukTMukTMukTM/uATMzUjLwEzM14CMxMTN/overview

    :param spread_sheet_token: 电子表格token
    :param sheet_id: 电子表格中指定 sheet 的 id
    :param kwargs:
            feishu_app_id: 飞书APP的app_id
            feishu_app_secret: 飞书APP的app_secret
    :return:
    """
    ss = SpreadSheets(app_id=kwargs['feishu_app_id'], app_secret=kwargs['feishu_app_secret'])
    if not sheet_id:
        res = ss.get_sheets(spread_sheet_token)
        sheet_id = res['data']['sheets'][0]['sheet_id']
    df = ss.read_table(spread_sheet_token, sheet_id)
    return df


def get_feishu_members_by_mobiles(mobiles: list, **kwargs):
    """根据手机号获取飞书用户id

    飞书接口文档：https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/contact-v3/user/batch_get_id

    :param mobiles: 手机号列表
    :param kwargs:
            feishu_app_id: 飞书APP的app_id
            feishu_app_secret: 飞书APP的app_secret
    :return:
    """
    fim = IM(app_id=kwargs['feishu_app_id'], app_secret=kwargs['feishu_app_secret'])
    res = fim.get_user_id({"mobiles": mobiles})['data']['user_list']
    return [x['user_id'] for x in res]


def push_message(msg: str, msg_type: str = 'text', receive_id_type: str = 'open_id', **kwargs) -> None:
    """使用飞书APP批量推送消息

    API介绍：https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/im-v1/message/create
    请求体构建: https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/im-v1/message/create_json

    :param msg: 消息内容
    :param msg_type: 消息类型，支持：text, image, file
    :param receive_id_type:  接收者是用户还是群聊  open_id / user_id / union_id / email / chat_id
    :param kwargs:
        feishu_app_id: 飞书APP的app_id
        feishu_app_secret: 飞书APP的app_secret
        feishu_members: 需要通知的飞书APP的成员列表，支持单个成员或多个成员或群聊，
                        成员格式为：'user_id'或 'open_id'，必须是同一类型的
    :return:
    """
    fim = IM(app_id=kwargs['feishu_app_id'], app_secret=kwargs['feishu_app_secret'])
    members = kwargs['feishu_members']
    if isinstance(members, str):
        members = [members]

    for member in members:
        try:
            if msg_type == 'text':
                fim.send_text(msg, member, receive_id_type)
            elif msg_type == 'image':
                fim.send_image(msg, member, receive_id_type)
            elif msg_type == 'file':
                fim.send_file(msg, member, receive_id_type)
            else:
                logger.error(f"不支持的消息类型：{msg_type}")
        except Exception as e:
            logger.error(f"推送消息失败：{e}")

