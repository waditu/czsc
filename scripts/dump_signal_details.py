"""扫描 crates/czsc-signals/src/*.rs，提取每个 `#[signal(...)]` 的详细信息。

用法:
    uv run --no-sync python scripts/dump_signal_details.py                       # 输出 XML 到 stdout
    uv run --no-sync python scripts/dump_signal_details.py --format json
    uv run --no-sync python scripts/dump_signal_details.py --format xml --output /tmp/signal_details.xml

输出包含字段：
    name / category / template / opcode / file / doc_summary / doc_logic / signal_examples

XML 输出为飞书 docx 兼容片段，按 .rs 文件分组。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIGNALS_DIR = ROOT / "crates" / "czsc-signals" / "src"
SKIP_FILES = {"lib.rs", "registry.rs", "params.rs", "types.rs"}

# 匹配整个 #[signal(...)] 注解（支持跨行；非贪婪匹配最近的右括号）
SIGNAL_ATTR_RE = re.compile(r"#\[signal\s*\((?P<body>.*?)\)\s*\]", re.DOTALL)
# 匹配注解 body 内的 key = "value"
KV_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"')
# 匹配 docstring 中的 Signal('...') 字符串
SIGNAL_EXAMPLE_RE = re.compile(r"Signal\('([^']+)'\)")
# 段标题，doc_logic 截断用
SECTION_HEADERS = (
    "参数模板",
    "信号列表示例",
    "参数说明",
    "对齐说明",
    "示例",
    "注意",
    "说明",
    "返回",
    "依赖",
)


@dataclass
class SignalInfo:
    name: str
    category: str
    template: str
    opcode: str
    file: str
    doc_summary: str = ""
    doc_logic: str = ""
    signal_examples: list[str] = field(default_factory=list)


def extract_doc_lines(text: str, attr_start: int) -> list[str]:
    """从 attr_start 位置向前回溯，连续抓取 /// 注释行。

    返回顺序：与源码顺序一致（从前到后）。
    """
    # 找到 attr_start 所在行的行首
    line_start = text.rfind("\n", 0, attr_start)
    if line_start == -1:
        line_start = 0
    else:
        line_start += 1  # 跳过换行符本身
    # 向前一行一行扫
    doc_lines: list[str] = []
    cursor = line_start
    while cursor > 0:
        prev_newline = text.rfind("\n", 0, cursor - 1)
        prev_line_start = prev_newline + 1 if prev_newline != -1 else 0
        line = text[prev_line_start : cursor - 1] if cursor > 0 else text[prev_line_start:cursor]
        stripped = line.strip()
        if stripped.startswith("///"):
            # 去掉 /// 前缀；保留一个空格之后的内容
            content = stripped[3:]
            if content.startswith(" "):
                content = content[1:]
            doc_lines.append(content)
            cursor = prev_line_start
            if cursor == 0:
                break
        else:
            break
    doc_lines.reverse()
    return doc_lines


def parse_docstring(doc_lines: list[str]) -> tuple[str, str, list[str]]:
    """解析 doc lines -> (summary, logic, examples)。"""
    # summary: 第一非空行，去掉 `name：` 或 `name:` 前缀
    summary = ""
    for line in doc_lines:
        if line.strip():
            summary = line.strip()
            break
    # 去掉 `xxx_V230506：xxx描述` 中的 `xxx_V230506：` 前缀（中文冒号或英文冒号）
    if summary:
        # 匹配形如 "name_V240328：描述" 的格式
        m = re.match(r"^[A-Za-z][A-Za-z0-9_]*\s*[：:]\s*(.+)$", summary)
        if m:
            summary = m.group(1).strip()

    # logic: 找到 "信号逻辑" 段，直到下一个段标题或末尾
    logic_lines: list[str] = []
    in_logic = False
    for line in doc_lines:
        stripped = line.strip()
        # 检查是否进入"信号逻辑"段
        if not in_logic:
            if re.match(r"^信号逻辑\s*[：:]", stripped):
                in_logic = True
                # 同行剩余内容也算
                rest = re.sub(r"^信号逻辑\s*[：:]\s*", "", stripped)
                if rest:
                    logic_lines.append(rest)
                continue
        else:
            # 检查是否进入下一个段（段标题以 "xxx：" 开头）
            is_next_section = False
            for hdr in SECTION_HEADERS:
                if re.match(rf"^{hdr}\s*[：:]", stripped):
                    is_next_section = True
                    break
            if is_next_section:
                break
            logic_lines.append(line)

    # 修剪 logic 前后空行
    while logic_lines and not logic_lines[0].strip():
        logic_lines.pop(0)
    while logic_lines and not logic_lines[-1].strip():
        logic_lines.pop()
    logic = "\n".join(logic_lines).strip()

    # examples: 所有 Signal('...')，去重保序
    raw_text = "\n".join(doc_lines)
    seen: set[str] = set()
    examples: list[str] = []
    for m in SIGNAL_EXAMPLE_RE.finditer(raw_text):
        v = m.group(1)
        if v not in seen:
            seen.add(v)
            examples.append(v)

    return summary, logic, examples


def parse_signal_attr(body: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in KV_RE.findall(body):
        out[k] = v
    return out


def scan() -> list[SignalInfo]:
    if not SIGNALS_DIR.is_dir():
        sys.exit(f"目录不存在: {SIGNALS_DIR}")

    signals: list[SignalInfo] = []
    for rs in sorted(SIGNALS_DIR.glob("*.rs")):
        if rs.name in SKIP_FILES:
            continue
        text = rs.read_text(encoding="utf-8")
        for m in SIGNAL_ATTR_RE.finditer(text):
            attr_start = m.start()
            kv = parse_signal_attr(m.group("body"))
            name = kv.get("name", "")
            if not name:
                # 没有 name 字段的注解，跳过（防御性）
                continue
            doc_lines = extract_doc_lines(text, attr_start)
            summary, logic, examples = parse_docstring(doc_lines)
            signals.append(
                SignalInfo(
                    name=name,
                    category=kv.get("category", ""),
                    template=kv.get("template", ""),
                    opcode=kv.get("opcode", ""),
                    file=rs.name,
                    doc_summary=summary,
                    doc_logic=logic,
                    signal_examples=examples,
                )
            )
    return signals


# ---------------- 渲染 ----------------

def xml_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_json(signals: list[SignalInfo]) -> str:
    return json.dumps([asdict(s) for s in signals], ensure_ascii=False, indent=2)


def render_xml(signals: list[SignalInfo]) -> str:
    """飞书 docx 兼容 XML 片段，按文件分组。"""
    by_file: dict[str, list[SignalInfo]] = {}
    for s in signals:
        by_file.setdefault(s.file, []).append(s)

    parts: list[str] = []
    for filename in sorted(by_file):
        group = by_file[filename]
        parts.append(f"<h2>📦 {xml_escape(filename)}（{len(group)} 个信号）</h2>")
        parts.append("")
        for s in group:
            parts.append(f"<h3>{xml_escape(s.name)}</h3>")
            if s.doc_summary:
                parts.append(
                    f"<p><b>一句话用途：</b>{xml_escape(s.doc_summary)}</p>"
                )
            # 元数据表
            parts.append("<table>")
            parts.append('<colgroup><col width="100"/><col width="380"/></colgroup>')
            parts.append("<tbody>")
            parts.append(
                f'<tr><td background-color="light-gray"><b>template</b></td>'
                f'<td><code>{xml_escape(s.template)}</code></td></tr>'
            )
            parts.append(
                f'<tr><td background-color="light-gray"><b>category</b></td>'
                f'<td>{xml_escape(s.category)}</td></tr>'
            )
            parts.append(
                f'<tr><td background-color="light-gray"><b>opcode</b></td>'
                f'<td><code>{xml_escape(s.opcode)}</code></td></tr>'
            )
            parts.append("</tbody>")
            parts.append("</table>")

            if s.doc_logic:
                parts.append("<p><b>信号逻辑：</b></p>")
                parts.append("<blockquote>")
                for ln in s.doc_logic.split("\n"):
                    if ln.strip():
                        parts.append(f"<p>{xml_escape(ln)}</p>")
                    else:
                        parts.append("<p></p>")
                parts.append("</blockquote>")

            parts.append("<p><b>信号表达示例：</b></p>")
            if s.signal_examples:
                parts.append("<ul>")
                for ex in s.signal_examples:
                    parts.append(f"<li><code>{xml_escape(ex)}</code></li>")
                parts.append("</ul>")
            else:
                parts.append(
                    "<p><i>该信号未在 docstring 中给出表达示例（可参考 template 自行组装）。</i></p>"
                )

            parts.append("<hr/>")
            parts.append("")
    return "\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--format",
        choices=["json", "xml"],
        default="xml",
        help="输出格式（默认 xml）",
    )
    parser.add_argument("--output", type=Path, help="写入文件而非 stdout")
    args = parser.parse_args()

    signals = scan()
    payload = render_json(signals) if args.format == "json" else render_xml(signals)

    if args.output:
        args.output.write_text(payload, encoding="utf-8")
        print(
            f"已写入 {args.output}（{len(signals)} 个信号，{len(payload)} bytes）",
            file=sys.stderr,
        )
    else:
        print(payload)


if __name__ == "__main__":
    main()
