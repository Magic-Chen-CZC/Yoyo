# Routing zh-hard benchmark report (2026-05-08)

## 1. 本轮目标

本轮 benchmark 的目标是为 QA routing fallback 建立一套正式、可复用的中文 hard-case 基线，用于第一轮 Qwen 官方 DashScope 候选选型。

本轮重点不是评估最终回答质量，而是评估在 **rules-first + fallback classifier** 架构下，小模型在模糊意图上的补位能力，尤其关注：
- 准确率
- 低置信度冲突题表现
- 平均时延
- 剩余失败样本模式

## 2. 范围与不在范围内的内容

本轮纳入范围：
- 全中文 query
- 6 个 routing intent：`translation`、`live_info`、`trip_assistant`、`attraction_explain`、`manual_route_edit_redirect`、`out_of_scope`
- 规则路由 + 小模型 fallback 的分类能力
- Qwen 官方 DashScope 商业模型

本轮不纳入范围：
- 开源 Qwen 模型
- `qwen-plus`
- 最终 QA 文案生成质量
- 多语种 direct routing
- 真实线上 cost 精算

## 3. Prompt 设计思路

本轮 fallback prompt 已统一切换为中文模板，详细版本见：`docs/router-fallback-zh-prompt-template.md`。

设计原则：
- 模型只做单标签分类，不回答用户
- 输出协议严格限制为 JSON：`intent`、`confidence`、`reason`
- 明确写出 translation / live_info / trip_assistant / attraction_explain / manual_route_edit_redirect / out_of_scope 的意图边界
- 对冲突项给出显式优先级，重点约束：
  - translation 优先于 explain
  - same-day live signal 优先于 explain
  - 明确改路线优先于 trip assistant
  - weather / traffic / crowd 统一归 `out_of_scope`

## 4. 数据集设计思路

数据集文件：`evals/datasets/routing_benchmark_cases_zh_hard_v1.json`

数据集特征：
- 总计 72 条
- 全部为中文 query
- 六类 intent 全覆盖
- 重点覆盖 hard case 与边界冲突

intent 分布：
- `attraction_explain`: 12
- `live_info`: 12
- `trip_assistant`: 12
- `manual_route_edit_redirect`: 12
- `translation`: 8
- `out_of_scope`: 16

重点 hard case：
- `live_info` vs `attraction_explain`
- `trip_assistant` vs `manual_route_edit_redirect`
- translation 显式请求 vs explain/live/edit 混淆
- weather / traffic / crowd 边界题
- 短 follow-up 与 history 依赖
- 中文口语、省略表达、复合约束句

## 5. 候选模型与运行配置

候选配置文件：`evals/routing_candidates_qwen_zh_hard_v1.yaml`

纳入候选：
- `rules_only`
- `rules_plus_fallback_qwen_flash`
- `rules_plus_fallback_qwen35_flash_0223`
- `rules_plus_fallback_qwen_turbo`

对应 fallback model：
- `qwen-flash`
- `qwen3.5-flash-2026-02-23`
- `qwen-turbo`

运行产物目录：`evals/results/routing_zh_hard_v1/`

Excel 导出文件：`evals/results/routing_zh_hard_v1_results.xlsx`

## 6. 指标口径

本轮主要看：
- `accuracy`
- `needs_fallback_accuracy`
- `manual_route_edit_accuracy`
- `boundary_accuracy`
- `conflict_accuracy`
- `avg_latency_ms`

说明：
- `boundary_accuracy` 主要看天气 / 交通 / 拥挤度边界题是否稳
- `needs_fallback_accuracy` 表示对规则层低置信度或冲突样本的承接能力
- 当前 `estimated_total_cost` 仍为 `0.0`，原因不是“免费”，而是本轮 summary 尚未完成真实成本累计接入，因此这里只做准确率与时延结论，不把 cost 作为正式排序依据

## 7. 汇总结果

### 7.1 主对比：当前生产候选形态（rules + selective fallback）

> 说明：本节保留两轮信息。2026-05-08 是首轮 zh-hard rerun；2026-05-09 keyed v2 是在 benchmark/runtime 对齐、translator routing prompt 收紧、mixed-intent fallback 与 route-edit negation 收口之后的最新同口径 rerun。

#### 2026-05-08 首轮结果

| Candidate | Accuracy | Fallback Used | Needs-fallback Acc | Manual-edit Acc | Boundary Acc | Conflict Acc | Avg Latency (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `rules_only` | 0.5694 | 0 | 0.5094 | 0.25 | 1.0 | 0.7778 | 0.02 |
| `rules_plus_fallback_qwen_flash` | 0.8611 | 51 | 0.9057 | 0.9167 | 1.0 | 0.9444 | 721.45 |
| `rules_plus_fallback_qwen35_flash_0223` | 0.5694 | 0 | 0.5094 | 0.25 | 1.0 | 0.7778 | 5772.77 |
| `rules_plus_fallback_qwen_turbo` | 0.8889 | 51 | 0.9434 | 0.9167 | 1.0 | 1.0 | 681.0 |

#### 2026-05-09 keyed v2 最新结果

| Candidate | Accuracy | Fallback Used | Needs-fallback Acc | Manual-edit Acc | Boundary Acc | Conflict Acc | Avg Latency (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `rules_only` | 0.7222 | 0 | 0.6226 | 0.6667 | 1.0 | 0.6471 | 3.61 |
| `rules_plus_fallback_qwen_flash` | 1.0 | 51 | 1.0 | 1.0 | 1.0 | 1.0 | 720.79 |
| `rules_plus_fallback_qwen35_flash_0223` | 0.7222 | 0 | 0.6226 | 0.6667 | 1.0 | 0.6471 | 5760.93 |
| `rules_plus_fallback_qwen_turbo` | 0.9861 | 51 | 0.9811 | 1.0 | 1.0 | 1.0 | 689.05 |

### 7.2 额外对照：pure fallback turbo（不走规则，72/72 全部强制调模型）

| Candidate | Accuracy | Fallback Used | Manual-edit Acc | Out-of-scope Acc | Avg Latency (ms) |
| --- | ---: | ---: | ---: | ---: | ---: |
| `routing_pure_fallback_qwen_turbo` | 0.9861 | 72 | 1.0 | 1.0 | 943.88 |

这个对照实验不是当前生产方案，而是为了判断“模型本体分类能力”和“规则层触发策略”谁是当前瓶颈。按 2026-05-09 keyed v2 的 apples-to-apples 结果，当前最新 selective fallback 已不低于 pure fallback；其中 `qwen-flash` selective fallback 甚至达到 `1.0`。

## 8. 分维度结果分析

### 8.1 rules_only 基线

`rules_only` 的强项仍然是高精度显式规则：
- `attraction_explain = 1.0`
- `live_info = 0.9167`
- `trip_assistant = 0.9167`
- `boundary_accuracy = 1.0`

但在需要语义承接的三类上明显不足：
- `manual_route_edit_redirect = 0.25`
- `translation = 0.125`
- `out_of_scope = 0.1875`

这说明在去掉“弱旅游信号直接 out_of_scope”兜底之后，规则层确实更符合产品方向，但也把模型补位的必要性暴露得更充分。

### 8.2 qwen-flash

`qwen-flash` 相比 `rules_only` 已经带来大幅提升：
- 总准确率提升到 `0.8611`
- `manual_route_edit_redirect` 提升到 `0.9167`
- `live_info` / `trip_assistant` / `attraction_explain` 都达到 `1.0`
- `conflict_accuracy = 0.9444`

但残余问题仍较多集中在：
- translation 三类混淆
- travel-adjacent 的 `out_of_scope`
- 一条软表达 route-edit

### 8.3 qwen3.5-flash-2026-02-23

这一候选在本轮配置下没有形成有效 fallback：
- `fallback_used_cases = 0`
- 准确率与 `rules_only` 完全相同：`0.5694`
- 平均时延却高达 `5772.77ms`

因此本轮可视为“不产生有效收益且时延显著偏高”，不建议继续作为当前 fallback 候选。

### 8.4 qwen-turbo

在 2026-05-08 首轮里，`qwen-turbo` 是最佳候选：
- 总准确率 `0.8889`
- `needs_fallback_accuracy = 0.9434`
- `manual_route_edit_accuracy = 0.9167`
- `out_of_scope = 0.75`
- `conflict_accuracy = 1.0`
- 平均时延 `681ms`

但在 2026-05-09 keyed v2 rerun 中，经过 benchmark/runtime 对齐和规则收口后，`qwen-turbo` selective fallback 已进一步提升到：
- 总准确率 `0.9861`
- `needs_fallback_accuracy = 0.9811`
- `manual_route_edit_accuracy = 1.0`
- `out_of_scope = 1.0`
- `conflict_accuracy = 1.0`
- 平均时延 `689.05ms`

这一轮它和 pure fallback turbo 已经打平，说明当前 `qwen-turbo` 的主要残余问题不再是规则层漏放太多样本，而是最后 1 条 fallback 边界题本身。

### 8.5 pure fallback turbo 对照实验

在额外追加的一轮对照实验中，我们强制所有 72 条 case 都直接走 `qwen-turbo`，完全绕过规则层，只保留同一版中文 fallback prompt。

2026-05-09 keyed v2 正式结果：
- 总准确率 `0.9861`（71/72）
- `attraction_explain = 1.0`
- `live_info = 1.0`
- `trip_assistant = 0.9167`
- `manual_route_edit_redirect = 1.0`
- `translation = 1.0`
- `out_of_scope = 1.0`
- 平均时延 `943.88ms`

这个结果说明：
- `qwen-turbo` 的纯分类能力本身依然很强
- 但在 keyed v2 这一轮，最新 selective fallback 已不再低于 pure fallback
- 这也意味着当前优化方向要更细：不是简单地“多交给模型”，而是继续盯住少数 fallback prompt / few-shot 边界题

## 9. 按 intent / conflict / hard case 的结论

### 9.1 intent 维度

在 `qwen-turbo` 上：
- `attraction_explain = 1.0`
- `live_info = 1.0`
- `trip_assistant = 1.0`
- `manual_route_edit_redirect = 0.9167`
- `translation = 0.625`
- `out_of_scope = 0.75`

因此剩余薄弱面已经明显收口到：
- `translation`
- `out_of_scope`
- 极少数软表达 route-edit

### 9.2 conflict 维度

`qwen-turbo` 的 conflict 结果：
- `live_vs_attraction_conflict = 1.0`
- `trip_vs_edit_conflict = 1.0`
- `small_margin = 1.0`
- `boundary_topic_conflict = 1.0`
- `low_top_score = 0.9032`

这说明本轮中文 prompt + zh-hard 数据集已经把主要冲突题的方向收口出来了，后续重点不再是“大框架是否成立”，而是剩余 bucket 的局部补强。

## 10. 典型误判案例

以下先写 `rules + selective fallback qwen-turbo` 的剩余错例，再补 pure fallback 对照结论：

### 10.1 soft route edit
- bucket: `route_edit_soft_zh`
- query: `下一站能不能改近一点？`
- expected: `manual_route_edit_redirect`
- actual: `trip_assistant`

判断：
- 当前“弱改路线诉求”仍容易被模型理解成普通行程建议，而不是明确 route edit。
- 后续可继续强化“改近一点 / 换近一点 / 调近一点 / 轻松一点但保持现有路线语境”的 few-shot 或词表信号。

### 10.2 translation 显式请求仍会漂移
- `这段介绍帮我翻成中文，不用解释。` -> `attraction_explain`
- `把今天的闭馆通知翻成中文给工作人员看。` -> `live_info`
- `帮我把这句话换成自然一点的中文说法。` -> `manual_route_edit_redirect`

判断：
- translation 当前最容易被三类信号抢走：
  - explain 内容词
  - live notice 内容词
  - “换成” 这类与 route-edit 共形的动词
- 后续应继续强化“只要明确要求翻译/改写成另一种语言，就优先归 translation”的约束，必要时加入极少量 few-shot。

### 10.3 travel-adjacent out_of_scope
- `给我写个 Python 排序算法。` -> `trip_assistant`
- `现在买什么股票比较好？` -> `trip_assistant`
- `从北京南站到故宫最快怎么坐地铁？` -> `trip_assistant`
- `今天北京空气质量怎么样？` -> `live_info`

判断：
- 当前问题分两类：
  1. hard deny 非旅游任务在 router 层仍可能被 travel signal 拉偏
  2. travel-adjacent 但当前产品不支持的话题（如 transit / air quality）仍会向 `trip_assistant` 或 `live_info` 漂移
- 后续应继续补 boundary / unsupported travel-adjacent 的判别样本，而不是回到“大量弱信号直接拒答”的旧策略。

### 10.4 keyed v2 当前唯一共同错例
- `如果中间先吃点东西，后面接哪个点更合理？` -> `manual_route_edit_redirect`

判断：
- 在 2026-05-09 keyed v2 这一轮里，这条 `trip_assistant_after_meal_zh` 是 `rules_plus_fallback_qwen_turbo` 与 `routing_pure_fallback_qwen_turbo` 的共同唯一错例。
- 这说明问题已经收口成 fallback 分类边界：模型会把“中间先吃点东西 / 后面接哪个点更合理”理解成在重排现有路线，而不是普通的下一步安排建议。
- 因而下一轮更值得改的是 fallback prompt / few-shot 对 `trip_assistant` vs `manual_route_edit_redirect` 的边界表达，而不是重新放松规则层去硬抓这类句子。

## 11. 准确率 / 时延 / 成本综合结论

### 推荐排序
1. `qwen-flash`（按 2026-05-09 keyed v2 结果）
2. `qwen-turbo`
3. `rules_only`
4. `qwen3.5-flash-2026-02-23`

### 结论说明

- `qwen-flash`：在最新 keyed v2 rerun 中达到 `1.0`，是当前同口径结果最优的 selective fallback 候选。
- `qwen-turbo`：在 keyed v2 中达到 `0.9861`，和同轮 pure fallback turbo 持平，仍然是很强的备选；当前只剩 1 条 fallback 边界题。
- `rules_only`：最新也提升到 `0.7222`，说明规则层本身已经比首轮更稳，但仍不足以单独承担最终方案。
- `qwen3.5-flash-2026-02-23`：当前配置下既没有带来准确率收益，也存在明显时延问题，建议继续移出主比较集。
- pure fallback 对照实验额外说明：最新 keyed v2 下，selective fallback 已经不再低于 pure fallback，因此下一轮首要优化对象从“扩大规则放行范围”进一步收口为“少数 fallback 边界题的提示词/样例修正”。

## 12. 推荐下一步

按优先级建议：

1. 下一轮优先重设计规则模块，而不是先换模型。
   - 重点复查哪些 query 被规则层过早直接通过
   - 重点复查哪些 query 本应交给 fallback，但没有进入 fallback
   - 重点复查 unsupported travel-adjacent 与 hard deny 的边界口径

2. 规则层重点补三类：
   - `translation` 的 top confusion：explicit translation / notice translation / natural-English paraphrase
   - soft route-edit 表达：改近一点 / 轻松一点 / 换顺一点 / 调整得没那么赶
   - `out_of_scope` 的 travel-adjacent：transit / air quality / queue / crowd 口语表达 / hard deny 非旅游任务

3. 继续保留 pure fallback turbo 作为对照基线。
   - 它可以帮助判断问题是“模型不会分”，还是“规则没有把句子交给模型”

4. 补真实成本累计逻辑，让下一轮报告能把 cost 一起纳入正式排序。

5. 只有在规则模块重设计后仍然卡在局部 bucket，再考虑少量 few-shot 或 prompt 微调，而不是先扩大 prompt 复杂度。
