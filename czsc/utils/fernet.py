# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2024/07/11 12:39
describe: Fernet 加密解密
"""
import os
from typing import Union


def generate_fernet_key():
    """生成 Fernet key

    等价于：base64.urlsafe_b64encode(os.urandom(32))
    """
    from cryptography.fernet import Fernet

    key = Fernet.generate_key()
    return key.decode()


def fernet_encrypt(data: Union[dict, str], key: str = None) -> str:
    """加密文本/字典

    :param data: 需要加密的文本、字典
    :param key: Fernet key must be 32 url-safe base64-encoded bytes.
        推荐使用 generate_fernet_key() 生成
    :return: 加密后的文本
    """
    from cryptography.fernet import Fernet

    key = key or os.getenv("FERNET_KEY")
    cipher_suite = Fernet(key.encode())
    encrypted_text = cipher_suite.encrypt(str(data).encode()).decode()
    return encrypted_text


def fernet_decrypt(data: str, key: str = None, is_dict=False) -> str:
    """解密文本

    :param data: 需要解密的文本
    :param key: Fernet key must be 32 url-safe base64-encoded bytes.
        推荐使用 generate_fernet_key() 生成
    :param is_dict: 是否解密字典数据
    :return: 解密后的文本
    """
    from cryptography.fernet import Fernet

    key = key or os.getenv("FERNET_KEY")
    cipher_suite = Fernet(key.encode())
    decrypted_text = cipher_suite.decrypt(data.encode()).decode()
    return eval(decrypted_text) if is_dict else decrypted_text


def test():
    key = generate_fernet_key()
    # key = 'HYtUW7y0HOMQySGmOiDHztUGaHC-WnBVh-yqn11Tszw='
    text = {"account": "admin", "password": "123456"}
    encrypted = fernet_encrypt(text, key)
    decrypted = fernet_decrypt(encrypted, key, is_dict=True)
    assert text == decrypted, f"{text} != {decrypted}"
