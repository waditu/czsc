import pytest

from czsc import Event, Position


@pytest.fixture
def position_file(tmp_path):
    """构造一个 unique_signals 非空的真实 Position，落盘为 JSON 文件，返回路径。"""
    oe = Event.load({"operate": "开多", "signals_all": ["30分钟_D1_表里关系V230101_向上_任意_任意_0"]})
    xe = Event.load({"operate": "平多", "signals_all": ["30分钟_D1_表里关系V230101_向下_任意_任意_0"]})
    pos = Position(symbol="000001", name="表里多头", opens=[oe], exits=[xe], interval=0, timeout=20, stop_loss=300)
    p = tmp_path / "pos.json"
    p.write_text(pos.to_json())
    return p
