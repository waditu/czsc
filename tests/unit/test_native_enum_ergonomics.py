"""PyO3 enum 在 Python 端的人体工学测试。

覆盖 czsc 暴露的 4 个 enum 类型——``Freq`` / ``Mark`` / ``Direction`` /
``Operate``——验证它们在 Python 端：

1. 都可以哈希（``hash(x)`` 不抛、可作为 ``dict`` / ``set`` 的 key）；
2. 都暴露 ``.name`` getter，返回 Rust variant 名（如 ``"F30"`` / ``"Up"`` / ``"HL"``），
   对齐 Python ``enum.Enum.name`` 的习惯；
3. ``.value`` getter 保留原有行为（返回中文显示串，向后兼容）；
4. ``__hash__`` 与 ``__eq__`` 满足 Python 数据模型不变量：
   ``a == b ⇒ hash(a) == hash(b)``；
5. pickle 往返与 ``__richcmp__`` 行为不受影响。

这套测试是 PyO3 enum 暴露层的 ratchet：将来若有人去掉 ``__hash__`` 或
``name`` getter 而破坏多进程缓存 / dict 化场景，可在 CI 第一时间被拦下。
"""

from __future__ import annotations

import pickle

import pytest

from czsc import Direction, Freq, Mark, Operate


@pytest.fixture(
    params=[
        pytest.param(("Freq", Freq.F30, "F30", "30分钟"), id="Freq.F30"),
        pytest.param(("Freq", Freq.D, "D", "日线"), id="Freq.D"),
        pytest.param(("Freq", Freq.Tick, "Tick", "Tick"), id="Freq.Tick"),
        pytest.param(("Mark", Mark.G, "G", "顶分型"), id="Mark.G"),
        pytest.param(("Mark", Mark.D, "D", "底分型"), id="Mark.D"),
        pytest.param(("Direction", Direction.Up, "Up", "向上"), id="Direction.Up"),
        pytest.param(("Direction", Direction.Down, "Down", "向下"), id="Direction.Down"),
        # Operate 7 个 variant 全覆盖：HL/HS/HO/LO/LE/SO/SE 的 name match arm
        # 各自独立，必须逐个测，否则换 arm 顺序或 typo 不会被 CI 拦下。
        pytest.param(("Operate", Operate.HL, "HL", "持多"), id="Operate.HL"),
        pytest.param(("Operate", Operate.HS, "HS", "持空"), id="Operate.HS"),
        pytest.param(("Operate", Operate.HO, "HO", "持币"), id="Operate.HO"),
        pytest.param(("Operate", Operate.LO, "LO", "开多"), id="Operate.LO"),
        pytest.param(("Operate", Operate.LE, "LE", "平多"), id="Operate.LE"),
        pytest.param(("Operate", Operate.SO, "SO", "开空"), id="Operate.SO"),
        pytest.param(("Operate", Operate.SE, "SE", "平空"), id="Operate.SE"),
    ]
)
def enum_case(request):
    return request.param


def test_enum_has_name_attribute(enum_case):
    """每个 enum 实例都暴露 ``.name``，返回 Rust variant 名。"""
    _, member, expected_name, _ = enum_case
    assert hasattr(member, "name"), f"{member!r} 缺少 .name getter"
    assert member.name == expected_name


def test_enum_preserves_value_attribute(enum_case):
    """``.value`` getter 保持原有中文显示串语义，不被本次改动破坏。"""
    _, member, _, expected_value = enum_case
    assert member.value == expected_value


def test_enum_is_hashable(enum_case):
    """``hash(member)`` 不抛异常。"""
    _, member, _, _ = enum_case
    hash(member)  # 不抛即过


def test_enum_usable_as_dict_key(enum_case):
    """可作为 ``dict`` key，按变体身份去重。"""
    _, member, _, _ = enum_case
    bucket = {member: "x"}
    assert bucket[member] == "x"


def test_enum_usable_in_set_with_dedup():
    """同一变体进集合应去重，不同变体保留。"""
    s = {Freq.F30, Freq.F30, Freq.D}
    assert len(s) == 2
    assert Freq.F30 in s and Freq.D in s and Freq.F60 not in s

    s2 = {Direction.Up, Direction.Up, Direction.Down}
    assert len(s2) == 2

    s3 = {Mark.G, Mark.G, Mark.D}
    assert len(s3) == 2

    s4 = {Operate.HL, Operate.HL, Operate.HS}
    assert len(s4) == 2


def test_hash_eq_invariant(enum_case):
    """Python 数据模型不变量：``a == b ⇒ hash(a) == hash(b)``。

    对相同 variant 的两个实例（在 Rust 端可能是同一份 ``Copy`` 也可能是新构造的），
    哈希必须一致；否则 dict/set 行为会损坏。
    """
    cls_name, member, name, _ = enum_case
    # 用 __reduce__ + 构造器复刻一份"同变体的新对象"
    twin = Operate.from_str(name) if cls_name == "Operate" else type(member)(name)
    assert member == twin
    assert hash(member) == hash(twin), f"{cls_name}.{name} 的 hash 在重构后变了，违反 Python 数据模型"


def test_eq_with_value_string_does_not_require_hash_match():
    """`__richcmp__` 允许 ``Freq.F30 == 任何 .value == '30分钟' 的对象``，
    这是历史兼容路径；不在此处强制要求 hash 一致（跨类型比较本来就在
    Python 数据模型的"未定义"区，dict/set 不会依赖这种情况）。"""

    class FakeValueHolder:
        value = "30分钟"

    # Yoda 写法是有意的：本测试要验证 Freq 在左侧时走 `__richcmp__` 的
    # ".value 字符串兼容路径"，反过来写就变成在测 FakeValueHolder 的 __eq__，
    # 测试意图完全不同。
    assert Freq.F30 == FakeValueHolder()  # noqa: SIM300 — 见上方注释，刻意保留 Yoda 形式


def test_enum_pickle_roundtrip_preserves_name_and_hash(enum_case):
    """pickle 往返不应改变 ``name`` / ``value`` / ``hash``。

    安全性说明：此处 ``pickle.loads`` 反序列化的是本测试上一行 ``pickle.dumps``
    自己生成的字节串，属于受控的同进程往返测试，**不是**加载外部不可信
    数据，因此不存在 pickle RCE 风险。
    """
    _, member, expected_name, expected_value = enum_case
    restored = pickle.loads(pickle.dumps(member))  # noqa: S301 — 见 docstring 中的安全性说明
    assert type(restored) is type(member)
    assert restored.name == expected_name
    assert restored.value == expected_value
    assert restored == member
    assert hash(restored) == hash(member)


def test_freq_repr_unchanged():
    """``__repr__`` 行为保持不变（Freq.F30 形式）。"""
    assert repr(Freq.F30) == "Freq.F30"
    assert repr(Freq.D) == "Freq.D"


def test_mark_direction_repr_unchanged():
    assert repr(Mark.G) == "Mark.G"
    assert repr(Direction.Up) == "Direction.Up"


def test_operate_repr_is_consistent_with_other_enums():
    """`Operate` 的 ``__repr__`` 必须返回 ``Operate.<Variant>`` 形式，
    与 Freq / Mark / Direction 一致，不再泄漏内部 Rust 结构名
    （历史上曾返回 ``"PyOperate::HL"``）。"""
    assert repr(Operate.HL) == "Operate.HL"
    assert repr(Operate.SE) == "Operate.SE"
    assert repr(Operate.HO) == "Operate.HO"
