# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/06/16 19:45
describe: 飞书多维表格接口
"""
import pandas as pd
from czsc.fsa.base import FeishuApiBase, request


class BiTable(FeishuApiBase):
    """
    多维表格概述: https://open.feishu.cn/document/server-docs/docs/bitable-v1/bitable-overview
    """

    def __init__(self, app_id, app_secret):
        super().__init__(app_id, app_secret)

    def list_tables(self, app_token):
        """列出数据表

        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table/list

        :param app_token: 应用token
        :return: 返回数据
        """
        url = f"{self.host}/open-apis/bitable/v1/apps/{app_token}/tables"
        return request("GET", url, self.get_headers())

    def list_records(self, app_token, table_id, **kwargs):
        """列出数据表中的记录

        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-record/list

        :param app_token: 应用token
        :param table_id: 数据表id
        :return: 返回数据
        """
        url = f"{self.host}/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
        if kwargs.get("page_size") is None:
            kwargs["page_size"] = 500
        if kwargs.get("page_token") is None:
            kwargs["page_token"] = ""
        url = url + "?" + "&".join([f"{k}={v}" for k, v in kwargs.items()])
        return request("GET", url, self.get_headers())

    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # 以下是便捷使用的封装，非官方API接口
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def read_table(self, app_token, table_id, **kwargs):
        """读取多维表格中指定表格的数据

        :param app_token: 多维表格应用token
        :param table_id: 表格id
        :return:
        """
        rows = []
        res = self.list_records(app_token, table_id, **kwargs)['data']
        total = res['total']
        rows.extend(res['items'])
        while res['has_more']:
            res = self.list_records(app_token, table_id, page_token=res['page_token'], **kwargs)['data']
            rows.extend(res['items'])

        assert len(rows) == total, "数据读取异常"
        return pd.DataFrame([x['fields'] for x in rows])
