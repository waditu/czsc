"""
缠中说禅状态标记工具

该模块提供基于缠论分析的V字反转识别和状态标记功能，主要用于后验分析。

主要功能：
1. V字反转识别（两笔V字、四笔V字）
2. 趋势标记（基于多维度打分）
3. 震荡标记（基于多维度打分）
4. 正常标记（其他状态）

注意：该模块使用未来信息进行分析，仅适用于研究和回测，不能用于实盘交易。
"""

import pandas as pd
from typing import List, Dict, Tuple, Optional


def __two_bi_v(b1: pd.Series, b2: pd.Series, min_score: float = 0.7) -> Optional[Dict]:
    """识别两笔构成的V字反转形态

    前提条件：
    1. 至少分别有一个向下笔和向上笔的趋势打分在 min_score 以上
    2. 两笔方向相反

    识别逻辑：
    - 正V字：b1 向下、b2 向上，且 b2 的高点大于 b1 的高点
    - 倒V字：b1 向上、b2 向下，且 b2 的低点小于 b1 的低点

    :param b1: 第一笔数据
    :param b2: 第二笔数据
    :param min_score: 最小趋势打分阈值
    :return: V字模式信息，如果不符合条件返回None
    """
    # 前提条件：检查趋势打分
    if b1['score'] < min_score or b2['score'] < min_score:
        return None

    # 检查方向相反
    if b1['direction'] == b2['direction']:
        return None

    # 正V字识别：b1 向下、b2 向上，且 b2 的高点大于 b1 的高点
    if b1['direction'] == '向下' and b2['direction'] == '向上':
        if b2['high'] > b1['high']:
            return {
                'type': '两笔正V',
                'pattern': 'two_bi',
                'bi_indices': [b1['bi_idx'], b2['bi_idx']],
                'start_price': b1['high'],
                'end_price': b2['high'],
                'bottom_price': min(b1['low'], b2['low'])
            }

    # 倒V字识别：b1 向上、b2 向下，且 b2 的低点小于 b1 的低点
    elif b1['direction'] == '向上' and b2['direction'] == '向下':
        if b2['low'] < b1['low']:
            return {
                'type': '两笔倒V',
                'pattern': 'two_bi',
                'bi_indices': [b1['bi_idx'], b2['bi_idx']],
                'start_price': b1['low'],
                'end_price': b2['low'],
                'top_price': max(b1['high'], b2['high'])
            }

    return None


def __four_bi_v(b1: pd.Series, b2: pd.Series, b3: pd.Series, b4: pd.Series,
                min_score: float = 0.7) -> Optional[Dict]:
    """识别四笔构成的V字反转形态

    前提条件：
    1. 至少分别有一个向下笔和向上笔的趋势打分在 min_score 以上

    识别逻辑：
    - 正V字：第1、3笔向下，第2、4笔向上，且第4笔的高点大于第1笔的高点
      * B1最低：第1笔为最低点且得分较高
      * B3最低：第3笔为最低点且第1笔高点高于第3笔高点
    - 倒V字：第1、3笔向上，第2、4笔向下，且第4笔的低点小于第1笔的低点
      * B1最高：第1笔为最高点且得分较高
      * B3最高：第3笔为最高点且第1笔低点低于第3笔低点

    :param b1, b2, b3, b4: 四笔数据
    :param min_score: 最小趋势打分阈值
    :return: V字模式信息，如果不符合条件返回None
    """
    # 前提条件：检查至少有一个向上笔和一个向下笔的趋势打分在阈值以上
    if not __validate_four_bi_scores(b1, b2, b3, b4, min_score):
        return None

    # 计算极值
    min_low = min(b1['low'], b2['low'], b3['low'], b4['low'])
    max_high = max(b1['high'], b2['high'], b3['high'], b4['high'])

    # 正V字识别
    result = __identify_four_bi_positive_v(b1, b2, b3, b4, min_low, min_score)
    if result:
        return result

    # 倒V字识别
    result = __identify_four_bi_negative_v(b1, b2, b3, b4, max_high, min_score)
    return result


def __validate_four_bi_scores(b1: pd.Series, b2: pd.Series, b3: pd.Series, b4: pd.Series,
                              min_score: float) -> bool:
    """验证四笔的趋势打分是否满足条件"""
    up_scores = [b['score'] for b in [b1, b2, b3, b4] if b['direction'] == '向上']
    down_scores = [b['score'] for b in [b1, b2, b3, b4] if b['direction'] == '向下']

    if not up_scores or not down_scores:
        return False

    return max(up_scores) >= min_score and max(down_scores) >= min_score


def __identify_four_bi_positive_v(b1: pd.Series, b2: pd.Series, b3: pd.Series, b4: pd.Series,
                                  min_low: float, min_score: float) -> Optional[Dict]:
    """识别四笔正V字形态"""
    # 检查方向条件：1、3向下，2、4向上
    down_directions = b1['direction'] == '向下' and b3['direction'] == '向下'
    up_directions = b2['direction'] == '向上' and b4['direction'] == '向上'
    if not (down_directions and up_directions):
        return None

    if b4['high'] <= b1['high']:
        return None

    # 最低点在 b1
    if b1['low'] == min_low and b1['score'] > min_score:
        return {
            'type': '四笔正V-B1最低',
            'pattern': 'four_bi',
            'bi_indices': [b1['bi_idx'], b2['bi_idx'], b3['bi_idx'], b4['bi_idx']],
            'start_price': b1['high'],
            'end_price': b4['high'],
            'bottom_price': b1['low']
        }

    # 最低点在 b3
    if b3['low'] == min_low and b1['high'] > b3['high']:
        return {
            'type': '四笔正V-B3最低',
            'pattern': 'four_bi',
            'bi_indices': [b1['bi_idx'], b2['bi_idx'], b3['bi_idx'], b4['bi_idx']],
            'start_price': b1['high'],
            'end_price': b4['high'],
            'bottom_price': b3['low']
        }

    return None


def __identify_four_bi_negative_v(b1: pd.Series, b2: pd.Series, b3: pd.Series, b4: pd.Series,
                                  max_high: float, min_score: float) -> Optional[Dict]:
    """识别四笔倒V字形态"""
    # 检查方向条件：1、3向上，2、4向下
    up_directions = b1['direction'] == '向上' and b3['direction'] == '向上'
    down_directions = b2['direction'] == '向下' and b4['direction'] == '向下'
    if not (up_directions and down_directions):
        return None

    if b4['low'] >= b1['low']:
        return None

    # 最高点在 b1
    if b1['high'] == max_high and b1['score'] > min_score:
        return {
            'type': '四笔倒V-B1最高',
            'pattern': 'four_bi',
            'bi_indices': [b1['bi_idx'], b2['bi_idx'], b3['bi_idx'], b4['bi_idx']],
            'start_price': b1['low'],
            'end_price': b4['low'],
            'top_price': b1['high']
        }

    # 最高点在 b3
    if b3['high'] == max_high and b1['low'] < b3['low']:
        return {
            'type': '四笔倒V-B3最高',
            'pattern': 'four_bi',
            'bi_indices': [b1['bi_idx'], b2['bi_idx'], b3['bi_idx'], b4['bi_idx']],
            'start_price': b1['low'],
            'end_price': b4['low'],
            'top_price': b3['high']
        }

    return None


def __find_v(bi_stats: pd.DataFrame, min_score: float = 0.7,
             trend_ratio: float = 0.15, oscillation_ratio: float = 0.5) -> Tuple[pd.DataFrame, List[Dict]]:
    """在笔统计数据上标记V字反转、趋势、震荡笔

    实现顺序：
    1. 遍历所有笔，识别两笔和四笔V字反转，在mark列标记
    2. 对非V字反转的笔，取趋势得分最大的前trend_ratio比例，标记为趋势
    3. 对非V字反转的笔，取趋势得分最小的前oscillation_ratio比例，标记为震荡

    :param bi_stats: 笔统计数据，必须包含direction, score, bi_idx等列
    :param min_score: V字识别的最小趋势打分阈值
    :param trend_ratio: 标记为趋势的笔比例（默认15%）
    :param oscillation_ratio: 标记为震荡的笔比例（默认50%）
    :return: 带标记的笔统计DataFrame和V字模式列表
    """
    # 参数校验
    if not isinstance(bi_stats, pd.DataFrame):
        raise ValueError("bi_stats 必须是 pandas DataFrame")

    required_columns = ['direction', 'score', 'bi_idx', 'high', 'low', 'sdt', 'edt']
    missing_cols = [col for col in required_columns if col not in bi_stats.columns]
    if missing_cols:
        raise ValueError(f"bi_stats 缺少必要列: {missing_cols}")

    # 添加 mark 列，默认为 normal
    bi_stats = bi_stats.copy()
    bi_stats['mark'] = 'normal'

    v_patterns = []  # 存储找到的V字模式
    v_bi_indices = set()  # 存储参与V字模式的笔索引

    # 1. 遍历所有笔，识别V字反转
    # 两笔V字识别
    for i in range(len(bi_stats) - 1):
        v_result = __two_bi_v(bi_stats.iloc[i], bi_stats.iloc[i + 1], min_score)
        if v_result:
            v_patterns.append(v_result)
            v_bi_indices.update(v_result['bi_indices'])

    # 四笔V字识别
    for i in range(len(bi_stats) - 3):
        # 跳过已经被识别为两笔V字的笔
        if bi_stats.iloc[i]['bi_idx'] in v_bi_indices:
            continue

        v_result = __four_bi_v(
            bi_stats.iloc[i], bi_stats.iloc[i + 1],
            bi_stats.iloc[i + 2], bi_stats.iloc[i + 3], min_score
        )
        if v_result:
            v_patterns.append(v_result)
            v_bi_indices.update(v_result['bi_indices'])

    # 在 mark 列上标记 V 字反转
    bi_stats.loc[bi_stats['bi_idx'].isin(v_bi_indices), 'mark'] = 'v_reversal'

    # 2. 标记趋势和震荡笔
    non_v_mask = bi_stats['mark'] == 'normal'
    non_v_stats = bi_stats[non_v_mask]

    if len(non_v_stats) > 0:
        # 趋势标记：取趋势得分最大的前trend_ratio比例
        trend_count = max(1, int(len(non_v_stats) * trend_ratio))
        trend_bi = non_v_stats.nlargest(trend_count, 'score')
        bi_stats.loc[trend_bi.index, 'mark'] = 'trend'

        # 震荡标记：取趋势得分最小的前oscillation_ratio比例
        oscillation_count = max(1, int(len(non_v_stats) * oscillation_ratio))
        oscillation_bi = non_v_stats.nsmallest(oscillation_count, 'score')
        bi_stats.loc[oscillation_bi.index, 'mark'] = 'oscillation'

    return bi_stats, v_patterns


def mark_czsc_status(df: pd.DataFrame, **kwargs) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """【后验分析，有未来信息，不能用于实盘】标记V字反转、趋势、震荡的时间段

    该函数基于缠论分析，对K线数据进行状态标记，识别以下四种状态：
    1. V字反转：基于两笔或四笔形态识别的反转信号
    2. 趋势：基于多维度打分识别的强趋势时段
    3. 震荡：基于多维度打分识别的震荡时段
    4. 正常：其他普通时段

    :param df: 标准K线数据，必须包含 dt, symbol, open, close, high, low, vol, amount 列
    :param kwargs: 可选参数
        - copy: bool, 是否复制数据，默认True
        - verbose: bool, 是否打印日志，默认False
        - logger: 日志记录器，默认使用loguru
        - min_score: float, V字识别最小打分阈值，默认0.7
        - trend_ratio: float, 趋势笔比例，默认0.15
        - oscillation_ratio: float, 震荡笔比例，默认0.5
        - freq: str, 分析周期，默认"30分钟"

    :return: tuple, (带有标记的K线数据, 笔状态统计数据)
        - K线数据新增列：is_reversal, is_trend, is_oscillation, is_normal
        - 笔统计数据包含：笔基本信息、趋势打分、状态标记
    """
    from czsc import CZSC, format_standard_kline
    import loguru

    # 参数处理
    copy_data = kwargs.get("copy", True)
    verbose = kwargs.get("verbose", False)
    logger_obj = kwargs.get("logger", loguru.logger)
    min_score = kwargs.get("min_score", 0.7)
    trend_ratio = kwargs.get("trend_ratio", 0.15)
    oscillation_ratio = kwargs.get("oscillation_ratio", 0.5)
    freq = kwargs.get("freq", "30分钟")

    # 参数校验
    if not isinstance(df, pd.DataFrame):
        raise ValueError("df 必须是 pandas DataFrame")

    required_columns = ['dt', 'symbol', 'open', 'close', 'high', 'low', 'vol']
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        raise ValueError(f"K线数据缺少必要列: {missing_cols}")

    # 数据预处理
    if copy_data:
        df = df.copy()

    all_bi_stats = []
    all_kline_data = []

    # 按品种分组处理
    for symbol, dfg in df.groupby("symbol"):
        if verbose:
            logger_obj.info(
                f"正在处理 {symbol} 数据，共 {len(dfg)} 根K线；"
                f"时间范围：{dfg['dt'].min()} - {dfg['dt'].max()}"
            )

        # 数据排序和格式化
        dfg = dfg.sort_values("dt").copy().reset_index(drop=True)
        bars = format_standard_kline(dfg, freq=freq)

        if len(bars) < 300:  # 至少需要300根K线才能进行有效的缠论分析
            if verbose:
                logger_obj.warning(f"{symbol} 数据不足，跳过分析")
            continue

        # 缠论分析
        c = CZSC(bars, max_bi_num=len(bars))

        if len(c.bi_list) < 4:  # 至少需要4笔才能进行V字识别
            if verbose:
                logger_obj.warning(f"{symbol} 笔数量不足，跳过V字识别")
            # 仍然进行基本的趋势标记
            bi_stats = []
            for bi_idx, bi in enumerate(c.bi_list):
                bi_stats.append({
                    "symbol": symbol,
                    "bi_idx": bi_idx,
                    "sdt": bi.sdt,
                    "edt": bi.edt,
                    "direction": bi.direction.value,
                    "high": bi.high,
                    "low": bi.low,
                    "power_price": abs(bi.change),
                    "length": bi.length,
                    "rsq": bi.rsq,
                    "power_volume": bi.power_volume,
                })
            bi_stats = pd.DataFrame(bi_stats)
        else:
            # 提取笔统计信息
            bi_stats = []
            for bi_idx, bi in enumerate(c.bi_list):
                bi_stats.append({
                    "symbol": symbol,
                    "bi_idx": bi_idx,
                    "sdt": bi.sdt,
                    "edt": bi.edt,
                    "direction": bi.direction.value,
                    "high": bi.high,
                    "low": bi.low,
                    "power_price": abs(bi.change),
                    "length": bi.length,
                    "rsq": bi.rsq,
                    "power_volume": bi.power_volume,
                })
            bi_stats = pd.DataFrame(bi_stats)

            # 计算滚动排名指标
            window_size = min(100, len(bi_stats))
            min_periods = min(10, len(bi_stats) // 2)

            bi_stats["power_price_rank"] = (
                bi_stats["power_price"].rolling(window=window_size, min_periods=min_periods)
                .rank(method="min", ascending=True, pct=True)
            )
            bi_stats["rsq_rank"] = (
                bi_stats["rsq"].rolling(window=window_size, min_periods=min_periods)
                .rank(method="min", ascending=True, pct=True)
            )
            bi_stats["power_volume_rank"] = (
                bi_stats["power_volume"].rolling(window=window_size, min_periods=min_periods)
                .rank(method="min", ascending=True, pct=True)
            )

            # 计算趋势度打分
            price_rank = bi_stats["power_price_rank"]
            rsq_rank = bi_stats["rsq_rank"]
            volume_rank = bi_stats["power_volume_rank"]
            bi_stats["score"] = price_rank + rsq_rank + volume_rank
            bi_stats["score"] = bi_stats["score"].rank(method="min", ascending=True, pct=True)

            # V字反转识别和状态标记
            bi_stats, v_patterns = __find_v(
                bi_stats.dropna(subset=['score']).reset_index(drop=True),
                min_score=min_score,
                trend_ratio=trend_ratio,
                oscillation_ratio=oscillation_ratio
            )

            if verbose:
                mark_counts = bi_stats['mark'].value_counts().to_dict()
                logger_obj.info(f"{symbol} - 笔类型统计: {mark_counts}")

                if v_patterns:
                    v_type_counts = pd.DataFrame(v_patterns)['type'].value_counts().to_dict()
                    logger_obj.info(f"{symbol} - V字模式分类：{v_type_counts}")

        # 初始化状态标记列
        dfg["is_reversal"] = 0
        dfg["is_trend"] = 0
        dfg["is_oscillation"] = 0
        dfg["is_normal"] = 0

        # 根据笔状态标记对应的时间段
        if 'mark' in bi_stats.columns:
            # V字反转标记
            v_reversal_bis = bi_stats[bi_stats['mark'] == 'v_reversal']
            for _, row in v_reversal_bis.iterrows():
                dfg.loc[(dfg["dt"] >= row["sdt"]) & (dfg["dt"] <= row["edt"]), "is_reversal"] = 1

            # 趋势标记
            trend_bis = bi_stats[bi_stats['mark'] == 'trend']
            for _, row in trend_bis.iterrows():
                dfg.loc[(dfg["dt"] >= row["sdt"]) & (dfg["dt"] <= row["edt"]), "is_trend"] = 1

            # 震荡标记
            oscillation_bis = bi_stats[bi_stats['mark'] == 'oscillation']
            for _, row in oscillation_bis.iterrows():
                dfg.loc[(dfg["dt"] >= row["sdt"]) & (dfg["dt"] <= row["edt"]), "is_oscillation"] = 1

            # 正常标记
            normal_bis = bi_stats[bi_stats['mark'] == 'normal']
            for _, row in normal_bis.iterrows():
                dfg.loc[(dfg["dt"] >= row["sdt"]) & (dfg["dt"] <= row["edt"]), "is_normal"] = 1

        all_bi_stats.append(bi_stats)
        all_kline_data.append(dfg)

    # 合并所有品种的数据
    if not all_kline_data:
        raise ValueError("没有足够的数据进行分析")

    dfr = pd.concat(all_kline_data, ignore_index=True)
    bi_stats_all = pd.concat(all_bi_stats, ignore_index=True)

    # 输出统计信息
    if verbose:
        total_rows = len(dfr)
        reversal_coverage = dfr['is_reversal'].sum() / total_rows * 100
        trend_coverage = dfr['is_trend'].sum() / total_rows * 100
        oscillation_coverage = dfr['is_oscillation'].sum() / total_rows * 100
        normal_coverage = dfr['is_normal'].sum() / total_rows * 100

        logger_obj.info(
            f"状态标记覆盖率统计：\n"
            f"  V字反转：{reversal_coverage:.2f}%\n"
            f"  趋势时间：{trend_coverage:.2f}%\n"
            f"  震荡时间：{oscillation_coverage:.2f}%\n"
            f"  正常时间：{normal_coverage:.2f}%"
        )

    return dfr, bi_stats_all
