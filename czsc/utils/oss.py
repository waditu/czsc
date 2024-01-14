# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/6/6 13:56
describe: 阿里云OSS操作类
"""
import os
from loguru import logger
from tqdm import tqdm
try:
    import oss2
    from oss2.models import PartInfo
except:
    logger.warning("请安装 oss2 库，pip install oss2")
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from typing import List


class AliyunOSS:
    def __init__(self, access_key_id: str, access_key_secret: str, endpoint: str, bucket_name: str):
        """
        初始化AliyunOSS客户端。

        :param access_key_id: string, 阿里云账号AccessKey的ID。
        :param access_key_secret: string, 阿里云账号AccessKey的Secret。
        :param endpoint: string, OSS服务所在的区域的域名信息。
        :param bucket_name: string, 需要操作的Bucket的名称。
        """
        self.auth = oss2.Auth(access_key_id, access_key_secret)
        self.bucket = oss2.Bucket(self.auth, endpoint, bucket_name)

    def upload(self, filepath: str, oss_key: str, replace: bool = False) -> bool:
        """
        上传文件到OSS。

        :param filepath: string, 本地文件的路径。
        :param oss_key: string, 文件在OSS上的路径和名称。
        :param replace: boolean, 如果为True，将覆盖OSS上的同名文件。默认为False。
        :return: boolean, 如果上传成功，返回True；否则，返回False。
        """
        oss_key = oss_key.replace("\\", "/")
        dir_name = os.path.dirname(oss_key)
        if dir_name:
            self.create_folder(dir_name)

        if not replace and self.file_exists(oss_key):
            logger.info(f"{oss_key} exists in the bucket. Set replace=True to overwrite.")
            return False

        with open(filepath, "rb") as file:
            result = self.bucket.put_object(oss_key, file)
            if result.status == 200:
                logger.info(f"Upload {filepath} to {oss_key} successfully.")
                return True
            else:
                logger.error(f"Upload {filepath} to {oss_key} failed: {result.status}, {result.request_id}")
                return False

    def download(self, oss_key: str, filepath: str, replace: bool = False) -> bool:
        """
        从OSS下载文件。

        :param oss_key: string, 文件在OSS上的路径和名称。
        :param filepath: string, 本地存储文件的路径。
        :return: boolean, 如果下载成功，返回True；否则，返回False。
        """
        path = os.path.dirname(filepath)
        if not os.path.exists(path):
            os.makedirs(path)

        if not replace and os.path.exists(filepath):
            logger.info(f"{filepath} exists in the local. Set replace=True to overwrite.")
            return False

        result = self.bucket.get_object_to_file(oss_key, filepath)
        if result.status == 200:
            logger.info(f"Download {oss_key} to {filepath} successfully.")
            return True
        else:
            logger.error(f"Download {oss_key} to {filepath} failed: {result.status}, {result.request_id}")
            return False

    def delete_file(self, oss_key: str) -> bool:
        """
        从OSS删除文件。

        :param oss_key: string, 文件在OSS上的路径和名称。
        :return: boolean, 如果删除成功，返回True；否则，返回False.
        """
        result = self.bucket.delete_object(oss_key)
        if result.status == 204:
            logger.info(f"Delete {oss_key} successfully.")
            return True
        else:
            logger.error(f"Delete {oss_key} failed: {result.status}, {result.request_id}")
            return False

    def file_exists(self, oss_key: str) -> bool:
        """
        检查文件是否在OSS上存在。

        :param oss_key: string, 文件在OSS上的路径和名称。
        :return: boolean, 如果文件存在，返回True；否则，返回False.
        """
        return self.bucket.object_exists(oss_key)

    def get_file_stream(self, oss_key: str) -> BytesIO:
        """
        获取OSS上文件的数据流。

        :param oss_key: string, 文件在OSS上的路径和名称。
        :return: BytesIO, 文件的数据流。
        """
        result = self.bucket.get_object(oss_key)
        return BytesIO(result.read()) # type: ignore

    def create_folder(self, folder_path: str):
        """
        在OSS上创建文件夹。

        :param folder_path: string, 需要创建的文件夹的路径。
        """
        self.bucket.put_object(folder_path + "/", "")

    def list_files(self, prefix="", extensions=None):
        """
        列举OSS上的文件。

        :param prefix: string, 列举的文件前缀，默认为空。
        :param extensions: list, 需要列举的文件的后缀名，默认为空，表示列举所有文件。
        :return: list, 列举的文件的名称列表。
        """
        oss_keys = []
        for obj in tqdm(oss2.ObjectIterator(self.bucket, prefix=prefix), desc=f"List files of {prefix}"):
            if obj.key.endswith("/"):
                continue
            if extensions and not any(obj.key.endswith(ext) for ext in extensions):
                continue
            oss_keys.append(obj.key)
        return oss_keys

    def batch_upload(self, filepaths: List[str], oss_keys: List[str], replace: bool = False, threads: int = 5):
        """
        批量上传文件到OSS。

        :param filepaths: list, 本地文件的路径列表。
        :param oss_keys: list, 文件在OSS上的路径和名称列表。
        :param replace: boolean, 如果为True，将覆盖OSS上的同名文件。默认为False。
        :param threads: int, 并行上传的线程数。默认为5。
        """
        with ThreadPoolExecutor(max_workers=threads) as executor:
            for filepath, oss_key in tqdm(zip(filepaths, oss_keys), total=len(filepaths), desc="Uploading"):
                executor.submit(self.upload, filepath, oss_key, replace)

    def batch_download(self, oss_keys: List[str], local_paths: List[str], replace: bool = False, threads: int = 5):
        """
        批量从OSS下载文件。

        :param oss_keys: list, 文件在OSS上的路径和名称列表。
        :param local_paths: list, 本地存储文件的路径列表。
        :param threads: int, 并行下载的线程数。默认为5。
        """
        assert len(oss_keys) == len(local_paths), "The length of oss_keys and local_paths must be the same."
        with ThreadPoolExecutor(max_workers=threads) as executor:
            for oss_key, local_path in zip(oss_keys, local_paths):
                executor.submit(self.download, oss_key, local_path, replace)

    def multipart_upload(self, filepath: str, oss_key: str):
        """
        分块上传大文件到OSS。

        :param filepath: string, 本地文件的路径。
        :param oss_key: string, 文件在OSS上的路径和名称。
        """
        total_size = os.path.getsize(filepath)
        part_size = oss2.determine_part_size(total_size, preferred_size=100 * 1024)
        upload_id = self.bucket.init_multipart_upload(oss_key).upload_id
        parts = []
        with open(filepath, "rb") as file:
            part_number = 1
            offset = 0
            while offset < total_size:
                num_to_upload = min(part_size, total_size - offset)
                result = self.bucket.upload_part(oss_key, upload_id, part_number, file.read(num_to_upload))
                parts.append(PartInfo(part_number, result.etag))
                offset += num_to_upload
                part_number += 1
        self.bucket.complete_multipart_upload(oss_key, upload_id, parts)

    def download_folder(self, oss_folder: str, local_folder: str, threads: int = 5):
        """
        从OSS下载指定文件夹。

        :param oss_folder: string, OSS上的文件夹路径。
        :param local_folder: string, 本地存储文件夹的路径。
        :param threads: int, 并行下载的线程数。默认为5。
        """
        if not os.path.exists(local_folder):
            os.makedirs(local_folder)

        oss_keys = self.list_files(prefix=oss_folder)
        file_paths = []
        for oss_key in oss_keys:
            file_path = os.path.join(local_folder, oss_key.replace(oss_folder, "", 1).lstrip("/\\"))
            file_paths.append(file_path)
        self.batch_download(oss_keys, file_paths, threads)

    def upload_folder(self, local_folder: str, oss_folder: str, replace: bool = False, threads: int = 5):
        """
        上传本地文件夹到OSS。

        :param local_folder: string, 本地文件夹的路径。
        :param oss_folder: string, OSS上的目标文件夹路径。
        :param replace: boolean, 如果为True，将覆盖OSS上的同名文件。默认为False。
        :param threads: int, 并行上传的线程数。默认为5。
        """
        filepaths = []
        oss_keys = []
        for root, dirs, files in os.walk(local_folder):
            for filename in files:
                filepath = os.path.join(root, filename)
                filepaths.append(filepath)

                relative_path = os.path.relpath(filepath, local_folder)
                oss_key = os.path.join(oss_folder, relative_path)
                oss_keys.append(oss_key)

        logger.info(f"Uploading {local_folder} to {oss_folder}, {len(filepaths)} files in total.")
        self.batch_upload(filepaths, oss_keys, replace, threads)
        logger.info(f"Upload {local_folder} finished.")
