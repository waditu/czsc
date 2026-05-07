"""``czsc.utils`` 通用工具函数单元测试。

本测试套件覆盖 ``czsc.utils`` 中若干通用工具函数的基础行为，包括数值四舍五入、
对称加密往返以及超时装饰器在正常与超时两种场景下的表现。

模块作者：
    zengbin93 (zeng_bin8888@163.com)，创建于 2022/2/16 20:31
"""

import time

import numpy as np
import pandas as pd

from czsc import utils
from czsc.utils import timeout_decorator


def test_x_round():
    """验证 ``utils.x_round`` 按指定小数位进行四舍五入的行为。

    测试场景：
        - 整数输入：保留 3 位小数应保持原值；
        - 浮点输入：分别在 3 / 4 / 5 位精度下校验截断与舍入结果。

    关键断言：
        ``x_round(1.000342, n)`` 在 n=3/4/5 时分别得到 1.0 / 1.0003 / 1.00034。
    """
    assert utils.x_round(100, 3) == 100
    assert utils.x_round(1.000342, 3) == 1.0
    assert utils.x_round(1.000342, 4) == 1.0003
    assert utils.x_round(1.000342, 5) == 1.00034


def test_fernet():
    """验证 Fernet 对称加密的 encrypt → decrypt 往返一致性。

    测试场景：
        1. 调用 ``generate_fernet_key`` 生成一把随机密钥；
        2. 使用该密钥对一个字典对象做 ``fernet_encrypt`` 加密；
        3. 再用同一密钥执行 ``fernet_decrypt`` 解密（``is_dict=True`` 表示
           还原为字典而非字符串）。

    关键断言：
        解密后得到的字典与原始字典完全相等，证明加密往返不损失信息。
    """
    from czsc.utils.crypto.fernet import fernet_decrypt, fernet_encrypt, generate_fernet_key

    key = generate_fernet_key()
    text = {"account": "admin", "password": "123456"}
    encrypted = fernet_encrypt(text, key)
    decrypted = fernet_decrypt(encrypted, key, is_dict=True)
    assert text == decrypted, f"{text} != {decrypted}"


def test_timeout_decorator_success():
    """验证超时装饰器在被装饰函数耗时小于阈值时正常返回结果。

    测试场景：
        定义一个执行约 1 秒的 ``fast_function``，并用 ``timeout_decorator(2)``
        装饰（超时阈值 2 秒）。

    关键断言：
        函数能够在阈值内正常完成并返回 ``"Completed"``。
    """

    @timeout_decorator(2)
    def fast_function():
        time.sleep(1)
        return "Completed"

    assert fast_function() == "Completed", "快速函数应该正常返回结果"


def test_timeout_decorator_timeout():
    """验证超时装饰器在被装饰函数耗时超过阈值时返回 None。

    测试场景：
        定义一个执行约 5 秒的 ``slow_function``，并用 ``timeout_decorator(1)``
        装饰（超时阈值 1 秒）。

    关键断言：
        装饰器在 1 秒后中止函数执行并返回 ``None``。
    """

    @timeout_decorator(1)
    def slow_function():
        time.sleep(5)
        return "Completed"

    assert slow_function() is None, "慢函数应该超时返回None"
