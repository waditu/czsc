"""
Rust/Python 兼容层（Compatibility Shim）

本模块封装了 Python 端遗留数据结构与 Rust 后端（rs-czsc / wbt）所需运行时格式
之间的相互转换逻辑，是迁移阶段保持"老代码不改、底层换 Rust"的桥梁。

涵盖的转换族：
    1. 周期（Freq）字符串排序                    —— sort_freqs
    2. 信号配置（dict）                          —— signal_config_to_runtime / signal_config_to_public
    3. Position 序列化转 Rust 期望布局           —— position_dump_to_runtime
    4. K 线 list[RawBar] / DataFrame 标准化      —— bars_to_dataframe
    5. 候选事件结构归一                          —— normalize_candidate_event(s)
    6. JSON 读写                                 —— load_json / dump_json
    7. 字符串/字面量转义、信号 KV 拼接           —— py_escape_str / py_repr_*

设计原则：
    - 所有转换函数无副作用，输入不可变（统一通过 ``dict(x)`` / ``list(x)`` 复制）
    - 字段缺失走"宽进严出"策略：能用默认值兜底就兜底，无法兜底就显式 raise
    - 不在此引入业务依赖（仅依赖 stdlib 与 pandas），保持兼容层最小内聚
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pandas as pd

# 周期字符串到排序权重的映射表
# 数字越小代表越小级别（越高频），按此权重做稳定排序后，
# 同一策略中"小周期 -> 大周期"的展示顺序与缠论惯例一致。
# 未在本表中的周期会被赋值 10_000，并用字面量做次级排序兜底。
_FREQ_ORDER = {
    "Tick": 0,
    "逐笔": 0,
    "1分钟": 1,
    "2分钟": 2,
    "3分钟": 3,
    "4分钟": 4,
    "5分钟": 5,
    "6分钟": 6,
    "10分钟": 7,
    "12分钟": 8,
    "15分钟": 9,
    "20分钟": 10,
    "30分钟": 11,
    "60分钟": 12,
    "120分钟": 13,
    "240分钟": 14,
    "360分钟": 15,
    "日线": 16,
    "周线": 17,
    "月线": 18,
    "季线": 19,
    "年线": 20,
}


def sort_freqs(freqs: Iterable[str]) -> list[str]:
    """
    按缠论惯用顺序对周期字符串去重并排序

    参数:
        freqs: 任意可迭代的周期字符串集合（允许包含 None / 空串，会被过滤）

    返回:
        从高频到低频依次排列的去重后的周期字符串列表

    备注:
        - 未登记的周期会被排到末尾（权重 10_000），并按字典序作次级排序
        - 排序结果稳定，方便用于 UI 展示与日志输出对齐
    """
    unique = {str(x) for x in freqs if x}
    return sorted(unique, key=lambda x: (_FREQ_ORDER.get(x, 10_000), x))


def signal_config_to_runtime(cfg: dict[str, Any]) -> dict[str, Any]:
    """
    将"用户层"信号配置 dict 转换为 Rust 后端期望的运行时三段式结构

    用户在 Python 端常以两种风格书写信号配置：
        风格 A（带 ``params`` 子字典）:
            {"name": "tas.cci_V230402", "freq": "30分钟", "params": {"di": 1, "n": 14}}
        风格 B（参数与 name/freq 平铺在同一层）:
            {"name": "tas.cci_V230402", "freq": "30分钟", "di": 1, "n": 14}

    本函数把以上两种写法都归一为：
        {"name": "cci_V230402", "freq": "30分钟", "params": {"di": 1, "n": 14}}

    其中 ``name`` 会被 :func:`_strip_signal_name` 截断为最后一段（去模块前缀），
    便于 Rust 端按短名直接派发到信号实现。

    参数:
        cfg: 任意一种风格的信号配置 dict

    返回:
        三段式 dict（``name`` / ``freq`` / ``params``），可直接喂给 Rust API
    """
    # 风格 A：已经显式区分 params，仅做名称清洗与浅拷贝
    if "params" in cfg:
        return {
            "name": _strip_signal_name(cfg["name"]),
            "freq": cfg.get("freq"),
            "params": dict(cfg.get("params", {})),
        }

    # 风格 B：除 name/freq/signals_module/module 以外的所有键都视为参数
    # 这里之所以同时排除 signals_module 与 module，是因为不同代码版本曾用过两种命名，
    # 都属于"模块定位元信息"，不应进入 params。
    params = {}
    for key, value in cfg.items():
        if key in {"name", "freq", "signals_module", "module"}:
            continue
        params[key] = value
    return {
        "name": _strip_signal_name(cfg["name"]),
        "freq": cfg.get("freq"),
        "params": params,
    }


def signal_config_to_public(cfg: dict[str, Any], signals_module_name: str) -> dict[str, Any]:
    """
    将运行时三段式信号配置反向转换为"用户层平铺式"配置

    主要用途：
        - 把 Rust 内部存储的紧凑配置对外展示给用户（如 dump 到 JSON）
        - 当 ``name`` 缺少模块前缀时，用 ``signals_module_name`` 自动补齐，
          保证导出的配置可被独立加载（无需依赖外部上下文）

    参数:
        cfg: 任意风格的信号配置（先经 :func:`signal_config_to_runtime` 归一）
        signals_module_name: 信号实现所在模块名，用于补全 name 前缀；为空则不补

    返回:
        平铺式 dict，name/freq 在外层，参数与之同级
    """
    runtime = signal_config_to_runtime(cfg)
    name = runtime["name"]
    # 若 name 不含点号，说明缺少模块前缀；按 signals_module_name 补全为完整路径
    if signals_module_name and "." not in name:
        name = f"{signals_module_name}.{name}"
    out = {"name": name, "freq": runtime.get("freq")}
    out.update(runtime.get("params", {}))
    return out


def position_dump_to_runtime(payload: dict[str, Any]) -> dict[str, Any]:
    """
    将 Position 的 JSON dump 结果转换为 Rust 运行时期望的事件/信号格式

    Python 端 Position 的 ``opens`` / ``exits`` 字段中，每个 Event 的
    ``signals_all`` / ``signals_any`` / ``signals_not`` 元素既可能是
    ``"key_value"`` 字符串，也可能是 ``{"key": ..., "value": ...}`` 字典。
    Rust 端只接受字符串形式，本函数统一转为字符串。

    参数:
        payload: Position.dump() 的输出（dict 形式）

    返回:
        浅拷贝后的 dict，opens/exits 内的信号字段已全部规范化为字符串列表
    """
    out = dict(payload)
    # 同时处理"开仓事件"与"平仓事件"两个分支
    for event_key in ("opens", "exits"):
        events = []
        for event in list(out.get(event_key) or []):
            event_copy = dict(event)
            # 三种信号关系字段：必须存在但允许为空列表
            for sig_key in ("signals_all", "signals_any", "signals_not"):
                event_copy[sig_key] = [signal_kv_to_string(sig) for sig in list(event_copy.get(sig_key) or [])]
            events.append(event_copy)
        out[event_key] = events
    return out


def bars_to_dataframe(bars: Any, symbol: str | None = None) -> pd.DataFrame:
    """
    将多种形式的 K 线表示统一转换为 Rust IPC 读取器期望的 DataFrame

    支持的输入：
        - ``pd.DataFrame`` —— 直接拷贝并补齐缺失列
        - ``list[RawBar]`` / ``tuple[RawBar]`` —— 通过 getattr 读取属性逐行构造

    输出契约（必须严格满足，否则 Rust 端反序列化会报错）：
        列顺序：``["symbol", "dt", "open", "close", "high", "low", "vol", "amount"]``
        类型：
            symbol -> str
            dt     -> datetime64[ns]
            其余 6 列 -> float64
        清洗：
            - 任一关键列为 NaN 的行会被丢弃
            - 同一时间戳重复时保留最后一条（last write wins）
            - 按 dt 升序排列、重置索引

    参数:
        bars: K 线集合（DataFrame 或 RawBar 列表）
        symbol: 当 bars 中缺少 symbol 列或部分缺失时用于回填的标的代码

    返回:
        规范化后的 DataFrame，可直接传入 Rust IPC 读取通道

    异常:
        TypeError: bars 类型不在支持列表中
        ValueError: 缺少必需列（dt 或转换后仍然缺失的其他列）
    """
    if isinstance(bars, pd.DataFrame):
        out = bars.copy()
    elif isinstance(bars, (list, tuple)):
        # 遍历对象列表，按字段名取值；缺失字段则使用 None 占位，后续 dropna 兜底
        rows = []
        for bar in bars:
            rows.append(
                {
                    "symbol": getattr(bar, "symbol", symbol),
                    "dt": getattr(bar, "dt", None),
                    "open": getattr(bar, "open", None),
                    "close": getattr(bar, "close", None),
                    "high": getattr(bar, "high", None),
                    "low": getattr(bar, "low", None),
                    "vol": getattr(bar, "vol", None),
                    "amount": getattr(bar, "amount", None),
                }
            )
        out = pd.DataFrame(rows)
    else:
        raise TypeError(f"unsupported bars type: {type(bars)!r}")

    # 兜底补齐 symbol 列：完全缺失就整列填充；部分缺失（NaN）就用 fillna 回填
    if "symbol" not in out.columns:
        out["symbol"] = symbol
    elif symbol:
        out["symbol"] = out["symbol"].fillna(symbol)

    # dt 是核心字段，必须存在；缺失意味着源数据本身有问题，立即报错
    if "dt" not in out.columns:
        raise ValueError("bars is missing dt column")

    # amount（成交额）允许由 vol*close 推算得出，方便上游只提供成交量的场景
    if "amount" not in out.columns:
        out["amount"] = out["vol"] * out["close"]

    # 二次校验：所有必需列必须齐全
    required = ["symbol", "dt", "open", "close", "high", "low", "vol", "amount"]
    missing = [col for col in required if col not in out.columns]
    if missing:
        raise ValueError(f"bars is missing columns: {missing}")

    out = out[required].copy()
    out["dt"] = pd.to_datetime(out["dt"])
    out["symbol"] = out["symbol"].astype(str)
    for col in ["open", "close", "high", "low", "vol", "amount"]:
        # 强制转 float64：Rust IPC 读取器要求六个数值列均为 Float64；
        # 而 wbt 提供的 mock 数据中 vol 默认是 int64，不显式转换会导致类型错误。
        out[col] = pd.to_numeric(out[col], errors="coerce").astype("float64")
    # 删除关键字段缺失的脏行，按 dt 升序去重并重置索引
    out = out.dropna(subset=["dt", "open", "close", "high", "low", "vol", "amount"])
    out = out.sort_values("dt").drop_duplicates(subset=["dt"], keep="last").reset_index(drop=True)
    return out


def normalize_candidate_event(event: dict[str, Any]) -> dict[str, Any]:
    """
    将一个候选 Event 字典归一化为标准结构

    历史上 Event 配置出现过两种风格：
        1. 旧风格：信号关系字段位于 ``factors[0]`` 子节点中
        2. 新风格：信号关系字段直接在 Event 顶层

    本函数统一两种写法，输出固定结构，便于上游统一处理：
        {
            "name": str,            # Event 名称（缺失时退回到 factors[0].name；再缺失为空串）
            "operate": str,         # 操作类型（必须存在，否则触发 KeyError）
            "signals_all": list,    # 必须全部命中
            "signals_any": list,    # 至少一个命中
            "signals_not": list,    # 必须全部不命中
        }

    参数:
        event: 任意风格的候选事件 dict

    返回:
        标准化后的浅拷贝 dict
    """
    raw = dict(event)
    # 取出旧风格的 factors[0]，若存在则其内的信号字段作为退路
    factors = list(raw.get("factors") or [])
    factor = dict(factors[0]) if factors else {}

    # "顶层优先、factor 兜底"的取值策略，兼容两种风格
    signals_all = list(raw.get("signals_all") or factor.get("signals_all") or [])
    signals_any = list(raw.get("signals_any") or factor.get("signals_any") or [])
    signals_not = list(raw.get("signals_not") or factor.get("signals_not") or [])
    name = raw.get("name") or factor.get("name") or ""

    return {
        "name": name,
        "operate": raw["operate"],
        "signals_all": signals_all,
        "signals_any": signals_any,
        "signals_not": signals_not,
    }


def normalize_candidate_events(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """批量调用 :func:`normalize_candidate_event`，返回标准化后的事件列表"""
    return [normalize_candidate_event(event) for event in events]


def md5_upper8(value: str) -> str:
    """
    计算字符串 MD5 哈希并截取前 8 位大写表示

    用途：
        生成简短、可复现的标识符（信号 ID、缓存 key 等），无加密强度要求。
        若有抗碰撞需求，请改用 SHA-256 等更长哈希。
    """
    return hashlib.md5(value.encode("utf-8")).hexdigest()[:8].upper()


def py_escape_str(value: str) -> str:
    """
    转义字符串中的反斜杠和单引号，便于嵌入 Python 源代码字面量

    应用场景：把动态生成的字符串拼接进代码模板（如生成策略骨架文件），
    避免引号冲突和路径中的反斜杠被解释为转义符。
    """
    return value.replace("\\", "\\\\").replace("'", "\\'")


def py_repr_list_str(items: list[str]) -> str:
    """
    将字符串列表渲染为 Python 字面量形式的源码片段

    示例:
        ['abc', "x'y"]  ->  "['abc', 'x\\'y']"

    空列表直接返回 ``"[]"``，避免输出 ``"[\n]"`` 等空白扰动。
    """
    if not items:
        return "[]"
    return "[" + ", ".join(f"'{py_escape_str(item)}'" for item in items) + "]"


def py_repr_json(value: Any) -> str:
    """
    将任意 JSON 兼容值递归渲染为 Python 字面量字符串

    与 ``repr()`` 的差异：
        - 总是使用单引号包裹字符串，便于嵌入双引号 docstring
        - 对反斜杠和单引号执行 :func:`py_escape_str` 转义，避免破坏代码结构
        - bool 单独处理，避免被 isinstance(_, int) 分支错误吞掉（True/False 是 int 的子类）

    支持类型: None / bool / int / float / str / list / dict
    其他类型走 str(value) 后递归处理（兜底）。
    """
    if value is None:
        return "None"
    if isinstance(value, bool):
        # 必须放在 int 检查之前：bool 是 int 的子类，否则会被当成 0/1 输出
        return "True" if value else "False"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return f"'{py_escape_str(value)}'"
    if isinstance(value, list):
        return "[" + ", ".join(py_repr_json(item) for item in value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"'{py_escape_str(str(key))}': {py_repr_json(val)}" for key, val in value.items()) + "}"
    # 兜底：把非典型类型按字符串处理，再走一次递归
    return py_repr_json(str(value))


def load_json(path: str | Path) -> dict[str, Any]:
    """读取 UTF-8 编码的 JSON 文件并解析为 dict（不做异常包装，由调用方处理 IO/解析错误）"""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump_json(path: str | Path, payload: dict[str, Any]) -> None:
    """
    将 dict 序列化为 UTF-8 编码的 JSON 文件

    使用 ``ensure_ascii=False`` 保留中文字符的可读性，
    便于人工查看与版本控制 diff（不会出现一堆 ``\\uXXXX``）。
    """
    Path(path).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _strip_signal_name(name: str) -> str:
    """
    截取信号 name 中以最后一个 ``.`` 分隔的末段

    示例:
        "czsc.signals.tas.cci_V230402" -> "cci_V230402"
        "cci_V230402"                   -> "cci_V230402"

    Rust 端按短名直接派发到信号实现，因此调用底层前需要剥离模块前缀。
    """
    return str(name).split(".")[-1]


def signal_kv_to_string(signal: dict[str, Any] | str) -> str:
    """
    将信号的 ``{"key": ..., "value": ...}`` 字典形式合并为 ``"key_value"`` 字符串

    若入参已经是字符串则原样返回，便于在批量处理时统一调用而不必预判类型。
    Rust 端只接受字符串形式的信号匹配条件，故所有 Python 端的信号最终都会经此函数。
    """
    if isinstance(signal, str):
        return signal
    return f"{signal['key']}_{signal['value']}"
