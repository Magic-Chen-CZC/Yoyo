# QA Intent Rule Hard 500 Benchmark - 2026-05-15

本轮目标是继续扩大意图路由 hardcase 覆盖，生成 500 条更复杂、口语化、多意图和带否定边界的中文 canonical query，并把它们与此前 300 条维护集整理成 800 条长期回归集。

## 产物

- 生成脚本：`evals/build_routing_rule_hard_500_dataset.py`
- 新增 500 条：`evals/datasets/routing_rule_hard_500_cases.yaml`
- 800 条合集：`evals/datasets/routing_rule_all_800_cases.yaml`
- 500 条结果：`evals/results/routing_rule_hard_500_final_cases.json`
- 500 条汇总：`evals/results/routing_rule_hard_500_final_summary.json`
- 800 条结果：`evals/results/routing_rule_all_800_final_cases.json`
- 800 条汇总：`evals/results/routing_rule_all_800_final_summary.json`

## 数据集分布

| intent | cases |
|---|---:|
| smalltalk | 25 |
| attraction_explain | 89 |
| live_info | 68 |
| weather_info | 60 |
| navigation_text | 69 |
| trip_assistant | 73 |
| manual_route_edit_redirect | 39 |
| translation | 33 |
| out_of_scope | 44 |

500 条 hardcase 中，标注期望直达 331 条、期望 fallback 169 条。样本重点覆盖：

- 礼貌/能力询问混入任务词，例如“文字导航和景点讲解，先回答能做什么”
- live_info 与 attraction_explain 的否定边界，例如“不是问今天开不开，单纯想听历史”
- weather/live/attraction 多意图转向，例如“现在问的是今天温度”
- navigation/trip 边界，例如“下一站去哪我知道了，现在问下一站怎么走”
- trip/edit 边界，例如“不要直接删，先判断会不会更轻松”
- translation 正负样本，例如“不是要逐句翻译，而是解释概念”
- unsupported boundary 正负样本，例如“先不管人多不多，告诉我怎么走”

## 执行命令

```bash
PYTHONPATH=src .venv/bin/python evals/build_routing_rule_hard_500_dataset.py
PYTHONPATH=src .venv/bin/python evals/run_routing_benchmark.py --dataset evals/datasets/routing_rule_hard_500_cases.yaml --candidate-name rules_only_hard_500_final --output-cases evals/results/routing_rule_hard_500_final_cases.json --output-summary evals/results/routing_rule_hard_500_final_summary.json
PYTHONPATH=src .venv/bin/python evals/run_routing_benchmark.py --dataset evals/datasets/routing_rule_all_800_cases.yaml --candidate-name rules_only_all_800_final --output-cases evals/results/routing_rule_all_800_final_cases.json --output-summary evals/results/routing_rule_all_800_final_summary.json
```

## 最终结果

| dataset | total | accuracy | safe_accuracy | direct_pass | direct_pass_precision | false_direct_pass | fallback_needed | avg_latency_ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| hard 500 | 500 | 0.9240 | 1.0000 | 176 | 1.0000 | 0 | 324 | 0.70 |
| all 800 | 800 | 0.9350 | 1.0000 | 307 | 1.0000 | 0 | 493 | 0.44 |

本轮更看重 `direct_pass_precision` 和 `false_direct_pass`。最终 500 / 800 两套都达到直达准确率 100%，没有规则层高风险误直达；剩余 raw accuracy 错例都已被规则判为需要 fallback，生产链路会交给 fallback classifier 继续裁决。

## 500 条 hardcase 分 intent 结果

| intent | total | correct | accuracy |
|---|---:|---:|---:|
| smalltalk | 25 | 22 | 0.8800 |
| attraction_explain | 89 | 89 | 1.0000 |
| live_info | 68 | 68 | 1.0000 |
| weather_info | 60 | 55 | 0.9167 |
| navigation_text | 69 | 64 | 0.9275 |
| trip_assistant | 73 | 55 | 0.7534 |
| manual_route_edit_redirect | 39 | 35 | 0.8974 |
| translation | 33 | 30 | 0.9091 |
| out_of_scope | 44 | 44 | 1.0000 |

## 本轮修复点

- `smalltalk` 能力询问与任务词冲突时强制 fallback，避免“你能做文字导航和景点讲解吗”误直达任务 intent。
- 补充 live_info 否定句式：`不是问今天开不开`、`先别查开放时间`、`不用查 + 开不开` 等。
- 补充 crowd/traffic boundary 的否定与导航转向：`先不管人多不多`、`交通怎么走`、`交通路线`。
- 补充 navigation 句式：`文字步骤`、`分两段`、`入口怎么找`、`附近/周边 + 怎么走`。
- 补充 trip/status 句式：`下一站是不是`、`按原计划`、`是不是后面的点`、`更轻松`。
- 修复 `开放到几点` 被 `放到` 误触发为 route edit 的问题。
- 补充 weather focus 结构：`现在问的是今天温度`、`温度大概多少`、`今天适合去吗`。
- 补充 route edit 句式：`不要去`、`重新排`、`排一下`、`顺序`。

## 剩余观察

剩余 raw accuracy 错例主要集中在：

- `trip_assistant` vs `navigation_text`
- `trip_assistant` vs `manual_route_edit_redirect`
- `weather_info` vs `attraction_explain`
- `translation` vs `attraction_explain`

这些样本都没有 direct-pass 风险，当前策略是继续交给 fallback classifier，而不是继续放宽规则直达。下一轮如果要提高 raw accuracy，应优先优化 fallback prompt / few-shot，而不是把规则层改成更激进的主分类器。
