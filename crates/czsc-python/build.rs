//! Build script for czsc-python.
//!
//! On macOS the cdylib needs `-undefined dynamic_lookup` so that Python
//! symbols are resolved at runtime by the host interpreter. PyO3's
//! `extension-module` feature normally emits this, but when building via
//! plain `cargo build --workspace` (without maturin) we make the link arg
//! explicit so the workspace layout test stays GREEN.

fn main() {
    if std::env::var("CARGO_CFG_TARGET_OS").as_deref() == Ok("macos") {
        println!("cargo:rustc-link-arg-cdylib=-undefined");
        println!("cargo:rustc-link-arg-cdylib=dynamic_lookup");
    }
}
