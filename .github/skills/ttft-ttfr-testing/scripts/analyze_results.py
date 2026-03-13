#!/usr/bin/env python3
"""
TTFT / TTFR 测试结果分析模块

读取 JSON 结果文件，按内置阈值对 TTFT、TTFR、TPS、稳定性进行评级，
生成 Markdown 格式分析报告和优化建议。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

# 仓库根目录
_SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = _SCRIPT_DIR.parents[3]

# ------------------------------------------------------------------
# 阈值定义
# ------------------------------------------------------------------

TTFT_THRESHOLDS = {
    "excellent": 500,   # < 500 ms
    "normal": 1500,     # 500–1500 ms
}

TTFR_THRESHOLDS = {
    "excellent": 1000,  # < 1000 ms
    "normal": 3000,     # 1000–3000 ms
}

TPS_THRESHOLDS = {
    "excellent": 50,    # > 50 tokens/s
    "normal": 20,       # 20–50 tokens/s
}

CV_THRESHOLDS = {
    "stable": 0.10,     # CV < 10%
    "moderate": 0.30,   # CV 10–30%
}


# ------------------------------------------------------------------
# 评级函数
# ------------------------------------------------------------------

def _rate_lower_is_better(value: float, thresholds: dict) -> str:
    if value < thresholds["excellent"]:
        return "🟢 优秀"
    if value < thresholds["normal"]:
        return "🟡 正常"
    return "🔴 需优化"


def _rate_higher_is_better(value: float, thresholds: dict) -> str:
    if value > thresholds["excellent"]:
        return "🟢 优秀"
    if value > thresholds["normal"]:
        return "🟡 正常"
    return "🔴 需优化"


def _rate_cv(cv: float) -> str:
    if cv < CV_THRESHOLDS["stable"]:
        return "🟢 稳定"
    if cv < CV_THRESHOLDS["moderate"]:
        return "🟡 一般"
    return "🔴 不稳定"


def _cv(stats: dict) -> Optional[float]:
    """计算变异系数 (CV = std / avg)。"""
    avg = stats.get("avg", 0)
    std = stats.get("std", 0)
    if avg > 0:
        return round(std / avg, 4)
    return None


# ------------------------------------------------------------------
# 结果加载
# ------------------------------------------------------------------

def load_result(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def find_latest_result(result_dir: Path | None = None) -> Optional[Path]:
    d = result_dir or (REPO_ROOT / "reports")
    if not d.is_dir():
        return None
    files = [p for p in d.glob("*.json") if p.is_file()]
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


# ------------------------------------------------------------------
# 分析函数
# ------------------------------------------------------------------

def analyze_ttft(stats: Optional[dict]) -> list[str]:
    if not stats:
        return ["TTFT 数据不可用（可能未启用 streaming 模式）。"]
    avg = stats["avg"]
    rating = _rate_lower_is_better(avg, TTFT_THRESHOLDS)
    lines = [
        f"**TTFT（首 Token 延迟）**: {avg} ms  —  {rating}",
        f"  - 范围: {stats['min']}–{stats['max']} ms | 标准差: {stats['std']} ms",
    ]
    cv = _cv(stats)
    if cv is not None:
        lines.append(f"  - 变异系数 CV: {cv:.2%}  —  {_rate_cv(cv)}")
    return lines


def analyze_ttfr(
    ttfr_stats: Optional[dict], ttft_stats: Optional[dict]
) -> list[str]:
    if not ttfr_stats:
        return ["TTFR 数据不可用（可能未启用 reasoning_summary 或模型不支持推理）。"]
    avg = ttfr_stats["avg"]
    rating = _rate_lower_is_better(avg, TTFR_THRESHOLDS)
    lines = [
        f"**TTFR（首推理延迟）**: {avg} ms  —  {rating}",
        f"  - 范围: {ttfr_stats['min']}–{ttfr_stats['max']} ms | 标准差: {ttfr_stats['std']} ms",
    ]
    if ttft_stats and ttft_stats.get("avg"):
        gap = round(avg - ttft_stats["avg"], 2)
        lines.append(
            f"  - TTFR − TTFT 差值: {gap} ms"
            + ("（推理启动在首 token 之前）" if gap < 0 else "")
        )
    cv = _cv(ttfr_stats)
    if cv is not None:
        lines.append(f"  - 变异系数 CV: {cv:.2%}  —  {_rate_cv(cv)}")
    return lines


def analyze_tps(stats: Optional[dict]) -> list[str]:
    if not stats:
        return ["TPS 数据不可用。"]
    avg = stats["avg"]
    rating = _rate_higher_is_better(avg, TPS_THRESHOLDS)
    lines = [
        f"**TPS（Token 生成速度）**: {avg} tokens/s  —  {rating}",
        f"  - 范围: {stats['min']}–{stats['max']} tokens/s | 标准差: {stats['std']}",
    ]
    cv = _cv(stats)
    if cv is not None:
        lines.append(f"  - 变异系数 CV: {cv:.2%}  —  {_rate_cv(cv)}")
    return lines


def analyze_latency(stats: Optional[dict]) -> list[str]:
    if not stats:
        return ["延迟数据不可用。"]
    avg = stats["avg"]
    lines = [
        f"**总延迟**: {avg} ms",
        f"  - 范围: {stats['min']}–{stats['max']} ms | 标准差: {stats['std']} ms",
    ]
    cv = _cv(stats)
    if cv is not None:
        lines.append(f"  - 变异系数 CV: {cv:.2%}  —  {_rate_cv(cv)}")
    return lines


# ------------------------------------------------------------------
# 优化建议
# ------------------------------------------------------------------

def generate_suggestions(data: dict) -> list[str]:
    """根据分析结果生成优化建议。"""
    suggestions: list[str] = []
    s = data.get("summary", {})

    ttft = s.get("ttft_stats")
    if ttft and ttft["avg"] >= TTFT_THRESHOLDS["normal"]:
        suggestions.append(
            "⚡ TTFT 偏高 — 考虑：缩短 prompt 长度、使用更快的模型变体、"
            "启用 KV-cache、减少 reasoning_effort、检查网络延迟"
        )

    ttfr = s.get("ttfr_stats")
    if ttfr and ttfr["avg"] >= TTFR_THRESHOLDS["normal"]:
        suggestions.append(
            "🧠 TTFR 偏高 — 考虑：降低 reasoning_effort（如 high → medium）、"
            "使用 concise 模式的 reasoning_summary、简化问题复杂度"
        )

    tps = s.get("tps_stats")
    if tps and tps["avg"] < TPS_THRESHOLDS["normal"]:
        suggestions.append(
            "📉 TPS 偏低 — 考虑：使用更快的推理基础设施、"
            "减小 max_tokens、检查 API 端限流策略"
        )

    # 稳定性检查
    for name, stats in [
        ("TTFT", ttft),
        ("TTFR", ttfr),
        ("TPS", tps),
    ]:
        if stats:
            cv = _cv(stats)
            if cv and cv >= CV_THRESHOLDS["moderate"]:
                suggestions.append(
                    f"📊 {name} 波动较大 (CV={cv:.2%}) — "
                    f"考虑：增加测试轮次、启用 no_cache 排除缓存影响、"
                    f"检查 API 端是否存在负载均衡抖动"
                )

    if s.get("failed", 0) > 0:
        rate = s["failed"] / s["total_requests"] * 100
        suggestions.append(
            f"❌ 有 {s['failed']} 次请求失败 ({rate:.1f}%) — "
            f"检查 API 密钥、终结点 URL、网络连通性、速率限制"
        )

    if not suggestions:
        suggestions.append("✅ 所有指标均在正常范围内，暂无优化建议。")

    return suggestions


# ------------------------------------------------------------------
# 报告生成
# ------------------------------------------------------------------

def generate_report(data: dict) -> str:
    """生成 Markdown 格式的分析报告。"""
    s = data.get("summary", {})
    lines: list[str] = []

    lines.append("# TTFT / TTFR 基准测试报告\n")

    if data.get("timestamp"):
        lines.append(f"**测试时间**: {data['timestamp']}\n")

    # 概览
    lines.append("## 概览\n")
    lines.append(f"- 总请求数: {s.get('total_requests', 0)}")
    lines.append(f"- 成功: {s.get('successful', 0)}")
    lines.append(f"- 失败: {s.get('failed', 0)}")
    total = s.get("total_requests", 1)
    lines.append(f"- 成功率: {s.get('successful', 0) / total * 100:.1f}%\n")

    # 指标详情
    lines.append("## 指标分析\n")

    for section in [
        analyze_ttft(s.get("ttft_stats")),
        analyze_ttfr(s.get("ttfr_stats"), s.get("ttft_stats")),
        analyze_tps(s.get("tps_stats")),
        analyze_latency(s.get("latency_stats")),
    ]:
        lines.extend(section)
        lines.append("")

    # 优化建议
    lines.append("## 优化建议\n")
    for suggestion in generate_suggestions(data):
        lines.append(f"- {suggestion}")
    lines.append("")

    return "\n".join(lines)


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="分析 TTFT/TTFR 基准测试结果")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--result-file", help="指定结果 JSON 文件路径")
    group.add_argument("--latest", action="store_true", help="自动读取 reports/ 下最新的结果文件")
    p.add_argument("--result-dir", help="result 目录路径（默认仓库根目录下 reports/）")
    return p


def main() -> int:
    args = build_parser().parse_args()

    if args.latest:
        result_dir = Path(args.result_dir) if args.result_dir else None
        path = find_latest_result(result_dir)
        if not path:
            print("错误：reports/ 目录下没有找到 JSON 结果文件", file=sys.stderr)
            return 1
        print(f"读取最新结果: {path}\n")
    else:
        path = Path(args.result_file)
        if not path.is_file():
            print(f"错误：文件不存在 — {path}", file=sys.stderr)
            return 1

    data = load_result(path)
    report = generate_report(data)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
