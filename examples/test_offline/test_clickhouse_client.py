import sys

sys.path.insert(0, r"A:\ZB\git_repo\waditu\czsc")
import dotenv

dotenv.load_dotenv(r"A:\ZB\git_repo\offline\dealer\.env", override=True)

import czsc
import pandas as pd
from czsc import cwc
from rs_czsc import WeightBacktest


def test_create_tables():
    database = "czsc_strategy"

    czsc.cwc.init_tables(database=database)

    # 测试 set_metadata
    czsc.cwc.set_meta(
        "test_strategy",
        "D",
        "测试策略",
        "ZB",
        "2021-01-01",
        weight_type="ts",
        memo="测试",
        database=database,
    )

    # send_heartbeat(db, "test_strategy")
    meta = cwc.get_meta("test_strategy", database=database)

    # 清空 metas 表
    # db.command("TRUNCATE TABLE czsc_strategy.metas")

    # # 测试 publish_weights
    dfw = pd.read_feather(r"C:\Users\zengb\Downloads\weight_example.feather")

    dfw1 = dfw[dfw["dt"] < pd.to_datetime("2023-01-01")].copy()
    dfw2 = dfw[dfw["dt"] >= pd.to_datetime("2023-01-01")].copy()

    cwc.publish_weights(df=dfw1, strategy="test_strategy", batch_size=100000, database=database)
    cwc.publish_weights(df=dfw2, strategy="test_strategy", batch_size=100000, database=database)

    dfx = cwc.get_strategy_weights(strategy="test_strategy", sdt="2023-01-01", database=database)
    dfx = cwc.get_strategy_weights(
        strategy="test_strategy", sdt="2023-01-01", symbols=["ZZUR9001", "ZZSA9001"], database=database
    )

    dfx = cwc.get_latest_weights(strategy="test_strategy", database=database)
    dfw_latest = dfw[dfw["dt"] == dfw["dt"].max()].copy()
    assert dfx["dt"].max() == dfw_latest["dt"].max()
    assert round(dfx["weight"].sum(), 2) == round(dfw_latest["weight"].sum(), 2)

    # cwc.clear_strategy("test_strategy")

    dfw = pd.read_feather(r"C:\Users\zengb\Downloads\weight_example.feather")
    wb = WeightBacktest(dfw, digits=1, fee_rate=0.0000)
    daily = wb.daily_return.copy()
    dfd = pd.melt(daily, id_vars=["date"], var_name="symbol", value_name="returns")
    dfd["dt"] = pd.to_datetime(dfd["date"])
    dfd = dfd[["dt", "symbol", "returns"]]
    cwc.publish_returns(df=dfd, strategy="test_strategy", batch_size=100000, database=database)

    dfx = cwc.get_strategy_returns(strategy="test_strategy", sdt="2023-01-01", database=database)
    dfx = cwc.get_strategy_returns(
        strategy="test_strategy", sdt="2022-01-01", symbols=["ZZUR9001", "ZZSA9001"], database=database
    )
