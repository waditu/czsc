from czsc.data.jq import *
from pandas import DataFrame as df


def test_get_industry():
    # 获取指数下面股票信息
    print(get_index_stocks("000300.XSHG"))


def test_get_all_securities():
    # 获取基金
    data: df = get_all_securities(code="fund")
    data = data.drop_duplicates(keep="last")
    print(data)
    data.to_csv("d://data/all_fund.csv", encoding="utf-8-sig")


def test_get_all_index():
    # 获取指数
    data: df = get_all_securities("index")
    data.to_csv("d://data/allindex.csv", encoding="utf-8-sig")


def test_get_stock_by_index():
    # 根据指数获取股票
    print(get_index_stocks("399808.XSHE"))


def test_finantional():
    orderedDictList = get_share_basic("600329.XSHG")

