"""
任务描述：根据标准持仓权重数据对策略进行回测，然后通过飞书卡片推送消息到飞书群

标准持仓权重数据格式要求：
- pd.DataFrame
- 包含 'dt'、'symbol'、'weight', 'price' 四列

使用 czsc.WeightBacktest 进行回测

使用飞书卡片2.0推送消息，飞书卡片2.0格式参考 @docs\飞书卡片2.0文档.md

推送中需要包含的信息：

1. 策略名称，样本外开始时间（默认值 20250101）
2. 策略最近10个交易日每个品种的收益表格，用 total 表示整个策略所有品种的等权收益
3. 策略样本外的累计收益曲线

编程要求：
1. 保持单个函数的简洁，职责单一
2. 函数和变量命名要有意义，符合其功能
3. 代码要有良好的注释，解释关键步骤和逻辑
"""
import czsc
import pandas as pd
import numpy as np
import json
import requests
from datetime import datetime
from typing import Dict, List, Any



def calculate_recent_returns(wb: czsc.WeightBacktest, days: int = 10) -> pd.DataFrame:
    """计算最近N个交易日的收益
    
    :param wb: WeightBacktest实例
    :param days: 最近的交易日数量
    :return: 收益数据表格
    """
    # 获取每日收益数据
    daily_returns = wb.daily_return
    
    # 获取最近N个交易日
    recent_dates = sorted(daily_returns['dt'].unique())[-days:]
    recent_data = daily_returns[daily_returns['dt'].isin(recent_dates)]
    
    # 计算每个品种的收益
    pivot_data = recent_data.pivot_table(
        index='dt', 
        columns='symbol', 
        values='return',
        aggfunc='mean'
    ).round(4)

    if 'total' not in pivot_data.columns:
        # 计算整体策略等权收益
        pivot_data['total'] = pivot_data.mean(axis=1)

    # 转换为百分比形式
    pivot_data = pivot_data * 100
    
    return pivot_data


def get_out_sample_curve(wb: czsc.WeightBacktest, out_sample_sdt: str) -> Dict[str, List]:
    """获取样本外累计收益曲线数据
    
    :param wb: WeightBacktest实例
    :param out_sample_sdt: 样本外开始时间
    :return: 图表数据字典
    """
    # 获取样本外数据
    returns_df = wb.results['品种等权']
    out_sample_data = returns_df[returns_df.index >= pd.to_datetime(out_sample_sdt)]
    
    # 准备图表数据
    chart_data = {
        "dates": out_sample_data.index.strftime('%Y-%m-%d').tolist(),
        "values": (out_sample_data['累计收益率'] * 100).round(2).tolist()
    }
    
    return chart_data


def create_feishu_card(strategy: str, out_sample_sdt: str, 
                      recent_returns: pd.DataFrame, 
                      curve_data: Dict[str, List]) -> Dict[str, Any]:
    """创建飞书卡片JSON结构
    
    :param strategy: 策略名称
    :param out_sample_sdt: 样本外开始时间
    :param recent_returns: 最近收益数据
    :param curve_data: 累计收益曲线数据
    :return: 飞书卡片JSON
    """
    # 构建表格数据
    table_rows = []
    
    # 添加表头
    header_cells = ["日期"] + [str(col) for col in recent_returns.columns]
    
    # 添加数据行
    for date, row in recent_returns.iterrows():
        row_cells = [date.strftime('%Y-%m-%d')]
        for col in recent_returns.columns:
            value = row[col]
            color = "green" if value >= 0 else "red"
            row_cells.append({
                "tag": "plain_text",
                "content": f"{value:.2f}%",
                "text_color": color
            })
        table_rows.append(row_cells)
    
    # 构建图表配置
    chart_spec = {
        "type": "line",
        "data": {
            "labels": curve_data["dates"],
            "datasets": [{
                "label": "累计收益率(%)",
                "data": curve_data["values"],
                "borderColor": "rgba(54, 162, 235, 1)",
                "backgroundColor": "rgba(54, 162, 235, 0.1)",
                "fill": True
            }]
        },
        "options": {
            "responsive": True,
            "maintainAspectRatio": False,
            "scales": {
                "y": {
                    "beginAtZero": True,
                    "ticks": {
                        "callback": "function(value) { return value + '%'; }"
                    }
                }
            }
        }
    }
    
    # 构建飞书卡片JSON 2.0结构
    card = {
        "schema": "2.0",
        "config": {
            "wide_screen_mode": True
        },
        "header": {
            "title": {
                "tag": "plain_text",
                "content": f"{strategy} - 策略最新表现"
            },
            "subtitle": {
                "tag": "plain_text",
                "content": f"样本外开始时间: {out_sample_sdt}"
            },
            "template": "blue"
        },
        "body": {
            "elements": [
                {
                    "tag": "markdown",
                    "content": "## 最近10个交易日收益表现"
                },
                {
                    "tag": "column_set",
                    "flex_mode": "stretch",
                    "columns": [
                        {
                            "tag": "column",
                            "width": "weighted",
                            "weight": 1,
                            "elements": [
                                {
                                    "tag": "markdown",
                                    "content": _format_returns_table(recent_returns)
                                }
                            ]
                        }
                    ]
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "markdown",
                    "content": "## 样本外累计收益曲线"
                },
                {
                    "tag": "markdown",
                    "content": f"**最新累计收益率**: {curve_data['values'][-1]:.2f}%\n\n"
                },
                {
                    "tag": "markdown",
                    "content": _format_curve_chart(curve_data)
                }
            ]
        }
    }
    
    return card


def _format_returns_table(df: pd.DataFrame) -> str:
    """将DataFrame格式化为Markdown表格
    
    :param df: 收益数据DataFrame
    :return: Markdown表格字符串
    """
    lines = []
    
    # 表头
    headers = ["日期"] + [str(col) for col in df.columns]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    
    # 数据行
    for date, row in df.iterrows():
        cells = [date.strftime('%m-%d')]
        for col in df.columns:
            value = row[col]
            if value >= 0:
                cells.append(f"<font color='green'>+{value:.2f}%</font>")
            else:
                cells.append(f"<font color='red'>{value:.2f}%</font>")
        lines.append("| " + " | ".join(cells) + " |")
    
    return "\n".join(lines)


def _format_curve_chart(curve_data: Dict[str, List]) -> str:
    """格式化累计收益曲线的简单文本表示
    
    :param curve_data: 曲线数据
    :return: 文本图表
    """
    values = curve_data['values']
    dates = curve_data['dates']
    
    # 只显示关键点
    n_points = min(10, len(values))
    step = max(1, len(values) // n_points)
    
    lines = []
    for i in range(0, len(values), step):
        date = dates[i]
        value = values[i]
        bar_length = int(abs(value) / 2)  # 简单的比例转换
        bar = "█" * bar_length
        
        if value >= 0:
            lines.append(f"{date}: {'':>20} | {bar} +{value:.2f}%")
        else:
            lines.append(f"{date}: {bar:>20} | {value:.2f}%")
    
    return "```\n" + "\n".join(lines) + "\n```"


def send_to_feishu(card: Dict[str, Any], webhook_key: str) -> bool:
    """发送卡片消息到飞书
    
    :param card: 飞书卡片JSON
    :param webhook_key: 飞书机器人webhook key
    :return: 是否发送成功
    """
    webhook_url = f"https://open.feishu.cn/open-apis/bot/v2/hook/{webhook_key}"
    
    payload = {
        "msg_type": "interactive",
        "card": card
    }
    
    try:
        response = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("code") == 0:
                print("消息发送成功")
                return True
            else:
                print(f"消息发送失败: {result.get('msg', '未知错误')}")
                return False
        else:
            print(f"HTTP请求失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"发送消息时出错: {str(e)}")
        return False


def push_strategy_latest(strategy: str, dfw: pd.DataFrame, feishu_key:str, out_sample_sdt="20250101", **kwargs):
    """推送策略最新表现到飞书群

    :param strategy: 策略名称
    :param dfw: 标准持仓权重数据，包含 'dt'、'symbol'、weight', 'price' 四列
    :param feishu_key: 飞书机器人 key
    :param out_sample_sdt: 样本外开始时间，默认值 '20250101'
    :param kwargs: 其他参数，参考 czsc.WeightBacktest
    :return:
    """
    try:
        # 1. 运行回测
        print(f"开始运行策略回测: {strategy}")
        wb = czsc.WeightBacktest(dfw, **kwargs)
        
        # 2. 计算最近10个交易日收益
        print("计算最近10个交易日收益...")
        recent_returns = calculate_recent_returns(wb, days=10)
        
        # 3. 获取样本外累计收益曲线
        print("获取样本外累计收益曲线...")
        curve_data = get_out_sample_curve(wb, out_sample_sdt)
        
        # 4. 创建飞书卡片
        print("创建飞书卡片...")
        card = create_feishu_card(strategy, out_sample_sdt, recent_returns, curve_data)
        
        # 5. 发送到飞书
        print("发送消息到飞书...")
        success = send_to_feishu(card, feishu_key)
        
        if success:
            print(f"策略 {strategy} 的最新表现已成功推送到飞书群")
        else:
            print(f"策略 {strategy} 推送失败")
            
        return success
        
    except Exception as e:
        print(f"推送过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_push_strategy_latest():
    """测试推送策略最新表现到飞书群"""
    dfw = czsc.mock.generate_klines_with_weights(seed=1234)
    feishu_key = "97ef04e5-1dea-499e-a99f-58ec30b05283"
    push_strategy_latest(strategy="测试策略", dfw=dfw, feishu_key=feishu_key)


if __name__ == '__main__':
    test_push_strategy_latest()
