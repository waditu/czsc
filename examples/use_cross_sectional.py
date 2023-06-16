# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/5/29 15:06
describe: 根据截面持仓信息，计算截面绩效
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '..')
import pandas as pd

from czsc.utils.cross import CrossSectionalPerformance

dfh = pd.read_feather(r"C:\Users\zengb\Downloads\截面分析样例数据.feather")
# 不使用杠杆进行截面分析
csp = CrossSectionalPerformance(dfh, max_total_weight=1)
# csp.report('不使用杠杆的表现.docx')
#
# # 使用一倍杠杆进行截面分析
# csp = CrossSectionalPerformance(dfh, max_total_weight=2)
# csp.report('使用1倍杠杆的表现.docx')
#



