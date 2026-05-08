"""缠论核心分析器（FX / BI）等价性测试。

本测试用例覆盖整个缠论核心算法的输出：在固定随机种子的 mock K 线数据
上，要求 ``czsc.CZSC`` 的分型列表（fx_list）、笔列表（bi_list）等关键
输出与 ``rs_czsc.CZSC`` 完全一致（容差为 0）。

这是迁移正确性的最强保证之一：只要这套测试通过，意味着所有依赖 CZSC
分析结果的下游工具（信号、回测、优化）就拥有了一致的输入基础。
"""

from __future__ import annotations


def _build_bars(module, mock_df):
    """通过模块自身的 ``format_standard_kline`` 把 mock DataFrame 转成 RawBar 列表。

    把转换过程放进每个模块各自完成，可以让 parity 测试同时覆盖各自的
    bar 构造路径，而不是只比较共享的 Rust 内部状态。
    """
    freq = module.Freq.D
    return module.format_standard_kline(mock_df, freq=freq)


def _bi_to_dict(bi):
    """把单个 BI（笔）对象快照成 JSON 友好的 dict，便于结构化对比。"""
    return {
        "direction": str(bi.direction),
        "high": bi.high,
        "low": bi.low,
        "sdt": str(bi.sdt),
        "edt": str(bi.edt),
        "fx_a_dt": str(bi.fx_a.dt),
        "fx_b_dt": str(bi.fx_b.dt),
    }


def _fx_to_dict(fx):
    """把单个 FX（分型）对象快照成 JSON 友好的 dict。"""
    return {
        "mark": str(fx.mark),
        "high": fx.high,
        "low": fx.low,
        "dt": str(fx.dt),
    }


def _zs_to_dict(zs):
    """把单个 ZS（中枢）对象快照成 JSON 友好的 dict（保留接口，用于以后扩展）。"""
    return {
        "zg": zs.zg,
        "zd": zs.zd,
        "gg": zs.gg,
        "dd": zs.dd,
        "sdt": str(zs.sdt),
        "edt": str(zs.edt),
    }


def _czsc_snapshot(module, mock_df):
    """对 ``module.CZSC(bars)`` 取一份完整快照，便于跨模块对比。

    返回字段：fxs、bi_list、freq、symbol、max_bi_num。
    备注：PyO3 暴露的 CZSC 类没有 ``zs_list`` 访问器（中枢推理目前在
    trader 信号层完成），因此这里不快照中枢。
    """
    bars = _build_bars(module, mock_df)
    c = module.CZSC(bars)
    return {
        "fxs": [_fx_to_dict(f) for f in c.fx_list],
        "bi_list": [_bi_to_dict(b) for b in c.bi_list],
        "freq": str(c.freq),
        "symbol": c.symbol,
        "max_bi_num": c.max_bi_num,
    }


def test_czsc_analyzer_outputs_match(rs_czsc_module, czsc_module, mock_kline_df):
    """缠论核心算法在 mock 数据上的输出必须与 rs_czsc 完全一致。

    测试场景：
        * 用同一份 fixed-seed 的 mock 日线 K 线分别构造两套 CZSC 对象
        * 对比 freq/symbol/max_bi_num 等元数据
        * 对比 fx_list、bi_list 的长度与逐元素内容

    关键断言：
        * 元数据完全相等
        * fx_list 长度与每一项内容完全相等
        * bi_list 长度与每一项内容完全相等
    """
    rs_snapshot = _czsc_snapshot(rs_czsc_module, mock_kline_df)
    czsc_snapshot = _czsc_snapshot(czsc_module, mock_kline_df)

    assert rs_snapshot["freq"] == czsc_snapshot["freq"]
    assert rs_snapshot["symbol"] == czsc_snapshot["symbol"]
    assert rs_snapshot["max_bi_num"] == czsc_snapshot["max_bi_num"]

    # 分型列表长度先做长度断言以提供更清晰的失败信息
    assert len(rs_snapshot["fxs"]) == len(czsc_snapshot["fxs"]), (
        f"fx_list length differs: rs={len(rs_snapshot['fxs'])} czsc={len(czsc_snapshot['fxs'])}"
    )
    assert rs_snapshot["fxs"] == czsc_snapshot["fxs"], "fx_list content diverges"

    # 笔列表同理
    assert len(rs_snapshot["bi_list"]) == len(czsc_snapshot["bi_list"])
    assert rs_snapshot["bi_list"] == czsc_snapshot["bi_list"], "bi_list content diverges"


def test_czsc_class_identity(rs_czsc_module, czsc_module):
    """两套实现必须暴露相同的公共类名集合。

    注意：实际的类对象不需要相同（它们来自不同的 cdylib），但公共 API
    表面上的名字必须一致，以保证下游用户的代码可以无差别地切换两套
    实现。

    关键断言：``expected`` 列表里的每一个名字在 rs_czsc 与 czsc 上都必须
    可以通过 ``hasattr`` 找到。
    """
    expected = {
        "CZSC",
        "FX",
        "BI",
        "ZS",
        "RawBar",
        "NewBar",
        "Freq",
        "Mark",
        "Direction",
        "Operate",
        "Signal",
        "Event",
        "Position",
    }
    for name in expected:
        assert hasattr(rs_czsc_module, name), f"rs_czsc lacks {name}"
        assert hasattr(czsc_module, name), f"czsc lacks {name}"
