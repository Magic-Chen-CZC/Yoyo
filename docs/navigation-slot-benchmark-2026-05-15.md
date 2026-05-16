# Navigation Slot Benchmark - 2026-05-15

本轮按新的导航 slot 方案新增 100 条专项 case，覆盖 `next_stop`、`destination_only`、`explicit_route`、`multi_leg`、北京同名/别名消歧，以及少量边界负例。

同日追加一轮复杂混合 100 case：在导航 query 中混入游览评价、闲聊、否定改路线、下一步安排、公共交通模式和 50-80 字长口语问法，用来验证主链路是否会被非导航话术抢意图。

## 产物

- 设计文档：`docs/navigation-slot-routing-design.md`
- 生成脚本：`evals/build_navigation_slot_100_dataset.py`
- 数据集：`evals/datasets/navigation_slot_100_cases.json`
- 复杂混合数据集：`evals/datasets/navigation_slot_complex_100_cases.json`
- 结果明细：`evals/results/navigation_slot_100_cases.json`
- 复杂混合结果明细：`evals/results/navigation_slot_complex_100_cases.json`
- 公共交通模式复跑明细：`evals/results/navigation_slot_100_transit_mode_cases.json`
- 公共交通模式复杂复跑明细：`evals/results/navigation_slot_complex_100_transit_mode_cases.json`
- 汇总结果：`evals/results/navigation_slot_100_summary.json`
- 复杂混合汇总结果：`evals/results/navigation_slot_complex_100_summary.json`
- 公共交通模式复跑汇总：`evals/results/navigation_slot_100_transit_mode_summary.json`
- 公共交通模式复杂复跑汇总：`evals/results/navigation_slot_complex_100_transit_mode_summary.json`
- Excel：`evals/results/navigation_slot_100_results.xlsx`
- 复杂混合 Excel：`evals/results/navigation_slot_complex_100_results.xlsx`
- 公共交通模式复跑 Excel：`evals/results/navigation_slot_100_transit_mode_results.xlsx`
- 公共交通模式复杂复跑 Excel：`evals/results/navigation_slot_complex_100_transit_mode_results.xlsx`

## 覆盖分布

| category | cases |
|---|---:|
| next_stop | 15 |
| destination_only_gps | 15 |
| destination_only_current_stop | 15 |
| explicit_route | 20 |
| multi_leg | 20 |
| beijing_disambiguation | 10 |
| boundary_negative | 5 |

## 执行命令

```bash
PYTHONPATH=src .venv/bin/python evals/build_navigation_slot_100_dataset.py
PYTHONPATH=src .venv/bin/python evals/run_navigation_benchmark.py \
  --dataset evals/datasets/navigation_slot_100_cases.json \
  --output-cases evals/results/navigation_slot_100_cases.json \
  --output-summary evals/results/navigation_slot_100_summary.json \
  --excel-output evals/results/navigation_slot_100_results.xlsx
PYTHONPATH=src .venv/bin/python evals/build_navigation_slot_complex_100_dataset.py
PYTHONPATH=src .venv/bin/python evals/run_navigation_benchmark.py \
  --dataset evals/datasets/navigation_slot_complex_100_cases.json \
  --output-cases evals/results/navigation_slot_complex_100_cases.json \
  --output-summary evals/results/navigation_slot_complex_100_summary.json \
  --excel-output evals/results/navigation_slot_complex_100_results.xlsx
```

默认不触发真实高德网络调用。需要真实高德检查时加 `--check-amap`。

## 最终结果

| metric | value |
|---|---:|
| total_cases | 100 |
| pass_count | 100 |
| pass_rate | 1.0000 |
| intent_correct_rate | 1.0000 |
| slot_correct_rate | 1.0000 |
| amap_checked_cases | 0 |
| amap_reasonable_cases | 0 |

## 复杂混合 100 case 结果

| metric | value |
|---|---:|
| total_cases | 100 |
| pass_count | 100 |
| pass_rate | 1.0000 |
| intent_correct_rate | 1.0000 |
| slot_correct_rate | 1.0000 |
| amap_checked_cases | 0 |
| amap_reasonable_cases | 0 |

| category | total | pass | pass_rate |
|---|---:|---:|---:|
| complex_next_stop | 20 | 20 | 1.0000 |
| complex_destination_gps | 20 | 20 | 1.0000 |
| complex_destination_current_stop | 10 | 10 | 1.0000 |
| complex_explicit_route | 15 | 15 | 1.0000 |
| complex_multi_leg | 20 | 20 | 1.0000 |
| complex_current_location | 5 | 5 | 1.0000 |
| complex_boundary_negative | 10 | 10 | 1.0000 |

本轮复杂集初跑 `pass_rate=0.81`，主要失败集中在：

- `想去X怎么走 / 等会去X怎么走 / 接着去X怎么走` 被 trip-assistant 或 manual-route-edit 抢意图。
- `从这里到X` 句子前面还有一个“从故宫出来”时，显式路线规则误切到第一个 `从`。
- `从现在这个站继续过去，下面到X怎么去` 把“现在这个站继续过去”当成真实 origin。
- `给我分段路线` 没被当成导航动作。
- 旧口径下 `坐地铁...不是问步行路线` 曾作为边界拒答；当前公共交通已支持，测试集已改为 `navigation_text + transit`。

修复后复杂集和原 100 条专项集均为 `pass_rate=1.0`。

## 分类别结果

| category | total | pass | pass_rate |
|---|---:|---:|---:|
| next_stop | 15 | 15 | 1.0000 |
| destination_only_gps | 15 | 15 | 1.0000 |
| destination_only_current_stop | 15 | 15 | 1.0000 |
| explicit_route | 20 | 20 | 1.0000 |
| multi_leg | 20 | 20 | 1.0000 |
| beijing_disambiguation | 10 | 10 | 1.0000 |
| boundary_negative | 5 | 5 | 1.0000 |

## 本轮修复点

- 新增 `place_resolver.py`，维护北京导航地点注册表，包含 `place_id`、别名、坐标和 adcode。
- `NavigationSlotResult` / `NavigationSlotPayload` 增加 `origin_place` 与 `destination_places`，保留可审计的地点解析结果。
- `destination_only` 与 `next_stop` 优先使用 `session_context.current_position` 作为 GPS 起点；无 GPS 时回退 `current_stop_name`。
- `explicit_route` 不被 GPS/current stop 覆盖；`从这里到X` 会使用 GPS/current stop。
- `multi_leg` 按 destinations 顺序逐段调用并聚合。
- 高德 client 支持已知坐标直传，未注册地点 geocode 时增加北京范围校验。
- `从A前往B` 已纳入显式起终点规则。
- 嵌入式目的地问法已纳入导航意图优先级，例如 `想去X怎么走`、`等会去X怎么走`、`接着去X怎么走`、`下面到X怎么去`。
- 显式路线解析改为从右侧 `从` 候选开始尝试，避免被前置闲聊里的 `我从故宫出来...` 干扰。
- `当前站 / 当前站点 / 现在这个站` 作为行程站点引用，回填 `current_stop_name`；`这里 / 我这儿 / 当前位置` 继续优先使用 GPS。
- `分段路线 / 分段` 已纳入导航动作；公交/地铁问法现在属于 `navigation_text` 的 `transit` 模式，不再作为地铁边界拒答。
- 出行方式槽位已扩展为 `walking/driving/transit`，显式方式优先；未指定方式时按已解析坐标的连续路段最大直线距离判断，超过 3km 默认 `transit`，否则默认 `walking`。
- Amap client 已接入公共交通 endpoint `/v3/direction/transit/integrated`，并把公交/地铁方案里的步行段和 busline 段归一化为可读 steps。
- `别导航 / 先别导航 / 别急着导航` 会压低 navigation 分数，避免“下一站去哪”被导航词误抢；停车场/车位类请求继续归 `out_of_scope`。
- 条件式改路线 `如果下雨，就把X挪到明天` 继续归 `manual_route_edit_redirect`，不被天气词抢走。
- runner 已修正 `_resolve_navigation_slots(...)` 返回 `(slot_result, debug)` 的新接口，并输出 place_id/source 字段。

## 真实高德检查说明

本轮 benchmark 没有加 `--check-amap`，因此 `amap_checked_cases=0`。原因是默认回归应稳定、低成本、无外部网络依赖。

后续需要高德真实检查时，先确认本地 `MAP_API_KEY` 可用，再用 `--check-amap` 单独跑；重点关注：

- `天坛` / `祈年殿` 是否解析为北京 `temple_of_heaven`
- `前门` / `正阳门` 是否解析为 `zhengyangmen`
- GPS origin 是否绕过 geocode
- 多段路线是否每段都有 distance/duration
- 非北京 geocode 是否 degraded
