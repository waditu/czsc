import czsc
import pandas as pd
from typing import Dict, List, Any


class WeightBacktestCard:
    """策略回测结果飞书卡片构建类"""
    
    def __init__(self, strategy_name: str, wb: czsc.WeightBacktest, out_sample_sdt: str = "20250101", describe: str = ""):
        """
        :param strategy_name: 策略名称
        :param wb: WeightBacktest实例
        :param out_sample_sdt: 样本外开始时间
        :param describe: 策略描述
        """
        self.strategy_name = strategy_name
        self.wb = wb
        self.out_sample_sdt = out_sample_sdt
        self.describe = describe if describe else f"{strategy_name} 在样本外时间 {out_sample_sdt} 之后的最新表现"
        
    def build(self) -> Dict[str, Any]:
        """构建飞书卡片数据"""
        recent_returns = self._calculate_recent_returns()
        stats_df = self._get_strategy_stats()
        chart_data = self._get_out_sample_curve()
        
        # 获取最新累计收益率
        latest_return = "N/A"
        if chart_data:
            for item in reversed(chart_data):
                if item['type'] == '总体':
                    latest_return = f"{item['value']:.2f}%"
                    break
        
        elements = []
        elements.append({"tag": "markdown", "content": f"**描述**: {self.describe}"})
        elements.append({"tag": "hr"})
        elements.append({"tag": "markdown", "content": "### 1.策略绩效指标"})
        elements.append(self._build_stats_section(stats_df))
        elements.append({"tag": "hr"})
        
        elements.append({"tag": "markdown", "content": "### 2.累计收益曲线"})
        elements.append({"tag": "markdown", "content": f"**最新累计收益率**: {latest_return}"})
        elements.append(self._build_curve_section(chart_data))
        elements.append({"tag": "hr"})

        elements.append({"tag": "markdown", "content": "### 3.最近10个交易日收益"})
        elements.extend(self._build_recent_returns_section(recent_returns))
        
        card = {
            "schema": "2.0",
            "config": {"wide_screen_mode": True},
            "header": self._build_header(),
            "body": {"elements": elements}
        }
        return card

    def _calculate_recent_returns(self, days: int = 10) -> pd.DataFrame:
        """计算最近N个交易日的收益"""
        daily_returns = self.wb.daily_return
        daily_returns.rename(columns={'date': 'dt'}, inplace=True)
        daily_returns['dt'] = pd.to_datetime(daily_returns['dt'])
        
        recent_dates = sorted(daily_returns['dt'].unique())[-days:]
        recent_data = daily_returns[daily_returns['dt'].isin(recent_dates)]
        recent_data.set_index('dt', inplace=True)
        recent_data = recent_data.sort_index()
        
        # 转置表格，日期作为列名
        df_t = recent_data.T
        df_t.columns = [d.strftime('%m-%d') for d in df_t.columns]
        return df_t

    def _get_out_sample_curve(self) -> List[Dict[str, Any]]:
        """获取样本外累计收益曲线数据"""
        df_total = self.wb.daily_return[['date', "total"]].copy().rename(columns={'total': '总体'})
        df_long = self.wb.long_daily_return[['date', "total"]].copy().rename(columns={'total': '多头'})
        df_short = self.wb.short_daily_return[['date', "total"]].copy().rename(columns={'total': '空头'})
        df_bench = self.wb.alpha[['date', '基准']].copy()
        
        df = df_total.merge(df_long, on='date', how='left')\
            .merge(df_short, on='date', how='left')\
            .merge(df_bench, on='date', how='left')
            
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        
        out_sample_data = df[df.index >= pd.to_datetime(self.out_sample_sdt)].copy()
        
        cols = ['总体', '多头', '空头', '基准']
        for col in cols:
            if col in out_sample_data.columns:
                out_sample_data[col] = out_sample_data[col].fillna(0).cumsum()
        
        chart_data = []
        for date, row in out_sample_data.iterrows():
            date_str = date.strftime('%Y-%m-%d')
            for col in cols:
                if col in row:
                    chart_data.append({
                        "time": date_str,
                        "type": col,
                        "value": round(row[col] * 100, 2)
                    })
        return chart_data

    def _get_strategy_stats(self) -> pd.DataFrame:
        """获取策略绩效指标"""
        stats = self.wb.stats
        key_map = {
            "年化": "年化收益",
            "夏普": "夏普比率",
            "最大回撤": "最大回撤",
            "卡玛": "卡玛比率",
            "日胜率": "日胜率",
            "盈亏平衡点": "盈亏平衡点"
        }
        
        data = []
        for k, v in key_map.items():
            if k in stats:
                val = stats[k]
                if isinstance(val, (int, float)):
                    if k in ["年化", "最大回撤", "日胜率", "盈亏平衡点"]:
                        val_str = f"{val*100:.2f}%"
                    else:
                        val_str = f"{val:.2f}"
                else:
                    val_str = str(val)
                data.append({"指标": v, "数值": val_str})
        return pd.DataFrame(data)

    def _build_header(self) -> Dict[str, Any]:
        """构建卡片头部"""
        return {
            "title": {
                "tag": "plain_text",
                "content": f"{self.strategy_name} - 策略最新表现"
            },
            "subtitle": {
                "tag": "plain_text",
                "content": f"样本外开始时间: {self.out_sample_sdt}"
            },
            "template": "blue"
        }

    def _build_recent_returns_section(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """构建最近收益表格部分"""
        return [{
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
                            "content": self._format_returns_table(df)
                        }
                    ]
                }
            ]
        }]

    def _build_stats_section(self, stats_df: pd.DataFrame) -> Dict[str, Any]:
        """构建绩效指标分栏展示"""
        columns = []
        items_per_col = (len(stats_df) + 2) // 3
        
        for i in range(3):
            start_idx = i * items_per_col
            end_idx = start_idx + items_per_col
            subset = stats_df.iloc[start_idx:end_idx]
            
            if subset.empty:
                continue
                
            elements = []
            for _, row in subset.iterrows():
                elements.append({
                    "tag": "markdown",
                    "content": f"**{row['指标']}**\n<font color='grey'>{row['数值']}</font>"
                })
                
            columns.append({
                "tag": "column",
                "width": "weighted",
                "weight": 1,
                "elements": elements
            })
            
        return {
            "tag": "column_set",
            "flex_mode": "stretch",
            "columns": columns
        }

    def _build_curve_section(self, chart_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """构建累计收益曲线部分"""
        return {
            "tag": "chart",
            "aspect_ratio": "16:9",
            "chart_spec": self._create_chart_spec(chart_data)
        }
        
    @staticmethod
    def _format_returns_table(df: pd.DataFrame) -> str:
        """将DataFrame格式化为Markdown表格"""
        lines = []
        headers = ["标的"] + [str(col) for col in df.columns]
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        
        for idx, row in df.iterrows():
            cells = [str(idx)]
            for col in df.columns:
                value = row[col]
                if isinstance(value, (int, float)):
                    if value >= 0:
                        cells.append(f"<font color='green'>+{value:.2f}%</font>")
                    else:
                        cells.append(f"<font color='red'>{value:.2f}%</font>")
                else:
                    cells.append(str(value))
            lines.append("| " + " | ".join(cells) + " |")
        return "\n".join(lines)
        
    @staticmethod
    def _create_chart_spec(chart_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """创建VChart规格的累计收益曲线图表"""
        mark_point_data = [
            {
                "type": "max", 
                "name": "最大值",
                "label": {"visible": True, "style": {"fill": "red"}}
            },
            {
                "type": "min", 
                "name": "最小值",
                "label": {"visible": True, "style": {"fill": "green"}}
            }
        ]
        
        last_points = {}
        for item in chart_data:
            last_points[item['type']] = item
            
        for s_type, item in last_points.items():
            mark_point_data.append({
                "coord": [item['time'], item['value']],
                "name": "最新值",
                "label": {
                    "visible": True,
                    "text": f"{item['value']}",
                    "position": "top",
                    "style": {"fill": "black"}
                },
                "symbolSize": 3
            })

        return {
            "type": "line",
            "title": {"text": "累计收益曲线"},
            "data": {"values": chart_data},
            "xField": "time",
            "yField": "value",
            "seriesField": "type",
            "point": {"visible": False},
            "label": {"visible": False},
            "legends": {"visible": True, "orient": "bottom"},
            "markPoint": {
                "data": mark_point_data,
                "itemContent": {"offsetY": -10}
            }
        }


def push_strategy_latest(strategy: str, dfw: pd.DataFrame, feishu_key: str, out_sample_sdt="20250101", **kwargs):
    """推送策略最新表现到飞书群

    :param strategy: 策略名称
    :param dfw: 标准持仓权重数据，包含 'dt'、'symbol'、weight', 'price' 四列
    :param feishu_key: 飞书机器人 key
    :param out_sample_sdt: 样本外开始时间，默认值 '20250101'
    :param kwargs: 其他参数，参考 czsc.WeightBacktest
    :return:
    """
    try:
        from czsc.fsa import push_card
        dfw['dt'] = pd.to_datetime(dfw['dt'])
        
        wb = czsc.WeightBacktest(dfw, **kwargs)
        card_builder = WeightBacktestCard(strategy, wb, out_sample_sdt)
        card = card_builder.build()
        push_card(card=card, key=feishu_key)
        # success = send_to_feishu(card, feishu_key)
        return True
        
    except Exception as e:
        print(f"推送过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_push_strategy_latest():
    """测试推送策略最新表现到飞书群"""
    dfw = czsc.mock.generate_klines_with_weights(seed=1234)
    feishu_key = "97ef04e5-1dea-9999-a99f-58ec30b05283"
    push_strategy_latest(strategy="测试策略", dfw=dfw, feishu_key=feishu_key)
