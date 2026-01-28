#!/usr/bin/env python3
"""
LLM 响应时间测试工具

测试大模型 API 的响应时间、首 token 延迟（TTFT）和 token 生成速度。
支持批量测试、streaming/non-streaming 模式、结果导出。

使用示例：
    # 单次测试
    python main.py --endpoint "https://api.openai.com/v1/chat/completions" \
                   --api-key "sk-xxx" \
                   --model "gpt-4" \
                   --prompt "Hello, how are you?"

    # 批量测试（从文件读取）
    python main.py --endpoint "https://api.openai.com/v1/chat/completions" \
                   --api-key "sk-xxx" \
                   --model "gpt-4" \
                   --prompt-file prompts.txt \
                   --runs 3 \
                   --streaming \
                   --output results.json
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

import click
import yaml
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich import box

from client import LLMClient
from metrics import TestResult, calculate_tps, summarize_results, BatchSummary, AggregatedStats


console = Console()

# 默认配置文件路径
DEFAULT_CONFIG_PATHS = [
    "config.yaml",
    "config.yml",
    os.path.expanduser("~/.llmtest/config.yaml"),
]


def load_config(config_path: Optional[str] = None) -> dict:
    """
    加载配置文件
    
    Args:
        config_path: 配置文件路径，如果为 None 则尝试默认路径
        
    Returns:
        配置字典
    """
    paths_to_try = [config_path] if config_path else DEFAULT_CONFIG_PATHS
    
    for path in paths_to_try:
        if path and Path(path).exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f) or {}
                    config["_config_file"] = path  # 记录使用的配置文件
                    return config
            except yaml.YAMLError as e:
                raise click.ClickException(f"配置文件解析失败：{e}")
    
    if config_path:
        raise click.ClickException(f"配置文件不存在：{config_path}")
    
    return {}  # 没有找到配置文件，返回空字典


def merge_config_with_cli(
    config: dict,
    cli_values: dict
) -> dict:
    """
    合并配置文件和命令行参数（命令行优先）
    
    Args:
        config: 配置文件中的配置
        cli_values: 命令行传入的参数
        
    Returns:
        合并后的配置
    """
    merged = config.copy()
    
    # 命令行参数覆盖配置文件
    for key, value in cli_values.items():
        if value is not None and value != () and value != False:
            merged[key] = value
        elif key not in merged:
            merged[key] = value
    
    return merged


def load_prompts_from_file(file_path: str) -> list[str]:
    """从文件加载提示词（每行一个）"""
    path = Path(file_path)
    if not path.exists():
        raise click.ClickException(f"文件不存在：{file_path}")
    
    prompts = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):  # 忽略空行和注释
                prompts.append(line)
    
    if not prompts:
        raise click.ClickException(f"文件中没有有效的提示词：{file_path}")
    
    return prompts


def run_single_test(
    client: LLMClient,
    prompt: str,
    streaming: bool
) -> TestResult:
    """执行单次测试"""
    if streaming:
        response = client.call_api_stream(prompt)
    else:
        response = client.call_api(prompt)
    
    if response.success:
        tps = None
        if response.tokens and response.timing:
            tps = calculate_tps(
                response.tokens.completion_tokens,
                response.timing.total_latency_ms
            )
        
        return TestResult(
            prompt=prompt,
            status="success",
            response_content=response.content,
            timing=response.timing,
            tokens=response.tokens,
            tps=round(tps, 2) if tps else None
        )
    else:
        return TestResult(
            prompt=prompt,
            status="error",
            error_message=response.error_message
        )


def run_batch_tests(
    client: LLMClient,
    prompts: list[str],
    runs: int,
    streaming: bool
) -> list[TestResult]:
    """执行批量测试"""
    results: list[TestResult] = []
    total_tests = len(prompts) * runs
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("测试进行中...", total=total_tests)
        
        for prompt_idx, prompt in enumerate(prompts):
            for run_idx in range(runs):
                progress.update(
                    task,
                    description=f"Prompt {prompt_idx + 1}/{len(prompts)}, Run {run_idx + 1}/{runs}"
                )
                
                result = run_single_test(client, prompt, streaming)
                results.append(result)
                
                progress.advance(task)
    
    return results


def display_results_table(results: list[TestResult], streaming: bool):
    """以表格形式显示测试结果"""
    table = Table(
        title="测试结果详情",
        box=box.ROUNDED,
        show_lines=True
    )
    
    table.add_column("序号", style="cyan", justify="center", width=6)
    table.add_column("提示词", style="white", max_width=30, overflow="ellipsis")
    table.add_column("状态", style="bold", justify="center", width=8)
    table.add_column("延迟(ms)", style="yellow", justify="right", width=12)
    if streaming:
        table.add_column("TTFT(ms)", style="magenta", justify="right", width=12)
    table.add_column("输出Tokens", style="green", justify="right", width=12)
    table.add_column("TPS", style="blue", justify="right", width=10)
    
    for idx, result in enumerate(results, 1):
        status_style = "green" if result.status == "success" else "red"
        status_text = "✓ 成功" if result.status == "success" else "✗ 失败"
        
        row = [
            str(idx),
            result.prompt[:30] + "..." if len(result.prompt) > 30 else result.prompt,
            f"[{status_style}]{status_text}[/{status_style}]"
        ]
        
        if result.status == "success":
            row.append(f"{result.timing.total_latency_ms:.2f}" if result.timing else "-")
            if streaming:
                row.append(f"{result.timing.ttft_ms:.2f}" if result.timing and result.timing.ttft_ms else "-")
            row.append(str(result.tokens.completion_tokens) if result.tokens else "-")
            row.append(f"{result.tps:.2f}" if result.tps else "-")
        else:
            row.append("-")
            if streaming:
                row.append("-")
            row.append("-")
            row.append("-")
        
        table.add_row(*row)
    
    console.print(table)


def display_summary(summary: BatchSummary, streaming: bool):
    """显示测试汇总"""
    def format_stats(stats: Optional[AggregatedStats], unit: str = "") -> str:
        if not stats:
            return "-"
        return f"平均: {stats.avg}{unit} | 标准差: {stats.std}{unit} | 范围: [{stats.min_val}, {stats.max_val}]{unit}"
    
    summary_text = f"""
[bold]请求统计[/bold]
  总请求数: {summary.total_requests}
  成功: [green]{summary.successful}[/green]
  失败: [red]{summary.failed}[/red]
  成功率: {summary.successful / summary.total_requests * 100:.1f}%

[bold]性能指标[/bold]
  延迟: {format_stats(summary.latency_stats, " ms")}
"""
    
    if streaming and summary.ttft_stats:
        summary_text += f"  TTFT: {format_stats(summary.ttft_stats, ' ms')}\n"
    
    summary_text += f"""  输出Tokens: {format_stats(summary.output_tokens_stats)}
  TPS: {format_stats(summary.tps_stats, " tokens/s")}
"""
    
    console.print(Panel(summary_text, title="📊 测试汇总", border_style="blue"))


def results_to_dict(results: list[TestResult], summary: BatchSummary) -> dict:
    """将结果转换为字典格式（用于 JSON 输出）"""
    def stats_to_dict(stats: Optional[AggregatedStats]) -> Optional[dict]:
        if not stats:
            return None
        return {
            "count": stats.count,
            "avg": stats.avg,
            "std": stats.std,
            "min": stats.min_val,
            "max": stats.max_val
        }
    
    return {
        "summary": {
            "total_requests": summary.total_requests,
            "successful": summary.successful,
            "failed": summary.failed,
            "latency_stats": stats_to_dict(summary.latency_stats),
            "ttft_stats": stats_to_dict(summary.ttft_stats),
            "output_tokens_stats": stats_to_dict(summary.output_tokens_stats),
            "tps_stats": stats_to_dict(summary.tps_stats)
        },
        "results": [
            {
                "prompt": r.prompt,
                "status": r.status,
                "error_message": r.error_message,
                "response_content": r.response_content,
                "latency_ms": r.timing.total_latency_ms if r.timing else None,
                "ttft_ms": r.timing.ttft_ms if r.timing else None,
                "output_tokens": r.tokens.completion_tokens if r.tokens else None,
                "tps": r.tps
            }
            for r in results
        ]
    }


@click.command()
@click.option(
    "--config", "-c",
    type=click.Path(),
    help="配置文件路径（默认自动查找 config.yaml）"
)
@click.option(
    "--endpoint", "-e",
    help="LLM API 终结点 URL（例如：https://api.openai.com/v1/chat/completions）"
)
@click.option(
    "--api-key", "-k",
    envvar="LLM_API_KEY",
    help="API 密钥（也可通过 LLM_API_KEY 环境变量设置）"
)
@click.option(
    "--model", "-m",
    help="模型名称（例如：gpt-4, gpt-3.5-turbo）"
)
@click.option(
    "--prompt", "-p",
    help="单个提示词（与 --prompt-file 二选一）"
)
@click.option(
    "--prompt-file", "-f",
    type=click.Path(),
    help="提示词文件路径，每行一个提示词（与 --prompt 二选一）"
)
@click.option(
    "--streaming", "-s",
    is_flag=True,
    default=None,
    help="使用 streaming 模式（可测量 TTFT）"
)
@click.option(
    "--runs", "-r",
    type=int,
    help="每个提示词的测试次数（默认：1）"
)
@click.option(
    "--timeout", "-t",
    type=float,
    help="请求超时时间，单位秒（默认：120）"
)
@click.option(
    "--output", "-o",
    type=click.Path(),
    help="输出结果到 JSON 文件"
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    default=None,
    help="仅输出 JSON 格式（不显示表格）"
)
@click.option(
    "--reasoning-effort",
    type=click.Choice(["low", "medium", "high"]),
    help="推理强度（适用于 o1 等推理模型）"
)
@click.option(
    "--max-tokens",
    type=int,
    help="最大输出 token 数"
)
@click.option(
    "--no-cache",
    is_flag=True,
    default=None,
    help="禁用 API 端缓存，确保每次请求都重新计算"
)
def main(
    config: Optional[str],
    endpoint: Optional[str],
    api_key: Optional[str],
    model: Optional[str],
    prompt: Optional[str],
    prompt_file: Optional[str],
    streaming: Optional[bool],
    runs: Optional[int],
    timeout: Optional[float],
    output: Optional[str],
    json_output: Optional[bool],
    reasoning_effort: Optional[str],
    max_tokens: Optional[int],
    no_cache: Optional[bool]
):
    """
    LLM 响应时间测试工具
    
    测试大模型 API 的响应时间、首 token 延迟（TTFT）和 token 生成速度。
    支持从配置文件读取参数，命令行参数优先级高于配置文件。
    """
    # 加载配置文件
    file_config = load_config(config)
    
    # 合并配置文件和命令行参数（命令行优先）
    cli_values = {
        "endpoint": endpoint,
        "api_key": api_key,
        "model": model,
        "prompt": prompt,
        "prompt_file": prompt_file,
        "streaming": streaming,
        "runs": runs,
        "timeout": timeout,
        "output": output,
        "json_output": json_output,
        "reasoning_effort": reasoning_effort,
        "max_tokens": max_tokens,
        "no_cache": no_cache,
    }
    cfg = merge_config_with_cli(file_config, cli_values)
    
    # 提取配置值
    endpoint = cfg.get("endpoint")
    api_key = cfg.get("api_key")
    model = cfg.get("model")
    prompt = cfg.get("prompt")
    prompt_file = cfg.get("prompt_file")
    streaming = cfg.get("streaming", False)
    runs = cfg.get("runs", 1)
    timeout = cfg.get("timeout", 120.0)
    output = cfg.get("output")
    json_output = cfg.get("json_output", False)
    reasoning_effort = cfg.get("reasoning_effort")
    max_tokens = cfg.get("max_tokens")
    no_cache = cfg.get("no_cache", False)
    config_file_used = cfg.get("_config_file")
    
    # 验证必需参数
    if not endpoint:
        raise click.ClickException("必须指定 --endpoint 或在配置文件中设置 endpoint")
    if not api_key:
        raise click.ClickException("必须指定 --api-key 或在配置文件中设置 api_key，也可通过 LLM_API_KEY 环境变量设置")
    if not model:
        raise click.ClickException("必须指定 --model 或在配置文件中设置 model")
    
    # 验证提示词输入
    if not prompt and not prompt_file:
        raise click.ClickException("必须指定 --prompt 或 --prompt-file，也可在配置文件中设置")
    
    if prompt and prompt_file:
        raise click.ClickException("--prompt 和 --prompt-file 不能同时使用")
    
    # 加载提示词
    if prompt:
        prompts = [prompt]
    else:
        prompts = load_prompts_from_file(prompt_file)
    
    # 显示测试配置
    if not json_output:
        config_info = f"[bold]配置文件:[/bold] {config_file_used}\n" if config_file_used else ""
        model_params = ""
        if reasoning_effort:
            model_params += f"\n[bold]推理强度:[/bold] {reasoning_effort}"
        if max_tokens:
            model_params += f"\n[bold]最大Tokens:[/bold] {max_tokens}"
        console.print(Panel(
            f"""{config_info}[bold]终结点:[/bold] {endpoint}
[bold]模型:[/bold] {model}{model_params}
[bold]模式:[/bold] {"Streaming" if streaming else "Non-streaming"}
[bold]提示词数量:[/bold] {len(prompts)}
[bold]每个提示词测试次数:[/bold] {runs}
[bold]总测试次数:[/bold] {len(prompts) * runs}
[bold]超时时间:[/bold] {timeout}s""",
            title="🔧 测试配置",
            border_style="green"
        ))
        console.print()
    
    # 创建客户端
    client = LLMClient(
        endpoint=endpoint,
        api_key=api_key,
        model=model,
        timeout=timeout,
        reasoning_effort=reasoning_effort,
        max_tokens=max_tokens,
        no_cache=no_cache
    )
    
    # 执行测试
    results = run_batch_tests(client, prompts, runs, streaming)
    
    # 汇总结果
    summary = summarize_results(results)
    
    # 输出结果
    result_dict = results_to_dict(results, summary)
    
    if json_output:
        # 纯 JSON 输出
        print(json.dumps(result_dict, ensure_ascii=False, indent=2))
    else:
        # 显示表格和汇总
        console.print()
        display_results_table(results, streaming)
        console.print()
        display_summary(summary, streaming)
    
    # 保存到文件
    if output:
        output_path = Path(output)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result_dict, f, ensure_ascii=False, indent=2)
        
        if not json_output:
            console.print(f"\n✅ 结果已保存到: [cyan]{output}[/cyan]")
    
    # 如果有失败的测试，返回非零退出码
    if summary.failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
