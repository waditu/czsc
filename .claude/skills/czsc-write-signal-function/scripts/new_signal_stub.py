#!/usr/bin/env python3
"""Generate Rust stubs for CZSC signal functions (auto-registered by #[signal])."""

from __future__ import annotations

import argparse
import re
import sys


def to_registry_name(func_name: str) -> str:
    m = re.match(r"^(.*)_v(\d{6})$", func_name)
    if not m:
        return func_name
    return f"{m.group(1)}_V{m.group(2)}"


def to_pascal_case(name: str) -> str:
    return "".join(part.capitalize() for part in name.split("_") if part)


def derive_opcode(func_name: str) -> str:
    m = re.match(r"^(.*)_v(\d{6})$", func_name)
    if not m:
        return to_pascal_case(func_name)
    return f"{to_pascal_case(m.group(1))}V{m.group(2)}"


def kline_stub(func_name: str) -> str:
    registry_name = to_registry_name(func_name)
    opcode = derive_opcode(func_name)
    return f'''use crate::params::ParamView;
use crate::types::TaCache;
use crate::utils::sig::get_usize_param;
use czsc_signal_macros::signal;
use czsc_core::analyze::CZSC;
use czsc_core::objects::signal::Signal;
use std::str::FromStr;

/// {func_name}: TODO 用一句话描述信号业务含义
///
/// 参数模板：\"{{freq}}_D{{di}}_{registry_name}\"
/// 判定逻辑：TODO 说明触发条件与 v1/v2/v3 的语义映射
/// 边界行为：当数据不足时返回空信号，避免输出误导状态
#[signal(
    category = "kline",
    name = "{registry_name}",
    template = "{{freq}}_D{{di}}_{registry_name}",
    opcode = "{opcode}",
    param_kind = "{opcode}"
)]
pub fn {func_name}(
    czsc: &CZSC,
    params: &ParamView,
    _cache: &mut TaCache,
) -> Vec<Signal> {{
    // 参数读取：统一从 params 提取，保证默认值行为可预期
    let di = get_usize_param(params, "di", 1);

    // 边界检查：避免 di 回看越界导致 panic 或错误信号
    if czsc.bars_raw.len() < di + 2 {{
        return vec![];
    }}

    // 组装信号 7 段：k1/k2/k3 决定匹配键，v1/v2/v3 表达状态值
    let k1 = czsc.freq.to_string();
    let k2 = format!("D{{}}", di);
    let k3 = "示例";
    let v1 = "其他";

    let sig_str = format!("{{}}_{{}}_{{}}_{{}}_任意_任意_0", k1, k2, k3, v1);
    Signal::from_str(&sig_str).map_or_else(|_| vec![], |s| vec![s])
}}
'''


def trader_stub(func_name: str) -> str:
    registry_name = to_registry_name(func_name)
    opcode = derive_opcode(func_name)
    return f'''use crate::params::ParamView;
use crate::utils::sig::get_str_param;
use czsc_signal_macros::signal;
use czsc_core::objects::signal::Signal;
use czsc_core::objects::state::TraderState;
use std::str::FromStr;

/// {func_name}: TODO 用一句话描述 Trader 级信号业务含义
///
/// 参数模板：\"{{pos_name}}_{registry_name}\"
/// 判定逻辑：TODO 说明如何读取 TraderState 并映射为信号值
/// 边界行为：查询不到仓位或关键参数缺失时输出“其他”
#[signal(
    category = "trader",
    name = "{registry_name}",
    template = "{{pos_name}}_{registry_name}",
    opcode = "{opcode}",
    param_kind = "{opcode}"
)]
pub fn {func_name}(
    cat: &dyn TraderState,
    params: &ParamView,
) -> Vec<Signal> {{
    // 参数读取：pos_name 是 Trader 级信号常见路由参数
    let pos_name = get_str_param(params, "pos_name", "").to_string();

    // 读取 TraderState：说明该信号依赖仓位状态而非单周期 K线
    let k1 = format!("{{}}_状态", pos_name);
    let v1 = if cat.get_position(&pos_name).is_some() {{
        "有效"
    }} else {{
        "其他"
    }};

    let sig_str = format!("{{}}_其他_示例_{{}}_任意_任意_0", k1, v1);
    Signal::from_str(&sig_str).map_or_else(|_| vec![], |s| vec![s])
}}
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=["kline", "trader"], required=True)
    parser.add_argument("--func", required=True, help="Rust function name, e.g. tas_xxx_v240101")
    args = parser.parse_args()

    func_name = args.func.strip()

    if args.kind == "kline":
        func_body = kline_stub(func_name)
    else:
        func_body = trader_stub(func_name)

    sys.stdout.write("=== Function Stub ===\n")
    sys.stdout.write(func_body)
    sys.stdout.write(
        "\n=== Notes ===\n使用 #[signal(...)] 自动注册，无需手写 registry.rs 注册项。\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
