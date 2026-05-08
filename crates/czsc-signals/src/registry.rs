use crate::types::{SignalFnRef, SignalMeta, TraderSignalMeta};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::LazyLock;

fn insert_generated_kline(
    m: &mut HashMap<&'static str, SignalMeta>,
    d: crate::types::SignalDescriptor,
) {
    if d.category != "kline" {
        return;
    }
    if let SignalFnRef::Kline(func) = d.func_ref {
        m.insert(
            d.name,
            SignalMeta {
                func,
                param_template: d.template,
                fast_kline: d.fast_kline,
            },
        );
    }
}

fn insert_generated_trader(
    m: &mut HashMap<&'static str, TraderSignalMeta>,
    d: crate::types::SignalDescriptor,
) {
    if d.category != "trader" {
        return;
    }
    if let SignalFnRef::Trader(func) = d.func_ref {
        m.insert(
            d.name,
            TraderSignalMeta {
                func,
                param_template: d.template,
            },
        );
    }
}

/// K线级运行时注册视图（来源：`#[signal(category = "kline", ...)]` + inventory 自动收集）
pub static SIGNAL_REGISTRY: LazyLock<HashMap<&'static str, SignalMeta>> = LazyLock::new(|| {
    let mut m: HashMap<&'static str, SignalMeta> = HashMap::new();
    for d in list_generated_signal_descriptors() {
        insert_generated_kline(&mut m, d);
    }
    m
});

/// Trader/Position 级运行时注册视图（来源：`#[signal(category = "trader", ...)]` + inventory 自动收集）
pub static TRADER_SIGNAL_REGISTRY: LazyLock<HashMap<&'static str, TraderSignalMeta>> =
    LazyLock::new(|| {
        let mut m: HashMap<&'static str, TraderSignalMeta> = HashMap::new();
        for d in list_generated_signal_descriptors() {
            insert_generated_trader(&mut m, d);
        }
        m
    });

/// 注册信号元信息（用于对照、文档、外部 API 只读查询）
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct RegisteredSignalInfo {
    /// 信号函数名，如 tas_ma_base_V221101
    pub name: String,
    /// 参数模板
    pub param_template: String,
    /// 注册表类别：kline / trader
    pub category: String,
    /// 信号命名空间前缀，如 bar/tas/cxt/pos
    pub namespace: String,
}

/// 汇总读取全部已注册信号（只读视图）。
pub fn list_all_signals(include_kline: bool, include_trader: bool) -> Vec<RegisteredSignalInfo> {
    let mut out = Vec::new();

    if include_kline {
        for (name, meta) in SIGNAL_REGISTRY.iter() {
            let namespace = name.split('_').next().unwrap_or_default().to_string();
            out.push(RegisteredSignalInfo {
                name: (*name).to_string(),
                param_template: meta.param_template.to_string(),
                category: "kline".to_string(),
                namespace,
            });
        }
    }

    if include_trader {
        for (name, meta) in TRADER_SIGNAL_REGISTRY.iter() {
            let namespace = name.split('_').next().unwrap_or_default().to_string();
            out.push(RegisteredSignalInfo {
                name: (*name).to_string(),
                param_template: meta.param_template.to_string(),
                category: "trader".to_string(),
                namespace,
            });
        }
    }

    out.sort_by(|a, b| {
        a.category
            .cmp(&b.category)
            .then_with(|| a.name.cmp(&b.name))
    });
    out
}

fn normalize_generated_signal_descriptors(
    mut out: Vec<crate::types::SignalDescriptor>,
) -> Result<Vec<crate::types::SignalDescriptor>, String> {
    let mut names: HashMap<&'static str, &'static str> = HashMap::new();
    let mut opcodes: HashMap<&'static str, &'static str> = HashMap::new();
    for d in &out {
        if let Some(prev) = names.insert(d.name, d.opcode) {
            return Err(format!(
                "duplicate signal name: {} (opcodes: {}, {})",
                d.name, prev, d.opcode
            ));
        }
        if let Some(prev_name) = opcodes.insert(d.opcode, d.name) {
            return Err(format!(
                "duplicate signal opcode: {} (names: {}, {})",
                d.opcode, prev_name, d.name
            ));
        }
    }
    out.sort_by(|a, b| a.name.cmp(b.name));
    Ok(out)
}

pub fn list_generated_signal_descriptors() -> Vec<crate::types::SignalDescriptor> {
    let out: Vec<crate::types::SignalDescriptor> =
        inventory::iter::<crate::types::SignalDescriptor>
            .into_iter()
            .copied()
            .collect();
    normalize_generated_signal_descriptors(out)
        .unwrap_or_else(|e| panic!("invalid generated signal descriptors: {e}"))
}

#[cfg(test)]
mod tests {
    use super::list_all_signals;
    use czsc_core::analyze::CZSC;
    use czsc_core::objects::signal::Signal;
    use serde_json::Value;
    use std::collections::HashMap;

    fn __inventory_probe_signal(
        _czsc: &CZSC,
        _params: &HashMap<String, Value>,
        _cache: &mut crate::types::TaCache,
    ) -> Vec<Signal> {
        Vec::new()
    }

    inventory::submit! {
        crate::types::SignalDescriptor {
            category: "kline",
            name: "__inventory_probe_V000000",
            template: "probe_template",
            opcode: "InventoryProbe",
            param_kind: "Probe",
            func_ref: crate::types::SignalFnRef::Kline(__inventory_probe_signal as crate::types::SignalFn),
            fast_kline: None,
        }
    }

    #[test]
    fn test_list_all_signals_contains_both_categories() {
        let all = list_all_signals(true, true);
        assert!(!all.is_empty());
        assert!(all.iter().any(|x| x.category == "kline"));
        assert!(all.iter().any(|x| x.category == "trader"));
    }

    #[test]
    fn test_list_all_signals_sorted_and_unique() {
        let all = list_all_signals(true, true);
        for i in 1..all.len() {
            let prev = (&all[i - 1].category, &all[i - 1].name);
            let curr = (&all[i].category, &all[i].name);
            assert!(prev <= curr);
        }
        let mut seen = std::collections::HashSet::new();
        for s in all {
            assert!(seen.insert((s.category, s.name)));
        }
    }

    #[test]
    fn test_pos_signal_registry_contains_all_python_pos_functions() {
        let expected = vec![
            "pos_ma_V230414",
            "pos_fx_stop_V230414",
            "pos_bar_stop_V230524",
            "pos_holds_V230414",
            "pos_fix_exit_V230624",
            "pos_profit_loss_V230624",
            "pos_status_V230808",
            "pos_holds_V230807",
            "pos_holds_V240428",
            "pos_holds_V240608",
            "pos_stop_V240428",
            "pos_take_V240428",
            "pos_stop_V240331",
            "pos_stop_V240608",
            "pos_stop_V240614",
            "pos_stop_V240717",
        ];
        for name in expected {
            assert!(
                super::TRADER_SIGNAL_REGISTRY.contains_key(name),
                "missing trader signal registration: {}",
                name
            );
        }
    }

    #[test]
    fn test_trader_registry_contains_cat_macd_functions() {
        for name in ["cat_macd_V230518", "cat_macd_V230520"] {
            assert!(
                super::TRADER_SIGNAL_REGISTRY.contains_key(name),
                "missing trader signal registration: {}",
                name
            );
        }
    }

    #[test]
    fn test_kline_registry_contains_jcc_batch_and_cxt_bi_status_v230102() {
        let expected = vec![
            "jcc_ci_tou_V221101",
            "jcc_fan_ji_xian_V221121",
            "jcc_fen_shou_xian_V20221113",
            "jcc_gap_yin_yang_V221121",
            "jcc_ping_tou_V221113",
            "jcc_san_fa_V20221115",
            "jcc_san_fa_V20221118",
            "jcc_san_szx_V221122",
            "jcc_san_xing_xian_V221023",
            "jcc_shan_chun_V221121",
            "jcc_szx_V221111",
            "jcc_ta_xing_V221124",
            "jcc_ten_mo_V221028",
            "jcc_three_crow_V221108",
            "jcc_two_crow_V221108",
            "jcc_wu_yun_gai_ding_V221101",
            "jcc_xing_xian_V221118",
            "jcc_yun_xian_V221118",
            "jcc_zhu_huo_xian_V221027",
            "cxt_bi_status_V230102",
        ];
        for name in expected {
            assert!(
                super::SIGNAL_REGISTRY.contains_key(name),
                "missing kline signal registration: {}",
                name
            );
        }
    }

    #[test]
    fn test_kline_registry_contains_cxt_batch2_20() {
        let expected = vec![
            "cxt_fx_power_V221107",
            "cxt_bi_end_V230104",
            "cxt_bi_end_V230105",
            "cxt_bi_end_V230224",
            "cxt_bi_end_V230312",
            "cxt_bi_end_V230324",
            "cxt_bi_end_V230815",
            "cxt_bi_stop_V230815",
            "cxt_bi_trend_V230824",
            "cxt_bi_zdf_V230601",
            "cxt_second_bs_V230320",
            "cxt_third_bs_V230318",
            "cxt_double_zs_V230311",
            "cxt_decision_V240526",
            "cxt_decision_V240612",
            "cxt_decision_V240613",
            "cxt_decision_V240614",
            "cxt_overlap_V240526",
            "cxt_bs_V240526",
            "cxt_bs_V240527",
        ];
        for name in expected {
            assert!(
                super::SIGNAL_REGISTRY.contains_key(name),
                "missing kline signal registration: {}",
                name
            );
        }
    }

    #[test]
    fn test_registry_contains_remaining_cxt_zdy_39() {
        let expected_kline = vec![
            "cxt_bi_end_V230222",
            "cxt_bi_end_V230320",
            "cxt_bi_end_V230322",
            "cxt_bi_end_V230618",
            "cxt_bi_trend_V230913",
            "cxt_eleven_bi_V230622",
            "cxt_first_buy_V221126",
            "cxt_first_sell_V221126",
            "cxt_five_bi_V230619",
            "cxt_nine_bi_V230621",
            "cxt_overlap_V240612",
            "cxt_range_oscillation_V230620",
            "cxt_second_bs_V240524",
            "cxt_seven_bi_V230620",
            "cxt_third_bs_V230319",
            "cxt_third_buy_V230228",
            "cxt_three_bi_V230618",
            "cxt_ubi_end_V230816",
            "zdy_bi_end_V230406",
            "zdy_bi_end_V230407",
            "zdy_dif_V230527",
            "zdy_dif_V230528",
            "zdy_macd_V230518",
            "zdy_macd_V230519",
            "zdy_macd_V230527",
            "zdy_macd_bc_V230422",
            "zdy_macd_bs1_V230422",
            "zdy_macd_dif_V230516",
            "zdy_macd_dif_V230517",
            "zdy_macd_dif_iqr_V230521",
            "zdy_zs_V230423",
            "zdy_zs_space_V230421",
        ];
        let expected_trader = vec![
            "cxt_intraday_V230701",
            "cxt_zhong_shu_gong_zhen_V221221",
            "zdy_stop_loss_V230406",
            "zdy_take_profit_V230406",
            "zdy_take_profit_V230407",
            "zdy_vibrate_V230406",
        ];
        for name in expected_kline {
            assert!(
                super::SIGNAL_REGISTRY.contains_key(name),
                "missing kline signal registration: {}",
                name
            );
        }
        for name in expected_trader {
            assert!(
                super::TRADER_SIGNAL_REGISTRY.contains_key(name),
                "missing trader signal registration: {}",
                name
            );
        }
    }

    #[test]
    fn test_tas_registry_contains_migrated_signals() {
        let expected = vec![
            "tas_ma_round_V221206",
            "tas_double_ma_V230511",
            "tas_first_bs_V230217",
            "tas_second_bs_V230228",
            "tas_second_bs_V230303",
            "tas_hlma_V230301",
            "tas_boll_cc_V230312",
            "tas_kdj_evc_V221201",
            "tas_kdj_evc_V230401",
            "tas_atr_break_V230424",
            "tas_ma_system_V230513",
            "tas_dif_layer_V241010",
            "tas_cross_status_V230619",
            "tas_cross_status_V230624",
            "tas_cross_status_V230625",
            "tas_slope_V231019",
            "tas_boll_vt_V230212",
            "tas_cci_base_V230402",
            "tas_accelerate_V230531",
            "tas_low_trend_V230627",
            "tas_atr_V230630",
            "tas_angle_V230802",
            "tas_double_ma_V240208",
            "tas_dma_bs_V240608",
            "tas_macd_bc_V230803",
            "tas_macd_bc_V240307",
            "tas_macd_first_bs_V221216",
            "tas_macd_second_bs_V221201",
            "tas_macd_xt_V221208",
            "tas_macd_bs1_V230312",
            "tas_macd_bs1_V230313",
            "tas_sar_base_V230425",
            "tas_rumi_V230704",
            "tas_macd_bs1_V230411",
            "tas_macd_bs1_V230412",
            "tas_macd_bc_V230804",
            "tas_macd_bc_ubi_V230804",
            "bar_end_V221211",
            "bar_operate_span_V221111",
            "bar_time_V230327",
            "bar_weekday_V230328",
            "vol_single_ma_V230214",
            "vol_double_ma_V230214",
            "vol_ti_suo_V221216",
            "vol_gao_di_V221218",
            "vol_window_V230731",
            "vol_window_V230801",
            "pressure_support_V240222",
            "pressure_support_V240402",
            "pressure_support_V240406",
            "pressure_support_V240530",
            "obvm_line_V230610",
            "obv_up_dw_line_V230719",
            "cvolp_up_dw_line_V230612",
            "ntmdk_V230824",
            "kcatr_up_dw_line_V230823",
            "clv_up_dw_line_V230605",
            "cmo_up_dw_line_V230605",
            "adtm_up_dw_line_V230603",
            "amv_up_dw_line_V230603",
            "asi_up_dw_line_V230603",
            "bias_up_dw_line_V230618",
            "dema_up_dw_line_V230605",
            "demakder_up_dw_line_V230605",
            "emv_up_dw_line_V230605",
            "er_up_dw_line_V230604",
            "skdj_up_dw_line_V230611",
            "coo_td_V221110",
            "coo_td_V221111",
            "coo_cci_V230323",
            "coo_kdj_V230322",
            "coo_sar_V230325",
            "byi_symmetry_zs_V221107",
            "byi_bi_end_V230106",
            "byi_bi_end_V230107",
            "byi_second_bs_V230324",
            "byi_fx_num_V230628",
            "xl_bar_position_V240328",
            "xl_bar_trend_V240329",
            "xl_bar_trend_V240330",
            "xl_bar_trend_V240331",
            "xl_bar_basis_V240411",
            "xl_bar_basis_V240412",
            "xl_bar_trend_V240623",
            "cci_decision_V240620",
            "tas_ma_cohere_V230512",
        ];
        for name in expected {
            assert!(
                super::SIGNAL_REGISTRY.contains_key(name),
                "missing kline signal registration: {}",
                name
            );
        }
    }

    #[test]
    fn test_macro_injected_kline_descriptors_registered() {
        let d1 = crate::tas::__RS_CZSC_SIGNAL_META_TAS_MA_BASE_V221101;
        let d2 = crate::tas::__RS_CZSC_SIGNAL_META_TAS_MA_BASE_V221203;
        let d3 = crate::tas::__RS_CZSC_SIGNAL_META_TAS_MACD_BASE_V221028;
        let d4 = crate::tas::__RS_CZSC_SIGNAL_META_TAS_MACD_CHANGE_V221105;
        let d5 = crate::tas::__RS_CZSC_SIGNAL_META_TAS_MACD_DIRECT_V221106;
        let d6 = crate::tas::__RS_CZSC_SIGNAL_META_TAS_MACD_POWER_V221108;
        let d7 = crate::tas::__RS_CZSC_SIGNAL_META_TAS_MACD_DIST_V230408;
        let d8 = crate::tas::__RS_CZSC_SIGNAL_META_TAS_MACD_DIST_V230409;
        let d9 = crate::tas::__RS_CZSC_SIGNAL_META_TAS_MACD_DIST_V230410;
        let d10 = crate::tas::__RS_CZSC_SIGNAL_META_TAS_CROSS_STATUS_V230619;
        let d11 = crate::tas::__RS_CZSC_SIGNAL_META_TAS_DOUBLE_MA_V221203;
        for d in [d1, d2, d3, d4, d5, d6, d7, d8, d9, d10, d11] {
            let meta = super::SIGNAL_REGISTRY
                .get(d.name)
                .unwrap_or_else(|| panic!("missing macro injected signal: {}", d.name));
            assert_eq!(meta.param_template, d.template);
        }
    }

    #[test]
    fn test_generated_descriptor_list_contains_macd_triplet() {
        let generated = super::list_generated_signal_descriptors();
        let names: std::collections::HashSet<_> = generated.iter().map(|d| d.name).collect();
        for name in [
            "tas_macd_change_V221105",
            "tas_macd_direct_V221106",
            "tas_macd_power_V221108",
        ] {
            assert!(names.contains(name), "missing generated descriptor: {name}");
        }
    }

    #[test]
    fn test_generated_descriptor_list_contains_unmigrated_baselines() {
        let generated = super::list_generated_signal_descriptors();
        let names: std::collections::HashSet<_> = generated.iter().map(|d| d.name).collect();
        for name in ["tas_rsi_base_V230227", "pos_ma_V230414"] {
            assert!(names.contains(name), "missing generated descriptor: {name}");
        }
    }

    #[test]
    fn test_generated_descriptor_list_contains_macd_dist_triplet() {
        let generated = super::list_generated_signal_descriptors();
        let names: std::collections::HashSet<_> = generated.iter().map(|d| d.name).collect();
        for name in [
            "tas_macd_dist_V230408",
            "tas_macd_dist_V230409",
            "tas_macd_dist_V230410",
        ] {
            assert!(names.contains(name), "missing generated descriptor: {name}");
        }
    }

    #[test]
    fn test_generated_descriptor_list_auto_discovers_inventory_submissions() {
        let generated = super::list_generated_signal_descriptors();
        let names: std::collections::HashSet<_> = generated.iter().map(|d| d.name).collect();
        assert!(
            names.contains("__inventory_probe_V000000"),
            "inventory submitted descriptor should be auto discovered"
        );
    }

    #[test]
    fn test_normalize_generated_rejects_duplicate_name() {
        let d1 = crate::types::SignalDescriptor {
            category: "kline",
            name: "dup_name_V000001",
            template: "a",
            opcode: "OpcodeA",
            param_kind: "A",
            func_ref: crate::types::SignalFnRef::Kline(
                __inventory_probe_signal as crate::types::SignalFn,
            ),
            fast_kline: None,
        };
        let d2 = crate::types::SignalDescriptor {
            opcode: "OpcodeB",
            ..d1
        };
        let err = match super::normalize_generated_signal_descriptors(vec![d1, d2]) {
            Ok(_) => panic!("expected duplicate signal name error"),
            Err(e) => e,
        };
        assert!(err.contains("duplicate signal name"));
    }

    #[test]
    fn test_normalize_generated_rejects_duplicate_opcode() {
        let d1 = crate::types::SignalDescriptor {
            category: "kline",
            name: "name_a_V000001",
            template: "a",
            opcode: "DupOpcode",
            param_kind: "A",
            func_ref: crate::types::SignalFnRef::Kline(
                __inventory_probe_signal as crate::types::SignalFn,
            ),
            fast_kline: None,
        };
        let d2 = crate::types::SignalDescriptor {
            name: "name_b_V000001",
            ..d1
        };
        let err = match super::normalize_generated_signal_descriptors(vec![d1, d2]) {
            Ok(_) => panic!("expected duplicate signal opcode error"),
            Err(e) => e,
        };
        assert!(err.contains("duplicate signal opcode"));
    }

    #[test]
    fn test_macro_injected_trader_descriptors_registered() {
        let d1 = crate::pos::__RS_CZSC_SIGNAL_META_POS_FX_STOP_V230414;
        let d2 = crate::pos::__RS_CZSC_SIGNAL_META_POS_STATUS_V230808;
        for d in [d1, d2] {
            let meta = super::TRADER_SIGNAL_REGISTRY
                .get(d.name)
                .unwrap_or_else(|| panic!("missing macro injected trader signal: {}", d.name));
            assert_eq!(meta.param_template, d.template);
        }
    }
}
