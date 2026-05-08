//! `czsc-python` 的 type stub 生成器入口（spec §2.4 / Q4）。
//!
//! 通过 `pyo3-stub-gen` 收集 Rust 端所有 `#[gen_stub_pyclass]` /
//! `#[gen_stub_pyfunction]` / `#[gen_stub_pymethods]` 装饰器注册的信息，
//! 写出 `czsc/_native.pyi` 供 basedpyright / IDE / type checker 消费。
//!
//! 触发方式：
//!     PYO3_PYTHON=$(uv run python -c 'import sys; print(sys.executable)') \
//!       cargo run --bin stub_gen -p czsc-python \
//!         --no-default-features --features stub-gen
//!
//! `--features stub-gen` 通过 [[bin]] required-features 启用本二进制，
//! `--no-default-features` 关闭 extension-module 和 abi3-py310，让 pyo3
//! 走非 abi3 链接路径（`-lpython3.X`）。两者必须配对出现。
//!
//! 输出路径由 `pyproject.toml` 里 `[tool.maturin].module-name = "czsc._native"`
//! 推导：写到 `czsc/_native.pyi`。

use pyo3_stub_gen::Result;

fn main() -> Result<()> {
    let stub = czsc_python::stub_info()?;
    stub.generate()?;
    println!("czsc/_native.pyi 生成完成");
    Ok(())
}
