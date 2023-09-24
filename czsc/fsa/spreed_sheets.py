# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/12/16 19:45
describe: 飞书电子表格接口
"""
import string
import pandas as pd
from loguru import logger
from czsc.fsa.base import FeishuApiBase, request


class SpreadSheets(FeishuApiBase):
    """
    电子表格概述: https://open.feishu.cn/document/ukTMukTMukTM/uATMzUjLwEzM14CMxMTN/overview
    """

    def __init__(self, app_id, app_secret):
        super().__init__(app_id, app_secret)

    def create(self, folder_token, title):
        """创建电子表格

        https://open.feishu.cn/document/ukTMukTMukTM/uUDN04SN0QjL1QDN/sheets-v3/spreadsheet/create

        :param folder_token: 文件夹 token
        :param title: 表格标题，长度范围：0 ～ 255 字符
        :return: 返回数据样例如下
                {
                    "code": 0,
                    "msg": "success",
                    "data": {
                        "spreadsheet": {
                            "title": "title",
                            "folder_token": "fldcnMsNb*****hIW9IjG1LVswg",
                            "url": "https://bytedance.feishu.cn/sheets/shtcnmBA*****yGehy8",
                            "spreadsheet_token": "shtcnmBA*****yGehy8"
                        }
                    }
                }
        """
        url = f"{self.host}/open-apis/sheets/v3/spreadsheets"
        payload = {"title": title, "folder_token": folder_token}
        return request("POST", url, self.get_headers(), payload)

    def check(self, token):
        """获取电子表格信息

        https://open.feishu.cn/document/ukTMukTMukTM/uUDN04SN0QjL1QDN/sheets-v3/spreadsheet/get

        :param token: 表格的token，示例值："shtxxxxxxxxxxxxxxx"
        :return: 返回数据样例如下
                {
                    "code": 0,
                    "msg": "success",
                    "data": {
                        "spreadsheet": {
                            "title": "title",
                            "owner_id": "ou_xxxxxxxxxxxx",
                            "token": "shtxxxxxxxxxxxxxx",
                            "url": "https://bytedance.feishu.cn/sheets/shtcnmBA*****yGehy8"
                        }
                    }
                }
        """
        url = f"{self.host}/open-apis/sheets/v3/spreadsheets/{token}"
        return request('GET', url, self.get_headers())

    def get_sheets(self, token):
        """获取工作表

        https://open.feishu.cn/document/ukTMukTMukTM/uUDN04SN0QjL1QDN/sheets-v3/spreadsheet-sheet/query

        :param token: 电子表格的token
        :return: 返回数据样例如下
                {'code': 0,
                 'data': {'sheets': [{'grid_properties': {'column_count': 20,
                     'frozen_column_count': 0,
                     'frozen_row_count': 0,
                     'row_count': 200},
                    'hidden': False,
                    'index': 0,
                    'resource_type': 'sheet',
                    'sheet_id': '50bafb',
                    'title': 'Sheet1'}]},
                 'msg': ''}
        """
        url = f"{self.host}/open-apis/sheets/v3/spreadsheets/{token}/sheets/query"
        return request("GET", url, self.get_headers())

    def get_sheet_meta(self, token, sheet_id):
        """查询工作表

        https://open.feishu.cn/document/ukTMukTMukTM/uUDN04SN0QjL1QDN/sheets-v3/spreadsheet-sheet/get

        :param token:
        :param sheet_id:
        :return: 返回数据样例
            {'code': 0,
             'data': {'sheet': {'grid_properties': {'column_count': 20,
                'frozen_column_count': 0,
                'frozen_row_count': 0,
                'row_count': 200},
               'hidden': False,
               'index': 0,
               'resource_type': 'sheet',
               'sheet_id': '50bafb',
               'title': 'Sheet1'}},
             'msg': ''}
        """
        url = f"{self.host}/open-apis/sheets/v3/spreadsheets/{token}/sheets/{sheet_id}"
        return request('GET', url, self.get_headers())

    def update_values(self, token, data):
        """向多个范围写入数据

        https://open.feishu.cn/document/ukTMukTMukTM/uEjMzUjLxIzM14SMyMTN

        :param token: spreadsheetToken
        :param data: 数据样例
            {
              "valueRanges": [
                {
                  "range": "range1",
                  "values": [
                    [
                      "string1", 1, "http://www.xx.com"
                    ]
                  ]
                },
                {
                  "range": "range2",
                  "values": [
                    [
                      "string2", 2, "http://www.xx.com"
                    ]
                  ]
                }
              ]
            }
        :return:
        """
        url = f"{self.host}/open-apis/sheets/v2/spreadsheets/{token}/values_batch_update"
        return request("POST", url, self.get_headers(), data)

    def update_styles(self, token, data):
        url = self.host + "/open-apis/sheets/v2/spreadsheets/" + token + "/styles_batch_update"
        return request("POST", url, self.get_headers(), data)

    def read_sheet(self, token, sheet_id):
        """获取工作表中的单个数据范围

        https://open.feishu.cn/document/ukTMukTMukTM/ugTMzUjL4EzM14COxMTN

        :param token: spreadsheetToken
        :param sheet_id: sheetId，有四种表达方式，参考文档说明，可以获取指定表格内的特定范围数据
        :return: 返回数据
        """
        url = f"{self.host}/open-apis/sheets/v2/spreadsheets/{token}/values/{sheet_id}"
        return request("GET", url, self.get_headers())

    def delete_values(self, token, sheet_id):
        """删除行列，清空数据

        https://open.feishu.cn/document/ukTMukTMukTM/ucjMzUjL3IzM14yNyMTN

        :param token:
        :param sheet_id:
        :return:
        """
        url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{token}/dimension_range"
        row_count = self.get_sheet_meta(token, sheet_id)['data']['sheet']['grid_properties']['row_count'] - 1
        while row_count > 1:
            data = {
                "dimension": {
                    "sheetId": sheet_id,
                    "majorDimension": "ROWS",
                    "startIndex": 1,
                    "endIndex": min(4001, row_count),
                }
            }
            request('DELETE', url, self.get_headers(), data)
            row_count = self.get_sheet_meta(token, sheet_id)['data']['sheet']['grid_properties']['row_count'] - 1

        col_count = self.get_sheet_meta(token, sheet_id)['data']['sheet']['grid_properties']['column_count'] - 1
        if col_count > 1:
            data = {
                "dimension": {
                    "sheetId": sheet_id,
                    "majorDimension": "COLUMNS",
                    "startIndex": 1,
                    "endIndex": min(4001, col_count),
                }
            }
            request('DELETE', url, self.get_headers(), data)

    def dimension_range(self, token, data):
        """增加行列

        https://open.feishu.cn/document/ukTMukTMukTM/uUjMzUjL1IzM14SNyMTN

        :param token:
        :param data:
            {
              "dimension":{
                   "sheetId": "string",
                    "majorDimension": "ROWS",
                    "length": 1
                 }
            }
        :return:
        """
        url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{token}/dimension_range"
        return request('POST', url, self.get_headers(), data)

    def update_sheets(self, token, operates):
        """增加工作表，复制工作表、删除工作表

        https://open.feishu.cn/document/ukTMukTMukTM/uYTMzUjL2EzM14iNxMTN

        :param token: spreadsheet 的 token
        :param operates: 定义工作表操作
            {
              "requests": [
                {
                  "addSheet": {
                    "properties": {
                      "title": "string",
                      "index": 0
                    }
                  }
                },
                {
                  "copySheet": {
                    "source": {
                      "sheetId": "string"
                    },
                    "destination": {
                      "title": "string"
                    }
                  }
                },
                {
                  "deleteSheet": {
                    "sheetId": "string"
                  }
                }
              ]
            }
        :return:
        """
        url = f"{self.host}/open-apis/sheets/v2/spreadsheets/{token}/sheets_batch_update"
        return request("POST", url, self.get_headers(), operates)

    def add_permissions_member(self, token, doctype, member_type, member_id, perm):
        url = (
            self.host
            + "/open-apis/drive/v1/permissions/"
            + token
            + "/members?type="
            + doctype
            + "&need_notification=false"
        )
        payload = {"member_type": member_type, "member_id": member_id, "perm": perm}
        request("POST", url, self.get_headers(), payload)

    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # 以下是便捷使用的封装，非官方API接口
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def append(self, token, sheet_id, df: pd.DataFrame, batch_size=2000, overwrite=True):
        """往 sheet 中追加数据

        :param token: spreadsheetToken
        :param sheet_id: sheetId
        :param df: 待写入的数据
        :param batch_size: 批次写入行数
        :return: None
        """
        if df.empty:
            logger.warning("待写入的数据为空，不执行写入操作")
            return

        if overwrite:
            self.delete_values(token, sheet_id)
            cols = df.columns.tolist()
            col_range = f"{sheet_id}!A1:{string.ascii_uppercase[len(cols) - 1]}1"
            self.update_values(token, {'valueRanges': [{"range": col_range, "values": [cols]}]})

        # 读取表格列名，确保 df 列名与表格列名一致
        sheet_cols = self.get_sheet_cols(token, sheet_id)
        df = df[sheet_cols]

        meta = self.get_sheet_meta(token, sheet_id)
        start_index = meta['data']['sheet']['grid_properties']['row_count']
        col_count = meta['data']['sheet']['grid_properties']['column_count']
        assert df.shape[1] == col_count, f"df 列数 {df.shape[1]} 与表格列数 {col_count} 不一致"

        for i in range(0, len(df), batch_size):
            dfi = df.iloc[i: i + batch_size]
            si = i + start_index + 1
            ei = si + batch_size
            vol_range = f"{sheet_id}!A{si}:{string.ascii_uppercase[col_count - 1]}{ei}"
            self.update_values(token, {'valueRanges': [{"range": vol_range, "values": dfi.values.tolist()}]})

    def get_sheet_cols(self, token, sheet_id, n=1):
        """读取表格列名

        :param token: spreadsheetToken
        :param sheet_id: sheetId
        :param n: 指名第几行为列名，默认为第一行
        :return: 列名列表
        """
        meta = self.get_sheet_meta(token, sheet_id)
        col_count = meta['data']['sheet']['grid_properties']['column_count']
        res = self.read_sheet(token, f"{sheet_id}!A{n}:{string.ascii_uppercase[col_count - 1]}{n}")
        values = res['data']['valueRange']['values']
        cols = values.pop(0)
        return cols

    def read_table(self, token, sheet_id):
        """读取表格

        :param token:
        :param sheet_id:
        :return:
        """
        res = self.read_sheet(token, sheet_id)
        values = res['data']['valueRange']['values']
        cols = values.pop(0)
        return pd.DataFrame(values, columns=cols)


class SingleSheet(SpreadSheets):
    """飞书表格中单个工作表的操作，继承自 SpreadSheets"""

    def __init__(self, app_id, app_secret, token, sheet_id):
        """
        初始化 SingleSheet 类

        :param app_id: 飞书应用的 app_id
        :param app_secret: 飞书应用的 app_secret
        :param token: 电子表格的 token
        :param sheet_id: 电子表格的 sheet_id
        """
        super().__init__(app_id, app_secret)
        self.token = token
        self.sheet_id = sheet_id

    def get_meta(self):
        """获取电子表格的元数据"""
        return super().get_sheet_meta(self.token, self.sheet_id)

    def get_cols(self, n=1):
        """
        获取电子表格的列名

        :param n: 指名第几行为列名，默认为第一行
        :return: 列名列表
        """
        super().get_sheet_cols(self.token, self.sheet_id, n)

    def single_append(self, df: pd.DataFrame, batch_size=2000, overwrite=False):
        """
        在电子表格的末尾追加数据

        :param df: 待追加的数据
        :param batch_size: 每次追加的数据量
        :param overwrite: 是否覆盖原有数据
        """
        super().append(self.token, self.sheet_id, df, batch_size, overwrite)

    def single_read_table(self):
        """读取整个电子表格的数据"""
        super().read_table(self.token, self.sheet_id)

    def single_delete_values(self):
        """
        删除电子表格的所有数据
        """
        super().delete_values(self.token, self.sheet_id)
