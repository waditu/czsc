"""LLM candidate generation for auto-czsc-quant."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests

from auto_quant.schema import AutoQuantConfig


def load_env_file(path: Path = Path(".env")) -> None:
    """Load missing environment variables from a .env file."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def parse_candidate_text(text: str) -> list[dict[str, Any]]:
    """Parse model output as JSONL or a JSON array."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()

    if stripped.startswith("["):
        data = json.loads(stripped)
        if not isinstance(data, list):
            raise ValueError("LLM JSON 输出必须是数组或 JSONL")
        return [item for item in data if isinstance(item, dict)]

    rows: list[dict[str, Any]] = []
    for line in stripped.splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _anthropic_messages(config: AutoQuantConfig, prompt: str) -> str:
    load_env_file()
    api_key = os.environ.get(config.llm_api_key_env, "")
    base_url = os.environ.get(config.llm_base_url_env, "").rstrip("/")
    model = os.environ.get(config.llm_model_env, config.llm_model)
    if not api_key:
        raise RuntimeError(f"未找到 {config.llm_api_key_env}，请在环境变量或 .env 中配置 LLM API key")
    if not base_url:
        raise RuntimeError(f"未找到 {config.llm_base_url_env}，请在环境变量或 .env 中配置 LLM base URL")
    if not model:
        raise RuntimeError(f"未找到 {config.llm_model_env}，请在环境变量或 .env 中配置 LLM model")

    if base_url.endswith("/messages"):
        url = base_url
    elif base_url.endswith("/v1"):
        url = f"{base_url}/messages"
    else:
        url = f"{base_url}/v1/messages"
    payload = {
        "model": model,
        "max_tokens": config.llm_max_tokens,
        "temperature": config.llm_temperature,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "content-type": "application/json",
        "x-api-key": api_key,
        "authorization": f"Bearer {api_key}",
        "anthropic-version": "2023-06-01",
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=config.llm_timeout)
    if resp.status_code >= 400:
        raise RuntimeError(f"LLM 请求失败: HTTP {resp.status_code} {resp.text[:300]}")
    data = resp.json()
    parts = data.get("content", [])
    text = "\n".join(part.get("text", "") for part in parts if isinstance(part, dict))
    if not text.strip():
        raise RuntimeError("LLM 响应为空")
    return text


def build_mutation_prompt(config: AutoQuantConfig, baseline_position: dict[str, Any]) -> str:
    """Build a strict prompt for complete Position JSONL candidates."""
    return f"""你是 CZSC 策略配置研究助手。请基于下面 baseline Position 生成最多 {config.llm_candidate_count} 个候选。

只输出 JSONL，不要输出解释、Markdown 或代码块。每行格式：
{{"id":"trial_001","hypothesis":"一句话说明本候选要验证的结构假设","position":{{完整 CZSC Position JSON}}}}

硬性要求：
- 每个 position 必须能被 czsc.Position.load 或 czsc.Position.from_json 加载。
- 不要修改 symbol；T+0 字段使用 `T0`。
- opens 不得为空；每个 hypothesis 必须非空。
- 可以调整 opens/exits、signals_all/signals_any/signals_not、interval、timeout、stop_loss、T0。
- 不要引用明显不存在的字段；优先做小步、可解释的结构变化。

baseline Position:
{json.dumps(baseline_position, ensure_ascii=False, indent=2)}

补充约束：
{config.llm_extra_prompt}
"""


def generate_llm_candidates(config: AutoQuantConfig) -> tuple[list[dict[str, Any]], str]:
    """Call the configured LLM and return candidate rows plus raw text."""
    if not config.baseline_position_path:
        raise ValueError("candidate_mode=llm 时必须配置 baseline_position_path")
    baseline = json.loads(config.baseline_position_path.read_text(encoding="utf-8"))
    prompt = build_mutation_prompt(config, baseline)
    raw = _anthropic_messages(config, prompt)
    return parse_candidate_text(raw), raw
