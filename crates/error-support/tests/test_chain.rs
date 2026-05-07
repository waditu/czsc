//! Phase D.0b — RED test: expand_error_chain must walk the full source chain
//! using `Caused by:` separators, and czsc_bail! must short-circuit with an
//! anyhow-wrapped error.

use error_support::{czsc_bail, expand_error_chain};

#[test]
fn expand_error_chain_walks_sources() {
    let inner = std::io::Error::new(std::io::ErrorKind::Other, "leaf");
    let mid = anyhow::Error::new(inner).context("middle layer");
    let outer = mid.context("outermost");
    let chain = expand_error_chain(&outer);
    assert!(chain.contains("outermost"), "chain missing outer: {chain}");
    assert!(chain.contains("Caused by: middle layer"), "missing middle: {chain}");
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
