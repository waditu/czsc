"""
任务描述：根据标准持仓权重数据对策略进行回测，然后通过飞书卡片推送消息到飞书群

标准持仓权重数据格式要求：
- pd.DataFrame
- 包含 'dt'、'symbol'、'weight', 'price' 四列

使用 WeightBacktest 进行回测

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
import pandas as pd
import requests
from rs_czsc import WeightBacktest
from typing import Dict, List, Any



def calculate_recent_returns(wb: WeightBacktest, days: int = 10) -> pd.DataFrame:
    """计算最近N个交易日的收益
    
    :param wb: WeightBacktest实例
    :param days: 最近的交易日数量
    :return: 收益数据表格
    """
    # 获取每日收益数据
    daily_returns = wb.daily_return
    daily_returns.rename(columns={'date': 'dt'}, inplace=True)
    daily_returns['dt'] = pd.to_datetime(daily_returns['dt'])
    # 获取最近N个交易日
    recent_dates = sorted(daily_returns['dt'].unique())[-days:]
    recent_data = daily_returns[daily_returns['dt'].isin(recent_dates)]
    recent_data.set_index('dt', inplace=True)
    recent_data = recent_data.sort_index()
    return recent_data


def get_out_sample_curve(wb: WeightBacktest, out_sample_sdt: str) -> Dict[str, List]:
    """获取样本外累计收益曲线数据
    
    :param wb: WeightBacktest实例
    :param out_sample_sdt: 样本外开始时间
    :return: 图表数据字典
    """
    # 获取样本外数据
    returns_df = wb.daily_return[['date', "total"]].copy()
    returns_df['date'] = pd.to_datetime(returns_df['date'])
    returns_df.set_index('date', inplace=True)
    out_sample_data = returns_df[returns_df.index >= pd.to_datetime(out_sample_sdt)].copy()
    
    out_sample_data['累计收益率'] = out_sample_data['total'].cumsum()
    # 准备图表数据，转换为百分比格式
    chart_data = {
        "dates": out_sample_data.index.strftime('%Y-%m-%d').tolist(),
        "values": (out_sample_data['累计收益率'] * 100).round(2).tolist()  # 转换为百分比
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
                    "content": f"**最新累计收益率**: {curve_data['values'][-1]:.2f}%"
                },
                {
                    "tag": "chart",
                    "aspect_ratio": "16:9",
                    "chart_spec": _create_chart_spec(curve_data)
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


def _create_chart_spec(curve_data: Dict[str, List]) -> Dict[str, Any]:
    """创建VChart规格的累计收益曲线图表，完全按照飞书文档格式
    
    :param curve_data: 曲线数据
    :return: VChart图表配置
    """
    # 构建VChart数据格式，按照文档使用 time 和 value 字段
    chart_data = []
    for date, value in zip(curve_data['dates'], curve_data['values']):
        chart_data.append({
            "time": date,  # 使用 time 字段，与文档示例一致
            "value": value
        })
    
    # VChart折线图配置，完全按照飞书文档格式
    chart_spec = {
        "type": "line",
        "title": {
            "text": "累计收益曲线"
        },
        "data": {
            "values": chart_data
        },
        "xField": "time",  # 对应 time 字段
        "yField": "value"  # 对应 value 字段
    }
    
    return chart_spec


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
    :param kwargs: 其他参数，参考 WeightBacktest
    :return: None
    
    example
    ==============
    from czsc import mock
    dfw = mock.generate_klines_with_weights(seed=1234)
    feishu_key = "97ef04e5-8888-499e-a99f-58ec30b05283"
    push_strategy_latest(strategy="测试策略", dfw=dfw, feishu_key=feishu_key)
    
    """
    from czsc.fsa import push_card
    
    wb = WeightBacktest(dfw, **kwargs)
    recent_returns = calculate_recent_returns(wb, days=10)
    curve_data = get_out_sample_curve(wb, out_sample_sdt)
    card = create_feishu_card(strategy, out_sample_sdt, recent_returns, curve_data)
    push_card(card=card, key=feishu_key)
