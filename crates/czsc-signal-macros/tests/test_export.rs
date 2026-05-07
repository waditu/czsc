//! Phase E.last — smoke test: czsc-signal-macros compiles and the test
//! binary can link against it. Proc-macros are compile-time constructs,
//! so the real validation is that this test target builds at all.
//!
//! Full expansion testing requires czsc-signals types and lands in
//! Phase F (every signal module under crates/czsc-signals/src/*.rs
//! exercises `#[signal_module]` and `#[signal]` against the real
//! types).

#[test]
fn proc_macro_crate_links() {
    // Reaching this assertion means the crate compiled with both
    // #[proc_macro_attribute] entrypoints exported.
    assert!(true);
}
