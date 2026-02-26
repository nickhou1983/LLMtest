# GPT-5.2-Codex 推理级别对比测试报告

**测试日期**: 2026年2月26日  
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
| 总延迟均值 (ms) | 17,628.65 | 16,991.86 | 50,217.56 | 47,529.63 |
| TTFT 均值 (ms) | 6,168.17 | 5,596.02 | 29,605.04 | 33,616.02 |
| TTFR 均值 (ms) | 5,185.13 | 4,328.64 | 13,062.57* | 14,415.44 |
| 输出 Tokens 均值 | 567.00 | 518.67 | 1,413.33 | 1,779.00 |
| TPS 均值 (tokens/s) | 49.37 | 48.11 | 79.56 | 139.69 |

> *High 档 TTFR 仅 1/3 请求返回，统计值代表单样本。

---

## 📈 趋势观察

- 本轮结果下，`medium` 在总延迟与 TTFT 两项都最快。
- 推理强度升到 `high`/`xhigh` 后，延迟明显上升，但输出 Tokens 与 TPS 同步提升。
- `xhigh` 生成吞吐最高（139.69 tokens/s），输出最丰富（1779 tokens）。
- `high` 的 TTFR 返回率偏低（1/3），该指标稳定性不足。

---

## 🎯 场景建议

- **低时延优先**：`medium`（16,991.86 ms）
- **最快首响应**：`medium`（TTFT 5,596.02 ms）
- **更完整输出**：`xhigh`（1779 tokens）
- **高吞吐生成**：`xhigh`（139.69 tokens/s）

---

## 📋 本轮冠军

| 维度 | 冠军 | 数值 |
| ---- | ---- | ----: |
| 最低总延迟 | Medium | 16,991.86 ms |
| 最低 TTFT | Medium | 5,596.02 ms |
| 最高输出 Tokens | xhigh | 1,779.00 |
| 最高 TPS | xhigh | 139.69 tokens/s |

---

## 📝 数据来源

- `results_low.json`
- `results_medium.json`
- `results_high.json`
- `results_xhigh.json`
