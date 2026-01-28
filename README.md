# LLM 响应时间测试工具

一个功能完整的大模型 API 响应时间测试工具，支持 Streaming/Non-streaming 双模式、批量测试、结果导出和配置文件管理。

## ✨ 功能特性

- 🚀 **双模式测试** - 支持 Streaming 和 Non-streaming 模式
- ⏱️ **多维度指标** - 测量总延迟、首 Token 时间（TTFT）、TPS
- 📊 **批量测试** - 支持多提示词、多次运行，自动计算统计数据
- 📁 **配置文件** - 支持 YAML 配置文件，避免重复输入参数
- 🎯 **推理模型支持** - 支持 `reasoning_effort` 参数（适用于 o1 等模型）
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
| **输出 Tokens** | 模型生成的 token 数量 |
| **TPS** | Tokens Per Second，每秒生成的 token 数 |

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
