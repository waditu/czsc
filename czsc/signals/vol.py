"""czsc.signals.vol —— 成交量（``vol_*``）信号命名空间。

本模块对外暴露所有以 ``vol_`` 为前缀的信号函数，覆盖与“量”相关的常见判断，
例如成交量放大/缩小、量价配合、量能突破、相对历史均量的分位数等。这些信号
常与 ``cxt_*`` 结构信号、``tas_*`` 技术指标信号配合使用，用于辅助判断买卖
力量是否真实有效。

实现位置
========
真正的计算逻辑由 Rust 实现，源文件位于 ``crates/czsc-signals/src/vol.rs``，
通过 ``#[signal(...)]`` 宏在编译期登记到 ``inventory`` 全局表里。Python 端
仅做轻量级转发，避免 Python 解释器层面的开销。

调用约定
========
- 所有 ``vol_*_VyymmDD`` 函数都是“按需暴露”的：访问 ``czsc.signals.vol.vol_xxx_V230101``
  时由 :func:`__getattr__` 临时合成 Python 闭包；
- 闭包签名为 ``fn(czsc, params)``，其中 ``params`` 是参数字典；
- 返回值为 ``list[Signal]``；
- 使用 :func:`list_signals` 可枚举所有可用名称。
"""

from __future__ import annotations

from typing import Any

from czsc.signals._helpers import (
    get_signal_template as _get_signal_template,
    list_signals as _list_signals,
    make_signal_callable as _make_signal_callable,
    parse_signal_value as _parse_signal_value,
)

# 当前子模块对应的类别前缀；所有以 ``vol_`` 开头的信号会归到这里
_CATEGORY = "vol"


def list_signals() -> list[str]:
    """列出 Rust 清单中所有 ``vol_*`` 信号的名称。

    Returns
    -------
    list[str]
        以 ``vol_`` 为前缀的信号名称列表，按字典序排序。
    """
    return _list_signals(_CATEGORY)


def get_signal_template(name: str) -> str | None:
    """获取某个 ``vol_*`` 信号的参数模板字符串。

    Parameters
    ----------
    name : str
        完整的信号名称。

    Returns
    -------
    str | None
        参数模板字符串；若名称未注册，返回 ``None``。
    """
    return _get_signal_template(name)


def parse_signal_value(text: str) -> dict[str, Any]:
    """解析序列化的信号字符串，等价于 :func:`czsc.signals._helpers.parse_signal_value`。

    Parameters
    ----------
    text : str
        形如 ``"freq_name_value"`` 的字符串。

    Returns
    -------
    dict[str, Any]
        含 ``freq``、``name``、``value`` 三个键的字典。
    """
    return _parse_signal_value(text)


def __getattr__(name: str):
    """按需暴露每个已注册的 ``vol_*`` 信号为可调用对象。

    访问 ``czsc.signals.vol.vol_xxx_V230101`` 时本函数被自动触发；
    若名称在 Rust 清单中存在，则合成一个 Python 闭包返回；否则抛出
    :class:`AttributeError`，与普通模块属性查找语义保持一致。

    Parameters
    ----------
    name : str
        访问的属性名。

    Returns
    -------
    Callable
        对应 Rust 信号的 Python 派发闭包，调用后返回 ``list[Signal]``。

    Raises
    ------
    AttributeError
        当 ``name`` 不属于 ``vol_*`` 信号或未在 Rust 清单中注册时抛出。
    """
    if name.startswith(_CATEGORY + "_") and name in _list_signals(_CATEGORY):
        return _make_signal_callable(name)
    raise AttributeError(f"module 'czsc.signals.vol' has no attribute {name!r}")


def __dir__() -> list[str]:
    """自定义 ``dir()`` 输出，让 IDE / REPL 能看到所有动态暴露的信号。"""
    return [
        "list_signals",
        "get_signal_template",
        "parse_signal_value",
        *_list_signals(_CATEGORY),
    ]


# ``__all__`` 仅声明显式暴露的工具函数；具体信号函数按需通过 ``__getattr__`` 取得
__all__ = ["list_signals", "get_signal_template", "parse_signal_value"]
