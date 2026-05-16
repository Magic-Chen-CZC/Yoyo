# E2E QA Intent Hard 1800 Qwen Benchmark - 2026-05-16

本轮只跑主链路默认模型，不再跑 Doubao。当前 `.env` 默认链路为 `LLM_PROVIDER=dashscope`、`LLM_MODEL=qwen-turbo`。

## 数据集与产物

- 数据集：`evals/datasets/e2e_qa_intent_hard_1800_cases.json`
- 结果目录：`evals/results/e2e_intent_hard_1800_qwen_default_20260516/`
- 人工评审 Excel：`evals/results/e2e_intent_hard_1800_qwen_default_20260516/e2e_qwen_default_intent_hard_1800_results.xlsx`
- Excel 主要 sheet：
  - `review_cases`：人工主表，含语种、原 query、中文释义、最终 answer、各环节结果与时延
  - `cases`：机器明细，含中间 JSON、metadata、token/cost 字段
  - `summary` / `latency_by_*`：聚合结果

## 总体结果

| 指标 | 结果 |
|---|---:|
| 总 case | 1800 |
| 覆盖意图 | 9 |
| 每意图 case | 200 |
| 语言覆盖 | zh/en/th/vi/id/ms/fil/my/km/lo |
| 通过数 | 1800 |
| 通过率 | 100% |
| 平均总时延 | 1699.57 ms |
| p50 总时延 | 703.30 ms |
| p95 总时延 | 4796.13 ms |
| max 总时延 | 46518.12 ms |

## 分意图结果

| intent | 通过 | 平均(ms) | p50(ms) | p95(ms) | max(ms) | 主要耗时来源 |
|---|---:|---:|---:|---:|---:|---|
| smalltalk | 200/200 | 184.22 | 6.71 | 615.95 | 730.31 | 外语预处理 |
| out_of_scope | 200/200 | 342.16 | 7.80 | 1712.68 | 2494.14 | 外语预处理、少量 fallback |
| attraction_explain | 200/200 | 3269.54 | 3117.90 | 5348.51 | 6903.90 | qwen 生成、RAG lookup |
| live_info | 200/200 | 3637.57 | 3140.95 | 7780.05 | 10190.77 | router fallback、live lookup、qwen 生成 |
| weather_info | 200/200 | 2436.61 | 2135.96 | 4595.56 | 4975.83 | 天气查询、qwen 生成、回译 |
| navigation_text | 200/200 | 3489.31 | 1147.17 | 10019.79 | 46518.12 | 高德 navigation lookup |
| trip_assistant | 200/200 | 1286.92 | 1076.07 | 4021.25 | 6154.87 | qwen 生成、少量 fallback |
| manual_route_edit_redirect | 200/200 | 218.97 | 8.74 | 1329.51 | 1547.20 | 外语预处理 |
| translation | 200/200 | 430.80 | 306.13 | 781.72 | 1059.55 | 翻译执行 |

## 本轮修复点

1. smalltalk 能力说明类问题误路由：
   - 问题：`第一次用这个导游`、`你会怎么回答问题`、`能力边界` 等问法被 fallback 漂到 `out_of_scope` 或 `trip_assistant`。
   - 修复：补 smalltalk/capability 规则，并允许高置信 capability query 规则直达。

2. route-edit 元否定误判：
   - 问题：`不用操作行程`、`不要把它误当成改路线`、`不要删除任何景点` 被当作改路线证据。
   - 修复：把这些表达加入 route-edit negation，并对 `trip_assistant + route_edit_negation` 做 fallback 保护。

3. 外语翻译吞掉硬拒绝信号：
   - 问题：越南语包裹的 `Python 爬虫` 被翻译预处理丢失关键字，后续误进 `live_info`。
   - 修复：domain guard 使用 `effective_query + raw_query + pivot_query` 合并文本，保留 raw query 的硬拒绝信号。

4. 交易型旅游邻接误进 live_info：
   - 问题：`帮我订两张今晚演出票，最好直接付款` 被当作实时票务信息。
   - 修复：新增 `transaction_boundary`，代订、付款、下单、直接支付等归 `out_of_scope`。

## 主要性能观察

- 规则直返类 intent（smalltalk、manual_route_edit_redirect）p50 在 10ms 内，平均值主要被外语预处理拉高。
- `navigation_text` 最大长尾来自真实高德请求，最慢 case 为 46.5s，集中在多段/步行/公共交通查询。
- `live_info` 平均 live lookup 约 348ms，缓存后外部 live 查询不是最大瓶颈；更大的耗时在 routing fallback 与 qwen 生成。
- `attraction_explain` 稳定通过 SQL / SQL+RAG / model_knowledge 三类 grounding，平均生成耗时约 1.97s。

## 后续建议

- 导航链路加单段高德请求超时和 degraded 兜底上限，避免 30s+ 长尾拖垮端到端 p95/max。
- live_info 优先继续减少 router fallback 触发，尤其是模板化开放/预约问题可规则直达并复用缓存。
- attraction_explain 可评估短答案模式或模板化 SQL-only 生成，降低基础介绍类 qwen 生成耗时。
