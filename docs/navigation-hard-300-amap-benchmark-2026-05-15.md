# Navigation Hard 300 Amap Benchmark - 2026-05-15

本轮新增 300 条复杂导航意图 case，并连接真实高德 Web 服务验证。

## 覆盖范围

| 维度 | 覆盖 |
|---|---|
| request_kind | `next_stop` 60、`destination_only` 80、`explicit_route` 80、`multi_leg` 80 |
| GPS | GPS 起点、current_stop 起点、显式起点混合 |
| 距离 | 3km 内 187、超过 3km 113 |
| mode | `walking` 130、`driving` 51、`transit` 119 |
| mode_source | 显式出行方式 251、距离默认 49 |
| hardcase | 口语长句、多意图干扰、否定地铁后步行、多段路线、显式起点覆盖 GPS |

## 产物

- 生成脚本：`evals/build_navigation_slot_hard_300_dataset.py`
- 数据集：`evals/datasets/navigation_slot_hard_300_cases.json`
- runner：`evals/run_navigation_benchmark.py`
- 规则/槽位本地结果：`evals/results/navigation_slot_hard_300_slot_results.xlsx`
- 真实高德最终结果：`evals/results/navigation_slot_hard_300_amap_retry_results.xlsx`
- 真实高德 case 明细：`evals/results/navigation_slot_hard_300_amap_retry_cases.json`
- 真实高德 summary：`evals/results/navigation_slot_hard_300_amap_retry_summary.json`
- 公共交通空结果步行兜底后最终结果：`evals/results/navigation_slot_hard_300_amap_fallback_results.xlsx`
- 公共交通空结果步行兜底后 case 明细：`evals/results/navigation_slot_hard_300_amap_fallback_cases.json`
- 公共交通空结果步行兜底后 summary：`evals/results/navigation_slot_hard_300_amap_fallback_summary.json`
- 公交/地铁细分后槽位结果：`evals/results/navigation_slot_hard_300_transit_pref_slot_results.xlsx`
- 公交/地铁细分后真实高德最终结果：`evals/results/navigation_slot_hard_300_transit_pref_amap_results.xlsx`
- 公交/地铁细分后真实高德 case 明细：`evals/results/navigation_slot_hard_300_transit_pref_amap_cases.json`
- 公交/地铁细分后真实高德 summary：`evals/results/navigation_slot_hard_300_transit_pref_amap_summary.json`

## 执行命令

```bash
PYTHONPATH=src .venv/bin/python evals/build_navigation_slot_hard_300_dataset.py

PYTHONPATH=src .venv/bin/python evals/run_navigation_benchmark.py \
  --dataset evals/datasets/navigation_slot_hard_300_cases.json \
  --output-cases evals/results/navigation_slot_hard_300_slot_cases.json \
  --output-summary evals/results/navigation_slot_hard_300_slot_summary.json \
  --excel-output evals/results/navigation_slot_hard_300_slot_results.xlsx \
  --progress-every 50

PYTHONPATH=src .venv/bin/python evals/run_navigation_benchmark.py \
  --dataset evals/datasets/navigation_slot_hard_300_cases.json \
  --output-cases evals/results/navigation_slot_hard_300_amap_retry_cases.json \
  --output-summary evals/results/navigation_slot_hard_300_amap_retry_summary.json \
  --excel-output evals/results/navigation_slot_hard_300_amap_retry_results.xlsx \
  --check-amap \
  --progress-every 25 \
  --case-delay-ms 150

PYTHONPATH=src .venv/bin/python evals/run_navigation_benchmark.py \
  --dataset evals/datasets/navigation_slot_hard_300_cases.json \
  --output-cases evals/results/navigation_slot_hard_300_amap_fallback_cases.json \
  --output-summary evals/results/navigation_slot_hard_300_amap_fallback_summary.json \
  --excel-output evals/results/navigation_slot_hard_300_amap_fallback_results.xlsx \
  --check-amap \
  --progress-every 25 \
  --case-delay-ms 150

PYTHONPATH=src .venv/bin/python evals/run_navigation_benchmark.py \
  --dataset evals/datasets/navigation_slot_hard_300_cases.json \
  --output-cases evals/results/navigation_slot_hard_300_transit_pref_amap_cases.json \
  --output-summary evals/results/navigation_slot_hard_300_transit_pref_amap_summary.json \
  --excel-output evals/results/navigation_slot_hard_300_transit_pref_amap_results.xlsx \
  --check-amap \
  --progress-every 25 \
  --case-delay-ms 150
```

真实高德调用需要本地 `MAP_API_KEY` 和外网访问权限。

## 最终结果（transit 空结果步行兜底后）

| metric | value |
|---|---:|
| total_cases | 300 |
| pass_count | 300 |
| pass_rate | 1.0000 |
| intent_correct_rate | 1.0000 |
| slot_correct_rate | 1.0000 |
| amap_checked_cases | 300 |
| amap_reasonable_cases | 300 |
| amap_final_answer_cases | 300 |
| amap_mode_fallback_cases | 15 |
| amap_reasonable_rate | 1.0000 |

## 最终结果（公交/地铁细分后）

| metric | value |
|---|---:|
| total_cases | 300 |
| pass_count | 300 |
| pass_rate | 1.0000 |
| intent_correct_rate | 1.0000 |
| slot_correct_rate | 1.0000 |
| amap_checked_cases | 300 |
| amap_reasonable_cases | 300 |
| amap_final_answer_cases | 300 |
| amap_mode_fallback_cases | 28 |
| amap_transit_preference_satisfied_cases | 119 |
| amap_reasonable_rate | 1.0000 |

本轮把公共交通大类继续拆成 `bus`、`subway`、`public_transport`：

- 公交请求：规则槽位输出 `transit_preference=bus`，高德公交规划使用不乘地铁策略，并在返回后过滤掉含地铁乘车段的方案。
- 地铁请求：规则槽位输出 `transit_preference=subway`，优先选择含地铁乘车段的方案；如果真实方案里还包含公交接驳，最终回复显示 `公交+地铁`。
- 公共交通泛化请求：`transit_preference=public_transport`，允许公交、地铁或混合方案。
- Excel 新增 `actual_transit_preference`、`amap_requested_transit_preference`、`amap_final_transit_vehicle_types`、`amap_transit_preference_satisfied`，用于人工确认“公交 case 是否真的没有返回地铁”。

`amap_mode_fallback_cases` 从 15 增加到 28，是因为细分后公交/地铁请求会严格过滤不符合偏好的公共交通方案；例如用户明确说公交时，如果高德只给地铁方案，就按“没有合适公交方案”处理并转步行兜底。这是产品口径收紧，不是槽位退化。

## 分类别（兜底前基线与兜底后）

兜底前基线：

| category | total | pass | pass_rate |
|---|---:|---:|---:|
| hard_next_stop | 60 | 58 | 0.9667 |
| hard_destination_only | 80 | 78 | 0.9750 |
| hard_explicit_route | 80 | 80 | 1.0000 |
| hard_multi_leg | 80 | 69 | 0.8625 |

兜底后：

| category | total | pass | pass_rate |
|---|---:|---:|---:|
| hard_next_stop | 60 | 60 | 1.0000 |
| hard_destination_only | 80 | 80 | 1.0000 |
| hard_explicit_route | 80 | 80 | 1.0000 |
| hard_multi_leg | 80 | 80 | 1.0000 |

## 按 mode

| mode | total | pass | pass_rate |
|---|---:|---:|---:|
| walking | 130 | 130 | 1.0000 |
| driving | 51 | 51 | 1.0000 |
| transit | 119 | 119 | 1.0000 |

## 按 mode_case

| mode_case | total | pass | pass_rate |
|---|---:|---:|---:|
| unspecified | 49 | 49 | 1.0000 |
| explicit_walking | 50 | 50 | 1.0000 |
| explicit_driving | 51 | 51 | 1.0000 |
| explicit_transit_metro | 51 | 51 | 1.0000 |
| explicit_transit_bus | 50 | 50 | 1.0000 |
| negated_transit_walking | 49 | 49 | 1.0000 |

## 时延

兜底后基线：

| stage | avg_ms | median_ms | p95_ms | max_ms |
|---|---:|---:|---:|---:|
| intent | 1.24 | 0.0 | 1 | 307 |
| slot | 0.0 | 0.0 | 0 | 0 |
| amap | 446.02 | 342.0 | 1044 | 1643 |
| total | 448.36 | 344.5 | 1045 | 1645 |

公交/地铁细分后：

| stage | avg_ms | median_ms | p95_ms | max_ms |
|---|---:|---:|---:|---:|
| intent | 1.36 | 0.0 | 1 | 267 |
| slot | 0.0 | 0.0 | 0 | 0 |
| amap | 502.20 | 373.0 | 1282 | 1961 |
| total | 504.61 | 374.5 | 1283 | 1963 |

说明：`intent` 的 max 主要是首次加载 jieba 词典，后续基本为 0-1ms。

## 兜底前失败分析

兜底前剩余 15 条失败全部是：

- `actual_mode = transit`
- `distance_bucket = within_3km`
- `amap_reason = empty_navigation_payload`

典型失败：

- `下一站怎么去，坐地铁也可以`
- `我想去景山公园坐地铁怎么走`
- `从天安门广场到故宫再到景山公园坐地铁怎么走`

结论：

- 意图识别、槽位抽取、origin/destination/place_id/mode/mode_source 均正确。
- walking 和 driving 的真实高德返回本轮为 100% 合理。
- transit 的失败集中在短距离公交/地铁无方案，尤其天安门、故宫、景山这类步行距离很近的路段。
- multi_leg 失败率更高，是因为只要任一子路段 transit 无方案，聚合结果就会标记为 degraded。

兜底后这 15 条全部转为 `amap_mode_fallback_used=true`，`amap_final_mode` 为 `walking` 或 `mixed`，最终回答包含：

```text
当前没有合适的公共交通，返回给你步行方案。
```

最终回复字段 `amap_final_answer` 用于人工看表，包含起终点、总距离/耗时、分段步骤和兜底话术，不暴露 provider 名称。

2026-05-15 后续检查又发现：部分公交/地铁 case 的真实 transit 结果里，乘车步骤排在较多“步行到站”步骤之后，旧 formatter 只截前三步会让 `amap_final_answer` 看起来像全程步行。当前已修正为：

- 公共交通最终回复必须保留首个 `乘坐...` 步骤。
- 如果 transit payload 完全没有乘车步骤，则按无合适公共交通处理并重查步行。
- multi-leg 回复增加 `路线总览`，并在每段展示方式、距离和耗时。
- 修复后复查：`final_mode=transit` 的 case 中，`amap_final_answer` 均包含 `乘坐`；`NAVH-EXP-021` 已显示“从北宫门乘坐地铁4号线大兴线...到西四”。

## 本轮代码调整

- `evals/run_navigation_benchmark.py`
  - 新增 intent / slot / amap / total 时延。
  - 新增 `actual_mode_source`、高德距离/耗时/腿数/步数/首段步骤导出。
  - 新增 `amap_final_answer`、`amap_final_mode`、`amap_mode_fallback_used` 和 `amap_mode_fallback_reason` 导出。
  - 新增 `--progress-every`、`--max-cases`、`--case-delay-ms`。
- `src/yoyo/modules/integrations/amap/client.py`
  - `_get_json(...)` 增加 3 次轻量重试，降低真实 benchmark 中 provider 瞬时失败对结果的污染。
  - transit 支持 `transit_preference`，公交请求过滤含地铁方案，地铁请求优先含地铁方案，并导出 `vehicle_types`。
- `src/yoyo/modules/knowledge/navigation_retriever.py`
  - `transit + empty_navigation_payload` 自动转步行重查；multi-leg 按腿兜底并聚合 `final_mode`。
  - 向高德透传公交/地铁偏好，并在 `NavigationLeg` / `NavigationContext` 记录请求偏好与最终车辆类型。
- `src/yoyo/modules/qa/formatters.py`
  - 对公共交通空结果步行兜底增加用户可见话术，不暴露 provider 名称。
  - 公共交通回复优先展示乘车步骤；multi-leg 回复增加路线总览和每段距离/耗时。
  - 最终回复按实际车辆类型显示 `公交`、`地铁`、`公交+地铁`，兜底话术按公交/地铁偏好细分。
- `src/yoyo/modules/knowledge/hybrid_context_builder.py`
  - 槽位层新增 `transit_preference=bus/subway/public_transport`，并保持显式方式优先于 3km 默认策略。
- `evals/run_navigation_benchmark.py`
  - 新增公交/地铁偏好相关字段，并把 `amap_transit_preference_satisfied=false` 计入不合理结果。

## 后续建议

- 继续观察真实线上 multi-leg 中 `mixed` final mode 的用户理解成本，必要时把兜底话术改为按段提示。
- 真实 benchmark 保留 `--case-delay-ms`，避免把 API 压测噪声误当成路线能力问题。
