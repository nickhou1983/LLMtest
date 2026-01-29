"""
LLM API 客户端模块
支持 OpenAI 兼容 API 的 streaming 和 non-streaming 模式
"""

import json
import time
from dataclasses import dataclass
from typing import Optional, Generator

import httpx

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
    """LLM API 客户端"""
    
    def __init__(
        self,
        endpoint: str,
        api_key: str,
        model: str,
        timeout: float = 120.0,
        reasoning_effort: Optional[str] = None,
        max_tokens: Optional[int] = None,
        no_cache: bool = False
    ):
        """
        初始化客户端
        
        Args:
            endpoint: API 终结点 URL
            api_key: API 密钥
            model: 模型名称
            timeout: 请求超时时间（秒）
            reasoning_effort: 推理强度（low/medium/high），适用于 o1 等推理模型
            max_tokens: 最大输出 token 数
            no_cache: 是否禁用 API 端缓存（默认 False）
        """
        self.endpoint = endpoint.rstrip('/')
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.reasoning_effort = reasoning_effort
        self.max_tokens = max_tokens
        self.no_cache = no_cache
        
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "api-key": api_key  # Azure OpenAI 使用 api-key header
        }
        
        # 检测是否为 Responses API（Azure 新格式）
        self.is_responses_api = "/responses" in endpoint
    
    def _build_request_body(self, prompt: str, stream: bool = False) -> dict:
        """构建请求体"""
        # Responses API 格式（Azure 新 API）
        if self.is_responses_api:
            body = {
                "model": self.model,
                "input": prompt,
                "stream": stream
            }
            if self.reasoning_effort:
                body["reasoning"] = {"effort": self.reasoning_effort}
            if self.max_tokens:
                body["max_output_tokens"] = self.max_tokens
            if self.no_cache:
                body["store"] = False  # 禁用 API 端缓存
            return body
        
        # Chat Completions API 格式（OpenAI 标准）
        body = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": stream
        }
        
        # 添加可选参数
        if self.reasoning_effort:
            body["reasoning_effort"] = self.reasoning_effort
        if self.max_tokens:
            body["max_tokens"] = self.max_tokens
        
        return body
    
    def _extract_tokens_from_response(self, response_data: dict) -> TokenMetrics:
        """从响应中提取 token 使用信息"""
        usage = response_data.get("usage", {})
        
        # Responses API 格式
        if self.is_responses_api:
            return TokenMetrics(
                prompt_tokens=usage.get("input_tokens", 0),
                completion_tokens=usage.get("output_tokens", 0),
                total_tokens=usage.get("total_tokens", 0)
            )
        
        # Chat Completions API 格式
        return TokenMetrics(
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0)
        )
    
    def _extract_content_from_response(self, response_data: dict) -> str:
        """从响应中提取生成的内容"""
        # Responses API 格式
        if self.is_responses_api:
            output = response_data.get("output", [])
            content_parts = []
            for item in output:
                if item.get("type") == "message":
                    for content in item.get("content", []):
                        if content.get("type") == "output_text":
                            content_parts.append(content.get("text", ""))
            return "".join(content_parts)
        
        # Chat Completions API 格式
        choices = response_data.get("choices", [])
        if choices:
            message = choices[0].get("message", {})
            return message.get("content", "")
        return ""
    
    def call_api(self, prompt: str) -> LLMResponse:
        """
        非流式 API 调用
        
        Args:
            prompt: 提示词
            
        Returns:
            LLMResponse 结果
        """
        body = self._build_request_body(prompt, stream=False)
        
        start_time = time.perf_counter()
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    self.endpoint,
                    headers=self.headers,
                    json=body
                )
            
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000
            
            # 检查 HTTP 状态码
            if response.status_code == 401:
                return LLMResponse(
                    success=False,
                    error_message="认证失败：API 密钥无效或已过期"
                )
            elif response.status_code == 403:
                return LLMResponse(
                    success=False,
                    error_message="权限不足：无法访问该模型或资源"
                )
            elif response.status_code == 429:
                return LLMResponse(
                    success=False,
                    error_message="请求过于频繁：已触发速率限制"
                )
            elif response.status_code >= 500:
                return LLMResponse(
                    success=False,
                    error_message=f"服务器错误：{response.status_code}"
                )
            elif response.status_code != 200:
                return LLMResponse(
                    success=False,
                    error_message=f"请求失败：HTTP {response.status_code}"
                )
            
            # 解析响应
            try:
                response_data = response.json()
            except json.JSONDecodeError as e:
                return LLMResponse(
                    success=False,
                    error_message=f"JSON 解析失败：{e}"
                )
            
            content = self._extract_content_from_response(response_data)
            tokens = self._extract_tokens_from_response(response_data)
            
            # 如果 API 没有返回 token 数量，使用 tiktoken 计算
            if tokens.completion_tokens == 0 and content:
                tokens.completion_tokens = count_tokens_tiktoken(content, self.model)
                tokens.total_tokens = tokens.prompt_tokens + tokens.completion_tokens
            
            return LLMResponse(
                success=True,
                content=content,
                timing=TimingMetrics(total_latency_ms=round(latency_ms, 2)),
                tokens=tokens,
                raw_response=response_data
            )
            
        except httpx.TimeoutException:
            return LLMResponse(
                success=False,
                error_message=f"请求超时：超过 {self.timeout} 秒"
            )
        except httpx.ConnectError as e:
            return LLMResponse(
                success=False,
                error_message=f"连接失败：{e}"
            )
        except Exception as e:
            return LLMResponse(
                success=False,
                error_message=f"未知错误：{e}"
            )
    
    def call_api_stream(self, prompt: str) -> LLMResponse:
        """
        流式 API 调用（SSE）
        
        Args:
            prompt: 提示词
            
        Returns:
            LLMResponse 结果（包含 TTFT）
        """
        body = self._build_request_body(prompt, stream=True)
        
        start_time = time.perf_counter()
        ttft: Optional[float] = None
        ttfr: Optional[float] = None
        content_chunks: list[str] = []
        completion_tokens = 0
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                with client.stream(
                    "POST",
                    self.endpoint,
                    headers=self.headers,
                    json=body
                ) as response:
                    
                    # 检查 HTTP 状态码
                    if response.status_code == 401:
                        return LLMResponse(
                            success=False,
                            error_message="认证失败：API 密钥无效或已过期"
                        )
                    elif response.status_code == 403:
                        return LLMResponse(
                            success=False,
                            error_message="权限不足：无法访问该模型或资源"
                        )
                    elif response.status_code == 429:
                        return LLMResponse(
                            success=False,
                            error_message="请求过于频繁：已触发速率限制"
                        )
                    elif response.status_code >= 500:
                        return LLMResponse(
                            success=False,
                            error_message=f"服务器错误：{response.status_code}"
                        )
                    elif response.status_code != 200:
                        return LLMResponse(
                            success=False,
                            error_message=f"请求失败：HTTP {response.status_code}"
                        )
                    
                    # 处理 SSE 流
                    for line in response.iter_lines():
                        if not line:
                            continue
                        
                        # SSE 格式：data: {...}
                        if line.startswith("data: "):
                            data_str = line[6:]  # 去掉 "data: " 前缀
                            
                            if data_str.strip() == "[DONE]":
                                break
                            
                            try:
                                chunk_data = json.loads(data_str)
                                
                                # Responses API 格式
                                if self.is_responses_api:
                                    # 处理 response.output_text.delta 事件
                                    chunk_type = chunk_data.get("type", "")
                                    if chunk_type == "response.output_text.delta":
                                        delta_text = chunk_data.get("delta", "")
                                        if delta_text:
                                            if ttft is None:
                                                ttft = (time.perf_counter() - start_time) * 1000
                                            content_chunks.append(delta_text)
                                    # 处理 reasoning delta 事件（首个 reasoning token 时间）
                                    elif chunk_type in ("response.reasoning_text.delta", "response.reasoning.delta"):
                                        reasoning_delta = chunk_data.get("delta") or chunk_data.get("text") or ""
                                        if isinstance(reasoning_delta, str) and reasoning_delta:
                                            if ttfr is None:
                                                ttfr = (time.perf_counter() - start_time) * 1000
                                    # 处理完成事件中的 usage
                                    elif chunk_type == "response.completed":
                                        resp = chunk_data.get("response", {})
                                        usage = resp.get("usage", {})
                                        if usage:
                                            completion_tokens = usage.get("output_tokens", 0)
                                else:
                                    # Chat Completions API 格式
                                    choices = chunk_data.get("choices", [])
                                    if choices:
                                        delta = choices[0].get("delta", {})
                                        chunk_content = delta.get("content", "")
                                        if chunk_content:
                                            if ttft is None:
                                                ttft = (time.perf_counter() - start_time) * 1000
                                            content_chunks.append(chunk_content)
                                    
                                    # 检查是否有 usage 信息（部分 API 在最后一个 chunk 返回）
                                    usage = chunk_data.get("usage")
                                    if usage:
                                        completion_tokens = usage.get("completion_tokens", 0)
                                    
                            except json.JSONDecodeError:
                                continue
            
            end_time = time.perf_counter()
            total_latency_ms = (end_time - start_time) * 1000
            
            full_content = "".join(content_chunks)
            
            # 如果 API 没有返回 token 数量，使用 tiktoken 计算
            if completion_tokens == 0 and full_content:
                completion_tokens = count_tokens_tiktoken(full_content, self.model)
            
            return LLMResponse(
                success=True,
                content=full_content,
                timing=TimingMetrics(
                    total_latency_ms=round(total_latency_ms, 2),
                    ttft_ms=round(ttft, 2) if ttft else None,
                    ttfr_ms=round(ttfr, 2) if ttfr else None
                ),
                tokens=TokenMetrics(
                    completion_tokens=completion_tokens,
                    total_tokens=completion_tokens  # streaming 模式可能没有 prompt_tokens
                )
            )
            
        except httpx.TimeoutException:
            return LLMResponse(
                success=False,
                error_message=f"请求超时：超过 {self.timeout} 秒"
            )
        except httpx.ConnectError as e:
            return LLMResponse(
                success=False,
                error_message=f"连接失败：{e}"
            )
        except Exception as e:
            return LLMResponse(
                success=False,
                error_message=f"未知错误：{e}"
            )
