# coding: utf-8

import sys

sys.path.insert(0, '.')
sys.path.insert(0, '..')
from czsc.signals import check_jing


def test_check_jing():
    fd1 = {"start_dt": 0, "end_dt": 1, "power": 0, "direction": "up", "high": 0, "low": 0, "mode": "bi"}
    fd2 = {"start_dt": 1, "end_dt": 2, "power": 0, "direction": "up", "high": 0, "low": 0, "mode": "bi"}
    fd3 = {"start_dt": 2, "end_dt": 3, "power": 0, "direction": "up", "high": 0, "low": 0, "mode": "bi"}
    fd4 = {"start_dt": 4, "end_dt": 5, "power": 0, "direction": "up", "high": 0, "low": 0, "mode": "bi"}
    fd5 = {"start_dt": 5, "end_dt": 6, "power": 0, "direction": "up", "high": 0, "low": 0, "mode": "bi"}
