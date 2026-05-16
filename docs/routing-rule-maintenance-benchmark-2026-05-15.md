# Routing Rule Maintenance Benchmark 2026-05-15

本报告记录首轮 100 case QA intent 规则维护集的 rules-only 运行结果。

## 测试口径

- 数据集：`evals/datasets/routing_rule_maintenance_100_cases.yaml`
- 结果明细：`evals/results/routing_rule_maintenance_100_rules_only_cases.json`
- 汇总结果：`evals/results/routing_rule_maintenance_100_rules_only_summary.json`
- 候选：`rules_only_maintenance_100`
- fallback：未启用
- 语言口径：外语样本保留 `raw_query`，但送入 router 的是中文 canonical query

运行命令：

```bash
PYTHONPATH=src .venv/bin/python evals/run_routing_benchmark.py \
  --dataset evals/datasets/routing_rule_maintenance_100_cases.yaml \
  --candidate-name rules_only_maintenance_100 \
  --output-cases evals/results/routing_rule_maintenance_100_rules_only_cases.json \
  --output-summary evals/results/routing_rule_maintenance_100_rules_only_summary.json
```

## 总结

| 指标 | 结果 |
|---|---:|
| total_cases | 100 |
| correct_cases | 82 |
| rules_only_accuracy | 0.82 |
| direct_pass_cases | 43 |
| direct_pass_correct | 43 |
| false_direct_pass | 0 |
| fallback_needed_cases | 57 |
| avg_latency_ms | 2.88 |

结论：当前规则层偏保守。总准确率只有 82%，但错误 case 全部带 `needs_fallback=True`，没有出现最危险的“错误直达”。后续优化重点不是放宽规则，而是补高置信中文句式和槽位，同时继续让模糊题进入 fallback。

## 按 intent 结果

| expected_intent | total | correct | accuracy |
|---|---:|---:|---:|
| smalltalk | 4 | 2 | 0.50 |
| attraction_explain | 16 | 15 | 0.9375 |
| live_info | 13 | 10 | 0.7692 |
| weather_info | 10 | 6 | 0.60 |
| navigation_text | 14 | 13 | 0.9286 |
| trip_assistant | 12 | 8 | 0.6667 |
| manual_route_edit_redirect | 9 | 6 | 0.6667 |
| translation | 9 | 9 | 1.00 |
| out_of_scope | 13 | 13 | 1.00 |

## 主要混淆

| expected -> predicted | count | 说明 |
|---|---:|---|
| `weather_info` -> `attraction_explain` | 4 | `带伞`、`适合去吗`、`太冷` 这类天气句式未被规则层稳定识别 |
| `live_info` -> `attraction_explain` | 3 | `还能买票`、`能进去吗` 缺少 live operation 句式支持 |
| `trip_assistant` -> `manual_route_edit_redirect` | 3 | `行程/路线` 被 route-edit object 污染，缺少状态问法优先级 |
| `manual_route_edit_redirect` -> `attraction_explain` | 3 | `不要去X了`、`把X提前/放到最后` 缺少 route-edit pattern |
| `smalltalk` -> `out_of_scope` | 2 | `你是谁`、`你能做什么` 未进入 smalltalk 词库 |
| `attraction_explain` -> `out_of_scope` | 1 | `颐和园` 不在当前 runtime 景点实体词库 |
| `navigation_text` -> `out_of_scope` | 1 | `交通怎么走` 被 traffic boundary 抢先压住 |
| `trip_assistant` -> `live_info` | 1 | `当前站是哪里` 的 `当前` 被 live_time 弱信号污染 |

## 错例清单

| case_id | expected | predicted | fallback_reason | query |
|---|---|---|---|---|
| RRM-ST-003 | smalltalk | out_of_scope | low_top_score | 你是谁 |
| RRM-ST-004 | smalltalk | out_of_scope | low_top_score | 你能做什么 |
| RRM-AT-012 | attraction_explain | out_of_scope | low_top_score | 颐和园的建筑有什么特点？ |
| RRM-LI-003 | live_info | attraction_explain | live_vs_attraction_conflict | 景山今天还能买票吗？ |
| RRM-LI-007 | live_info | attraction_explain | live_vs_attraction_conflict | 故宫现在能进去吗？ |
| RRM-LI-008 | live_info | attraction_explain | live_vs_attraction_conflict | 天坛现在还能进去吗？ |
| RRM-WE-004 | weather_info | attraction_explain | live_vs_attraction_conflict | 去故宫今天要不要带伞？ |
| RRM-WE-005 | weather_info | attraction_explain | live_vs_attraction_conflict | 天坛今天要不要带伞？ |
| RRM-WE-006 | weather_info | attraction_explain | live_vs_attraction_conflict | 故宫今天适合去吗？ |
| RRM-WE-007 | weather_info | attraction_explain | live_vs_attraction_conflict | 今天去景山会不会太冷？ |
| RRM-NAV-008 | navigation_text | out_of_scope | boundary_topic_conflict | 故宫附近交通怎么走？ |
| RRM-TRIP-004 | trip_assistant | live_info | low_top_score | 当前站是哪里？ |
| RRM-TRIP-005 | trip_assistant | manual_route_edit_redirect | low_top_score | 行程还剩几站？ |
| RRM-TRIP-006 | trip_assistant | manual_route_edit_redirect | low_top_score | 现在路线走到哪里了？ |
| RRM-TRIP-010 | trip_assistant | manual_route_edit_redirect | low_top_score | 现在路线走到哪里了？ |
| RRM-EDIT-002 | manual_route_edit_redirect | attraction_explain | low_top_score | 不要去天坛了 |
| RRM-EDIT-003 | manual_route_edit_redirect | attraction_explain | low_top_score | 把故宫提前一点 |
| RRM-EDIT-004 | manual_route_edit_redirect | attraction_explain | low_top_score | 把天坛放到最后 |

## 下一步优化点

1. 补 `smalltalk` 精确短句：`你是谁`、`你能做什么`。
2. 扩 runtime 景点实体：至少补 `颐和园`、`圆明园`、`北海公园`、`什刹海`、`南锣鼓巷` 等当前文档词库已有但 runtime 未覆盖的景点。
3. 补 `live_info` 句式：`现在/今天 + 能进去/还能进去/能进/还能买票`。
4. 补 `weather_info` 句式：`要不要带伞`、`会不会太冷/太热`；`适合去吗` 建议保持 fallback 或仅在天气词明确时直达。
5. 调整 traffic boundary 顺序：先抽 `怎么走/怎么去` 槽位，再判断是否是实时路况边界。
6. 提高 trip 状态优先级：`当前站是哪里`、`还剩几站`、`路线走到哪里` 不应被 live_time 或 route-edit object 抢走。
7. 补 route-edit pattern：`不要去X了`、`把X提前`、`把X放到最后`。
