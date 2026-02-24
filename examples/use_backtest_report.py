# -*- coding: utf-8 -*-
"""
权重回测报告生成器使用样例
"""
import os
import sys
import czsc
import pandas as pd

# 将项目根目录添加到 sys.path 以便导入 czsc
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from czsc.utils.backtest_report import generate_backtest_report, generate_pdf_backtest_report


def main():
    # 0. 准备输出目录
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 1. 准备数据
    print("正在生成模拟数据...")
    df = pd.read_feather(r"C:\Users\dell\Downloads\weight_example.feather")
    print(f"数据生成完毕，共 {len(df)} 行数据")
    print(df.head())
    
    # 2. 生成 HTML 报告（默认配置）
    print("\n[场景1] 正在生成默认 HTML 报告...")
    html_path = os.path.join(output_dir, 'backtest_report_default.html')
    try:
        generate_backtest_report(
            df,
            output_path=html_path,
            title="默认参数回测报告"
        )
        print(f"HTML 报告已生成: {html_path}")
    except Exception as e:
        print(f"HTML 报告生成失败: {e}")

    # 3. 生成 HTML 报告（自定义配置）
    print("\n[场景2] 正在生成自定义配置的 HTML 报告...")
    html_custom_path = os.path.join(output_dir, 'backtest_report_custom.html')
    try:
        # 自定义参数说明：
        # fee_rate: 交易手续费率，例如万五为 0.0005
        # digits: 权重小数位数保留
        # yearly_days: 年化天数，通常为 252 或 240
        # n_jobs: 并行计算使用的 CPU 核心数
        generate_backtest_report(
            df,
            output_path=html_custom_path,
            title="高频交易策略回测报告",
            fee_rate=0.0005,    
            digits=4,           
            yearly_days=240,    
            n_jobs=1            
        )
        print(f"自定义 HTML 报告已生成: {html_custom_path}")
    except Exception as e:
        print(f"自定义 HTML 报告生成失败: {e}")

    # 4. 生成 PDF 报告
    print("\n[场景3] 正在生成 PDF 报告...")
    pdf_path = os.path.join(output_dir, 'backtest_report.pdf')
    try:
        generate_pdf_backtest_report(
            df,
            output_path=pdf_path,
            title="策略回测分析报告",
            fee_rate=0.0002
        )
        print(f"PDF 报告已生成: {pdf_path}")
    except Exception as e:
        print(f"PDF 报告生成失败: {e}")
        # PDF 生成依赖 reportlab，如果未安装可能会失败
        print("提示: 确保已安装 reportlab 库: pip install reportlab")

if __name__ == "__main__":
    main()
