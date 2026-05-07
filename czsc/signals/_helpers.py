"""czsc.signals.* 子包共享的内部辅助工具集。

本模块是 ``czsc.signals`` 各类别子模块（``bar`` / ``cxt`` / ``tas`` / ``vol`` /
``pressure`` / ``obv`` / ``cvolp``）共同依赖的基础设施层。所有子模块都通过
``__getattr__`` 这种“按需查找 + 懒加载”的方式将真正的信号函数暴露出来，
而真正的派发工作则委托给本文件中的薄封装。

底层接口对接
============
本模块从 :mod:`czsc._native`（Rust 扩展模块）中导入了四个核心接口：

* ``call_signal``           —— 真正的派发函数，接收 ``(name, czsc, params)``，
                                调用对应的 Rust 实现并返回 ``list[Signal]``。
* ``list_signal_names``     —— 返回 Rust ``inventory`` 中已注册的所有信号名称。
* ``get_signal_template``   —— 返回某个信号在 ``#[signal(...)]`` 宏中登记的
                                参数模板字符串，用于上层做参数说明展示。
* ``get_signal_category``   —— 返回某个信号所属的类别前缀（如 ``"bar"``）。

派发工作流概览
==============
1. 子模块在 ``__getattr__`` 中检测访问的属性名是否符合
   ``"<category>_<name>_VyymmDD"`` 这一信号命名约定；
2. 若符合，则调用 :func:`make_signal_callable` 动态合成一个 Python 闭包，
   闭包内部转发到 ``call_signal``；
3. 上层用户拿到这个闭包后，便可像普通 Python 函数那样调用 ``fn(czsc, params)``，
   屏蔽了 Rust 侧的复杂签名。

提供的工具
==========
* :func:`list_signals`         —— 列出所有（或某类别下的）信号名称。
* :func:`get_signal_template`  —— 查询单个信号的参数模板。
* :func:`get_signal_category`  —— 查询单个信号所属类别。
* :func:`parse_signal_value`   —— 把序列化字符串 ``"freq_name_value"`` 拆成结构化字典。
* :func:`make_signal_callable` —— 为某个 Rust 信号生成 Python 调用包装器。
"""

from __future__ import annotations

from typing import Any, Callable

# 从 Rust 扩展模块按需导入底层接口；使用 ``as _xxx`` 显式标注为内部依赖，避免被外部直接引用
from czsc._native import call_signal as _call_signal
from czsc._native import (
    get_signal_category as _get_signal_category,
)
from czsc._native import (
    get_signal_template as _get_signal_template,
)
from czsc._native import (
    list_signal_names as _list_signal_names,
)


def list_signals(category: str | None = None) -> list[str]:
    """列出 ``czsc-signals`` Rust 清单中已注册的信号名称。

    匹配规则按信号名第一个下划线之前的部分进行（即“类别前缀”），例如
    ``category="bar"`` 会返回所有以 ``bar_`` 开头的信号名。

    Parameters
    ----------
    category : str | None, optional
        类别前缀。例如 ``"bar"``、``"cxt"``、``"tas"`` 等；
        传入 ``None``（默认）时返回全部已注册信号，并按字典序排序。

    Returns
    -------
    list[str]
        信号名称列表，已按字典序排序。
    """
    return _list_signal_names(category)


def get_signal_template(name: str) -> str | None:
    """获取某个信号的参数模板字符串。

    参数模板由 Rust 端 ``#[signal(...)]`` 宏在编译期登记，描述了该信号支持的
    参数及其默认值，常用于做配置说明或动态构建 UI。

    Parameters
    ----------
    name : str
        完整的信号名称，如 ``"bar_amount_acc_V230214"``。

    Returns
    -------
    str | None
        若该名称已注册，返回其参数模板字符串；否则返回 ``None``。
    """
    return _get_signal_template(name)


def get_signal_category(name: str) -> str | None:
    """获取某个信号所属的类别前缀。

    返回的是信号名第一个下划线之前的部分，对应它隶属于
    ``czsc.signals.<category>`` 中的哪个子模块。

    Parameters
    ----------
    name : str
        完整的信号名称。

    Returns
    -------
    str | None
        类别前缀字符串（如 ``"bar"``、``"cxt"`` 等）；若该名称未注册，返回 ``None``。
    """
    return _get_signal_category(name)


def parse_signal_value(text: str) -> dict[str, Any]:
    """把序列化的信号字符串拆解为结构化字典。

    上层在持久化 K 线快照或回放交易状态时，往往以 ``"freq_signal_name_value"``
    这种 ``"_"`` 拼接形式存储信号；本函数负责把它还原成 ``{"freq", "name", "value"}``
    三元结构，便于后续过滤、对比与可视化。

    Parameters
    ----------
    text : str
        待解析的字符串。预期格式为 ``"freq_name_value"``，使用 ``_`` 作为分隔符。
        因为 ``value`` 自身可能含有 ``_``，所以最多只在前两个 ``_`` 处分割。

    Returns
    -------
    dict[str, Any]
        包含三个键的字典：

        - ``"freq"``: 周期标识（如 ``"30分钟"``、``"日线"`` 等）；
        - ``"name"``: 信号名称；
        - ``"value"``: 信号值字符串。

        当输入不足三段时，``freq`` 与 ``value`` 均回退为空字符串，
        ``name`` 则填回原始文本，便于下游做容错处理。
    """
    # 按 "_" 最多分成 3 段；避免 value 自身包含 "_" 时被错误切割
    parts = text.split("_", 2)
    if len(parts) < 3:
        # 字段数量不足时返回降级结果，保持调用方约定的字典结构不变
        return {"freq": "", "name": text, "value": ""}
    return {"freq": parts[0], "name": parts[1], "value": parts[2]}


def make_signal_callable(name: str) -> Callable[..., list[Any]]:
    """为指定的 Rust 信号合成一个 Python 调用包装器。

    返回的可调用对象签名为 ``fn(czsc, params=None)``，与 Rust 派发器保持一致：

    - ``czsc``  : 已构造完成的 :class:`czsc.CZSC` 分析对象；
    - ``params``: 信号参数字典；为 ``None`` 时会自动转成空字典 ``{}``，
                  避免 Rust 端在解参时出现空指针异常。

    包装器会把 ``__name__`` / ``__qualname__`` / ``__doc__`` 设置为有意义的
    元信息，让 Python 端的 ``help()``、IDE 跳转、序列化等内省行为表现自然。

    Parameters
    ----------
    name : str
        Rust 信号清单中的信号名称。

    Returns
    -------
    Callable[..., list[Any]]
        转发到 Rust 派发器的 Python 闭包，调用后返回 ``list[Signal]``。
    """

    # 提前查询参数模板，便于在文档字符串中展示，便于使用者快速了解参数格式
    template = _get_signal_template(name)

    def _wrapped(czsc, params: dict[str, Any] | None = None):
        # 真正的派发：把 None 兜底成空字典，避免 Rust 端做额外校验
        return _call_signal(name, czsc, params or {})

    # 将包装器伪装成原信号函数，方便上层做内省与日志输出
    _wrapped.__name__ = name
    _wrapped.__qualname__ = name
    if template is not None:
        _wrapped.__doc__ = (
            f"Rust 信号 {name!r} 的 Python 派发包装器。\n\n"
            f"参数模板（parameter template）: {template!r}\n\n"
            "调用方式: ``fn(czsc, params_dict)``，返回 ``list[Signal]``。"
        )
    return _wrapped
