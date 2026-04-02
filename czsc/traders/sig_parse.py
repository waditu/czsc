"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/3/29 10:04
describe: 基于 rs_czsc 的信号解析兼容层
"""

from __future__ import annotations

import re
from typing import Any

from loguru import logger
from parse import parse

from rs_czsc import derive_signals_config, derive_signals_freqs, list_all_signals


def _normalize_template(template: str) -> str:
    """规范化模板中的空白，避免文档换行导致解析失败。"""
    text = re.sub(r"\s+", " ", template or "").strip()
    text = text.replace(" _", "_").replace("_ ", "_")
    return text


def _prefix_name(name: str, signals_module: str) -> str:
    return name if "." in str(name) else f"{signals_module}.{name}"


class SignalsParser:
    """解析信号字符串并反推信号函数配置。"""

    def __init__(self, signals_module: str = "czsc.signals"):
        self.signals_module = signals_module

        sig_pats_map: dict[str, str] = {}
        sig_k3_map: dict[str, str] = {}

        for item in list_all_signals(include_kline=True, include_trader=True):
            name = str(item.get("name", "")).strip()
            template = _normalize_template(str(item.get("param_template", "")).strip())
            if not name or not template:
                continue
            sig_pats_map[name] = template

            parts = template.split("_")
            if len(parts) >= 3:
                sig_k3_map[name] = parts[2].strip()

        self.sig_pats_map = sig_pats_map
        self.sig_k3_map = sig_k3_map
        # 保留旧属性名，兼容历史调用
        self.sig_name_map = {k: [v] for k, v in sig_k3_map.items()}

    def parse_params(self, name: str, signal: str | Any):
        """根据信号函数名和信号字符串反推出参数。"""
        if isinstance(signal, str):
            parts = signal.split("_")
            if len(parts) < 3:
                return None
            key = "_".join(parts[:3])
        else:
            key = getattr(signal, "key", "")

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
                params["di"] = int(params["di"])
            params["name"] = _prefix_name(short_name, self.signals_module)
            return params
        except Exception as e:
            logger.error(f"解析信号 {signal} - {name} - {pats} 出错：{e}")
            return None

    def get_function_name(self, signal: str):
        """根据信号字符串匹配信号函数名。"""
        parts = str(signal).split("_")
        if len(parts) < 3:
            return None
        k3 = parts[2].strip()

        matches = [name for name, tk3 in self.sig_k3_map.items() if tk3 == k3]
        if len(matches) == 1:
            return matches[0]

        if len(matches) > 1:
            logger.error(f"信号 {signal} 有多个匹配函数：{matches}，请手动解析信号")
            return None

        # 回退到 rs_czsc 的官方反推能力
        try:
            conf = derive_signals_config([signal])
            if conf:
                return str(conf[0]["name"]).split(".")[-1]
        except Exception:
            pass
        return None

    def config_to_keys(self, config: list[dict]):
        """将信号函数配置转换为信号 key 列表。"""
        keys = []
        for conf in config:
            name = str(conf.get("name", "")).split(".")[-1]
            pats = self.sig_pats_map.get(name)
            if not pats:
                continue
            try:
                keys.append(pats.format(**conf))
            except Exception:
                continue
        return keys

    def parse(self, signal_seq: list[str]):
        """解析信号序列，返回可执行的信号配置列表。"""
        if not signal_seq:
            return []

        try:
            conf = derive_signals_config(signal_seq)
            out: list[dict[str, Any]] = []
            for row in conf:
                raw = dict(row)
                item: dict[str, Any] = {
                    "name": _prefix_name(str(raw.get("name", "")), self.signals_module),
                }
                if raw.get("freq"):
                    item["freq"] = raw.get("freq")
                params = raw.get("params") or {}
                if isinstance(params, dict):
                    item.update(params)
                # 兼容输入本身就是扁平结构
                for k, v in raw.items():
                    if k not in {"name", "freq", "params"}:
                        item[k] = v
                if item not in out:
                    out.append(item)
            return out
        except Exception as e:
            logger.error(f"derive_signals_config 解析失败：{e}")
            return []


def get_signals_config(signals_seq: list[str], signals_module: str = "czsc.signals") -> list[dict]:
    """获取信号列表对应的信号函数配置。"""
    sp = SignalsParser(signals_module=signals_module)
    return sp.parse(signals_seq)


def get_signals_freqs(signals_seq: list) -> list[str]:
    """获取信号列表对应的 K 线周期列表。"""
    if not signals_seq:
        return []

    try:
        if isinstance(signals_seq[0], dict):
            return list(derive_signals_freqs(signals_seq))
        conf = derive_signals_config(signals_seq)
        return list(derive_signals_freqs(conf))
    except Exception:
        # 兜底：从字符串内容中抽取常见周期
        from czsc.utils import sorted_freqs

        freqs = []
        for signal in signals_seq:
            _freqs = re.findall("|".join(sorted_freqs), str(signal))
            if _freqs:
                freqs.extend(_freqs)
        return [x for x in sorted_freqs if x in freqs]
