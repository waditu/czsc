"""内部脚本：用一个 stub 替换 streamlit，让 docs/examples 下的 streamlit 案例
可以在普通 Python 解释器中走完一遍，捕获运行时错误。

用法：
    uv run python docs/examples/_streamlit_smoke.py 10_streamlit_kline.py
"""

from __future__ import annotations

import importlib.util
import sys
import types
from contextlib import contextmanager
from pathlib import Path


class _StubObj:
    """把任何属性访问/调用都吞掉的 stub，模拟 streamlit 控件返回的对象。

    对 ``radio`` / ``selectbox`` 等会返回选项之一的方法做特殊处理：
    返回第一个 options 元素（要求作为 dict key 时不能是 stub）。
    """

    _CHOICE_METHODS = {"radio", "selectbox"}
    _PASSTHROUGH_METHODS = {"text_input", "number_input", "slider", "date_input"}

    def __init__(self, value=None):
        self._value = value

    def __call__(self, *args, **kwargs):
        return _StubObj()

    def __getattr__(self, name):
        if name in self._CHOICE_METHODS:
            def _choice(label, options=(), index=0, **kw):
                opts = list(options)
                return opts[index] if opts else None
            return _choice
        if name in self._PASSTHROUGH_METHODS:
            def _passthrough(label, value=None, *args, **kw):
                return value
            return _passthrough
        return _StubObj()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def __iter__(self):
        for _ in range(4):
            yield _StubObj()

    def __getitem__(self, _):
        return _StubObj()


def _make_streamlit_stub() -> types.ModuleType:
    st = types.ModuleType("streamlit")

    # 兜底：未显式定义的属性都返回 _StubObj()
    def _module_getattr(name: str):
        return _StubObj()

    st.__getattr__ = _module_getattr  # type: ignore[attr-defined]

    def text_input(label, value="", **kw):
        return value

    def number_input(label, value=0, **kw):
        return value

    def slider(label, mn=0, mx=100, value=50, **kw):
        return value

    def selectbox(label, options, index=0, **kw):
        return list(options)[index] if options else None

    def date_input(label, value=None, **kw):
        return value

    def radio(label, options, index=0, **kw):
        return list(options)[index] if options else None

    # 注入常用 API
    st.set_page_config = lambda **kw: None
    st.title = lambda *a, **kw: None
    st.caption = lambda *a, **kw: None
    st.write = lambda *a, **kw: None
    st.error = lambda *a, **kw: None
    st.warning = lambda *a, **kw: None
    st.info = lambda *a, **kw: None
    st.subheader = lambda *a, **kw: None
    st.header = lambda *a, **kw: None
    st.markdown = lambda *a, **kw: None
    st.divider = lambda: None
    st.text_input = text_input
    st.number_input = number_input
    st.slider = slider
    st.selectbox = selectbox
    st.date_input = date_input
    st.radio = radio
    st.metric = lambda label, value=None, **kw: None
    st.dataframe = lambda *a, **kw: None
    st.plotly_chart = lambda *a, **kw: None
    st.json = lambda *a, **kw: None
    st.table = lambda *a, **kw: None
    st.stop = lambda: None

    st.sidebar = _StubObj()
    st.tabs = lambda labels: [_StubObj() for _ in labels]
    st.columns = lambda spec: [_StubObj() for _ in (spec if isinstance(spec, (list, tuple)) else range(int(spec)))]
    st.expander = lambda *a, **kw: _StubObj()
    st.container = lambda *a, **kw: _StubObj()

    # 缓存装饰器空实现
    def _cache_decorator(*a, **kw):
        if a and callable(a[0]):
            return a[0]

        def deco(fn):
            return fn

        return deco

    st.cache_data = _cache_decorator
    st.cache_resource = _cache_decorator
    return st


@contextmanager
def patch_streamlit():
    saved = sys.modules.get("streamlit")
    sys.modules["streamlit"] = _make_streamlit_stub()
    try:
        yield
    finally:
        if saved is None:
            sys.modules.pop("streamlit", None)
        else:
            sys.modules["streamlit"] = saved


def smoke(script_relpath: str) -> None:
    target = Path(__file__).parent / script_relpath
    spec = importlib.util.spec_from_file_location("_smoke_target", target)
    mod = importlib.util.module_from_spec(spec)
    with patch_streamlit():
        spec.loader.exec_module(mod)
        if hasattr(mod, "main"):
            mod.main()
    print(f"[OK] {script_relpath} 通过 streamlit stub 烟测")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python _streamlit_smoke.py <script_filename>")
        sys.exit(2)
    smoke(sys.argv[1])
