use serde_json::Value;
use std::collections::HashMap;

/// 统一参数只读视图，避免为每个信号维护独立 params 结构体。
#[derive(Debug, Clone, Copy)]
pub struct ParamView<'a> {
    inner: &'a HashMap<String, Value>,
}

impl<'a> ParamView<'a> {
    #[inline]
    pub fn new(inner: &'a HashMap<String, Value>) -> Self {
        Self { inner }
    }

    #[inline]
    pub fn usize(&self, key: &str, default: usize) -> usize {
        if let Some(val) = self.inner.get(key) {
            if let Some(n) = val.as_u64() {
                return n as usize;
            }
            if let Some(s) = val.as_str()
                && let Ok(n) = s.parse::<usize>()
            {
                return n;
            }
        }
        default
    }

    #[inline]
    pub fn str<'b>(&'b self, key: &str, default: &'b str) -> &'b str {
        if let Some(val) = self.inner.get(key)
            && let Some(s) = val.as_str()
        {
            return s;
        }
        default
    }

    #[inline]
    pub fn bool(&self, key: &str, default: bool) -> bool {
        if let Some(val) = self.inner.get(key) {
            if let Some(v) = val.as_bool() {
                return v;
            }
            if let Some(s) = val.as_str() {
                if s.eq_ignore_ascii_case("true") || s == "1" {
                    return true;
                }
                if s.eq_ignore_ascii_case("false") || s == "0" {
                    return false;
                }
            }
        }
        default
    }

    #[inline]
    pub fn value(&self, key: &str) -> Option<&Value> {
        self.inner.get(key)
    }
}
