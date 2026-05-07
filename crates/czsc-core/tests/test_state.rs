//! Phase D.A follow-up — RED test: TraderState trait is publicly defined
//! and a minimal stub impl is accepted by the type system. czsc-signals
//! and czsc-trader will depend on this trait once they migrate.

use czsc_core::analyze::CZSC;
use czsc_core::objects::position::Position;
use czsc_core::objects::state::TraderState;

struct StubTrader;

impl TraderState for StubTrader {
    fn get_position(&self, _name: &str) -> Option<&Position> {
        None
    }
    fn get_czsc(&self, _freq: &str) -> Option<&CZSC> {
        None
    }
    fn latest_price(&self) -> Option<f64> {
        None
    }
}

#[test]
fn stub_trader_implements_trait() {
    let s = StubTrader;
    let _: &dyn TraderState = &s;
    assert!(s.get_position("foo").is_none());
    assert!(s.get_czsc("30分钟").is_none());
    assert!(s.latest_price().is_none());
}
