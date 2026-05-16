# E2E QA Benchmark

这份文档定义真实 `/api/v1/qa/ask` 端到端 benchmark 的执行方式。

它和 `evals/run_eval.py` 那套 model-only benchmark 不同：
- model-only benchmark：直接把 prompt 发给模型，评估裸答能力
- E2E QA benchmark：通过真实 API，经过 session context、history、live_info provider、RAG backend、SQL grounding、product redirect 等系统链路

## 1. 目标

E2E QA benchmark 用来回答两个问题：
1. 当前 QA 系统在真实环境里能不能稳定工作？
2. 某个模型在真实系统链路下是否仍然胜任？

## 2. 建议板块

建议至少覆盖以下板块：
1. out_of_scope
2. translation
3. live_info（仅景点官网/官方通知类信息）
4. trip_assistant
5. attraction_explain
6. deep_attraction_ask_sql_then_rag
7. manual_route_edit_redirect
8. session_mutation_follow_through

## 2.1 reality_level 说明

为避免把当前 seed/mock 数据误当成真实知识库，E2E case 建议显式标注三种 reality level：

- `chain_validity`
  - 测系统链路是否正确
  - 例如：session context、redirect、降级、metadata
- `seed_plausibility`
  - 只测回答是否和当前数据库字段一致
  - 不下“真实世界准确性”结论
- `real_world_authenticity`
  - 测真实世界知识是否准确
  - 当前阶段默认**不要启用**，除非已经接入独立真实内容源

## 2.2 case 字段建议

本轮 E2E case 建议至少包含以下字段：

- `case_id`
- `category`
- `title`
- `language`
- `mode`
- `operation`
- `query_zh`
- `reality_level`
- `expected_intent`
- `expected_data_source`
- `session_required`
- `profile_id`（如适用）
- `fixture_mode`
- `variant_group`（如适用）
- `data_anchor`
- `assertions`
- `request` 或 `request_template`

### 新增字段含义
- `operation`
  - 表示本题主要测试的任务类型，例如 `grounded_qa`、`retrieve`、`translate`、`multi_hop`、`redirect`、`boundary_check`
- `query_zh`
  - 题目的中文翻译，用于预览和人工复核
- `profile_id`
  - 绑定 benchmark profile，验证个性化行为时必须填写
- `fixture_mode`
  - 当前建议值：`none`、`structured_data`、`profile_only`、`profile_plus_rag`、`real`、`degraded`
- `variant_group`
  - 用于标记同一能力点下的变体题，方便对比和抽样
- `data_anchor`
  - 明确 case 依赖的景点、字段、RAG 文档类型或 profile
- `assertions`
  - 结构化判定要点，建议包含 `must_include_any`、`must_not_depend_on`、`check_metadata` 等键

## 3. 环境要求

### 标准环境
- Docker / PostgreSQL / Redis
- alembic migration 已执行
- seed 已执行
- API 服务已启动
- 如本轮还串 guide job / asset / content，则 worker 也必须启动

### 降级环境
如需验证降级，建议单独起环境：
- `RAG_ENABLED=false`
- `TAVILY_API_KEY=''`
- 必要时 `TTS_API_KEY=''`

注意：
- API 和 worker 必须共用同一套环境变量
- 否则 guide/TTS 相关结论会被污染

## 4. 执行顺序

### 4.1 基础准备
1. `docker compose up -d`
2. `.venv/bin/alembic upgrade heads`
3. `PYTHONPATH=src .venv/bin/python src/yoyo/scripts/seed_mock_knowledge.py`
4. `.venv/bin/uvicorn yoyo.app:app --host 127.0.0.1 --port 8000`
5. 如需 guide 链路，再起 worker：`.venv/bin/arq yoyo.jobs.worker.WorkerSettings`

### 4.2 RAG 预热（如需要）
1. `GET /api/v1/rag/index-runs/latest`
2. `POST /api/v1/rag/index-runs/rebuild`
3. 再次 `GET /api/v1/rag/index-runs/latest`

### 4.3 真实 session 前置
需要 session-aware QA 时，固定先做：
1. `POST /api/v1/planning/itineraries`
2. `POST /api/v1/session/guide`
3. 必要时 `POST /api/v1/session/guide/{guide_session_id}/start`

### 4.4 执行 `/api/v1/qa/ask`
按照板块逐题请求，记录：
- 请求体
- 响应体
- latency
- metadata
- 降级语义
- 是否符合预期

### 4.5 全链路多语言时延 benchmark

当前新增一轮专门用于“回答模型质量 + 端到端分段时延”的数据集：

- 数据集：`evals/datasets/e2e_qa_fullchain_multilingual_v1.json`
- 模型 sweep：`evals/datasets/e2e_fullchain_qwen_doubao_sweep.json`
- 对比模型：
  - `dashscope/qwen-turbo`
  - `volcengine/doubao-seed-2-0-mini-260428`

覆盖链路：
- `smalltalk` 短路
- hard deny / boundary `out_of_scope`
- `translation`
- `attraction_explain` SQL-first
- `attraction_explain` SQL + RAG
- `live_info`
- `weather_info`
- `navigation_text`
- session-aware `trip_assistant`
- `manual_route_edit_redirect`

`live_info` 现在带 Redis 短缓存。复测 live_info 时建议至少跑两遍同一景点同一 `info_type` 的 query：
- 第一遍应看到 `live_info_cache_hit=false`
- 第二遍应看到 `live_info_cache_hit=true`
- `live_info_lookup_ms` 应从外部搜索级别下降到 Redis 命中级别

覆盖语言：
- 中文：`zh`
- 英文：`en`
- 东南亚语种：`th`、`vi`、`id`、`ms`、`fil`、`my`、`km`、`lo`

推荐执行命令：

```bash
PYTHONPATH=src .venv/bin/python evals/run_e2e_qa_benchmark.py \
  --dataset evals/datasets/e2e_qa_fullchain_multilingual_v1.json \
  --base-url http://127.0.0.1:8000 \
  --run-id e2e-fullchain-20260515 \
  --sweep evals/datasets/e2e_fullchain_qwen_doubao_sweep.json \
  --output-dir evals/results/e2e_qa_fullchain_multilingual_20260515
```

输出会包含：
- `<model>_cases.json`
- `<model>_summary.json`
- `e2e_model_sweep_results.xlsx`

Excel 中用于人工检查的主 sheet 是 `review_cases`。它把人最需要看的列放在前面：
- 原始 query / 中文释义
- 最终 answer
- 总时延
- 预处理、路由、SQL、RAG、实时信息、天气、导航、生成、翻译、回译各环节的结果与耗时

case 明细现在会平铺记录以下分段耗时：
- `preprocess_ms`
- `routing_ms`
- `context_build_ms`
- `generation_ms`
- `postprocess_ms`
- `reported_total_ms`

同时会记录 context build 子阶段：
- `attraction_lookup_ms`
- `profile_lookup_ms`
- `live_info_lookup_ms`
- `weather_target_resolution_ms`
- `weather_lookup_ms`
- `navigation_slot_resolution_ms`
- `navigation_lookup_ms`
- `rag_lookup_ms`
- `prompt_projection_ms`

Excel 现在额外包含按语言、功能类别、expected intent、operation 聚合的时延 sheet：
- `latency_by_language`
- `latency_by_category`
- `latency_by_intent`
- `latency_by_operation`

## 5. 判定建议

### 单题
- HTTP 200 / 非 500
- `intent` 正确
- 关键 metadata 正确
- answer 行为符合当前产品预期
- 若 `reality_level = seed_plausibility`，只判断是否与当前数据库字段一致，不判断真实世界准确性
- 若 `reality_level = chain_validity`，优先判断链路、metadata、降级和状态一致性
- `live_info` 当前只面向景点官网/官方通知类信息，不用于天气、交通、拥挤度

### 系统层
- 不因为外部 provider 问题整体崩溃
- session-aware 题会读取真实 current/next stop
- RAG on/off 会改变 metadata，而不是随机漂移
- manual route edit 题会 redirect，而不是执行 planner handoff

## 6. 记录方式

### 文档
- `docs/test-rounds-log.md`：记录每轮结论
- 飞书新文档：记录协作版结果

### 数据与结果目录
- `evals/datasets/e2e_qa_benchmark_cases.json`：E2E case 主数据集
- `evals/datasets/benchmark_profiles_v1.json`：benchmark profile fixtures
- `evals/datasets/real_rag_corpus_v1_zh.json`：RAG 参考语料 fixture（当前 runtime 尚未直接用它建索引，不应直接当作上线 retrieval truth）
- `evals/datasets/beijing_attractions_structured_v1.json`：结构化景点主数据
- `evals/results/benchmark_results.xlsx`：model-only benchmark 汇总表
- `evals/results/test_rounds.xlsx`：轮次级索引
- `evals/results/e2e_qa_benchmark.xlsx`：E2E QA benchmark run/case 台账

## 7. E2E Excel 建议字段

### runs
- run_id
- round_id
- round_name
- benchmark_type
- dataset_name
- dataset_version
- total_cases
- environment_name
- base_url
- api_revision
- worker_revision
- rag_enabled
- tts_enabled
- live_info_enabled
- provider
- model
- start_time
- end_time
- avg_latency_ms
- p95_latency_ms
- estimated_total_cost
- avg_score
- completion_rate
- qualified_category_count
- overall_qualified
- blocking_assessment
- key_findings
- notes
- log_doc_path
- feishu_doc_url

### cases
- run_id
- case_id
- query_id
- category
- language
- title
- mode
- expected_intent
- expected_data_source
- session_required
- session_state
- provider
- model
- request_text
- response_text
- http_status
- api_status
- latency_ms
- prompt_tokens
- completion_tokens
- total_tokens
- estimated_total_cost
- score
- max_score
- decision
- confidence
- degraded
- degraded_reason
- retrieval_strategy
- rag_backend_ready
- rag_query_status
- supported
- artifact_path
- notes

## 8. 当前已知风险

1. `manual_route_edit_redirect` / `out_of_scope` 的现有 rule-score 口径还不稳
2. 不建真实 guide session 会让 session-aware QA 结论失真
3. guide/TTS 降级结论会受到 API/worker 环境不一致影响
4. live_info 对 Tavily 配置高度敏感
5. RAG 深问对 backend ready / rebuild 强依赖
6. 当前 attraction/profile/RAG 数据仍以 seed/mock 为主，因此不能直接拿 E2E 结果判断真实世界知识质量
7. 当前 RAG 文档与 SQL 数据高度同源，更适合验证 `sql_then_rag` 链路和 metadata，而不适合验证独立外部知识增益

## 9. 本轮执行建议

本轮建议先固定跑以下三个运行时模型：
1. `openai/gpt-5.4-nano`
2. `google/gemini-2.5-flash`
3. `google/gemini-2.5-flash-lite`

case 重点覆盖：
1. SQL 主数据 grounding
2. profile personalization
3. SQL -> RAG 深问链路
4. live_info 正常 / degraded / 越界
5. session-aware trip assistant / state mutation
6. out-of-scope 与 manual route edit redirect

结果表至少要有两层：
- case 明细表：`case_id`、`model`、`category`、`operation`、`query`、`query_zh`、`score/decision`
- 模型汇总表：`model`、`case_count`、`avg_score`、`pass_rate`，以及按 `category` / `operation` 的统计

暂时不要把 live_info 扩到：
- 天气
- 交通
- 拥挤度 / 人流情况

## 10. 下一阶段：routing-only benchmark

当前 E2E QA benchmark 主要看最终回答质量，但后续如果要上线“规则 + 小模型兜底”的混合路由，需要单独新增一套 routing-only benchmark。

### 10.1 为什么要单独测 routing
因为：
- 最终回答质量不等于路由质量
- 一个模型即使最后答得不错，也可能在 intent 边界上不稳定
- 多语种扩展时，routing 边界会先于生成质量暴露问题

### 10.2 建议新增的 routing 标签
- `attraction_explain`
- `trip_assistant`
- `translation`
- `live_info`
- `manual_route_edit_redirect`
- `out_of_scope`

说明：
- 天气 / 交通 / 拥挤度 当前先作为 `out_of_scope` 的边界子类纳入 routing benchmark
- 当前版本先不写多语种 routing 策略，先把中文/英文主链路的 routing-only benchmark 跑通
