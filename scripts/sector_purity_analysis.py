"""同花顺概念板块「成分股纯度」分析。

做交易要做龙头，龙头分行业 / 分板块；第一步是找出成分股纯度高的板块——即板块内
个股是否被同一条主线（共同因子）驱动、是否齐涨齐跌。本脚本对每个同花顺概念板块的
成分股日收益做纯度打分（0~100，越高越纯），并汇总成一份自包含 HTML 报告。

两版打分指标（均来自任务文档）：

1. 第一主成分解释力 / Absorption Ratio（最贴本质，最推荐）
   对标准化后的收益矩阵 R̃ 做 PCA，第一主成分解释方差占比 λ₁ / Σλ 即为板块凝聚度。
       score1 = (λ₁ / Σλ) × 100
   含义：板块是否被单一共同因子驱动——这正是「板块作为一个整体」的数学定义，
   也是金融文献里 Absorption Ratio（系统性风险 / 板块凝聚度）的标准做法。

2. 齐涨齐跌方向一致性（无需相关矩阵，极快、对异常股不敏感）
   每个交易日 t：方向一致率 c_t = max(上涨股占比, 下跌股占比)，取 T 天平均 c̄。
   随机情形下 c̄ 期望约 0.6（不是 0.5），故按 0.55 重标定：
       score2 = clip((c̄ - 0.55) / (1 - 0.55), 0, 1) × 100

数据流（关键优化）：
   同花顺概念板块约 400+ 个、成分股并集近全市场（~5000 只）。逐股取日线需要数千次
   API 调用；本脚本改为「按交易日取全市场日线」——T 个交易日仅 T 次调用，再透视成
   收益矩阵（日期 × ts_code），各板块只需在矩阵上切列即可，省时且充分利用磁盘缓存。

用法：
    # 默认最近 250 个交易日，处理全部概念板块
    uv run --no-sync python scripts/sector_purity_analysis.py

    # 指定窗口 + 仅跑前 20 个板块（快速验证）
    uv run --no-sync python scripts/sector_purity_analysis.py --start 20240101 --end 20241231 --limit 20

    # 自定义输出目录
    uv run --no-sync python scripts/sector_purity_analysis.py --output-dir ~/sector_purity

TUSHARE_TOKEN 从环境变量或项目根目录 .env 读取。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]

# ---- 默认参数（模块级常量，避免魔法值）-------------------------------------
TUSHARE_URL = "http://api.tushare.pro"
# 同花顺指数类型（ths_index 的 type 参数）-> 中文标签
INDEX_TYPE_LABELS = {"N": "概念", "I": "行业", "R": "地域", "S": "特色", "ST": "风格", "TH": "主题", "BB": "宽基"}
DEFAULT_DAYS = 250  # 未显式给定起止日期时，回看的交易日数量
MIN_MEMBERS = 5  # 板块有效成分股下限，少于此数不计算
MIN_OBS_DAYS = 60  # 收益序列最少观测天数
MAX_MISSING_RATIO = 0.30  # 单只成分股窗口内缺失比例上限，超过则剔除
DIRECTION_BASELINE = 0.55  # 齐涨齐跌随机基准（重标定锚点）
THS_MEMBER_INTERVAL = 0.14  # ths_member 调用间隔（秒），约 430 次/分钟，规避 500 次/分钟限频
THS_MEMBER_RETRY_SLEEP = 5  # 限频失败后的退避等待（秒）
# 重试次数。节流已能规避限频，且大量行业指数（如 700/861 前缀）本就无成分数据，
# 对空结果重试纯属浪费，故默认 0；如遇限频可临时调大。
THS_MEMBER_RETRIES = 0
CACHE_PATH = os.path.expanduser("~/.quant_data_cache")


# ============================================================================
# 数据获取
# ============================================================================
def _load_dotenv(root: Path) -> None:
    """把项目根目录 .env 里的键值写入环境变量（不覆盖已存在的）。"""
    env_file = root / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def build_client(token: str | None):
    """构造带磁盘缓存的 Tushare DataClient。"""
    from czsc import DataClient

    token = token or os.environ.get("TUSHARE_TOKEN")
    if not token:
        logger.error("未找到 TUSHARE_TOKEN，请在 .env 或环境变量中设置")
        sys.exit(1)
    return DataClient(token=token, url=TUSHARE_URL, cache_path=CACHE_PATH)


def resolve_trade_dates(dc, start: str | None, end: str | None, days: int) -> list[str]:
    """返回窗口内的交易日列表（升序，YYYYMMDD）。

    显式给定 start/end 时取区间内全部交易日；否则取截至 end（默认今天）最近 days 个交易日。
    """
    end = end or datetime.now().strftime("%Y%m%d")
    cal_start = start or (datetime.strptime(end, "%Y%m%d") - timedelta(days=int(days * 2.2) + 60)).strftime("%Y%m%d")
    cal = dc.trade_cal(exchange="SSE", start_date=cal_start, end_date=end, is_open="1")
    trade_dates = sorted(cal["cal_date"].astype(str).tolist())
    if not start:
        trade_dates = trade_dates[-days:]
    return trade_dates


def fetch_concept_list(dc, index_type: str, limit: int | None) -> pd.DataFrame:
    """获取同花顺指定类型的板块列表（type=N 概念 / I 行业 ...）。"""
    idx = dc.ths_index(type=index_type)
    idx = idx.dropna(subset=["ts_code"]).reset_index(drop=True)
    if limit:
        idx = idx.head(limit).copy()
    logger.info(f"{INDEX_TYPE_LABELS.get(index_type, index_type)}板块数量：{len(idx)}")
    return idx


def _ths_member_with_retry(dc, code: str, retries: int = THS_MEMBER_RETRIES):
    """获取单个板块成分股，遇限频（40203）/空结果时退避重试。"""
    mem = None
    for attempt in range(retries + 1):
        try:
            mem = dc.ths_member(ts_code=code)
        except Exception:  # noqa: BLE001
            mem = None
        if mem is not None and not mem.empty:
            return mem
        if attempt < retries:
            time.sleep(THS_MEMBER_RETRY_SLEEP)  # 等待限频窗口恢复
    return mem


def fetch_members(dc, concept_codes: list[str]) -> dict[str, list[str]]:
    """逐板块获取成分股，返回 {板块代码: [成分股 ts_code, ...]}。

    ths_member 限频 500 次/分钟，板块数可能上千（行业指数），故每次调用间隔节流，
    并对限频失败做退避重试；命中磁盘缓存时不触发网络请求。
    """
    members: dict[str, list[str]] = {}
    for code in tqdm(concept_codes, desc="拉取板块成分股"):
        mem = _ths_member_with_retry(dc, code)
        time.sleep(THS_MEMBER_INTERVAL)  # 节流，规避 500 次/分钟限频
        if mem is None or mem.empty or "con_code" not in mem.columns:
            logger.warning(f"{code} 成分股为空 / 获取失败，跳过")
            continue
        members[code] = mem["con_code"].dropna().unique().tolist()
    return members


def fetch_return_matrix(dc, trade_dates: list[str], universe: set[str]) -> pd.DataFrame:
    """按交易日取全市场日线，透视成收益矩阵（index=日期, columns=ts_code, value=日收益）。

    日收益 = pct_chg / 100（pct_chg 已对除权除息做了 pre_close 调整）。
    """
    frames = []
    for d in tqdm(trade_dates, desc="拉取全市场日线"):
        try:
            day = dc.daily(trade_date=d, fields="ts_code,trade_date,pct_chg")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"{d} 日线获取失败：{e}")
            continue
        if day is None or day.empty:
            continue
        day = day[day["ts_code"].isin(universe)]
        frames.append(day[["trade_date", "ts_code", "pct_chg"]])

    if not frames:
        return pd.DataFrame()

    raw = pd.concat(frames, ignore_index=True)
    raw["ret"] = raw["pct_chg"].astype(float) / 100.0
    matrix = raw.pivot_table(index="trade_date", columns="ts_code", values="ret")
    matrix = matrix.sort_index()
    return matrix


# ============================================================================
# 纯度打分
# ============================================================================
def _clean_block(returns: pd.DataFrame) -> pd.DataFrame:
    """剔除缺失过多 / 零波动的成分股列，返回可用于打分的子矩阵。"""
    if returns.empty:
        return returns
    keep = returns.columns[returns.isna().mean() <= MAX_MISSING_RATIO]
    block = returns[keep]
    # 缺失天数较少的留下，剩余缺口按 0 填充（停牌当日视为零收益）
    block = block.dropna(axis=1, thresh=int(len(block) * (1 - MAX_MISSING_RATIO))).fillna(0.0)
    # 剔除整列零波动（长期停牌 / 新股未上市）
    block = block.loc[:, block.std(axis=0) > 1e-9]
    return block


def absorption_ratio(block: pd.DataFrame) -> float:
    """第一主成分解释方差占比 λ₁ / Σλ。

    对每列做 z-score 标准化（等价于对相关矩阵做 PCA），再用 SVD 求奇异值，
    λᵢ ∝ sᵢ²，故 AR = s₁² / Σsᵢ²。返回 0~1 的占比。
    """
    x = block.to_numpy(dtype=float)
    x = x - x.mean(axis=0, keepdims=True)
    std = x.std(axis=0, ddof=0, keepdims=True)
    std[std < 1e-12] = 1.0
    x = x / std
    # 奇异值平方正比于协方差/相关矩阵特征值
    sv = np.linalg.svd(x, compute_uv=False)
    eig = sv**2
    total = eig.sum()
    if total <= 0:
        return float("nan")
    return float(eig[0] / total)


def direction_consistency(block: pd.DataFrame) -> float:
    """齐涨齐跌方向一致率均值 c̄。

    每个交易日 c_t = max(上涨股占比, 下跌股占比)，分母为当日有效成分股数。
    """
    up = (block > 0).sum(axis=1)
    down = (block < 0).sum(axis=1)
    n = up + down + (block == 0).sum(axis=1)
    n = n.replace(0, np.nan)
    c_t = pd.concat([up / n, down / n], axis=1).max(axis=1)
    return float(c_t.mean())


def score_sector(returns: pd.DataFrame) -> dict | None:
    """对单个板块的成分股收益矩阵计算两版打分。"""
    block = _clean_block(returns)
    if block.shape[1] < MIN_MEMBERS or block.shape[0] < MIN_OBS_DAYS:
        return None

    ar = absorption_ratio(block)
    cbar = direction_consistency(block)
    score1 = ar * 100.0
    score2 = float(np.clip((cbar - DIRECTION_BASELINE) / (1 - DIRECTION_BASELINE), 0, 1) * 100.0)
    return {
        "n_valid": block.shape[1],
        "n_days": block.shape[0],
        "absorption_ratio": round(ar, 4),
        "score_absorption": round(score1, 2),
        "dir_consistency": round(cbar, 4),
        "score_direction": round(score2, 2),
        "score_avg": round((score1 + score2) / 2, 2),
        "_valid_codes": tuple(sorted(block.columns)),  # 用于去重：清洗后真正参与打分的成分集合
    }


def _dedup_by_members(df: pd.DataFrame) -> pd.DataFrame:
    """按「有效成分集合」去重。

    同花顺行业指数存在层级冗余（如 保险 / 保险Ⅲ / 保险Ⅲ(A股) 经清洗后落到同一批
    成分股，打分完全相同）。这里把有效成分集合相同的指数合并为一行，代表项取名称最短
    （最简洁的层级，如"保险"而非"保险Ⅲ(A股)"），并记录合并数量与被合并的别名。
    """
    df = df.copy()
    df["_key"] = df["_valid_codes"].map(lambda t: "|".join(t))
    df["_namelen"] = df["name"].str.len()
    out = []
    for _, g in df.groupby("_key", sort=False):
        g = g.sort_values(["_namelen", "n_members"], ascending=[True, False])
        rep = g.iloc[0].to_dict()
        rep["n_merged"] = len(g)
        rep["aliases"] = "，".join(n for n in g["name"].tolist() if n != rep["name"])
        out.append(rep)
    return pd.DataFrame(out)


def analyze(
    dc, concepts: pd.DataFrame, members: dict[str, list[str]], matrix: pd.DataFrame, dedup: bool = False
) -> pd.DataFrame:
    """逐板块打分，返回结果 DataFrame（按综合分降序）。dedup=True 时按有效成分集合去重。"""
    name_map = dict(zip(concepts["ts_code"], concepts["name"], strict=False))
    count_map = dict(zip(concepts["ts_code"], concepts.get("count", pd.Series(dtype=float)), strict=False))
    rows = []
    for code, cons in tqdm(members.items(), desc="计算板块纯度"):
        cols = [c for c in cons if c in matrix.columns]
        if len(cols) < MIN_MEMBERS:
            continue
        res = score_sector(matrix[cols])
        if res is None:
            continue
        cnt = count_map.get(code)
        res.update(
            {
                "ts_code": code,
                "name": name_map.get(code, code),
                "n_members": int(cnt) if cnt is not None and not pd.isna(cnt) else len(cons),
            }
        )
        rows.append(res)

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    if dedup:
        df = _dedup_by_members(df)
    cols = [
        "ts_code",
        "name",
        "n_members",
        "n_valid",
        "n_days",
        "score_avg",
        "score_absorption",
        "absorption_ratio",
        "score_direction",
        "dir_consistency",
    ]
    if dedup:
        cols += ["n_merged", "aliases"]
    df = df[cols].sort_values("score_avg", ascending=False, ignore_index=True)
    df.insert(0, "rank", range(1, len(df) + 1))
    return df


# ============================================================================
# HTML 报告
# ============================================================================
def build_html_report(df: pd.DataFrame, meta: dict, out_path: Path) -> None:
    """生成自包含 HTML 报告：散点图 + Top 排行柱状图 + 可排序明细表。"""
    import plotly.graph_objects as go
    from plotly.offline import get_plotlyjs

    # 散点：吸收率得分 vs 方向一致性得分
    scatter = go.Figure()
    scatter.add_trace(
        go.Scatter(
            x=df["score_absorption"],
            y=df["score_direction"],
            mode="markers",
            marker={
                "size": 7,
                "color": df["score_avg"],
                "colorscale": "RdYlGn",
                "showscale": True,
                "colorbar": {"title": "综合分"},
                "line": {"width": 0.5, "color": "#555"},
            },
            text=df["name"],
            customdata=df[["ts_code", "n_valid"]],
            hovertemplate="<b>%{text}</b><br>吸收率分: %{x}<br>一致性分: %{y}"
            "<br>代码: %{customdata[0]}<br>有效成分: %{customdata[1]}<extra></extra>",
        )
    )
    scatter.update_layout(
        title="板块纯度分布：第一主成分解释力 vs 齐涨齐跌一致性",
        xaxis_title="Absorption 得分",
        yaxis_title="方向一致性得分",
        template="plotly_white",
        height=520,
    )

    # Top 30 柱状图
    top = df.head(30).iloc[::-1]
    bar = go.Figure()
    bar.add_trace(
        go.Bar(x=top["score_absorption"], y=top["name"], orientation="h", name="Absorption", marker_color="#2c7fb8")
    )
    bar.add_trace(
        go.Bar(x=top["score_direction"], y=top["name"], orientation="h", name="方向一致性", marker_color="#fdae61")
    )
    bar.update_layout(
        title="纯度 Top 30 板块（按综合分）",
        barmode="group",
        template="plotly_white",
        height=820,
        legend={"orientation": "h"},
    )

    scatter_html = scatter.to_html(full_html=False, include_plotlyjs=False)
    bar_html = bar.to_html(full_html=False, include_plotlyjs=False)
    table_html = _df_to_sortable_table(df)
    plotlyjs = get_plotlyjs()

    label = meta.get("type_label", "概念")
    summary = (
        f"分析窗口 <b>{meta['start']} ~ {meta['end']}</b>（{meta['n_dates']} 个交易日）｜"
        f"{label}板块 <b>{meta['n_concepts']}</b> 个，成功打分 <b>{len(df)}</b> 个｜"
        f"成分股并集 <b>{meta['universe']}</b> 只｜生成时间 {meta['generated_at']}"
    )

    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>同花顺{label}板块成分股纯度分析</title>
<script>{plotlyjs}</script>
<style>
  body {{ font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
          margin: 0 auto; max-width: 1180px; padding: 24px; color: #1f2329; }}
  h1 {{ font-size: 24px; }}
  .summary {{ background:#f2f6fc; border-left:4px solid #2c7fb8; padding:12px 16px;
              border-radius:6px; margin:16px 0; line-height:1.8; }}
  .note {{ color:#646a73; font-size:13px; line-height:1.8; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 13px; margin-top: 12px; }}
  th, td {{ border: 1px solid #e5e6eb; padding: 6px 10px; text-align: right; }}
  th {{ background:#2c7fb8; color:#fff; cursor:pointer; position:sticky; top:0; user-select:none; }}
  th:hover {{ background:#236299; }}
  td:nth-child(2), td:nth-child(3) {{ text-align:left; }}
  tr:nth-child(even) {{ background:#f7f8fa; }}
  .sec {{ margin-top: 36px; }}
</style></head>
<body>
<h1>📊 同花顺{label}板块 · 成分股纯度分析</h1>
<div class="summary">{summary}</div>
<div class="note">
  <b>score_absorption</b> = 第一主成分解释方差占比 λ₁/Σλ × 100（板块被单一共同因子驱动的程度，越高越纯）；
  <b>score_direction</b> = 齐涨齐跌方向一致率按 0.55 重标定后 × 100；
  <b>score_avg</b> = 两者均值。点击表头可排序。
</div>
<div class="sec">{scatter_html}</div>
<div class="sec">{bar_html}</div>
<div class="sec"><h2>全部板块明细（{len(df)} 个）</h2>{table_html}</div>
<script>
  document.querySelectorAll('th').forEach(function(th, idx) {{
    th.addEventListener('click', function() {{
      var tbody = th.closest('table').querySelector('tbody');
      var rows = Array.from(tbody.querySelectorAll('tr'));
      var asc = th.dataset.asc !== 'true'; th.dataset.asc = asc;
      rows.sort(function(a, b) {{
        var x = a.children[idx].innerText, y = b.children[idx].innerText;
        var nx = parseFloat(x), ny = parseFloat(y);
        if (!isNaN(nx) && !isNaN(ny)) return asc ? nx - ny : ny - nx;
        return asc ? x.localeCompare(y, 'zh') : y.localeCompare(x, 'zh');
      }});
      rows.forEach(function(r) {{ tbody.appendChild(r); }});
    }});
  }});
</script>
</body></html>"""
    out_path.write_text(html, encoding="utf-8")
    logger.info(f"HTML 报告已生成：{out_path}")


def _df_to_sortable_table(df: pd.DataFrame) -> str:
    """把结果 DataFrame 转成带表头的 HTML 表格（中文列名）。"""
    headers = {
        "rank": "排名",
        "ts_code": "板块代码",
        "name": "板块名称",
        "n_members": "成分数",
        "n_valid": "有效成分",
        "n_days": "交易日",
        "score_avg": "综合分",
        "score_absorption": "Absorption分",
        "absorption_ratio": "λ₁/Σλ",
        "score_direction": "一致性分",
        "dir_consistency": "c̄",
        "n_merged": "合并数",
        "aliases": "合并别名",
    }
    use = [c for c in headers if c in df.columns]  # 去重列（n_merged/aliases）按需出现
    show = df[use].rename(columns=headers)
    return show.to_html(index=False, border=0, escape=False)


# ============================================================================
# 入口
# ============================================================================
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="同花顺概念板块成分股纯度分析")
    p.add_argument("--start", default=None, help="起始日期 YYYYMMDD（不填则取最近 --days 个交易日）")
    p.add_argument("--end", default=None, help="结束日期 YYYYMMDD（默认今天）")
    p.add_argument("--days", type=int, default=DEFAULT_DAYS, help=f"回看交易日数量，默认 {DEFAULT_DAYS}")
    p.add_argument(
        "--index-type",
        default="N",
        choices=list(INDEX_TYPE_LABELS),
        help="同花顺指数类型：N=概念(默认) I=行业 R=地域 S=特色 ST=风格 TH=主题 BB=宽基",
    )
    p.add_argument("--limit", type=int, default=None, help="仅处理前 N 个板块（用于快速验证）")
    p.add_argument("--dedup", action="store_true", help="按有效成分集合去重（同花顺行业指数层级冗余时建议开启）")
    p.add_argument("--token", default=None, help="Tushare token（默认读 .env / 环境变量）")
    p.add_argument("--output-dir", default=str(ROOT / "scripts" / "output"), help="输出目录")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    _load_dotenv(ROOT)
    dc = build_client(args.token)

    out_dir = Path(os.path.expanduser(args.output_dir))
    out_dir.mkdir(parents=True, exist_ok=True)

    trade_dates = resolve_trade_dates(dc, args.start, args.end, args.days)
    if len(trade_dates) < MIN_OBS_DAYS:
        logger.error(f"交易日数量 {len(trade_dates)} 少于最小观测天数 {MIN_OBS_DAYS}")
        sys.exit(1)
    logger.info(f"分析窗口：{trade_dates[0]} ~ {trade_dates[-1]}（{len(trade_dates)} 个交易日）")

    type_label = INDEX_TYPE_LABELS.get(args.index_type, args.index_type)
    concepts = fetch_concept_list(dc, args.index_type, args.limit)
    members = fetch_members(dc, concepts["ts_code"].tolist())
    universe = {c for cons in members.values() for c in cons}
    logger.info(f"成分股并集：{len(universe)} 只")

    matrix = fetch_return_matrix(dc, trade_dates, universe)
    if matrix.empty:
        logger.error("收益矩阵为空，终止")
        sys.exit(1)
    logger.info(f"收益矩阵形状：{matrix.shape}")

    result = analyze(dc, concepts, members, matrix, dedup=args.dedup)
    if result.empty:
        logger.error("无板块满足打分条件，终止")
        sys.exit(1)

    stamp = f"{args.index_type}_{trade_dates[0]}_{trade_dates[-1]}" + ("_dedup" if args.dedup else "")
    csv_path = out_dir / f"sector_purity_{stamp}.csv"
    html_path = out_dir / f"sector_purity_{stamp}.html"
    result.to_csv(csv_path, index=False, encoding="utf-8-sig")
    logger.info(f"明细 CSV 已保存：{csv_path}")

    meta = {
        "start": trade_dates[0],
        "end": trade_dates[-1],
        "n_dates": len(trade_dates),
        "n_concepts": len(concepts),
        "universe": len(universe),
        "index_type": args.index_type,
        "type_label": type_label,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    build_html_report(result, meta, html_path)

    print("\n=== 纯度 Top 15 板块 ===")
    print(result.head(15).to_string(index=False))
    print(f"\nCSV : {csv_path}\nHTML: {html_path}")
    (out_dir / f"sector_purity_{stamp}_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
