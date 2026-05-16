# Yoyo 测试轮次记录

这份文档用于持续记录每一轮测试做了什么、结果如何、有哪些结论可以复用。

## Round 1：P0 自动化回归（pytest）

### 目标
确认当前主流程相关的核心自动化测试是否稳定。

### 范围
- `tests/test_guide_job_runtime.py`
- `tests/test_rag_admin.py`
- `tests/test_session_lifecycle.py`
- `tests/test_qa.py`
- `tests/test_planner_edits.py`

### 首次结果
- 通过：40
- 失败：4

### 首次失败点
1. guide job 音频状态断言过旧：当前实现允许 `pending`
2. QA translation degraded 文案断言过死
3. QA live_info degraded 文案断言过死
4. QA attraction_explain / session-aware route 文案断言过死

### 后续处理
- 调整测试，使其对齐当前实现语义
- 重点验证 metadata 和行为，而不是写死 provider 文案

### 最终结果
- **55 passed**（合并回归后包含后续边界集）

---

## Round 1A：第二阶段第一轮功能测试（Guest quick entry 与 questionnaire）

### 目标
验证第二阶段第一轮功能测试的起始功能组是否仍保持稳定：
- guest quick entry
- questionnaire flow
- questionnaire submission

### 范围
- `tests/test_onboarding_flow.py`
- `tests/test_api_flow.py -k "guest or questionnaire"`

### 结果
- `tests/test_onboarding_flow.py` -> **2 passed**
- `tests/test_api_flow.py -k "guest or questionnaire"` -> **1 passed, 2 deselected**
- 合计：**3 passed**

### 结论
- 第一组功能的自动化回归通过
- guest session、questionnaire flow、questionnaire submission 当前无回归
- 可以继续进入第二组功能测试：Planning 与 itinerary creation

---

## Round 1B：第二阶段第一轮功能测试（Planning 与 itinerary creation）

### 目标
验证第二组功能在当前第二阶段环境下是否仍保持稳定：
- planning entry modes
- itinerary creation
- itinerary version readback

### 范围
- `tests/test_planning_entry_modes.py`
- `tests/test_api_flow.py -k "itinerary or planning"`

### 结果
- `tests/test_planning_entry_modes.py` -> **5 passed**
- `tests/test_api_flow.py -k "itinerary or planning"` -> **1 passed, 2 deselected**
- 合计：**6 passed**

### 结论
- 第二组功能的自动化回归通过
- template / manual_poi / ai_recommendation_selected 三种入口当前无回归
- itinerary create 与 version readback 行为稳定
- 可以继续进入第三组功能测试：Session lifecycle

---

## Round 1C：第二阶段第一轮功能测试（Session lifecycle）

### 目标
验证第三组功能在当前第二阶段环境下是否仍保持稳定：
- session create / start / finish
- session current 结构稳定性
- 基本状态流转

### 范围
- `tests/test_session_lifecycle.py`
- `tests/test_api_flow.py -k "session"`（用于检查现有 API flow 是否有可复用命中）

### 结果
- `tests/test_session_lifecycle.py` -> **1 passed**
- `tests/test_api_flow.py -k "session"` -> **0 selected / 3 deselected**

### 结论
- Session lifecycle 专项自动化测试通过
- 现有 `test_api_flow.py` 中没有直接命中 `session` 关键字的可复用 case，因此这次不把第二个命令视为失败，而是视为“无匹配用例”
- 下一步应使用更精确的 session/runtime 相关测试文件继续覆盖当前组与下一组联动能力

---

## Round 1D：第二阶段第一轮功能测试（GPS、playback 与 cognitive map）

### 目标
验证第四组运行时联动功能在当前第二阶段环境下是否仍保持稳定：
- GPS arrival 语义
- playback 状态推进
- map payload 与运行时状态一致性

### 范围
- `tests/test_map_gps.py`
- `tests/test_guide_playback.py`

### 结果
- `tests/test_map_gps.py` -> **1 passed**
- `tests/test_guide_playback.py` -> **2 passed**
- 合计：**3 passed**

### 结论
- GPS、playback 与 map 相关自动化回归通过
- 到站不自动推进、playback 推进、运行时状态联动当前无回归
- 可以继续进入第五组功能测试：Manual route edit

---

## Round 1E：第二阶段第一轮功能测试（Manual route edit）

### 目标
验证第五组高风险功能在当前第二阶段环境下是否仍保持稳定：
- manual route edit
- completed prefix 冻结
- version switch 后的 session/map/runtime 一致性

### 范围
- `tests/test_planner_edits.py`
- `tests/test_a_validation_suite.py`

### 结果
- `tests/test_planner_edits.py` -> **12 passed**
- `tests/test_a_validation_suite.py` -> **13 passed**
- 合计：**25 passed**

### 结论
- Manual route edit 的主要自动化回归通过
- completed prefix、editable suffix、request validation、version switch 一致性当前无回归
- 这是当前第一轮功能测试中通过数量最多的一组，也是高风险能力中的积极信号
- 可以继续进入第六组功能测试：Guide jobs、guide assets、cycle content 与 TTS

---

## Round 1F：第二阶段第一轮功能测试（Guide jobs、guide assets、cycle content 与 TTS）

### 目标
验证第六组内容生成相关功能在当前第二阶段环境下是否仍保持稳定：
- guide job runtime
- latest ready asset 选择
- cycle content 语义
- 基础 TTS / runtime fallback 相关回归

### 范围
- `tests/test_guide_job_runtime.py`
- `tests/test_guide_asset_latest.py`
- `tests/test_guide_content_cycle.py`

### 结果
- `tests/test_guide_job_runtime.py` -> **6 passed**
- `tests/test_guide_asset_latest.py` + `tests/test_guide_content_cycle.py` -> **7 passed**
- 合计：**13 passed**

### 结论
- Guide 相关核心自动化回归通过
- guide job runtime、latest asset 选择、cycle content 行为当前无回归
- 这一组仍然属于“自动化覆盖较强，但真实环境验证仍需继续加固”的功能区
- 可以继续进入第七组功能测试：QA ask

---

## Round 1G：第二阶段第一轮功能测试（QA ask）

### 目标
验证第七组 QA 能力在当前第二阶段环境下是否仍保持稳定：
- QA 主 API 行为
- routing regressions
- routing benchmark 基础回归

### 范围
- `tests/test_qa.py`
- `tests/test_qa_routing_regressions.py`
- `tests/test_routing_benchmark.py`

### 结果
- `tests/test_qa.py` -> **26 passed**
- `tests/test_qa_routing_regressions.py` + `tests/test_routing_benchmark.py` -> **25 passed**
- 合计：**51 passed**

### 结论
- QA ask 相关自动化回归通过
- 当前主 API、routing regressions 和 routing benchmark 基础回归均无自动化回归失败
- 但这仍不等于 QA 质量问题已经解决；translation、最弱 intent、degraded 与真实 E2E 表现仍需后续专项验证
- 可以继续进入第八组功能测试：RAG admin 与 retrieval

---

## Round 1H：第二阶段第一轮功能测试（RAG admin 与 retrieval）

### 目标
验证第八组 retrieval 相关能力在当前第二阶段环境下是否仍保持稳定：
- RAG admin latest / rebuild 语义
- retrieval query 行为
- backend readiness 与 indexing 回归

### 范围
- `tests/test_rag_admin.py`
- `tests/test_rag_query.py`
- `tests/test_rag_backend.py`
- `tests/test_rag_indexing.py`

### 结果
- `tests/test_rag_admin.py` + `tests/test_rag_query.py` -> **5 passed**
- `tests/test_rag_backend.py` + `tests/test_rag_indexing.py` -> **6 passed**
- 合计：**11 passed**

### 结论
- RAG 相关自动化回归通过
- admin、query、backend readiness 与 indexing 当前无自动化回归失败
- 这一组仍然属于“自动化基础存在，但真实环境 configured / disabled 双语义仍需继续验证”的功能区
- 可以继续进入第九组功能测试：Comments 与 share-card

---

## Round 1I：第二阶段第一轮功能测试（Comments 与 share-card）

### 目标
验证第九组轻社交与分享能力在当前第二阶段环境下是否仍保持稳定：
- comments create/list
- finished / unfinished share-card 行为
- 基本聚合一致性

### 范围
- `tests/test_comments.py`
- `tests/test_share_card.py`
- `tests/test_map_gps.py -k "comment or share or card"`（用于检查现有 map 侧是否有可复用命中）

### 结果
- `tests/test_comments.py` + `tests/test_share_card.py` -> **6 passed**
- `tests/test_map_gps.py -k "comment or share or card"` -> **0 selected / 1 deselected**

### 结论
- Comments 与 share-card 主要自动化回归通过
- 现有 `test_map_gps.py` 中没有直接命中 comment/share/card 关键字的可复用 case，因此第二个命令视为“无匹配用例”
- 这一组当前自动化层面稳定，可以继续进入第十组功能测试：Degraded 与外部依赖行为

---

## Round 1J：第二阶段第一轮功能测试（Degraded 与外部依赖行为）

### 目标
验证第十组 provider / config / fallback 相关能力在当前第二阶段环境下是否仍保持稳定：
- live search / provider 语义
- runtime provider 基础可用性
- degraded / unavailable / fallback 路径

### 范围
- `tests/test_live_search.py`
- `tests/test_runtime_openrouter.py`
- `tests/test_rag_backend.py`
- `tests/test_guide_job_runtime.py`
- `tests/test_qa.py -k "degrad or unavailable or missing or provider or fallback"`

### 结果
- `tests/test_live_search.py` + `tests/test_runtime_openrouter.py` -> **4 passed**
- `tests/test_rag_backend.py` + `tests/test_guide_job_runtime.py` + `tests/test_qa.py -k "degrad or unavailable or missing or provider or fallback"` -> **10 passed, 26 deselected**
- 合计：**14 passed**

### 结论
- degraded 与外部依赖相关自动化回归通过
- provider 缺失、fallback、unavailable 路径当前无自动化回归失败
- 这一组后续仍建议补真实环境 fault-injection 验证，但自动化层面已稳定

---

## Round 1 Summary：第二阶段第一轮功能测试（自动化）

### 执行范围
本轮已完成前十组功能的自动化测试执行：
1. Guest quick entry 与 questionnaire
2. Planning 与 itinerary creation
3. Session lifecycle
4. GPS、playback 与 cognitive map
5. Manual route edit
6. Guide jobs、guide assets、cycle content 与 TTS
7. QA ask
8. RAG admin 与 retrieval
9. Comments 与 share-card
10. Degraded 与外部依赖行为

### 汇总结果
- Round 1A：**3 passed**
- Round 1B：**6 passed**
- Round 1C：**1 passed**（另有 0 selected / 3 deselected 的无匹配补充命令）
- Round 1D：**3 passed**
- Round 1E：**25 passed**
- Round 1F：**13 passed**
- Round 1G：**51 passed**
- Round 1H：**11 passed**
- Round 1I：**6 passed**（另有 0 selected / 1 deselected 的无匹配补充命令）
- Round 1J：**14 passed**

### 当前结论
- 已执行的前十组功能自动化测试全部通过
- 本轮没有出现真实测试失败；只有两次补充筛选命令未命中任何用例，这两次均已按“无匹配用例”记录，不视为失败
- 当前最稳定的区域包括：
  - onboarding
  - planning
  - session / GPS / playback / map
  - manual route edit
  - comments / share-card
- 当前自动化通过但后续仍需真实环境继续加固的区域包括：
  - Guide / TTS
  - QA
  - RAG
  - degraded / provider fault behavior

### 下一步建议
- 若继续本轮测试，应进入第十一组：Benchmark 与 E2E QA validation
- 若按“先看已完成结果再决定”推进，可以先基于这一轮自动化结果做一次人工审阅，再决定是否立即进入真实 E2E / benchmark

---

## Round 2A：第二阶段第二轮真实环境测试（健康检查与 RAG admin）

### 目标
验证真实服务栈下基础服务与 RAG admin 真链路是否可用。

### 前置环境
- Docker / PostgreSQL / Redis 已启动
- alembic migration 已执行
- seed 已执行
- API 已启动
- worker 已启动

### 结果
- `GET /api/v1/health` -> **通过**
- `GET /api/v1/rag/index-runs/latest` -> **通过**，返回 `availability = ready`
- `POST /api/v1/rag/index-runs/rebuild` -> **通过**，返回 `status = succeeded`

### 关键结论
- 第二轮真实环境测试已成功进入可执行状态
- RAG admin 真链路可用
- `latest` 和 `rebuild` 都能在真实环境返回稳定结构
- 观察到数据库 collation version mismatch 警告，但当前未阻塞服务与测试执行

---

## Round 2B：第二阶段第二轮真实环境测试（session / map / QA 真链路）

### 目标
验证真实 itinerary -> session -> start -> current -> map -> QA 链路是否跑通。

### 结果
- itinerary create -> **通过**
- session create -> **通过**
- session start -> **通过**
- `GET /api/v1/session/{id}/current` -> **通过**
- `GET /api/v1/map/session/{id}` -> **通过**
- 深问 QA -> **通过**
- 越界 QA -> **通过**

### 关键字段结果
- `current.status = active`
- `playback_state = not_triggered`
- `map` 可返回 markers，当前 stop 与 session current 一致
- 深问 QA：
  - `intent = attraction_explain`
  - `retrieval_strategy = sql_then_rag`
  - `rag_backend_ready = true`
  - `rag_query_status = ok`
- 越界 QA：
  - `intent = out_of_scope`
  - `supported = false`

### 关键结论
- session / map / QA 真链路已经跑通
- 在真实链路验证过程中发现并修正了两个请求契约问题：
  - session create 需要 `itinerary_version_id`
  - QA ask 请求字段应为 `query`，不是 `question`
- 这两个问题来自手工验证请求构造，不是后端功能失败；修正后真实链路通过

---

## Round 2C：第二阶段第二轮真实环境测试（guide content 与 share-card）

### 目标
验证真实 guide asset / content / finish / share-card 链路是否跑通。

### 当前结果
- `GET /api/v1/guide/asset/{guide_session_id}` -> **通过**
- `POST /api/v1/guide/content/{guide_session_id}` -> **404 guide content not available**
- `POST /api/v1/session/guide/{guide_session_id}/finish` -> **通过**
- `GET /api/v1/share-card/session/{guide_session_id}` -> **通过**

### 当前观察
- worker 日志显示 guide generation job 实际有执行完成
- 但在当前真实链路下，`guide/asset` 返回 `asset_status = missing`，随后 `guide/content` 返回 `404`
- `share-card` 在 session finish 后仍能成功返回：
  - `is_shareable = true`
  - `status = finished`
  - `subheadline = Trip complete — ready to share`

### 当前结论
- Guide / share-card 真链路不是完全通过状态
- 当前已定位到一个真实环境问题：guide generation job 已运行，但 session 对应的 `guide/content` 仍不可用
- 这属于第二轮真实环境测试发现的**有效问题**，应继续排查 asset 缺失与 content 不可用的原因

---

## Round 2：P0 边界回归（pytest）

### 目标
确认 guide asset / content / share-card 这些边界状态是否稳定。

### 范围
- `tests/test_guide_asset_latest.py`
- `tests/test_guide_content_cycle.py`
- `tests/test_share_card.py`

### 结果
- **11 passed**

### 关键结论
- guide asset 选择语义稳定
- finished session 下 guide content / asset 边界符合预期
- share-card finished 一致性通过

---

## Round 3：真实 API 冒烟（正常环境）

### 目标
验证真实服务栈下主链路是否可跑通，而不是只依赖 pytest。

### 环境
- Docker / PostgreSQL / Redis 已启动
- migration 已执行
- seed 已执行
- API 服务已可用
- worker 已启动：`.venv/bin/arq yoyo.jobs.worker.WorkerSettings`

### 覆盖链路
- `GET /api/v1/health`
- `GET /api/v1/rag/index-runs/latest`
- `POST /api/v1/rag/index-runs/rebuild`
- `POST /api/v1/planning/itineraries`
- `POST /api/v1/session/guide`
- `POST /api/v1/session/guide/{id}/start`
- `GET /api/v1/session/{id}/current`
- `GET /api/v1/map/session/{id}`
- `POST /api/v1/guide/jobs`
- `GET /api/v1/guide/jobs/{id}`
- `GET /api/v1/guide/asset/{id}`
- `POST /api/v1/guide/content/{id}`
- `POST /api/v1/qa/ask`
- `GET /api/v1/share-card/session/{id}`
- `POST /api/v1/session/guide/{id}/finish`

### 结果
- **通过**

### 关键结论
- 核心 demo 主链路已真实跑通
- guide job -> worker -> asset -> content 真链路可用
- guide asset 总音频状态当前会先显示 `pending`
- `cycle_content` 已可返回当前批次 `audio_segments = ready`
- share-card 在 finish 前后状态正确切换

### 关键注意事项
- 只启动 API 不够，guide job 会停在 `queued`
- 要验证 guide 真链路，必须同时启动 worker

---

## Round 4：真实降级冒烟（RAG / TTS）

### 目标
验证关键依赖关闭时，系统是否受控降级。

### 场景 A：`RAG_ENABLED=false`
#### 结果
- `POST /api/v1/rag/index-runs/rebuild` -> `status = skipped`
- `reason = rag_disabled`
- QA 仍可给出 SQL-grounded 正常回答
- metadata:
  - `rag_backend_ready = false`
  - `rag_query_status = skipped`

### 场景 B：`TTS_API_KEY=''`
#### 结果
- `guide/content` 仍返回文本
- `audio_segments[*].status = unavailable`

### 关键结论
- RAG disabled 不等于 QA 必然整体 degraded
- TTS 缺 key 时 guide 主流程仍可继续

### 关键注意事项
- API 和 worker 必须共用同一套降级环境变量，否则 asset-level 音频状态可能混入 worker 配置

---

## Round 5：真实降级冒烟（live_info provider 缺失）

### 目标
验证 Tavily 缺失时，live_info 是否受控降级。

### 环境
- `TAVILY_API_KEY=''`

### 结果
- `intent = live_info`
- `status = unavailable`
- `reason = missing_provider_config`
- `degraded = true`
- `degraded_reason = missing_provider_config`
- `confidence = low`
- `sources[0].name = tavily_missing_key`

### 用户侧表现
- answer 不脏、不 500
- 会明确引导用户去官网或可靠渠道确认当日信息

---

## Round 6：QA benchmark（Gemini 2.5 Flash Lite）

### 目标
评估当前 `google/gemini-2.5-flash-lite` 是否能胜任 QA 主模型。

### 实际运行路径
- provider：`openrouter`
- model：`google/gemini-2.5-flash-lite`

### Benchmark 结构
- 总题数：180
- 6 个板块 × 每板块 30 题
  1. `attraction_explain`
  2. `live_info`
  3. `trip_assistant`
  4. `manual_route_edit_redirect`
  5. `translation`
  6. `out_of_scope`

### 判定口径
- 单题完成：`score >= 4`
- 板块胜任：`avg_score >= 4.0` 且完成率 `>= 80%`
- 总体胜任：总完成率 `>= 80%`，且至少 5 个板块达标

### Smoke 30 题结果
- 总完成率：`50.0%`

### 全量 180 题结果
- `avg_score = 2.89 / 5`
- 总完成率：`37.22%`
- 结论：**当前不胜任 QA 全板块主模型**

### 分板块结果
- `attraction_explain`：avg `3.90`，completion `76.67%`
- `live_info`：avg `3.47`，completion `60.00%`
- `trip_assistant`：avg `3.03`，completion `46.67%`
- `translation`：avg `2.93`，completion `40.00%`
- `manual_route_edit_redirect`：avg `2.00`，completion `0.00%`
- `out_of_scope`：avg `2.00`，completion `0.00%`

### 结论
- 它不适合作为当前 QA 的全板块主模型
- 但 `attraction_explain` 仍有一定可用性，可能适合作为低成本候选或子任务模型

### 结果文件
- `evals/results/qa_benchmark_gemini_flash_lite_smoke_30_results.json`
- `evals/results/qa_benchmark_gemini_flash_lite_smoke_30_scores.json`
- `evals/results/qa_benchmark_gemini_flash_lite_smoke_30_summary.json`
- `evals/results/qa_benchmark_gemini_flash_lite_180_results.json`
- `evals/results/qa_benchmark_gemini_flash_lite_180_scores.json`
- `evals/results/qa_benchmark_gemini_flash_lite_180_summary.json`

---

## Round 7：QA benchmark（OpenAI GPT-5.4-nano）

### 目标
用同一套 180 题 QA benchmark 对比 `openai/gpt-5.4-nano` 的可胜任性。

### 实际运行路径
- provider：`openrouter`
- model：`openai/gpt-5.4-nano`

### 全量 180 题结果
- `avg_score = 3.13 / 5`
- 总完成率：`43.89%`
- 结论：**仍不胜任 QA 全板块主模型**

### 分板块结果
- `attraction_explain`：avg `3.93`，completion `73.33%`
- `live_info`：avg `3.17`，completion `46.67%`
- `trip_assistant`：avg `3.57`，completion `66.67%`
- `translation`：avg `4.13`，completion `76.67%`
- `manual_route_edit_redirect`：avg `2.00`，completion `0.00%`
- `out_of_scope`：avg `2.00`，completion `0.00%`

### 延时与花费
- `avg_latency_ms = 3156.32`
- `estimated_total_cost = 0.06017435`
- `avg_prompt_tokens = 20.29`
- `avg_completion_tokens = 264.19`
- `avg_total_tokens = 284.49`

### 结果文件
- `evals/results/qa_benchmark_gpt_5_4_nano_180_results.json`
- `evals/results/qa_benchmark_gpt_5_4_nano_180_scores.json`
- `evals/results/qa_benchmark_gpt_5_4_nano_180_summary.json`

---

## Round 8：QA benchmark（Gemini 2.5 Flash）

### 目标
用同一套 180 题 QA benchmark 对比 `google/gemini-2.5-flash` 的可胜任性。

### 实际运行路径
- provider：`openrouter`
- model：`google/gemini-2.5-flash`

### 全量 180 题结果
- `avg_score = 2.80 / 5`
- 总完成率：`34.44%`
- 结论：**不胜任 QA 全板块主模型**

### 分板块结果
- `attraction_explain`：avg `3.47`，completion `60.00%`
- `live_info`：avg `3.03`，completion `50.00%`
- `trip_assistant`：avg `3.03`，completion `46.67%`
- `translation`：avg `3.27`，completion `50.00%`
- `manual_route_edit_redirect`：avg `2.00`，completion `0.00%`
- `out_of_scope`：avg `2.00`，completion `0.00%`

### 延时与花费
- `avg_latency_ms = 3891.62`
- `estimated_total_cost = 0.191468`
- `avg_prompt_tokens = 13.94`
- `avg_completion_tokens = 423.81`
- `avg_total_tokens = 437.76`

### 结果文件
- `evals/results/qa_benchmark_gemini_2_5_flash_180_results.json`
- `evals/results/qa_benchmark_gemini_2_5_flash_180_scores.json`
- `evals/results/qa_benchmark_gemini_2_5_flash_180_summary.json`

---

## Round 10：E2E QA benchmark rerun（23-case / three-model rerun after routing work）

### 目标
在当前 QA 路由与 selective router fallback 接入后，重新跑现有 `evals/datasets/e2e_qa_benchmark_cases.json` 这套 23 条 E2E QA case，对比之前同样的三个运行时模型：
- `openai/gpt-5.4-nano`
- `google/gemini-2.5-flash`
- `google/gemini-2.5-flash-lite`

### 数据集与结果文件
- dataset：`evals/datasets/e2e_qa_benchmark_cases.json`（23 cases）
- GPT rerun summary：`evals/results/e2e_qa_benchmark_gpt54nano_rerun_20260422_summary.json`
- Gemini Flash rerun summary：`evals/results/e2e_qa_benchmark_gemini25flash_rerun_20260422_summary.json`
- Gemini Flash Lite rerun summary：`evals/results/e2e_qa_benchmark_gemini25flashlite_rerun_20260422_summary.json`
- rerun workbook：`evals/results/e2e_qa_benchmark_run_rerun_20260422.xlsx`

### 模型汇总表

| 模型 | case_count | avg_score | pass_count | pass_rate |
| --- | ---: | ---: | ---: | ---: |
| `openai/gpt-5.4-nano` | 23 | 4.087 | 16 | 69.6% |
| `google/gemini-2.5-flash` | 23 | 4.174 | 18 | 78.3% |
| `google/gemini-2.5-flash-lite` | 23 | 4.130 | 17 | 73.9% |

### 分板块结果

| category | gpt-5.4-nano | gemini-2.5-flash | gemini-2.5-flash-lite |
| --- | --- | --- | --- |
| `attraction_explain` | 4.50 / 100% | 4.17 / 83.3% | 4.33 / 83.3% |
| `deep_attraction_ask_sql_then_rag` | 3.00 / 0% | 3.67 / 66.7% | 3.67 / 66.7% |
| `live_info` | 5.00 / 100% | 5.00 / 100% | 5.00 / 100% |
| `live_info_boundary` | 4.50 / 100% | 4.50 / 100% | 4.50 / 100% |
| `live_info_provider_missing` | 3.00 / 0% | 4.00 / 100% | 3.00 / 0% |
| `manual_route_edit_redirect` | 2.00 / 0% | 3.00 / 0% | 2.00 / 0% |
| `out_of_scope` | 4.00 / 50% | 4.00 / 50% | 4.00 / 50% |
| `session_mutation_follow_through` | 5.00 / 100% | 5.00 / 100% | 5.00 / 100% |
| `translation` | 5.00 / 100% | 5.00 / 100% | 5.00 / 100% |
| `trip_assistant` | 4.00 / 75% | 4.00 / 75% | 4.00 / 75% |

### 主要失败点
- 三个模型这轮共同仍不稳定的点：
  - `E2E-BOUNDARY-001`（manual route edit redirect 边界）
  - `E2E-OOS-002`（out_of_scope 边界）
- `deep_attraction_ask_sql_then_rag` 仍是 GPT-5.4-nano 的明显弱项；Gemini Flash / Flash Lite 在这组三题上更稳。
- `live_info_provider_missing` 这轮只有 Gemini Flash 通过，GPT-5.4-nano 与 Gemini Flash Lite 仍有 degraded/provider-missing 表达不稳的问题。
- `trip_assistant` 相关个别 case 仍会漂向 `live_info`。

### 当前结论
1. 这轮 23-case rerun 里，**`google/gemini-2.5-flash` 暂时是最佳 overall**（avg_score 与 pass_rate 都最高）。
2. **`openai/gpt-5.4-nano` 的 attraction_explain 仍强**，但在 `sql_then_rag` 深问链路上落后于两条 Gemini 线。
3. **`google/gemini-2.5-flash-lite` 仍是可接受但稍弱的低成本候选**。
4. 三模型共同暴露的主要系统边界仍是：
   - manual route edit redirect case 设计/判分口径
   - out_of_scope 边界 case
   - provider-missing degraded wording consistency

## 当前整体判断

### 已经完成的验证
- 自动化回归
- 真实主链路冒烟
- 真实降级冒烟
- live_info provider 缺失验证
- Gemini 2.5 Flash Lite QA benchmark

### 当前可复用结论
1. demo 主链路当前可提测
2. guide 真链路测试必须带 worker
3. 降级验证必须保证 API / worker 环境一致
4. `gemini-2.5-flash-lite` 当前不适合作为 QA 全板块主模型

---

## Round 2D：第二阶段第二轮真实环境复核（guide asset / content 真链路）

### 目标
复核 Round 2C 中出现的 `guide/asset = missing` 与 `guide/content = 404` 是否仍可稳定复现，并收口真实根因。

### 复核方式
在当前本地真实环境中重新执行：
- `POST /api/v1/planning/itineraries`
- `POST /api/v1/session/guide`
- `POST /api/v1/session/guide/{id}/start`
- 轮询 `GET /api/v1/guide/asset/{id}`
- `POST /api/v1/guide/content/{id}`
- `POST /api/v1/session/guide/{id}/finish`
- `GET /api/v1/share-card/session/{id}`

### 结果
- itinerary create -> **通过**
- session create -> **通过**
- session start -> **通过**
- `guide/asset` 前 4 次轮询在旧语义下返回 `asset_status = missing`
- 第 5 次轮询返回 `asset_status = ready`
- `POST /api/v1/guide/content/{id}` -> **通过**
- `POST /api/v1/session/guide/{id}/finish` -> **通过**
- `GET /api/v1/share-card/session/{id}` -> **通过**

### 关键观察
- 当前代码中，`guide/asset` 只会读取与 `guide_session.itinerary_version_id` 相同、且满足 `SUCCEEDED + READY` 条件的最新 job。
- 旧语义下，worker 完成前，`guide/asset` 会以 **200 + `asset_status = missing`** 的形式返回，而不是报错。
- 当前代码已经把这部分状态进一步细化为：生成中返回 `asset_status = pending`，失败返回 `asset_status = failed`，无 job 才返回 `asset_status = missing`。
- `guide/content` 依赖 active asset 的 `result` 已就绪，因此如果在 asset 尚未 ready 的窗口过早调用，现在会收到 **409 `guide asset not ready`**。
- 本次复核中，等待 job 完成后再调用 content，真链路恢复正常；返回了文本 segments 与 `audio_segments = ready`。

### 当前结论
- Round 2C 发现的问题在当前仓库状态下**不是持久性后端 bug**，而是 guide job 尚未落到 `SUCCEEDED + READY` 前的短暂等待窗口。
- 当前更准确的验证口径应是：
  - 先确认 worker 在运行；
  - 再轮询 `guide/asset` 直到 `asset_status = ready`；
  - 然后再调用 `guide/content`。
- 当前代码还进一步把 guide 相关语义改清楚了：
  - `guide/asset`：生成中 -> `pending`，失败 -> `failed`，无 job -> `missing`，可用稳定资产 -> `ready`
  - `guide/content`：asset 未 ready -> `409 guide asset not ready`
  - `guide/content`：session 已 finished -> `409 guide session finished`
  - `guide/content`：真正 session 不存在 -> `404 guide session not found`
- 如果后续还要继续做发布前真实冒烟，应把这条等待语义写入执行清单，而不是把首次 `missing/404` 直接记为功能失败。

---

## Round 9：E2E QA benchmark（标准环境）

### 目标
验证真实 `/api/v1/qa/ask` 链路，而不是只测模型裸答能力。

### 覆盖案例
- out_of_scope
- translation
- live_info
- trip_assistant
- attraction_explain
- deep_attraction_ask_sql_then_rag
- manual_route_edit_redirect
- session_mutation_follow_through

### 结果
- 案例数：8
- `avg_score = 3.25 / 5`
- 完成率：`37.5%`

### 结论
- 真实 `/api/v1/qa/ask` E2E 结果明显不同于 model-only benchmark
- session / redirect / RAG metadata 这类系统链路能力，必须通过真实 API 才能测到
- 当前 E2E 仅是 baseline，还需要继续扩题

### 结果文件
- `evals/results/e2e_qa_benchmark_run1_cases.json`
- `evals/results/e2e_qa_benchmark.xlsx`

---

## Round 10：E2E QA benchmark（live_info 降级环境）

### 目标
验证真实 `/api/v1/qa/ask` 在 Tavily 缺失时的 live_info 降级语义。

### 结果
- 案例数：1
- `score = 5 / 5`
- 通过

### 关键观察
- `intent = live_info`
- `status = unavailable`
- `reason = missing_provider_config`
- `degraded = true`
- `degraded_reason = missing_provider_config`
- answer 明确提示当前无法提供实时信息

### 结果文件
- `evals/results/e2e_qa_benchmark_run2_cases.json`
- `evals/results/e2e_qa_benchmark.xlsx`

### 下一步建议
- 修 benchmark 对 `manual_route_edit_redirect` / `out_of_scope` 的 scorer
- 扩展 E2E case 数量，特别是 trip_assistant / deep RAG / session mutation
- 对比更强模型（如 Claude Sonnet 4.6）
- 按“发布前风险轮”继续做部署一致性 / 故障注入 / 状态切换 / 时延测试

### Case 设计最新调整
- 当前 E2E case 已改成优先服务于两类目标：
  - `chain_validity`：系统链路/metadata/降级/状态一致性
  - `seed_plausibility`：只验证回答与当前数据库/seed 字段一致
- 当前阶段默认不再把这些 case 直接用作 `real_world_authenticity` 判断

---

## Round 2E：第二阶段第二轮真实环境复核（QA 边界 / translation / session-aware）

### 目标
在真实服务栈下补做一轮面向 QA 薄弱点的验证，重点看：
- session-aware follow-up
- trip_assistant 中文口语问法
- manual_route_edit_redirect
- 天气 / 交通 / 拥挤度边界题
- translation 直译路径
- live_info 与 attraction-explain 混合问句

### 前置环境
- API 已启动：`127.0.0.1:8000`
- PostgreSQL / Redis 已启动
- worker 已启动
- 通过真实 itinerary + guide session 创建测试上下文

### 覆盖 case
- 深问：`不要只给我简介，详细讲讲天安门广场背后的历史脉络和象征意义。`
- follow-up：`那这个呢？`
- trip assistant：`下一个去哪里？`
- translation：`Please translate: 请帮我拍张照片`
- route-edit redirect：`把景山去掉，路线轻松点`
- 边界题：天气 / 交通 / 拥挤度
- live_info：`故宫今天开放吗？`
- 混合题：`故宫今天开放吗，顺便讲讲值不值得去`
- hard out-of-scope：`Write me a sorting algorithm in Python`

### 结果
- 深问 -> **通过**：`intent = attraction_explain`，`retrieval_strategy = sql_then_rag`
- follow-up -> **通过但需关注**：保持 `intent = attraction_explain`，命中 `follow_up_from_history`
- trip assistant 中文口语问法 -> **未通过预期**：`下一个去哪里？` 返回 `intent = out_of_scope`
- translation 直译 -> **通过但 metadata 不一致**：回答正确，但 `degraded = false` 时 `degraded_reason` 仍出现说明性文本
- route-edit redirect -> **通过**：`intent = manual_route_edit_redirect`
- 天气 / 交通 / 拥挤度边界题 -> **通过**：均返回 `intent = out_of_scope` + `boundary_redirect = true`
- live_info 当日开放题 -> **通过**：`intent = live_info`，返回高置信度开放信息
- live_info + attraction 混合题 -> **未通过预期**：最终 `intent = attraction_explain`，虽然答案同时覆盖开放信息与“值不值得去”，但路由没有收敛到更稳定的 live-first 语义
- hard out-of-scope -> **通过**：稳定拒答

### 关键观察
- `manual_route_edit_redirect` 在真实环境里的语义比历史 benchmark 结论更稳定，当前更大的真实风险已转向中文口语 `trip_assistant`。
- `weather / traffic / crowd` 三类边界题当前真实行为稳定，`out_of_scope` + `boundary_redirect` 语义清晰。
- `那这个呢？` 这种 follow-up 已能靠历史保持 `attraction_explain`，但本次返回里 `retrieval_strategy = sql_only`、`rag_backend_ready = false`，说明多轮深问的 retrieval 连续性还不稳。
- translation 直译主路径可用，但成功路径里的 `degraded_reason` 元数据仍有一致性问题，属于 translation readiness / observability 待修项。
- `故宫今天开放吗，顺便讲讲值不值得去` 这类 mixed query 仍暴露 live_info 与 attraction-explain 边界未完全收口。

### 当前结论
- 本轮真实验证后，QA 当前最值得优先收口的真实问题变为：
  1. `trip_assistant` 中文口语问法
  2. live_info 与 attraction-explain 混合题
  3. session-aware follow-up 的 retrieval 连续性
  4. translation 成功路径的 metadata 一致性
- `manual_route_edit_redirect` 和 `weather / traffic / crowd` 边界题当前可从“历史弱项”下调为“已在真实环境获得稳定验证”的区域。
- 这些问题当前更像下一轮 QA routing / translation hardening 的输入，并不阻塞已存在的 demo 主链路可用性判断。

---

## Round 2F：第二阶段非 QA 发布前风险轮（状态切换 / guide 链路 / share-card / 部署一致性）

### 目标
在不继续展开 QA 的前提下，补做一轮非 QA 真实环境测试，重点覆盖：
- guide job -> worker -> asset -> content 真链路
- GPS / playback / finish / route edit 的状态切换
- share-card 的 finish 前后边界
- 部署一致性与基础时延观察

### 前置环境
- API 已启动：`127.0.0.1:8000`
- PostgreSQL / Redis 已启动
- worker 已启动
- 本轮 API 进程启动参数为：`uvicorn yoyo.app:app --host 127.0.0.1 --port 8000`
- 额外观察：当前 API 进程不是 `--reload` 模式

### 覆盖链路
1. create itinerary
2. create session
3. start session
4. share-card before finish
5. create guide job
6. poll guide job / guide asset until ready
7. `cycle_content`
8. GPS 到站 -> playback complete -> current
9. route edit（`replace_stop`）-> version switch -> current
10. finish session -> share-card after finish
11. finish 后再读 asset / 再调 content

### 结果
- itinerary / session / start -> **通过**
- share-card before finish -> **通过**：`is_shareable = false`，状态为 active
- guide job -> worker -> asset -> content -> **通过**
- GPS 到站不自动推进 -> **通过**
- playback complete 推进到下一站 -> **通过**
- route edit 后 runtime version switch -> **通过**
- share-card after finish -> **通过**：`is_shareable = true`、`status = finished`、`subheadline = Trip complete — ready to share`
- finish 后 `guide/asset` 仍可读 -> **通过**
- finish 后 `guide/content` -> **结果需谨慎解释**：当前运行中的本地 API 返回 `404 guide content not available`

### 关键时延观测
- create itinerary：约 `44.54ms`（基线）/ `6.28ms`（风险轮）
- create session：约 `2-3ms`
- start session：约 `2-4ms`
- create guide job：约 `3.83ms`
- guide job 从 queued 到 succeeded：约 `4s`
- 首次 `cycle_content`：约 `13.97ms`
- GPS update：约 `8.0ms`
- playback complete：约 `8.73ms`
- route edit `replace_stop`：约 `14.24ms`
- finish session：约 `9.53ms`
- share-card after finish：约 `10.59ms`

### 关键观察
- 初始 guide job 轮询表现符合预期：`queued -> running -> succeeded`，对应 asset 最终进入 `ready`。
- route edit 后新的 itinerary version 对应 asset 会先出现短暂 `missing` 窗口，随后恢复到 `ready`；这说明 edit 后重新生成链路在真实环境可用。
- 当前基线 finish 流与 route edit 后 finish 流里，`POST /api/v1/guide/content/{guide_session_id}` 都返回了 `404 guide content not available`，这与仓库中当前源码表达的 `409 guide session finished` 预期不一致。
- 进一步检查发现：本轮本地 API 进程启动于 `20:10`，且并非 `--reload` 模式；而 `src/yoyo/api/v1/guide.py` 与 `src/yoyo/modules/guide/asset_service.py` 在其后仍有修改时间。这意味着本轮观察到的 `404` 更应被记录为**部署一致性风险 / 运行进程与当前源码可能不一致**，而不是直接下结论为当前仓库源码语义。

### 当前结论
- 非 QA 主链路当前仍然稳定：guide/worker、playback、route edit version switch、share-card finish 边界都已真实跑通。
- 当前最值得记录的非 QA 风险不是主流程失败，而是**部署一致性**：测试时必须确认 API / worker 已经按当前源码重启，否则会得到与仓库代码不一致的运行语义。
- 因此，本轮 `finished 后 content 返回 404` 暂记为**运行环境与源码可能不一致的有效风险信号**，不直接记为当前代码 bug；后续若要继续发布前风险轮，应先重启 API / worker 到当前源码状态，再复核 finished-session content 语义。

---

## Round 2G：重启 API / worker 后的非 QA 复测

### 目标
在按当前源码重启 API 与 worker 后，复测上一轮观察到的 finished-session content 语义偏差，并顺带确认非 QA 主链路仍稳定。

### 操作
- 停止旧 API / worker 进程
- 重新以当前源码启动：
  - `uvicorn yoyo.app:app --host 127.0.0.1 --port 8000`
  - `arq yoyo.jobs.worker.WorkerSettings`
- 健康检查通过后，重跑 baseline finish 语义与主链路复测

### 结果
- baseline：finished session 后 `POST /api/v1/guide/content/{guide_session_id}` -> **409 `guide session finished`**
- 主链路复测：
  - guide job -> worker -> asset -> content -> **通过**
  - GPS 到站不自动推进 -> **通过**
  - playback complete 推进 -> **通过**
  - route edit 后 version switch -> **通过**
  - share-card finish 前后边界 -> **通过**
  - finish 后 `guide/asset` 仍可读 -> **通过**
  - finish 后 `guide/content` -> **409 `guide session finished`**

### 关键观察
- 重启后，`guide/asset` 的 job 元信息恢复完整：`queued/running/succeeded` 与 `pending/ready` 能在真实轮询中稳定观察到。
- route edit 后的 asset 语义也与当前代码一致：会先返回 `pending`，随后进入 `ready`，不再出现上一轮那种连续 `missing` 且无 job 元信息的现象。
- 这说明上一轮的 `404 guide content not available` 与 `asset_status = missing` 更应归因于**运行进程未对齐当前源码**，而不是当前仓库代码本身。

### 时延补记
- guide job 从 queued 到 succeeded：约 `24.2s`
- route edit 后新 asset 从 pending 到 ready：约 `7.1s`
- 首次 `cycle_content`：约 `17.18ms`
- finish 后再次请求 `guide/content`：约 `3.19ms`

### 当前结论
- 重启复测已确认：当前源码语义与文档一致，finished session 下 `guide/content` 应返回 `409 guide session finished`。
- 上一轮记录的偏差已成功收口为**部署一致性问题**，不是当前代码语义 bug。
- 当前非 QA 主链路在“按当前源码重启后的真实环境”下可视为再次通过。
