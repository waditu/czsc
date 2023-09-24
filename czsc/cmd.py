# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/10/14 22:54
describe: 命令行工具集

https://click.palletsprojects.com/en/8.0.x/quickstart/
"""
import click


@click.group()
def czsc():
    """CZSC 命令行工具"""
    pass


@czsc.command()
def aphorism():
    """随机输出一条缠中说禅良言警句"""
    from czsc.aphorism import print_one

    print_one()
