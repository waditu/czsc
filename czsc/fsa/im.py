# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/1/12 10:30
describe: 即时消息
"""
import json
import os
import requests
from czsc.fsa.base import FeishuApiBase, request, MultipartEncoder


class IM(FeishuApiBase):
    """即时消息发送"""

    def __init__(self, app_id, app_secret):
        super().__init__(app_id, app_secret)

    def get_user_id(self, payload, user_id_type='open_id'):
        """获取用户ID

        https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/contact-v3/user/batch_get_id

        :param user_id_type:
        :param payload:
        :return:
        """
        url = f"https://open.feishu.cn/open-apis/contact/v3/users/batch_get_id?user_id_type={user_id_type}"
        res = request('POST', url, headers=self.get_headers(), payload=payload)
        return res

    def upload_im_file(self, file_path, file_type='stream'):
        """上传文件，文件大小不得超过30M，且不允许上传空文件

        https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/im-v1/file/create

        :param file_path: 文件路径，推荐使用绝对路径
        :param file_type: 文件格式
            opus：上传opus音频文件；其他格式的音频文件，请转为opus格式后上传，转换方式可参考：ffmpeg -i SourceFile.mp3 -acodec libopus -ac 1 -ar 16000 TargetFile.opus
            mp4：上传mp4视频文件
            pdf：上传pdf格式文件
            doc：上传doc格式文件
            xls：上传xls格式文件
            ppt：上传ppt格式文件
            stream：上传stream格式文件。若上传文件不属于以上类型，可以使用stream格式
        :return: file_key
        """
        url = "https://open.feishu.cn/open-apis/im/v1/files"
        form = {'file_name': os.path.basename(file_path), 'file_type': file_type, 'file': (open(file_path, 'rb'))}
        multi_form = MultipartEncoder(form)
        headers = {'Authorization': f'Bearer {self.get_access_token()}', 'Content-Type': multi_form.content_type}
        response = requests.request("POST", url, headers=headers, data=multi_form)
        return response.json()['data']['file_key']

    def upload_im_image(self, image_path, image_type='message'):
        """上传图片接口

        支持上传 JPEG、PNG、WEBP、GIF、TIFF、BMP、ICO格式图片，图片大小不得超过10M，且不支持上传大小为0的图片。
        https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/im-v1/image/create

        :param image_path: 图片路径，推荐使用绝对路径
        :param image_type: 图片类型
            message：用于发送消息
            avatar：用于设置头像
        :return: image_key
        """
        url = "https://open.feishu.cn/open-apis/im/v1/images"
        form = {'image_type': image_type, 'image': (open(image_path, 'rb'))}
        multi_form = MultipartEncoder(form)
        headers = {'Authorization': f'Bearer {self.get_access_token()}', 'Content-Type': multi_form.content_type}
        response = requests.request("POST", url, headers=headers, data=multi_form)
        return response.json()['data']['image_key']

    def send(self, payload, receive_id_type='open_id'):
        """发送消息

        API介绍：https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/im-v1/message/create
        请求体构建: https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/im-v1/message/create_json
        """
        if isinstance(payload['content'], dict):
            payload['content'] = json.dumps(payload['content'])
        url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={receive_id_type}"
        res = request('POST', url, headers=self.get_headers(), payload=payload)
        return res

    def send_text(self, text, receive_id, receive_id_type='open_id'):
        """发送文本消息

        :param text: 文本内容
        :param receive_id: 接收者ID
        :param receive_id_type: ID类型
        :return:
        """
        payload = {"receive_id": receive_id, "content": {"text": text}, "msg_type": "text"}
        return self.send(payload, receive_id_type)

    def send_image(self, image_path, receive_id, receive_id_type='open_id'):
        """发送图片

        :param image_path: 图片路径
        :param receive_id: 接收者ID
        :param receive_id_type: ID类型
        :return:
        """
        image_key = self.upload_im_image(image_path, image_type='message')
        payload = {"receive_id": receive_id, "content": {"image_key": image_key}, "msg_type": "image"}
        return self.send(payload, receive_id_type)

    def send_file(self, file_path, receive_id, receive_id_type='open_id'):
        """发送文件

        :param file_path: 图片路径
        :param receive_id: 接收者ID
        :param receive_id_type: ID类型
        :return:
        """
        file_key = self.upload_im_file(file_path, file_type='stream')
        payload = {"receive_id": receive_id, "content": {"file_key": file_key}, "msg_type": "file"}
        return self.send(payload, receive_id_type)
