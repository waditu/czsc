"""parity 测试包 —— Python ↔ Rust 等价性测试套件。

本包内的所有测试用例均围绕一个核心目标：保证迁移后的 ``czsc`` 模块
（基于 Rust 重构的 ``_native`` / ``_rs_czsc`` 后端）在功能与数值上与
PyPI 上的基线版本 ``rs_czsc`` 完全一致。

主要覆盖范围：
    * 缠论核心分析器（CZSC 分型/笔/中枢）
    * 信号注册表与 ``derive_signals_*`` 系列工具
    * ``run_research`` 全链路回测
    * ``OpensOptimize`` / ``ExitsOptimize`` 优化流程
    * 示例脚本（如 ``30分钟笔非多即空``、``use_optimize`` 等）

测试数据全部使用固定随机种子的 mock K线，保证结果可重现。
"""
