通读一下 ./czsc 库的代码，在 ./test 中优化测试代码，测试代码用 pytest 的格式。
以下的信息对你有用:
1. czsc 项目用 uv 管理，详情参考docs\UV管理开源项目指南.md
2. test 下面的所有测试如果需要有mock数据，统一通过 czsc.mock 模块获取