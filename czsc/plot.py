# coding: utf-8
"""
使用 pyecharts 定制绘图模块

"""

from pyecharts import options as opts
from pyecharts.charts import HeatMap, Grid
from pyecharts.options import HeatMapItem
from typing import List, Callable


def heat_map(data: List[dict],
             x_label: List[str] = None,
             y_label: List[str] = None,
             title: str = "热力图",
             width: str = "900px",
             height: str = "680px") -> HeatMap:
    """绘制热力图

    :param data: 用于绘制热力图的数据，示例如下
        [{'x': '0hour', 'y': '0day', 'heat': 11},
         {'x': '0hour', 'y': '1day', 'heat': 40},
         {'x': '0hour', 'y': '2day', 'heat': 38},
         {'x': '0hour', 'y': '3day', 'heat': 36},
         {'x': '0hour', 'y': '4day', 'heat': 11}]
    :param x_label: x轴标签
    :param y_label: y轴标签
    :param title: 图表标题
    :param width: 图表宽度
    :param height: 图表高度
    :return: 图表
    """

    value = [HeatMapItem(value=[s['x'], s['y'], s['heat']]) for s in data]
    heat = [s['heat'] for s in data]

    if not x_label:
        x_label = sorted(list(set([s['x'] for s in data])))

    if not y_label:
        y_label = sorted(list(set([s['y'] for s in data])))

    vis_map_opts = opts.VisualMapOpts(pos_left="90%", pos_top="20%", min_=min(heat), max_=max(heat))
    title_opts = opts.TitleOpts(title=title)
    init_opts = opts.InitOpts(page_title=title, width=width, height=height)
    dz_inside = opts.DataZoomOpts(False, "inside", xaxis_index=[0], range_start=80, range_end=100)
    dz_slider = opts.DataZoomOpts(True, "slider", xaxis_index=[0], pos_top="96%", pos_bottom="0%",
                                  range_start=80, range_end=100)
    legend_opts = opts.LegendOpts(is_show=False)

    hm = HeatMap(init_opts=init_opts)
    hm.add_xaxis(x_label)
    hm.add_yaxis("heat", y_label, value, label_opts=opts.LabelOpts(is_show=True, position="inside"))
    hm.set_global_opts(title_opts=title_opts, visualmap_opts=vis_map_opts, legend_opts=legend_opts,
                       xaxis_opts=opts.AxisOpts(grid_index=0), datazoom_opts=[dz_inside, dz_slider])
    return hm



