#!/usr/bin/env python3
"""
TTFT / TTFR 基准测试主入口

完全独立脚本 — 不依赖仓库根目录的 main.py / client.py / metrics.py。
通过 argparse 接收参数，支持从 config.yaml 加载默认值。
结果以 JSON 格式保存到 reports/ 目录。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv

# 将 scripts/ 目录加入 sys.path 以支持直接运行时的 import
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from llm_client import LLMClient  # noqa: E402
from metrics import (  # noqa: E402
    BatchSummary,
    TestResult,
    calculate_tps,
    summarize_results,
)

# 仓库根目录：scripts/ -> ttft-ttfr-testing/ -> skills/ -> .github/ -> repo root
REPO_ROOT = _SCRIPT_DIR.parents[3]
# Skill 目录：scripts/ -> ttft-ttfr-testing/
SKILL_DIR = _SCRIPT_DIR.parent


# ------------------------------------------------------------------
# 配置加载
# ------------------------------------------------------------------

def load_config(config_path: Optional[str] = None) -> dict:
    """加载 YAML 配置文件，返回字典。"""
    candidates = (
        [config_path]
        if config_path
        else [
            str(SKILL_DIR / "config.yaml"),
            str(REPO_ROOT / "config.yaml"),
            str(REPO_ROOT / "config.yml"),
        ]
    )
    for p in candidates:
        if p and Path(p).is_file():
            with open(p, encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
                cfg["_config_file"] = p
                return cfg
    if config_path:
        print(f"错误：配置文件不存在 — {config_path}", file=sys.stderr)
        sys.exit(1)
    return {}


def load_prompts_from_file(file_path: str) -> list[str]:
    """从文件加载提示词（每行一个，忽略空行和 # 注释）。"""
    path = Path(file_path)
    if not path.is_file():
        print(f"错误：提示词文件不存在 — {file_path}", file=sys.stderr)
        sys.exit(1)
    prompts: list[str] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                prompts.append(line)
    if not prompts:
        print(f"错误：文件中没有有效的提示词 — {file_path}", file=sys.stderr)
        sys.exit(1)
    return prompts


# ------------------------------------------------------------------
# 测试执行
# ------------------------------------------------------------------

def run_single_test(
    client: LLMClient, prompt: str, streaming: bool
) -> TestResult:
    response = client.call_api_stream(prompt) if streaming else client.call_api(prompt)

    if response.success:
        tps = None
        if response.tokens and response.timing:
            tps = calculate_tps(
                response.tokens.completion_tokens,
                response.timing.total_latency_ms,
                response.timing.ttft_ms,
            )
        return TestResult(
            prompt=prompt,
            status="success",
            response_content=response.content,
            timing=response.timing,
            tokens=response.tokens,
            tps=round(tps, 2) if tps is not None else None,
        )
    return TestResult(
        prompt=prompt,
        status="error",
        error_message=response.error_message,
    )


def run_batch_tests(
    client: LLMClient,
    prompts: list[str],
    runs: int,
    streaming: bool,
) -> list[TestResult]:
    results: list[TestResult] = []
    total = len(prompts) * runs
    for pi, prompt in enumerate(prompts):
        for ri in range(runs):
            idx = pi * runs + ri + 1
            print(
                f"  [{idx}/{total}] Prompt {pi + 1}/{len(prompts)}, "
                f"Run {ri + 1}/{runs} ...",
                flush=True,
            )
            results.append(run_single_test(client, prompt, streaming))
    return results


# ------------------------------------------------------------------
# 结果序列化
# ------------------------------------------------------------------

def _stats_dict(stats) -> Optional[dict]:
    if stats is None:
        return None
    return {
        "count": stats.count,
        "avg": stats.avg,
        "std": stats.std,
        "min": stats.min_val,
        "max": stats.max_val,
    }


def results_to_dict(
    results: list[TestResult], summary: BatchSummary
) -> dict:
    return {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_requests": summary.total_requests,
            "successful": summary.successful,
            "failed": summary.failed,
            "latency_stats": _stats_dict(summary.latency_stats),
            "ttft_stats": _stats_dict(summary.ttft_stats),
            "ttfr_stats": _stats_dict(summary.ttfr_stats),
            "output_tokens_stats": _stats_dict(summary.output_tokens_stats),
            "tps_stats": _stats_dict(summary.tps_stats),
        },
        "results": [
            {
                "prompt": r.prompt,
                "status": r.status,
                "error_message": r.error_message,
                "response_content": r.response_content,
                "latency_ms": r.timing.total_latency_ms if r.timing else None,
                "ttft_ms": r.timing.ttft_ms if r.timing else None,
                "ttfr_ms": r.timing.ttfr_ms if r.timing else None,
                "ttfr_event_type": r.timing.ttfr_event_type if r.timing else None,
                "output_tokens": r.tokens.completion_tokens if r.tokens else None,
                "tps": r.tps,
            }
            for r in results
        ],
    }


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="TTFT/TTFR 基准测试工具（独立版）",
    )
    p.add_argument("--config", "-c", help="配置文件路径（默认使用仓库根目录 config.yaml）")
    p.add_argument("--endpoint", "-e", help="LLM API 终结点 URL")
    p.add_argument("--api-key", "-k", help="API 密钥（也可通过 LLM_API_KEY 环境变量设置）")
    p.add_argument("--model", "-m", help="模型名称")
    p.add_argument("--prompt", "-p", help="单个提示词")
    p.add_argument("--prompt-file", "-f", help="提示词文件路径（每行一个）")
    p.add_argument("--runs", "-r", type=int, help="每个提示词的测试次数（默认 1）")
    p.add_argument("--timeout", "-t", type=float, help="请求超时（秒，默认 120）")
    p.add_argument("--streaming", "-s", action="store_true", default=None, help="使用 streaming 模式")
    p.add_argument("--reasoning-effort", choices=["low", "medium", "high"], help="推理强度")
    p.add_argument("--reasoning-summary", choices=["auto", "detailed", "concise"], help="推理摘要模式")
    p.add_argument("--max-tokens", type=int, help="最大输出 token 数")
    p.add_argument("--no-cache", action="store_true", default=None, help="禁用 API 端缓存")
    p.add_argument("--json", dest="json_output", action="store_true", help="仅输出 JSON（不显示进度）")
    p.add_argument("--output", "-o", help="输出文件路径（默认自动保存到 reports/）")
    return p


def main() -> int:
    # 加载 .env
    env_path = REPO_ROOT / ".env"
    if env_path.is_file():
        load_dotenv(env_path)

    args = build_parser().parse_args()

    # 加载并合并配置
    cfg = load_config(args.config)
    def _get(key: str, default=None):
        cli_val = getattr(args, key.replace("-", "_"), None)
        if cli_val is not None:
            return cli_val
        return cfg.get(key, default)

    endpoint = _get("endpoint")
    api_key = _get("api_key") or _get("api-key") or os.environ.get("LLM_API_KEY")
    model = _get("model")
    prompt = _get("prompt")
    prompt_file = _get("prompt_file") or _get("prompt-file")
    streaming = _get("streaming", False)
    runs = _get("runs", 1)
    timeout = _get("timeout", 120.0)
    reasoning_effort = _get("reasoning_effort") or _get("reasoning-effort")
    reasoning_summary = _get("reasoning_summary") or _get("reasoning-summary")
    max_tokens = _get("max_tokens") or _get("max-tokens")
    no_cache = _get("no_cache", False)
    json_output = args.json_output
    output = args.output

    # 验证
    for name, val in [("endpoint", endpoint), ("model", model)]:
        if not val:
            print(f"错误：必须指定 --{name} 或在 config.yaml 中配置", file=sys.stderr)
            return 1
    if not api_key:
        print("错误：必须指定 --api-key 或设置 LLM_API_KEY 环境变量", file=sys.stderr)
        return 1
    if not prompt and not prompt_file:
        print("错误：必须指定 --prompt 或 --prompt-file", file=sys.stderr)
        return 1

    prompts = [prompt] if prompt else load_prompts_from_file(prompt_file)

    # 显示配置
    if not json_output:
        print("=" * 60)
        print("TTFT/TTFR 基准测试")
        print("=" * 60)
        print(f"  终结点 : {endpoint}")
        print(f"  模型   : {model}")
        print(f"  模式   : {'Streaming' if streaming else 'Non-streaming'}")
        print(f"  提示词 : {len(prompts)} 条 × {runs} 次 = {len(prompts) * runs} 次测试")
        if reasoning_effort:
            print(f"  推理强度: {reasoning_effort}")
        if reasoning_summary:
            print(f"  推理摘要: {reasoning_summary}")
        print("=" * 60)

    # 创建客户端并执行测试
    client = LLMClient(
        endpoint=endpoint,
        api_key=api_key,
        model=model,
        timeout=timeout,
        reasoning_effort=reasoning_effort,
        reasoning_summary=reasoning_summary,
        max_tokens=max_tokens,
        no_cache=no_cache,
    )

    results = run_batch_tests(client, prompts, runs, streaming)
    summary = summarize_results(results)
    result_dict = results_to_dict(results, summary)

    # JSON 输出
    if json_output:
        print(json.dumps(result_dict, ensure_ascii=False, indent=2))

    # 保存文件
    result_dir = REPO_ROOT / "reports"
    result_dir.mkdir(exist_ok=True)

    if output:
        out_path = Path(output)
        if not out_path.parent.name:
            out_path = result_dir / out_path
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        effort_tag = f"_{reasoning_effort}" if reasoning_effort else ""
        safe_model = model.replace("/", "_").replace(" ", "_")
        out_path = result_dir / f"{safe_model}{effort_tag}_{ts}.json"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result_dict, f, ensure_ascii=False, indent=2)

    if not json_output:
        print(f"\n✅ 结果已保存到: {out_path}")

    return 1 if summary.failed > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
