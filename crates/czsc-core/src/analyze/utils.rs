use super::errors::AnalyzeErorr;
use crate::objects::bar::RawBarBuilder;
use crate::objects::{
    bar::{NewBar, NewBarBuilder, RawBar},
    bi::{BI, BIBuilder},
    direction::Direction,
    freq::Freq,
    fx::{FX, FXBuilder},
    mark::Mark,
};
use anyhow::Context;
use chrono::DateTime;
use chrono::Utc;
use polars::frame::DataFrame;
use polars::prelude::TimeUnit;

/// 去除包含关系：输入三根k线，其中k1和k2为没有包含关系的K线，k3为原始K线
/// 处理逻辑如下：
///
/// 1. 首先，通过比较k1和k2的高点(high)的大小关系来确定direction的值。如果k1的高点小于k2的高点，
///    则设定direction为Up；如果k1的高点大于k2的高点，则设定direction为Down；如果k1和k2的高点相等，
///    则创建一个新的K线k4，与k3具有相同的属性，并返回False和k4。
///
/// 2. 接下来，判断k2和k3之间是否存在包含关系。如果存在，则根据direction的值进行处理。
///     - 如果direction为Up，则选择k2和k3中的较大高点作为新K线k4的高点，较大低点作为低点，较大高点所在的时间戳(dt)作为k4的时间戳。
///     - 如果direction为Down，则选择k2和k3中的较小高点作为新K线k4的高点，较小低点作为低点，较小低点所在的时间戳(dt)作为k4的时间戳。
///
/// 3. 根据上述处理得到的高点、低点、开盘价(open_)、收盘价(close)，计算新K线k4的成交量(vol)和成交金额(amount)，
///    并将k2中除了与k3时间戳相同的元素之外的其他元素与k3一起作为k4的元素列表(elements)。
///
/// 4. 返回一个布尔值和新的K线k4。如果k2和k3之间存在包含关系，则返回True和k4；否则返回False和k4，其中k4与k3具有相同的属性。
pub fn remove_include(
    k1: &NewBar,
    k2: &NewBar,
    k3: RawBar,
) -> Result<(bool, NewBar), AnalyzeErorr> {
    // 根据k1和k2的high确定direction
    let direction = if k1.high < k2.high {
        Direction::Up
    } else if k1.high > k2.high {
        Direction::Down
    } else {
        return Ok((false, NewBar::new_from_raw(&k3)));
    };

    // 检查k2和k3是否存在包含关系
    let has_inclusion =
        (k2.high <= k3.high && k2.low >= k3.low) || (k2.high >= k3.high && k2.low <= k3.low);

    if !has_inclusion {
        return Ok((false, NewBar::new_from_raw(&k3)));
    }

    // 处理包含关系
    let (high, low, dt) = match direction {
        Direction::Up => {
            let high = k2.high.max(k3.high);
            let low = k2.low.max(k3.low);
            let dt = if k2.high > k3.high { k2.dt } else { k3.dt };
            (high, low, dt)
        }
        Direction::Down => {
            let high = k2.high.min(k3.high);
            let low = k2.low.min(k3.low);
            let dt = if k2.low < k3.low { k2.dt } else { k3.dt };
            (high, low, dt)
        }
    };

    let (open_, close) = if k3.open > k3.close {
        (high, low)
    } else {
        (low, high)
    };

    let k4 = {
        let k3_dt = k3.dt;
        NewBarBuilder::default()
            .symbol(k2.symbol.clone())
            .id(k2.id)
            .freq(k2.freq)
            .dt(dt)
            .open(open_)
            .close(close)
            .high(high)
            .low(low)
            .vol(k2.vol + k3.vol)
            .amount(k2.amount + k3.amount)
            .elements(
                k2.elements
                    .iter()
                    .take(100)
                    .filter(|x| x.dt != k3_dt)
                    .cloned()
                    .chain(std::iter::once(k3))
                    .collect::<Vec<RawBar>>(),
            )
            .build()
            .context("Failed to new NewBar")?
    };

    Ok((true, k4))
}

///    输入一串无包含关系K线，查找其中所有分型
///
///    函数的主要步骤：
///
///    1. 创建一个空列表`fxs`用于存储找到的分型。
///    2. 遍历`bars`列表中的每个元素（除了第一个和最后一个），并对每三个连续的`NewBar`对象调用`check_fx`函数。
///    3. 如果`check_fx`函数返回一个`FX`对象，检查它的标记是否与`fxs`列表中最后一个`FX`对象的标记相同。如果相同，记录一个错误日志。
///       如果不同，将这个`FX`对象添加到`fxs`列表中。
///    4. 最后返回`fxs`列表，它包含了`bars`列表中所有找到的分型。
///
///    这个函数的主要目的是找出`bars`列表中所有的顶分型和底分型，并确保它们是交替出现的。如果发现连续的两个分型标记相同，它会记录一个错误日志。
///
///    :param bars: 无包含关系K线列表
///    :return: 分型列表
pub fn check_fxs<B: AsRef<NewBar>>(bars: &[B]) -> Vec<FX> {
    let mut fxs: Vec<FX> = Vec::new();
    for window in bars[0..bars.len()].windows(3) {
        if let [k1, k2, k3] = window
            && let Some(fx1) = check_fx(k1.as_ref(), k2.as_ref(), k3.as_ref())
        {
            // 与Python版本保持一致：过滤重复的相同标记分型
            // 默认情况下，fxs本身是顶底交替的，但是对于一些特殊情况下不是这样; 临时强制要求fxs序列顶底交替
            if fxs.len() >= 2 && fx1.mark == fxs.last().unwrap().mark {
                eprintln!(
                    "check_fxs错误: {}，{:?}，{:?}",
                    k2.as_ref().dt,
                    fx1.mark,
                    fxs.last().unwrap().mark
                );
            } else {
                fxs.push(fx1);
            }
        }
    }
    fxs
}

///    查找分型
///
///    函数计算逻辑：
///
///    1. 如果第二个`NewBar`对象的最高价和最低价都高于第一个和第三个`NewBar`对象的对应价格，那么它被认为是顶分型（G）。
///       在这种情况下，函数会创建一个新的`FX`对象，其标记为`Mark.G`，并将其赋值给`fx`。
///
///    2. 如果第二个`NewBar`对象的最高价和最低价都低于第一个和第三个`NewBar`对象的对应价格，那么它被认为是底分型（D）。
///       在这种情况下，函数会创建一个新的`FX`对象，其标记为`Mark.D`，并将其赋值给`fx`。
///
///    3. 函数最后返回`fx`，如果没有找到分型，`fx`将为`None`。
///
///    :param k1: 第一个`NewBar`对象
///    :param k2: 第二个`NewBar`对象
///    :param k3: 第三个`NewBar`对象
///    :return: `FX`对象或`None`
pub fn check_fx(k1: &NewBar, k2: &NewBar, k3: &NewBar) -> Option<FX> {
    // 顶分型判断
    if k1.high < k2.high && k2.high > k3.high && k1.low < k2.low && k2.low > k3.low {
        return Some(
            FXBuilder::default()
                .symbol(k1.symbol.clone())
                .dt(k2.dt)
                .mark(Mark::G)
                .high(k2.high)
                .low(k2.low)
                .fx(k2.high)
                .elements(vec![k1.clone(), k2.clone(), k3.clone()])
                .build()
                .unwrap(),
        );
    }

    // 底分型判断
    if k1.low > k2.low && k2.low < k3.low && k1.high > k2.high && k2.high < k3.high {
        return Some(
            FXBuilder::default()
                .symbol(k1.symbol.clone())
                .dt(k2.dt)
                .mark(Mark::D)
                .high(k2.high)
                .low(k2.low)
                .fx(k2.low)
                .elements(vec![k1.clone(), k2.clone(), k3.clone()])
                .build()
                .unwrap(),
        );
    }

    None
}

///    输入一串无包含关系K线，查找其中的一笔
///
///    :param bars: 无包含关系K线列表
///    :return:
pub fn check_bi<B>(bars: &[B]) -> (Option<BI>, &[B])
where
    B: AsRef<NewBar>,
{
    let fxs = check_fxs(bars);
    if fxs.len() < 2 {
        return (None, bars);
    }

    let fx_a = &fxs[0];
    let (direction, fx_b) = match fx_a.mark {
        Mark::D => {
            // 对齐 Python max(..., key=fx.high):
            // 仅当更高时替换；并列时保留首次出现的候选。
            let mut fx_b: Option<&FX> = None;
            for x in fxs
                .iter()
                .filter(|x| x.mark == Mark::G && x.dt > fx_a.dt && x.fx > fx_a.fx)
            {
                match fx_b {
                    None => fx_b = Some(x),
                    Some(best) if x.high > best.high => fx_b = Some(x),
                    _ => {}
                }
            }
            let fx_b = fx_b.cloned();
            (Direction::Up, fx_b)
        }
        Mark::G => {
            // 对齐 Python min(..., key=fx.low):
            // 仅当更低时替换；并列时保留首次出现的候选。
            let mut fx_b: Option<&FX> = None;
            for x in fxs
                .iter()
                .filter(|x| x.mark == Mark::D && x.dt > fx_a.dt && x.fx < fx_a.fx)
            {
                match fx_b {
                    None => fx_b = Some(x),
                    Some(best) if x.low < best.low => fx_b = Some(x),
                    _ => {}
                }
            }
            let fx_b = fx_b.cloned();
            (Direction::Down, fx_b)
        }
    };

    let fx_b = match fx_b {
        Some(fx) => fx,
        None => return (None, bars),
    };

    // 确定bars_a的起始和结束索引
    let start_dt = fx_a.elements[0].dt;
    let end_dt = fx_b.elements[2].dt;

    let start_idx = bars.partition_point(|bar| bar.as_ref().dt < start_dt);
    let end_idx = bars.partition_point(|bar| bar.as_ref().dt <= end_dt);
    if start_idx >= end_idx {
        return (None, bars);
    }

    let bars_a = &bars[start_idx..end_idx];

    // 确定剩余bars_b的起始索引（基于fx_b.elements[0].dt）
    let new_start_dt = fx_b.elements[0].dt;
    let new_start_idx = bars.partition_point(|bar| bar.as_ref().dt < new_start_dt);
    let bars_b = &bars[new_start_idx..];

    // 判断包含关系
    let ab_include = (fx_a.high > fx_b.high && fx_a.low < fx_b.low)
        || (fx_a.high < fx_b.high && fx_a.low > fx_b.low);

    // todo
    let min_bi_len = 6;
    // 检查成笔条件
    if !ab_include && bars_a.len() >= min_bi_len {
        let fxs_filtered: Vec<_> = fxs
            .iter()
            .filter(|x| x.dt >= start_dt && x.dt <= end_dt)
            .cloned()
            .collect();

        let bi = BIBuilder::default()
            .symbol(fx_a.symbol.clone())
            .fx_a(fx_a.clone())
            .fx_b(fx_b.clone())
            .fxs(fxs_filtered)
            .direction(direction)
            .bars(
                bars_a
                    .iter()
                    .map(|b| b.as_ref().to_owned())
                    .collect::<Vec<NewBar>>(),
            )
            .build()
            .unwrap();

        (Some(bi), bars_b)
    } else {
        (None, bars)
    }
}

/// # 格式化标准K线数据为 CZSC 标准数据结构 RawBar 列表
///
/// ## 参数
///
/// * `df` - 标准K线数据，DataFrame结构。每一行包含以下字段：
///     - `dt`: 时间
///     - `symbol`: 股票代码
///     - `open`: 开盘价
///     - `close`: 收盘价
///     - `high`: 最高价
///     - `low`: 最低价
///     - `vol`: 成交量
///     - `amount`: 成交金额
///
/// * `freq` - K线级别
///
/// ## 返回值
/// 返回一个 `RawBar` 列表，表示格式化后的K线数据。
///
/// ## 示例
/// ```ignore
/// let df = // 创建 DataFrame 示例数据;
/// let freq = Freq::D;  // K线级别
/// let result = format_standard_kline(df, freq);
/// ```
///
pub fn format_standard_kline(df: DataFrame, freq: Freq) -> Result<Vec<RawBar>, AnalyzeErorr> {
    // 获取各列的 Series 引用
    let symbol_col = df.column("symbol")?.str()?;
    let dt_col = df.column("dt")?.datetime()?;
    let open_col = df.column("open")?.f64()?;
    let close_col = df.column("close")?.f64()?;
    let high_col = df.column("high")?.f64()?;
    let low_col = df.column("low")?.f64()?;
    let vol_col = df.column("vol")?.f64()?;
    let amount_col = df.column("amount")?.f64()?;

    // 获取时间单位信息
    let time_unit = dt_col.time_unit();

    let len = df.height();
    let mut bars = Vec::with_capacity(len);
    for i in 0..len {
        // 时间戳数值
        let ts = dt_col.phys.get(i).unwrap();
        // 根据时间单位转换为纳秒
        let ns = match time_unit {
            TimeUnit::Milliseconds => ts * 1_000_000,
            TimeUnit::Microseconds => ts * 1_000,
            TimeUnit::Nanoseconds => ts,
        };
        let dt_utc = DateTime::<Utc>::from_timestamp_nanos(ns);

        // TODO 是否检查df有没有Nan?
        let bar = RawBarBuilder::default()
            .symbol(symbol_col.get(i).unwrap_or(""))
            .id(i as i32)
            .dt(dt_utc)
            .freq(freq)
            .open(open_col.get(i).unwrap())
            .close(close_col.get(i).unwrap())
            .high(high_col.get(i).unwrap())
            .low(low_col.get(i).unwrap())
            .vol(vol_col.get(i).unwrap())
            .amount(amount_col.get(i).unwrap())
            .build()
            .context("Failed to create raw bar")?;

        bars.push(bar);
    }

    Ok(bars)
}
