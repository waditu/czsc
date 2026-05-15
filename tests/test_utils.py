"""``czsc.utils`` 通用工具函数单元测试。

模块作者：
    zengbin93 (zeng_bin8888@163.com)
"""

from czsc.utils import freqs_sorted


def test_freqs_sorted_basic():
    """验证 ``freqs_sorted`` 按缠论惯用顺序对周期字符串去重并排序。

    测试场景：
        - 输入打乱顺序的周期列表，包含重复项
        - 应去重后按从高频到低频顺序输出

    关键断言：
        - ``'5分钟'`` 排在 ``'30分钟'`` 之前
        - ``'30分钟'`` 排在 ``'日线'`` 之前
        - 重复项被去重
    """
    result = freqs_sorted(["30分钟", "5分钟", "日线", "5分钟"])
    assert result == ["5分钟", "30分钟", "日线"]


def test_freqs_sorted_unknown_freq_to_tail():
    """验证未登记的周期被排到末尾，并按字典序作次级排序。"""
    result = freqs_sorted(["日线", "未知A", "5分钟", "未知B"])
    assert result[:2] == ["5分钟", "日线"]
    # 未登记的两个周期排在末尾，按字典序
    assert set(result[2:]) == {"未知A", "未知B"}
