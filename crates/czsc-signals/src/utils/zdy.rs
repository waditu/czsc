use crate::types::TaCache;
use crate::utils::ta::update_macd_cache;
use czsc_core::analyze::CZSC;
use czsc_core::objects::bi::BI;
use czsc_core::objects::zs::ZS;
use std::collections::HashMap;

pub fn macd_cache_maps(
    c: &CZSC,
    fast: usize,
    slow: usize,
    signal: usize,
    cache: &mut TaCache,
) -> (HashMap<i32, f64>, HashMap<i32, f64>, HashMap<i32, f64>) {
    let short = fast.min(slow);
    let long = fast.max(slow);
    let cache_key = format!("MACD{}#{}#{}", short, long, signal);
    update_macd_cache(c, &cache_key, short, long, signal, cache);

    let mut dif_map = HashMap::new();
    let mut dea_map = HashMap::new();
    let mut macd_map = HashMap::new();
    if let Some(series) = cache.macd.get(&cache_key) {
        for (i, id) in series.ids.iter().enumerate() {
            dif_map.insert(*id, series.dif[i]);
            dea_map.insert(*id, series.dea[i]);
            macd_map.insert(*id, series.macd[i]);
        }
    }
    (dif_map, dea_map, macd_map)
}

pub fn is_valid_zs(bis: &[BI]) -> bool {
    if bis.len() < 3 {
        return false;
    }
    ZS::new(bis.to_vec()).is_valid()
}

pub fn find_peaks_valleys(data: &[f64]) -> (HashMap<usize, f64>, HashMap<usize, f64>) {
    let mut peaks = HashMap::new();
    let mut valleys = HashMap::new();
    if data.len() < 5 {
        return (peaks, valleys);
    }
    for i in 2..data.len() - 2 {
        if data[i - 2] < data[i - 1]
            && data[i - 1] < data[i]
            && data[i] > data[i + 1]
            && data[i + 1] > data[i + 2]
        {
            peaks.insert(i, data[i]);
        }
        if data[i - 2] > data[i - 1]
            && data[i - 1] > data[i]
            && data[i] < data[i + 1]
            && data[i + 1] < data[i + 2]
        {
            valleys.insert(i, data[i]);
        }
    }
    (peaks, valleys)
}
