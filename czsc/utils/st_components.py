import czsc
import pandas as pd
import streamlit as st
import plotly.express as px


def show_daily_return(df, **kwargs):
    """用streamlit展示日收益"""
    assert df.index.dtype == 'datetime64[ns]', "index必须是datetime64[ns]类型, 请先使用 pd.to_datetime 进行转换"
    type_ = "持有日" if kwargs.get("none_zero", False) else "交易日"

    df = df.copy().fillna(0)
    stats = []
    for col in df.columns:
        col_stats = czsc.daily_performance([x for x in df[col] if x != 0]) if type_ == '持有日' else czsc.daily_performance(df[col])
        col_stats['日收益名称'] = col
        stats.append(col_stats)

    stats = pd.DataFrame(stats).set_index('日收益名称')
    fmt_cols = ['年化', '夏普', '最大回撤', '卡玛', '年化波动率', '非零覆盖']
    stats = stats.style.background_gradient(cmap='RdYlGn_r', axis=None).format('{:.4f}', subset=fmt_cols)

    df = df.cumsum()
    fig = px.line(df, y=df.columns.to_list(), title="日收益累计曲线")
    for col in kwargs.get("legend_only_cols", []):
        fig.update_traces(visible="legendonly", selector=dict(name=col))

    with st.container():
        st.subheader(f'{kwargs.get("title", "日收益表现评价")}（{type_}）')
        st.divider()
        st.dataframe(stats, use_container_width=True)
        st.plotly_chart(fig, use_container_width=True)
