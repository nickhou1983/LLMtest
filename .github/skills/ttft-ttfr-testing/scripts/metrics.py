"""
指标数据结构与统计计算模块

独立实现，不依赖仓库根目录的 metrics.py。
提供 TTFT/TTFR 测试所需的全部数据结构和统计函数。
"""

import statistics
from dataclasses import dataclass
from typing import Optional

try:
    import tiktoken
except ImportError:
    tiktoken = None


@dataclass
class TimingMetrics:
    """时间指标"""
    total_latency_ms: float
    ttft_ms: Optional[float] = None
    ttfr_ms: Optional[float] = None
    ttfr_event_type: Optional[str] = None


@dataclass
class TokenMetrics:
    """Token 指标"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class TestResult:
    """单次测试结果"""
    prompt: str
    status: str  # "success" | "error"
    error_message: Optional[str] = None
    response_content: Optional[str] = None
    timing: Optional[TimingMetrics] = None
    tokens: Optional[TokenMetrics] = None
    tps: Optional[float] = None


@dataclass
class AggregatedStats:
    """聚合统计结果"""
    count: int = 0
    avg: float = 0.0
    std: float = 0.0
    min_val: float = 0.0
    max_val: float = 0.0


@dataclass
class BatchSummary:
    """批量测试汇总"""
    total_requests: int = 0
    successful: int = 0
    failed: int = 0
    latency_stats: Optional[AggregatedStats] = None
    ttft_stats: Optional[AggregatedStats] = None
    ttfr_stats: Optional[AggregatedStats] = None
    output_tokens_stats: Optional[AggregatedStats] = None
    tps_stats: Optional[AggregatedStats] = None


def count_tokens_tiktoken(text: str, model: str = "gpt-4") -> int:
    """使用 tiktoken 计算文本的 token 数量，降级为字符估计。"""
    if tiktoken is None:
        return len(text) // 3

    try:
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception:
        return len(text) // 3


def calculate_tps(
    tokens: int,
    total_latency_ms: float,
    ttft_ms: Optional[float] = None,
) -> float:
    """计算每秒生成的 token 数量（排除 TTFT 时间）。"""
    if total_latency_ms <= 0:
        return 0.0
    effective_ms = total_latency_ms
    if ttft_ms is not None and 0 < ttft_ms < total_latency_ms:
        effective_ms = total_latency_ms - ttft_ms
    if effective_ms <= 0:
        return 0.0
    return tokens / (effective_ms / 1000.0)


def aggregate_values(values: list[float]) -> AggregatedStats:
    """计算一组数值的统计指标。"""
    if not values:
        return AggregatedStats()
    count = len(values)
    avg = statistics.mean(values)
    std = statistics.stdev(values) if count > 1 else 0.0
    return AggregatedStats(
        count=count,
        avg=round(avg, 2),
        std=round(std, 2),
        min_val=round(min(values), 2),
        max_val=round(max(values), 2),
    )


def summarize_results(results: list[TestResult]) -> BatchSummary:
    """汇总批量测试结果。"""
    successful = [r for r in results if r.status == "success"]

    latencies: list[float] = []
    ttfts: list[float] = []
    ttfrs: list[float] = []
    output_tokens: list[float] = []
    tps_values: list[float] = []

    for r in successful:
        if r.timing:
            latencies.append(r.timing.total_latency_ms)
            if r.timing.ttft_ms is not None:
                ttfts.append(r.timing.ttft_ms)
            if r.timing.ttfr_ms is not None:
                ttfrs.append(r.timing.ttfr_ms)
        if r.tokens:
            output_tokens.append(float(r.tokens.completion_tokens))
        if r.tps is not None:
            tps_values.append(r.tps)

    return BatchSummary(
        total_requests=len(results),
        successful=len(successful),
        failed=len(results) - len(successful),
        latency_stats=aggregate_values(latencies) if latencies else None,
        ttft_stats=aggregate_values(ttfts) if ttfts else None,
        ttfr_stats=aggregate_values(ttfrs) if ttfrs else None,
        output_tokens_stats=aggregate_values(output_tokens) if output_tokens else None,
        tps_stats=aggregate_values(tps_values) if tps_values else None,
    )
