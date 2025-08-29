# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/06/16 19:45
describe: 飞书多维表格接口
"""
import os
import loguru
import pandas as pd
from czsc.fsa.base import FeishuApiBase, request


class BiTable(FeishuApiBase):
    """
    多维表格概述: https://open.feishu.cn/document/server-docs/docs/bitable-v1/bitable-overview
    """

    def __init__(self, app_id=None, app_secret=None, app_token=None, **kwargs):
        """

        :param app_id: 飞书应用的唯一标识
        :param app_secret: 飞书应用的密钥
        :param app_token: 一个多维表格的唯一标识。示例值："bascnKMKGS5oD3lmCHq9euO8cGh"
        """
        app_id = app_id or os.getenv("FEISHU_APP_ID")
        app_secret = app_secret or os.getenv("FEISHU_APP_SECRET")
        super().__init__(app_id, app_secret, **kwargs)
        self.app_token = app_token
        # self.logger = kwargs.get("logger", loguru.logger)

    def one_record(self, table_id, record_id):
        """根据 record_id 的值检索现有记录

        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-record/get
        """
        url = f"{self.host}/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}/records/{record_id}"
        return request("GET", url, self.get_headers())

    def list_records(self, table_id, **kwargs):
        """列出数据表中的记录

        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-record/list

        :param table_id: 数据表id
        :return: 返回数据
        """
        url = f"{self.host}/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}/records"
        if kwargs.get("page_size") is None:
            kwargs["page_size"] = 500
        if kwargs.get("page_token") is None:
            kwargs["page_token"] = ""
        url = url + "?" + "&".join([f"{k}={v}" for k, v in kwargs.items()])
        return request("GET", url, self.get_headers())

    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # 数据表相关api
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def create_table(self, name=None, default_view_name=None, fields=None):
        """新增一个仅包含索引列的空数据表，也可以指定一部分初始字段。

        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table/create
        :param name:非必填 数据表名称 请注意：
            名称中的首尾空格将会被去除。
            示例值："table1"
            数据校验规则：
            长度范围：1 字符 ～ 100 字符
        :param default_view_name:非必填 默认表格视图的名称，不填则默认为 表格。
        :param fields: 非必填 数据表的初始字段。数组类型
            结构：
            field_name： 必填 字段名
            type：必填	字段类型
            ui_type：字段在界面上的展示类型
            property：字段属性
            description： 字段的描述
        :return: 返回数据
        """
        params = {}
        if name is not None:
            params["name"] = name
        if default_view_name is not None:
            params["default_view_name"] = default_view_name
        if default_view_name is not None:
            params["fields"] = fields
        url = f"{self.host}/open-apis/bitable/v1/apps/{self.app_token}/tables"
        return request("POST", url, self.get_headers(), payload={"table": params})

    def batch_create_table(self, names=None):
        """新增多个数据表。

        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table/batch_create
        :param names:非必填 数据表名称 []
            name :数据表名称
                    请注意：
                    名称中的首尾空格将会被去除。
                    示例值："table1"
                    数据校验规则：
                    长度范围：1 字符 ～ 100 字符
        :return: 返回数据
        """
        params = []
        if names is not None:
            for name in names:
                params.append({"name": name})
        url = f"{self.host}/open-apis/bitable/v1/apps/{self.app_token}/tables/batch_create"
        return request("POST", url, self.get_headers(), payload={"tables": params})

    def delete_table(self, table_id):
        """删除一个数据表，最后一张数据表不允许被删除。

        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table/delete
        :param table_id:多维表格数据表的唯一标识符

        :return: 返回数据
        """
        url = f"{self.host}/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}"
        return request("DELETE", url, self.get_headers())

    def batch_delete_table(self, table_ids=None):
        """删除一个数据表，最后一张数据表不允许被删除。

        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table/batch_delete
        :param table_ids: 待删除的数据表的id [table_id 参数说明]，当前一次操作最多支持50个数据表

        :return: 返回数据
        """
        url = f"{self.host}/open-apis/bitable/v1/apps/{self.app_token}/tables/batch_delete"
        return request("POST", url, self.get_headers(), payload={"table_ids": table_ids})

    def patch_table(self, table_id, name):
        """更新数据表的基本信息，包括数据表的名称等

        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table/patch
        :param table_id: 多维表格数据表的唯一标识符
        :param name: 数据表的新名称。请注意：
                    名称中的首尾空格将会被去除。
                    如果名称为空或和旧名称相同，接口仍然会返回成功，但是名称不会被更改。
                    示例值："数据表的新名称"
                    数据校验规则：
                    长度范围：1 字符 ～ 100 字符
                    正则校验：^[^\[\]\:\\\/\?\*]+$

        :return: 返回数据
        """
        params = {}
        if name is not None:
            params["name"] = name
        url = f"{self.host}/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}"
        return request("PATCH", url, self.get_headers(), payload=params)

    def list_tables(self, page_token=None, page_size=20):
        """获取多维表格下的所有数据表。

        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table/list
        :param page_token: 	分页标记，第一次请求不填，表示从头开始遍历；分页查询结果还有更多项时会同时返回新的 page_token，
            下次遍历可采用该 page_token 获取查询结果
        :param page_size: 	分页大小示例值：10 默认值：20 数据校验规则：最大值：100
        :return: 返回数据
        """
        url = f"{self.host}/open-apis/bitable/v1/apps/{self.app_token}/tables?page_size={page_size}"
        url = url if page_token is None else url + f"&page_token={page_token}"
        return request("GET", url, self.get_headers())

    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # 记录相关api
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def table_record_get(
        self,
        table_id,
        record_id,
        text_field_as_array=None,
        user_id_type=None,
        display_formula_ref=None,
        with_shared_url=None,
        automatic_fields=None,
    ):
        """获取多维表格下的所有数据表。

        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-record/get
        :param table_id: table id
        :param record_id: 单条记录的 id
        :param text_field_as_array: 非必需 多行文本字段数据是否以数组形式返回。true 表示以数组形式返回。默认为 false
        :param user_id_type: 非必需 用户 ID 类型
        :param display_formula_ref: 控制公式、查找引用是否显示完整原样的返回结果。默认为 false
        :param with_shared_url: 非必需 	控制是否返回该记录的链接，即 record_url 参数。默认为 false，即不返回
        :param automatic_fields: 非必需 控制是否返回自动计算的字段，例如 created_by/created_time/last_modified_by/last_modified_time，true 表示返回。默认为 false

        :return: 返回数据
        """
        url = f"{self.host}/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}/records/{record_id}?1=1"
        url = url if text_field_as_array is None else url + f"&text_field_as_array={text_field_as_array}"
        url = url if user_id_type is None else url + f"&user_id_type={user_id_type}"
        url = url if display_formula_ref is None else url + f"&display_formula_ref={display_formula_ref}"
        url = url if with_shared_url is None else url + f"&with_shared_url={with_shared_url}"
        url = url if automatic_fields is None else url + f"&automatic_fields={automatic_fields}"
        return request("GET", url, self.get_headers())

    def table_record_search(
        self,
        table_id,
        user_id_type=None,
        page_token=None,
        page_size=20,
        view_id=None,
        field_names=None,
        sort=None,
        filter=None,
        automatic_fields=None,
    ):
        """查询数据表中的现有记录，单次最多查询 500 行记录，支持分页获取

        https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/bitable-v1/app-table-record/search
        :param table_id: table id
        :param user_id_type: 非必需	用户 ID 类型
        :param page_token: 非必需 分页标记，第一次请求不填，表示从头开始遍历；分页查询结果还有更多项时会同时返回新的 page_token，下次遍历可采用该 page_token 获取查询结果
        :param page_size: 非必需 分页大小。最大值为 500

        :param view_id: 非必需 视图的唯一标识符，获取指定视图下的记录view_id 参数说明 注意：当 filter 参数 或 sort 参数不为空时，请求视为对数据表中的全部数据做条件过滤，指定的view_id 会被忽略。数据校验规则：长度范围：0 字符 ～ 50 字符
        :param field_names: 非必需 字段名称，用于指定本次查询返回记录中包含的字段
        :param sort: 非必需 sort[] 排序条件
                        field_name: 非必需 字段名称 示例值："多行文本"  数据校验规则：长度范围：0 字符 ～ 1000 字符
                        desc:非必需 是否倒序排序 示例值：true 默认值：false
        :param filter: 非必需 筛选条件
        :param automatic_fields: 非必需 控制是否返回自动计算的字段, true 表示返回

        :return: 返回数据
        """
        url = f"{self.host}/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}/records/search?page_size={page_size}"
        url = url if user_id_type is None else url + f"&user_id_type={user_id_type}"
        url = url if page_token is None else url + f"&page_token={page_token}"

        params = {}
        if view_id is not None:
            params["view_id"] = view_id
        if field_names is not None:
            params["field_names"] = field_names
        if sort is not None:
            params["sort"] = sort
        if filter is not None:
            params["filter"] = filter
        if automatic_fields is not None:
            params["automatic_fields"] = automatic_fields
        return request("POST", url, self.get_headers(), payload=params)

    def table_record_create(self, table_id, fields, user_id_type=None, client_token=None):
        """数据表中新增一条记录

        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-record/create

        :param table_id: table id
        :param user_id_type: 非必需 用户 ID 类型
        :param client_token: 非必需 格式为标准的 uuidv4，操作的唯一标识，用于幂等的进行更新操作。此值为空表示将发起一次新的请求，此值非空表示幂等的进行更新操作。
        :param fields: 必需
            数据表的字段，即数据表的列。当前接口支持的字段类型为：多行文本、单选、条码、多选、日期、人员、附件、复选框、超链接、数字、单向关联、双向关联、电话号码、地理位置。详情参考
        :return: 返回数据
        """
        url = f"{self.host}/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}/records?1=1"
        url = url if user_id_type is None else url + f"&user_id_type={user_id_type}"
        url = url if client_token is None else url + f"&client_token={client_token}"
        return request("POST", url, self.get_headers(), payload={"fields": fields})

    def table_record_update(self, table_id, record_id, fields, user_id_type=None):
        """更新数据表中的一条记录

        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-record/update
        :param table_id: table id
        :param record_id: 一条记录的唯一标识 id

        :param user_id_type: 非必需 用户 ID 类型

        :param fields: 必需
            数据表的字段，即数据表的列。当前接口支持的字段类型为：多行文本、单选、条码、多选、日期、人员、附件、复选框、超链接、数字、单向关联、双向关联、电话号码、地理位置。详情参考

        :return: 返回数据
        """
        url = f"{self.host}/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}/records/{record_id}/?1=1"
        url = url if user_id_type is None else url + f"&user_id_type={user_id_type}"
        return request("PUT", url, self.get_headers(), payload={"fields": fields})

    def table_record_delete(self, table_id, record_id):
        """删除数据表中的一条记录

        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-record/delete
        :param table_id: table id
        :param record_id: 一条记录的唯一标识 id
        :return: 返回数据
        """
        url = f"{self.host}/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}/records/{record_id}"
        return request("DELETE", url, self.get_headers())

    def table_record_batch_create(self, table_id, records, user_id_type=None, client_token=None):
        """在数据表中新增多条记录，单次调用最多新增 500 条记录。

        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-record/batch_create

        :param table_id: table id
        :param user_id_type: 非必需 用户 ID 类型
        :param client_token: 非必需 格式为标准的 uuidv4，操作的唯一标识，用于幂等的进行更新操作。此值为空表示将发起一次新的请求，此值非空表示幂等的进行更新操作。
        :param records:[] 	数据表的字段，即数据表的列当前接口支持的字段类型 示例值：{"多行文本":"HelloWorld"}
        :return: 返回数据
        """
        # records = []
        # for field in fields:
        #     records.append({"fields": field})
        url = f"{self.host}/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}/records/batch_create?1=1"
        url = url if user_id_type is None else url + f"&user_id_type={user_id_type}"
        url = url if client_token is None else url + f"&client_token={client_token}"
        return request("POST", url, self.get_headers(), payload={"records": records})

    def table_record_batch_update(self, table_id, records, user_id_type=None):
        """更新数据表中的多条记录，单次调用最多更新 500 条记录。

        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-record/batch_update
        :param table_id: table id

        :param user_id_type: 非必需 用户 ID 类型

        :param records:[] 	记录
                        [{
                            "record_id": "reclAqylTN",
                            "fields": {
                                "索引": "索引列多行文本类型"
                            }
                        }]
        :return: 返回数据
        """
        url = f"{self.host}/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}/records/batch_update?1=1"
        url = url if user_id_type is None else url + f"&user_id_type={user_id_type}"
        return request("POST", url, self.get_headers(), payload={"records": records})

    def table_record_batch_delete(self, table_id, record_ids):
        """删除数据表中现有的多条记录，单次调用中最多删除 500 条记录

        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-record/batch_delete
        :param table_id: table id

        :param record_ids:string[] 	删除的多条记录id列表示例值：["recwNXzPQv"]

        :return: 返回数据
        """
        url = f"{self.host}/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}/records/batch_delete"
        return request("POST", url, self.get_headers(), payload={"records": record_ids})

    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # 视图相关api
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def table_view_patch(self, table_id, view_id, infos):
        """增量修改视图信息

        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-view/patch
        :param table_id: table id
        :param view_id: 视图 ID

        :param infos: 修改信息
                    view_name: 	视图名称
                    property: 非必需	视图属性
        :return: 返回数据
        """
        url = f"{self.host}/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}/views/{view_id}"
        return request("PATCH", url, self.get_headers(), payload=infos)

    def table_view_get(self, table_id, view_id):
        """根据 view_id 检索现有视图

        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-view/get
        :param table_id: table id
        :param view_id: 视图 ID

        :return: 返回数据
        """
        url = f"{self.host}/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}/views/{view_id}"
        return request("GET", url, self.get_headers())

    def table_view_list(self, table_id, page_size=20, user_id_type=None, page_token=None):
        """根据 app_token 和 table_id，获取数据表的所有视图

        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-view/list
        :param table_id: table id

        :param user_id_type: 非必需 用户 ID 类型 示例值："open_id"
        :param page_token:非必需 	分页标记，第一次请求不填，表示从头开始遍历；分页查询结果还有更多项时会同时返回新的 page_token，下次遍历可采用该 page_token 获取查询结果
        :param page_size:非必需 分页大小 示例值：10 默认值：20 数据校验规则：最大值：100

        :return: 返回数据
        """
        url = f"{self.host}/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}/views?page_size={page_size}"
        url = url if user_id_type is None else url + f"&user_id_type={user_id_type}"
        url = url if page_token is None else url + f"&page_token={page_token}"
        return request("GET", url, self.get_headers())

    def table_view_create(self, table_id, view_name, view_type):
        """在数据表中新增一个视图

        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-view/create
        :param table_id: table id

        :param view_name: 视图名字
        :param view_type: 视图类型 示例值："grid"
                        可选值有：
                            grid:表格视图
                            kanban:看板视图
                            gallery:画册视图
                            gantt:甘特视图
                            form:表单视图
        :return: 返回数据
        """
        url = f"{self.host}/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}/views"
        return request("POST", url, self.get_headers(), payload={"view_name": view_name, "view_type": view_type})

    def table_view_delete(self, table_id, view_id):
        """在数据表中新增一个视图

        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-view/create
        :param table_id: table id

        :param view_id: 视图id

        :return: 返回数据
        """
        url = f"{self.host}/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}/views/{view_id}"
        return request("DELETE", url, self.get_headers())

    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # 字段相关api
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def table_field_list(self, table_id, page_size=20, view_id=None, text_field_as_array=None, page_token=None):
        """根据 app_token 和 table_id，获取数据表的所有字段

        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-field/list
        :param table_id: table id

        :param view_id: 视图 ID
        :param text_field_as_array: 控制字段描述（多行文本格式）数据的返回格式, true 表示以数组富文本形式返回
        :param page_token: 	分页标记，第一次请求不填，表示从头开始遍历；分页查询结果还有更多项时会同时返回新的 page_token，下次遍历可采用该 page_token 获取查询结果
        :param page_size: 分页大小 示例值：10 默认值：20 数据校验规则：最大值：100

        :return: 返回数据
        """
        url = f"{self.host}/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}/fields?page_size={page_size}"
        url = url if view_id is None else url + f"&view_id={view_id}"
        url = url if text_field_as_array is None else url + f"&text_field_as_array={text_field_as_array}"
        url = url if page_token is None else url + f"&page_token={page_token}"
        return request("GET", url, self.get_headers())

    def table_field_create(
        self, table_id, field_name, type, property=None, description=None, ui_type=None, client_token=None
    ):
        """在数据表中新增一个字段

        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-field/create
        :param table_id: table id

        :param client_token: 格式为标准的 uuidv4，操作的唯一标识，用于幂等的进行更新操作。此值为空表示将发起一次新的请求，此值非空表示幂等的进行更新操作。

        :param field_name: 	多维表格字段名
        :param type: 	多维表格字段类型
                        可选值有：1：多行文本 2：数字 3：单选 4：多选5：日期7：复选框11：人员13：电话号码15：超链接17：附件18：关联20：公式21：双向关联22：地理位置23：群组1001：创建时间1002：最后更新时间1003：创建人1004：修改人1005：自动编号
        :param property: 字段属性
        :param description: 字段的描述
        :param ui_type: 字段在界面上的展示类型，例如进度字段是数字的一种展示形态
                        示例值："Progress"
                        可选值有：Text：多行文本 Email：邮箱地址 Barcode：条码 Number：数字 Progress：进度 Currency：货币 Rating：评分 SingleSelect：单选 MultiSelect：多选 DateTime：日期 Checkbox：复选框 User：人员 GroupChat：群组 Phone：电话号码 Url：超链接 Attachment：附件 SingleLink：单向关联 Formula：公式 DuplexLink：双向关联 Location：地理位置 CreatedTime：创建时间 ModifiedTime：最后更新时间 CreatedUser：创建人 ModifiedUser：修改人 AutoNumber：自动编号
        :return: 返回数据
        """
        url = f"{self.host}/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}/fields?1=1"
        url = url if client_token is None else url + f"&client_token={client_token}"

        params = {}
        if field_name is not None:
            params["field_name"] = field_name
        if type is not None:
            params["type"] = type
        if property is not None:
            params["property"] = property
        if description is not None:
            params["description"] = description
        if ui_type is not None:
            params["ui_type"] = ui_type

        return request("POST", url, self.get_headers(), payload=params)

    def table_field_update(self, table_id, field_id, field_name, type, property=None, description=None, ui_type=None):
        """数据表中更新一个字段

        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-field/update
        :param table_id: table id

        :param field_id: field id

        :param field_name: 	多维表格字段名
        :param type: 	多维表格字段类型
                        可选值有：1：多行文本 2：数字 3：单选 4：多选5：日期7：复选框11：人员13：电话号码15：超链接17：附件18：关联20：公式21：双向关联22：地理位置23：群组1001：创建时间1002：最后更新时间1003：创建人1004：修改人1005：自动编号
        :param property: 字段属性
        :param description: 字段的描述
        :param ui_type: 字段在界面上的展示类型，例如进度字段是数字的一种展示形态
                        示例值："Progress"
                        可选值有：Text：多行文本 Email：邮箱地址 Barcode：条码 Number：数字 Progress：进度 Currency：货币 Rating：评分 SingleSelect：单选 MultiSelect：多选 DateTime：日期 Checkbox：复选框 User：人员 GroupChat：群组 Phone：电话号码 Url：超链接 Attachment：附件 SingleLink：单向关联 Formula：公式 DuplexLink：双向关联 Location：地理位置 CreatedTime：创建时间 ModifiedTime：最后更新时间 CreatedUser：创建人 ModifiedUser：修改人 AutoNumber：自动编号
        :return: 返回数据
        """
        url = f"{self.host}/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}/fields/{field_id}"

        params = {}
        if field_name is not None:
            params["field_name"] = field_name
        if type is not None:
            params["type"] = type
        if property is not None:
            params["property"] = property
        if description is not None:
            params["description"] = description
        if ui_type is not None:
            params["ui_type"] = ui_type

        return request("PUT", url, self.get_headers(), payload=params)

    def table_field_delete(self, table_id, field_id):
        """数据表中删除一个字段

        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-field/delete
        :param table_id: table id

        :param field_id: field id

        :return: 返回数据
        """
        url = f"{self.host}/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}/fields/{field_id}"
        return request("DELETE", url, self.get_headers())

    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # 表单相关api
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def table_form_patch_2(
        self, table_id, form_id, name=None, description=None, shared=None, shared_limit=None, submit_limit_once=None
    ):
        """更新表单中的元数据项

        https://open.feishu.cn/document/server-docs/docs/bitable-v1/form/patch-2
        :param table_id: table id

        :param field_id: field id

        :param name: 非必需 表单名称
        :param description: 非必需 表单描述
        :param shared: 非必需 是否开启共享
        :param shared_limit: 非必需 分享范围限制 示例值："tenant_editable" 可选值有：off：仅邀请的人可填写 tenant_editable：组织内获得链接的人可填写 anyone_editable：互联网上获得链接的人可填写
        :param submit_limit_once: 非必需 填写次数限制一次 示例值：true

        :return: 返回数据
        """
        url = f"{self.host}/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}/forms/{form_id}"
        params = {}
        if name is not None:
            params["name"] = name
        if description is not None:
            params["description"] = description
        if shared is not None:
            params["shared"] = shared
        if shared_limit is not None:
            params["shared_limit"] = shared_limit
        if submit_limit_once is not None:
            params["submit_limit_once"] = submit_limit_once
        return request("PATCH", url, self.get_headers(), payload=params)

    def table_form_get(self, table_id, form_id):
        """列出表单的所有问题项

        https://open.feishu.cn/document/server-docs/docs/bitable-v1/form/list
        :param table_id: table id

        :param field_id: field id

        :return: 返回数据
        """
        url = f"{self.host}/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}/forms/{form_id}"
        return request("GET", url, self.get_headers())

    def table_form_patch(
        self, table_id, form_id, field_id, pre_field_id=None, title=None, description=None, required=None, visible=None
    ):
        """更新表单中的问题项

        https://open.feishu.cn/document/server-docs/docs/bitable-v1/form/patch
        :param table_id: table id

        :param field_id: field id

        :param pre_field_id: 非必需 上一个表单问题 ID，用于支持调整表单问题的顺序，通过前一个表单问题的 field_id 来确定位置；如果 pre_field_id 为空字符串，则说明要排到首个表单问题
        :param title: 非必需 	表单问题
        :param description: 非必需 	问题描述
        :param required: 非必需 是否必填
        :param visible: 非必需 是否可见，当值为 false 时，不允许更新其他字段

        :return: 返回数据
        """
        url = f"{self.host}/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}/forms/{form_id}/fields/{field_id}"
        params = {}
        if pre_field_id is not None:
            params["pre_field_id"] = pre_field_id
        if description is not None:
            params["description"] = description
        if title is not None:
            params["title"] = title
        if required is not None:
            params["required"] = required
        if visible is not None:
            params["visible"] = visible
        return request("PATCH", url, self.get_headers(), payload=params)

    def table_form_list(self, table_id, form_id):
        """列出表单的所有问题项

        https://open.feishu.cn/document/server-docs/docs/bitable-v1/form/list
        :param table_id: table id

        :param field_id: field id

        :return: 返回数据
        """
        url = f"{self.host}/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}/forms/{form_id}/fields"
        return request("GET", url, self.get_headers())

    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # 多维表格相关api
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def table_copy(self, app_token=None, name=None, folder_token=None, without_content=None, time_zone=None):
        """复制一个多维表格，可以指定复制到某个有权限的文件夹下

        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app/copy

        :param app_token: app_token 不传复制当前表格
        :param name: 多维表格 App 名字
        :param folder_token: 多维表格 App 归属文件夹
        :param without_content: 是否复制多维表格内容，取值：true：不复制 false：复制
        :param time_zone: 文档时区 示例值："Asia/Shanghai"
        :return: 返回数据
        """
        if app_token is None:
            app_token = self.app_token
        url = f"{self.host}/open-apis/bitable/v1/apps/{app_token}/copy"
        params = {}
        if name is not None:
            params["name"] = name
        if folder_token is not None:
            params["folder_token"] = folder_token
        if without_content is not None:
            params["without_content"] = without_content
        if time_zone is not None:
            params["time_zone"] = time_zone
        return request("POST", url, self.get_headers(), payload=params)

    def table_create(self, name=None, folder_token=None, time_zone=None):
        """复制一个多维表格，可以指定复制到某个有权限的文件夹下

        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app/create
        :param name: 多维表格 App 名字
        :param folder_token: 多维表格 App 归属文件夹
        :param time_zone: 文档时区 示例值："Asia/Shanghai"

        :return: 返回数据
        """
        url = f"{self.host}/open-apis/bitable/v1/apps"
        params = {}
        if name is not None:
            params["name"] = name
        if folder_token is not None:
            params["folder_token"] = folder_token
        if time_zone is not None:
            params["time_zone"] = time_zone
        return request("POST", url, self.get_headers(), payload=params)

    def table_get(self, app_token=None):
        """复制一个多维表格，可以指定复制到某个有权限的文件夹下

        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app/get

        :param app_token: 不传获取当前表格
        :return: 返回数据
        """
        if app_token is None:
            app_token = self.app_token
        url = f"{self.host}/open-apis/bitable/v1/apps/{app_token}"
        return request("GET", url, self.get_headers())

    def table_update(self, app_token=None, name=None, is_advanced=None):
        """通过 app_token 更新多维表格元数据

        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app/update
        :param app_token: 不传修改当前表格
        :param name: 新的多维表格名字
        :param is_advanced: 多维表格是否开启高级权限

        :return: 返回数据
        """
        if app_token is None:
            app_token = self.app_token
        url = f"{self.host}/open-apis/bitable/v1/apps/{app_token}"

        params = {}
        if name is not None:
            params["name"] = name
        if is_advanced is not None:
            params["is_advanced"] = is_advanced
        return request("PUT", url, self.get_headers(), payload=params)

    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # 以下是便捷使用的封装，非官方API接口
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    @property
    def tables(self):
        """获取所有表格

        :return:
        """
        res = self.list_tables()
        return res["data"]["items"]

    def read_table(self, table_id, **kwargs):
        """读取多维表格中指定表格的数据

        :param table_id: 表格id
        :return:
        """
        rows = []
        res = self.list_records(table_id, **kwargs)["data"]
        total = res["total"]

        if total == 0:
            return pd.DataFrame()

        rows.extend(res["items"])
        while res["has_more"]:
            res = self.list_records(table_id, page_token=res["page_token"], **kwargs)["data"]
            rows.extend(res["items"])

        assert len(rows) == total, "数据读取异常"
        return pd.DataFrame([x["fields"] for x in rows])

    def empty_table(self, table_id, **kwargs):
        """清空多维表格中指定表格的数据，保留表头

        :param table_id: 表格id
        :return:
        """
        res = self.list_records(table_id, **kwargs)["data"]
        self.logger.info(f"{table_id} 表格中共有 {res['total']} 条数据")
        records = res["items"]
        if records:
            record_ids = [x["record_id"] for x in records]
            self.table_record_batch_delete(table_id, record_ids)
            self.logger.info(f"{table_id} 删除 {len(record_ids)} 条数据")

        while res["has_more"]:
            res = self.list_records(table_id, page_token=res["page_token"], **kwargs)["data"]
            records = res["items"]
            if records:
                record_ids = [x["record_id"] for x in records]
                self.table_record_batch_delete(table_id, record_ids)
                self.logger.info(f"{table_id} 删除 {len(record_ids)} 条数据")
