# Yoyo Round 1 模型评测总结

## 结论
本轮基于当前 SQL-first B 轨架构，对 5 个候选模型做了第一轮自动化评测。综合 **平均分、延迟、成本** 三项因素，当前建议暂定：

- **主候选：`google/gemini-2.5-flash-lite`**
- **备选：`openai/gpt-5.4-mini`**
- **可保留观察：`qwen/qwen3.5-flash-02-23`**

不建议进入下一轮的：
- `openai/gpt-5-nano`
- `x-ai/grok-4.1-fast`

---

## 评测模型
- `google/gemini-2.5-flash-lite`
- `x-ai/grok-4.1-fast`
- `openai/gpt-5-nano`
- `qwen/qwen3.5-flash-02-23`
- `openai/gpt-5.4-mini`

Provider 统一使用：`openrouter`

---

## 测试范围
第一轮测试集共 12 条，覆盖：
- 意图识别 / 路由
- 多轮对话 / 记忆
- 澄清机制
- 联网实时信息
- SQL grounding
- planner handoff 结构化理解

---

## 总体排名

| Rank | Provider | Model | Avg score | Avg latency (ms) | Estimated total cost | Queries |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | openrouter | google/gemini-2.5-flash-lite | 4.25 | 2229.22 | 0.00155 | 12 |
| 2 | openrouter | qwen/qwen3.5-flash-02-23 | 4.25 | 14456.18 | 0.005931 | 12 |
| 3 | openrouter | openai/gpt-5.4-mini | 4.17 | 2409.52 | 0.009635 | 12 |
| 4 | openrouter | x-ai/grok-4.1-fast | 3.92 | 11242.34 | 0.006153 | 12 |
| 5 | openrouter | openai/gpt-5-nano | 1.17 | 13605.84 | 0.002474 | 12 |

---

## 关键发现

### 1. 综合最优模型：Gemini 2.5 Flash Lite
- 平均分并列第一：**4.25**
- 延迟最低：**2229 ms**
- 成本最低：**0.00155**

这使它成为当前最符合目标的模型：
- 小
- 快
- 便宜
- 输出质量仍然在第一梯队

### 2. Qwen 质量不错，但速度明显不占优
- 平均分同样是 **4.25**
- 但延迟达到 **14.4s**
- 成本也高于 Gemini Flash Lite

结论：
- 作为中文/风格观察样本值得保留
- 但不适合作为当前默认模型

### 3. GPT-5.4-mini 表现稳，但成本偏高
- 平均分：**4.17**
- 延迟：**2409 ms**
- 成本：**0.009635**

结论：
- 质量稳定
- 适合做质量基准或备选
- 当前不如 Gemini Flash Lite 有性价比优势

### 4. GPT-5-nano 不适合当前任务
- 平均分：**1.17**
- 延迟也不占优

结论：
- 可直接淘汰

### 5. Grok-4.1-fast 当前不占优
- 平均分：**3.92**
- 延迟较高
- 成本也不低

结论：
- 当前不建议进入下一轮

---

## 分类表现

### attraction_explain
- 最好：`qwen/qwen3.5-flash-02-23`（4.67）
- Gemini Flash Lite / GPT-5.4-mini / Grok 均为 4.0

### live_info
- Gemini Flash Lite：**5.0**
- Qwen：**5.0**
- GPT-5.4-mini：4.67

### planner_handoff
- 最好：`openai/gpt-5.4-mini`（4.5）
- Gemini Flash Lite：4.25

### translation
- 最好：`x-ai/grok-4.1-fast`（5.0）
- Qwen：4.0
- Gemini Flash Lite / GPT-5.4-mini / GPT-5-nano：3.0

### trip_assistant
- 最好：`google/gemini-2.5-flash-lite`（4.0）
- GPT-5.4-mini：3.0
- Qwen / Grok：2.0

---

## 当前建议

### 暂定上线主候选
**`google/gemini-2.5-flash-lite`**

### 选择原因
1. 总分并列第一
2. 延迟最低
3. 成本最低
4. 在 live_info 和 trip_assistant 这两类当前核心能力上表现稳定

### 备选模型
**`openai/gpt-5.4-mini`**
- 如果后续更看重稳定性和结构化理解，可作为备选/对照基准

### 观察模型
**`qwen/qwen3.5-flash-02-23`**
- attraction explain 能力值得继续观察
- 但当前速度不符合主模型目标

---

## 下一步建议
针对 `google/gemini-2.5-flash-lite` 进入第二轮更聚焦测试，重点看：
- 多轮记忆稳定性
- 澄清机制
- planner_handoff 结构化理解边界
- profile-aware guide generation 文风稳定性
- SQL grounding 是否会在复杂 case 下漂移

---

## 附件 / 本地文件
当前仓库内已生成：
- `benchmark_results_round1_real.xlsx`
- `evals/results_round1_real/`
- `docs/b-track-round1-test-cases.md`
