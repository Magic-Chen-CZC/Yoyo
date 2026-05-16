# Routing Rule Complex Benchmark 2026-05-15

本报告记录新增 200 条复杂 QA intent hard cases 后的 rules-only 路由结果，以及本轮规则修复后的复跑结果。

## 测试资产

- 复杂 200 case：`evals/datasets/routing_rule_complex_200_cases.yaml`
- 全量 300 case 合集：`evals/datasets/routing_rule_all_300_cases.yaml`
- 复杂 200 最终明细：`evals/results/routing_rule_complex_200_final_v2_cases.json`
- 复杂 200 最终汇总：`evals/results/routing_rule_complex_200_final_v2_summary.json`
- 全量 300 最终明细：`evals/results/routing_rule_all_300_final_v2_cases.json`
- 全量 300 最终汇总：`evals/results/routing_rule_all_300_final_v2_summary.json`

`routing_rule_all_300_cases.yaml` 使用 `include_datasets` 合并：

- `routing_rule_maintenance_100_cases.yaml`
- `routing_rule_complex_200_cases.yaml`

## 设计口径

这 200 条不是为了刷通过率设计的简单样本，而是刻意覆盖规则容易出错的复杂表达：

- 礼貌前缀 + 真实任务
- 外语 query 经中文 pivot 后的任务
- 多意图混合：live + explain、weather + trip、translation + live
- 否定词：不是翻译、先别改路线、不是问人多不多、不坐地铁
- 边界词污染：交通、人多、餐厅、空气质量
- 长口语：带条件、转折、补充说明、先后顺序
- session-aware 表达：下一站、当前路线、还剩几站
- route edit 和 trip advice 的边界

## Runner 口径更新

本轮 benchmark runner 增加了安全性指标：

- `direct_pass_precision`：规则直达的准确率。
- `false_direct_pass_cases`：最危险的错误，规则错误直达且没有 fallback。
- `safe_accuracy`：intent 正确，或 case 期望 fallback 且规则确实进入 fallback。
- `fallback_decision_accuracy`：当 case 标注 `expected_needs_fallback` 时，判断规则是否按预期 fallback。

## 修复前后对比

### 复杂 200 case

| 指标 | baseline | final |
|---|---:|---:|
| total_cases | 200 | 200 |
| correct_cases | 121 | 173 |
| accuracy | 0.605 | 0.865 |
| safe_cases | 148 | 188 |
| safe_accuracy | 0.740 | 0.940 |
| direct_pass_cases | 55 | 71 |
| direct_pass_precision | 0.7818 | 1.0000 |
| false_direct_pass_cases | 12 | 0 |
| fallback_needed_cases | 145 | 129 |
| fallback_decision_accuracy | 0.445 | 0.515 |
| avg_latency_ms | 1.61 | 1.62 |

### 全量 300 case

| 指标 | baseline | final |
|---|---:|---:|
| total_cases | 300 | 300 |
| correct_cases | 203 | 270 |
| accuracy | 0.6767 | 0.9000 |
| safe_cases | 230 | 285 |
| safe_accuracy | 0.7667 | 0.9500 |
| direct_pass_cases | 98 | 121 |
| direct_pass_precision | 0.8776 | 1.0000 |
| false_direct_pass_cases | 12 | 0 |
| fallback_needed_cases | 202 | 179 |
| fallback_decision_accuracy | 0.445 | 0.515 |
| avg_latency_ms | 1.04 | 1.10 |

### 原 100 case 回归

| 指标 | before | final |
|---|---:|---:|
| total_cases | 100 | 100 |
| correct_cases | 82 | 97 |
| accuracy | 0.8200 | 0.9700 |
| direct_pass_precision | n/a | 1.0000 |
| false_direct_pass_cases | n/a | 0 |
| fallback_needed_cases | 57 | 50 |

## 本轮修复内容

本轮只修高置信、可解释的规则，不放宽模糊语义：

- smalltalk：补 `你是谁`、`你能做什么`、`辛苦了` 等纯寒暄/能力问法。
- 景点实体：补 `颐和园`、`圆明园`、`北海公园`、`什刹海`、`南锣鼓巷`、`雍和宫`、`恭王府`、`中轴线`。
- 景点讲解：补 `意味着什么`、`是什么地方`、`建筑`、`原理`、`格局`、`故事`、`象征`、`价值`。
- live_info：补 `入园`、`能进去`、`停止入场`、`停止检票`、`停售票`、`提前闭馆`、`开不开`。
- weather_info：补 `带伞`、`冷`、`热`、`晒`、`风大`、`体感`、`穿短袖`。
- navigation_text：补 `步行路线`、`文字路线`、`走法`、`少绕路`、`往哪边走`，并加强 A 到 B 路线形状。
- trip_assistant：补 `当前路线`、`路线状态`、`走到哪里`、`还剩`、`哪些点没去`、`下一站如果`、`先确认下一站`。
- route edit：补 `删`、`取消`、`拿掉`、`提前`、`放到`、`挪到`、`移到`、`压缩`、`留一点`，并识别 `把A换成B`。
- negation：补 `不是要翻译`、`不要逐句翻译`、`不是翻译这句话`、`不坐地铁`、`餐厅不用推荐`、`空气质量没关系`、`不是问人多不多` 等否定边界。
- runner：支持 `include_datasets`，并输出 direct pass / false direct pass / safe accuracy。

## 剩余问题

复杂 200 最终仍有 27 条 intent top-1 不正确，但全部没有 false direct pass。其中 15 条因为 case 标注期望 fallback 且规则也进入 fallback，属于可接受的安全态；剩余 12 条是 top intent 错但也进入 fallback，后续可以继续优化 fallback prompt 或进一步补否定结构。

主要剩余混淆：

| expected -> predicted | count |
|---|---:|
| `attraction_explain` -> `live_info` | 3 |
| `navigation_text` -> `trip_assistant` | 3 |
| `trip_assistant` -> `navigation_text` | 3 |
| `trip_assistant` -> `attraction_explain` | 3 |
| `weather_info` -> `attraction_explain` | 2 |
| `trip_assistant` -> `manual_route_edit_redirect` | 2 |

这些 case 多数属于“含否定词、多意图、需要上下文”的 hard cases，不建议继续用关键词强行直达。下一轮优化应优先看 fallback 裁决质量，而不是继续扩 direct pass。

## 运行命令

```bash
PYTHONPATH=src .venv/bin/python evals/run_routing_benchmark.py \
  --dataset evals/datasets/routing_rule_complex_200_cases.yaml \
  --candidate-name rules_only_complex_200_final_v2 \
  --output-cases evals/results/routing_rule_complex_200_final_v2_cases.json \
  --output-summary evals/results/routing_rule_complex_200_final_v2_summary.json

PYTHONPATH=src .venv/bin/python evals/run_routing_benchmark.py \
  --dataset evals/datasets/routing_rule_all_300_cases.yaml \
  --candidate-name rules_only_all_300_final_v2 \
  --output-cases evals/results/routing_rule_all_300_final_v2_cases.json \
  --output-summary evals/results/routing_rule_all_300_final_v2_summary.json
```

## 验证

- `PYTHONPATH=src .venv/bin/python -m py_compile src/yoyo/evals/routing.py src/yoyo/modules/qa/intent_router.py src/yoyo/modules/qa/rule_assets.py`
- `PYTHONPATH=src .venv/bin/pytest tests/test_routing_benchmark.py tests/test_qa_routing_regressions.py -q`
- `36 passed`

补充：`ruff check src/yoyo/evals/routing.py` 已通过；对 `intent_router.py` / `rule_assets.py` 的全量 ruff 仍会暴露仓库既有长行问题，本轮未做大范围格式化重排。
