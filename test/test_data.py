# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/2/24 16:39
describe: data 模块的单元测试
"""
from czsc import data


def test_symbol_converter():
    jq_symbol = "300033.XSHE"
    gm_symbol = "SZSE.300033"
    ts_symbol = "300033.SZ"
    tdx_symbol = "0300033"

    assert data.gm_symbol_to_ts(gm_symbol) == ts_symbol
    assert data.gm_symbol_to_jq(gm_symbol) == jq_symbol
    assert data.gm_symbol_to_tdx(gm_symbol) == tdx_symbol

    assert data.jq_symbol_to_gm(jq_symbol) == gm_symbol
    assert data.jq_symbol_to_ts(jq_symbol) == ts_symbol
    assert data.jq_symbol_to_tdx(jq_symbol) == tdx_symbol

    assert data.ts_symbol_to_tdx(ts_symbol) == tdx_symbol
    assert data.ts_symbol_to_gm(ts_symbol) == gm_symbol
    assert data.ts_symbol_to_jq(ts_symbol) == jq_symbol

    assert data.ts_symbol_to_jq(ts_symbol) == jq_symbol
    assert data.ts_symbol_to_gm(ts_symbol) == gm_symbol
    assert data.ts_symbol_to_tdx(ts_symbol) == tdx_symbol

    assert data.tdx_symbol_to_ts(tdx_symbol) == ts_symbol
    assert data.tdx_symbol_to_gm(tdx_symbol) == gm_symbol
    assert data.tdx_symbol_to_jq(tdx_symbol) == jq_symbol
