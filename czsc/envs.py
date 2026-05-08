"""czsc.envs —— 极简环境变量适配层（spec §3.4）。

迁移到 Rust 后端后仅保留三项运行时参数：

- ``CZSC_VERBOSE``     —— 是否打印详细日志（True/False）
- ``CZSC_MIN_BI_LEN``  —— 笔的最小长度（去包含后的 K 线根数；默认 6）
- ``CZSC_MAX_BI_NUM``  —— 单个 CZSC 实例保留的最大笔数（默认 50）

约定：环境变量名同时接受全大写与全小写写法（大写优先），函数参数显式传值时
优先级最高（覆盖环境变量）。
"""

from __future__ import annotations

import os

# 被视为"真值"的字符串（小写化后比对，覆盖常见写法）
_VALID_TRUE = {"1", "true", "y", "yes"}


def _env(name: str, default: str | None = None) -> str | None:
    """读取环境变量，依次按 UPPER / lower 大小写降级。"""
    return os.environ.get(name.upper(), os.environ.get(name.lower(), default))


def _to_bool(v) -> bool:
    """把任意值宽松地转成 bool（None → False；字符串按 ``_VALID_TRUE`` 集合判定）。"""
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    return str(v).strip().lower() in _VALID_TRUE


def get_verbose(verbose=None) -> bool:
    """返回是否启用详细日志（``CZSC_VERBOSE`` 环境变量；显式参数优先）。"""
    return _to_bool(verbose if verbose is not None else _env("czsc_verbose"))


def get_min_bi_len(v: int | None = None) -> int:
    """返回笔最小长度（``CZSC_MIN_BI_LEN``；默认 6）。``int(float(...))`` 兼容 "6"/"6.0"/6.5 等输入。"""
    raw = v if v is not None else _env("czsc_min_bi_len", 6)
    return int(float(raw))


def get_max_bi_num(v: int | None = None) -> int:
    """返回单个 CZSC 实例的最大笔数（``CZSC_MAX_BI_NUM``；默认 50）。"""
    raw = v if v is not None else _env("czsc_max_bi_num", 50)
    return int(float(raw))
