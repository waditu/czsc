"""信号注册表 + ``derive_signals_*`` 系列工具的等价性测试。

本套件验证以下三件事在 ``rs_czsc`` 与 ``czsc`` 之间完全一致：

    * ``list_all_signals()`` 返回的描述符集合（数量、name、param_template、
      category 都必须相同）。
    * ``derive_signals_config(unique_signals)`` 根据信号字符串反推出的
      运行时配置 dict（结构等价，允许顺序差异）。
    * ``derive_signals_freqs(configs)`` 根据运行时配置推导出的 freq
      列表（排序后必须相等）。

这些工具直接决定了下游 ``run_research`` / ``OpensOptimize`` 等流程的
输入 shape，一旦不一致，会导致不可解释的下游差异。
"""

from __future__ import annotations


def test_list_all_signals_count_matches(rs_czsc_module, czsc_module):
    """注册表中信号数量必须一致。"""
    rs_list = rs_czsc_module.list_all_signals()
    czsc_list = czsc_module._native.list_all_signals()
    assert len(rs_list) == len(czsc_list), (
        f"signal count mismatch: rs_czsc={len(rs_list)} vs czsc={len(czsc_list)}"
    )


def test_list_all_signals_names_match(rs_czsc_module, czsc_module):
    """注册表中信号 name 集合必须严格一致。"""
    rs_names = sorted(d["name"] for d in rs_czsc_module.list_all_signals())
    czsc_names = sorted(d["name"] for d in czsc_module._native.list_all_signals())
    assert rs_names == czsc_names, (
        f"signal name set differs.\n"
        f"only in rs_czsc: {set(rs_names) - set(czsc_names)}\n"
        f"only in czsc:    {set(czsc_names) - set(rs_names)}"
    )


def test_list_all_signals_templates_match(rs_czsc_module, czsc_module):
    """每个信号的 param_template 字符串必须一致。

    模板字符串是渲染信号字符串的源头，任何差异都会被下游放大。
    """
    rs_map = {d["name"]: d.get("param_template") for d in rs_czsc_module.list_all_signals()}
    czsc_map = {d["name"]: d.get("param_template") for d in czsc_module._native.list_all_signals()}
    diffs = {
        name: (rs_map[name], czsc_map[name])
        for name in rs_map
        if rs_map[name] != czsc_map[name]
    }
    assert not diffs, f"param_template mismatches: {diffs}"


def test_list_all_signals_categories_match(rs_czsc_module, czsc_module):
    """每个信号的 category 必须一致（如 ``kline`` / ``trader`` 等）。"""
    rs_map = {d["name"]: d.get("category") for d in rs_czsc_module.list_all_signals()}
    czsc_map = {d["name"]: d.get("category") for d in czsc_module._native.list_all_signals()}
    assert rs_map == czsc_map


def test_derive_signals_config_matches(rs_czsc_module, czsc_module, sample_signal_strings):
    """``derive_signals_config`` 在两套实现间产出的配置必须等价。

    运行时配置以 list[dict] 形式输出，等价性按 (name, freq, sorted params)
    三元组的集合相等来判定 —— 顺序在两套实现中可能不同，但内容必须相同。
    """
    rs_cfg = rs_czsc_module._derive_signals_config_impl(sample_signal_strings)
    czsc_cfg = czsc_module.derive_signals_config(sample_signal_strings)

    def _canon(cfgs):
        return sorted(
            (
                cfg["name"],
                cfg.get("freq"),
                tuple(sorted((cfg.get("params") or {}).items())),
            )
            for cfg in cfgs
        )

    assert _canon(rs_cfg) == _canon(czsc_cfg)


def test_derive_signals_freqs_matches(rs_czsc_module, czsc_module, sample_signal_strings):
    """``derive_signals_freqs`` 输出的 freq 列表必须等价。

    通过 rs_czsc 先把信号字符串转成运行时配置，再让两套实现都推导
    freq 列表，保证它们的输入 shape 完全一致，差异只可能来自 freq
    推导逻辑本身。
    """
    runtime = rs_czsc_module._derive_signals_config_impl(sample_signal_strings)
    rs_freqs = sorted(rs_czsc_module._derive_signals_freqs_impl(runtime))
    czsc_freqs = sorted(czsc_module._native.derive_signals_freqs(runtime))
    assert rs_freqs == czsc_freqs
