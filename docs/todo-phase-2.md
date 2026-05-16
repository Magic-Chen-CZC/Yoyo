# Yoyo 第二阶段待办

这是当前阶段关于**文档重组、测试整理和 QA 加固**的活动待办文档。

它已经替代 `docs/todo.md`，成为新 session 默认应继续执行的待办入口。
上一阶段的 `docs/todo.md` 保留为历史归档，用来追溯 integrated first-phase build 和 hardening 过程。

## 0. 第二阶段目标
- 让文档入口清晰地指向当前活动工作集
- 把当前活动文档与历史日志、上一阶段 todo 历史分开
- 产出一份人和模型都容易阅读的功能级测试说明文档
- 为下一轮 QA 改进做准备，重点聚焦 routing accuracy、translation readiness 和 release-oriented verification

---

## 1. P0 —— 文档入口重置
- [x] 建立并启用新的第二阶段活动文档集：
  - `docs/todo-phase-2.md`
  - `docs/phase-2-summary.md`
  - `docs/feature-test-guide.md`
- [x] 更新 `AGENTS.md` / `README.md` 相关入口，让新 session 优先读取第二阶段文档
- [x] 更新 `README.md`，让主文档索引优先指向第二阶段文档
- [x] 新增 `docs/README.md` 与 QA / routing / intent-rules / navigation / testing / evals 等专题索引，先不移动原文档，降低链接破坏风险
- [x] 将 `docs/todo.md` 重新标记为上一阶段归档，而不是当前活动 todo
- [x] 将 `docs/current-session-summary.md` 重新标记为历史 session 日志，而不是当前阶段总结

---

## 2. P0 —— 次级入口文档一致性
- [x] 更新 `docs/collaboration.md`，让 minimum handoff set 指向第二阶段文档
- [x] 更新 `docs/dev-setup-for-teammates.md`，让推荐阅读顺序指向第二阶段文档
- [x] 更新 `docs/todo.zh-CN.md`，明确它是上一阶段中文参考，而不是当前活动 todo
- [x] 更新 `docs/demo-test-plan.md`，把 `docs/feature-test-guide.md` 作为功能级测试总览入口
- [x] 更新 `docs/test-readiness-checklist.md`，把 `docs/feature-test-guide.md` 作为功能级测试总览入口

---

## 3. P0 —— 功能级测试说明文档
- [x] 增加测试说明引言，解释测试文档分层：
  - contracts
  - test plan
  - readiness checklist
  - QA benchmark
  - rounds log
  - feature-level testing guide
- [x] 用统一结构记录主要产品能力：
  - 功能基本描述
  - 功能当前做法
  - 测试方法
- [x] 至少覆盖以下功能组：
  - guest quick entry 与 questionnaire
  - planning 与 itinerary creation
  - session lifecycle
  - GPS、playback 与 cognitive map
  - manual route edit
  - guide job、guide asset、cycle content 与 TTS
  - QA ask
  - RAG admin 与 retrieval
  - comments 与 share-card
  - degraded 与外部依赖行为
- [x] 为每个功能组关联主要测试文件和支持文档
- [x] 将面向用户阅读的 phase-2 文档改成中文，并仅在必要术语处保留英文

---

## 4. P1 —— QA 下一阶段准备

### 4.1 路由与翻译方案收口
- [x] 在 `docs/phase-2-summary.md` 中补一节“下一轮 QA 工作包”，明确本轮不是直接改大功能，而是先收口改进范围
- [x] 明确保持目标 routing 方向：
  - translator preprocessor
  - high-precision rule layer
  - small-model fallback classifier
  - downstream handlers
- [x] 把 translation 拆成两个独立问题记录到阶段计划里：
  - 面向用户的 translation 能力
  - routing 前置预处理的 translation readiness

### 4.2 QA routing accuracy 工作包
> 状态说明（2026-05-04）：本节后续项暂缓。用户计划先完成面向东南亚小语种的语言改动，再由用户本人单独设计并执行 QA 测试。

- [x] 盘点当前最弱 intent：
  - `manual_route_edit_redirect`
  - `out_of_scope`
  - attraction-explain 与 trip-assistant 边界
  - live_info 与边界题的区分
  - 最新真实环境结论：
    - 已相对稳定：`manual_route_edit_redirect`、天气 / 交通 / 拥挤度边界题
    - 仍偏弱：`trip_assistant` 中文口语问法（如“下一个去哪里？”）
    - 仍偏弱：live_info + attraction-explain 混合问句
    - 仍需关注：follow-up 场景下 retrieval 连续性
- [x] 为下一轮 routing benchmark 补充 case 设计清单：
  - 中文口语问法
  - 英文边界问法
  - 多轮短 follow-up
  - route-edit redirect 题
  - 天气 / 交通 / 拥挤度边界题
- [x] 明确下一轮要对比的 routing 方案：
  - rules only
  - rules + fallback classifier
  - translate-then-route
- [x] 同步 zh-hard routing rerun 的正式文档交付：
  - `docs/routing-zh-hard-benchmark-report-2026-05-08.md`
  - `evals/results/routing_zh_hard_v1_results.xlsx`
  - rerun 结果已回写 `docs/phase-2-summary.md` 与 `docs/current-session-summary.md`
- [x] 追加 pure fallback turbo 对照实验并完成文档回写：
  - `pure_fallback_qwen_turbo=0.9861`（71/72）
  - 已确认当前主要瓶颈从“fallback 模型本体”转向“规则模块与 selective fallback 触发策略”
  - 已同步 `docs/routing-zh-hard-benchmark-report-2026-05-08.md`、`docs/phase-2-summary.md`、`docs/current-session-summary.md`、`docs/dev-retrospective.md`
- [ ] 下一轮优先重设计规则模块：
  - 2026-05-10 导航 hard-case benchmark baseline 已补齐：`evals/datasets/navigation_hard_cases_v1.json` + `evals/run_navigation_benchmark.py`。
  - 2026-05-11 已继续修完首轮残余错例：`接下来怎么走` 的 `next_stop` / `trip_assistant` 边界与 `去故宫再去景山怎么走` 的 destination-only multi-leg 切分都已收口；当前导航 benchmark 最新结果为 `14/14=1.0`，`intent_correct_rate=1.0`，`slot_correct_rate=1.0`。
  - 2026-05-11 已继续收口 QA 主链路的 SQL/RAG 语义与 session-aware trip-assistant 回归：
    - benchmark 口径已对齐：`北京今天会不会下雨？ -> weather_info`、`把景山公园换掉，帮我把路线改轻松一点。 -> manual_route_edit_redirect`、交通/拥挤度保持 boundary `out_of_scope`
    - 中文景点 alias 解析已补到 attraction retrieval / orchestrator，单轮 query 可直接解析 `故宫`、`故宫博物院`、`天安门`、`景山公园`、`正阳门`
    - SQL / RAG 分工已在 retrieval metadata、generation prompt、router fallback prompt 中显式化；后续需继续维护两份白名单：`SQL 覆盖字段白名单`、`RAG 覆盖深问字段白名单`
    - 本轮 targeted 回归已通过：`tests/test_qa.py tests/test_qa_routing_regressions.py tests/test_rag_query.py`（61 passed）
  - [x] 引入 `jieba` 并建立 QA 规则模块的中文分词基础能力
  - [x] 抽离规则资源目录，承载归一化词库、分词词库、关键词库、句式短语库与黑名单库
  - [x] 实现规则层基础预处理：去噪/表达归一化后进入 `jieba` 分词，并继续保留 `raw_query`
  - [x] 将 `domain_guard` 的 hard deny 词库收口到共享规则资产
  - [x] 复查哪些 query 被规则层过早直接通过
  - [x] 复查哪些 query 本应进入 fallback 但没有进入
  - [x] 优先补 `translation`、soft route-edit、travel-adjacent `out_of_scope` 的规则与触发口径
  - 2026-05-09 同轮 keyed v2 rerun 结论：
    - `rules_only=0.7222`（52/72）
    - `rules_plus_fallback_qwen_flash=1.0`（72/72）
    - `rules_plus_fallback_qwen_turbo=0.9861`（71/72）
    - `routing_pure_fallback_qwen_turbo=0.9861`（71/72）
    - 当前最新 apples-to-apples 结果已满足“规则 + fallback 不低于纯模型”目标；`qwen-flash` 这一轮甚至优于同轮 pure fallback turbo。
    - `qwen-turbo` 当前唯一残余错例仍是 `RZH-TA-012`：`如果中间先吃点东西，后面接哪个点更合理？`，且该错例已确认发生在 fallback 分类阶段，不是规则层 direct-pass 过早放行。
  - [ ] 建立并持续维护以下规则资产：
    - 归一化词库
    - `jieba` 自定义分词词库
    - `translation` 关键词库 / 直短语库 / 语言名词库 / 文本对象词库
    - `manual_route_edit_redirect` 动作词库 / 对象词库 / soft route-edit 词库
    - `live_info` 时间词库 / 运营词库 / 直短语库
    - `attraction_explain` 景点名词库 / explain 关键词库 / 直短语库
    - `trip_assistant` 进度词库 / 安排词库 / 直短语库
    - weather / traffic / crowd boundary 词库
    - 公共交通导航支持已纳入 `navigation_text`；parking / air quality / restaurant 等 travel-adjacent boundary 词库仍需持续维护
    - hard deny 黑名单词库
    - 意图优先级与 fallback 触发规则配置
  - [x] 去掉 follow-up 词库与相关规则触发，避免把常见短句误当成稳定意图信号
  - [x] 收紧规则层口径：仅高把握命中才 direct pass，其余模糊 query 默认进入 fallback classifier
  - [x] 明确中文规则层不再维护英文词表；非中文 query 应先经 translator pivot 成中文后再路由
  - [x] 对齐英文 trip-assistant 集成测试到 preprocess-first 架构，避免测试继续依赖英文直路由
  - [x] 把 `weather_info` / `navigation_text` 接成正式 QA 能力，并补齐 `tests/test_qa.py`、`tests/test_qa_routing_regressions.py`、`tests/test_amap_weather_client.py`、`tests/test_amap_navigation_client.py` 的回归覆盖
  - [x] 把 `navigation_text` 从单纯 point-to-point intent 进一步收口为“规则直提槽位 + fallback 结构化提取 + multi-leg 聚合”能力，并补齐 `next-stop` / `destination-only` / `explicit route` / `multi-leg` 回归

### 4.3 Translation readiness 工作包
- [x] 盘点 translation 当前缺失的后端准备项，并完成第一轮后端实现收口：
  - config
  - provider/model 选择
  - timeout / fail-open 语义
  - metadata / observability
  - 2026-05-07 最新实现：translator 已从单一 QA intent 分支升级为共享底座，覆盖 query preprocessing、answer postprocess 和 explicit QA translation 三条路径
- [x] 将 translation benchmark 结果结构补成可表格化导出的 schema：
  - per-case 补 `run_id`、`dataset_name/version`、`question_type`、`direction`
  - 补 `prompt_tokens` / `completion_tokens` / `total_tokens` / `estimated_total_cost`
  - summary 补 `by_language` / `by_direction` / `by_question_type`
- [x] 扩 translator 语言支持到东南亚小语种首轮矩阵：
  - `ms`
  - `fil` / `tl`
  - `my`
  - `km`
  - `lo`
- [x] 扩 translation benchmark 数据集到东南亚语种 × 提问类型 × 双向翻译矩阵：
  - `product_translation`
  - `routing_preprocess`
- [x] 接入 translation Excel 导出与真实跑数验证：
  - `translation_cases`
  - `translation_model_compare`
  - 两模型真实 benchmark 结果导出
  - 已补一版中文 benchmark 总结文档，包含 XFYun 字符计费估算、长文本/短文本平均成本与推荐结论
- [x] 规划 translation 相关验证维度：
  - 纯 translation 输出质量
  - translation 后的 routing 稳定性
  - provider 缺失与 degraded 行为
  - bilingual translation 场景质量
  - 2026-05-07 已补一轮 XFYun ITS 真实验证：
    - `product_translation` 136 case，平均分 `4.39/5`，平均时延 `209ms`
    - `routing_preprocess` 48 case，平均分 `4.27/5`，平均时延 `587ms`
    - bilingual display 8 case，平均分 `4.0/5`
    - 本轮自然暴露 1 个 degraded case：Khmer `live_info` 预处理超时，`execution_path=timeout`
    - 当前最明显薄弱点仍是：translation 指令句在 preprocess 后未稳定路由到 `translation`，以及部分 `manual_route_edit_redirect` / `trip_assistant` 在小语种下仍会漂移
  - 2026-05-07 严格显式语种口径下复跑 XFYun ITS：
    - `product_translation` 维持 136 case，平均分 `4.69/5`，剩余 `2` 个 isolated `provider_error` degraded case（`product-009`、`product-025`）
    - `routing_preprocess` 维持 48 case，平均分 `4.74/5`，无 degraded case
    - 已确认本轮修复有效收口：translation 指令句在 preprocess 后已稳定命中 `translation`；显式 translation 已收口为默认信任 `user_language`，不再依赖正文语种推断
    - benchmark 数据口径也已正式收紧：每条 case 显式声明语种字段，去掉极端多语混合 case，runner 对缺字段和方向不一致直接 fail-fast
    - plain MT 可观测性与抗抖动能力已补第一轮收口：benchmark per-case 结果现已落 `llm_error/raw_text/structured_output_valid/attempt_count/retry_performed/attempts`，且 plain MT 默认启用 `1s` 单次超时 + 最多 `1` 次顺序重试
    - 当前剩余薄弱点进一步收口为：部分 `manual_route_edit_redirect` 仍会漂到 `trip_assistant/out_of_scope`，以及少数 `trip_assistant` 的 Burmese / Khmer / Lao pivot 中文表述仍不够稳定
  - 2026-05-08 routing 收口补记：当前实现已按方案 A 改为仅信任 `user_language`；`zh*` 直接路由，其余语言统一先 pivot 到中文后只跑一次规则路由。
  - 暂挂问题记录：用户选中文但正文含大量外语的混合输入场景已记入复盘，处理方案待后续单独设计。

### 4.4 QA 发布前验证工作包
- [x] 准备下一轮 QA 验证列表：
  - 2026-05-10 已补第一轮 E2E 主链路模型横评基础设施：`/api/v1/qa/ask` 支持 request-level `llm_provider/llm_model` override，`evals/run_e2e_qa_benchmark.py` 支持 `--sweep`，并新增示例配置 `evals/datasets/e2e_model_sweep_example.json`。
  - 2026-05-11 已继续把 E2E 数据集 grounding 口径收紧到当前 runtime truth：`evals/datasets/e2e_qa_benchmark_cases.json` 已升到 `v3`，当前 RAG 深问 case 只依赖运行时真实会建索引的四类文档（`history` / `practical_notes` / `photo_spot_notes` / `family_notes`），`real_rag_corpus_v1_zh.json` 暂仅保留为参考语料；后续若要恢复 `正阳门/中轴线/architecture/curation` 等更深 case，需先把 runtime ingestion 真正接通。
  - 2026-05-11 已修复一轮 RAG 深问未命中的主故障：`rag_retriever` 不再向 pgvector 查询注入运行时文档中不存在的 `poi_aliases` filter，`rag_index_service` 也已改为支持 list/scalar membership 过滤。修复后在 fallback-on 的 `8002` 服务上定向复测 `E2E-RAG-001/002/003`，三条都已恢复为 `retrieval_strategy=sql_then_rag`、`rag_query_status=ok`、`rag_backend_ready=true`。
  - 同日晚些时候已基于修复后的 `8002` 服务完整重跑 fallback E2E sweep：`qwen-plus` 当前成为新的最佳模型（`avg_score=4.43`，`pass_rate=0.90`，`intent_correct_rate=0.933`，`avg_latency_ms=2624`）；`gemini-2.5-flash-lite` 为 `avg_score=4.37`、`pass_rate=0.90`、`intent_correct_rate=0.933`、`avg_latency_ms=4194`；`doubao-seed-mini` 为 `avg_score=4.37`、`pass_rate=0.867`、`intent_correct_rate=0.90`、`avg_latency_ms=3013`。这一轮 benchmark 若只看质量/时延，阶段性最佳仍是 `qwen-plus`。
  - 但 2026-05-11 当晚产品最终决策已切到 `Doubao Mini`：主链路默认配置现已改为 `volcengine/doubao-seed-2-0-mini-260428`，按非思考模式运行；后续工作重点转为围绕 Doubao Mini 收口 prompt 结构、上下文裁剪与输出稳定性，而不是继续追求 benchmark 最优模型。  
  - 同日晚些时候已完成首轮 Doubao Mini prompt 收口：`src/yoyo/modules/qa/prompts.py` 已从英文长 system prompt 改为中文短结构，按“角色 / 能力边界 / SQL-RAG grounding / 输出格式”四段组织；同时继续按 intent 分上下文，并对 attraction / RAG / dialogue 做了首轮裁剪。定向回归 `tests/test_qa.py` 维持 `36 passed`。
  - 随后又补了第二轮 prompt 规则：保持 JSON 输出，但 `answer` 默认控制在 300 字以内，能简洁回答就优先短答；历史/文化深问可以适度更长，但长回复必须自然分成 2~3 段。主回答 prompt 传入的 dialogue history 也已扩到最近 10 轮，并单独沉淀文稿到 `docs/qa-prompt-doubao-v4.md`。
  - 2026-05-12 已继续收口 Doubao 主链路残余问题：`trip_assistant` prompt 现已显式约束完整 JSON 字段、`reason=null` 与布尔字段写法，`src/yoyo/modules/qa/generator.py` 也补了有边界的结构化 payload 归一化（补缺失 `reason`、裁剪空白、收口字符串布尔值），使 near-valid Doubao 输出不再轻易退回 formatter fallback。
  - 同轮还修复了显式 translation 的真实主链路故障：`src/yoyo/modules/translator/service.py` 已改为按产品定义默认提取“译成中文 / 给工作人员看”的 query 形态，并在 `_plain_mt_translate_for_qa(...)` 中增加保守兜底提取；`src/yoyo/modules/qa/orchestrator.py` 也已改为 translation intent 优先把 `raw_query` 而不是 pivot 后的 `effective_query` 传给 `translate_for_qa(...)`，避免原始引号短句在预翻译后丢失。
  - 2026-05-12 同日晚些时候又继续修了 QA 短路链路的三类真实问题：`src/yoyo/modules/qa/formatters.py` 与 `src/yoyo/modules/qa/orchestrator.py` 的英文 fallback / redirect 文案已统一改成中文；`src/yoyo/modules/knowledge/hybrid_context_builder.py` 的显式 route 槽位清洗也已补上，`从天安门怎么走到故宫？` 不再把 `怎么走` 污染进 origin。
  - 针对这一轮链路修复的定向回归现已通过：`pytest tests/test_qa.py -k "weather or navigation or route_edit or out_of_scope or translation" -v`（14 passed）、`pytest tests/test_navigation_slot_extraction.py -v`（3 passed）、`pytest tests/test_translator.py -k "show_to_local or bilingual or zh_suffix" -v`（4 passed）。
  - 下一步仅剩真实服务对齐验证：重启本地最新 QA 进程后，重新确认天气、文字导航、manual route edit redirect、boundary out_of_scope，以及 `帮我把‘Where is the restroom?’翻给工作人员看` 这五条真实请求都已命中当前源码语义。
  - 2026-05-12 又继续修了一条 session-aware trip status 残余问题：`我现在到哪一站了？` 现已稳定命中 `trip_assistant`，不再误落到 `live_info`；同时 `format_trip_assistant_answer(...)` 的确定性 fallback 文案也已同步中文化。
  - 新增回归已锁住这条主链路：`tests/test_qa_routing_regressions.py::test_intent_router_routes_current_stop_status_query_to_trip_assistant` 与 `tests/test_qa.py::test_trip_assistant_current_stop_status_query_uses_session_context`；本轮定向 pytest 通过 `6 passed`。
  - 2026-05-14 已补出 QA 手动联调页与预览接口：`GET /api/v1/qa/playground` + `POST /api/v1/qa/preview`。当前可直接覆写 `session/profile/attraction/dialogue_history` 等 prompt 变量，并配套 `tests/test_qa_playground.py`（3 passed）。
  - 同日还修复了一条 mixed-language translation 回归：`language=en` 且 query 同时含英文指令与中文原句时，不再因“含中文即直路由”而跳过 preprocess-first；`pytest tests/test_qa.py -k "translation" -vv` 当前为 `7 passed`。
  - 同日晚些时候继续收口了 playground 可用性：`发送 QA 请求` 现已只调用一次 `/api/v1/qa/ask`，默认页面改为最小 payload，不再预填大量 `session/profile/attraction/dialogue_history` override；同时 `metadata.latency_ms` 已补齐 `preprocess/routing/context_build/generation/postprocess/total` 分段耗时，页面也新增链路摘要与耗时摘要区。定向回归 `pytest tests/test_qa_playground.py -vv`（4 passed）与 `pytest tests/test_qa.py -k "translation or trip_assistant" -vv`（14 passed）已通过。
  - 2026-05-15 已继续把天气 fallback 链路收口成单次模型决策：只有规则已判 `weather_info` 且成功抽到地点时才跳过 fallback；其余天气问句统一进入 router fallback，由 fallback 一次同时返回 `intent + weather_location_name`，后续 `build_hybrid_context(...)` 直接复用该地点，不再单独触发第二次 weather-slot 模型调用。对应定向回归：`pytest tests/test_qa.py -k "weather or router_fallback" -vv`（9 passed）、`pytest tests/test_routing_benchmark.py -vv`（6 passed）。
  - 2026-05-15 已继续修两条真实 QA 主链路问题：1）`out_of_scope` / hard deny 的短路返回现已统一补齐 `latency_ms`，避免出现 `null` 分段耗时；2）router fallback prompt 已显式强化“深解释仍属 attraction_explain”的判定，像 `Please unpack the Forbidden City’s sequence... political theater` 这类 query 不再误收进 `out_of_scope`。另外 answer postprocess 在英文回译降级时新增了保守语言一致性兜底，避免直接把纯中文答案回给英文用户。对应定向回归：`pytest tests/test_qa.py -k "out_of_scope or answer_translation_degraded or forbidden_city_explanation" -vv`（4 passed）、`pytest tests/test_qa_routing_regressions.py -vv`（30 passed）。
  - 2026-05-15 已补出新一轮全链路多语言 QA benchmark 设计与 runner 时延埋点导出：
    - 数据集：`evals/datasets/e2e_qa_fullchain_multilingual_v1.json`
    - 模型 sweep：`evals/datasets/e2e_fullchain_qwen_doubao_sweep.json`
    - 对比模型：`dashscope/qwen-turbo` 与 `volcengine/doubao-seed-2-0-mini-260428`
    - 覆盖链路：smalltalk、hard deny、boundary、translation、SQL、SQL+RAG、live_info、weather_info、navigation_text、session-aware trip_assistant、manual_route_edit_redirect
    - 覆盖语言：中文、英文、泰语、越南语、印尼语、马来语、菲律宾语、缅甸语、高棉语、老挝语
    - `evals/run_e2e_qa_benchmark.py` 现已平铺输出 `preprocess/routing/context_build/generation/postprocess` 与 RAG / 天气 / 导航 / attraction / profile lookup 子阶段耗时，并在 Excel 中新增按语言、功能类别、intent、operation 聚合的 latency sheet
  - 2026-05-15 已基于 qwen-turbo 高延时 case 继续补出 `live_info` Redis 短缓存：
    - cache key 使用 `{beijing_date, attraction, info_type}`，避免同景点同日同类开放/预约/公告问题重复调用 live search provider
    - 普通结果、闭馆公告、provider 失败分别使用不同 TTL
    - metadata / E2E 导出会暴露 `live_info_cache_hit` 与 `live_info_info_type`
  - 2026-05-15 已补出 QA intent rule redesign 维护资产：
    - 设计文档：`docs/qa-intent-routing-rule-design.md`
    - 关键词/策略库：`docs/qa-intent-keyword-library.yaml`
    - 当前只作为设计资产，不接入 runtime；后续接入前先验证多意图冲突策略和 hard-negative 集合
  - routing accuracy
  - translation verification
  - degraded / fallback consistency
  - session-aware QA consistency
  - release-oriented E2E verification

---

## 5. P1 —— 测试与发布加固准备

### 5.1 功能测试说明 -> test matrix
- [x] 把 `docs/feature-test-guide.md` 进一步整理成 test matrix 的基础表
- [x] 为每个功能补充测试分层标签：
  - 单元测试
  - 集成测试
  - 链路测试
  - smoke / readiness
  - degraded / fault-injection
- [x] 为每个功能补充当前状态标记：
  - 已覆盖
  - 部分覆盖
  - 待补充

### 5.2 发布前验证轮次设计
- [x] 准备一轮面向发布的验证，重点覆盖：
  - smoke coverage
  - degraded / fault-injection coverage
  - QA routing 与 translation verification
  - worker / API environment consistency
  - 主链路的 latency 与 responsiveness 检查
- [x] 明确该轮验证的输出物：
  - 测试矩阵
  - 执行清单
  - 结果记录入口
  - blocking / non-blocking 判定口径
- 补充最新真实环境观察（2026-05-04）：
  - 非 QA 主链路已再次跑通
  - 已通过重启复测确认：finished-session 下 `guide/content` 当前语义为 `409 guide session finished`
  - 后续若继续做发布前风险轮，仍应先确认 API / worker 已按当前源码重启，避免再次混入旧进程语义

---

## 6. 未来 session 的工作规则
- 当前阶段默认阅读顺序应为：
  1. `AGENTS.md`
  2. `README.md`
  3. `docs/README.md`
  4. `docs/todo-phase-2.md`
  5. `docs/phase-2-summary.md`
- `README.md` 继续作为 canonical document index。
- `docs/README.md` 作为详细文档地图和专题入口。
- `docs/todo.md` 保留为上一阶段归档。
- `docs/current-session-summary.md` 保留为历史 session 日志。
- 只要发生实质开发、调试、benchmark、规则调整、架构决策、文档结构、routing 方向、测试策略或阶段范围变化，就需要在同一轮里同步更新：
  - `docs/phase-2-summary.md`：当前状态和续接摘要。
  - `docs/todo-phase-2.md`：完成项、待办项和下一步。
  - `docs/dev-retrospective.md`：只在有策略变化、明确问题归因、回归、可复用解决方案或维护规则变化时更新；普通小测试和 routine verification 不写。
  - 如入口结构变化，再同步 `README.md` 与 `docs/README.md`。
