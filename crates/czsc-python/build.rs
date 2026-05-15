//! czsc-python 的 build script。
//!
//! 职责：
//!
//! 1. **校验 Python 版本约束**：`pyo3-stub-gen` 0.22 与 `pyo3` 0.22 都依赖
//!    `Py_3_10` cfg，需要解释器 ≥ 3.10。当 `PYO3_PYTHON` 被显式指向更低
//!    版本（或当前 PATH 里的 `python3` 低于 3.10）时，把错误信息提前
//!    抛给开发者，而不是让 `cargo test` 在符号链接阶段才神秘失败。
//!
//! 2. **macOS cdylib 链接参数**：cdylib 需要 `-undefined dynamic_lookup`，
//!    这样 Python 符号才能在运行时由宿主解释器解析。PyO3 的
//!    `extension-module` feature 一般会自动加上，但当我们直接用
//!    `cargo build --workspace`（不走 maturin）构建时，需要显式声明，
//!    以便 workspace layout test 保持 GREEN。
//!
//! 任何一步检查失败都会 `panic!`，并附带具体的修复建议。

use std::process::Command;

fn main() {
    println!("cargo:rerun-if-env-changed=PYO3_PYTHON");
    println!("cargo:rerun-if-env-changed=CARGO_CFG_TARGET_OS");

    check_python_version();

    if std::env::var("CARGO_CFG_TARGET_OS").as_deref() == Ok("macos") {
        println!("cargo:rustc-link-arg-cdylib=-undefined");
        println!("cargo:rustc-link-arg-cdylib=dynamic_lookup");
    }
}

/// 校验 `PYO3_PYTHON`（或 fallback 解释器）≥ 3.10。
///
/// 行为说明：
/// - 优先使用 `PYO3_PYTHON` 指定的解释器；未设置则 fallback 到 `python3` → `python`。
/// - 通过 `python -c "import sys; print(sys.version_info[:3]...)"` 拿到版本三元组。
/// - 任一步骤失败都打印明确建议（设置 `PYO3_PYTHON` 指向 Python 3.10+），并直接 `panic!`，
///   避免 cargo 报“神秘的 `Py_3_10` cfg 缺失”错误。
fn check_python_version() {
    let interpreter = std::env::var("PYO3_PYTHON")
        .ok()
        .or_else(|| which("python3"))
        .or_else(|| which("python"))
        .unwrap_or_else(|| {
            panic!(
                "czsc-python build.rs: 未找到 Python 解释器。\n\
                 请设置环境变量 PYO3_PYTHON 指向 Python 3.10+，例如：\n\
                 \texport PYO3_PYTHON=$(which python3.12)"
            );
        });

    let output = Command::new(&interpreter)
        .args([
            "-c",
            "import sys; v = sys.version_info; print(f'{v.major}.{v.minor}.{v.micro}')",
        ])
        .output()
        .unwrap_or_else(|err| {
            panic!(
                "czsc-python build.rs: 调用解释器 {interpreter} 失败：{err}\n\
                 请设置 PYO3_PYTHON 指向可用的 Python 3.10+。"
            )
        });
    if !output.status.success() {
        panic!(
            "czsc-python build.rs: 解释器 {interpreter} 返回非 0 状态码：{}\n{}",
            output.status,
            String::from_utf8_lossy(&output.stderr)
        );
    }
    let version = String::from_utf8_lossy(&output.stdout).trim().to_string();
    let mut parts = version.splitn(3, '.');
    let major: u32 = parts.next().and_then(|s| s.parse().ok()).unwrap_or(0);
    let minor: u32 = parts.next().and_then(|s| s.parse().ok()).unwrap_or(0);

    if (major, minor) < (3, 10) {
        panic!(
            "czsc-python build.rs: 检测到 Python {version}（位于 {interpreter}），\n\
             但本项目依赖 pyo3 / pyo3-stub-gen 要求 Python ≥ 3.10。\n\
             修复方法（任选其一）：\n\
             \t1. 安装 Python 3.10+ 并通过 PYO3_PYTHON 指定：\n\
             \t   export PYO3_PYTHON=$(which python3.12)\n\
             \t2. 使用 uv 同步项目环境后再构建：\n\
             \t   uv sync --extra dev && uv run maturin develop\n"
        );
    }
}

/// 简易 `which` 实现：返回找到的可执行路径。
///
/// 仅依赖标准库；不引入 `which` crate，避免给 build 阶段引入额外依赖。
fn which(name: &str) -> Option<String> {
    let path = std::env::var_os("PATH")?;
    for dir in std::env::split_paths(&path) {
        let candidate = dir.join(name);
        if candidate.is_file() {
            return Some(candidate.to_string_lossy().into_owned());
        }
        #[cfg(windows)]
        {
            let candidate_exe = dir.join(format!("{}.exe", name));
            if candidate_exe.is_file() {
                return Some(candidate_exe.to_string_lossy().into_owned());
            }
        }
    }
    None
}
