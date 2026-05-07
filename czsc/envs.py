"""
czsc.envs —— 极简环境变量适配层（迁移到 Rust 后保留版本）

背景与定位:
    迁移到 Rust 后端之后，原本的"Python 回退开关"已经下线（Phase H 之后
    Python 端不再保留任何缠论核心算法的回退实现，所有调用都走 Rust）。
    因此运行时参数被裁剪到仅剩三项，全部用于配置 czsc-core 的分析行为或
    日志详尽程度。

环境变量命名约定:
    1. 推荐使用全大写形式（如 ``CZSC_MIN_BI_LEN``）
    2. 出于历史兼容性，也接受全小写形式（如 ``czsc_min_bi_len``）
    3. 当大小写两种形式都设置时，**大写形式优先**
    4. 函数参数 v 显式传入时，优先级最高（覆盖环境变量）

可读取的环境变量:
    - CZSC_VERBOSE      —— 是否打印详细日志（True/False）
    - CZSC_MIN_BI_LEN   —— 笔的最小长度（含包含处理后 K 线根数）
    - CZSC_MAX_BI_NUM   —— 单个 CZSC 实例保留的最大笔数
"""

from __future__ import annotations

import os

# 被视为"真值"的字符串集合（大小写不敏感，比较前会先 lower 化）
# 列举常见写法，避免用户因大小写或缩写导致开关不生效
_VALID_TRUE = {"1", "true", "y", "yes"}


def _env(name: str, default: str | None = None) -> str | None:
    """
    带大小写兜底的环境变量读取

    优先级:
        1. 全大写形式（如 ``NAME``）
        2. 全小写形式（如 ``name``）
        3. 调用方提供的 default

    保留小写形式纯属向后兼容；新代码请只使用大写命名。
    """
    return os.environ.get(name.upper(), os.environ.get(name.lower(), default))


def _to_bool(v) -> bool:
    """
    宽松版"任意值 -> bool" 转换

    规则:
        - bool 直接原样返回（避免 ``True/False`` 被字符串化后重判一次）
        - None 视为 False
        - 其他对象先 ``str()`` 再 strip + lower，比对 ``_VALID_TRUE`` 集合

    用于解析"用户填写的环境变量值是否启用某开关"的场景，
    比 ``bool(s)``（任意非空字符串都为 True）更符合直觉。
    """
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    return str(v).strip().lower() in _VALID_TRUE


def get_verbose(verbose=None) -> bool:
    """
    判断是否启用详细日志输出

    参数:
        verbose: 显式传入的开关值；若为 None 则读取环境变量 ``CZSC_VERBOSE``

    返回:
        bool；任何被 :func:`_to_bool` 视为真值的输入都会返回 True
    """
    return _to_bool(verbose if verbose is not None else _env("czsc_verbose"))


def get_min_bi_len(v: int | None = None) -> int:
    """
    获取笔的最小长度（去包含后的 K 线根数）

    取值含义:
        6 —— 新规范，要求笔至少跨越 6 根去包含后的 K 线
        7 —— 旧规范，部分历史策略仍依赖此设置以维持原始走势识别口径

    参数:
        v: 显式传入的最小笔长度；若为 None 则读取 ``CZSC_MIN_BI_LEN``，
           都未提供时使用默认值 6

    返回:
        int 形式的最小笔长度

    备注:
        ``int(float(raw))`` 是为兼容 ``"6"`` / ``"6.0"`` / ``6.5`` 等多种
        字符串/数值书写形式，统一在小数点截断后再转 int。
    """
    raw = v if v is not None else _env("czsc_min_bi_len", 6)
    return int(float(raw))


def get_max_bi_num(v: int | None = None) -> int:
    """
    获取单个 CZSC 实例保留的最大笔数

    参数:
        v: 显式传入的上限值；若为 None 则读取 ``CZSC_MAX_BI_NUM``，
           都未提供时默认 50

    返回:
        int 形式的最大笔数

    备注:
        - 用途：回放/实时计算时只保留最近 N 笔，避免内存与计算量随时间无界增长
        - 取值过小会丢掉中长周期信号；过大会增加每根 K 线的更新成本
    """
    raw = v if v is not None else _env("czsc_max_bi_num", 50)
    return int(float(raw))
