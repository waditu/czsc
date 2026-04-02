# 进度日志

- 已初始化计划文件，准备读取飞书任务详情。
- 已确认任务详情接口支持使用 task_guid 直接读取，第一次命令因参数位置错误失败，准备修正后重试。
- 已成功读取飞书任务详情，并识别负责人为曾斌（open_id: ou_9de69a4a443be939b6311a153e018458）。
- 首次 IM 发送尝试失败，原因是 `im +messages-send` 仅支持 bot 身份，已切换 bot 重试。
- 已确认 rs-czsc 的信号实现主要存在于 Rust `czsc-signals` registry 中，但 Python 层暂未发现与 `czsc.signals.xxx` 完全同名的直接导入入口，正在核实是否存在按名称执行单个信号的 API。
- 已将 `czsc.traders.sig_parse` 切换为基于 `rs_czsc` 注册表和反解析能力实现。
- 已新增 `czsc.traders._rs_signals`，并将 `generate_czsc_signals` 改为走 rs-czsc 统一执行引擎。
- 已重写 `test/test_signals.py`，不再依赖旧的 Python 信号函数逐个导入调用。
- 测试阶段发现当前 `czsc` 虚拟环境中的 `rs_czsc` 版本偏旧，缺少 `generate_signals` 接口；正在切换到本地工作区版本继续验证。
- 已按用户指定路径重装 wheel：`rs_czsc-0.1.25.post260320-cp39-abi3-win_amd64.whl`（先卸载再安装）。
- 用户回滚后导致 `czsc/traders/_rs_signals.py` 与 `czsc/traders/sig_parse.py` 缺失，现已重建并恢复兼容能力。
- `sig_parse.py` 已切换为 rs_czsc 公开接口：`list_all_signals / derive_signals_config / derive_signals_freqs`。
- `_rs_signals.py` 已切换为 `run_research` 驱动的统一信号执行桥接，并通过 `ResearchResult.signals_df()` 返回结果。
- 本轮验证通过：`test_trader_sig.py`、`test_signals.py`、`test_objects.py`、`test_strategy.py`（共 15 passed, 0 failed）。
- 已向任务负责人飞书私信同步当前阶段进展（message_id: `om_x100b53d6968538a8c439cf9ff6a24c2`）。
