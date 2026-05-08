"""compat 测试包 —— 公共 API 兼容性测试套件。

本包内的测试用例锁定迁移后 ``czsc`` 包对外暴露的公共 API 表面，
包括：
    * 顶层模块需要导出的名称（``CZSC``、``RawBar``、``Signal`` 等）
    * 信号子包是否齐全（如 ``czsc.signals.bar`` 等）
    * ``czsc.traders`` 命名空间下应保留的公共名称
    * ``czsc.ta`` 技术指标命名空间
    * 已废弃的旧 API 必须被移除（``WeightBacktest`` 应来自 ``wbt`` 包等）

通过对比 ``snapshots/api_v1.json`` 中的快照，确保任何破坏性的 import
路径或签名修改都能被立即捕获，保护下游用户的兼容性。
"""
