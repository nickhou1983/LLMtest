# LLM 响应时间测试工具

一个功能完整的大模型 API 响应时间测试工具，支持 Streaming/Non-streaming 双模式、批量测试、结果导出和配置文件管理。

## ✨ 功能特性

- 🚀 **双模式测试** - 支持 Streaming 和 Non-streaming 模式
- ⏱️ **多维度指标** - 测量总延迟、首 Token 时间（TTFT）、首推理时间（TTFR）、TPS
- 📊 **批量测试** - 支持多提示词、多次运行，自动计算统计数据
- 📁 **配置文件** - 支持 YAML 配置文件，避免重复输入参数
- 🎯 **推理模型支持** - 支持 `reasoning_effort` 和 `reasoning_summary` 参数（适用于 o1、GPT-5 等模型）
- 📤 **结果导出** - 支持 JSON 格式输出和文件保存
- 🎨 **美观输出** - 使用 Rich 库提供彩色表格和进度条

## 📦 安装

### 1. 克隆项目

```bash
cd /path/to/LLMtest
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

依赖列表：
- `httpx` - HTTP 客户端（支持 Streaming）
- `tiktoken` - Token 计数
- `click` - 命令行接口
- `rich` - 终端美化
- `pyyaml` - 配置文件解析

## 🚀 快速开始

### 方式一：命令行参数

```bash
python main.py \
  --endpoint "https://api.openai.com/v1/chat/completions" \
  --api-key "sk-your-api-key" \
  --model "gpt-4" \
  --prompt "Hello, how are you?"
```

### 方式二：使用配置文件

1. 编辑 `config.yaml` 文件：

```yaml
endpoint: "https://api.openai.com/v1/chat/completions"
api_key: "sk-your-api-key"
model: "gpt-4"
prompt: "Hello, how are you?"
```

2. 直接运行：

```bash
python main.py
```

## 📖 详细使用说明

### 命令行参数

| 参数 | 缩写 | 说明 | 默认值 |
|------|------|------|--------|
| `--config` | `-c` | 配置文件路径 | 自动查找 `config.yaml` |
| `--endpoint` | `-e` | API 终结点 URL | 必填 |
| `--api-key` | `-k` | API 密钥 | 必填（或设置环境变量） |
| `--model` | `-m` | 模型名称 | 必填 |
| `--prompt` | `-p` | 单个提示词 | 与 `--prompt-file` 二选一 |
| `--prompt-file` | `-f` | 提示词文件路径 | 与 `--prompt` 二选一 |
| `--streaming` | `-s` | 启用 Streaming 模式 | `false` |
| `--runs` | `-r` | 每个提示词测试次数 | `1` |
| `--timeout` | `-t` | 请求超时时间（秒） | `120` |
| `--output` | `-o` | 输出结果到 JSON 文件 | - |
| `--json` | - | 仅输出 JSON 格式 | `false` |
| `--reasoning-effort` | - | 推理强度 (`low`/`medium`/`high`) | - |
| `--reasoning-summary` | - | 推理摘要模式 (`auto`/`detailed`/`concise`)，启用后可获取 TTFR | - |
| `--max-tokens` | - | 最大输出 token 数 | - |

### 配置文件

程序会按以下顺序查找配置文件：

1. `--config` 参数指定的路径
2. 当前目录的 `config.yaml`
3. 当前目录的 `config.yml`
4. `~/.llmtest/config.yaml`（用户级配置）

**完整配置示例：**

```yaml
# LLM 响应时间测试配置文件

# API 配置
endpoint: "https://api.openai.com/v1/chat/completions"
api_key: "sk-your-api-key-here"  # 也可通过 LLM_API_KEY 环境变量设置
model: "gpt-4"

# 测试配置
streaming: false      # 是否使用 streaming 模式（可测量 TTFT）
runs: 1               # 每个提示词的测试次数
timeout: 120          # 请求超时时间（秒）

# 模型参数
# reasoning_effort: "medium"  # 推理强度：low, medium, high（适用于 o1 等推理模型）
# reasoning_summary: "auto"   # 推理摘要模式：auto, detailed, concise（启用后可获取 TTFR）
# max_tokens: 4096            # 最大输出 token 数

# 提示词配置（二选一）
# 方式1：直接指定单个提示词
prompt: "Hello, how are you?"

# 方式2：从文件读取（每行一个提示词）
# prompt_file: "prompts.txt"

# 输出配置
# output: "results.json"  # 保存结果到文件
# json_output: false      # 是否仅输出 JSON 格式
```

**优先级规则：** 命令行参数 > 配置文件 > 环境变量 > 默认值

### 环境变量

| 变量名 | 说明 |
|--------|------|
| `LLM_API_KEY` | API 密钥，避免在命令行中暴露 |

```bash
export LLM_API_KEY="sk-your-api-key"
python main.py -e "https://api.openai.com/v1/chat/completions" -m "gpt-4" -p "Hello"
```

## 📊 使用示例

### 1. 基础测试

```bash
python main.py \
  -e "https://api.openai.com/v1/chat/completions" \
  -k "sk-xxx" \
  -m "gpt-4" \
  -p "What is the capital of France?"
```

### 2. Streaming 模式（测量 TTFT）

```bash
python main.py \
  -e "https://api.openai.com/v1/chat/completions" \
  -k "sk-xxx" \
  -m "gpt-4" \
  -p "Write a short poem about AI" \
  --streaming
```

### 3. 批量测试（从文件读取提示词）

创建 `prompts.txt`：

```text
What is machine learning?
Explain quantum computing in simple terms.
Write a haiku about programming.
```

运行测试：

```bash
python main.py \
  -e "https://api.openai.com/v1/chat/completions" \
  -k "sk-xxx" \
  -m "gpt-4" \
  -f prompts.txt \
  --runs 3 \
  --streaming \
  -o results.json
```

### 4. 测试推理模型（o1）

```bash
python main.py \
  -e "https://api.openai.com/v1/chat/completions" \
  -k "sk-xxx" \
  -m "o1" \
  -p "Prove the Pythagorean theorem" \
  --reasoning-effort high \
  --max-tokens 8192
```

### 5. 纯 JSON 输出（适合脚本处理）

```bash
python main.py \
  -e "https://api.openai.com/v1/chat/completions" \
  -k "sk-xxx" \
  -m "gpt-4" \
  -p "Hello" \
  --json
```

### 6. 测试本地模型（Ollama / vLLM）

```bash
# Ollama
python main.py \
  -e "http://localhost:11434/v1/chat/completions" \
  -k "ollama" \
  -m "llama3" \
  -p "Hello"

# vLLM
python main.py \
  -e "http://localhost:8000/v1/chat/completions" \
  -k "EMPTY" \
  -m "meta-llama/Llama-3-8B-Instruct" \
  -p "Hello"
```

## 📈 输出指标

### 终端表格输出

```
┌────────┬──────────────────────────────┬──────────┬────────────┬────────────┬────────────┬──────────┐
│ 序号   │ 提示词                       │ 状态     │ 延迟(ms)   │ TTFT(ms)   │ 输出Tokens │ TPS      │
├────────┼──────────────────────────────┼──────────┼────────────┼────────────┼────────────┼──────────┤
│ 1      │ What is machine learning?    │ ✓ 成功   │ 1234.56    │ 156.23     │ 42         │ 34.02    │
│ 2      │ Explain quantum computing... │ ✓ 成功   │ 2345.67    │ 189.45     │ 68         │ 28.99    │
└────────┴──────────────────────────────┴──────────┴────────────┴────────────┴────────────┴──────────┘
```

### 指标说明

| 指标 | 说明 |
|------|------|
| **延迟 (Latency)** | 从发送请求到接收完整响应的总时间（毫秒） |
| **TTFT** | Time To First Token，首个 token 返回的时间（仅 Streaming 模式） |
| **TTFR** | Time To First Reasoning，首个推理摘要返回的时间（仅 Streaming 模式 + 启用 `reasoning_summary`） |
| **输出 Tokens** | 模型生成的 token 数量 |
| **TPS** | Tokens Per Second，每秒生成的 token 数 |

### 📐 统计口径详解

#### 1. 总延迟 (Total Latency)

```text
总延迟 = 请求结束时间 - 请求开始时间
```

- **测量起点**：HTTP 请求发送的瞬间（`httpx` 客户端发起请求）
- **测量终点**：
  - **Non-streaming 模式**：收到完整 HTTP 响应体
  - **Streaming 模式**：收到最后一个 SSE chunk（`data: [DONE]`）
- **单位**：毫秒 (ms)
- **包含内容**：网络延迟 + 服务端处理时间 + Token 生成时间

#### 2. 首 Token 延迟 (TTFT - Time To First Token)

```text
TTFT = 首个有效内容 chunk 接收时间 - 请求开始时间
```

- **仅在 Streaming 模式下可用**
- **测量起点**：HTTP 请求发送的瞬间
- **测量终点**：收到第一个包含非空 `content` 的 SSE chunk
- **单位**：毫秒 (ms)
- **意义**：反映模型"思考"时间，对于推理模型（如 o1、GPT-5.2-Codex）此值较大
- **注意**：不计入空 chunk 或仅包含 `role` 字段的初始 chunk

#### 3. 首推理摘要延迟 (TTFR - Time To First Reasoning)

```text
TTFR = 首个推理摘要 chunk 接收时间 - 请求开始时间
```

- **仅在 Streaming 模式 + 启用 `reasoning_summary` 参数时可用**
- **测量起点**：HTTP 请求发送的瞬间
- **测量终点**：收到第一个 `response.reasoning_summary_text.delta` 事件
- **单位**：毫秒 (ms)
- **意义**：反映模型开始输出推理摘要的时间，通常 TTFR < TTFT
- **配置要求**：需要在请求中设置 `reasoning_summary: "auto"` 或 `"detailed"`
- **支持事件类型**：
  - `response.reasoning_summary_text.delta` - 推理摘要增量（Azure OpenAI 支持）
  - `response.reasoning_text.delta` - 原始推理增量（部分平台支持）

**配置示例：**

```yaml
streaming: true
reasoning_effort: "high"
reasoning_summary: "detailed"  # 启用后可获取 TTFR
```

**测试数据参考（gpt-5.2-codex）：**

| 推理深度 | TTFR | TTFT | 总延迟 | 输出 Tokens | TPS |
|---|---|---|---|---|---|
| Low | 12,420 ms | 13,201 ms | 35,352 ms | 633 | 28.58 |
| Medium | 7,546 ms | 8,859 ms | 27,411 ms | 669 | 36.06 |
| High | 17,307 ms | 52,620 ms | 81,126 ms | 1,807 | 63.39 |

#### 4. 输出 Token 数 (Output Tokens / Completion Tokens)

```text
输出 Tokens = API 返回的 usage.completion_tokens || tiktoken 本地计算
```

- **优先使用 API 返回值**：大多数 OpenAI 兼容 API 会在响应中返回 `usage.completion_tokens`
- **降级计算**：若 API 未返回 token 统计，使用 `tiktoken` 库本地计算：
  - 优先使用模型对应的编码器
  - 默认使用 `cl100k_base` 编码（GPT-4/3.5 标准）
- **单位**：个
- **注意**：本地计算可能与服务端略有差异（通常 ±5%）

#### 4. Token 生成速度 (TPS - Tokens Per Second)

```text
# Streaming 模式（推荐，更精确）
TPS = 输出 Tokens / ((总延迟 - TTFT) / 1000)

# Non-streaming 模式
TPS = 输出 Tokens / (总延迟 / 1000)
```

- **Streaming 模式**：使用**生成阶段时间**（总延迟 - TTFT）作为分母
  - 排除了首 Token 前的"思考"时间
  - 更准确反映模型的实际生成速度
- **Non-streaming 模式**：使用总延迟作为分母
  - 包含了完整的请求处理时间
- **单位**：tokens/s
- **边界处理**：若有效延迟 ≤ 0，返回 0.0

#### 5. 聚合统计指标

对于批量测试，会对上述指标进行聚合统计：

| 统计量 | 计算方式 | 说明 |
| -------- | ---------- | ------ |
| **平均值 (avg)** | `sum(values) / count` | 所有成功请求的算术平均 |
| **标准差 (std)** | `stdev(values)` | 衡量数据离散程度，样本数 > 1 时计算 |
| **最小值 (min)** | `min(values)` | 最快/最少的一次 |
| **最大值 (max)** | `max(values)` | 最慢/最多的一次 |
| **样本数 (count)** | `len(successful_results)` | 成功请求的数量 |

**注意**：

- 失败的请求不参与统计计算
- 标准差在仅有 1 个样本时为 0
- 所有数值保留 2 位小数

#### 6. 效率指标（报告中使用）

| 指标 | 公式 | 说明 |
| ------ | ------ | ------ |
| **每 Token 平均延迟** | `总延迟 / 输出 Tokens` | 生成每个 token 的平均耗时 |
| **有效生成时间** | `总延迟 - TTFT` | 排除思考时间的纯生成耗时 |
| **输出效率** | `输出 Tokens / (总延迟 / 1000)` | 每秒有效输出 token 数（不排除 TTFT） |
| **思考时间** | `≈ TTFT` | 模型推理/规划阶段的耗时 |

#### 7. 时间戳精度

- 使用 Python `time.perf_counter()` 获取高精度时间戳
- 精度：微秒级（取决于操作系统）
- 输出精度：保留 2 位小数（0.01 ms）

### JSON 输出格式

```json
{
  "summary": {
    "total_requests": 10,
    "successful": 10,
    "failed": 0,
    "latency_stats": {
      "count": 10,
      "avg": 1234.56,
      "std": 123.45,
      "min": 1000.0,
      "max": 1500.0
    },
    "ttft_stats": {
      "count": 10,
      "avg": 156.23,
      "std": 15.67,
      "min": 120.0,
      "max": 200.0
    },
    "output_tokens_stats": {
      "count": 10,
      "avg": 42.5,
      "std": 8.3,
      "min": 30,
      "max": 60
    },
    "tps_stats": {
      "count": 10,
      "avg": 34.02,
      "std": 5.12,
      "min": 25.0,
      "max": 45.0
    }
  },
  "results": [
    {
      "prompt": "What is machine learning?",
      "status": "success",
      "error_message": null,
      "response_content": "Machine learning is...",
      "latency_ms": 1234.56,
      "ttft_ms": 156.23,
      "output_tokens": 42,
      "tps": 34.02
    }
  ]
}
```

## 🔧 支持的 API

本工具兼容所有 OpenAI 格式的 API：

| 服务 | 终结点示例 |
|------|-----------|
| OpenAI | `https://api.openai.com/v1/chat/completions` |
| Azure OpenAI | `https://{resource}.openai.azure.com/openai/deployments/{deployment}/chat/completions?api-version=2024-02-01` |
| Ollama | `http://localhost:11434/v1/chat/completions` |
| vLLM | `http://localhost:8000/v1/chat/completions` |
| LM Studio | `http://localhost:1234/v1/chat/completions` |
| Groq | `https://api.groq.com/openai/v1/chat/completions` |
| Together AI | `https://api.together.xyz/v1/chat/completions` |
| DeepSeek | `https://api.deepseek.com/v1/chat/completions` |

## 🛠️ 项目结构

```
LLMtest/
├── main.py           # CLI 入口和主逻辑
├── client.py         # API 客户端（Streaming/Non-streaming）
├── metrics.py        # 指标计算和统计
├── config.yaml       # 配置文件模板
├── requirements.txt  # Python 依赖
└── README.md         # 使用文档
```

## ❓ 常见问题

### Q: 如何避免在命令行暴露 API 密钥？

**A:** 使用以下任一方式：

1. 配置文件：在 `config.yaml` 中设置 `api_key`
2. 环境变量：`export LLM_API_KEY="sk-xxx"`

### Q: Token 计数不准确？

**A:** 程序优先使用 API 返回的 `usage.completion_tokens`。如果 API 未返回，会使用 `tiktoken` 本地计算（可能与实际略有差异）。

### Q: 如何测试本地部署的模型？

**A:** 将 `--endpoint` 设置为本地服务地址，`--api-key` 可设置任意值（如 `EMPTY`）。

### Q: Streaming 模式下 TTFT 为什么是空？

**A:** 某些 API 可能不立即返回第一个 chunk，或返回格式不标准。程序会在收到第一个包含内容的 chunk 时记录 TTFT。

## 📄 许可证

MIT License
