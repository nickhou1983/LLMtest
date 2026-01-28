"""
指标计算和统计模块
"""

import statistics
from dataclasses import dataclass, field
from typing import Optional

import tiktoken


@dataclass
class TimingMetrics:
    """时间指标"""
    total_latency_ms: float  # 总延迟（毫秒）
    ttft_ms: Optional[float] = None  # 首 token 时间（仅 streaming 模式）


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
    tps: Optional[float] = None  # Tokens Per Second


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
    output_tokens_stats: Optional[AggregatedStats] = None
    tps_stats: Optional[AggregatedStats] = None


def count_tokens_tiktoken(text: str, model: str = "gpt-4") -> int:
    """
    使用 tiktoken 计算文本的 token 数量
    
    Args:
        text: 要计算的文本
        model: 模型名称，用于选择正确的编码器
        
    Returns:
        token 数量
    """
    try:
        # 尝试获取模型对应的编码器
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            # 如果模型不存在，使用 cl100k_base（GPT-4/3.5 使用的编码）
            encoding = tiktoken.get_encoding("cl100k_base")
        
        return len(encoding.encode(text))
    except Exception:
        # 降级：粗略估计（英文约 4 字符/token，中文约 1.5 字符/token）
        return len(text) // 3


def calculate_tps(tokens: int, latency_ms: float) -> float:
    """
    计算每秒生成的 token 数量
    
    Args:
        tokens: 生成的 token 数量
        latency_ms: 延迟时间（毫秒）
        
    Returns:
        每秒 token 数
    """
    if latency_ms <= 0:
        return 0.0
    return tokens / (latency_ms / 1000.0)


def aggregate_values(values: list[float]) -> AggregatedStats:
    """
    计算一组数值的统计指标
    
    Args:
        values: 数值列表
        
    Returns:
        聚合统计结果
    """
    if not values:
        return AggregatedStats()
    
    count = len(values)
    avg = statistics.mean(values)
    std = statistics.stdev(values) if count > 1 else 0.0
    min_val = min(values)
    max_val = max(values)
    
    return AggregatedStats(
        count=count,
        avg=round(avg, 2),
        std=round(std, 2),
        min_val=round(min_val, 2),
        max_val=round(max_val, 2)
    )


def summarize_results(results: list[TestResult]) -> BatchSummary:
    """
    汇总批量测试结果
    
    Args:
        results: 测试结果列表
        
    Returns:
        批量测试汇总
    """
    successful_results = [r for r in results if r.status == "success"]
    
    latencies = []
    ttfts = []
    output_tokens = []
    tps_values = []
    
    for r in successful_results:
        if r.timing:
            latencies.append(r.timing.total_latency_ms)
            if r.timing.ttft_ms is not None:
                ttfts.append(r.timing.ttft_ms)
        if r.tokens:
            output_tokens.append(r.tokens.completion_tokens)
        if r.tps is not None:
            tps_values.append(r.tps)
    
    return BatchSummary(
        total_requests=len(results),
        successful=len(successful_results),
        failed=len(results) - len(successful_results),
        latency_stats=aggregate_values(latencies) if latencies else None,
        ttft_stats=aggregate_values(ttfts) if ttfts else None,
        output_tokens_stats=aggregate_values(output_tokens) if output_tokens else None,
        tps_stats=aggregate_values(tps_values) if tps_values else None
    )
