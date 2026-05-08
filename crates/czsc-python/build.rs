//! czsc-python 的 build script。
//!
//! 在 macOS 上 cdylib 需要 `-undefined dynamic_lookup`，这样 Python 符号
//! 才能在运行时由宿主解释器解析。PyO3 的 `extension-module` feature 一般
//! 会自动加上这个 flag，但是当我们直接用
//! `cargo build --workspace`（不走 maturin）构建时，需要显式声明这个
//! 链接参数，以便 workspace layout test 保持 GREEN。

fn main() {
    if std::env::var("CARGO_CFG_TARGET_OS").as_deref() == Ok("macos") {
        println!("cargo:rustc-link-arg-cdylib=-undefined");
        println!("cargo:rustc-link-arg-cdylib=dynamic_lookup");
    }
}
