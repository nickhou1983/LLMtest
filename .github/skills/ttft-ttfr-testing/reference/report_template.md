# TTFT / TTFR 基准测试报告

> 本报告由 `ttft-ttfr-testing` Skill 自动生成。请用实际测试数据替换 `{{...}}` 占位符。

---

## 测试信息

| 项目 | 值 |
|------|-----|
| 测试时间 | {{timestamp}} |
| 模型 | {{model}} |
| 终结点 | {{endpoint}} |
| 推理强度 | {{reasoning_effort}} |
| 推理摘要模式 | {{reasoning_summary}} |
| 测试提示词 | {{prompt}} |
| 测试轮次 | {{runs}} |
| Streaming | {{streaming}} |

---

## 概览

| 项目 | 值 |
|------|-----|
| 总请求数 | {{total_requests}} |
| 成功 | {{successful}} |
| 失败 | {{failed}} |
| 成功率 | {{success_rate}}% |

---

## 核心指标

### TTFT — 首 Token 延迟

| 指标 | 值 | 评级 |
|------|-----|------|
| 平均值 | {{ttft_avg}} ms | {{ttft_rating}} |
| 最小值 | {{ttft_min}} ms | |
| 最大值 | {{ttft_max}} ms | |
| 标准差 | {{ttft_std}} ms | |
| 变异系数 CV | {{ttft_cv}}% | {{ttft_cv_rating}} |

> 评级标准：< 500ms 🟢 优秀 | 500–1500ms 🟡 正常 | > 1500ms 🔴 需优化

### TTFR — 首推理延迟

| 指标 | 值 | 评级 |
|------|-----|------|
| 平均值 | {{ttfr_avg}} ms | {{ttfr_rating}} |
| 最小值 | {{ttfr_min}} ms | |
| 最大值 | {{ttfr_max}} ms | |
| 标准差 | {{ttfr_std}} ms | |
| 变异系数 CV | {{ttfr_cv}}% | {{ttfr_cv_rating}} |
| TTFR − TTFT 差值 | {{ttfr_ttft_gap}} ms | |

> 评级标准：< 1000ms 🟢 优秀 | 1000–3000ms 🟡 正常 | > 3000ms 🔴 需优化
>
> 如果 TTFR 不可用，说明模型在当前配置下未产生独立推理事件。

### TPS — Token 生成速度

| 指标 | 值 | 评级 |
|------|-----|------|
| 平均值 | {{tps_avg}} tokens/s | {{tps_rating}} |
| 最小值 | {{tps_min}} tokens/s | |
| 最大值 | {{tps_max}} tokens/s | |
| 标准差 | {{tps_std}} | |
| 变异系数 CV | {{tps_cv}}% | {{tps_cv_rating}} |

> 评级标准：> 50 tokens/s 🟢 优秀 | 20–50 🟡 正常 | < 20 🔴 需关注

### 总延迟

| 指标 | 值 |
|------|-----|
| 平均值 | {{latency_avg}} ms |
| 最小值 | {{latency_min}} ms |
| 最大值 | {{latency_max}} ms |
| 标准差 | {{latency_std}} ms |
| 变异系数 CV | {{latency_cv}}% — {{latency_cv_rating}} |

### 输出 Tokens

| 指标 | 值 |
|------|-----|
| 平均值 | {{output_tokens_avg}} |
| 最小值 | {{output_tokens_min}} |
| 最大值 | {{output_tokens_max}} |

---

## 详细测试数据

| # | 延迟 (ms) | TTFT (ms) | TTFR (ms) | TTFR 事件类型 | 输出 Tokens | TPS |
|---|-----------|-----------|-----------|---------------|-------------|-----|
| 1 | {{r1_latency}} | {{r1_ttft}} | {{r1_ttfr}} | {{r1_ttfr_event}} | {{r1_tokens}} | {{r1_tps}} |
| 2 | {{r2_latency}} | {{r2_ttft}} | {{r2_ttfr}} | {{r2_ttfr_event}} | {{r2_tokens}} | {{r2_tps}} |
| 3 | {{r3_latency}} | {{r3_ttft}} | {{r3_ttfr}} | {{r3_ttfr_event}} | {{r3_tokens}} | {{r3_tps}} |
| ... | ... | ... | ... | ... | ... | ... |

---

## 对比分析（可选）

如果进行多组测试（不同模型/参数），可按以下格式对比：

| 指标 | 配置 A | 配置 B | 变化 |
|------|--------|--------|------|
| TTFT | {{a_ttft}} ms | {{b_ttft}} ms | {{ttft_change}}% |
| TTFR | {{a_ttfr}} ms | {{b_ttfr}} ms | {{ttfr_change}}% |
| TPS | {{a_tps}} tokens/s | {{b_tps}} tokens/s | {{tps_change}}% |
| 总延迟 | {{a_latency}} ms | {{b_latency}} ms | {{latency_change}}% |

---

## 优化建议

根据测试结果，以下是具体的优化方向：

### TTFT 优化
- [ ] 缩短 prompt 长度，减少输入 token 数
- [ ] 使用地理位置更近的 API 终结点
- [ ] 尝试更快的模型变体（如更小参数量的版本）
- [ ] 启用 KV-cache（如 API 支持）
- [ ] 降低 reasoning_effort

### TTFR 优化
- [ ] 降低 reasoning_effort（如 high → medium）
- [ ] 使用 `concise` 模式的 reasoning_summary
- [ ] 简化问题复杂度，减少推理负担

### TPS 优化
- [ ] 检查 API 端是否存在限流策略
- [ ] 使用更快的推理基础设施
- [ ] 减小 max_tokens 限制不必要的长输出

### 稳定性优化
- [ ] 增加测试轮次（`--runs 5` 或更多）
- [ ] 启用 `--no-cache` 排除缓存对结果的影响
- [ ] 检查 API 端是否存在负载均衡抖动
- [ ] 避开高峰时段测试

---

## 附录

### 评级标准速查

| 指标 | 🟢 优秀 | 🟡 正常 | 🔴 需优化 |
|------|---------|---------|----------|
| TTFT | < 500 ms | 500–1500 ms | > 1500 ms |
| TTFR | < 1000 ms | 1000–3000 ms | > 3000 ms |
| TPS | > 50 tokens/s | 20–50 tokens/s | < 20 tokens/s |
| CV（稳定性） | < 10% | 10–30% | > 30% |

### 指标计算公式

- **TTFT**: `time(first_content_token) - time(request_sent)`
- **TTFR**: `time(first_reasoning_event) - time(request_sent)`
- **TPS**: `completion_tokens / (total_latency_ms - ttft_ms) × 1000`
- **CV**: `std / avg × 100%`
