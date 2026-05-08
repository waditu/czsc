"""信号模板参数默认值与渲染工具。

本模块为 parity 测试套件提供"参数模板 -> 具体信号字符串"的转换能力。
``czsc-signals`` 库中每一个 K 线信号都会向注册表登记一个参数模板，
形如 ``{freq}_D{di}N{n}M{m}_..._VyymmDD``。在等价性测试中，我们需要
把每个信号都跑一遍，因此必须把模板里的 ``{placeholder}`` 替换成具体
的、能让 Rust 端 ``assert!`` 校验通过的取值，从而合成一个可消费的
七段式信号字符串。

设计要点：
    * ``DEFAULTS`` 中的取值需要同时满足 Rust 实现里的所有约束断言，
      例如 ``n < m``、``w > 10``、``th in 30..300``、``t1 < t2`` 等，
      否则 all-signals 批量测试在某些信号上会触发 panic。
    * 字典 key 大小写敏感，``n`` 与 ``N`` 都需要登记，因为不同信号
      使用了不同大小写的占位符。
    * ``render`` 在替换之后还会拼接一个标准化的取值后缀
      ``_v1_v2_v3_0``，保证渲染结果是合法的七段式信号字符串。
"""

from __future__ import annotations

# 信号模板占位符 -> 默认替换值。
# 取值经过精挑细选，必须满足 Rust 端所有 assert! 约束。
DEFAULTS: dict[str, str] = {
    "freq": "日线",
    "freq1": "日线",
    # 计数器 / 回看窗口（lookback）
    "di": "1",
    "n": "5",
    "N": "5",
    "m": "20",
    "M": "20",
    "p": "5",
    "q": "5",
    "k": "5",
    "j": "5",
    "l": "5",
    "s": "5",
    "z": "5",
    "t": "5",
    "w": "15",  # >10 才能满足"压力位/支撑位"信号的 assert
    "window": "15",
    "rumi_window": "15",
    # 成对参数（必须满足 a < b 的约束）
    "t1": "5",
    "t2": "20",
    "th1": "5",
    "th2": "20",
    "th3": "30",
    "tha": "5",
    "thb": "50",
    "thc": "500",
    "timeperiod1": "5",
    "timeperiod2": "20",
    "min_count": "3",
    "max_count": "10",
    # 单一阈值（RSI / 动量类信号常用）
    "th": "50",  # 必须落在 30 < th < 300 区间
    "ndev": "2",
    "nbdev": "2",
    "avg_bp": "5",
    "bi_init_length": "20",
    "max_overlap": "3",
    "num": "5",
    "up": "1",
    "dw": "1",
    "zf": "5",
    "tl": "5",
    "key": "close",
    "line": "close",
    # 移动平均与技术指标参数
    "ma_type": "SMA",
    "ma_seq": "5",
    "timeperiod": "20",
    "fastperiod": "5",
    "slowperiod": "20",
    "signalperiod": "9",
    "fastk_period": "5",
    "slowd_period": "9",
    "slowk_period": "9",
    "md": "5",
    "mp": "5",
    "sp": "10",
    "lp": "20",
    # 常量类占位符
    "mode": "CO",
    "K1": "K1",
    "K2": "K2",
    "c1": "K1",
    "c2": "K2",
}


def render(template: str) -> str:
    """将模板中的所有 ``{placeholder}`` 替换为默认值，并补齐取值后缀。

    具体行为：
        1. 把 ``template`` 中的每一个 ``{name}`` 替换为 ``DEFAULTS[name]``，
           对于未登记的占位符回退到字符串 ``"5"``。
        2. 在结果末尾追加 ``_v1_v2_v3_0``，使其成为一个合法的、由七段
           组成的信号字符串。

    参数:
        template: 形如 ``"{freq}_D{di}N{n}M{m}_..._VyymmDD"`` 的参数模板。

    返回:
        渲染后的完整七段式信号字符串。
    """
    import re

    def _sub(m):
        # 取出 {} 中的占位符名称，回退到默认 "5"
        ph = m.group(1)
        return DEFAULTS.get(ph, "5")

    rendered = re.sub(r"\{([^}]+)\}", _sub, template)
    # 追加标准化的取值后缀，组成完整七段式信号
    return f"{rendered}_v1_v2_v3_0"
