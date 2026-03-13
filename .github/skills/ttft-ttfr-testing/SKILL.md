---
name: ttft-ttfr-testing
description: "测试大模型的 TTFT（首 Token 延迟）和 TTFR（首推理延迟）性能。Use when: 用户要求测试 TTFT、TTFR、首 token 延迟、首推理延迟、响应时间、LLM 性能基准测试、token 生成速度、模型延迟分析、streaming 性能测试。Trigger on: TTFT, TTFR, Time To First Token, Time To First Reasoning, LLM benchmark, 模型延迟, 响应速度测试, 性能基准."
---

# TTFT / TTFR 基准测试技能

自动运行大模型 TTFT（Time To First Token）和 TTFR（Time To First Reasoning）基准测试，分析结果并给出性能优化建议。

## 触发场景

- 用户要求测试大模型的响应速度、首 token 延迟
- 用户要求测量 TTFT 或 TTFR
- 用户要求进行 LLM 性能基准测试
- 用户要求分析模型延迟或 token 生成速度
- 用户提到 streaming 性能测试

## 前置要求

- Python 3.10+
- 依赖包：`httpx`, `tiktoken`, `pyyaml`, `python-dotenv`
- 仓库根目录下的 `.env` 文件中包含 `LLM_API_KEY`
- Skill 目录下的 `config.yaml`（或仓库根目录下的 `config.yaml`）中配置好 endpoint 和 model

安装依赖（如尚未安装）：

```bash
pip install httpx tiktoken pyyaml python-dotenv
```

## 工作流程

按以下步骤依次执行：

### Step 1: 确认测试配置

读取 Skill 目录下的配置文件 `.github/skills/ttft-ttfr-testing/config.yaml`（优先）或仓库根目录下的 `config.yaml`，确认以下关键配置：
- `endpoint` — API 终结点 URL
- `model` — 模型名称
- `streaming` — 必须为 `true` 才能测量 TTFT
- `reasoning_summary` — 如需测量 TTFR，需设置为 `auto`、`detailed` 或 `concise`
- `reasoning_effort` — 推理强度（low/medium/high）
- `runs` — 每个提示词的测试轮次
- `prompt` — 测试用的提示词

如果用户有自定义需求（如更换模型、增加测试轮次），先修改 `.github/skills/ttft-ttfr-testing/config.yaml` 或通过命令行参数覆盖。

### Step 2: 环境检查

在终端执行以下检查：

1. 确认 `.env` 文件存在且包含 `LLM_API_KEY`：
   ```bash
   grep -q "LLM_API_KEY" .env && echo "✅ API Key 已配置" || echo "❌ 缺少 LLM_API_KEY"
   ```

2. 确认依赖已安装：
   ```bash
   python -c "import httpx, tiktoken, yaml, dotenv; print('✅ 依赖已就绪')"
   ```

### Step 3: 运行测试

在仓库根目录执行测试脚本：

```bash
python .github/skills/ttft-ttfr-testing/scripts/run_ttft_ttfr_test.py --streaming --json
```

常用参数覆盖示例：
- 指定模型：`--model gpt-4o`
- 指定提示词：`--prompt "你好，请介绍一下自己"`
- 增加测试轮次：`--runs 5`
- 调整推理强度：`--reasoning-effort medium`
- 禁用缓存：`--no-cache`

脚本会自动将结果保存到 `reports/` 目录下的 JSON 文件。

### Step 4: 读取结果

测试完成后，读取 `reports/` 目录下最新的 JSON 结果文件。文件包含：
- `summary` — 汇总统计（TTFT/TTFR/TPS/Latency 的 avg/std/min/max）
- `results` — 每次测试的详细数据

### Step 5: 分析结果

运行分析脚本，自动生成评级报告：

```bash
python .github/skills/ttft-ttfr-testing/scripts/analyze_results.py --latest
```

或指定特定结果文件：

```bash
python .github/skills/ttft-ttfr-testing/scripts/analyze_results.py --result-file reports/xxx.json
```

### Step 6: 输出报告

参考 `.github/skills/ttft-ttfr-testing/reference/report_template.md` 中的报告模板，将分析结果以结构化方式呈现给用户。模板中的 `{{...}}` 占位符需替换为实际测试数据。报告保存到 `reports/` 目录下。

报告应包含以下核心部分：

1. **测试信息** — 模型、终结点、推理强度、提示词等配置
2. **概览** — 总请求数、成功率
3. **核心指标** — TTFT / TTFR / TPS / 总延迟的数值、评级和 CV
4. **详细测试数据** — 每轮测试的完整数据表
5. **对比分析**（可选）— 多组测试之间的横向对比
6. **优化建议** — 具体可操作的改进方向

## 指标解读指南

以下信息帮助理解和解读测试结果中的各项指标：

### TTFT — Time To First Token（首 Token 延迟）
- **含义**: 从发送请求到收到第一个内容 token 的时间
- **影响**: 直接影响用户感知的"响应启动速度"
- **测量条件**: 需启用 `streaming: true`
- **评级**:
  | 范围 | 评级 |
  |------|------|
  | < 500 ms | 🟢 优秀 |
  | 500–1500 ms | 🟡 正常 |
  | > 1500 ms | 🔴 需优化 |

### TTFR — Time To First Reasoning（首推理延迟）
- **含义**: 从发送请求到收到第一个推理事件（reasoning token）的时间
- **影响**: 反映推理模型的"思考启动速度"
- **测量条件**: 需启用 `streaming: true` + `reasoning_summary` 配置
- **事件来源**: `response.reasoning_text.delta`、`response.reasoning.delta`、`response.reasoning_summary_text.delta`
- **评级**:
  | 范围 | 评级 |
  |------|------|
  | < 1000 ms | 🟢 优秀 |
  | 1000–3000 ms | 🟡 正常 |
  | > 3000 ms | 🔴 需优化 |

### TPS — Tokens Per Second（Token 生成速度）
- **含义**: 每秒生成的 token 数量
- **计算**: `completion_tokens / (total_latency - ttft)` （排除首 token 等待时间）
- **评级**:
  | 范围 | 评级 |
  |------|------|
  | > 50 tokens/s | 🟢 优秀 |
  | 20–50 tokens/s | 🟡 正常 |
  | < 20 tokens/s | 🔴 需关注 |

### 稳定性指标 — 变异系数 (CV)
- **计算**: `CV = 标准差 / 平均值`
- **评级**:
  | 范围 | 评级 |
  |------|------|
  | < 10% | 🟢 稳定 |
  | 10–30% | 🟡 一般 |
  | > 30% | 🔴 不稳定 |

## 脚本参数速查

### run_ttft_ttfr_test.py

| 参数 | 缩写 | 说明 | 默认值 |
|------|------|------|--------|
| `--config` | `-c` | 配置文件路径 | `config.yaml` |
| `--endpoint` | `-e` | API 终结点 URL | 从 config 读取 |
| `--api-key` | `-k` | API 密钥 | `LLM_API_KEY` 环境变量 |
| `--model` | `-m` | 模型名称 | 从 config 读取 |
| `--prompt` | `-p` | 单个提示词 | 从 config 读取 |
| `--prompt-file` | `-f` | 提示词文件 | — |
| `--runs` | `-r` | 测试轮次 | 1 |
| `--timeout` | `-t` | 超时时间（秒） | 120 |
| `--streaming` | `-s` | 启用 streaming | false |
| `--reasoning-effort` | | 推理强度 | — |
| `--reasoning-summary` | | 推理摘要模式 | — |
| `--max-tokens` | | 最大输出 tokens | — |
| `--no-cache` | | 禁用缓存 | false |
| `--json` | | 仅输出 JSON | false |
| `--output` | `-o` | 输出文件路径 | 自动生成 |

### analyze_results.py

| 参数 | 说明 |
|------|------|
| `--latest` | 自动读取 reports/ 下最新结果 |
| `--result-file` | 指定结果文件路径 |
| `--result-dir` | 指定 result 目录 |
