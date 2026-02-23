# -*- coding: utf-8 -*-
"""
导入性能测试

验证 czsc 库的导入速度在合理范围内，确保不因新增依赖或错误的模块级导入
而导致导入速度显著下降，影响用户体验。
"""
import subprocess
import sys
import time


# 可接受的最大导入时间（秒）。该阈值在 CI 环境中会有一定冗余，
# 主要用于检测灾难性的回归（如在模块级误引入 Streamlit / scipy 等重型依赖）。
MAX_IMPORT_TIME_SECONDS = 10.0


def _measure_import_time(module_name: str) -> float:
    """在独立子进程中测量模块导入耗时（秒）"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            f"import time as _t; _s = _t.time(); import {module_name}; print(_t.time() - _s)",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"导入 {module_name} 失败:\n{result.stderr}"
    return float(result.stdout.strip())


def test_czsc_import_time():
    """czsc 库的导入时间应在可接受范围内"""
    elapsed = _measure_import_time("czsc")
    assert elapsed < MAX_IMPORT_TIME_SECONDS, (
        f"czsc 导入耗时 {elapsed:.2f}s，超过了阈值 {MAX_IMPORT_TIME_SECONDS}s。"
        f"请检查是否在模块级引入了重型依赖（如 streamlit、scipy、clickhouse_connect、redis 等）。"
    )


def test_heavy_dependencies_not_loaded_on_import():
    """导入 czsc 后，不应自动加载 streamlit / scipy 等重型可选依赖"""
    code = """
import sys
# 记录导入前已加载的模块（排除测试框架等）
import czsc

loaded = set(sys.modules.keys())
heavy = ["streamlit", "scipy", "clickhouse_connect", "redis", "IPython", "lightweight_charts"]
violations = [m for m in heavy if any(k == m or k.startswith(m + ".") for k in loaded)]
if violations:
    print("FAIL:" + ",".join(violations))
else:
    print("OK")
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"子进程异常:\n{result.stderr}"
    output = result.stdout.strip()
    assert output == "OK", (
        f"import czsc 后意外加载了重型依赖: {output.replace('FAIL:', '')}。"
        "这些依赖应该使用延迟导入（lazy import）。"
    )


def test_svc_lazy_loaded():
    """czsc.svc 应延迟加载（访问 czsc.svc 时才触发 streamlit 导入）"""
    code = """
import sys
import czsc

# 仅导入 czsc 本身，不访问 czsc.svc
# streamlit 不应被加载
loaded = set(sys.modules.keys())
if any(k == "streamlit" or k.startswith("streamlit.") for k in loaded):
    print("FAIL: streamlit loaded before accessing czsc.svc")
else:
    print("OK")
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"子进程异常:\n{result.stderr}"
    output = result.stdout.strip()
    assert output == "OK", output


def test_czsc_svc_accessible():
    """czsc.svc 通过延迟加载仍可正常访问"""
    import czsc
    svc = czsc.svc
    assert svc is not None
    assert hasattr(svc, "show_daily_return")
