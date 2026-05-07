"""
Pandas <-> Arrow IPC 字节流互转工具

用途：
    在 Python 与 Rust 之间通过 Arrow IPC 文件格式做零拷贝（或低拷贝）的数据传递。
    Arrow IPC 是 Rust polars / arrow-rs 原生支持的格式，相较于直接 PyO3 行级
    传递可大幅降低跨语言边界的开销，尤其适合大数据量场景。

注意:
    - 本模块属于 ``czsc._utils`` 内部工具，前缀 ``_`` 表示不属于公开 API
    - 上层任何调用方都不应该假设字节流的内部结构稳定，仅可视为不透明二进制
    - PyArrow 与 Pandas 的版本组合需保持一致，否则可能在 Schema 推断时报错
"""

import pandas as pd
import pyarrow as pa
import pyarrow.ipc as ipc
from typing import Union

def pandas_to_arrow_bytes(df: Union[pd.DataFrame, pd.Series]) -> bytes:
    """
    将 Pandas DataFrame/Series 序列化为 Arrow IPC 文件格式的字节流

    参数:
        df: 输入的 Pandas DataFrame 或 Series；若是 Series 会被 PyArrow 自动
            包装为单列 Table。所有列的 dtype 必须为 PyArrow 可识别的类型，
            否则在 ``pa.Table.from_pandas`` 阶段会抛 ArrowTypeError。

    返回:
        bytes: 完整的 Arrow IPC File 字节流，可直接通过网络传输或写入文件，
        在另一端使用 :func:`arrow_bytes_to_pd_df` 还原。

    备注:
        - 使用 IPC File（含尾部 footer）而非 IPC Stream 格式，便于随机读取
        - ``BufferOutputStream`` 在内存中累积，对 GB 级超大表不适合，
          这种规模请改用磁盘文件 + 流式写入的方案
    """
    # 第一步：把 Pandas DataFrame 转为 PyArrow Table，会做一次类型推断
    table = pa.Table.from_pandas(df)

    # 第二步：序列化为 Arrow IPC 文件格式
    # - sink 是 PyArrow 提供的内存缓冲；with 语句确保 footer 被正确写入
    sink = pa.BufferOutputStream()
    with ipc.new_file(sink, table.schema) as writer:
        writer.write_table(table)

    # 第三步：把 Buffer 转为 Python bytes，方便跨边界传递
    return sink.getvalue().to_pybytes()


def arrow_bytes_to_pd_df(arrow_bytes: bytes) -> pd.DataFrame:
    """
    将 Arrow IPC 字节流反序列化为 Pandas DataFrame

    参数:
        arrow_bytes: 由 :func:`pandas_to_arrow_bytes` 或同等格式产生的字节串。
                     不接受 Arrow IPC Stream 格式，传入会触发 InvalidArgument。

    返回:
        pd.DataFrame: 与原始 DataFrame 等价的对象。
                      索引信息若在序列化时存在 schema 元数据中会被还原；否则
                      保持默认 RangeIndex。

    备注:
        ``read_all()`` 一次性把所有 RecordBatch 加载到内存。对于巨型表，应改用
        ``reader.get_record_batch(i)`` 逐批读取以控制内存峰值。
    """
    # 用 BufferReader 把 bytes 包装为可读流
    buffer = pa.BufferReader(arrow_bytes)

    # 通过 IPC 文件格式读取 Arrow Table（含 schema 与 footer 校验）
    with ipc.open_file(buffer) as reader:
        table = reader.read_all()

    # Arrow Table -> Pandas DataFrame 会涉及一次列级别的 zero-copy / copy 决策，
    # 由 PyArrow 内部根据 dtype 自行选择，调用方无需关心。
    return table.to_pandas()
