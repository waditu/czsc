//! 由原 `error-support` crate 内联进来的测试（Phase J）：
//! `expand_error_chain` 必须用 `Caused by:` 分隔遍历完整 source 链；
//! `czsc_bail!` 必须以 `anyhow::Error` 包裹后短路。

use czsc_core::czsc_bail;
use czsc_core::error_chain::expand_error_chain;

#[test]
fn expand_error_chain_walks_sources() {
    let inner = std::io::Error::other("leaf");
    let mid = anyhow::Error::new(inner).context("middle layer");
    let outer = mid.context("outermost");
    let chain = expand_error_chain(&outer);
    assert!(chain.contains("outermost"), "chain missing outer: {chain}");
    assert!(
        chain.contains("Caused by: middle layer"),
        "missing middle: {chain}"
    );
    assert!(chain.contains("Caused by: leaf"), "missing leaf: {chain}");
}

fn callee() -> Result<(), anyhow::Error> {
    czsc_bail!("kaboom");
}

#[test]
fn czsc_bail_returns_err() {
    let err = callee().unwrap_err();
    assert!(err.to_string().contains("kaboom"));
}
