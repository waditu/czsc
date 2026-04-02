# 发现记录

- 飞书任务 GUID `70d0f90e-183a-499f-80c5-f42d04a18ad4` 可通过 `lark-cli task tasks get --as user --params '{\"task_guid\":\"...\"}'` 直接读取。
- 任务标题：使用 rs-czsc 的模块替换掉 czsc 中现有的一些模块。
- 任务描述要求：
	- 删除 czsc 中整个 `signals` 模块，使用 rs-czsc 中已有实现替代。
	- `czsc.py` 模块内若对象/实现已在 rs-czsc 中存在，需要移除 Python 实现并改为 Rust 替换。
	- 更新相关单元测试并保证测试通过。
- 当前任务负责人 open_id：`ou_9de69a4a443be939b6311a153e018458`。

