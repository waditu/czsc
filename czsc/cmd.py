# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/10/14 22:54
describe: 命令行工具集

https://click.palletsprojects.com/en/8.0.x/quickstart/
"""
import click
import pandas as pd
from czsc.aphorism import print_one


@click.group()
def czsc():
    pass


@czsc.command()
def aphorism():
    """随机输出一条缠中说禅良言警句"""
    print_one()


