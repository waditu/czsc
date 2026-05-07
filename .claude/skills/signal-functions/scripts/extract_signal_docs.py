"""
从 rs_czsc Rust 源码提取信号函数文档，为每个信号生成独立 markdown 文件。

用法: python extract_signal_docs.py <rs_czsc_signals_src_dir> <output_references_dir>

示例:
    python extract_signal_docs.py crates/czsc-signals/src .claude/skills/signal-functions/references
"""

import re
import sys
from pathlib import Path


# ── 文档块解析 ──────────────────────────────────────────────────────

SIGNAL_ATTR_RE = re.compile(
    r'#\[signal\(\s*\n(.*?)\)\]', re.DOTALL
)
SIGNAL_FIELD_RE = re.compile(
    r'(\w+)\s*=\s*"([^"]*)"'
)
DOC_LINE_RE = re.compile(r'^\s*///\s?(.*)')


def extract_signals_from_file(filepath: Path) -> list[dict]:
    """从单个 Rust 源文件提取所有信号函数的文档。"""
    text = filepath.read_text(encoding='utf-8')
    lines = text.split('\n')

    signals: list[dict] = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # 查找 #[signal(...)] 属性
        if line.strip().startswith('#[signal('):
            attr_start = i
            attr_text = line
            depth = line.count('(') - line.count(')')
            j = i + 1
            while depth > 0 and j < len(lines):
                attr_text += '\n' + lines[j]
                depth += lines[j].count('(') - lines[j].count(')')
                j += 1
            i = j

            # 解析属性字段
            attr_match = SIGNAL_ATTR_RE.search(attr_text)
            if not attr_match:
                continue
            fields = dict(SIGNAL_FIELD_RE.findall(attr_match.group(1)))

            # 向上查找文档注释块（紧贴 #[signal] 之前的 /// 行）
            doc_lines: list[str] = []
            k = attr_start - 1
            while k >= 0 and lines[k].strip().startswith('///'):
                doc_lines.insert(0, lines[k])
                k -= 1

            # 解析文档注释
            doc_parts = parse_doc_comment(doc_lines)

            # 向下查找函数签名
            func_line = ''
            while i < len(lines):
                if lines[i].strip().startswith('pub fn ') or lines[i].strip().startswith('pub async fn '):
                    func_line = lines[i].strip()
                    break
                i += 1

            sig_info = {
                'name': fields.get('name', ''),
                'template': fields.get('template', ''),
                'category': fields.get('category', ''),
                'opcode': fields.get('opcode', ''),
                'param_kind': fields.get('param_kind', ''),
                'module': filepath.stem,
                'title': doc_parts.get('title', fields.get('name', '')),
                'param_template': doc_parts.get('param_template', ''),
                'logic': doc_parts.get('logic', ''),
                'examples': doc_parts.get('examples', ''),
                'params': doc_parts.get('params', ''),
                'alignment': doc_parts.get('alignment', ''),
            }
            signals.append(sig_info)
        else:
            i += 1

    return signals


def parse_doc_comment(doc_lines: list[str]) -> dict[str, str]:
    """解析 /// 文档注释块，提取各段落。"""
    # 去掉 /// 前缀
    cleaned: list[str] = []
    for raw in doc_lines:
        m = DOC_LINE_RE.match(raw)
        cleaned.append(m.group(1) if m else '')

    # 合并为一整段文本
    full_text = '\n'.join(cleaned)

    parts: dict[str, str] = {}

    # 标题行（第一行非空）
    title_match = re.match(r'([^\n]+)', full_text)
    if title_match:
        parts['title'] = title_match.group(1).strip()

    # 参数模板
    m = re.search(r'参数模板：[`"](.+?)[`"]', full_text)
    if m:
        parts['param_template'] = m.group(1)

    # 信号逻辑
    logic_match = re.search(r'信号逻辑：(.*?)(?=信号列表示例：|参数说明：|$)', full_text, re.DOTALL)
    if logic_match:
        parts['logic'] = logic_match.group(1).strip()

    # 信号列表示例
    examples_match = re.search(r'信号列表示例：(.*?)(?=参数说明：|对齐说明：|$)', full_text, re.DOTALL)
    if examples_match:
        parts['examples'] = examples_match.group(1).strip()

    # 参数说明
    params_match = re.search(r'参数说明：(.*?)(?=对齐说明：|$)', full_text, re.DOTALL)
    if params_match:
        parts['params'] = params_match.group(1).strip()

    # 对齐说明
    align_match = re.search(r'对齐说明：(.+)', full_text, re.DOTALL)
    if align_match:
        parts['alignment'] = align_match.group(1).strip()

    return parts


# ── Markdown 生成 ──────────────────────────────────────────────────

def generate_signal_md(sig: dict) -> str:
    """为单个信号生成 markdown 内容。"""
    name = sig['name']
    lines: list[str] = []

    lines.append(f'# {sig.get("title", name)}')
    lines.append('')
    lines.append(f'> 模块: `{sig["module"]}.rs` | 类别: `{sig["category"]}`')
    lines.append('')

    # 参数模板
    if sig.get('param_template'):
        lines.append('## 参数模板')
        lines.append('')
        lines.append(f'`{sig["param_template"]}`')
        lines.append('')

    # 信号逻辑
    if sig.get('logic'):
        lines.append('## 信号逻辑')
        lines.append('')
        for logic_line in sig['logic'].split('\n'):
            stripped = logic_line.strip()
            if stripped:
                lines.append(stripped)
        lines.append('')

    # 信号列表示例
    if sig.get('examples'):
        lines.append('## 信号列表示例')
        lines.append('')
        for ex_line in sig['examples'].split('\n'):
            stripped = ex_line.strip()
            if stripped:
                lines.append(stripped)
        lines.append('')

    # 参数说明
    if sig.get('params'):
        lines.append('## 参数说明')
        lines.append('')
        for p_line in sig['params'].split('\n'):
            stripped = p_line.strip()
            if stripped:
                lines.append(stripped)
        lines.append('')

    # 对齐说明
    if sig.get('alignment'):
        lines.append('## 对齐说明')
        lines.append('')
        lines.append(sig['alignment'])
        lines.append('')

    return '\n'.join(lines)


def generate_module_index(module_name: str, signals: list[dict], all_signal_files: dict[str, str]) -> str:
    """为模块生成索引 markdown。"""
    lines: list[str] = []
    lines.append(f'# {module_name} 模块信号索引')
    lines.append('')
    lines.append(f'> 源码: `crates/czsc-signals/src/{module_name}.rs`')
    lines.append(f'> 共 {len(signals)} 个信号')
    lines.append('')
    lines.append('| 信号名 | 参数模板 | 说明 | 详细文档 |')
    lines.append('|--------|----------|------|----------|')

    for sig in sorted(signals, key=lambda s: s['name']):
        name = sig['name']
        template = sig.get('param_template', sig.get('template', ''))
        # 从标题中提取简短说明
        title = sig.get('title', name)
        desc = title.split('：', 1)[-1] if '：' in title else title
        # 文件链接
        filename = all_signal_files.get(name, '')
        link = f'[详细文档](signals/{filename})' if filename else ''
        lines.append(f'| `{name}` | `{template}` | {desc} | {link} |')

    lines.append('')
    return '\n'.join(lines)


# ── 主流程 ─────────────────────────────────────────────────────────

# 模块分类映射
MODULE_GROUPS = {
    # K线级信号
    'bar': 'bar',
    'cxt': 'cxt',
    'tas': 'tas',
    'jcc': 'jcc',
    'zdy': 'zdy',
    'ang': 'misc',
    'xl': 'misc',
    'vol': 'misc',
    'coo': 'misc',
    'byi': 'misc',
    'pressure': 'misc',
    'obv': 'misc',
    'cvolp': 'misc',
    'ntmdk': 'misc',
    'kcatr': 'misc',
    'clv': 'misc',
    # 交易级信号
    'pos': 'trader',
    'cat': 'trader',
    'cxt_trader': 'trader',
    'zdy_trader': 'trader',
}


def main():
    if len(sys.argv) < 3:
        print(f'用法: python {sys.argv[0]} <signals_src_dir> <output_dir>')
        sys.exit(1)

    src_dir = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    signals_dir = out_dir / 'signals'

    signals_dir.mkdir(parents=True, exist_ok=True)

    # 收集所有信号
    all_signals: list[dict] = []
    rs_files = sorted(src_dir.glob('*.rs'))

    for rs_file in rs_files:
        if rs_file.name in ('lib.rs', 'registry.rs', 'types.rs', 'params.rs', 'utils.rs'):
            continue
        sigs = extract_signals_from_file(rs_file)
        all_signals.extend(sigs)
        print(f'  {rs_file.name}: 提取 {len(sigs)} 个信号')

    print(f'\n共提取 {len(all_signals)} 个信号函数')

    # 为每个信号生成独立 markdown 文件
    signal_file_map: dict[str, str] = {}  # name -> filename
    for sig in all_signals:
        name = sig['name']
        filename = f'{name}.md'
        md_content = generate_signal_md(sig)
        (signals_dir / filename).write_text(md_content, encoding='utf-8')
        signal_file_map[name] = filename

    print(f'已生成 {len(signal_file_map)} 个信号文档文件到 {signals_dir}/')

    # 按模块分组
    module_signals: dict[str, list[dict]] = {}
    for sig in all_signals:
        mod = sig['module']
        module_signals.setdefault(mod, []).append(sig)

    # 生成模块级索引文件
    for mod_name, sigs in sorted(module_signals.items()):
        index_content = generate_module_index(mod_name, sigs, signal_file_map)
        index_path = out_dir / f'signals-{mod_name}.md'
        index_path.write_text(index_content, encoding='utf-8')
        print(f'  模块索引: {index_path.name} ({len(sigs)} 个信号)')

    # 生成总索引（按分组归类）
    group_order = ['bar', 'cxt', 'tas', 'jcc', 'zdy', 'ang', 'xl', 'vol', 'coo', 'byi',
                   'pressure', 'obv', 'cvolp', 'ntmdk', 'kcatr', 'clv',
                   'pos', 'cat', 'cxt_trader', 'zdy_trader']

    print('\n=== 信号统计 ===')
    kline_count = sum(1 for s in all_signals if s['category'] == 'kline')
    trader_count = sum(1 for s in all_signals if s['category'] == 'trader')
    print(f'K线级信号: {kline_count}')
    print(f'交易级信号: {trader_count}')
    print(f'总计: {len(all_signals)}')


if __name__ == '__main__':
    main()
