//! 错误链工具：把 `anyhow::Error` 的 source 链展开为带 "Caused by:" 前缀
//! 的多行字符串，以及一个仿 `anyhow::bail!` 的便捷宏 [`czsc_bail!`]。
//!
//! 由 Phase J 从原 `error-support` crate 内联进来 —— 内容只有 38 行，独立成
//! crate 收益不抵命名占用通用空间的代价；保留为内部模块，按需 re-export。

use std::fmt::Write;

/// 把 [`anyhow::Error`] 的 source 链展开为多行字符串：
///
/// ```text
/// 顶层错误
/// Caused by: 中间错误
/// Caused by: 根因
/// ```
pub fn expand_error_chain(err: &anyhow::Error) -> String {
    let mut error_chain = String::new();
    let mut current_error: Option<&(dyn std::error::Error + 'static)> = Some(err.as_ref());
    // 标记是否是错误链中的第一个错误
    let mut is_first = true;

    // 遍历整个错误链，直到没有更多的源错误
    while let Some(error) = current_error {
        // 除了第一个错误之外，为每个后续错误添加 "Caused by: " 前缀
        if !is_first {
            // 这里使用 `unwrap()` 是安全的，因为 `write!` 向 `String` 写入内容不会失败（`String` 会自动扩容）- 唯一可能导致 `write!` 失败的情况是内存分配失败，这种情况下程序已经处于不可恢复状态。
            write!(error_chain, "\nCaused by: ").unwrap();
        }
        // 将当前错误信息写入错误链字符串
        write!(error_chain, "{error}").unwrap();
        // 获取下一个源错误（如果存在）
        current_error = error.source();
        is_first = false;
    }

    error_chain
}

/// 从 anyhow::bail! 复制而来。
///
/// 与 `anyhow::bail!` 相比，本宏对返回类型更宽松 —— 任何实现了
/// `From<anyhow::Error>` 的错误类型（典型如 `czsc-derive` 生成的枚举）
/// 都能直接 `czsc_bail!`，省去手动 `?`。
#[macro_export]
macro_rules! czsc_bail {
    ($msg:literal $(,)?) => {
        return Err(anyhow::anyhow!($msg).into())
    };
    ($err:expr $(,)?) => {
        return Err(anyhow::anyhow!($err).into())
    };
    ($fmt:expr, $($arg:tt)*) => {
        return Err(anyhow::anyhow!($fmt, $($arg)*).into())
    };
}
