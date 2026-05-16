# QA Intent Rule Maintenance

这份文档定义 QA intent 规则库的日常维护方式。规则资产入口是：

- `docs/qa-intent-routing-rule-design.md`
- `docs/qa-intent-keyword-library.yaml`
- `evals/datasets/routing_rule_maintenance_100_cases.yaml`
- `evals/datasets/routing_rule_hard_500_cases.yaml`
- `evals/datasets/routing_rule_all_800_cases.yaml`

## 维护目标

规则层只负责高置信、可解释、低时延的直达路由。

不追求 rules-only 覆盖所有 query。只要表达含糊、多意图冲突、依赖上下文或证据不足，就应该交给 router fallback 模型裁决。

## 硬约束

- 外语、东南亚语言和中外混合 query 必须先转成中文 canonical query，再进入规则评分。
- 规则评分只维护中文词库、中文句式和中文冲突策略。
- `raw_query`、`source_language`、`pivot_query` 和 translator metadata 必须保留，方便排查翻译层是否改变了意图。
- 显式翻译请求路由时可看中文 pivot，但执行翻译时必须回到 `raw_query` 提取原文，避免 pivot 改写掉待翻译文本。

## 改规则前的归因

看到错例后先分类，不要直接加关键词。

| 错误类型 | 优先修复位置 |
|---|---|
| 外语 pivot 后意图变了 | translator prompt / translation benchmark |
| 规则把不该直达的 query 直达了 | deny / conflict / 阈值 / fallback 条件 |
| 高置信中文句式漏召回 | pattern / slot / 中文词库 |
| 多意图混合题误判 | conflict resolver 或 fallback few-shot |
| fallback 模型裁决错 | fallback prompt / examples / label definition |
| intent 对但回答错 | 下游 SQL / RAG / live_info / weather / navigation / generation |

## 新增规则要求

每次新增关键词、句式或冲突策略，必须同时补测试：

- 至少 1 条正例：应该命中的 query。
- 至少 1 条负例：含有相同关键词但不该命中的 query。
- 至少 1 条冲突例：应该进入 fallback 或命中另一个 intent 的 query。

不能因为单个关键词直接增加 direct pass。direct pass 必须同时满足：

- 必要条件满足，例如 `景点 + 今天/现在 + 开放/预约/门票`。
- 无 deny condition。
- 无 unresolved conflict。
- 分数和 margin 达到该 intent 阈值。
- 对应 benchmark 中没有新增 false direct pass。

## 维护循环

```text
收集错例
-> 标注 expected_intent / expected_boundary_behavior / conflict_type
-> 归因到 translator / rule / fallback / downstream
-> 修改词库、句式、冲突策略或 fallback prompt
-> 跑 router-only benchmark
-> 抽样跑 E2E QA benchmark
-> 更新 README、设计文档、测试报告和 dev-retrospective
```

## 指标口径

重点看这些指标：

- `direct_pass_precision`：规则直达准确率，目标 98%+。
- `false_direct_pass`：最高优先级风险，必须优先修。
- `fallback_rate`：规则不确定交给模型的比例，可以接受偏高。
- `rules_plus_fallback_accuracy`：规则 + fallback 总准确率。
- `translator_pivot_intent_preservation`：外语转中文后是否保留意图。
- `confusion matrix`：按 intent 看误路由方向，重点关注 `trip_assistant` vs `manual_route_edit_redirect`、`live_info` vs `attraction_explain`、`weather_info` vs `live_info`。

## 测试集维护

`routing_rule_maintenance_100_cases.yaml` 是日常规则健康检查集，不追求真实流量比例，而是覆盖高风险边界：

- smalltalk/task 礼貌前缀
- attraction_explain 景点讲解
- live_info 当日开放、门票、预约
- weather_info 天气、温度、带伞
- navigation_text 文本导航和路线槽位
- trip_assistant 当前行程状态
- manual_route_edit_redirect 人工改路线
- translation 显式翻译
- out_of_scope hard deny 与 unsupported boundary
- 外语 pivot 后的中文 canonical query

新增 case 要写清楚：

- `query`：实际进入当前 router 的中文 canonical query。
- `raw_query`：可选，原始外语或混合语 query。
- `query_zh`：中文 pivot，与 `query` 一致或作为说明字段。
- `expected_intent`：期望 intent。
- `conflict_type`：主要冲突类型。
- `label_rationale`：为什么这样标注。

## 验收标准

规则层改动默认验收标准：

- 100 case 日常集准确率不能下降。
- 已知 hard negative 不能回退。
- false direct pass 必须为 0 或有明确产品接受理由。
- 新增 fallback case 可以接受，但要说明原因。
- 如果为了提升召回引入新误判，应回滚该规则或改成 fallback。

## 首轮基线

2026-05-15 已新增并运行首轮 100 case 维护集：

- 报告：`docs/routing-rule-maintenance-benchmark-2026-05-15.md`
- 数据集：`evals/datasets/routing_rule_maintenance_100_cases.yaml`
- rules-only 准确率：`82/100 = 0.82`
- direct pass：`43/43` 正确
- false direct pass：`0`
- 当前主要缺口：天气句式、live 入园句式、trip 状态问法、route-edit 顺序/删除句式、runtime 景点实体覆盖。

## 复杂集与全量集

2026-05-15 追加 200 条复杂 hard cases，并整理成 300 条合集：

- 复杂集：`evals/datasets/routing_rule_complex_200_cases.yaml`
- 全量合集：`evals/datasets/routing_rule_all_300_cases.yaml`
- 报告：`docs/routing-rule-complex-benchmark-2026-05-15.md`

最终 rules-only 结果：

| dataset | accuracy | safe_accuracy | direct_pass_precision | false_direct_pass |
|---|---:|---:|---:|---:|
| 100 maintenance | 0.9700 | 0.9700 | 1.0000 | 0 |
| 200 complex | 0.8650 | 0.9400 | 1.0000 | 0 |
| 300 all | 0.9000 | 0.9500 | 1.0000 | 0 |

## 500 hardcase 与 800 合集

同日继续追加 500 条更复杂的 hardcase，重点覆盖长口语、多意图、否定边界、能力询问混任务词、navigation/trip、trip/edit、live/explain、weather/live、translation/explain 与 unsupported boundary 正负例。

- 生成脚本：`evals/build_routing_rule_hard_500_dataset.py`
- 500 hardcase：`evals/datasets/routing_rule_hard_500_cases.yaml`
- 800 合集：`evals/datasets/routing_rule_all_800_cases.yaml`
- 报告：`docs/routing-rule-hard-500-benchmark-2026-05-15.md`

最终 rules-only 结果：

| dataset | accuracy | safe_accuracy | direct_pass_precision | false_direct_pass |
|---|---:|---:|---:|---:|
| 500 hard | 0.9240 | 1.0000 | 1.0000 | 0 |
| 800 all | 0.9350 | 1.0000 | 1.0000 | 0 |

后续日常回归优先跑 `routing_rule_all_800_cases.yaml`；需要快速冒烟时再跑 `routing_rule_maintenance_100_cases.yaml`。
