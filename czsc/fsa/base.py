# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/12/16 19:42
describe: 
"""
# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/12/5 19:02
describe: 飞书应用API接口封装
"""
import os
import time
import requests
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_random
from requests_toolbelt import MultipartEncoder

logger.disable(__name__)


@retry(stop=stop_after_attempt(3), wait=wait_random(min=1, max=5))
def request(method, url, headers, payload=None) -> dict:
    """飞书API标准请求

    :param method: 请求方法
    :param url: 请求地址
    :param headers: 请求头
    :param payload: 传参
    :return:
    """
    payload = {} if not payload else payload
    response = requests.request(method, url, headers=headers, json=payload)
    logger.info(f"{'+' * 88}")
    logger.info(f"URL: {url} || X-Tt-Logid: {response.headers['X-Tt-Logid']}")
    logger.info(f"headers: {headers}")
    logger.info(f"payload: {payload}")

    resp = {}
    if response.text[0] == '{':
        resp = response.json()
        logger.info(f"response: {resp}")
    else:
        logger.info(f"response: {response.text}")

    code = resp.get("code", -1)
    if code == -1:
        code = resp.get("StatusCode", -1)
    if code == -1 and response.status_code != 200:
        response.raise_for_status()
    if code != 0:
        logger.debug(f"request fail: code={code}, msg={resp.get('msg', '')}")
        raise ValueError(f"request fail: code={code}, msg={resp.get('msg', '')}")
    return resp


class FeishuApiBase:
    def __init__(self, app_id, app_secret):
        self.app_id = app_id
        self.app_secret = app_secret
        self.host = "https://open.feishu.cn"
        self.headers = {'Content-Type': 'application/json'}
        self.cache = dict()

    def get_access_token(self, key='app_access_token'):
        assert key in ['app_access_token', 'tenant_access_token']
        cache_key = 'access_token_data'
        data = self.cache.get(cache_key, {})

        if not data or time.time() - data['update_time'] > data['expire'] * 0.8:
            url = "https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal"
            data = request('POST', url, self.headers, {"app_id": self.app_id, "app_secret": self.app_secret})
            data['update_time'] = time.time()

        self.cache[cache_key] = data
        return data[key]

    def get_headers(self):
        headers = dict(self.headers)
        headers['Authorization'] = f"Bearer {self.get_access_token()}"
        return headers

    def get_root_folder_token(self):
        """获取飞书云空间根目录 token"""
        url = f"{self.host}/open-apis/drive/explorer/v2/root_folder/meta"
        resp = request("GET", url, self.get_headers())
        return resp['data']['token']

    def remove(self, token, kind):
        """删除用户在云空间内的文件或者文件夹。文件或者文件夹被删除后，会进入用户回收站里。

        https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/drive-v1/file/delete

        :param token:
        :param kind: 删除文件类型
            file        文件类型
            docx        新版文档类型
            bitable     多维表格类型
            folder      文件夹类型
            doc         文档类型
            sheet       电子表格类型
            mindnote    思维笔记类型
            shortcut    快捷方式类型
        :return:
        """
        url = f"{self.host}/open-apis/drive/v1/files/{token}?type={kind.lower()}"
        return request("DELETE", url, self.get_headers())

    def move(self, token, payload):
        """将文件或者文件夹移动到用户云空间的其他位置

        https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/drive-v1/file/move

        :param token:
        :param payload:
                {
                    "type": "file",
                    "folder_token": "fldbcO1UuPz8VwnpPx5a92abcef"
                }
        :return:
        """
        url = f"{self.host}/open-apis/drive/v1/files/{token}/move"
        return request("POST", url, self.get_headers(), payload=payload)

    def copy(self, token, payload):
        """将文件复制到用户云空间的其他文件夹中。不支持复制文件夹。

        https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/drive-v1/file/copy

        :param token:
        :param payload: 复制文件相关参数，样例如下
                {
                    "name": "name",
                    "type": "file",
                    "folder_token": "fldbcO1UuPz8VwnpPx5a92abcef"
                }
        :return:
        """
        url = f"{self.host}/open-apis/drive/v1/files/{token}/copy"
        return request("POST", url, self.get_headers(), payload=payload)

    def upload_file(self, file_path, parent_node):
        """向云空间指定目录下上传一个小文件

        https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/drive-v1/file/upload_all

        :param file_path: 本地文件绝对路径
        :param parent_node: 文件夹token，示例值："fldbcO1UuPz8VwnpPx5a92abcef"
        :return:
        """
        file_size = os.path.getsize(file_path)
        url = "https://open.feishu.cn/open-apis/drive/v1/files/upload_all"
        form = {'file_name': os.path.basename(file_path), 'parent_type': 'explorer',
                'parent_node': parent_node, 'size': str(file_size), 'file': (open(file_path, 'rb'))}
        multi_form = MultipartEncoder(form)
        headers = {'Authorization': f'Bearer {self.get_access_token()}', 'Content-Type': multi_form.content_type}
        response = requests.request("POST", url, headers=headers, data=multi_form)
        return response.json()['data']['file_token']

    def download_file(self, file_token, file_path):
        """使用该接口可以下载在云空间目录下的文件（不含飞书文档/表格/思维导图等在线文档）

        https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/drive-v1/file/download

        :param file_token: 文件 token
        :param file_path: 下载保存本地路径
        :return:
        """
        url = f"{self.host}/open-apis/drive/v1/files/{file_token}/download"
        res = requests.request("GET", url, headers=self.get_headers())
        with open(file_path, 'w') as f:
            f.write(res.text)
        return res
