# coding: utf-8

import sys

sys.path.insert(0, '.')
sys.path.insert(0, '..')
from czsc.analyze import check_jing, check_bei_chi, check_third_bs


def test_check_jing_up():
    fd1 = {"start_dt": 0, "end_dt": 1, "power": 5, "direction": "up", "high": 2, "low": 0, "mode": "bi"}
    fd2 = {"start_dt": 1, "end_dt": 2, "power": 4, "direction": "down", "high": 2, "low": 1, "mode": "bi"}
    fd3 = {"start_dt": 2, "end_dt": 3, "power": 3, "direction": "up", "high": 3, "low": 1, "mode": "bi"}
    fd4 = {"start_dt": 4, "end_dt": 5, "power": 2, "direction": "down", "high": 3, "low": 1.5, "mode": "bi"}
    fd5 = {"start_dt": 5, "end_dt": 6, "power": 1, "direction": "up", "high": 4, "low": 1.5, "mode": "bi"}

    j = check_jing(fd1, fd2, fd3, fd4, fd5)
    assert j['jing'] == "向上大井" and j['notes'] == '12345向上，5最高3次之1最低，力度上1大于3，3大于5'

    fd1 = {"start_dt": 0, "end_dt": 1, "power": 5, "direction": "up", "high": 2, "low": 0, "mode": "bi"}
    fd2 = {"start_dt": 1, "end_dt": 2, "power": 4, "direction": "down", "high": 2, "low": 1, "mode": "bi"}
    fd3 = {"start_dt": 2, "end_dt": 3, "power": 1, "direction": "up", "high": 3, "low": 1, "mode": "bi"}
    fd4 = {"start_dt": 4, "end_dt": 5, "power": 2, "direction": "down", "high": 3, "low": 1.5, "mode": "bi"}
    fd5 = {"start_dt": 5, "end_dt": 6, "power": 3, "direction": "up", "high": 4, "low": 1.5, "mode": "bi"}

    j = check_jing(fd1, fd2, fd3, fd4, fd5)
    assert j['jing'] == "向上小井" and j['notes'] == "12345向上，5最高3次之1最低，力度上1大于5，5大于3"

    fd1 = {"start_dt": 0, "end_dt": 1, "power": 5, "direction": "up", "high": 2, "low": 0, "mode": "bi"}
    fd2 = {"start_dt": 1, "end_dt": 2, "power": 4, "direction": "down", "high": 2, "low": 1, "mode": "bi"}
    fd3 = {"start_dt": 2, "end_dt": 3, "power": 1, "direction": "up", "high": 4, "low": 1, "mode": "bi"}
    fd4 = {"start_dt": 4, "end_dt": 5, "power": 2, "direction": "down", "high": 4, "low": 1.5, "mode": "bi"}
    fd5 = {"start_dt": 5, "end_dt": 6, "power": 3, "direction": "up", "high": 3, "low": 1.5, "mode": "bi"}

    j = check_jing(fd1, fd2, fd3, fd4, fd5)
    assert j['jing'] == "向上小井" and j['notes'] == "12345向上，3最高5次之1最低，力度上5的力度比1小"

    fd1 = {"start_dt": 0, "end_dt": 1, "power": 5, "direction": "up", "high": 2, "low": 0, "mode": "bi"}
    fd2 = {"start_dt": 1, "end_dt": 2, "power": 4, "direction": "down", "high": 2, "low": 1, "mode": "bi"}
    fd3 = {"start_dt": 2, "end_dt": 3, "power": 3, "direction": "up", "high": 3, "low": 1, "mode": "bi"}
    fd4 = {"start_dt": 4, "end_dt": 5, "power": 2, "direction": "down", "high": 3, "low": 2.5, "mode": "bi"}
    fd5 = {"start_dt": 5, "end_dt": 6, "power": 1, "direction": "up", "high": 4, "low": 2.5, "mode": "bi"}

    j = check_jing(fd1, fd2, fd3, fd4, fd5)
    assert j['jing'] == "向上小井" and j['notes'] == "12345类上涨趋势，力度依次降低"


def test_check_jing_down():
    fd1 = {"start_dt": 0, "end_dt": 1, "power": 5, "direction": "down", "high": 5, "low": 3, "mode": "bi"}
    fd2 = {"start_dt": 1, "end_dt": 2, "power": 4, "direction": "up", "high": 4, "low": 3, "mode": "bi"}
    fd3 = {"start_dt": 2, "end_dt": 3, "power": 3, "direction": "down", "high": 4, "low": 1, "mode": "bi"}
    fd4 = {"start_dt": 4, "end_dt": 5, "power": 2, "direction": "up", "high": 3.5, "low": 1, "mode": "bi"}
    fd5 = {"start_dt": 5, "end_dt": 6, "power": 1, "direction": "down", "high": 3.5, "low": 0.5, "mode": "bi"}

    j = check_jing(fd1, fd2, fd3, fd4, fd5)
    assert j['jing'] == "向下大井" and j['notes'] == "12345向下，5最低3次之1最高，力度上1大于3，3大于5"

    fd1 = {"start_dt": 0, "end_dt": 1, "power": 5, "direction": "down", "high": 5, "low": 3, "mode": "bi"}
    fd2 = {"start_dt": 1, "end_dt": 2, "power": 4, "direction": "up", "high": 4, "low": 3, "mode": "bi"}
    fd3 = {"start_dt": 2, "end_dt": 3, "power": 3, "direction": "down", "high": 4, "low": 0.5, "mode": "bi"}
    fd4 = {"start_dt": 4, "end_dt": 5, "power": 2, "direction": "up", "high": 3.5, "low": 0.5, "mode": "bi"}
    fd5 = {"start_dt": 5, "end_dt": 6, "power": 1, "direction": "down", "high": 3.5, "low": 1, "mode": "bi"}

    j = check_jing(fd1, fd2, fd3, fd4, fd5)
    assert j['jing'] == "向下小井" and j['notes'] == "12345向下，3最低5次之1最高，力度上5的力度比1小"

    fd1 = {"start_dt": 0, "end_dt": 1, "power": 5, "direction": "down", "high": 5, "low": 3, "mode": "bi"}
    fd2 = {"start_dt": 1, "end_dt": 2, "power": 4, "direction": "up", "high": 4, "low": 3, "mode": "bi"}
    fd3 = {"start_dt": 2, "end_dt": 3, "power": 1, "direction": "down", "high": 4, "low": 1, "mode": "bi"}
    fd4 = {"start_dt": 4, "end_dt": 5, "power": 2, "direction": "up", "high": 3.5, "low": 1, "mode": "bi"}
    fd5 = {"start_dt": 5, "end_dt": 6, "power": 3, "direction": "down", "high": 3.5, "low": 0.5, "mode": "bi"}

    j = check_jing(fd1, fd2, fd3, fd4, fd5)
    assert j['jing'] == "向下小井" and j['notes'] == "12345向下，5最低3次之1最高，力度上1大于5，5大于3"

    fd1 = {"start_dt": 0, "end_dt": 1, "power": 5, "direction": "down", "high": 5, "low": 3, "mode": "bi"}
    fd2 = {"start_dt": 1, "end_dt": 2, "power": 4, "direction": "up", "high": 4, "low": 3, "mode": "bi"}
    fd3 = {"start_dt": 2, "end_dt": 3, "power": 3, "direction": "down", "high": 4, "low": 1, "mode": "bi"}
    fd4 = {"start_dt": 4, "end_dt": 5, "power": 2, "direction": "up", "high": 2, "low": 1, "mode": "bi"}
    fd5 = {"start_dt": 5, "end_dt": 6, "power": 1, "direction": "down", "high": 2, "low": 0.5, "mode": "bi"}

    j = check_jing(fd1, fd2, fd3, fd4, fd5)
    assert j['jing'] == "向下小井" and j['notes'] == "12345类下跌趋势，力度依次降低"


def test_check_bei_chi():
    fd1 = {"start_dt": 0, "end_dt": 1, "power": 5, "direction": "up", "high": 2, "low": 0, "mode": "bi"}
    fd2 = {"start_dt": 1, "end_dt": 2, "power": 4, "direction": "down", "high": 2, "low": 1, "mode": "bi"}
    fd3 = {"start_dt": 2, "end_dt": 3, "power": 3, "direction": "up", "high": 3, "low": 1, "mode": "bi"}
    fd4 = {"start_dt": 4, "end_dt": 5, "power": 2, "direction": "down", "high": 3, "low": 1.5, "mode": "bi"}
    fd5 = {"start_dt": 5, "end_dt": 6, "power": 1, "direction": "up", "high": 4, "low": 1.5, "mode": "bi"}

    bc = check_bei_chi(fd1, fd2, fd3, fd4, fd5)
    assert bc['bc'] == "向上趋势背驰" and bc['notes'] == '12345向上，234构成中枢，5最高，力度上1大于5'

    fd1 = {"start_dt": 0, "end_dt": 1, "power": 5, "direction": "up", "high": 2, "low": 0, "mode": "bi"}
    fd2 = {"start_dt": 1, "end_dt": 2, "power": 4, "direction": "down", "high": 2, "low": 1, "mode": "bi"}
    fd3 = {"start_dt": 2, "end_dt": 3, "power": 3, "direction": "up", "high": 3, "low": 1, "mode": "bi"}
    fd4 = {"start_dt": 4, "end_dt": 5, "power": 2, "direction": "down", "high": 3, "low": 2.5, "mode": "bi"}
    fd5 = {"start_dt": 5, "end_dt": 6, "power": 1, "direction": "up", "high": 4, "low": 2.5, "mode": "bi"}

    bc = check_bei_chi(fd1, fd2, fd3, fd4, fd5)
    assert bc['bc'] == "向上盘整背驰" and bc['notes'] == '12345向上，234不构成中枢，5最高，力度上1大于5'

    fd1 = {"start_dt": 0, "end_dt": 1, "power": 5, "direction": "down", "high": 5, "low": 3, "mode": "bi"}
    fd2 = {"start_dt": 1, "end_dt": 2, "power": 4, "direction": "up", "high": 4, "low": 3, "mode": "bi"}
    fd3 = {"start_dt": 2, "end_dt": 3, "power": 3, "direction": "down", "high": 4, "low": 1, "mode": "bi"}
    fd4 = {"start_dt": 4, "end_dt": 5, "power": 2, "direction": "up", "high": 3.5, "low": 1, "mode": "bi"}
    fd5 = {"start_dt": 5, "end_dt": 6, "power": 1, "direction": "down", "high": 3.5, "low": 0.5, "mode": "bi"}

    bc = check_bei_chi(fd1, fd2, fd3, fd4, fd5)
    assert bc['bc'] == "向下趋势背驰" and bc['notes'] == "12345向下，234构成中枢，5最低，力度上1大于5"

    fd1 = {"start_dt": 0, "end_dt": 1, "power": 5, "direction": "down", "high": 5, "low": 3, "mode": "bi"}
    fd2 = {"start_dt": 1, "end_dt": 2, "power": 4, "direction": "up", "high": 4, "low": 3, "mode": "bi"}
    fd3 = {"start_dt": 2, "end_dt": 3, "power": 3, "direction": "down", "high": 4, "low": 2, "mode": "bi"}
    fd4 = {"start_dt": 4, "end_dt": 5, "power": 2, "direction": "up", "high": 2.5, "low": 2, "mode": "bi"}
    fd5 = {"start_dt": 5, "end_dt": 6, "power": 1, "direction": "down", "high": 2.5, "low": 0.5, "mode": "bi"}

    bc = check_bei_chi(fd1, fd2, fd3, fd4, fd5)
    assert bc['bc'] == "向下盘整背驰" and bc['notes'] == "12345向下，234不构成中枢，5最低，力度上1大于5"


def test_check_third_bs():
    fd1 = {"start_dt": 0, "end_dt": 1, "power": 5, "direction": "down", "high": 3, "low": 1, "mode": "bi"}
    fd2 = {"start_dt": 1, "end_dt": 2, "power": 4, "direction": "up", "high": 2, "low": 1, "mode": "bi"}
    fd3 = {"start_dt": 2, "end_dt": 3, "power": 3, "direction": "down", "high": 2, "low": 1.5, "mode": "bi"}
    fd4 = {"start_dt": 4, "end_dt": 5, "power": 9, "direction": "up", "high": 5, "low": 1.5, "mode": "bi"}
    fd5 = {"start_dt": 5, "end_dt": 6, "power": 1, "direction": "down", "high": 5, "low": 4, "mode": "bi"}

    third_bs = check_third_bs(fd1, fd2, fd3, fd4, fd5)
    assert third_bs['third_bs'] == "三买" and third_bs['notes'] == '前三段构成中枢，第四段向上离开，第五段不回中枢'

    fd1 = {"start_dt": 0, "end_dt": 1, "power": 5, "direction": "up", "high": 8, "low": 7, "mode": "bi"}
    fd2 = {"start_dt": 1, "end_dt": 2, "power": 4, "direction": "down", "high": 8, "low": 6, "mode": "bi"}
    fd3 = {"start_dt": 2, "end_dt": 3, "power": 3, "direction": "up", "high": 9, "low": 6, "mode": "bi"}
    fd4 = {"start_dt": 4, "end_dt": 5, "power": 9, "direction": "down", "high": 9, "low": 3, "mode": "bi"}
    fd5 = {"start_dt": 5, "end_dt": 6, "power": 1, "direction": "up", "high": 5, "low": 3, "mode": "bi"}

    third_bs = check_third_bs(fd1, fd2, fd3, fd4, fd5)
    assert third_bs['third_bs'] == "三卖" and third_bs['notes'] == '前三段构成中枢，第四段向下离开，第五段不回中枢'

