# -*- coding: utf-8 -*-
"""
test_io.py - czsc.utils.io 文件IO工具模块单元测试

测试覆盖:
- save_pkl / read_pkl: pickle 序列化/反序列化
- save_json / read_json: JSON 序列化/反序列化
- make_zip: 目录压缩为 zip
- 边界情况: 空数据、嵌套结构、中文字符
"""
import os
import pytest
from czsc.utils.io import save_pkl, read_pkl, save_json, read_json, make_zip


@pytest.fixture
def tmp_dir(tmp_path):
    """提供临时目录"""
    return tmp_path


class TestPickle:
    """测试 pickle 序列化"""

    def test_basic_dict(self, tmp_dir):
        """测试基本字典"""
        data = {"key": "value", "number": 42}
        filepath = str(tmp_dir / "test.pkl")
        save_pkl(data, filepath)
        loaded = read_pkl(filepath)
        assert loaded == data

    def test_nested_structure(self, tmp_dir):
        """测试嵌套结构"""
        data = {"list": [1, 2, 3], "nested": {"a": 1}, "tuple": (1, 2)}
        filepath = str(tmp_dir / "test_nested.pkl")
        save_pkl(data, filepath)
        loaded = read_pkl(filepath)
        assert loaded["list"] == [1, 2, 3]
        assert loaded["nested"]["a"] == 1

    def test_empty_data(self, tmp_dir):
        """测试空数据"""
        filepath = str(tmp_dir / "test_empty.pkl")
        save_pkl({}, filepath)
        loaded = read_pkl(filepath)
        assert loaded == {}

    def test_none_value(self, tmp_dir):
        """测试 None 值"""
        filepath = str(tmp_dir / "test_none.pkl")
        save_pkl(None, filepath)
        loaded = read_pkl(filepath)
        assert loaded is None


class TestJson:
    """测试 JSON 序列化"""

    def test_basic_dict(self, tmp_dir):
        """测试基本字典"""
        data = {"key": "value", "number": 42}
        filepath = str(tmp_dir / "test.json")
        save_json(data, filepath)
        loaded = read_json(filepath)
        assert loaded == data

    def test_chinese_characters(self, tmp_dir):
        """测试中文字符"""
        data = {"名称": "缠中说禅", "状态": "正常"}
        filepath = str(tmp_dir / "test_cn.json")
        save_json(data, filepath)
        loaded = read_json(filepath)
        assert loaded["名称"] == "缠中说禅"

    def test_list_data(self, tmp_dir):
        """测试列表数据"""
        data = [1, 2, 3, "abc"]
        filepath = str(tmp_dir / "test_list.json")
        save_json(data, filepath)
        loaded = read_json(filepath)
        assert loaded == data

    def test_empty_dict(self, tmp_dir):
        """测试空字典"""
        filepath = str(tmp_dir / "test_empty.json")
        save_json({}, filepath)
        loaded = read_json(filepath)
        assert loaded == {}


class TestMakeZip:
    """测试 make_zip 函数"""

    def test_basic_zip(self, tmp_dir):
        """测试基本压缩"""
        source = tmp_dir / "source"
        source.mkdir()
        (source / "file1.txt").write_text("hello")
        (source / "file2.txt").write_text("world")

        zip_path = str(tmp_dir / "test.zip")
        make_zip(str(source), zip_path)
        assert os.path.exists(zip_path)

    def test_nested_dir_zip(self, tmp_dir):
        """测试嵌套目录压缩"""
        source = tmp_dir / "source"
        source.mkdir()
        sub = source / "subdir"
        sub.mkdir()
        (sub / "nested.txt").write_text("nested content")

        zip_path = str(tmp_dir / "test_nested.zip")
        make_zip(str(source), zip_path)
        assert os.path.exists(zip_path)

    def test_invalid_dir_raises(self, tmp_dir):
        """测试无效目录应抛出异常"""
        with pytest.raises(AssertionError):
            make_zip("/nonexistent/path", str(tmp_dir / "test.zip"))
