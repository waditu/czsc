import pandas as pd
from typing import Dict, List, Any


class StrategyCard:
    """策略回测结果飞书卡片构建类"""
    
    def __init__(self, strategy_name: str, dfw: pd.DataFrame, out_sample_sdt: str = "20250101", describe: str = "", **kwargs):
        """
        :param strategy_name: 策略名称
        :param dfw: 包含权重和价格数据的DataFrame，必须包含 'dt'、'symbol'、'weight'、'price' 四列
        :param out_sample_sdt: 样本外开始时间
        :param describe: 策略描述
        """
        from czsc import WeightBacktest
                
        fee_rate = kwargs.get('fee_rate', 0.0)
        digits = kwargs.get('digits', 3)
        weight_type = kwargs.get('weight_type', 'ts')
        yearly_days = kwargs.get('yearly_days', 252)
        self.dfw = dfw[['dt', 'symbol', 'weight', 'price']].copy()
        self.dfw = self.dfw[self.dfw['dt'] >= pd.to_datetime(out_sample_sdt)].copy().reset_index(drop=True)
        
        self.strategy_name = strategy_name
        self.wb = WeightBacktest(self.dfw.copy(), fee_rate=fee_rate, digits=digits, weight_type=weight_type, yearly_days=yearly_days)
        self.out_sample_sdt = out_sample_sdt
        pre_describe = f"{strategy_name} 在样本外时间 {out_sample_sdt} 之后的最新表现；回测参数："
        pre_describe += f"\n手续费率 {fee_rate}, 权重小数位数 {digits}, 权重类型 {weight_type}, 年交易日 {yearly_days}。"
        self.describe = pre_describe + ("\n" + describe if describe else "")
        self.latest_weights = dfw.sort_values("dt").groupby("symbol").tail(1).reset_index(drop=True)
        
    def build(self) -> Dict[str, Any]:
        """构建飞书卡片数据"""
        stats_df = self._get_strategy_stats()
        chart_data = self._get_out_sample_curve()
        latest_positions = self._get_latest_positions()
        
        # 获取最新累计收益率
        latest_return = "N/A"
        if chart_data:
            for item in reversed(chart_data):
                if item['type'] == '总体':
                    latest_return = f"{item['value']:.2f}%"
                    break
        
        elements = []
        elements.append({"tag": "markdown", "content": f"{self.describe}"})
        elements.append({"tag": "hr"})
        elements.append({"tag": "markdown", "content": "### 1.策略绩效指标"})
        elements.append(self._build_stats_section(stats_df))
        elements.append({"tag": "hr"})
        
        elements.append({"tag": "markdown", "content": "### 2.最新持仓明细"})
        elements.extend(self._build_positions_section(latest_positions))
        elements.append({"tag": "hr"})
        
        elements.append({"tag": "markdown", "content": "### 3.累计收益曲线"})
        elements.append({"tag": "markdown", "content": f"**最新累计收益率**: {latest_return}"})
        elements.append(self._build_curve_section(chart_data))
        elements.append({"tag": "hr"})

        # 第4部分：最近若干交易日收益。仅在持仓品种数不超过30时展示，且只看最近3个交易日
        try:
            include_recent = len(latest_positions) <= 30
        except Exception:
            include_recent = True

        if include_recent:
            recent_returns = self._calculate_recent_returns(days=3)
            elements.append({"tag": "markdown", "content": "### 4.最近3个交易日收益"})
            elements.extend(self._build_recent_returns_section(recent_returns))
        
        card = {
            "schema": "2.0",
            "config": {"wide_screen_mode": True},
            "header": self._build_header(),
            "body": {"elements": elements}
        }
        return card

    def _get_latest_positions(self) -> pd.DataFrame:
        """获取最新持仓"""
        df = self.dfw.copy()
        if df.empty:
            return pd.DataFrame(columns=['dt', 'symbol', 'weight', 'price'])
            
        # 每个品种的最新时间可能不一样，按品种分组取最新
        latest_pos = df.sort_values('dt').groupby('symbol').tail(1)
        
        # 过滤掉权重为0的
        latest_pos = latest_pos[latest_pos['weight'] != 0]
        return latest_pos[['dt', 'symbol', 'weight', 'price']].reset_index(drop=True)

    def _calculate_recent_returns(self, days: int = 3) -> pd.DataFrame:
        """计算最近N个交易日的收益（默认最近3个交易日）"""
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
            "年化波动率": "年化波动率",
            "单笔收益": "单笔收益",
            "持仓K线数": "持仓K线数",
            "交易胜率": "交易胜率",
            "多头占比": "多头占比",
            "空头占比": "空头占比",
            "开始日期": "开始日期",
            "结束日期": "结束日期",
        }
        
        data = []
        for k, v in key_map.items():
            if k in stats:
                val = stats[k]
                if isinstance(val, (int, float)):
                    if k in ["年化", "最大回撤", "日胜率", "年化波动率", "交易胜率", "多头占比", "空头占比"]:
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

    def _build_positions_section(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """构建最新持仓表格部分"""
        if df.empty:
            return [{
                "tag": "markdown",
                "content": "当前无持仓"
            }]
            
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
                            "content": self._format_positions_table(df)
                        }
                    ]
                }
            ]
        }]

    def _build_stats_section(self, stats_df: pd.DataFrame) -> Dict[str, Any]:
        """构建绩效指标分栏展示"""
        columns = []
        items_per_col = (len(stats_df) + 4) // 5
        
        for i in range(5):
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
                        cells.append(f"<font color='green'>+{value * 100:.2f}%</font>")
                    else:
                        cells.append(f"<font color='red'>{value * 100:.2f}%</font>")
                else:
                    cells.append(str(value))
            lines.append("| " + " | ".join(cells) + " |")
        return "\n".join(lines)

    @staticmethod
    def _format_positions_table(df: pd.DataFrame) -> str:
        """将持仓DataFrame格式化为Markdown表格"""
        lines = []
        headers = ["时间", "标的", "权重", "价格"]
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        
        for _, row in df.iterrows():
            dt = row['dt'].strftime('%Y-%m-%d %H:%M') if isinstance(row['dt'], pd.Timestamp) else str(row['dt'])
            symbol = row['symbol']
            weight = row['weight']
            price = row['price']
            
            weight_str = f"{weight:.4f}"
            if weight > 0:
                weight_str = f"<font color='red'>{weight_str}</font>"
            elif weight < 0:
                weight_str = f"<font color='green'>{weight_str}</font>"
                
            lines.append(f"| {dt} | {symbol} | {weight_str} | {price:.2f} |")
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

        card_builder = StrategyCard(strategy, dfw, out_sample_sdt, **kwargs)
        card = card_builder.build()
        push_card(card=card, key=feishu_key)
        return True
        
    except Exception as e:
        print(f"推送过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_push_strategy_latest():
    """测试推送策略最新表现到飞书群"""
    import czsc
    dfw = czsc.mock.generate_klines_with_weights(seed=1234)
    feishu_key = "97ef04e5-1dea-499e-----58ec30b05283"
    push_strategy_latest(strategy="测试策略", dfw=dfw, feishu_key=feishu_key)
