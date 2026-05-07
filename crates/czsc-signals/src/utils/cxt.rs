use crate::utils::math::mean;
use czsc_core::analyze::{CZSC, UBI};
use czsc_core::objects::bar::RawBar;
use czsc_core::objects::bi::BI;
use czsc_core::objects::direction::Direction;
use czsc_core::objects::fx::FX;
use czsc_core::objects::mark::Mark;
use czsc_core::objects::zs::ZS;

#[inline]
pub fn raw_bar_upper(bar: &RawBar) -> f64 {
    bar.high - bar.open.max(bar.close)
}

#[inline]
pub fn raw_bar_lower(bar: &RawBar) -> f64 {
    bar.open.min(bar.close) - bar.low
}

pub fn fx_raw_bars(fx: &FX) -> Vec<RawBar> {
    fx.elements
        .iter()
        .flat_map(|nb| nb.elements.iter().cloned())
        .collect()
}

pub fn fx_power_str(fx: &FX) -> &'static str {
    if fx.elements.len() != 3 {
        return "弱";
    }
    let k1 = &fx.elements[0];
    let k2 = &fx.elements[1];
    let k3 = &fx.elements[2];
    match fx.mark {
        Mark::D => {
            if k3.close > k1.high {
                "强"
            } else if k3.close > k2.high {
                "中"
            } else {
                "弱"
            }
        }
        Mark::G => {
            if k3.close < k1.low {
                "强"
            } else if k3.close < k2.low {
                "中"
            } else {
                "弱"
            }
        }
    }
}

pub fn fx_has_zs(fx: &FX) -> bool {
    if fx.elements.len() != 3 {
        return false;
    }
    let zd = fx
        .elements
        .iter()
        .map(|x| x.low)
        .fold(f64::NEG_INFINITY, f64::max);
    let zg = fx
        .elements
        .iter()
        .map(|x| x.high)
        .fold(f64::INFINITY, f64::min);
    zg >= zd
}

pub fn get_zs_seq(bis: &[BI]) -> Vec<ZS> {
    let mut zs_list: Vec<ZS> = Vec::new();
    if bis.is_empty() {
        return zs_list;
    }

    for bi in bis.iter().cloned() {
        if zs_list.is_empty() {
            zs_list.push(ZS::new(vec![bi]));
            continue;
        }

        let last_zs = zs_list.pop().unwrap();
        if last_zs.bis.is_empty() {
            let mut new_bis = last_zs.bis;
            new_bis.push(bi);
            zs_list.push(ZS::new(new_bis));
        } else if (bi.direction == Direction::Up && bi.get_high() < last_zs.zd)
            || (bi.direction == Direction::Down && bi.get_low() > last_zs.zg)
        {
            zs_list.push(last_zs);
            zs_list.push(ZS::new(vec![bi]));
        } else {
            let mut new_bis = last_zs.bis;
            new_bis.push(bi);
            zs_list.push(ZS::new(new_bis));
        }
    }
    zs_list
}

pub fn unique_prices_from_bars(bars: &[RawBar]) -> Vec<f64> {
    let mut prices: Vec<f64> = Vec::with_capacity(bars.len() * 4);
    for b in bars {
        if b.close.is_finite() {
            prices.push(b.close);
        }
        if b.high.is_finite() {
            prices.push(b.high);
        }
        if b.low.is_finite() {
            prices.push(b.low);
        }
        if b.open.is_finite() {
            prices.push(b.open);
        }
    }
    prices.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    prices.dedup_by(|a, b| (*a - *b).abs() <= f64::EPSILON);
    prices
}

pub fn ubi_raw_bars(c: &CZSC) -> Vec<RawBar> {
    c.bars_ubi
        .iter()
        .flat_map(|nb| nb.elements.iter().cloned())
        .collect()
}

pub fn calc_bi_status_values(czsc: &CZSC, ubi_fxs: &[FX]) -> (&'static str, &'static str) {
    let last_bi = czsc.bi_list.last().unwrap();
    let v1 = match last_bi.direction {
        Direction::Down => {
            if czsc.bars_ubi.len() > 7 {
                "向上"
            } else {
                "向下"
            }
        }
        Direction::Up => {
            if czsc.bars_ubi.len() > 7 {
                "向下"
            } else {
                "向上"
            }
        }
    };

    let last_fx = ubi_fxs.last().unwrap();
    let v2 = match last_fx.mark {
        Mark::D => {
            if v1 == "向下" {
                "底分"
            } else {
                "延伸"
            }
        }
        Mark::G => {
            if v1 == "向上" {
                "顶分"
            } else {
                "延伸"
            }
        }
    };
    (v1, v2)
}

pub fn rebuild_ubi(c: &CZSC) -> Option<UBI> {
    if c.bars_ubi.is_empty() || c.bi_list.is_empty() {
        return None;
    }
    let ubi_fxs = c.get_ubi_fxs()?;
    if ubi_fxs.is_empty() {
        return None;
    }
    let raw_bars: Vec<RawBar> = c
        .bars_ubi
        .iter()
        .flat_map(|x| x.elements.iter().cloned())
        .collect();
    let high_bar = raw_bars
        .iter()
        .max_by(|a, b| {
            a.high
                .partial_cmp(&b.high)
                .unwrap_or(std::cmp::Ordering::Less)
        })?
        .clone();
    let low_bar = raw_bars
        .iter()
        .min_by(|a, b| {
            a.low
                .partial_cmp(&b.low)
                .unwrap_or(std::cmp::Ordering::Greater)
        })?
        .clone();
    let direction = if c.bi_list.last().unwrap().direction == Direction::Down {
        Direction::Up
    } else {
        Direction::Down
    };
    Some(UBI {
        symbol: c.symbol.clone(),
        direction,
        high: high_bar.high,
        low: low_bar.low,
        high_bar,
        low_bar,
        bars: c.bars_ubi.clone(),
        raw_bars,
        fxs: ubi_fxs.clone(),
        fx_a: ubi_fxs.first().unwrap().clone(),
    })
}

pub fn check_first_buy(bis: &[BI]) -> bool {
    if bis.len() % 2 != 1
        || bis.last().unwrap().direction == Direction::Up
        || bis.first().unwrap().direction != bis.last().unwrap().direction
    {
        return false;
    }
    let max_high = bis
        .iter()
        .map(|x| x.get_high())
        .fold(f64::NEG_INFINITY, f64::max);
    let min_low = bis
        .iter()
        .map(|x| x.get_low())
        .fold(f64::INFINITY, f64::min);
    if max_high != bis.first().unwrap().get_high() || min_low != bis.last().unwrap().get_low() {
        return false;
    }
    let mut key_bis: Vec<&BI> = Vec::new();
    for i in (0..=(bis.len() - 3)).step_by(2) {
        if i == 0 {
            key_bis.push(&bis[i]);
        } else {
            let b1 = &bis[i - 2];
            let b3 = &bis[i];
            if b3.get_low() < b1.get_low() {
                key_bis.push(b3);
            }
        }
    }
    if key_bis.is_empty() {
        return false;
    }
    let last = bis.last().unwrap();
    let prev = &bis[bis.len() - 3];
    let bc_price = last.get_power_price()
        < prev.get_power_price().max(mean(
            &key_bis
                .iter()
                .map(|x| x.get_power_price())
                .collect::<Vec<_>>(),
        ));
    let bc_volume = last.get_power_volume()
        < prev.get_power_volume().max(mean(
            &key_bis
                .iter()
                .map(|x| x.get_power_volume())
                .collect::<Vec<_>>(),
        ));
    let bc_length = (last.get_length() as f64)
        < (prev.get_length() as f64).max(mean(
            &key_bis
                .iter()
                .map(|x| x.get_length() as f64)
                .collect::<Vec<_>>(),
        ));
    bc_price && (bc_volume || bc_length)
}

pub fn check_first_sell(bis: &[BI]) -> bool {
    if bis.len() % 2 != 1
        || bis.last().unwrap().direction == Direction::Down
        || bis.first().unwrap().direction != bis.last().unwrap().direction
    {
        return false;
    }
    let max_high = bis
        .iter()
        .map(|x| x.get_high())
        .fold(f64::NEG_INFINITY, f64::max);
    let min_low = bis
        .iter()
        .map(|x| x.get_low())
        .fold(f64::INFINITY, f64::min);
    if max_high != bis.last().unwrap().get_high() || min_low != bis.first().unwrap().get_low() {
        return false;
    }
    let mut key_bis: Vec<&BI> = Vec::new();
    for i in (0..=(bis.len() - 3)).step_by(2) {
        if i == 0 {
            key_bis.push(&bis[i]);
        } else {
            let b1 = &bis[i - 2];
            let b3 = &bis[i];
            if b3.get_high() > b1.get_high() {
                key_bis.push(b3);
            }
        }
    }
    if key_bis.is_empty() {
        return false;
    }
    let last = bis.last().unwrap();
    let prev = &bis[bis.len() - 3];
    let bc_price = last.get_power_price()
        < prev.get_power_price().max(mean(
            &key_bis
                .iter()
                .map(|x| x.get_power_price())
                .collect::<Vec<_>>(),
        ));
    let bc_volume = last.get_power_volume()
        < prev.get_power_volume().max(mean(
            &key_bis
                .iter()
                .map(|x| x.get_power_volume())
                .collect::<Vec<_>>(),
        ));
    let bc_length = (last.get_length() as f64)
        < (prev.get_length() as f64).max(mean(
            &key_bis
                .iter()
                .map(|x| x.get_length() as f64)
                .collect::<Vec<_>>(),
        ));
    bc_price && (bc_volume || bc_length)
}
