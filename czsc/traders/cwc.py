# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2024/12/30 15:19
describe: 基于 clickhouse 的策略持仓权重管理，cwc 为 clickhouse weights client 的缩写

推荐在环境变量中设置 clickhouse 的连接信息，如下：

- CLICKHOUSE_HOST: 服务器地址，如 127.0.0.1
- CLICKHOUSE_PORT: 服务器端口，如 9000
- CLICKHOUSE_USER: 用户名, 如 default
- CLICKHOUSE_PASS: 密码, 如果没有密码，可以设置为空字符串

"""
# pip install clickhouse_connect -i https://pypi.tuna.tsinghua.edu.cn/simple
import os
import loguru
import pandas as pd
import clickhouse_connect as ch
from clickhouse_connect.driver import Client
from typing import Optional


def __db_from_env():
    host = os.getenv("CLICKHOUSE_HOST")
    port = int(os.getenv("CLICKHOUSE_PORT"))
    user = os.getenv("CLICKHOUSE_USER")
    password = os.getenv("CLICKHOUSE_PASS")

    if not (host and port and user and password):
        raise ValueError(
            """
        请设置环境变量：CLICKHOUSE_HOST, CLICKHOUSE_PORT, CLICKHOUSE_USER, CLICKHOUSE_PASS
        
        - CLICKHOUSE_HOST: 服务器地址，如 127.0.0.1
        - CLICKHOUSE_PORT: 服务器端口，如 9000
        - CLICKHOUSE_USER: 用户名, 如 default
        - CLICKHOUSE_PASS: 密码, 如果没有密码，可以设置为空字符串
        """
        )

    db = ch.get_client(host=host, port=port, user=user, password=password)
    return db


def init_tables(db: Optional[Client] = None, database="czsc_strategy", **kwargs):
    """
    创建数据库表

    :param db: clickhouse_connect.driver.Client, 数据库连接
    :param database: str, 数据库名称
    :param kwargs: dict, 数据表名和建表语句
    :return: None
    """
    db = db or __db_from_env()

    # 创建数据库
    db.command(f"CREATE DATABASE IF NOT EXISTS {database}")

    metas_table = f"""
    CREATE TABLE IF NOT EXISTS {database}.metas (
        strategy String NOT NULL,                      -- 策略名（唯一且不能为空）
        base_freq String,                              -- 周期
        description String,                            -- 描述
        author String,                                 -- 作者
        outsample_sdt DateTime,                        -- 样本外起始时间
        create_time DateTime,                          -- 策略入库时间
        update_time DateTime,                          -- 策略更新时间
        heartbeat_time DateTime,                       -- 最后一次心跳时间
        weight_type String,                            -- 策略上传的权重类型，ts 或 cs
        memo String                                    -- 策略备忘信息
    ) 
    ENGINE = ReplacingMergeTree()
    ORDER BY strategy;
    """

    weights_table = f"""
    CREATE TABLE IF NOT EXISTS {database}.weights (
        dt DateTime,                     -- 持仓权重时间
        symbol String,                   -- 符号（例如，股票代码或其他标识符）
        weight Float64,                  -- 策略持仓权重值
        strategy String,                 -- 策略名称
        update_time DateTime             -- 持仓权重更新时间
    ) 
    ENGINE = ReplacingMergeTree()
    ORDER BY (strategy, dt, symbol);
    """

    latest_weights_view = f"""
    CREATE VIEW IF NOT EXISTS {database}.latest_weights AS
        SELECT
           strategy,
           symbol,
           argMax(dt, dt) as latest_dt,
           argMax(weight, dt) as latest_weight,
           argMax(update_time, dt) as latest_update_time
        FROM {database}.weights
        GROUP BY strategy, symbol;
    """

    returns_table = f"""
    CREATE TABLE IF NOT EXISTS {database}.returns (
        dt DateTime,                     -- 时间
        symbol String,                   -- 符号（例如，股票代码或其他标识符）
        returns Float64,                 -- 策略收益，从上一个 dt 到当前 dt 的收益
        strategy String,                 -- 策略名称
        update_time DateTime             -- 更新时间
    )
    ENGINE = ReplacingMergeTree()
    ORDER BY (strategy, dt, symbol);
    """

    db.command(metas_table)
    db.command(weights_table)
    db.command(latest_weights_view)
    db.command(returns_table)

    print("数据表创建成功！")


def get_meta(strategy, db: Optional[Client] = None, database="czsc_strategy", logger=loguru.logger) -> dict:
    """获取策略元数据

    :param db: clickhouse_connect.driver.Client, 数据库连接
    :param strategy: str, 策略名称
    :param database: str, 数据库名称
    :param logger: loguru.logger, 日志记录器
    :return: pd.DataFrame
    """
    db = db or __db_from_env()

    query = f"""
    SELECT * FROM {database}.metas final WHERE strategy = '{strategy}'
    """
    df = db.query_df(query)
    if df.empty:
        logger.warning(f"策略 {strategy} 不存在元数据")
        return {}
    else:
        assert len(df) == 1, f"策略 {strategy} 存在多条元数据，请检查"
        return df.iloc[0].to_dict()


def get_all_metas(db: Optional[Client] = None, database="czsc_strategy") -> pd.DataFrame:
    """获取所有策略元数据

    :param db: clickhouse_connect.driver.Client, 数据库连接
    :param database: str, 数据库名称
    :return: pd.DataFrame
    """
    db = db or __db_from_env()
    df = db.query_df(f"SELECT * FROM {database}.metas final")
    return df


def set_meta(
    strategy,
    base_freq,
    description,
    author,
    outsample_sdt,
    weight_type="ts",
    memo="",
    logger=loguru.logger,
    overwrite=False,
    database="czsc_strategy",
    db: Optional[Client] = None,
):
    """设置策略元数据

    :param strategy: str, 策略名
    :param base_freq: str, 周期
    :param description: str, 描述
    :param author: str, 作者
    :param outsample_sdt: str, 样本外起始时间
    :param weight_type: str, 权重类型，ts 或 cs
    :param memo: str, 备注
    :param logger: loguru.logger, 日志记录器
    :param overwrite: bool, 是否覆盖已有元数据
    :param database: str, 数据库名称
    :param db: clickhouse_connect.driver.Client, 数据库连接
    :return: None
    """
    db = db or __db_from_env()

    outsample_sdt = pd.to_datetime(outsample_sdt).tz_localize(None)
    current_time = pd.to_datetime("now").tz_localize(None)
    meta = get_meta(db=db, strategy=strategy, database=database)

    if not overwrite and meta:
        logger.warning(f"策略 {strategy} 已存在元数据，如需更新请设置 overwrite=True")
        return

    # create_time 在任何情况下都不会被覆盖，只有元数据不存在时才会设置
    create_time = current_time if not meta else pd.to_datetime(meta["create_time"])

    # 构建DataFrame用于插入
    df = pd.DataFrame(
        [
            {
                "strategy": strategy,
                "base_freq": base_freq,
                "description": description,
                "author": author,
                "outsample_sdt": outsample_sdt,
                "create_time": create_time,
                "update_time": current_time,
                "heartbeat_time": current_time,
                "weight_type": weight_type,
                "memo": memo,
            }
        ]
    )
    res = db.insert_df(f"{database}.metas", df)
    logger.info(f"{strategy} set_metadata: {res.summary}")


def __send_heartbeat(db: ch.driver.Client, strategy, logger=loguru.logger, database="czsc_strategy"):
    """发送心跳

    :param db: clickhouse_connect.driver.Client, 数据库连接
    :param strategy: str, 策略名称
    :param database: str, 数据库名称
    :param logger: loguru.logger, 日志记录器
    :return: None
    """
    try:
        meta = get_meta(db=db, strategy=strategy)
        if not meta:
            logger.warning(f"策略 {strategy} 不存在元数据，无法发送心跳")
            return

        current_time = pd.to_datetime("now").strftime("%Y-%m-%d %H:%M:%S")
        db.command(
            f"ALTER TABLE {database}.metas UPDATE heartbeat_time = '{current_time}' WHERE strategy = '{strategy}'"
        )
        logger.info(f"策略 {strategy} 发送心跳成功")

    except Exception as e:
        logger.error(f"发送心跳失败: {e}")
        raise


def get_strategy_weights(
    strategy, db: Optional[Client] = None, sdt=None, edt=None, symbols=None, database="czsc_strategy"
):
    """获取策略持仓权重

    :param db: clickhouse_connect.driver.Client, 数据库连接
    :param strategy: str, 策略名称
    :param sdt: str, 开始时间
    :param edt: str, 结束时间
    :param symbols: list, 符号列表
    :param database: str, 数据库名称
    :return: pd.DataFrame
    """
    db = db or __db_from_env()

    query = f"""
    SELECT * FROM {database}.weights final WHERE strategy = '{strategy}'
    """
    if sdt:
        query += f" AND dt >= '{sdt}'"
    if edt:
        query += f" AND dt <= '{edt}'"
    if symbols:
        if isinstance(symbols, str):
            symbols = [symbols]
        symbol_str = ", ".join([f"'{s}'" for s in symbols])
        query += f""" AND symbol IN ({symbol_str})"""

    df = db.query_df(query)
    df = df.sort_values(["dt", "symbol"]).reset_index(drop=True)
    df["dt"] = df["dt"].dt.tz_localize(None)
    df["update_time"] = df["update_time"].dt.tz_localize(None)
    return df


def get_latest_weights(db: Optional[Client] = None, strategy=None, database="czsc_strategy") -> pd.DataFrame:
    """获取策略最新持仓权重时间

    :param db: clickhouse_connect.driver.Client, 数据库连接
    :param strategy: str, 策略名称, 默认 None
    :param database: str, 数据库名称
    :return: pd.DataFrame
    """
    db = db or __db_from_env()

    query = f"SELECT * FROM {database}.latest_weights final"
    if strategy:
        query += f" WHERE strategy = '{strategy}'"

    df = db.query_df(query)
    df = df.rename(columns={"latest_dt": "dt", "latest_weight": "weight", "latest_update_time": "update_time"})
    if not df.empty:
        df["dt"] = df["dt"].dt.tz_localize(None)
        df["update_time"] = df["update_time"].dt.tz_localize(None)
        df = df.sort_values(["strategy", "dt", "symbol"]).reset_index(drop=True)
    return df


def publish_weights(
    strategy: str,
    df: pd.DataFrame,
    batch_size=100000,
    logger=loguru.logger,
    db: Optional[Client] = None,
    database="czsc_strategy",
):
    """发布策略持仓权重

    :param df: pd.DataFrame, 待发布的持仓权重数据
    :param db: clickhouse_connect.driver.Client, 数据库连接
    :param strategy: str, 策略名称
    :param batch_size: int, 批量发布的大小, 默认 100000
    :param logger: loguru.logger, 日志记录器
    :param database: str, 数据库名称
    :return: None
    """
    db = db or __db_from_env()

    __send_heartbeat(db, strategy, database=database, logger=logger)
    df = df[["dt", "symbol", "weight"]].copy()
    df["strategy"] = strategy
    df["dt"] = pd.to_datetime(df["dt"])

    dfl = get_latest_weights(db, strategy, database=database)

    if not dfl.empty:
        dfl["dt"] = pd.to_datetime(dfl["dt"])
        symbol_dt = dfl.set_index("symbol")["dt"].to_dict()
        logger.info(f"策略 {strategy} 最新时间：{dfl['dt'].max()}")

        rows = []
        for symbol, dfg in df.groupby("symbol"):
            if symbol in symbol_dt:
                dfg = dfg[dfg["dt"] > symbol_dt[symbol]]
                rows.append(dfg)
        if rows:
            df = pd.concat(rows, ignore_index=True)

        logger.info(f"策略 {strategy} 共 {len(df)} 条新信号")

    df = df.sort_values(["dt", "symbol"]).reset_index(drop=True)
    df["update_time"] = pd.to_datetime("now")
    df = df[["strategy", "symbol", "dt", "weight", "update_time"]].copy()
    df = df.drop_duplicates(["symbol", "dt", "strategy"], keep="last").reset_index(drop=True)
    df["weight"] = df["weight"].astype(float)

    logger.info(f"准备发布 {len(df)} 条策略信号")

    # 批量写入
    for i in range(0, len(df), batch_size):
        batch_df = df.iloc[i : i + batch_size]
        res = db.insert_df(f"{database}.weights", batch_df)
        __send_heartbeat(db, strategy)

        if res:
            logger.info(f"完成批次 {i//batch_size + 1}, 发布 {len(batch_df)} 条信号")
        else:
            logger.error(f"批次 {i//batch_size + 1} 发布失败: {res}")
            return

    logger.info(f"完成所有信号发布, 共 {len(df)} 条")
    __send_heartbeat(db, strategy)


def publish_returns(
    strategy: str,
    df: pd.DataFrame,
    batch_size=100000,
    logger=loguru.logger,
    database="czsc_strategy",
    db: Optional[Client] = None,
):
    """发布策略日收益

    :param df: pd.DataFrame, 待发布的日收益数据
    :param db: clickhouse_connect.driver.Client, 数据库连接
    :param strategy: str, 策略名称
    :param batch_size: int, 批量发布的大小, 默认 100000
    :param logger: loguru.logger, 日志记录器
    :return: None
    """
    db = db or __db_from_env()

    df = df[["dt", "symbol", "returns"]].copy()
    df["strategy"] = strategy
    df["dt"] = pd.to_datetime(df["dt"])

    # 查询 czsc_strategy.returns 表中，每个品种最新的时间
    dfl = db.query_df(
        f"SELECT symbol, max(dt) as dt FROM {database}.returns final WHERE strategy = '{strategy}' GROUP BY symbol"
    )

    if not dfl.empty:
        dfl["dt"] = dfl["dt"].dt.tz_localize(None)
        symbol_dt = dfl.set_index("symbol")["dt"].to_dict()
        logger.info(f"策略 {strategy} 最新时间：{dfl['dt'].max()}")

        rows = []
        for symbol, dfg in df.groupby("symbol"):
            if symbol in symbol_dt:
                # 允许覆盖同一天的数据
                dfg = dfg[dfg["dt"] >= symbol_dt[symbol]]
                rows.append(dfg)
        if rows:
            df = pd.concat(rows, ignore_index=True)

        logger.info(f"策略 {strategy} 共 {len(df)} 条新日收益")

    df = df.sort_values(["dt", "symbol"]).reset_index(drop=True)
    df["update_time"] = pd.to_datetime("now")
    df = df[["strategy", "symbol", "dt", "returns", "update_time"]].copy()
    df = df.drop_duplicates(["symbol", "dt", "strategy"], keep="last").reset_index(drop=True)
    df["returns"] = df["returns"].astype(float)

    logger.info(f"准备发布 {len(df)} 条策略日收益")

    # 批量写入
    for i in range(0, len(df), batch_size):
        batch_df = df.iloc[i : i + batch_size]
        res = db.insert_df(f"{database}.returns", batch_df)

        if res:
            logger.info(f"完成批次 {i//batch_size + 1}, 发布 {len(batch_df)} 条日收益")
        else:
            logger.error(f"批次 {i//batch_size + 1} 发布失败")
            return

    logger.info(f"完成所有日收益发布, 共 {len(df)} 条")


def get_strategy_returns(
    strategy, db: Optional[Client] = None, sdt=None, edt=None, symbols=None, database="czsc_strategy"
):
    """获取策略日收益

    :param db: clickhouse_connect.driver.Client, 数据库连接
    :param strategy: str, 策略名称
    :param sdt: str, 开始时间
    :param edt: str, 结束时间
    :param symbols: list, 符号列表
    :param database: str, 数据库名称
    :return: pd.DataFrame
    """
    db = db or __db_from_env()

    query = f"""
    SELECT * FROM {database}.returns final WHERE strategy = '{strategy}'
    """
    if sdt:
        query += f" AND dt >= '{sdt}'"
    if edt:
        query += f" AND dt <= '{edt}'"
    if symbols:
        if isinstance(symbols, str):
            symbols = [symbols]
        symbol_str = ", ".join([f"'{s}'" for s in symbols])
        query += f""" AND symbol IN ({symbol_str})"""

    df = db.query_df(query)
    df = df.sort_values(["dt", "symbol"]).reset_index(drop=True)
    df["dt"] = df["dt"].dt.tz_localize(None)
    df["update_time"] = df["update_time"].dt.tz_localize(None)
    return df


def clear_strategy(
    strategy, db: Optional[Client] = None, logger=loguru.logger, human_confirm=True, database="czsc_strategy"
):
    """清空策略

    :param db: clickhouse_connect.driver.Client, 数据库连接
    :param strategy: str, 策略名称
    :param logger: loguru.logger, 日志记录器
    :param human_confirm: bool, 是否需要人工确认，默认 True
    :param database: str, 数据库名称
    :return: None
    """
    db = db or __db_from_env()

    if human_confirm:
        confirm = input(f"确认清空策略 {strategy} 的所有数据？(y/n): ")
        if confirm.lower() != "y":
            logger.warning(f"取消清空策略 {strategy} 的所有数据")
            return

    query = f"""
    DELETE FROM {database}.metas WHERE strategy = '{strategy}'
    """
    _ = db.command(query)
    logger.info(f"清空策略 {strategy} 元数据成功")

    query = f"""
    DELETE FROM {database}.weights WHERE strategy = '{strategy}'
    """
    _ = db.command(query)
    logger.info(f"清空策略 {strategy} 持仓权重成功")

    query = f"""
    DELETE FROM {database}.returns WHERE strategy = '{strategy}'
    """
    _ = db.command(query)
    logger.info(f"清空策略 {strategy} 日收益成功")
    logger.warning(f"策略 {strategy} 清空完成")
