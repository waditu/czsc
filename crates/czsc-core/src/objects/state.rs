use crate::analyze::CZSC;
use crate::objects::position::Position;

/// 交易员状态接口
///
/// 将 `CzscTrader` 的运行时状态抽象为 trait，允许 `czsc-signals` 中的 pos 系列
/// 信号函数访问仓位和K线数据，而无需直接依赖 `czsc-trader` crate，从根本上解除
/// czsc-signals ↔ czsc-trader 循环依赖。
///
/// 依赖链：
///   czsc-core  (定义 TraderState)
///     ↑
///   czsc-signals  (pos.rs 使用 &dyn TraderState)
///     ↑
///   czsc-trader   (CzscTrader 实现 TraderState)
pub trait TraderState {
    /// 按名称查询仓位
    fn get_position(&self, name: &str) -> Option<&Position>;
    /// 按频率查询 CZSC 解析器
    fn get_czsc(&self, freq: &str) -> Option<&CZSC>;
    /// 获取当前最新价格（通常为基础周期最新 close）
    fn latest_price(&self) -> Option<f64>;
}
