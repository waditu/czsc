# coding: utf-8
import sys
import warnings

sys.path.insert(0, '.')
sys.path.insert(0, '..')
import os
import numpy as np
import pandas as pd
import random
import czsc
from czsc import plot

warnings.warn("czsc version is {}".format(czsc.__version__))

# cur_path = os.path.split(os.path.realpath(__file__))[0]
cur_path = "./test"

def test_heat_map():
    data = [{"x": "{}hour".format(i), "y": "{}day".format(j), "heat": random.randint(0, 50)}
            for i in range(24) for j in range(7)]
    x_label = ["{}hour".format(i) for i in range(24)]
    y_label = ["{}day".format(i) for i in range(7)]
    hm = plot.heat_map(data, x_label=x_label, y_label=y_label)




