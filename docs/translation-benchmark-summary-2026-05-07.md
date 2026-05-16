# Translation benchmark 总结（2026-05-07）

## 1. 本轮目标
本轮不是再补 translator 架构，而是基于已经完成的共享 translator、东南亚小语种扩展和正式 benchmark 数据集，做一轮真实跑数与结果整理。

本轮重点包括：
- 对比 `HY-MT1.5-1.8B` 和 `XFYun ITS`
- 覆盖 `product_translation` 与 `routing_preprocess` 两套 translation benchmark
- 覆盖东南亚小语种矩阵：`th`、`vi`、`id`、`ms`、`fil`、`my`、`km`、`lo`
- 覆盖中译外、外译中，以及 bilingual display 场景
- 要求每条 case 显式声明 `user_language`、`source_language`、`target_language`、`direction`
- 去掉极端多语混合 case，并让 runner 对缺字段和方向不一致直接 fail-fast
- 输出可导出的 JSON / Excel 结果，并整理一版中文结论

## 2. 数据范围
### 2.1 Product translation
- suite: `product_translation`
- dataset: `translation_product_sea_v1`
- version: `2026-05-07`
- case 数：136
- 覆盖 question type：
  - `ask_location`
  - `ask_opening_hours`
  - `ask_ticketing`
  - `ask_restroom`
  - `ask_photo_help`
  - `ask_next_stop`
  - `ask_rest_break`
  - `ask_queue_or_entrance`

### 2.2 Routing preprocess
- suite: `routing_preprocess`
- dataset: `translation_routing_sea_v1`
- version: `2026-05-07`
- case 数：48
- 覆盖 routing 场景：
  - `trip_assistant`
  - `live_info`
  - `attraction_explain`
  - `translation`
  - `manual_route_edit_redirect`
  - `out_of_scope`

### 2.3 总规模
- 两套 suite 合计：184 条 case
- 全部真实跑数均已导出到：
  - `evals/results/translation_*_results.json`
  - `evals/results/translation_*_summary.json`
  - `evals/results/benchmark_results.xlsx`
- Excel 已包含：
  - `translation_cases`
  - `translation_model_compare`

## 3. 模型总览结论
### 3.1 总体推荐
当前这轮 benchmark 下，`XFYun ITS` 可以作为更优的线上翻译候选：
- 两套 suite 的平均分都高于 `HY-MT1.5-1.8B`
- 两套 suite 的平均时延都显著低于 `HY-MT1.5-1.8B`
- 在严格显式语种数据集的复跑结果里，XFYun 仍然整体更稳、更快；当前仅 `product_translation` 剩余 2 条 isolated `provider_error` degraded case

`HY-MT1.5-1.8B` 在这轮结果里仍然提供了有价值的对照基线，但当前不再作为后续正式 translator 候选。

## 4. Product translation 对比
| 指标 | HY-MT1.5-1.8B | XFYun ITS |
|---|---:|---:|
| avg_score | 3.85 | 4.69 |
| avg_latency_ms | 1865.11 | 397.95 |
| total_cases | 136 | 136 |
| degraded_cases | 0 | 2 |

结论：
- XFYun 在这轮严格显式语种复跑的 `product_translation` 上，平均分达到 **4.69/5**。
- 即使保留 2 条 isolated `provider_error` degraded case，XFYun 的整体质量和时延仍明显优于 HY-MT。
- 对用户可见翻译而言，当前主路径已经从“数据口径不一致导致整批跑崩”收口到“少量 provider 级异常需要继续观察”。

### 4.1 XFYun 在 product_translation 上的特点
- direct translation 主体已经稳定，`128` 条 direct case 平均分达到 `4.74/5`。
- bilingual display 场景能跑通，但 8 条 case 平均分仍是 `4.0/5`，明显弱于 direct translation，说明展示型翻译还值得继续优化 wording 和 display block 质量。
- 当前只剩 2 条 degraded case：`product-009`（`zh_to_th`，`ask_photo_help`）和 `product-025`（`vi_to_zh`，`ask_restroom`），两条都表现为 `provider_error -> runtime_translation_unavailable`，不是数据字段口径问题。
- 为了便于下次直接定位这类 isolated failure，translation benchmark per-case 结果现在已补落上游错误和重试轨迹字段：`llm_error`、`raw_text`、`structured_output_valid`、`attempt_count`、`retry_performed`、`attempts`。
- plain MT 当前默认采用“单次 1s 超时 + 最多 1 次顺序重试”的策略，只对 timeout / 连接错误 / provider 5xx 等 retryable 上游异常触发，不再继续容忍 18s 级单次长等待。

### 4.2 HY-MT 在 product_translation 上的特点
- `zh -> vi`、`th/vi -> zh` 这类相对常见语言对表现还可以。
- `id/ms/my/km/lo` 等小语种方向掉分明显，尤其是 `zh -> x` 方向。
- bilingual display 的分数还可以，但整体时延偏高，难作为当前默认线上主选。

## 5. Routing preprocess 对比
| 指标 | HY-MT1.5-1.8B | XFYun ITS |
|---|---:|---:|
| avg_score | 3.95 | 4.74 |
| avg_latency_ms | 2561.19 | 173.09 |
| total_cases | 48 | 48 |
| degraded_cases | 0 | 0 |

结论：
- XFYun 在严格显式语种复跑的 `routing_preprocess` 上平均分达到 **4.74/5**。
- 这轮 routing suite 已经做到 **48/48 全覆盖且无 degraded case**。
- 这说明如果后续要把 translator 真正放到 routing 前置链路里，XFYun 当前更适合作为默认 preprocessing provider。

### 5.1 Routing preprocess 里的观察
当前最明显的弱项已经进一步收口到：
- `manual_route_edit_redirect`
- 少数 `trip_assistant` 的 Burmese / Khmer / Lao pivot 中文稳定性

而这轮 strict rerun 里，`translation` intent 已经不再是主要问题；XFYun 的整体 routing preservation 在以下方向尤其稳定：
- `live_info`
- `attraction_explain`
- `translation`
- `out_of_scope`

这意味着当前 translator 的下游价值不只是“翻译得通”，而是“更不容易把原始 query 的 routing 语义翻丢”。

## 6. 严格数据口径复跑补记
本轮补做的不是普通复跑，而是一次数据口径收口后的严格复跑。

本轮新口径包括：
- 每条 case 都必须显式声明 `user_language`、`source_language`、`target_language`、`direction`
- `direction` 必须与 `source_language/target_language` 一致
- `product_translation` 的 direct case 必须满足 `user_language == source_language`
- 去掉极端多语混合 case，避免把不代表真实产品输入的复杂样本混进主 benchmark
- runner 不再对缺失语种字段做 fallback 推断，而是直接 fail-fast

在这套口径下重新跑数后：
- `product_translation`：`avg_score = 4.69`，`avg_latency_ms = 397.95`，`degraded_cases = 2`
- `routing_preprocess`：`avg_score = 4.74`，`avg_latency_ms = 173.09`，`degraded_cases = 0`

因此当前结论应以这轮严格显式语种复跑结果为准。

## 7. XFYun 成本估算（字符计费口径）
### 7.1 估算前提
由于 XFYun ITS 本轮结果没有返回 token usage，这里不按 token 计，而按用户给定字符计费口径估算：
- 本轮总调用字符数：`1770`
- 单价：`0.45 元 / 万字符`

按这个口径：
- 总成本 = `1770 / 10000 * 0.45` ≈ **0.07965 元**
- 总 case 数 = `184`
- 单条平均成本 = `0.07965 / 184` ≈ **0.00043288 元 / 条**

也就是：
- 平均每条翻译成本约 **0.00043 元**
- 换算成人民币，约等于 **0.043 分 / 条** 量级

### 7.2 长文本 / 短文本口径
为了补“长文本翻译”和“短文本翻译”的平均成本，这里按本轮输入文本长度分桶：
- 短文本：输入长度 `<= 12` 字符
- 中文本：输入长度 `13-19` 字符
- 长文本：输入长度 `>= 20` 字符

本轮 184 条 case 的输入长度统计：
- 平均输入长度：`23.69` 字符 / 条
- 短文本：65 条，平均 `8.51` 字符 / 条
- 中文本：28 条，平均 `15.61` 字符 / 条
- 长文本：91 条，平均 `37.02` 字符 / 条

在“1770 总字符按整轮样本均摊，并按输入长度比例折算”的近似口径下：

| 类型 | case 数 | 平均输入长度 | 估算平均计费字符 | 估算平均成本 |
|---|---:|---:|---:|---:|
| 短文本 | 65 | 8.51 | 3.45 | 0.00015546 元/条 |
| 中文本 | 28 | 15.61 | 6.34 | 0.00028518 元/条 |
| 长文本 | 91 | 37.02 | 15.03 | 0.00067649 元/条 |

可以把这组数字直接理解为：
- **短文本翻译平均成本** ≈ **0.00016 元 / 条**
- **长文本翻译平均成本** ≈ **0.00068 元 / 条**

### 7.3 长短文本示例
短文本极短样例：
- `票价是多少？`
- 输入长度：6 字符

长文本样例：
- `Bisakah kamu mengganti pemberhentian berikutnya dengan yang lebih mudah?`
- 输入长度：72 字符

说明：
- 这份估算是按照“整轮已知总字符数 1770”反推的平均成本，不是 provider 返回的逐条官方账单。
- 如果后续需要更精确的单条成本，最好在 provider 层单独补入 request/response 字符数统计字段。

## 8. 对产品落地的意义
如果后续目标是：
- 把 translator 放到 routing 前置链路
- 支撑东南亚小语种的 query preprocessing
- 同时保留面向用户的 direct translation / bilingual display

那么当前已经收口的正式选择是：
1. **默认翻译器：XFYun ITS**
2. **HY-MT 仅保留为历史 benchmark 对照，不再作为后续正式 translator 方案**

原因很直接：
- XFYun 在质量上领先
- XFYun 在时延上大幅领先
- 当前按字符估算的单条成本非常低，足以支撑高频短句翻译场景

## 9. 下一步建议
建议下一轮继续做三件事：
1. 补人工 spot check
   - 重点看 2 条残余 degraded case：`product-009`、`product-025`
   - 重点看 bilingual display 的自然度
2. 把字符统计正式下沉到结果 schema
   - 为 XFYun 单独补 `input_chars` / `output_chars` / `billed_chars`
   - 避免之后还要靠整轮均摊反推
3. 把 translation benchmark 结果接到下一轮 routing / QA 设计里
   - 优先验证 translate-then-route 的真实收益
   - 尤其关注 `trip_assistant`、`manual_route_edit_redirect`、mixed query 边界
