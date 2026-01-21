"""
HTML 报告构建器

提供灵活的 HTML 报告生成功能，支持链式调用和按需添加内容元素。
"""

import os
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd


class HtmlReportBuilder:
    """HTML 报告构建器
    
    支持链式调用，按需添加各种 HTML 元素，生成美观的 HTML 报告。
    
    示例用法：
        builder = HtmlReportBuilder(title="我的报告")
        builder.add_header({"日期": "2024-01-01", "版本": "v1.0"}) \
               .add_metrics([{"label": "收益率", "value": "15.3%", "is_positive": True}]) \
               .add_section("简介", "<p>这是报告内容</p>") \
               .save("report.html")
    """
    
    def __init__(self, title: str = "HTML 报告", theme: str = "light"):
        """初始化 HTML 报告构建器
        
        :param title: 报告标题
        :param theme: 主题，可选 'light' 或 'dark'
        """
        self.title = title
        self.theme = theme
        self.sections = []  # 存储所有内容区域
        self.custom_css = []  # 自定义 CSS
        self.custom_scripts = []  # 自定义脚本
        self.chart_count = 0  # 图表计数器，用于生成唯一ID
        self._init_default_styles()
        
    def _init_default_styles(self):
        """初始化默认样式"""
        self.base_css = """
        :root {
            --bg-primary: #ffffff;
            --bg-secondary: #f8f9fa;
            --bg-tertiary: #e9ecef;
            --text-primary: #212529;
            --text-secondary: #6c757d;
            --accent-green: #28a745;
            --accent-red: #dc3545;
            --accent-blue: #007bff;
            --accent-yellow: #ffc107;
            --border-color: #dee2e6;
            --shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        html, body {
            width: 100%;
            height: 100%;
            overflow-x: hidden;
        }
        
        body {
            background-color: var(--bg-primary);
            color: var(--text-primary);
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            line-height: 1.5;
            display: flex;
            flex-direction: column;
        }
        
        .container {
            max-width: 96%;
            padding: 0 1rem;
            margin: 0 auto;
        }
        
        .header-section {
            background: linear-gradient(135deg, var(--bg-secondary) 0%, var(--bg-tertiary) 100%);
            border-bottom: 1px solid var(--border-color);
            padding: 1.5rem 0;
            margin-bottom: 1.5rem;
        }
        
        .header-title {
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 0.3rem;
        }
        
        .header-subtitle {
            color: var(--text-secondary);
            font-size: 0.9rem;
        }
        
        .param-badges {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-top: 1rem;
        }
        
        .param-badge {
            background-color: var(--bg-primary);
            color: var(--text-secondary);
            padding: 0.35rem 0.7rem;
            border-radius: 6px;
            font-size: 0.8rem;
            border: 1px solid var(--border-color);
            transition: all 0.2s;
        }
        
        .param-badge:hover {
            border-color: var(--accent-blue);
            color: var(--text-primary);
        }
        
        .main-content {
            flex: 1;
            padding-bottom: 2rem;
        }
        
        .metric-card {
            background: var(--bg-primary);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 1rem;
            text-align: center;
            transition: all 0.3s;
            box-shadow: var(--shadow);
            height: 100%;
        }
        
        .metric-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            border-color: var(--accent-blue);
        }
        
        .metric-value {
            font-size: 1.6rem;
            font-weight: 700;
            margin-bottom: 0.2rem;
        }
        
        .metric-label {
            font-size: 0.75rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .metric-positive {
            color: var(--accent-green);
        }
        
        .metric-negative {
            color: var(--accent-red);
        }
        
        .metric-neutral {
            color: var(--accent-blue);
        }
        
        .chart-card {
            background: var(--bg-primary);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            overflow: hidden;
            box-shadow: var(--shadow);
            min-height: 500px;
        }
        
        .chart-header {
            background: var(--bg-secondary);
            padding: 0.8rem 1.2rem;
            border-bottom: 1px solid var(--border-color);
        }
        
        .chart-title {
            font-size: 1.1rem;
            font-weight: 600;
            margin: 0;
            color: var(--text-primary);
        }
        
        .chart-body {
            padding: 0;
            width: 100%;
        }
        
        .chart-body .plotly-graph-div {
            width: 100% !important;
        }
        
        .nav-tabs {
            border-bottom: 2px solid var(--border-color);
            background: var(--bg-secondary);
        }
        
        .nav-tabs .nav-link {
            color: var(--text-secondary);
            border: none;
            border-bottom: 3px solid transparent;
            padding: 0.8rem 1.2rem;
            transition: all 0.2s;
            font-size: 0.9rem;
        }
        
        .nav-tabs .nav-link:hover {
            color: var(--text-primary);
            background: var(--bg-tertiary);
        }
        
        .nav-tabs .nav-link.active {
            color: var(--accent-blue);
            background: var(--bg-primary);
            border-bottom-color: var(--accent-blue);
        }
        
        .tab-content {
            background: var(--bg-primary);
            padding: 0;
            height: 100%;
        }
        
        .tab-pane {
            height: 100%;
        }
        
        .data-table {
            background: var(--bg-primary);
            border-radius: 10px;
            overflow: hidden;
            box-shadow: var(--shadow);
        }
        
        .table {
            color: var(--text-primary);
            margin-bottom: 0;
            font-size: 0.9rem;
        }
        
        .table thead th {
            background: var(--bg-secondary);
            border-bottom: 2px solid var(--border-color);
            color: var(--text-primary);
            font-weight: 600;
            padding: 0.8rem;
            text-transform: uppercase;
            font-size: 0.75rem;
        }
        
        .table tbody tr {
            border-bottom: 1px solid var(--border-color);
            transition: background 0.2s;
        }
        
        .table tbody tr:hover {
            background: var(--bg-secondary);
        }
        
        .table tbody td {
            padding: 0.8rem;
            vertical-align: middle;
        }
        
        .section-header {
            display: flex;
            align-items: center;
            margin-bottom: 1rem;
            padding-bottom: 0.3rem;
            border-bottom: 2px solid var(--border-color);
        }
        
        .section-title {
            font-size: 1.3rem;
            font-weight: 700;
            color: var(--text-primary);
            margin: 0;
        }
        
        .section-icon {
            margin-right: 0.5rem;
            color: var(--accent-blue);
        }
        
        .footer {
            background: var(--bg-secondary);
            border-top: 1px solid var(--border-color);
            padding: 1rem 0;
            margin-top: auto;
            text-align: center;
            color: var(--text-secondary);
            font-size: 0.85rem;
        }
        
        @media (max-width: 768px) {
            .header-title {
                font-size: 1.4rem;
            }
            
            .metric-value {
                font-size: 1.3rem;
            }
            
            .nav-tabs .nav-link {
                padding: 0.6rem 0.8rem;
                font-size: 0.85rem;
            }
            
            .chart-card {
                height: 70vh;
            }
        }
        """
        
    def add_custom_css(self, css: str) -> 'HtmlReportBuilder':
        """添加自定义 CSS 样式
        
        :param css: CSS 字符串
        :return: self，支持链式调用
        """
        self.custom_css.append(css)
        return self
        
    def add_custom_script(self, script: str) -> 'HtmlReportBuilder':
        """添加自定义 JavaScript 脚本
        
        :param script: JavaScript 字符串
        :return: self，支持链式调用
        """
        self.custom_scripts.append(script)
        return self
        
    def add_header(self, params: Dict[str, str], subtitle: str = None) -> 'HtmlReportBuilder':
        """添加头部区域
        
        :param params: 参数字典，如 {"日期": "2024-01-01", "版本": "v1.0"}
        :param subtitle: 副标题
        :return: self，支持链式调用
        """
        badges_html = ""
        for key, value in params.items():
            badges_html += f'''                        <span class="param-badge">
                            <i class="bi bi-info-circle"></i> {key}: {value}
                        </span>\n'''
        
        header_html = f'''    <!-- 头部区域 -->
    <div class="header-section">
        <div class="container">
            <div class="row">
                <div class="col-12">
                    <h1 class="header-title">
                        <i class="bi bi-graph-up-arrow section-icon"></i>
                        {self.title}
                    </h1>
                    {f'<p class="header-subtitle">{subtitle}</p>' if subtitle else ''}
                    
                    <div class="param-badges">
{badges_html}                    </div>
                </div>
            </div>
        </div>
    </div>
'''
        
        self.sections.append(("header", header_html))
        return self
        
    def add_metrics(self, metrics: List[Dict[str, Any]], title: str = "核心绩效指标") -> 'HtmlReportBuilder':
        """添加绩效指标卡片
        
        :param metrics: 指标列表，每个元素为 {"label": str, "value": str, "is_positive": bool}
        :param title: 区域标题
        :return: self，支持链式调用
        """
        metrics_html = ""
        for m in metrics:
            value_class = "metric-positive" if m.get("is_positive", False) else "metric-negative"
            metrics_html += f'''                <div class="col-6 col-md-4 col-lg-3 col-xl-2">
                    <div class="metric-card">
                        <div class="metric-value {value_class}">
                            {m["value"]}
                        </div>
                        <div class="metric-label">{m["label"]}</div>
                    </div>
                </div>\n'''
        
        section_html = f'''    <!-- {title} -->
    <section class="mb-4">
        <div class="section-header">
            <i class="bi bi-speedometer2 section-icon"></i>
            <h2 class="section-title">{title}</h2>
        </div>
        
        <div class="row g-2">
{metrics_html}        </div>
    </section>
'''
        
        self.sections.append(("metrics", section_html))
        return self
        
    def add_chart_tab(self, name: str, chart_html: str, icon: str = "bi-graph-up", 
                     active: bool = False) -> 'HtmlReportBuilder':
        """添加单个图表标签页
        
        :param name: 标签页名称
        :param chart_html: 图表 HTML 内容
        :param icon: 图标类名（Bootstrap Icons）
        :param active: 是否为默认激活的标签页
        :return: self，支持链式调用
        """
        self.chart_count += 1
        tab_id = f"chart-tab-{self.chart_count}"
        
        tab_button = f'''                        <li class="nav-item">
                            <button class="nav-link {"active" if active else ""}" 
                                    data-bs-toggle="tab" data-bs-target="#{tab_id}" 
                                    type="button" role="tab">
                                <i class="bi {icon}"></i> {name}
                            </button>
                        </li>'''
        
        tab_content = f'''                        <div class="tab-pane fade {"show active" if active else ""}" 
                                          id="{tab_id}" role="tabpanel">
                            <div class="chart-body">
                                {chart_html}
                            </div>
                        </div>'''
        
        self.sections.append(("chart_tab", {"button": tab_button, "content": tab_content}))
        return self
        
    def add_charts_section(self, title: str = "可视化分析") -> 'HtmlReportBuilder':
        """添加图表展示区域（收集所有之前添加的图表标签页）
        
        :param title: 区域标题
        :return: self，支持链式调用
        """
        # 收集所有图表标签页
        chart_tabs = [section for section in self.sections if section[0] == "chart_tab"]
        
        if not chart_tabs:
            return self
            
        # 构建标签按钮HTML
        tabs_html = "                <div class=\"chart-card\">\n                    <ul class=\"nav nav-tabs\" role=\"tablist\">\n"
        tabs_html += "\n".join([tab[1]["button"] for tab in chart_tabs])
        tabs_html += "\n                    </ul>\n"
        
        # 构建标签内容HTML
        content_html = "                    <div class=\"tab-content\">\n"
        content_html += "\n".join([tab[1]["content"] for tab in chart_tabs])
        content_html += "\n                    </div>\n                </div>"
        
        section_html = f'''    <!-- {title} -->
    <section class="mb-4">
        <div class="section-header">
            <i class="bi bi-bar-chart-line section-icon"></i>
            <h2 class="section-title">{title}</h2>
        </div>
        
{tabs_html}
{content_html}
    </section>
'''
        
        # 移除单独的图表标签页，替换为整个区域
        self.sections = [s for s in self.sections if s[0] != "chart_tab"]
        self.sections.append(("charts_section", section_html))
        
        return self
        
    def add_table(self, df: pd.DataFrame, title: str = "数据表", 
                  max_rows: int = None, style: str = "Table Grid") -> 'HtmlReportBuilder':
        """添加数据表格
        
        :param df: pandas DataFrame
        :param title: 表格标题
        :param max_rows: 最大显示行数，None 表示全部显示
        :param style: 表格样式
        :return: self，支持链式调用
        """
        if df.empty:
            return self
            
        # 限制行数
        if max_rows and len(df) > max_rows:
            df = df.head(max_rows)
            
        # 生成表格 HTML
        table_html = df.to_html(classes='table table-striped table-hover', 
                                index=False, border=0, justify='center')
        
        section_html = f'''    <!-- {title} -->
    <section class="mb-4">
        <div class="section-header">
            <i class="bi bi-table section-icon"></i>
            <h2 class="section-title">{title}</h2>
        </div>
        
        <div class="data-table">
            {table_html}
        </div>
    </section>
'''
        
        self.sections.append(("table", section_html))
        return self
        
    def add_section(self, title: str, content: str, icon: str = "bi-file-text") -> 'HtmlReportBuilder':
        """添加自定义章节
        
        :param title: 章节标题
        :param content: 章节内容（HTML字符串）
        :param icon: 图标类名
        :return: self，支持链式调用
        """
        section_html = f'''    <!-- {title} -->
    <section class="mb-4">
        <div class="section-header">
            <i class="bi {icon} section-icon"></i>
            <h2 class="section-title">{title}</h2>
        </div>
        
        <div class="section-content">
            {content}
        </div>
    </section>
'''
        
        self.sections.append(("custom", section_html))
        return self
        
    def add_footer(self, text: str = None) -> 'HtmlReportBuilder':
        """添加页脚
        
        :param text: 页脚文本，None 则使用默认文本
        :return: self，支持链式调用
        """
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if text is None:
            text = f'''<i class="bi bi-code-square"></i>
                由 CZSC 缠中说禅技术分析工具生成 | 
                <i class="bi bi-clock-history"></i>
                生成时间: {current_time}'''
            
        footer_html = f'''    <!-- 页脚 -->
    <footer class="footer">
        <div class="container">
            <p class="mb-0">
                {text}
            </p>
        </div>
    </footer>
'''
        
        self.sections.append(("footer", footer_html))
        return self
        
    def render(self) -> str:
        """渲染完整的 HTML 报告
        
        :return: HTML 字符串
        """
        # 合并所有 CSS
        all_css = self.base_css + "\n" + "\n".join(self.custom_css)
        
        # 分离头部、页脚和主要内容
        header_html = ""
        footer_html = ""
        main_body_html = ""
        
        for section_type, section_content in self.sections:
            if isinstance(section_content, dict):
                continue  # 跳过未处理的图表标签页
            
            if section_type == "header":
                header_html += section_content + "\n"
            elif section_type == "footer":
                footer_html += section_content + "\n"
            else:
                main_body_html += section_content + "\n"

        # 预先拼接自定义脚本（避免在f-string中使用反斜杠）
        custom_scripts_str = "\n".join(self.custom_scripts)

        # 构建完整 HTML
        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.title}</title>
    
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
    
    <style>
{all_css}
    </style>
</head>
<body>
{header_html}
    <div class="container main-content">
{main_body_html}
    </div>
{footer_html}
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // 监听 Tab 切换事件，重新调整图表大小
        document.addEventListener('DOMContentLoaded', function() {{
            var triggerTabList = [].slice.call(document.querySelectorAll('button[data-bs-toggle="tab"]'))
            triggerTabList.forEach(function(triggerEl) {{
                triggerEl.addEventListener('shown.bs.tab', function(event) {{
                    var targetId = event.target.getAttribute('data-bs-target');
                    var targetPane = document.querySelector(targetId);
                    var plotlyDiv = targetPane.querySelector('.plotly-graph-div');
                    if (plotlyDiv) {{
                        Plotly.Plots.resize(plotlyDiv);
                    }}
                }})
            }})
            
            // 窗口大小改变时也触发 resize
            window.addEventListener('resize', function() {{
                var activePane = document.querySelector('.tab-pane.active');
                if (activePane) {{
                    var plotlyDiv = activePane.querySelector('.plotly-graph-div');
                    if (plotlyDiv) {{
                        Plotly.Plots.resize(plotlyDiv);
                    }}
                }}
            }});
        }});
        
        // 用户自定义脚本
        {custom_scripts_str}
    </script>
</body>
</html>
    """
        
        return html_content
        
    def save(self, file_path: str) -> str:
        """保存 HTML 报告到文件
        
        :param file_path: 输出文件路径
        :return: 文件路径
        """
        html_content = self.render()
        
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else ".", exist_ok=True)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        return file_path
