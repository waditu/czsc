import pandas as pd
import numpy as np
from czsc.utils.plot_backtest import plot_colored_table

def test_plot_colored_table():
    # 构造测试数据
    df = pd.DataFrame({
        "策略名称": ["策略A", "策略B", "策略C", "策略D", "策略E"],
        "年化收益率": [0.15, 0.25, -0.05, 0.10, 0.30],
        "最大回撤": [0.10, 0.15, 0.20, 0.05, 0.12],
        "夏普比率": [1.5, 2.0, -0.5, 1.2, 2.5],
        "胜率": [0.55, 0.60, 0.45, 0.52, 0.65],
        "交易次数": [100, 120, 80, 90, 150]
    })
    df.set_index("策略名称", inplace=True)

    # 生成 HTML
    html_content = plot_colored_table(
        df, 
        title="策略绩效对比测试", 
        to_html=True,
        is_good_high_columns=["年化收益率", "夏普比率", "胜率"],
        row_height=40,
        border_color="white",
        header_bgcolor="darkblue"
    )
    
    # 包装成完整的 HTML 文件
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>测试报告</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #111; color: #eee; }}
            .chart-container {{ margin-bottom: 30px; border: 1px solid #333; padding: 10px; }}
        </style>
    </head>
    <body>
        <h1>策略绩效对比测试</h1>
        <div class="chart-container">
            {html_content}
        </div>
    </body>
    </html>
    """

    with open("test_plot_colored_table_result.html", "w", encoding="utf-8") as f:
        f.write(full_html)
    
    print("测试完成，结果已保存至 test_plot_colored_table_result.html")

if __name__ == "__main__":
    test_plot_colored_table()
