"""czsc.traders.sig_parse —— 信号字符串解析与配置反解工具模块。

本模块提供一组面向信号字符串的解析、反向构造与频率提取工具，用于在
"信号字符串 ↔ 信号配置（dict）"两种表达之间进行往返转换。这些能力主要
被策略加载器、信号注册表与信号编辑器等上层组件使用，以便用户既能用紧凑
的字符串描述信号，也能在程序内部以结构化字典进行编辑、序列化与回放。

底层 ``derive_signals_config`` / ``derive_signals_freqs`` / ``list_all_signals``
均由 Rust 端 ``czsc._native`` 提供（已在 Phase F 完成迁移）；本模块只做
Python 侧的解析、模板格式化与配置展平等编排工作。

:class:`SignalsParser` 在初始化时调用 ``list_all_signals`` 拉取全量信号模板；
失败时退化为空注册表，上层调用方仍可顺利构造解析器，只是部分功能会返回空结果。
"""

from __future__ import annotations

import re
from typing import Any

from loguru import logger
from parse import parse

from czsc._native import (
    derive_signals_config,
    derive_signals_freqs,
    list_all_signals,
)


def _normalize_template(template: str) -> str:
    """规范化信号模板字符串，避免因换行/多余空白而无法解析。

    主要处理两类问题：
    1. 模板被人为换行后产生多余空白，导致 ``parse`` 无法匹配。
    2. ``_`` 两侧若残留空格，会让占位符与实际信号串对不齐。

    Args:
        template: 原始模板字符串；允许为 ``None`` 或空串。

    Returns:
        统一为单行、``_`` 两侧无空格的紧凑模板字符串。
    """
    # 把任意连续空白（含换行/制表符）压成单个空格，并去除首尾空白。
    text = re.sub(r"\s+", " ", template or "").strip()
    # 把 "_ x" 或 "x _" 这样的残留空格修正回紧凑形式。
    text = text.replace(" _", "_").replace("_ ", "_")
    return text



def _extract_signal_key(signal: Any) -> str:
    """从字符串或 Signal 对象中提取信号 key（前 3 段）。

    czsc 信号串遵循 ``"freq_k1_k2_v1_v2_v3_v4"`` 的 7 段约定，前 3 段
    为 key，后 4 段为 value。本函数兼容字符串与具备 ``key`` 属性的对象。

    Args:
        signal: 信号字符串或 ``Signal`` 实例。

    Returns:
        信号 key 字符串；当输入无法解析时返回空串。
    """
    if isinstance(signal, str):
        parts = signal.split("_")
        # 需要至少 3 段才能拼出有意义的 key；否则视为无效输入。
        return "_".join(parts[:3]) if len(parts) >= 3 else ""
    return str(getattr(signal, "key", "") or "")


class SignalsParser:
    """把扁平的信号字符串解析回 czsc 标准信号配置结构的解析器。

    解析器在初始化时会尝试通过 ``list_all_signals`` 拉取全量信号定义，
    建立"函数名 → 模板"的注册表；后续调用 ``parse_params`` /
    ``get_function_name`` / ``config_to_keys`` / ``parse`` 均依赖该注册表。

    当 ``list_all_signals`` 失败（如 Rust 扩展异常）时，注册表会被置空，
    此时各方法会按"找不到匹配模板"的语义返回空值，而不会抛出异常。
    """

    def __init__(self):
        """构建解析器并预加载信号模板注册表。"""
        # 三张本地注册表：分别保存模板字符串、k3 段（信号子类标识）以及
        # "k3 → 函数名列表"的反向索引，供后续解析与匹配使用。
        sig_pats_map: dict[str, str] = {}
        sig_k3_map: dict[str, str] = {}
        signal_defs: list[dict[str, Any]] = []

        try:
            # 尽力拉取全量信号定义；失败时降级为空注册表，不影响模块导入。
            signal_defs = list(list_all_signals(include_kline=True, include_trader=True))
        except Exception as exc:
            logger.warning(f"list_all_signals unavailable, using empty parser registry: {exc}")

        for item in signal_defs:
            name = str(item.get("name", "")).strip()
            template = _normalize_template(str(item.get("param_template", "")).strip())
            if not name or not template:
                # 信息不完整的条目无法用于解析，直接跳过。
                continue

            sig_pats_map[name] = template
            parts = template.split("_")
            if len(parts) >= 3:
                # k3 段是 czsc 信号体系中常用的"子分类"标识，用于反向查函数。
                sig_k3_map[name] = parts[2].strip()

        self.sig_pats_map = sig_pats_map
        self.sig_k3_map = sig_k3_map
        # 兼容旧版 API：保留 sig_name_map 字段（k3 → [函数名]）。
        self.sig_name_map = {k: [v] for k, v in sig_k3_map.items()}

    def parse_params(self, name: str, signal: str | Any):
        """根据指定信号函数模板，把信号 key 反解为函数参数字典。

        Args:
            name: 信号函数名或完整路径；只取末段进行注册表查找。
            signal: 信号字符串或具备 ``key`` 属性的 Signal 对象。

        Returns:
            包含函数调用所需参数的字典（含补全的 ``name`` 字段）；当输入
            非法、模板缺失或解析失败时返回 ``None``。
        """
        key = _extract_signal_key(signal)
        if not key:
            return None

        # 取模块名末段做注册表查找，兼容传入完整路径的情况。
        short_name = str(name).split(".")[-1]
        pats = self.sig_pats_map.get(short_name)
        if not pats:
            return None

        try:
            res = parse(pats, key)
            if not res:
                return None

            params = dict(res.named)
            if "di" in params:
                # di（distance index）按约定恒为整数，反解出来时仍是字符串，
                # 在此显式转回 int，避免下游再次手动转换。
                params["di"] = int(params["di"])
            params["name"] = short_name
            return params
        except Exception as exc:
            logger.error(f"failed to parse signal params for {signal} - {name}: {exc}")
            return None

    def get_function_name(self, signal: str):
        """根据信号字符串猜测对应的信号函数名。

        匹配优先级如下：

        1. 在本地注册表中按 k3 段精确匹配，若仅命中 1 个候选则返回；
        2. 命中多个候选时记录错误日志并返回 ``None``，避免歧义；
        3. 本地匹配失败时回退到 ``derive_signals_config`` 让 Rust 端做
           权威解析，并取其首条结果的函数名末段返回。

        Args:
            signal: 待识别的信号字符串。

        Returns:
            匹配到的函数名字符串；无法唯一确定时返回 ``None``。
        """
        key = _extract_signal_key(signal)
        if not key:
            return None

        parts = key.split("_")
        if len(parts) < 3:
            return None

        k3 = parts[2].strip()
        # 在本地注册表中按 k3 段做反向索引匹配。
        matches = [name for name, tk3 in self.sig_k3_map.items() if tk3 == k3]
        if len(matches) == 1:
            return matches[0]

        if len(matches) > 1:
            # 多函数共用相同 k3 时无法唯一定位，记录日志后放弃。
            logger.error(f"signal {signal} matched multiple functions: {matches}")
            return None

        try:
            # 本地匹配失败时，回退到 Rust 端的权威解析作为兜底。
            conf = derive_signals_config([signal])
            if conf:
                return str(conf[0]["name"]).split(".")[-1]
        except Exception:
            # 兜底失败保持静默（log 已在更底层打印），避免噪声。
            pass
        return None

    def config_to_keys(self, config: list[dict]):
        """利用模板把若干信号配置字典反向格式化为信号 key 字符串。

        Args:
            config: 信号配置字典列表；每项至少应包含 ``name`` 键，并提供
                模板占位符所需的全部参数键值。

        Returns:
            成功格式化的信号 key 字符串列表；模板缺失或格式化失败的项
            会被静默跳过，不会中断整体流程。
        """
        keys = []
        for conf in config:
            name = str(conf.get("name", "")).split(".")[-1]
            pats = self.sig_pats_map.get(name)
            if not pats:
                # 找不到模板的配置项无法重建 key，直接跳过。
                continue
            try:
                # 利用 str.format 将参数填回模板占位符，得到完整 key。
                keys.append(pats.format(**conf))
            except Exception:
                continue
        return keys

    def parse(self, signal_seq: list[str]):
        """把一组信号字符串解析成扁平化的信号配置列表。

        实现上首先把信号序列交给 ``derive_signals_config``（Rust 端）
        做权威解析，再在 Python 侧补齐模块前缀、展开 ``params`` 字段并
        去重，得到的结构可以直接用作 czsc 信号配置项。

        Args:
            signal_seq: 信号字符串序列。

        Returns:
            扁平化后的信号配置字典列表；输入为空或底层解析不可用时返回
            空列表。
        """
        if not signal_seq:
            return []

        try:
            conf = derive_signals_config(signal_seq)
        except Exception as exc:
            logger.error(f"derive_signals_config failed: {exc}")
            return []

        out: list[dict[str, Any]] = []
        for row in conf:
            raw = dict(row)
            item: dict[str, Any] = {"name": str(raw.get("name", ""))}
            if raw.get("freq"):
                item["freq"] = raw.get("freq")
            params = raw.get("params") or {}
            if isinstance(params, dict):
                # params 字段在配置层不嵌套，直接平铺到顶层方便后续使用。
                item.update(params)
            for key, value in raw.items():
                # 其余字段（如版本号、扩展元数据等）原样透传。
                if key not in {"name", "freq", "params"}:
                    item[key] = value
            if item not in out:
                # 最终结果按整条字典做去重，避免重复配置。
                out.append(item)
        return out


def get_signals_config(signals_seq: list[str]) -> list[dict]:
    """把信号字符串序列解析为扁平化的信号配置列表。

    Args:
        signals_seq: 信号字符串序列。

    Returns:
        扁平化后的信号配置字典列表；语义与 :meth:`SignalsParser.parse` 一致。
    """
    return SignalsParser().parse(signals_seq)


def get_signals_freqs(signals_seq: list) -> list[str]:
    """从信号序列中提取所有涉及到的 K 线周期。

    输入既可以是已经解析好的信号配置字典列表，也可以是原始的信号字符串
    列表；前者直接交给 ``derive_signals_freqs``，后者会先经过
    ``derive_signals_config`` 解析后再提取频率。

    Args:
        signals_seq: 信号字符串列表或信号配置字典列表。

    Returns:
        去重的 K 线周期字符串列表；输入为空时返回空列表。

    Notes:
        语义解析由 Rust 扩展 ``czsc._native.derive_signals_*`` 完成。
    """
    if not signals_seq:
        return []

    if isinstance(signals_seq[0], dict):
        # 输入已是字典形式（信号配置），直接交给 Rust 端提取频率。
        return list(derive_signals_freqs(signals_seq))
    # 输入为字符串信号时，先解析为配置字典再提取频率。
    conf = derive_signals_config(signals_seq)
    return list(derive_signals_freqs(conf))
