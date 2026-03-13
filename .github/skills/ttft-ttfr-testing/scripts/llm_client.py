"""
独立 LLM API 客户端模块

支持 OpenAI Chat Completions API 和 Azure Responses API 的 streaming/non-streaming 模式。
在 streaming 模式下精确测量 TTFT（首 Token 延迟）和 TTFR（首推理延迟）。
不依赖仓库根目录的 client.py。
"""

import json
import time
from dataclasses import dataclass
from typing import Optional

import httpx

# 支持直接运行和包内 import 两种方式
try:
    from .metrics import TimingMetrics, TokenMetrics, count_tokens_tiktoken
except ImportError:
    from metrics import TimingMetrics, TokenMetrics, count_tokens_tiktoken


@dataclass
class LLMResponse:
    """LLM API 响应结果"""
    success: bool
    content: Optional[str] = None
    timing: Optional[TimingMetrics] = None
    tokens: Optional[TokenMetrics] = None
    error_message: Optional[str] = None
    raw_response: Optional[dict] = None


class LLMClient:
    """LLM API 客户端，支持双 API 格式和 TTFT/TTFR 测量。"""

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        model: str,
        timeout: float = 120.0,
        reasoning_effort: Optional[str] = None,
        reasoning_summary: Optional[str] = None,
        max_tokens: Optional[int] = None,
        no_cache: bool = False,
    ):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.reasoning_effort = reasoning_effort
        self.reasoning_summary = reasoning_summary
        self.max_tokens = max_tokens
        self.no_cache = no_cache

        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "api-key": api_key,  # Azure OpenAI 使用 api-key header
        }

        # 检测是否为 Responses API（Azure 新格式）
        self.is_responses_api = "/responses" in endpoint

    # ------------------------------------------------------------------
    # 请求体构建
    # ------------------------------------------------------------------

    def _build_request_body(self, prompt: str, stream: bool = False) -> dict:
        if self.is_responses_api:
            body: dict = {
                "model": self.model,
                "input": prompt,
                "stream": stream,
            }
            if self.reasoning_effort or self.reasoning_summary:
                reasoning: dict = {}
                if self.reasoning_effort:
                    reasoning["effort"] = self.reasoning_effort
                if self.reasoning_summary:
                    reasoning["summary"] = self.reasoning_summary
                body["reasoning"] = reasoning
            if self.max_tokens:
                body["max_output_tokens"] = self.max_tokens
            if self.no_cache:
                body["store"] = False
            return body

        # Chat Completions API
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": stream,
        }
        if self.reasoning_effort:
            body["reasoning_effort"] = self.reasoning_effort
        if self.max_tokens:
            body["max_tokens"] = self.max_tokens
        return body

    # ------------------------------------------------------------------
    # 响应解析
    # ------------------------------------------------------------------

    def _extract_tokens(self, data: dict) -> TokenMetrics:
        usage = data.get("usage", {})
        if self.is_responses_api:
            return TokenMetrics(
                prompt_tokens=usage.get("input_tokens", 0),
                completion_tokens=usage.get("output_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
            )
        return TokenMetrics(
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
        )

    def _extract_content(self, data: dict) -> str:
        if self.is_responses_api:
            parts: list[str] = []
            for item in data.get("output", []):
                if item.get("type") == "message":
                    for c in item.get("content", []):
                        if c.get("type") == "output_text":
                            parts.append(c.get("text", ""))
            return "".join(parts)

        choices = data.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "")
        return ""

    # ------------------------------------------------------------------
    # HTTP 状态码检查
    # ------------------------------------------------------------------

    @staticmethod
    def _check_status(status_code: int) -> Optional[str]:
        """返回错误消息，或 None 表示正常。"""
        if status_code == 200:
            return None
        mapping = {
            401: "认证失败：API 密钥无效或已过期",
            403: "权限不足：无法访问该模型或资源",
            429: "请求过于频繁：已触发速率限制",
        }
        if status_code in mapping:
            return mapping[status_code]
        if status_code >= 500:
            return f"服务器错误：{status_code}"
        return f"请求失败：HTTP {status_code}"

    # ------------------------------------------------------------------
    # 非流式调用
    # ------------------------------------------------------------------

    def call_api(self, prompt: str) -> LLMResponse:
        body = self._build_request_body(prompt, stream=False)
        start = time.perf_counter()

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(self.endpoint, headers=self.headers, json=body)

            latency_ms = (time.perf_counter() - start) * 1000

            err = self._check_status(resp.status_code)
            if err:
                return LLMResponse(success=False, error_message=err)

            try:
                data = resp.json()
            except (json.JSONDecodeError, ValueError) as e:
                return LLMResponse(success=False, error_message=f"JSON 解析失败：{e}")

            content = self._extract_content(data)
            tokens = self._extract_tokens(data)
            if tokens.completion_tokens == 0 and content:
                tokens.completion_tokens = count_tokens_tiktoken(content, self.model)
                tokens.total_tokens = tokens.prompt_tokens + tokens.completion_tokens

            return LLMResponse(
                success=True,
                content=content,
                timing=TimingMetrics(total_latency_ms=round(latency_ms, 2)),
                tokens=tokens,
                raw_response=data,
            )

        except httpx.TimeoutException:
            return LLMResponse(success=False, error_message=f"请求超时：超过 {self.timeout} 秒")
        except httpx.ConnectError as e:
            return LLMResponse(success=False, error_message=f"连接失败：{e}")
        except Exception as e:
            return LLMResponse(success=False, error_message=f"未知错误：{e}")

    # ------------------------------------------------------------------
    # 流式调用（SSE），精确测量 TTFT / TTFR
    # ------------------------------------------------------------------

    def call_api_stream(self, prompt: str) -> LLMResponse:
        body = self._build_request_body(prompt, stream=True)
        start = time.perf_counter()

        ttft: Optional[float] = None
        ttfr: Optional[float] = None
        ttfr_event_type: Optional[str] = None
        chunks: list[str] = []
        completion_tokens = 0

        try:
            with httpx.Client(timeout=self.timeout) as client:
                with client.stream(
                    "POST", self.endpoint, headers=self.headers, json=body
                ) as resp:
                    err = self._check_status(resp.status_code)
                    if err:
                        return LLMResponse(success=False, error_message=err)

                    for line in resp.iter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break

                        try:
                            chunk = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        if self.is_responses_api:
                            ct = chunk.get("type", "")
                            # TTFT
                            if ct == "response.output_text.delta":
                                delta = chunk.get("delta", "")
                                if delta:
                                    if ttft is None:
                                        ttft = (time.perf_counter() - start) * 1000
                                    chunks.append(delta)
                            # TTFR — reasoning 事件
                            elif ct in (
                                "response.reasoning_text.delta",
                                "response.reasoning.delta",
                            ):
                                rd = chunk.get("delta") or chunk.get("text") or ""
                                if isinstance(rd, str) and rd and ttfr is None:
                                    ttfr = (time.perf_counter() - start) * 1000
                                    ttfr_event_type = ct
                            elif ct == "response.reasoning_summary_text.delta":
                                sd = chunk.get("delta") or chunk.get("text") or ""
                                if isinstance(sd, str) and sd and ttfr is None:
                                    ttfr = (time.perf_counter() - start) * 1000
                                    ttfr_event_type = ct
                            # Token 用量
                            elif ct == "response.completed":
                                usage = chunk.get("response", {}).get("usage", {})
                                if usage:
                                    completion_tokens = usage.get("output_tokens", 0)
                        else:
                            # Chat Completions 格式
                            choices = chunk.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                text = delta.get("content", "")
                                if text:
                                    if ttft is None:
                                        ttft = (time.perf_counter() - start) * 1000
                                    chunks.append(text)
                            usage = chunk.get("usage")
                            if usage:
                                completion_tokens = usage.get("completion_tokens", 0)

            total_ms = (time.perf_counter() - start) * 1000
            full_content = "".join(chunks)

            if completion_tokens == 0 and full_content:
                completion_tokens = count_tokens_tiktoken(full_content, self.model)

            return LLMResponse(
                success=True,
                content=full_content,
                timing=TimingMetrics(
                    total_latency_ms=round(total_ms, 2),
                    ttft_ms=round(ttft, 2) if ttft else None,
                    ttfr_ms=round(ttfr, 2) if ttfr else None,
                    ttfr_event_type=ttfr_event_type,
                ),
                tokens=TokenMetrics(
                    completion_tokens=completion_tokens,
                    total_tokens=completion_tokens,
                ),
            )

        except httpx.TimeoutException:
            return LLMResponse(success=False, error_message=f"请求超时：超过 {self.timeout} 秒")
        except httpx.ConnectError as e:
            return LLMResponse(success=False, error_message=f"连接失败：{e}")
        except Exception as e:
            return LLMResponse(success=False, error_message=f"未知错误：{e}")
