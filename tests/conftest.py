"""pytest 全局配置：实现 @pytest.mark.slow 默认跳过、可通过 --run-slow 启用。

CI / 发布前跑全套：``pytest --run-slow``
日常开发：``pytest``（自动跳过 slow 标记的测试）
"""

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="运行被 @pytest.mark.slow 标记的耗时测试",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-slow"):
        return
    skip_slow = pytest.mark.skip(reason="slow 测试默认跳过，加 --run-slow 启用")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)
