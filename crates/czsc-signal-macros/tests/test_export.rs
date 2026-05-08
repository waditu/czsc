//! Phase E.last — smoke test：czsc-signal-macros 能编译，且测试二进制
//! 能成功 link 到它。proc-macro 属于编译期构造，因此真正的验证就是
//! 这个 test target 能不能编译通过。
//!
//! 完整的展开测试需要 czsc-signals 的类型，安排在 Phase F
//! 进行（crates/czsc-signals/src/*.rs 下的每个信号模块都会针对
//! 真实类型走一遍 `#[signal_module]` 和 `#[signal]`）。

#[test]
fn proc_macro_crate_links() {
    // 能跑到这个函数就说明 crate 编译通过，并且两个
    // #[proc_macro_attribute] 入口都已正常导出。
}
