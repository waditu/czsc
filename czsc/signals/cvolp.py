"""czsc.signals.cvolp —— 累积成交量分布（``cvolp_*``）信号命名空间。

本模块对外暴露所有以 ``cvolp_`` 为前缀的信号函数。CVOLP（Cumulative Volume Profile）
通过对一段时间内的成交量按价位分布进行累计统计，从而刻画筹码分布、价值区间
（VAH/VAL）、控制点（POC）等市场结构特征，常用于辅助判断支撑/阻力区域。

实现位置
========
真正的计算逻辑由 Rust 实现，源文件位于 ``crates/czsc-signals/src/cvolp.rs``，
通过 ``#[signal(...)]`` 宏在编译期登记到 ``inventory`` 全局表里。Python 端
仅做轻量级转发，避免 Python 解释器层面的开销。

调用约定
========
- 所有 ``cvolp_*_VyymmDD`` 函数都是“按需暴露”的：访问 ``czsc.signals.cvolp.cvolp_xxx_V230101``
  时由 :func:`__getattr__` 临时合成 Python 闭包；
- 闭包签名为 ``fn(czsc, params)``，其中 ``params`` 是参数字典；
- 返回值为 ``list[Signal]``；
- 使用 :func:`list_signals` 可枚举所有可用名称。
"""

from __future__ import annotations

from typing import Any

from czsc.signals._helpers import (
    get_signal_template as _get_signal_template,
)
from czsc.signals._helpers import (
    list_signals as _list_signals,
)
from czsc.signals._helpers import (
    make_signal_callable as _make_signal_callable,
)
from czsc.signals._helpers import (
    parse_signal_value as _parse_signal_value,
)

# 当前子模块对应的类别前缀；所有以 ``cvolp_`` 开头的信号会归到这里
_CATEGORY = "cvolp"


def list_signals() -> list[str]:
    """列出 Rust 清单中所有 ``cvolp_*`` 信号的名称。

    Returns
    -------
    list[str]
        以 ``cvolp_`` 为前缀的信号名称列表，按字典序排序。
    """
    return _list_signals(_CATEGORY)


def get_signal_template(name: str) -> str | None:
    """获取某个 ``cvolp_*`` 信号的参数模板字符串。

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
    """按需暴露每个已注册的 ``cvolp_*`` 信号为可调用对象。

    访问 ``czsc.signals.cvolp.cvolp_xxx_V230101`` 时本函数被自动触发；
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
        当 ``name`` 不属于 ``cvolp_*`` 信号或未在 Rust 清单中注册时抛出。
    """
    if name.startswith(_CATEGORY + "_") and name in _list_signals(_CATEGORY):
        return _make_signal_callable(name)
    raise AttributeError(f"module 'czsc.signals.cvolp' has no attribute {name!r}")


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
