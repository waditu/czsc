# coding: utf-8
# from enum import Enum
from rs_czsc import (
    Mark, 
    Direction, 
    Freq, 
    Operate

)


__all__ = [
    "Mark",
    "Direction",
    "Freq",
    "Operate"
]


# class Operate(Enum):
#     # 持有状态
#     HL = "持多"  # Hold Long
#     HS = "持空"  # Hold Short
#     HO = "持币"  # Hold Other

#     # 多头操作
#     LO = "开多"  # Long Open
#     LE = "平多"  # Long Exit

#     # 空头操作
#     SO = "开空"  # Short Open
#     SE = "平空"  # Short Exit

#     def __str__(self):
#         return self.value
