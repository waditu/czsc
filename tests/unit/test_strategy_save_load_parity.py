"""``CzscStrategyBase.save_positions`` / ``load_positions`` 的 Rust 透传契约测试。

2026-05-17 PR-G：md5(str(dict)) 旧契约重新设计为 sha256(canonical JSON)，
IO + 校验逻辑整段下沉 Rust（``czsc._native.strategy_save_position`` /
``strategy_load_position``，背后是
``czsc_trader::strategy::{save_position_to_file, load_position_from_file}``）。

本文件锁定 3 条契约：

1. **开发宪法第一条**：Python 侧的 save/load 必须把工作完整委托给 Rust，
   不再依赖 ``hashlib`` / ``json`` 自写校验。
2. **新格式 checksum**：新写出的文件包含 ``checksum`` 字段，不再包含
   ``md5`` 字段；篡改后再加载会失败。
3. **历史兼容**：包含旧 ``md5`` 字段（即便值是错的）的文件仍能正常加载，
   不再尝试校验。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from czsc import CzscStrategyBase
from czsc._native import Event, Operate, Position, Signal


def _signal(suffix: str) -> str:
    return f"日线_{suffix}_kind_v1_v2_v3_0"


def _make_position(name: str, signals: list[str]) -> Position:
    open_event = Event(
        operate=Operate.LO,
        signals_all=[Signal(s) for s in signals],
        signals_any=[],
        signals_not=[],
    )
    exit_event = Event(
        operate=Operate.LE,
        signals_all=[],
        signals_any=[],
        signals_not=[],
    )
    return Position(symbol="TEST", opens=[open_event], exits=[exit_event], name=name)


class _DummyStrategy(CzscStrategyBase):
    @property
    def positions(self):
        return self.kwargs["_positions"]


def test_save_writes_checksum_field_not_md5(tmp_path: Path) -> None:
    """新格式：写出的 JSON 必须含 checksum 字段，且不含 md5 字段。"""
    tactic = _DummyStrategy(
        symbol="TEST",
        _positions=[_make_position("p1", [_signal("a")])],
    )
    tactic.save_positions(tmp_path)

    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text(encoding="utf-8"))
    assert "checksum" in data, "新格式必须写 checksum 字段"
    assert "md5" not in data, "新格式不应再写 md5 字段（PR-G breaking change）"
    assert "symbol" not in data, "save_positions 剥离 symbol，加载时按调用方注入"
    # SHA256 hex 字符串固定 64 字符
    assert len(data["checksum"]) == 64


def test_save_load_round_trip(tmp_path: Path) -> None:
    """save → load 往返：positions 结构一致，symbol 重新注入。"""
    src_positions = [
        _make_position("p1", [_signal("a"), _signal("b")]),
        _make_position("p2", [_signal("b"), _signal("c")]),
    ]
    tactic = _DummyStrategy(symbol="ORIG_SYMBOL", _positions=src_positions)
    tactic.save_positions(tmp_path)

    files = sorted(tmp_path.glob("*.json"))
    assert len(files) == 2

    reloaded = _DummyStrategy(symbol="NEW_SYMBOL", _positions=[])
    loaded = reloaded.load_positions(files, check=True)

    assert [p.name for p in loaded] == [p.name for p in src_positions]
    # symbol 在 save 时被剥离，load 时由 self.symbol 注入
    for pos in loaded:
        assert pos.symbol == "NEW_SYMBOL"


def test_tampered_file_fails_check(tmp_path: Path) -> None:
    """新格式 checksum 校验失败时必须抛 ValueError（不是 AssertionError）。"""
    tactic = _DummyStrategy(symbol="TEST", _positions=[_make_position("p1", [_signal("a")])])
    tactic.save_positions(tmp_path)
    target = next(tmp_path.glob("*.json"))

    # 篡改：把 name 改掉
    payload = json.loads(target.read_text(encoding="utf-8"))
    payload["name"] = "tampered"
    target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    reloaded = _DummyStrategy(symbol="X", _positions=[])
    with pytest.raises(ValueError, match="checksum"):
        reloaded.load_positions([target], check=True)

    # check=False 时静默放行
    loaded = reloaded.load_positions([target], check=False)
    assert loaded[0].name == "tampered"


def test_legacy_md5_file_loads_silently(tmp_path: Path) -> None:
    """历史兼容：含旧 md5 字段（甚至值是错的）的文件，PR-G 加载不抛错。"""
    # 手工构造一个旧格式文件：故意写一个错 md5
    payload = {
        "name": "legacy",
        "opens": [
            {
                "operate": "开多",
                "signals_all": [_signal("a")],
                "signals_any": [],
                "signals_not": [],
                "name": "open",
            }
        ],
        "exits": [
            {
                "operate": "平多",
                "signals_all": [],
                "signals_any": [],
                "signals_not": [],
                "name": "exit",
            }
        ],
        "interval": 0,
        "timeout": 0,
        "stop_loss": 0.0,
        "T0": False,
        "md5": "deadbeefdeadbeefdeadbeefdeadbeef",
    }
    target = tmp_path / "legacy.json"
    target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    reloaded = _DummyStrategy(symbol="X", _positions=[])
    # check=True 也应该成功（旧 md5 算法不可跨语言复现，静默跳过）
    loaded = reloaded.load_positions([target], check=True)
    assert loaded[0].name == "legacy"
    assert loaded[0].symbol == "X"


def test_strategies_module_no_longer_uses_hashlib_or_json() -> None:
    """开发宪法第一条 ratchet：czsc.strategies 不应再 import hashlib / json。

    一旦有人退回 Python 自实现 md5 / json IO，本测试立即红。
    """
    import czsc.strategies as strategies_module

    src = Path(strategies_module.__file__).read_text(encoding="utf-8")
    assert "import hashlib" not in src, "PR-G 之后 czsc.strategies 不应再依赖 hashlib"
    # json 仅在历史 load_positions 里用，下沉 Rust 后应当也消失
    assert "import json" not in src, "PR-G 之后 czsc.strategies 不应再依赖 json"
