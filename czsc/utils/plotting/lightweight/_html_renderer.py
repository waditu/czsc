"""离线 HTML 渲染：Quant Almanac · 量化年鉴 设计模板。

设计取向：编辑式财经研报 + 终端美学融合。warm paper 配色 + IBM Plex Sans/Mono。

功能：
- 三子图（K + SMA + FX + BI / Volume / MACD）通过 ``subscribeCrosshairMove`` 实现
  跨图十字光标联动，post-init 强制右价格轴等宽 → 竖线严格对齐
- 浮动 tooltip 同时显示 OHLC + Volume + DIFF / DEA / MACD
- header 右上角 light / dark 主题切换按钮
- pane meta 中的图例条目可点击 → toggle 对应 series 可见性
- 多周期通过顶部 tab 切换
"""

from __future__ import annotations

import json
from string import Template

from . import _theme
from ._data import ChartPayload

__all__ = ["render"]


# 占位符统一用 ${name}；CSS / JS 中需要原样保留的 $ 写成 $$。
_PAGE_TPL = Template(
    """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <title>${title}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet"/>
  <script src="${lwc_script}"></script>
  <style>
    :root[data-theme="light"] {
      --bg: ${l_bg}; --text: ${l_text}; --hairline: ${l_grid};
      --accent: ${l_bi}; --up: ${l_up}; --down: ${l_down};
      --sma5: ${l_sma5}; --sma20: ${l_sma20}; --fx: ${l_fx_dashed};
      --paper-tint: color-mix(in srgb, ${l_bg} 92%, ${l_text} 8%);
      --muted: color-mix(in srgb, ${l_text} 55%, transparent);
    }
    :root[data-theme="dark"] {
      --bg: ${d_bg}; --text: ${d_text}; --hairline: ${d_grid};
      --accent: ${d_bi}; --up: ${d_up}; --down: ${d_down};
      --sma5: ${d_sma5}; --sma20: ${d_sma20}; --fx: ${d_fx_dashed};
      --paper-tint: color-mix(in srgb, ${d_bg} 92%, ${d_text} 8%);
      --muted: color-mix(in srgb, ${d_text} 55%, transparent);
    }
    * { box-sizing: border-box; }
    html, body { margin: 0; padding: 0; background: var(--bg); color: var(--text);
                 font-family: 'IBM Plex Sans', 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif;
                 transition: background 0.32s ease, color 0.32s ease;
                 font-feature-settings: 'cv05', 'cv11', 'ss01'; -webkit-font-smoothing: antialiased;
                 letter-spacing: 0.005em; }
    .mono { font-family: 'IBM Plex Mono', 'JetBrains Mono', 'SF Mono', Menlo, monospace; font-feature-settings: 'tnum' 1; }

    /* —— 页头 —————————————————————————————————————————————— */
    .masthead {
      display: grid; grid-template-columns: auto 1fr auto; align-items: end; gap: 24px;
      padding: 28px 40px 20px; border-bottom: 1px solid var(--hairline);
      background: linear-gradient(180deg, var(--paper-tint) 0%, var(--bg) 100%);
    }
    .masthead__brand { display: flex; flex-direction: column; gap: 4px; }
    .masthead__eyebrow {
      font-size: 10px; letter-spacing: 0.22em; text-transform: uppercase; color: var(--muted); font-weight: 500;
    }
    .masthead__symbol {
      font-family: 'IBM Plex Mono', 'SF Mono', monospace; font-weight: 600;
      font-size: 36px; line-height: 1; letter-spacing: -0.01em;
    }
    .masthead__title { font-size: 13px; color: var(--muted); line-height: 1.55; max-width: 56ch; padding-bottom: 4px; }
    .masthead__right {
      display: flex; align-items: center; gap: 14px; padding-bottom: 4px;
    }
    .masthead__status {
      display: flex; align-items: center; gap: 8px;
      font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: var(--muted);
      letter-spacing: 0.08em; text-transform: uppercase;
    }
    .masthead__pulse {
      width: 6px; height: 6px; border-radius: 50%; background: var(--up);
      box-shadow: 0 0 0 0 var(--up); animation: pulse 2.4s cubic-bezier(0.4,0,0.6,1) infinite;
    }
    @keyframes pulse { 0% { box-shadow: 0 0 0 0 color-mix(in srgb, var(--up) 70%, transparent); }
                       70% { box-shadow: 0 0 0 8px transparent; }
                       100% { box-shadow: 0 0 0 0 transparent; } }
    .theme-toggle {
      appearance: none; -webkit-appearance: none; cursor: pointer;
      background: transparent; color: var(--muted);
      border: 1px solid var(--hairline); border-radius: 999px;
      padding: 6px 12px; font-family: 'IBM Plex Mono', monospace; font-size: 10px;
      letter-spacing: 0.16em; text-transform: uppercase;
      display: inline-flex; align-items: center; gap: 6px;
      transition: color 0.2s ease, border-color 0.2s ease, background 0.2s ease;
    }
    .theme-toggle:hover { color: var(--text); border-color: var(--accent); }
    .theme-toggle__icon {
      width: 10px; height: 10px; border-radius: 50%;
      background: radial-gradient(circle at 30% 30%, var(--text) 0%, var(--text) 48%, transparent 50%);
    }

    /* —— Tab 栏 ————————————————————————————————————————— */
    .tabs { display: flex; gap: 0; padding: 0 40px; border-bottom: 1px solid var(--hairline);
            background: var(--bg); position: relative; }
    .tab {
      appearance: none; -webkit-appearance: none; background: transparent; border: 0;
      padding: 14px 20px; cursor: pointer; color: var(--muted);
      font-family: 'IBM Plex Mono', monospace; font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase;
      position: relative; transition: color 0.2s ease;
    }
    .tab::after {
      content: ''; position: absolute; left: 50%; right: 50%; bottom: -1px; height: 2px;
      background: var(--accent); transition: left 0.28s ease, right 0.28s ease, opacity 0.2s; opacity: 0;
    }
    .tab:hover { color: var(--text); }
    .tab.active { color: var(--text); font-weight: 600; }
    .tab.active::after { left: 16px; right: 16px; opacity: 1; }
    .tab__dot { display: inline-block; width: 4px; height: 4px; border-radius: 50%;
                background: currentColor; margin-right: 8px; opacity: 0.4; vertical-align: middle; }
    .tab.active .tab__dot { background: var(--accent); opacity: 1; }

    /* —— 面板 —————————————————————————————————————————————— */
    .freq-pane { padding: 16px 40px 32px; animation: fadein 0.32s ease-out both; }
    .freq-pane[hidden] { display: none; }
    @keyframes fadein { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
    .pane-meta {
      display: flex; align-items: center; gap: 14px; padding: 6px 0 12px;
      font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.06em;
      color: var(--muted); text-transform: uppercase; flex-wrap: wrap;
    }
    .pane-meta__divider { width: 1px; height: 10px; background: var(--hairline); }
    .pane-meta__legend {
      display: inline-flex; align-items: center; gap: 6px; cursor: pointer;
      padding: 4px 8px; border-radius: 3px; user-select: none;
      transition: background 0.18s ease, color 0.18s ease, opacity 0.18s ease;
    }
    .pane-meta__legend:hover { background: color-mix(in srgb, var(--text) 6%, transparent); color: var(--text); }
    .pane-meta__legend.legend--off { opacity: 0.35; text-decoration: line-through; }
    .pane-meta__legend.legend--hover {
      background: color-mix(in srgb, var(--text) 12%, transparent);
      color: var(--text); font-weight: 500;
    }
    .pane-meta__swatch { width: 14px; height: 2px; flex-shrink: 0; }
    .pane-meta__chip-vlegend {
      color: var(--muted); font-size: 9px; opacity: 0.7; letter-spacing: 0.04em;
    }
    .pane-meta__swatch--bi { background: var(--accent); height: 2px; }
    .pane-meta__swatch--fx {
      background: linear-gradient(90deg, var(--fx) 0 4px, transparent 4px 8px, var(--fx) 8px 12px);
    }
    .pane-meta__swatch--sma5  { background: var(--sma5); }
    .pane-meta__swatch--sma20 { background: var(--sma20); }
    .pane-meta__hint { color: var(--muted); font-size: 10px; opacity: 0.6; margin-left: auto; }

    /* —— 图表容器 ———————————————————————————————————————— */
    .chart-stack { position: relative; }
    .row { width: 100%; position: relative; }
    .row-main { height: ${h_main}px; }
    .row-vol  { height: ${h_vol}px; }
    .row-macd { height: ${h_macd}px; }
    .row-sig  { height: ${h_signal}px; }
    .row-sig[hidden] { display: none; }
    .row + .row { margin-top: 2px; }
    .row__label {
      position: absolute; left: 12px; top: 10px; z-index: 2;
      font-family: 'IBM Plex Mono', monospace; font-size: 10px; letter-spacing: 0.15em;
      color: var(--muted); text-transform: uppercase; pointer-events: none;
      padding: 2px 6px; background: color-mix(in srgb, var(--bg) 80%, transparent); border-radius: 2px;
    }
    .row__rowlabels {
      position: absolute; left: 12px; top: 26px; bottom: 4px; z-index: 2;
      display: flex; flex-direction: column; justify-content: space-evenly;
      pointer-events: none;
    }
    .row__rowlabel {
      font-family: 'IBM Plex Mono', 'SF Mono', Menlo, monospace; font-size: 10px;
      color: var(--muted); letter-spacing: 0.04em; white-space: nowrap;
      background: color-mix(in srgb, var(--bg) 90%, transparent);
      padding: 1px 4px; border-radius: 2px;
    }

    /* —— K 线 Tooltip ———————————————————————————————————— */
    .tooltip {
      position: absolute; z-index: 30; min-width: 200px;
      padding: 10px 14px; pointer-events: none; opacity: 0;
      background: color-mix(in srgb, var(--bg) 96%, var(--text) 4%);
      border: 1px solid var(--hairline); border-radius: 4px;
      box-shadow: 0 8px 24px -8px color-mix(in srgb, var(--text) 12%, transparent),
                  0 1px 0 0 color-mix(in srgb, var(--text) 6%, transparent);
      transition: opacity 0.12s ease;
      font-family: 'IBM Plex Mono', monospace; font-size: 11px;
      backdrop-filter: blur(8px);
    }
    .tooltip.visible { opacity: 1; }
    .tooltip__time {
      font-size: 10px; color: var(--muted); letter-spacing: 0.06em;
      text-transform: uppercase; border-bottom: 1px solid var(--hairline);
      padding-bottom: 6px; margin-bottom: 8px;
    }
    .tooltip__section {
      font-size: 9px; color: var(--muted); letter-spacing: 0.12em;
      text-transform: uppercase; margin-top: 8px; padding-top: 6px;
      border-top: 1px solid color-mix(in srgb, var(--hairline) 60%, transparent);
    }
    .tooltip__grid { display: grid; grid-template-columns: auto 1fr; row-gap: 4px; column-gap: 16px; }
    .tooltip__label { color: var(--muted); font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase; }
    .tooltip__value { text-align: right; font-variant-numeric: tabular-nums; }
    .tooltip__value--up   { color: var(--up); }
    .tooltip__value--down { color: var(--down); }

    /* —— 错误 / 页脚 ————————————————————————————————————— */
    .lwc-error { padding: 24px 40px; color: var(--down); font-family: 'IBM Plex Mono', monospace; white-space: pre-wrap; }
    .footer {
      padding: 20px 40px 32px; border-top: 1px solid var(--hairline);
      display: flex; justify-content: space-between; align-items: center;
      font-family: 'IBM Plex Mono', monospace; font-size: 10px; letter-spacing: 0.12em;
      color: var(--muted); text-transform: uppercase;
    }
    .footer__crest { font-weight: 600; letter-spacing: 0.25em; }
  </style>
</head>
<body>
  <header class="masthead">
    <div class="masthead__brand">
      <div class="masthead__eyebrow">缠论 · Quant Almanac</div>
      <div class="masthead__symbol mono">${symbol}</div>
    </div>
    <div class="masthead__title">${title}</div>
    <div class="masthead__right">
      <div class="masthead__status">
        <span class="masthead__pulse"></span>
        <span>LWC · LIVE</span>
      </div>
      <button id="theme-toggle" class="theme-toggle" type="button" aria-label="切换主题">
        <span class="theme-toggle__icon"></span>
        <span id="theme-toggle-label">LIGHT</span>
      </button>
    </div>
  </header>
  <nav id="tabs" class="tabs"></nav>
  <main id="root"></main>
  <footer class="footer">
    <div>czsc · lightweight_charts renderer</div>
    <div class="footer__crest">缠 · ALMANAC</div>
  </footer>

  <script>
  (function () {
    function fail(msg) {
      var root = document.getElementById("root");
      var box = document.createElement("div");
      box.className = "lwc-error";
      box.textContent = msg;
      root.appendChild(box);
    }
    if (typeof LightweightCharts === "undefined") {
      fail("lightweight-charts JS 未加载。请检查网络或换 inline 模式。");
      return;
    }

    var PAYLOAD = __PAYLOAD_JSON__;
    var THEMES = PAYLOAD.themes;            // { light: {...}, dark: {...} }
    var currentThemeName = PAYLOAD.theme_name || 'light';
    var currentTheme = THEMES[currentThemeName];

    var tabsBar = document.getElementById("tabs");
    var root = document.getElementById("root");
    var groups = [];     // 每周期一个 { trio, els, paneEl, tipEl, series, raw, candleByTime, macdByTime }
    var crosshairTime = null;  // 最近一次 hover 的 unix 秒；用于跨 tab 联动
    var dashedLineStyle = LightweightCharts && LightweightCharts.LineStyle
      ? LightweightCharts.LineStyle.Dashed : 2;
    var MIN_AXIS_W = 64;

    function applySize(chart, container) {
      var w = container.clientWidth || (container.parentElement && container.parentElement.clientWidth) || 800;
      var h = container.clientHeight || 200;
      chart.applyOptions({ width: w, height: h });
    }

    function commonOpts(opts, theme) {
      return Object.assign({
        layout: {
          background: { type: "solid", color: theme.background },
          textColor: theme.text,
          fontFamily: "'IBM Plex Mono', 'SF Mono', monospace",
          fontSize: 11,
        },
        grid: {
          vertLines: { color: theme.grid, style: 1 },
          horzLines: { color: theme.grid, style: 1 },
        },
        rightPriceScale: {
          borderColor: theme.grid,
          minimumWidth: MIN_AXIS_W,
          scaleMargins: { top: 0.08, bottom: 0.08 },
          entireTextOnly: true,
        },
        leftPriceScale: { visible: false },
        timeScale: {
          borderColor: theme.grid, timeVisible: true, secondsVisible: false,
          rightOffset: 6, fixLeftEdge: false, lockVisibleTimeRangeOnResize: true,
        },
        crosshair: {
          mode: 1,
          vertLine: { color: theme.text, width: 1, style: 2, labelBackgroundColor: theme.text },
          horzLine: { color: theme.text, width: 1, style: 2, labelBackgroundColor: theme.text },
        },
        autoSize: false,
      }, opts || {});
    }

    function fmt(v)   { return (v == null) ? '—' : Number(v).toFixed(2); }
    function sgn(v)   { return v > 0 ? '+' : (v < 0 ? '−' : ''); }
    function clsOf(v) { return v > 0 ? 'up' : (v < 0 ? 'down' : ''); }
    function fmtVol(v) {
      if (v == null) return '—';
      if (v >= 1e8) return (v/1e8).toFixed(2) + 'B';
      if (v >= 1e6) return (v/1e6).toFixed(2) + 'M';
      if (v >= 1e3) return (v/1e3).toFixed(2) + 'K';
      return String(Math.round(v));
    }

    function tooltipHTML(c, prev, macd, signals) {
      var change = prev ? (c.close - prev.close) : 0;
      var pct = prev && prev.close ? (change / prev.close * 100) : 0;
      var ccls = clsOf(change);
      var dt = new Date(c.time * 1000);
      var pad = function (n) { return n < 10 ? '0' + n : '' + n; };
      var timeStr = dt.getFullYear() + '-' + pad(dt.getMonth() + 1) + '-' + pad(dt.getDate())
                  + ' ' + pad(dt.getHours()) + ':' + pad(dt.getMinutes());
      var macdCls = (macd && macd.macd != null) ? clsOf(macd.macd) : '';
      var diffCls = (macd && macd.diff != null) ? clsOf(macd.diff) : '';
      var html = ''
        + '<div class="tooltip__time">' + timeStr + '</div>'
        + '<div class="tooltip__grid">'
        + '<span class="tooltip__label">Open</span>'
        + '<span class="tooltip__value">' + fmt(c.open) + '</span>'
        + '<span class="tooltip__label">High</span>'
        + '<span class="tooltip__value">' + fmt(c.high) + '</span>'
        + '<span class="tooltip__label">Low</span>'
        + '<span class="tooltip__value">' + fmt(c.low) + '</span>'
        + '<span class="tooltip__label">Close</span>'
        + '<span class="tooltip__value tooltip__value--' + ccls + '">' + fmt(c.close) + '</span>'
        + '<span class="tooltip__label">Chg %</span>'
        + '<span class="tooltip__value tooltip__value--' + ccls + '">' + sgn(change) + Math.abs(pct).toFixed(2) + '%</span>'
        + (c.volume != null
            ? '<span class="tooltip__label">Vol</span><span class="tooltip__value">' + fmtVol(c.volume) + '</span>'
            : '')
        + '</div>'
        + (macd ?
            '<div class="tooltip__section">MACD · 12/26/9</div>'
            + '<div class="tooltip__grid">'
            + '<span class="tooltip__label">DIFF</span>'
            + '<span class="tooltip__value tooltip__value--' + diffCls + '">' + fmt(macd.diff) + '</span>'
            + '<span class="tooltip__label">DEA</span>'
            + '<span class="tooltip__value">' + fmt(macd.dea) + '</span>'
            + '<span class="tooltip__label">MACD</span>'
            + '<span class="tooltip__value tooltip__value--' + macdCls + '">' + fmt(macd.macd) + '</span>'
            + '</div>'
            : '');
      if (signals && signals.length) {
        html += '<div class="tooltip__section">SIGNALS · @CURRENT BAR</div>'
              + '<div class="tooltip__grid">';
        signals.forEach(function (s) {
          var labelColor = 'var(--muted)';  // key 用淡色，让 value 突出
          var dirCls = (s.direction === 'up') ? 'tooltip__value--up'
                     : (s.direction === 'down') ? 'tooltip__value--down' : '';
          html +=
            '<span class="tooltip__label" style="color:' + labelColor + '">' + s.key + '</span>'
            + '<span class="tooltip__value ' + dirCls + '">' + s.value + '</span>';
        });
        html += '</div>';
      }
      return html;
    }

    function placeTooltip(tooltipEl, mainEl, x, y) {
      var paneRect = mainEl.getBoundingClientRect();
      var contRect = mainEl.parentElement.getBoundingClientRect();
      var w = tooltipEl.offsetWidth || 220, h = tooltipEl.offsetHeight || 200;
      var pad = 16;
      var px = x + 18;
      var py = y + 18;
      if (px + w > paneRect.width - pad) px = x - w - 18;
      if (py + h > paneRect.height - pad) py = y - h - 18;
      tooltipEl.style.left = (paneRect.left - contRect.left + Math.max(8, px)) + 'px';
      tooltipEl.style.top  = (paneRect.top  - contRect.top  + Math.max(8, py)) + 'px';
    }

    function colorizeVol(rawCandles, rawVol, theme) {
      // rawVol[i] 与 rawCandles[i] 严格对齐
      return rawVol.map(function (b, i) {
        var c = rawCandles[i];
        var up = c && (Number(c.close) >= Number(c.open));
        return { time: b.time, value: b.value, color: up ? theme.up : theme.down };
      });
    }
    function colorizeMacd(rawMacd, theme) {
      return rawMacd.map(function (b) {
        var v = (b.value == null) ? 0 : Number(b.value);
        return { time: b.time, value: b.value, color: v >= 0 ? theme.up : theme.down };
      });
    }

    function buildFreqPane(freq, fi, theme) {
      var pane = document.createElement("section");
      pane.className = "freq-pane chart-stack";
      pane.setAttribute("data-idx", String(fi));

      var legendMain = (
        '<span class="pane-meta__legend" data-series="sma5">'
          + '<span class="pane-meta__swatch pane-meta__swatch--sma5"></span>SMA5</span>'
        + '<span class="pane-meta__legend" data-series="sma20">'
          + '<span class="pane-meta__swatch pane-meta__swatch--sma20"></span>SMA20</span>'
        + '<span class="pane-meta__legend" data-series="fx">'
          + '<span class="pane-meta__swatch pane-meta__swatch--fx"></span>FX (DASHED)</span>'
        + '<span class="pane-meta__legend" data-series="bi">'
          + '<span class="pane-meta__swatch pane-meta__swatch--bi"></span>BI (SOLID)</span>'
      );
      pane.innerHTML =
        '<div class="pane-meta">'
        + '<span>' + freq.freq_label + ' · ' + freq.main.candles.length + ' BARS</span>'
        + '<span class="pane-meta__divider"></span>'
        + legendMain
        + '<span class="pane-meta__hint">CLICK LEGEND TO TOGGLE</span>'
        + '</div>'
        + '<div class="chart-stack">'
        +   '<div class="row row-main" id="main-' + fi + '"><div class="row__label">PRICE · K + SMA + FX + BI</div></div>'
        +   '<div class="row row-vol"  id="vol-'  + fi + '"><div class="row__label">VOLUME</div></div>'
        +   '<div class="row row-sig"  id="sig-'  + fi + '"><div class="row__label">SIGNAL TIMELINE</div><div class="row__rowlabels" id="siglabels-' + fi + '"></div></div>'
        +   '<div class="row row-macd" id="macd-' + fi + '"><div class="row__label">MACD · 12/26/9</div></div>'
        +   '<div class="tooltip mono" id="tip-' + fi + '"></div>'
        + '</div>';
      root.appendChild(pane);

      var mainEl = pane.querySelector('#main-' + fi);
      var volEl  = pane.querySelector('#vol-'  + fi);
      var macdEl = pane.querySelector('#macd-' + fi);
      var tipEl  = pane.querySelector('#tip-'  + fi);

      // 主图（隐藏 time 轴，最底 MACD 才显示）
      var cMain = LightweightCharts.createChart(mainEl, commonOpts({
        timeScale: { borderColor: theme.grid, timeVisible: true, secondsVisible: false, rightOffset: 6, visible: false },
      }, theme));
      applySize(cMain, mainEl);
      var ks = cMain.addCandlestickSeries({
        upColor: theme.up, downColor: theme.down,
        borderUpColor: theme.up, borderDownColor: theme.down,
        wickUpColor: theme.up, wickDownColor: theme.down,
      });
      ks.setData(freq.main.candles);

      var smaCommon = { lineWidth: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false };
      var sma5 = (freq.main.sma5 && freq.main.sma5.length)
        ? cMain.addLineSeries(Object.assign({ color: theme.sma5 }, smaCommon)) : null;
      if (sma5) sma5.setData(freq.main.sma5);
      var sma20 = (freq.main.sma20 && freq.main.sma20.length)
        ? cMain.addLineSeries(Object.assign({ color: theme.sma20 }, smaCommon)) : null;
      if (sma20) sma20.setData(freq.main.sma20);
      var fx = (freq.main.fx_line && freq.main.fx_line.length)
        ? cMain.addLineSeries(Object.assign({ color: theme.fx_dashed, lineStyle: dashedLineStyle }, smaCommon)) : null;
      if (fx) fx.setData(freq.main.fx_line);
      var bi = (freq.main.bi_line && freq.main.bi_line.length)
        ? cMain.addLineSeries(Object.assign({ color: theme.bi, lineWidth: 2 }, { priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false })) : null;
      if (bi) bi.setData(freq.main.bi_line);

      // —— Signal markers（每个 key 一个 SignalSeries，合并到 candle series 上）——
      var signalSeries = freq.signals || [];
      var signalMarkersAll = [];      // 当前可见的 markers 数组
      var signalsByTime = {};         // tooltip 用：time → [{ key, v1, value, color, direction }, ...]
      var seriesVisibleMap = {};      // key → bool
      signalSeries.forEach(function (s) {
        seriesVisibleMap[s.key] = true;
        s.markers.forEach(function (m) {
          // marker.direction 决定 position；marker.color 已是直接的红/绿/灰
          var pos = (m.direction === 'down') ? 'belowBar' : 'aboveBar';
          var entry = {
            time: m.time,
            position: pos,
            color: m.color,
            shape: s.shape || 'circle',
            text: m.vnum != null ? String(m.vnum) : '',
          };
          entry.__key = s.key;
          entry.__value = m.value;
          entry.__direction = m.direction;
          signalMarkersAll.push(entry);
          if (!signalsByTime[m.time]) signalsByTime[m.time] = [];
          signalsByTime[m.time].push({
            key: s.key, v1: m.v1, value: m.value, color: m.color, direction: m.direction,
          });
        });
      });
      var highlightedKey = null;

      function hexToRgba(hex, alpha) {
        // hex format #RRGGBB
        var r = parseInt(hex.slice(1, 3), 16);
        var g = parseInt(hex.slice(3, 5), 16);
        var b = parseInt(hex.slice(5, 7), 16);
        return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
      }

      function applySignalMarkers() {
        var visible = signalMarkersAll
          .filter(function (m) { return seriesVisibleMap[m.__key]; })
          .sort(function (a, b) { return a.time - b.time; })
          .map(function (m) {
            var isHi = (highlightedKey !== null && m.__key === highlightedKey);
            var isDim = (highlightedKey !== null && m.__key !== highlightedKey);
            return {
              time: m.time,
              position: m.position,
              color: isDim ? hexToRgba(m.color, 0.25) : m.color,
              shape: m.shape,
              text: m.text,
              size: isHi ? 2 : 1,
            };
          });
        ks.setMarkers(visible);
      }
      applySignalMarkers();

      // VOL
      var cVol = LightweightCharts.createChart(volEl, commonOpts({
        timeScale: { borderColor: theme.grid, timeVisible: true, secondsVisible: false, rightOffset: 6, visible: false },
      }, theme));
      applySize(cVol, volEl);
      var volSeries = cVol.addHistogramSeries({ priceFormat: { type: "volume" }, priceScaleId: "right" });
      volSeries.setData(colorizeVol(freq.main.candles, freq.volume.bars, theme));

      // MACD
      var cMacd = LightweightCharts.createChart(macdEl, commonOpts({
        timeScale: { borderColor: theme.grid, timeVisible: true, secondsVisible: false, rightOffset: 6, visible: true },
      }, theme));
      applySize(cMacd, macdEl);
      var diffSeries = cMacd.addLineSeries(Object.assign({ color: theme.macd_diff }, smaCommon));
      diffSeries.setData(freq.macd.diff);
      var deaSeries = cMacd.addLineSeries(Object.assign({ color: theme.macd_dea }, smaCommon));
      deaSeries.setData(freq.macd.dea);
      var macdHist = cMacd.addHistogramSeries({ priceScaleId: "right" });
      macdHist.setData(colorizeMacd(freq.macd.macd, theme));
      // 0 基准线（保留引用以便主题切换重建）
      var zeroLineRef = diffSeries.createPriceLine({
        price: 0, color: theme.text, lineWidth: 1, lineStyle: dashedLineStyle, axisLabelVisible: true, title: '0',
      });

      // —— SIGNAL TIMELINE pane ——
      var sigEl = pane.querySelector('#sig-' + fi);
      var sigLabelsEl = pane.querySelector('#siglabels-' + fi);
      var cSig = LightweightCharts.createChart(sigEl, commonOpts({
        timeScale: { borderColor: theme.grid, timeVisible: true, secondsVisible: false, rightOffset: 6, visible: false },
        rightPriceScale: { visible: false },
        leftPriceScale: { visible: false },
        crosshair: { mode: 1 },
        grid: { vertLines: { color: theme.grid, style: 1 }, horzLines: { visible: false } },
      }, theme));
      applySize(cSig, sigEl);

      // 每行一个 Line series（用作时间锚 + marker 承载）
      var sigRowSeriesByKey = {};
      var sigRowMarkersAllByKey = {};   // key → markers 数组（独立于主图）
      if (signalSeries.length > 0) {
        var firstT = (freq.main.candles[0] || {}).time || 0;
        var lastT  = (freq.main.candles[freq.main.candles.length - 1] || {}).time || (firstT + 1);
        // 行号倒序，让第 0 行画在最上
        signalSeries.forEach(function (s, ri) {
          var rowY = signalSeries.length - ri;  // 顶部 > 1，底部 1
          var line = cSig.addLineSeries({
            color: 'transparent',
            lineVisible: false,
            priceLineVisible: false,
            lastValueVisible: false,
            crosshairMarkerVisible: false,
          });
          line.setData([{ time: firstT, value: rowY }, { time: lastT, value: rowY }]);
          sigRowSeriesByKey[s.key] = line;
          line._signalShape = s.shape || 'circle';
          // 该行 markers：固定 position='aboveBar'（line series 本体不可见，仅显示 marker）
          var rowMarkers = s.markers.map(function (m) {
            return {
              time: m.time,
              position: 'aboveBar',
              color: m.color,
              shape: s.shape || 'circle',
              text: m.vnum != null ? String(m.vnum) : '',
            };
          });
          sigRowMarkersAllByKey[s.key] = rowMarkers;
          // HTML 行标签
          var lab = document.createElement('span');
          lab.className = 'row__rowlabel';
          lab.textContent = s.key;
          sigLabelsEl.appendChild(lab);
        });
        cSig.timeScale().fitContent();
      } else {
        // 没 signal → 隐藏整行
        sigEl.hidden = true;
      }

      function applyRowMarkers() {
        Object.keys(sigRowSeriesByKey).forEach(function (key) {
          var rowSer = sigRowSeriesByKey[key];
          if (!seriesVisibleMap[key]) {
            rowSer.setMarkers([]);
            return;
          }
          var origMarkers = sigRowMarkersAllByKey[key] || [];
          var mapped = origMarkers.map(function (m) {
            var isHi = (highlightedKey !== null && key === highlightedKey);
            var isDim = (highlightedKey !== null && key !== highlightedKey);
            return {
              time: m.time,
              position: 'aboveBar',
              color: isDim ? hexToRgba(m.color, 0.25) : m.color,
              shape: rowSer._signalShape || 'circle',
              text: m.text != null ? m.text : '',
              size: isHi ? 2 : 1,
            };
          });
          rowSer.setMarkers(mapped);
        });
      }
      applyRowMarkers();

      // —— 跨子图 时间轴 & 十字光标 联动 ——
      var trio = [cMain, cVol, cMacd];
      var trioEls = [mainEl, volEl, macdEl];
      var primarySeries = [ks, volSeries, diffSeries];
      if (signalSeries.length > 0) {
        trio.push(cSig);
        trioEls.push(sigEl);
        // 用第一个行的 line series 作为 crosshair anchor
        var firstRowKey = Object.keys(sigRowSeriesByKey)[0];
        primarySeries.push(sigRowSeriesByKey[firstRowKey]);
      }
      var lockTime = false, lockCh = false;
      trio.forEach(function (src, i) {
        src.timeScale().subscribeVisibleLogicalRangeChange(function (r) {
          if (!r || lockTime) return;
          lockTime = true;
          for (var j = 0; j < trio.length; j++) {
            if (j !== i) trio[j].timeScale().setVisibleLogicalRange(r);
          }
          lockTime = false;
        });
      });

      // 建索引（tooltip 用）
      var candleByTime = {}, macdByTime = {};
      var orderedCandles = freq.main.candles;
      var volByTime = {};
      freq.volume.bars.forEach(function (h) { volByTime[h.time] = h.value; });
      for (var i = 0; i < orderedCandles.length; i++) {
        var c = orderedCandles[i];
        candleByTime[c.time] = { idx: i, ohlc: c, volume: volByTime[c.time] };
      }
      freq.macd.diff.forEach(function (d, idx) {
        macdByTime[d.time] = {
          diff: d.value,
          dea: freq.macd.dea[idx] && freq.macd.dea[idx].value,
          macd: freq.macd.macd[idx] && freq.macd.macd[idx].value,
        };
      });

      trio.forEach(function (src, i) {
        src.subscribeCrosshairMove(function (param) {
          // 记录最后一次 hover 的时间，用于跨 tab 联动
          if (param && param.time != null) {
            crosshairTime = param.time;
          }
          if (!lockCh && param && param.time) {
            lockCh = true;
            for (var j = 0; j < trio.length; j++) {
              if (j !== i) {
                try { trio[j].setCrosshairPosition(NaN, param.time, primarySeries[j]); }
                catch (e) { /* ignore boundary errors */ }
              }
            }
            lockCh = false;
          }
          // tooltip 任何子图上的光标移动都更新；位置吸附到主图坐标系
          if (!param || !param.time) { tipEl.classList.remove('visible'); return; }
          var entry = candleByTime[param.time];
          if (!entry) { tipEl.classList.remove('visible'); return; }
          var prev = entry.idx > 0 ? candleByTime[orderedCandles[entry.idx - 1].time] : null;
          var c = Object.assign({}, entry.ohlc, { volume: entry.volume });
          var m = macdByTime[param.time] || null;
          var sigs = signalsByTime[param.time] || [];
          tipEl.innerHTML = tooltipHTML(c, prev ? prev.ohlc : null, m, sigs);
          tipEl.classList.add('visible');
          var px = param.point ? param.point.x : null;
          var py = param.point ? param.point.y : null;
          if (px == null || py == null || i !== 0) {
            // 副图光标 → tooltip 固定在主图右上
            var mainBR = mainEl.getBoundingClientRect();
            placeTooltip(tipEl, mainEl, mainBR.width - 240, 16);
          } else {
            placeTooltip(tipEl, mainEl, px, py);
          }

          // 反向高亮：crosshair param.hoveredSeries 命中 sigRow series 时高亮对应 chip
          var hovered = null;
          if (param && param.hoveredSeries) {
            Object.keys(sigRowSeriesByKey).forEach(function (k) {
              if (sigRowSeriesByKey[k] === param.hoveredSeries) hovered = k;
            });
          }
          // 仅在状态变化时更新（避免反复刷新 markers）
          if (hovered !== highlightedKey) {
            highlightedKey = hovered;
            pane.querySelectorAll('.pane-meta__legend[data-signal-key]').forEach(function (el) {
              el.classList.toggle('legend--hover', el.getAttribute('data-signal-key') === hovered);
            });
            applySignalMarkers();
            applyRowMarkers();
          }
        });
      });

      var seriesRefs = {
        candles: ks, sma5: sma5, sma20: sma20, fx: fx, bi: bi,
        volume: volSeries, macdDiff: diffSeries, macdDea: deaSeries, macdHist: macdHist,
        zeroLine: zeroLineRef, diffForZero: diffSeries,
      };
      var rawRefs = {
        candles: freq.main.candles, volume: freq.volume.bars, macdHist: freq.macd.macd,
      };

      groups.push({
        trio: trio, els: trioEls, paneEl: pane, tipEl: tipEl,
        series: seriesRefs, raw: rawRefs,
      });

      // —— Signal 图例条目（动态注入到 pane-meta 末尾）——
      if (signalSeries.length) {
        var meta = pane.querySelector('.pane-meta');
        var divider = document.createElement('span');
        divider.className = 'pane-meta__divider';
        meta.insertBefore(divider, meta.querySelector('.pane-meta__hint') || null);
        signalSeries.forEach(function (s) {
          var chip = document.createElement('span');
          chip.className = 'pane-meta__legend';
          chip.setAttribute('data-signal-key', s.key);
          // shape icon（用 Unicode 表示 shape）+ key + 数字图例
          var shapeIcon = {
            circle: '●', square: '■', arrowUp: '▲', arrowDown: '▼',
          }[s.shape] || '●';
          // value_index 是 {value: vnum}, 按 vnum 升序得到 "1=v1 2=v2 ..." legend
          var vEntries = Object.keys(s.value_index || {}).sort(function (a, b) {
            return s.value_index[a] - s.value_index[b];
          });
          var vLegend = vEntries.map(function (val) {
            return s.value_index[val] + '=' + val.split('_')[0];
          }).join(' ');
          chip.innerHTML =
            '<span class="pane-meta__swatch" style="color:' + s.color + ';font-size:11px;line-height:1">' + shapeIcon + '</span>'
            + ' ' + s.key
            + (vLegend ? ' <span class="pane-meta__chip-vlegend">· ' + vLegend + '</span>' : '');
          chip.addEventListener('click', function () {
            seriesVisibleMap[s.key] = !seriesVisibleMap[s.key];
            chip.classList.toggle('legend--off', !seriesVisibleMap[s.key]);
            applySignalMarkers();
            applyRowMarkers();
          });
          chip.addEventListener('mouseenter', function () {
            highlightedKey = s.key;
            chip.classList.add('legend--hover');
            applySignalMarkers();
            applyRowMarkers();
          });
          chip.addEventListener('mouseleave', function () {
            highlightedKey = null;
            chip.classList.remove('legend--hover');
            applySignalMarkers();
            applyRowMarkers();
          });
          meta.insertBefore(chip, meta.querySelector('.pane-meta__hint') || null);
        });
      }

      // 图例点击 → toggle series 可见
      pane.querySelectorAll('.pane-meta__legend').forEach(function (item) {
        item.addEventListener('click', function () {
          var key = item.getAttribute('data-series');
          var s = seriesRefs[key];
          if (!s) return;
          var off = item.classList.toggle('legend--off');
          s.applyOptions({ visible: !off });
        });
      });
    }

    // —— 三子图右价格轴 后置等宽 → 竖线严格对齐 ——
    function alignAxes() {
      var maxW = MIN_AXIS_W;
      groups.forEach(function (g) {
        g.trio.forEach(function (c) {
          try {
            var w = c.priceScale('right').width();
            if (w > maxW) maxW = w;
          } catch (e) { /* old API fallback */ }
        });
      });
      groups.forEach(function (g) {
        g.trio.forEach(function (c) {
          c.priceScale('right').applyOptions({ minimumWidth: maxW });
        });
      });
    }

    // —— 主题切换 ——
    function applyTheme(name) {
      if (!THEMES[name]) return;
      currentThemeName = name;
      currentTheme = THEMES[name];
      document.documentElement.setAttribute('data-theme', name);
      document.getElementById('theme-toggle-label').textContent = name.toUpperCase();
      groups.forEach(function (g) {
        g.trio.forEach(function (c) {
          c.applyOptions({
            layout: { background: { type: 'solid', color: currentTheme.background }, textColor: currentTheme.text },
            grid:   { vertLines: { color: currentTheme.grid }, horzLines: { color: currentTheme.grid } },
            rightPriceScale: { borderColor: currentTheme.grid },
            timeScale: { borderColor: currentTheme.grid },
            crosshair: {
              vertLine: { color: currentTheme.text, labelBackgroundColor: currentTheme.text },
              horzLine: { color: currentTheme.text, labelBackgroundColor: currentTheme.text },
            },
          });
        });
        g.series.candles.applyOptions({
          upColor: currentTheme.up, downColor: currentTheme.down,
          borderUpColor: currentTheme.up, borderDownColor: currentTheme.down,
          wickUpColor: currentTheme.up, wickDownColor: currentTheme.down,
        });
        if (g.series.sma5)  g.series.sma5.applyOptions({ color: currentTheme.sma5 });
        if (g.series.sma20) g.series.sma20.applyOptions({ color: currentTheme.sma20 });
        if (g.series.fx)    g.series.fx.applyOptions({ color: currentTheme.fx_dashed });
        if (g.series.bi)    g.series.bi.applyOptions({ color: currentTheme.bi });
        g.series.macdDiff.applyOptions({ color: currentTheme.macd_diff });
        g.series.macdDea.applyOptions({ color: currentTheme.macd_dea });
        // 直方图 per-bar 颜色 → 重新染色
        g.series.volume.setData(colorizeVol(g.raw.candles, g.raw.volume, currentTheme));
        g.series.macdHist.setData(colorizeMacd(g.raw.macdHist, currentTheme));
        // 0 基准线：旧的删除 + 重建（lightweight-charts v4 不支持 applyOptions on priceLine）
        try { g.series.diffForZero.removePriceLine(g.series.zeroLine); } catch (e) { /* noop */ }
        g.series.zeroLine = g.series.diffForZero.createPriceLine({
          price: 0, color: currentTheme.text, lineWidth: 1, lineStyle: dashedLineStyle, axisLabelVisible: true, title: '0',
        });
      });
      setTimeout(alignAxes, 0);
    }

    // 初始化：所有 panes 用 currentTheme 构建
    PAYLOAD.panes.forEach(function (f, i) { buildFreqPane(f, i, currentTheme); });

    function resizePane(idx) {
      var g = groups[idx];
      if (!g) return;
      g.trio.forEach(function (chart, i) { applySize(chart, g.els[i]); });
      setTimeout(alignAxes, 0);
    }
    function applyCrosshairToTab(idx) {
      if (crosshairTime == null) return;
      var g = groups[idx];
      if (!g) return;
      var candles = (PAYLOAD.panes[idx].main.candles) || [];
      var nearest = null;
      for (var i = candles.length - 1; i >= 0; i--) {
        if (candles[i].time <= crosshairTime) {
          nearest = candles[i].time;
          break;
        }
      }
      if (nearest == null) return;
      // 三个主图（main / vol / macd）的 primary series
      var primaries = [g.series.candles, g.series.volume, g.series.macdDiff];
      g.trio.forEach(function (chart, ti) {
        if (primaries[ti]) {
          try { chart.setCrosshairPosition(NaN, nearest, primaries[ti]); } catch (e) { /* ignore */ }
        }
      });
    }
    function resizeAll() { for (var i = 0; i < groups.length; i++) resizePane(i); }
    window.addEventListener("resize", resizeAll);

    // Tab 栏
    if (PAYLOAD.panes.length <= 1) {
      tabsBar.style.display = "none";
    } else {
      PAYLOAD.panes.forEach(function (freq, idx) {
        var btn = document.createElement("button");
        btn.className = "tab" + (idx === 0 ? " active" : "");
        btn.setAttribute("data-idx", String(idx));
        btn.innerHTML = '<span class="tab__dot"></span>' + freq.freq_label;
        btn.addEventListener("click", function () {
          for (var i = 0; i < groups.length; i++) {
            var active = (i === idx);
            groups[i].paneEl.hidden = !active;
            tabsBar.children[i].classList.toggle("active", active);
          }
          setTimeout(function () {
            resizePane(idx);
            applyCrosshairToTab(idx);
          }, 0);
        });
        tabsBar.appendChild(btn);
      });
      for (var i = 1; i < groups.length; i++) groups[i].paneEl.hidden = true;
    }

    // 主题 toggle
    document.documentElement.setAttribute('data-theme', currentThemeName);
    document.getElementById('theme-toggle-label').textContent = currentThemeName.toUpperCase();
    document.getElementById('theme-toggle').addEventListener('click', function () {
      applyTheme(currentThemeName === 'light' ? 'dark' : 'light');
    });

    // 首屏对齐
    setTimeout(function () { resizePane(0); alignAxes(); }, 0);
  })();
  </script>
</body>
</html>
"""
)


_CDN_URL = "https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"


def render(
    payload: ChartPayload,
    *,
    lwc_source: str = "cdn",
    height_main: int = 420,
    height_vol: int = 130,
    height_macd: int = 170,
    height_signal: int = 80,
) -> str:
    """渲染整页 HTML 字符串。"""
    lwc_script = _CDN_URL
    if lwc_source not in ("cdn", "inline"):
        raise ValueError(f"lwc_source must be 'cdn' or 'inline', got {lwc_source!r}")

    payload_dict = payload.to_dict()
    # 两套主题都注入，前端可切换
    payload_dict["themes"] = {
        "light": dict(_theme.THEMES["light"]),
        "dark": dict(_theme.THEMES["dark"]),
    }
    # 推断初始主题名（按 payload.theme 反查）
    payload_dict["theme_name"] = (
        "dark" if payload.theme["background"] == _theme.THEMES["dark"]["background"] else "light"
    )

    light = _theme.THEMES["light"]
    dark = _theme.THEMES["dark"]
    page_no_payload = _PAGE_TPL.substitute(
        title=payload.title,
        symbol=payload.symbol,
        # light theme CSS vars
        l_bg=light["background"],
        l_text=light["text"],
        l_grid=light["grid"],
        l_up=light["up"],
        l_down=light["down"],
        l_bi=light["bi"],
        l_sma5=light["sma5"],
        l_sma20=light["sma20"],
        l_fx_dashed=light["fx_dashed"],
        # dark theme CSS vars
        d_bg=dark["background"],
        d_text=dark["text"],
        d_grid=dark["grid"],
        d_up=dark["up"],
        d_down=dark["down"],
        d_bi=dark["bi"],
        d_sma5=dark["sma5"],
        d_sma20=dark["sma20"],
        d_fx_dashed=dark["fx_dashed"],
        lwc_script=lwc_script,
        h_main=height_main,
        h_vol=height_vol,
        h_macd=height_macd,
        h_signal=height_signal,
    )
    payload_json = json.dumps(payload_dict, ensure_ascii=False, allow_nan=False, default=str)
    return page_no_payload.replace("__PAYLOAD_JSON__", payload_json)
