use crate::params::ParamView;
use crate::utils::sig::{get_str_param, get_usize_param, make_signal_v1};
use czsc_core::objects::bar::RawBar;
use czsc_core::objects::direction::Direction;
use czsc_core::objects::signal::Signal;
use czsc_core::objects::state::TraderState;
use czsc_core::objects::zs::ZS;
use czsc_signal_macros::signal;

fn is_valid_zs(bis: &[czsc_core::objects::bi::BI]) -> bool {
    bis.len() >= 3 && ZS::new(bis.to_vec()).zg > ZS::new(bis.to_vec()).zd
}

/// cxt_zhong_shu_gong_zhen_V221221：大小级别中枢共振
///
/// 参数模板：`"{freq1}_{freq2}_中枢共振V221221"`
///
/// 信号逻辑：
/// 1. 大小级别最近 3 笔均构成有效中枢；
/// 2. 小级别中枢位置相对大级别中轴偏上且末笔向下，判 `看多`；
/// 3. 小级别中枢位置相对大级别中轴偏下且末笔向上，判 `看空`。
#[signal(
    category = "trader",
    name = "cxt_zhong_shu_gong_zhen_V221221",
    template = "{freq1}_{freq2}_中枢共振V221221",
    opcode = "CxtZhongShuGongZhenV221221",
    param_kind = "CxtZhongShuGongZhenV221221"
)]
pub fn cxt_zhong_shu_gong_zhen_v221221(cat: &dyn TraderState, params: &ParamView) -> Vec<Signal> {
    let freq1 = get_str_param(params, "freq1", "日线");
    let freq2 = get_str_param(params, "freq2", "60分钟");
    let k1 = freq1.to_string();
    let k2 = freq2.to_string();
    let k3 = "中枢共振V221221";

    let Some(max_freq) = cat.get_czsc(freq1) else {
        return make_signal_v1(&k1, &k2, k3, "其他");
    };
    let Some(min_freq) = cat.get_czsc(freq2) else {
        return make_signal_v1(&k1, &k2, k3, "其他");
    };
    if max_freq.bi_list.len() < 5 || min_freq.bi_list.len() < 5 {
        return make_signal_v1(&k1, &k2, k3, "其他");
    }

    let big_bis = &max_freq.bi_list[max_freq.bi_list.len() - 3..];
    let small_bis = &min_freq.bi_list[min_freq.bi_list.len() - 3..];
    if !is_valid_zs(big_bis) || !is_valid_zs(small_bis) {
        return make_signal_v1(&k1, &k2, k3, "其他");
    }

    let big_zs = ZS::new(big_bis.to_vec());
    let small_zs = ZS::new(small_bis.to_vec());
    if small_zs.dd > big_zs.zz && min_freq.bi_list.last().unwrap().direction == Direction::Down {
        return make_signal_v1(&k1, &k2, k3, "看多");
    }
    if small_zs.gg < big_zs.zz && min_freq.bi_list.last().unwrap().direction == Direction::Up {
        return make_signal_v1(&k1, &k2, k3, "看空");
    }
    make_signal_v1(&k1, &k2, k3, "其他")
}

/// cxt_intraday_V230701：30分钟日内走势分类
///
/// 参数模板：`"{freq1}#{freq2}_D{di}日_走势分类V230701"`
///
/// 信号逻辑：
/// 1. 取指定日的 30 分钟 bars；
/// 2. 识别无中枢、双中枢、单中枢平衡市；
/// 3. 返回对应日内结构标签。
#[signal(
    category = "trader",
    name = "cxt_intraday_V230701",
    template = "{freq1}#{freq2}_D{di}日_走势分类V230701",
    opcode = "CxtIntradayV230701",
    param_kind = "CxtIntradayV230701"
)]
pub fn cxt_intraday_v230701(cat: &dyn TraderState, params: &ParamView) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 2);
    let freq1 = get_str_param(params, "freq1", "30分钟");
    let freq2 = get_str_param(params, "freq2", "日线");
    assert_eq!(freq1, "30分钟");
    assert_eq!(freq2, "日线");
    assert!(di > 0 && di < 21);

    let k1 = format!("{}#{}", freq1, freq2);
    let k2 = format!("D{}日", di);
    let k3 = "走势分类V230701";

    let Some(c1) = cat.get_czsc(freq1) else {
        return make_signal_v1(&k1, &k2, k3, "其他");
    };
    let Some(c2) = cat.get_czsc(freq2) else {
        return make_signal_v1(&k1, &k2, k3, "其他");
    };
    if c2.bars_raw.len() < di {
        return make_signal_v1(&k1, &k2, k3, "其他");
    }

    let day = c2.bars_raw[c2.bars_raw.len() - di].dt.date_naive();
    let bars: Vec<&RawBar> = c1
        .bars_raw
        .iter()
        .filter(|x| x.dt.date_naive() == day)
        .collect();
    assert!(bars.len() <= 8, "仅适用于A股市场 30 分钟日内 8 根K线");
    if bars.len() <= 4 {
        return make_signal_v1(&k1, &k2, k3, "其他");
    }

    let mut zs_list: Vec<(f64, f64)> = Vec::new();
    for w in bars.windows(3) {
        let highs = [w[0].high, w[1].high, w[2].high];
        let lows = [w[0].low, w[1].low, w[2].low];
        let zg = highs.into_iter().fold(f64::INFINITY, f64::min);
        let zd = lows.into_iter().fold(f64::NEG_INFINITY, f64::max);
        if zg >= zd {
            zs_list.push((
                [w[0].high, w[1].high, w[2].high]
                    .into_iter()
                    .fold(f64::NEG_INFINITY, f64::max),
                [w[0].low, w[1].low, w[2].low]
                    .into_iter()
                    .fold(f64::INFINITY, f64::min),
            ));
        }
    }

    let dir = if bars.last().unwrap().close > bars.first().unwrap().open {
        "上涨"
    } else {
        "下跌"
    };
    if zs_list.is_empty() {
        return make_signal_v1(&k1, &k2, k3, &format!("无中枢{}", dir));
    }

    if zs_list.len() >= 2 {
        let (zs1_high, zs1_low) = zs_list[0];
        let (zs2_high, zs2_low) = zs_list[zs_list.len() - 1];
        if (dir == "上涨" && zs1_high < zs2_low) || (dir == "下跌" && zs1_low > zs2_high) {
            return make_signal_v1(&k1, &k2, k3, &format!("双中枢{}", dir));
        }
    }

    let high_first = bars[0].high.max(bars[1].high).max(bars[2].high)
        == bars.iter().map(|x| x.high).fold(f64::NEG_INFINITY, f64::max);
    let low_first = bars[0].low.min(bars[1].low).min(bars[2].low)
        == bars.iter().map(|x| x.low).fold(f64::INFINITY, f64::min);
    let v1 = if high_first && !low_first {
        "弱平衡市"
    } else if low_first && !high_first {
        "强平衡市"
    } else {
        "转折平衡市"
    };
    make_signal_v1(&k1, &k2, k3, v1)
}
