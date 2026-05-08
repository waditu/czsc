"""``czsc.envs`` 环境变量与配置接口单元测试（迁移后版本）。

本测试套件覆盖 ``czsc.envs`` 模块在迁移完成后保留下来的公共配置接口，
并通过"反向断言"（negative pin）防止已废弃的 helper 被意外重新引入。

业务背景：
    经过迁移清理，``czsc.envs`` 仅保留三个公开配置项：

    - ``czsc_min_bi_len``：最小笔长度（K 线根数）
    - ``czsc_max_bi_num``：最大笔数量
    - ``czsc_verbose``：是否启用详细日志输出

    历史遗留的 ``use_python``、``get_welcome``、``valid_true`` 等 helper
    以及 ``CZSC_USE_PYTHON`` 环境变量分支均已废弃。本套件除了覆盖这些
    保留接口的正确行为之外，还显式断言废弃符号的缺失，避免后续重构时
    被无意中重新加入。

测试覆盖：
    - 已废弃接口的"不存在"反向断言；
    - ``get_verbose`` 默认值、环境变量与参数覆盖三种来源；
    - ``get_min_bi_len`` 默认值、参数覆盖、环境变量覆盖、返回类型；
    - ``get_max_bi_num`` 默认值、参数覆盖、环境变量覆盖、返回类型。
"""

from __future__ import annotations

import os

import pytest

from czsc import envs as envs_mod
from czsc.envs import get_max_bi_num, get_min_bi_len, get_verbose


class TestRetiredHelpers:
    """反向断言：确认所有已废弃的 helper 已经被移除。"""

    # 参数化覆盖所有需要被废弃的旧符号；其中 _env 是私有助手，应当保留
    @pytest.mark.parametrize("name", ["use_python", "get_welcome", "valid_true", "_env"])
    def test_legacy_helper_removed(self, name: str) -> None:
        """对每个旧名称做存在性检查。

        测试场景：
            遍历四个历史符号；其中 ``_env`` 是模块内私有 helper，仍然保留；
            其余三个公共 helper 必须已经从 ``czsc.envs`` 模块中移除。

        关键断言：
            - ``_env`` 必须存在（私有实现细节，保留向下兼容）；
            - 其他三个公共名称必须已移除。
        """
        # `_env` 仍然作为模块内私有 helper 保留；其余符号必须已经移除
        if name == "_env":
            assert hasattr(envs_mod, name), "私有 _env helper 应当继续保留"
        else:
            assert not hasattr(envs_mod, name), f"czsc.envs.{name} 必须被移除"

    def test_no_czsc_use_python_branch(self) -> None:
        """验证 czsc.envs 源码中不再引用 CZSC_USE_PYTHON 环境变量。

        测试场景：
            通过 ``inspect.getsource`` 获取整个 ``czsc.envs`` 模块的源码字符串，
            搜索其中是否仍然包含 ``CZSC_USE_PYTHON`` 关键字。

        关键断言：
            源码中不得出现 ``CZSC_USE_PYTHON`` 字符串，确保迁移后已经
            完全切断 Rust/Python 双实现的环境变量切换分支。
        """
        import inspect

        src = inspect.getsource(envs_mod)
        assert "CZSC_USE_PYTHON" not in src, "CZSC_USE_PYTHON 环境变量必须不被引用"


class TestGetVerbose:
    """``get_verbose`` 函数行为测试：覆盖默认值、环境变量、参数覆盖三类来源。"""

    def test_default_false(self) -> None:
        """无任何外部输入时，get_verbose 默认返回 False。

        测试场景：
            清除两种大小写形式的环境变量后调用 ``get_verbose()``。

        关键断言：
            返回值严格为 ``False``（使用 ``is`` 比较布尔身份）。
        """
        os.environ.pop("CZSC_VERBOSE", None)
        os.environ.pop("czsc_verbose", None)
        assert get_verbose() is False

    def test_env_true(self, monkeypatch) -> None:
        """通过环境变量 CZSC_VERBOSE=1 开启详细模式。

        使用 pytest 的 ``monkeypatch`` fixture 临时设置环境变量，
        测试结束后会自动还原。
        """
        monkeypatch.setenv("CZSC_VERBOSE", "1")
        assert get_verbose() is True

    def test_parameter_override(self) -> None:
        """显式传入参数覆盖环境变量与默认值。

        关键断言：
            - ``get_verbose(verbose="1")`` 返回 True；
            - ``get_verbose(verbose="0")`` 返回 False。
        """
        os.environ.pop("czsc_verbose", None)
        assert get_verbose(verbose="1") is True
        assert get_verbose(verbose="0") is False


class TestGetMinBiLen:
    """``get_min_bi_len`` 函数行为测试：覆盖默认值、参数覆盖、环境变量、返回类型。"""

    def test_default_value(self) -> None:
        """无任何外部输入时，最小笔长度默认值为 6 根 K 线。"""
        os.environ.pop("CZSC_MIN_BI_LEN", None)
        os.environ.pop("czsc_min_bi_len", None)
        assert get_min_bi_len() == 6

    def test_parameter_override(self) -> None:
        """显式传入参数应直接被采用，不受默认值影响。"""
        assert get_min_bi_len(7) == 7
        assert get_min_bi_len(6) == 6

    def test_env_override(self, monkeypatch) -> None:
        """通过环境变量 CZSC_MIN_BI_LEN 覆盖默认值。"""
        monkeypatch.setenv("CZSC_MIN_BI_LEN", "7")
        assert get_min_bi_len() == 7

    def test_returns_int(self) -> None:
        """返回值类型必须为 int，便于下游算法直接使用。"""
        assert isinstance(get_min_bi_len(), int)


class TestGetMaxBiNum:
    """``get_max_bi_num`` 函数行为测试：覆盖默认值、参数覆盖、环境变量、返回类型。"""

    def test_default_value(self) -> None:
        """无任何外部输入时，最大笔数量默认值为 50。"""
        os.environ.pop("CZSC_MAX_BI_NUM", None)
        os.environ.pop("czsc_max_bi_num", None)
        assert get_max_bi_num() == 50

    def test_parameter_override(self) -> None:
        """显式传入参数应直接被采用。"""
        assert get_max_bi_num(100) == 100

    def test_env_override(self, monkeypatch) -> None:
        """通过环境变量 CZSC_MAX_BI_NUM 覆盖默认值。"""
        monkeypatch.setenv("CZSC_MAX_BI_NUM", "100")
        assert get_max_bi_num() == 100

    def test_returns_int(self) -> None:
        """返回值类型必须为 int。"""
        assert isinstance(get_max_bi_num(), int)
