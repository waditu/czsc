"""基于 Plotly 的 networkx 图绘制。

二阶段清理 PR-C 之后：

- ``KlineChart`` 类与 :func:`plot_czsc_chart` 已删除（参见
  ``docs/migration/cleanup-non-czsc-core.md`` 阶段二章节）。
- 缠论 K 线可视化统一改用 :mod:`czsc.utils.plotting.lightweight` 中的
  ``plot_czsc`` / ``plot_czsc_trader`` / ``plot_czsc_signals``。
- 本模块仅保留 :func:`plot_nx_graph`，渲染 ``networkx`` 图（节点 + 带权边）。

作者: zengbin93
邮箱: zeng_bin8888@163.com
创建时间: 2023/2/26 15:03
"""

from plotly import graph_objects as go


def plot_nx_graph(g, **kwargs) -> go.Figure:
    """使用 Plotly 绘制 ``nx.Graph`` 的图形

    采用 ``spring_layout`` 自动布局节点，边宽与节点大小可通过 kwargs 控制；同时把
    每条边的权重作为文字标签放在边的中点，正负权重用红绿区分。

    :param g: nx.Graph 对象
    :param kwargs: 其他参数
        - title: str，图表标题，默认 ``"Network graph made with Python"``
        - edge_width: float，边宽，默认 1.5
        - node_marker_size: float，节点大小，默认 10
    :return: plotly.graph_objs.Figure
    """
    import networkx as nx

    title = kwargs.get("title", "Network graph made with Python")
    edge_width = kwargs.get("edge_width", 1.5)
    node_marker_size = kwargs.get("node_marker_size", 10)

    # 通过 spring_layout 给每个节点分配二维坐标
    pos = nx.spring_layout(g)

    # 准备绘图数据：边起止点 + 权重
    edge_x = []
    edge_y = []
    edge_weights = []
    for edge in g.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
        edge_weights.append(f"{g[edge[0]][edge[1]]['weight']:.2f}")

    node_x = []
    node_y = []
    node_labels = []
    for node in g.nodes():
        node_x.append(pos[node][0])
        node_y.append(pos[node][1])
        node_labels.append(node)

    # 边：用线条 trace 表示
    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line={"width": edge_width, "color": "#888"},
        hoverinfo="none",
        mode="lines",
    )

    # 节点：用散点 trace 表示
    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers",
        hoverinfo="text",
        text=node_labels,  # 节点标签
        marker={
            "showscale": False,
            "color": "skyblue",
            "size": node_marker_size,
            "line_width": 0,
        },
    )

    # 计算每条边中点位置，作为权重文字的注释
    edge_annotations = []
    for edge in g.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        mid_x = (x0 + x1) / 2
        mid_y = (y0 + y1) / 2
        weight = f"{g[edge[0]][edge[1]]['weight']:.2f}"
        edge_annotations.append(
            {
                "x": mid_x,
                "y": mid_y,
                "text": weight,
                "showarrow": False,
                "font": {"size": 12, "color": "red" if float(weight) > 0 else "green"},
            }
        )

    # 组装最终 figure
    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            title=f"<br>{title}",
            titlefont_size=16,
            showlegend=False,
            hovermode="closest",
            margin={"b": 20, "l": 5, "r": 5, "t": 40},
            xaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
            yaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
            annotations=edge_annotations,  # 边的权重文字注释
        ),
    )

    return fig
