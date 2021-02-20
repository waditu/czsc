# coding: utf-8

from czsc.enum import Factors, Signals

def test_factors():
    for k, v in Factors.__members__.items():
        if k == "Other":
            continue
        assert k == v.value.split("~")[0], "{} - {}".format(k, v.value)

def test_signals():
    for k, v in Signals.__members__.items():
        if k == "Other":
            continue
        assert k == v.value.split("~")[0], "{} - {}".format(k, v.value)

