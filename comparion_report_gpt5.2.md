# GPT-5.2-Codex 推理级别对比测试报告

**测试日期**: 2026年2月26日（已重新测试更新）  
**模型**: gpt-5.2-codex  
**API端点**: Azure OpenAI (Responses API)  
**测试模式**: Streaming  
**缓存设置**: 禁用（no_cache=true）  
**每级别测试次数**: 3次  
**测试提示词**: 生成一个日历应用的代码示例，使用 Python 和 Tkinter 库。

---

## 📊 四种模式汇总（Low / Medium / High / xhigh）

| 指标 | Low | Medium | High | xhigh |
| ------ | -----: | -------: | -----: | ------: |
| 请求成功/总数 | 3/3 | 3/3 | 3/3 | 3/3 |
| 总延迟均值 (ms) | 19,779.95 | 24,315.68 | 48,691.15 | 75,654.05 |
| TTFT 均值 (ms) | 5,517.94 | 7,436.41 | 33,819.16 | 67,155.29 |
| TTFR 均值 (ms) | 5,010.66 (2/3) | 7,732.99 (2/3) | 10,051.98 (2/3) | 14,448.04 (3/3) |
| 输出 Tokens 均值 | 562.33 | 714.67 | 1,441.67 | 2,866.33 |
| TPS 均值 (tokens/s) | 39.56 | 47.23 | 102.32 | 498.75 |

> 括号内为 TTFR 可用次数/总次数。

---

## 📈 趋势观察

- `low` 在总延迟上最快（19,780 ms），TTFT 也最低（5,518 ms）。
- 推理强度升到 `high`/`xhigh` 后，延迟显著上升，但输出 Tokens 与 TPS 同步大幅提升。
- `xhigh` 生成吞吐最高（498.75 tokens/s），输出最丰富（2,866 tokens），但延迟也最高（75,654 ms）。
- TTFR 在 low/medium/high 三档返回率为 2/3，xhigh 为 3/3。

---

## 🎯 场景建议

- **低时延优先**：`low`（19,779.95 ms）
- **最快首响应**：`low`（TTFT 5,517.94 ms）
- **更完整输出**：`xhigh`（2,866 tokens）
- **高吞吐生成**：`xhigh`（498.75 tokens/s）

---

## 📋 本轮冠军

| 维度 | 冠军 | 数值 |
| ---- | ---- | ----: |
| 最低总延迟 | Low | 19,779.95 ms |
| 最低 TTFT | Low | 5,517.94 ms |
| 最高输出 Tokens | xhigh | 2,866.33 |
| 最高 TPS | xhigh | 498.75 tokens/s |

---

## 📝 数据来源

- `results_low_gpt52.json`
- `results_medium_gpt52.json`
- `results_high_gpt52.json`
- `results_xhigh_gpt52.json`
