"""
test_envs.py - czsc.envs 环境变量管理模块单元测试

测试覆盖:
- use_python(): 环境变量控制Python/Rust版本选择
- get_verbose(): 详细输出控制
- get_welcome(): 欢迎信息控制
- get_min_bi_len(): 最小笔长度配置
- get_max_bi_num(): 最大笔数量配置
- 边界情况: 无效环境变量值、参数覆盖
"""

import os

from czsc.envs import get_max_bi_num, get_min_bi_len, get_verbose, get_welcome, use_python


class TestUsePython:
    """测试 use_python 函数"""

    def test_default_false(self):
        """默认情况下应返回 False"""
        os.environ.pop("CZSC_USE_PYTHON", None)
        assert use_python() is False

    def test_set_true_values(self):
        """测试各种 True 的有效表达"""
        for val in ["1", "True", "true", "Y", "y", "yes", "Yes"]:
            os.environ["CZSC_USE_PYTHON"] = val
            assert use_python() is True
        os.environ.pop("CZSC_USE_PYTHON", None)

    def test_set_false_values(self):
        """测试无效值应返回 False"""
        for val in ["0", "False", "false", "N", "n", "no", "No", "abc"]:
            os.environ["CZSC_USE_PYTHON"] = val
            assert use_python() is False
        os.environ.pop("CZSC_USE_PYTHON", None)


class TestGetVerbose:
    """测试 get_verbose 函数"""

    def test_default_false(self):
        """默认情况下应返回 False"""
        os.environ.pop("czsc_verbose", None)
        assert get_verbose() is False

    def test_env_true(self, monkeypatch):
        """环境变量设为 True 时应返回 True"""
        monkeypatch.setenv("CZSC_VERBOSE", "1")
        assert get_verbose() is True

    def test_parameter_override(self):
        """参数传入时应覆盖环境变量"""
        os.environ.pop("czsc_verbose", None)
        assert get_verbose(verbose="1") is True
        assert get_verbose(verbose="0") is False


class TestGetWelcome:
    """测试 get_welcome 函数"""

    def test_default_false(self):
        """默认应返回 False"""
        os.environ.pop("czsc_welcome", None)
        os.environ["CZSC_WELCOME"] = "0"
        assert get_welcome() is False
        os.environ.pop("czsc_welcome", None)

    def test_set_true(self, monkeypatch):
        """设置为 1 时应返回 True"""
        monkeypatch.setenv("CZSC_WELCOME", "1")
        assert get_welcome() is True


class TestGetMinBiLen:
    """测试 get_min_bi_len 函数"""

    def test_default_value(self):
        """默认值应为 6"""
        os.environ.pop("czsc_min_bi_len", None)
        assert get_min_bi_len() == 6

    def test_parameter_override(self):
        """参数传入时应覆盖默认值"""
        assert get_min_bi_len(7) == 7
        assert get_min_bi_len(6) == 6

    def test_env_override(self, monkeypatch):
        """环境变量应覆盖默认值"""
        monkeypatch.setenv("CZSC_MIN_BI_LEN", "7")
        assert get_min_bi_len() == 7

    def test_returns_int(self):
        """返回值应为整数"""
        result = get_min_bi_len()
        assert isinstance(result, int)


class TestGetMaxBiNum:
    """测试 get_max_bi_num 函数"""

    def test_default_value(self):
        """默认值应为 50"""
        os.environ.pop("czsc_max_bi_num", None)
        assert get_max_bi_num() == 50

    def test_parameter_override(self):
        """参数传入时应覆盖默认值"""
        assert get_max_bi_num(100) == 100
        assert get_max_bi_num(20) == 20

    def test_env_override(self, monkeypatch):
        """环境变量应覆盖默认值"""
        monkeypatch.setenv("CZSC_MAX_BI_NUM", "100")
        assert get_max_bi_num() == 100

    def test_returns_int(self):
        """返回值应为整数"""
        result = get_max_bi_num()
        assert isinstance(result, int)
