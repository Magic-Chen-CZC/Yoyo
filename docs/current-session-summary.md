# Current Session Summary

> History note: this file is now a historical session log.
> For the current active summary, read `docs/phase-2-summary.md`.
> For the current active todo, read `docs/todo-phase-2.md`.

This document summarizes the major product/backend changes completed in prior Claude sessions so later work can recover historical context when needed.

Note: this file is no longer part of the default current-phase resume set. The current working handoff set should be kept current through `CLAUDE.md`, `README.md`, `docs/todo-phase-2.md`, and `docs/phase-2-summary.md`, with README acting as the canonical document index for architectural and implementation work.

## 0. 2026-05-15 天气 fallback 链路收口补记

- 当前天气主链路已进一步收口为：只有规则已经判定 `weather_info` 且规则已经抽到地点时，才允许直接跳过 fallback；只要规则未命中天气，或者命中了天气但没有抽出地点，都必须进入 router fallback。
- router fallback 不再只做“意图分类”，而是会在 `intent=weather_info` 时同时返回 `weather_location_name`；orchestrator 会把该值透传到 routing session context，供后续 `build_hybrid_context(...)` 直接复用。
- 因此天气链路已不再额外调用独立的 weather-slot fallback 模型；之前“先路由 fallback，再额外抽天气地点 fallback”的双模型串行路径已经去掉。
- 对应新的可观测性语义是：若 `context_build_breakdown_ms.weather_target_source = fallback`，则说明天气地点来自 routing 阶段已经完成的 fallback 结果，而不是 context-build 阶段再发起一次模型调用；因此 `weather_target_fallback_ms` 现在应保持 `0`，额外模型成本主要体现在 `routing_ms`。
- 对应回归已通过：`pytest tests/test_qa.py -k "weather or router_fallback" -vv`（9 passed）与 `pytest tests/test_routing_benchmark.py -vv`（6 passed）。

## 0. 2026-05-14 QA playground 与 mixed-language translation 修复补记

- 本轮已在后端直接补出首版 QA 手动联调页：`GET /api/v1/qa/playground`，同时新增 `POST /api/v1/qa/preview` 作为调试预览接口。
- playground 当前支持直接覆写 `session_context`、`profile`、`attraction`、`dialogue_history` 等 prompt 变量，并把实际应用状态写回 `metadata.playground`，便于前端/产品直接手动验证翻译、路由、session-aware QA 与回答生成链路。
- 同轮也修复了一条真实回归：`language=en` 但 query 同时含英文指令和中文原句时，orchestrator 之前会因为“只要含中文就当中文直路由”而跳过 preprocess-first 语义，导致 `Please translate: 请帮我拍张照片` 误落到 `out_of_scope`。
- 当前已把这条判断收口为：仅当 `language=en` 且全文不含拉丁字母时，才把 query 视作 CJK 直路由；因此 mixed-language translation query 会继续走 preprocess/translation 主链路。
- 对应验证已通过：`tests/test_qa_playground.py`（3 passed）与 `pytest tests/test_qa.py -k "translation" -vv`（7 passed）。
- 同日晚些时候又继续收口了 playground 的真实可用性：`发送 QA 请求` 现已只发一次 `/api/v1/qa/ask`，不再额外串行调用 preview；默认表单也改成最小 payload，不再预填大量 `session/profile/attraction/dialogue_history` override，只有用户显式填写或切换 preset 时才注入 `context.qa_playground`。同时 QA metadata 已补出 `latency_ms` 分段耗时，playground 页面新增链路摘要与耗时摘要，便于直接看出慢点是在 preprocess、routing、context build、generation 还是 postprocess。对应回归当前为：`pytest tests/test_qa_playground.py -vv`（4 passed）与 `pytest tests/test_qa.py -k "translation or trip_assistant" -vv`（14 passed）。
- 随后又继续把 `context_build_ms` 拆细到子步骤级别：`metadata.latency_ms.context_build_breakdown_ms` 现会暴露 attraction/profile 查询、weather target 解析、weather/navigation provider 调用、RAG 查询、prompt projection 等耗时与来源标记。这样后续再看“为什么 context_build 很慢”时，不需要再靠读代码猜，而是可以直接看本次请求到底慢在 fallback 模型、Amap、RAG 还是其他上下文加载子步骤。

## 0. 2026-05-09 天气 / 文字导航接入范围补记

- 本轮新的 QA 能力工作包已收口：先只保留“景点天气”和“文字导航”两项，不继续推进“人流量统计 / 拥挤度”能力。
- 原因不是路由层问题，而是产品输入边界尚不成立：用户当前无法稳定提供图片或实时画面，因此百度视觉人数统计接口暂不适合作为当前产品能力入口。
- 当前建议的数据源边界因此调整为：天气与文字导航走高德 Web 服务 API；景点官网/开放时间/预约/闭馆通知仍保留现有 `live_info` 链路；拥挤度 / 排队热度继续保留为 boundary / `out_of_scope`。
- 预期实现方向：新增 `weather_info` 与 `navigation_text` 两个正式 intent，而不是继续把天气塞在 `out_of_scope`，也不把导航混入现有 `trip_assistant`。
- 若后续再恢复人流量能力，应以“有图片/画面输入的视觉统计”而不是“按景点名查询实时热度”的产品语义重新单独设计。
- 2026-05-09 当日晚些时候，这一工作包已经从计划进入实现：Amap weather / text navigation provider、HybridContext、orchestrator 确定性分支、formatter/validator、以及 QA/API/client 回归测试都已补齐，`weather_info` 与 `navigation_text` 已成为正式 supported QA intent。

## 0. 2026-05-09 导航槽位提取补记

- 在 `weather_info` / `navigation_text` 已接入 QA 主链路后，本轮又把导航从“point-to-point 文字导航 intent”继续收口成槽位优先实现。
- 当前导航处理顺序已变成：规则优先直提高把握槽位（`下一站怎么去`、`去X怎么走`、`从A到B怎么走`）-> 复杂或多地点表达走 fallback 结构化槽位提取 -> 下游按连续 legs 逐段复用 Amap 单段导航并聚合输出。
- 规则侧已开始复用北京景点 canonical + alias 词表，避免导航只认英文 canonical 名；同时继续保留 route-edit / trip-assistant 的边界，避免“删掉下一站”之类编辑语义被误抓成导航。
- 本轮新增自动化覆盖包括：`tests/test_qa_routing_regressions.py` 的 destination-only / next-stop / multi-leg 路由回归、`tests/test_qa.py` 的 multi-leg API 行为测试，以及 `tests/test_navigation_slot_extraction.py` 的导航聚合测试。
- 当前导航相关回归已通过：`tests/test_qa_routing_regressions.py`、`tests/test_qa.py`、`tests/test_amap_navigation_client.py`、`tests/test_navigation_slot_extraction.py`，共 62 passed。
- 2026-05-10 本轮又补了首版导航 hard-case benchmark 数据集与 runner：`evals/datasets/navigation_hard_cases_v1.json`、`evals/run_navigation_benchmark.py`、`evals/results/navigation_hard_v1_results.xlsx`。
- 2026-05-11 已继续修完该 benchmark 的两条残余错例：`接下来怎么走？` 已通过 follow-up navigation phrase 优先级与 conflict 豁免稳定命中 `navigation_text`；`去故宫再去景山怎么走？` 已通过 destination-only multi-leg 切分顺序修正与 origin hydrate 收口。当前导航 benchmark 最新结果为 `14/14=1.0`。
- 同轮把 E2E QA benchmark 升级成可直接做主链路模型 sweep：`/api/v1/qa/ask` 请求体新增 `llm_provider` / `llm_model`，`evals/run_e2e_qa_benchmark.py` 已支持 `--sweep` 和示例配置 `evals/datasets/e2e_model_sweep_example.json`；共享 runtime 也已注册 `volcengine` / `doubao` provider，用于后续 gemini / qwen / doubao 横评。
- 2026-05-11 当日晚些时候又继续修复了 E2E RAG 深问未命中的真实故障。最终定位结果是：问题不在 orchestrator attraction 透传，而在 RAG query filter 本身——`rag_retriever.py` 会向 pgvector 查询注入当前 runtime 文档里并不存在的 `poi_aliases` filter，`rag_index_service.py` 同时又把 `language/doc_type` 这类 list filter 用标量 `!=` 直接比较，导致有效向量命中被过滤空。
- 修复内容已经落地：`rag_retriever.py` 移除了 `poi_aliases` filter，`rag_index_service.py` 改成 list/scalar membership 过滤；并新增测试锁住这两个点：`tests/test_rag_backend.py`、`tests/test_rag_query.py`（8 passed）。
- 修复后已重启 fallback-on 的 `8002` 服务，并定向复测三条深问：`E2E-RAG-001`、`E2E-RAG-002`、`E2E-RAG-003` 均恢复为 `retrieval_strategy=sql_then_rag`、`rag_query_status=ok`、`rag_backend_ready=true`、`grounding=sql_then_rag`。
- 随后已基于修复后的 `8002` 再完整重跑一轮 fallback E2E sweep，最新 summary 为：`qwen-plus avg_score=4.4333 / pass_rate=0.90 / intent_correct_rate=0.9333 / latency=2624ms`，`gemini-2.5-flash-lite avg_score=4.3667 / pass_rate=0.90 / intent_correct_rate=0.9333 / latency=4194ms`，`doubao-seed-mini avg_score=4.3667 / pass_rate=0.8667 / intent_correct_rate=0.90 / latency=3013ms`。
- 这一轮新的 benchmark 结论一度是：在 fallback-on 主链路下，RAG 修复后 `qwen-plus` 已经成为当前综合最优候选；Gemini 质量接近但延迟最高，Doubao 延迟中等但通过率略低。
- 但同日晚些时候，用户已明确改产品决策：主链路默认回答模型不再跟随这一轮 benchmark 最优项，而是正式切到 `volcengine/doubao-seed-2-0-mini-260428`，按非思考模式运行；代码默认值、README 与 readiness 文档已同步到这一决策。
- 随后已继续完成首轮 Doubao Mini prompt 收口：`src/yoyo/modules/qa/prompts.py` 不再使用英文长 system prompt，而是改成中文短结构，按“角色 / 能力边界 / SQL-RAG grounding / 输出格式”组织；同时 attraction / RAG / session / dialogue 上下文已做首轮裁剪，降低小模型的 token 负担与偏航概率。`tests/test_qa.py` 回归维持 `36 passed`。
- 同日晚些时候又继续补了第二轮 prompt 规则：仍保持 JSON 输出，但 `answer` 默认要求 300 字以内、能短答就短答；历史/文化深问可适度更长，但长回复必须自然分成 2~3 段。另外，主回答 prompt 现在已携带最近 10 轮对话作为上下文，并把当前 prompt 版本单独落在 `docs/qa-prompt-doubao-v4.md`，方便后续直接改。
- 2026-05-12 本轮继续修完了 Doubao 主链路的两个明确阻塞点。第一处是 `trip_assistant` 虽然已成功调用 Doubao，但结构化输出会因轻微格式漂移（缺失 `reason`、枚举字段带空白、布尔值写成字符串）被判成 `structured_output_valid=false`，随后退回 formatter fallback；当前已通过 `src/yoyo/modules/qa/prompts.py` 的更硬 JSON 契约与 `src/yoyo/modules/qa/generator.py` 的有边界 payload 归一化共同收口。第二处是显式 translation 在真实主链路里虽然补了中文提取规则，但 orchestrator 仍把 pivot 后的 `effective_query` 传入 `translate_for_qa(...)`，导致原始引号短句在 preprocess 后丢失；当前已改为 translation intent 优先传 `raw_query`，并在 `src/yoyo/modules/translator/service.py` 加了保守兜底提取。
- 本轮新增/更新的定向回归已通过：`tests/test_translator.py`（17 passed）与 `pytest tests/test_qa.py -k "trip_assistant or translation" -v`（12 passed）。真实服务冒烟也已确认：`把“Where is the restroom?”翻成中文` 已恢复为 `intent=translation`、`execution_path=plain_mt`、`provider=xfyun_its`、`target_language=zh`，回答为 `洗手间在哪里？`；`我下一站去哪？` 也已可稳定走 `volcengine/doubao-seed-2-0-mini-260428` 的结构化成功路径，不再因轻微格式漂移退回 fallback。
- 同日晚些时候又继续修了五条真实短路链路暴露出的残余问题：`src/yoyo/modules/qa/formatters.py` 与 `src/yoyo/modules/qa/orchestrator.py` 中所有用户可见的英文 weather / navigation / translation / route-edit / out-of-scope fallback 文案都已统一中文化；`src/yoyo/modules/knowledge/hybrid_context_builder.py` 也补上了显式 route 槽位片段清洗，修复 `从天安门怎么走到故宫？` 会把 `怎么走` 混进 `origin_name` 的问题。
- 与这轮修复对应的测试已全部通过：`pytest tests/test_qa.py -k "weather or navigation or route_edit or out_of_scope or translation" -v`（14 passed）、`pytest tests/test_navigation_slot_extraction.py -v`（3 passed）、`pytest tests/test_translator.py -k "show_to_local or bilingual or zh_suffix" -v`（4 passed）。
- 随后已在新起的 `8017` 实例上完成真实复测：天气、文字导航、manual route edit redirect、boundary out_of_scope 四条请求都已验证收口；`帮我把‘Where is the restroom?’翻给工作人员看` 也已确认不再误判成 `out_of_scope`，而是稳定命中 `translation`。
- bilingual display 这条剩余的真实问题已进一步缩小到 provider 层：`src/yoyo/modules/translator/service.py` 已修正 plain-MT 显式翻译在 `language=zh` 且正文为英文原句时的 source-language 选择逻辑，不再把该请求误固定成 `zh -> zh`；新增 translator/QA 回归均已通过。当前真实链路仍退回 degraded，只因为 `xfyun_its` 上游连续返回 `500 Internal Server Error`，metadata 已显示 `source_language=null`、`target_language=zh`、`execution_path=provider_error`。
- 同轮又继续修了一条 session-aware trip status 残余问题：`我现在到哪一站了？` 之前在真实主链路里会误落到 `live_info`，原因是规则层只命中了 `现在` 这类 live 弱信号，没有把“哪一站/当前站/现在到哪”识别成 trip-status 强信号。当前已在 `src/yoyo/modules/qa/rule_assets.py` 与 `src/yoyo/modules/qa/intent_router.py` 补齐 trip-assistant 直短语、关键词与 conflict 豁免，并新增 `tests/test_qa_routing_regressions.py::test_intent_router_routes_current_stop_status_query_to_trip_assistant` 和 `tests/test_qa.py::test_trip_assistant_current_stop_status_query_uses_session_context` 锁住行为。与此同时，`src/yoyo/modules/qa/formatters.py::format_trip_assistant_answer(...)` 的确定性 fallback 文案也已同步中文化，避免这条短路链路继续暴露英文回答。
- 同轮继续修了 QA 主链路的 benchmark / grounding 语义：
  - E2E benchmark 口径已对齐：`北京今天会不会下雨？ -> weather_info`，`把景山公园换掉，帮我把路线改轻松一点。 -> manual_route_edit_redirect`，交通/拥挤度继续保持 boundary `out_of_scope`
  - 中文景点 alias 解析已补到 retrieval + orchestrator，单轮 query 可解析 `故宫`、`故宫博物院`、`天安门`、`景山公园`、`正阳门`
  - RAG filter 已从英文单语改为 `zh+en`，并按深问信号优先限制到 `history/symbolism/architecture/curation`
  - SQL / RAG 分工已显式化到 retrieval metadata、generation prompt 与 router fallback prompt；后续维护项为 `SQL 覆盖字段白名单` 与 `RAG 覆盖深问字段白名单`
  - session-aware trip-assistant 还补了一个确定性短路：对“当前路线 / 当前站点”这类 query 直接用 session context 回答，避免被生成式回答漂移
  - 2026-05-11 又继续把 E2E benchmark grounding 口径收紧到当前 runtime truth：数据集已升到 `v3`，RAG case 只依赖当前 runtime 真正会建索引的 `history/practical_notes/photo_spot_notes/family_notes` 四类文档；`real_rag_corpus_v1_zh.json` 当前只保留为参考语料，不再直接假设 `正阳门/中轴线/architecture` 已被运行时接入
  - 本轮 targeted 回归已通过：`tests/test_qa.py tests/test_qa_routing_regressions.py tests/test_rag_query.py`（61 passed）

## 0. 2026-05-09 routing keyed v2 rerun 补记

- 本轮继续把 benchmark runner 对齐到真实 runtime 语义：非中文 case 改为优先走 `query_zh` / pivot 中文路由，`evaluate_routing_case(...)` 也补上与 orchestrator 一致的 hard deny override，避免 benchmark 继续沿用旧的直路由语义。
- translator routing preprocess prompt 也已同步加强：明确要求保留 negation、same-day signal、mixed-intent structure 与 ambiguity，不允许把 mixed-intent query 简化成单意图。
- 规则层继续按用户要求收紧：中文规则资产不再维护英文词表；去掉 follow-up 词库；`translation` 与 `live_info` 的 mixed-intent case 改为显式进 fallback；route-edit negation（如“先别改路线”）不再被 route-edit 规则强抓。
- 回归已通过：`tests/test_qa_routing_regressions.py`、`tests/test_routing_benchmark.py`，以及 translator prompt 的新增回归均已跑通。
- 随后完成 keyed v2 rerun：`rules_only=0.7222`（52/72）、`rules_plus_fallback_qwen_flash=1.0`（72/72）、`rules_plus_fallback_qwen_turbo=0.9861`（71/72）、`rules_plus_fallback_qwen35_flash_0223=0.7222`（52/72）。
- 为了做同轮 apples-to-apples 对照，又补跑了 `routing_pure_fallback_qwen_turbo`：`0.9861`（71/72），`fallback_used_cases=72`，平均时延 `943.88ms`。这轮先后两次尝试里，第一次因为没把 DashScope key 带进运行时而意外全部退回规则结果，定位后已按正确环境重跑并覆盖产物。
- 当前最重要的新结论是：最新结果已满足“规则 + fallback 不低于纯模型”目标；其中 `qwen-flash` selective fallback 这一轮达到 `1.0`，高于同轮 pure fallback turbo，而 `qwen-turbo` selective fallback 与 pure fallback turbo 持平。
- `qwen-turbo` 当前 selective fallback 与 pure fallback turbo 的唯一共同残余错例都是 `RZH-TA-012`：`如果中间先吃点东西，后面接哪个点更合理？`，仍被判成 `manual_route_edit_redirect`。这说明该问题现阶段已经从规则层 direct-pass 误抓，收口成 fallback 分类边界问题。
- 最新 xlsx 已刷新到：`evals/results/routing_zh_hard_v1_rerun_20260509_qwen_turbo_keyed_v2_results.xlsx`。

## 0. 2026-05-08 pure fallback turbo 对照实验补记

- 在完成 zh-hard routing rerun 之后，本轮继续把 `rules_plus_fallback_qwen_turbo` 的剩余错例逐条抽出，确认问题主要集中在 soft route-edit、translation 混淆和 travel-adjacent `out_of_scope`。
- 随后额外补做了一轮 `pure_fallback_qwen_turbo` 对照实验：72 条 case 全部绕过规则层，直接调用同一版中文 fallback prompt + DashScope `qwen-turbo` 做单标签分类。
- 首次尝试因缺失 DashScope key 导致实验无效；在补上 `DASHSCOPE_API_KEY` 后重跑，正式结果收口为：71/72 正确，准确率 `0.9861`，平均时延 `944.82ms`。
- pure fallback 下六类 intent 的结果几乎全部拉满：`attraction_explain`、`live_info`、`trip_assistant`、`manual_route_edit_redirect`、`translation` 都达到 `1.0`，只剩 `out_of_scope=0.9375`，唯一错例是 `从北京南站到故宫最快怎么坐地铁？` 仍被判成 `trip_assistant`。
- 这轮对照实验带来的关键结论不是“要再换更强模型”，而是“当前 rules + selective fallback 形态的主要瓶颈已经转移到规则模块本身”：许多残余错例并不是 `qwen-turbo` 不会分，而是规则层过早直接通过，或没有把足够多的模糊 query 交给 fallback。
- 因此后续优先级已进一步收口为：先重设计规则模块与 fallback 触发策略，再考虑局部 few-shot、prompt 微调或继续扩模型比较范围。
- 这轮结论已回写到 `docs/routing-zh-hard-benchmark-report-2026-05-08.md`、`docs/phase-2-summary.md`、`docs/todo-phase-2.md` 与 `docs/dev-retrospective.md`。
- 同日后续实现已开始把 QA 规则层落到 `jieba`：新增共享 `rule_assets.py`，把归一化词库、直短语、关键词库、boundary 词库和 hard-deny 词库从 router 常量中抽离，并让 router 开始走“表达归一化 -> `jieba` 分词 -> 短语/关键词命中 -> fallback 决策”的骨架。
- 2026-05-09 继续补了一轮规则层收口：去掉 follow-up 词库与相关触发，不再把常见短句当作稳定意图信号；中文规则层也不再维护英文词表，非中文 query 必须先经 translator pivot 到中文再路由。
- 同轮把最后一条英文 trip-assistant QA 集成测试对齐到 preprocess-first 架构：`tests/test_qa.py::test_trip_assistant_runtime_error_returns_route_aware_fallback` 现已显式 mock `preprocess_query`，先把英文 query 转成中文再进入严格规则层。
- 回归结果已确认收口：`tests/test_qa_routing_regressions.py` 16 passed，`tests/test_qa.py -k "fallback or translation or pivot or boundary or route_edit"` 16 passed，`tests/test_routing_benchmark.py` 4 passed。

## 0. 2026-05-07 translator / translation verification 补记

- 在上一轮 translator / benchmark 收口之后，本轮继续补做了一轮严格显式语种口径下的 XFYun ITS translation verification，分别覆盖 `product_translation` 与 `routing_preprocess` 两套数据。
- 新口径要求每条 case 显式声明 `user_language`、`source_language`、`target_language`、`direction`，并移除了极端多语混合 case；runner 对缺字段和方向不一致直接 fail-fast。
- `product_translation` 共 136 case，平均分 `4.69/5`，平均时延 `398ms`，剩余 2 条 isolated `provider_error` degraded case（`product-009`、`product-025`）；direct translation 已基本稳定，bilingual display 8 case 平均分仍为 `4.0/5`。
- `routing_preprocess` 共 48 case，平均分 `4.74/5`，平均时延 `173ms`，本轮无 degraded case。
- 本轮最重要的新结论不是“XFYun 纯翻译质量不够”，而是“数据口径收口后，translation 主路径已稳定，当前剩余问题已经缩小到少量 provider 级异常与个别 routing 边界题”。
- 同日又继续补完 plain MT 可观测性与抗抖动收口：benchmark per-case 结果现在会落 `llm_error`、`raw_text`、`structured_output_valid`、`attempt_count`、`retry_performed`、`attempts`，后续再遇到 isolated degraded case 时不需要再靠外部重跑猜原因。
- plain MT 当前默认改为“单次 `1s` 超时 + 最多 `1` 次顺序重试”，仅对 retryable 上游故障触发；这轮已补齐对应回归并确认 `tests/test_translator.py` 与 `tests/test_translation_benchmark.py` 通过。
- 目前最明显的剩余 routing 弱点包括：
  - `manual_route_edit_redirect` 仍有一部分在 preprocess 后漂移到 `trip_assistant` 或 `out_of_scope`
  - Burmese / Khmer / Lao 的少数 trip_assistant pivot 中文表述仍不够稳定
- 因此，translation readiness 现阶段最该继续补的，不是再扩数据集，而是补残余 degraded 样本 spot check，以及“preprocess 后 intent 保持”专项验证与修正。
- 同轮产品策略也已进一步收口：显式 translation 默认按用户所选语言作为 source language，不再继续做正文语种检测；极少数“界面语言 A、正文语言 B”场景暂不处理。
- 2026-05-08 新的 QA routing 收口决定：按方案 A 仅信任请求里的 `language` 字段判断是否中文；若为 `zh*` 则直接路由，否则统一先做中文 pivot 再路由一次，不再保留原始 query 的第一轮规则路由。
- 同轮补记一个暂挂问题：若用户选择中文，但正文里包含大量外语，当前 routing 仍会直接按中文路径处理并绕过 preprocess；该问题本轮只记录到复盘，暂不定义处理方案。
- 同轮也开始正式落地第一轮 DashScope Qwen routing benchmark：已补 runtime DashScope provider、中文 router fallback prompt、`routing_candidates_qwen_zh_hard_v1.yaml`，并新建 72 条的 `routing_benchmark_cases_zh_hard_v1.json` 作为中文 hard-case 基线数据集。
- 随后已完成首轮真实跑数与导出，并在放松弱信号 `out_of_scope` 兜底后完成 rerun：`rules_only` 准确率 `0.5694`；`rules_plus_fallback_qwen_flash` 为 `0.8611`；`rules_plus_fallback_qwen35_flash_0223` 仍为 `0.5694` 且 fallback 未生效；`rules_plus_fallback_qwen_turbo` 为 `0.8889`，当前是本轮最佳候选。对应 xlsx 已导出到 `evals/results/routing_zh_hard_v1_results.xlsx`。
- rerun 后的主要剩余错例已收口为三组：`route_edit_soft_zh` 这类弱改路线表达、`translation` 的显式翻译/通知/自然表达三类混淆，以及少量 travel-adjacent `out_of_scope`（如 programming / finance / transit / air_quality）。正式分析已落到 `docs/routing-zh-hard-benchmark-report-2026-05-08.md`。
- 同轮又按最新产品判断收口了 rules/fallback 分工：移除 `weak_travel_signal_before_out_of_scope` 这类弱信号直接拒答，只保留 hard deny 与 weather/traffic/crowd 明确 boundary 的早拒绝；其余规则未命中 query 继续交给 intent router 与 fallback 承接，并补了 API / router regression 覆盖。

## 0. 2026-05-07 translator / translation benchmark 补记

- 本轮已开始落地新的 translator 架构，不再把 translation 仅视为 QA 内的单一 intent。
- 当前后端已补出共享 translator 底座，覆盖三条路径：
  - query preprocessing：外语 query -> 中文 pivot
  - answer postprocess：内部中文回答 -> 用户语言
  - explicit QA translation：显式翻译请求，支持双语展示输出
- 当前实现策略是：
  - 中文与英文请求默认不强制走 preprocessing，以避免打扰现有主链路
  - 东南亚等其他外语 query 可进入 translate-then-route 路径
  - 普通 QA 回答在需要时再翻回用户语言
  - 显式 translation 继续保留独立产品语义，用于“帮我翻给本地人看 / 帮我问一下”类场景
- 本轮新增实现：
  - `TranslatorResult` 已补 token / cost 字段
  - translation benchmark runner 已补 `run_id`、`dataset_name/version`、`question_type`、`direction`、平铺评分字段与 summary 聚合字段
  - 东南亚小语种首轮支持已扩到 `ms`、`fil/tl`、`my`、`km`、`lo`
  - translation datasets 已扩成“语种 × 提问类型 × 中译外/外译中”矩阵
  - `evals/export_excel.py` 已新增 `translation_cases` 与 `translation_model_compare` sheet
- 当前已补的自动化验证覆盖：
  - translator disabled / degraded 行为
  - usage/cost 透传
  - bilingual translation intent 输出
  - translation benchmark per-case / summary 字段完整性
- 当前阶段结论：translator 与 translation benchmark 已从 smoke 原型进入可比较、可导出阶段；下一步重点变成真实跑数、Excel 结果核对，以及两模型在大样本东南亚语种矩阵上的对比。
- 同日已完成 HY-MT 与 XFYun ITS 的真实 benchmark 跑数和中文对比总结：在修复 `.env` 中缺失的 XFYun 凭证后，XFYun 在 `product_translation`（4.39 vs 3.85）与 `routing_preprocess`（4.36 vs 3.95）两套数据上的平均分都高于 HY-MT，平均时延也分别从 1865ms / 2561ms 降到 249ms / 234ms。
- 当前还补了一版按字符计费的 XFYun 成本估算：以本轮 1770 字符、每万字符约 0.45 元计，总成本约 0.07965 元，184 条 case 的单条平均成本约 0.00043 元；按输入长度分桶，短文本约 0.00016 元/条，长文本约 0.00068 元/条。
- 同日产品决策已进一步收口：放弃 HY-MT 作为后续正式 translator 候选，默认翻译器切换为 XFYun ITS；HY-MT benchmark 结果仅保留为历史对照，不再作为后续正式翻译方案。
- 为便于下一次清空上下文后续接，当前最短 handoff 结论是：translator 和 benchmark 主体工作已收口，后续从 `docs/todo-phase-2.md` 的 `4.3` 未完成项继续，优先规划 translation verification 维度，而不是继续改 translator 默认模型或数据集矩阵。

## 0. 2026-05-04 真实 QA 复核补记

- 在本地真实服务栈下追加完成了一轮面向 QA 薄弱点的验证，覆盖了 deep attraction、follow-up、trip_assistant 中文口语、translation、manual route edit redirect、天气/交通/拥挤度边界、live_info、mixed query 和 hard out-of-scope。
- 当前真实环境里更稳定的区域包括：`manual_route_edit_redirect`、weather/traffic/crowd 边界题、hard out-of-scope。
- 当前更需要进入下一轮收口的区域包括：`trip_assistant` 中文口语问法、live_info + attraction-explain 混合题、follow-up retrieval 连续性、translation 成功路径 metadata 一致性。
- 这些结论已经同步回 `docs/test-rounds-log.md`、`docs/todo-phase-2.md` 和 `docs/phase-2-summary.md`，原本可作为 QA routing / translation hardening 的输入继续推进。
- 2026-05-04 新决定：QA 部分暂不继续展开；用户会先把语言能力改到支持东南亚小语种，再由用户本人单独设计和执行 QA 测试。
- 同日补做了一轮非 QA 发布前风险测试：guide/worker 真链路、GPS/playback 状态切换、route edit 后 version switch、share-card finish 边界均通过；期间曾发现一个部署一致性风险——本地 API 进程不是 `--reload` 模式，且启动后源码仍有变更，因此一度观测到 finished-session 下 `guide/content` 返回 `404`。
- 随后在重启 API / worker 并按当前源码复测后，该问题已收口：finished-session 下 `guide/content` 恢复为 `409 guide session finished`，说明上一轮偏差来自运行进程未对齐源码，而不是当前代码语义 bug。

## 1. Product direction confirmed in this session

### QA routing direction update
- The product direction for intent recognition is now: **translator first -> rules + small-model classifier -> downstream processing pipelines**.
- All multilingual queries are planned to be translated into Chinese before intent recognition.
- The classifier layer is responsible for routing into downstream pipelines such as SQL, RAG, live search, redirect, or reject handlers.
- Rules are still kept, but only as high-precision guardrails rather than the main semantic classifier.

### Onboarding / identity
- First phase uses **guest quick entry** rather than full auth.
- The user picks a **guide role**, but this is currently mapped onto `guide_style_preference` rather than a separate role system.
- The onboarding questionnaire is now a fixed, versioned, choice-based flow.

### Travel selection
- Planner now supports first-phase entry modes:
  - `template`
  - `manual_poi`
  - `ai_recommendation_selected`
- These are still first-phase backend scaffolds, not the final full planner experience.

### Map direction
- The map is explicitly treated as a **cognitive map**, not a real map product.
- Amap is only used as a **route engine** for order/polyline calculation, not as the rendering map itself.

### QA / Guide knowledge strategy
- **QA**: SQL-first + first-phase RAG fallback path.
- **Guide**: keep SQL-first; do **not** make Guide depend on RAG.
- The user explicitly decided Guide should rely on richer SQL content instead of Guide-side RAG.

### Guide UX decision
- Guide content is short because of audio playback constraints.
- From the user perspective, there should be only **one** “more/change content” action.
- Backend action is now unified as `cycle_content`.

### External business-material framing update
- The current external proposal draft for the Southeast Asia inbound-tourism AI guide project is now considered **too product-spec / implementation-plan oriented** for investor use.
- The next rewrite direction should shift from a feature-and-architecture narrative to an **investor-facing business plan** narrative.
- The rewritten material should lead with market opportunity, target customer, wedge, distribution, monetization, milestones, and defensibility, while compressing technical details into a brief execution-enabler section.

---

## 2. Main implementation completed in this session

### 2.1 Guest onboarding
Added guest quick-entry and questionnaire/profile mapping.

Key work:
- Guest session API
- Fixed questionnaire flow (`v1`, 7 questions)
- Guide-role choice mapped to `guide_style_preference`
- Questionnaire submission now validates answers and updates `UserProfile`

Key files:
- `src/yoyo/db/models/guest.py`
- `src/yoyo/modules/guest/*`
- `src/yoyo/api/v1/guest.py`
- `src/yoyo/modules/questionnaire/flow.py`
- `src/yoyo/modules/questionnaire/profile_mapper.py`
- `src/yoyo/modules/questionnaire/schemas.py`
- `src/yoyo/modules/questionnaire/service.py`
- `src/yoyo/api/v1/questionnaire.py`
- `alembic/versions/0004_add_guest_users_and_profile_sources.py`

---

### 2.2 Planning entry modes
Expanded itinerary creation toward the first-phase travel selection flows.

Key work:
- Added route templates
- Added recommendation endpoint
- Added manual POI entry support
- Planner input now tracks `entry_type`, `template_id`, `selected_poi_ids`

Key files:
- `src/yoyo/modules/planner/template_repository.py`
- `src/yoyo/modules/planner/recommendation_service.py`
- `src/yoyo/modules/planner/recommendation_schemas.py`
- `src/yoyo/modules/planner/poi_selector.py`
- `src/yoyo/modules/planner/plan_builder.py`
- `src/yoyo/modules/planner/schemas.py`
- `src/yoyo/modules/planner/service.py`
- `src/yoyo/api/v1/planning.py`

---

### 2.3 Session lifecycle
Added explicit trip start / finish semantics.

Key work:
- `GuideSessionStatus` now includes `PENDING`, `ACTIVE`, `FINISHED`
- Added start / finish APIs
- Session context records `trip_state`, `trip_started_at`, `trip_finished_at`

Key files:
- `src/yoyo/modules/shared/enums.py`
- `src/yoyo/db/models/session.py`
- `src/yoyo/modules/session/schemas.py`
- `src/yoyo/modules/session/service.py`
- `src/yoyo/api/v1/session.py`
- `alembic/versions/0005_add_pending_guide_sessions.py`

Note:
- Lifecycle semantics now exist, but some runtime paths remain intentionally backward-compatible.

---

### 2.4 Planner route engine and Amap integration point
Added route optimization hooks and an Amap-backed route engine skeleton.

Key work:
- Added `add_stop`
- Added route optimization hook
- Added route engine / Amap client
- Planner now writes `route_meta` and `polyline`
- Degraded fallback works when no Amap key is configured

Key files:
- `src/yoyo/modules/planner/optimization_service.py`
- `src/yoyo/modules/planner/route_engine.py`
- `src/yoyo/modules/integrations/amap/client.py`
- `src/yoyo/modules/planner/service.py`
- `src/yoyo/modules/planner/schemas.py`
- `tests/test_amap_route_engine.py`

---

### 2.5 Cognitive map enrichment
The map payload now carries stop knowledge summaries and comment stats.

Key work:
- Added stop summary builder
- Map marker/current_stop now include summary/highlights/tips/source/comment stats
- Map can read route polyline from plan

Key files:
- `src/yoyo/modules/knowledge/stop_summary_builder.py`
- `src/yoyo/modules/map/schemas.py`
- `src/yoyo/modules/map/service.py`
- `src/yoyo/api/v1/map.py`

---

### 2.6 Stop comments
Added first-phase stop-level comments / review module.

Key work:
- Comment model
- Comment API create/list
- Map aggregates comment count and latest preview

Key files:
- `src/yoyo/db/models/comment.py`
- `src/yoyo/modules/comments/*`
- `src/yoyo/api/v1/comments.py`
- `alembic/versions/0006_add_poi_comments.py`

---

### 2.7 Share card aggregation
Added a dedicated share-card read model instead of reusing guide asset directly.

Key work:
- New share-card schema/service/API
- Aggregates:
  - finished session lifecycle
  - latest ready guide card content
  - itinerary / plan summary
  - cognitive map preview
  - comment statistics
- Unfinished sessions return `is_shareable = false`

Key files:
- `src/yoyo/modules/share_card/*`
- `src/yoyo/api/v1/share_card.py`
- `src/yoyo/api/router.py`
- `tests/test_share_card.py`

---

### 2.8 QA RAG path
QA now has a first-phase SQL-first + RAG fallback path.

Key work:
- Extended `HybridContext` with `rag`
- Added RAG retrieval guard and fallback router
- QA prompts now accept SQL + RAG supporting context
- QA metadata now traces retrieval strategy and backend/query state

Key files:
- `src/yoyo/modules/knowledge/fallback_router.py`
- `src/yoyo/modules/knowledge/rag_retriever.py`
- `src/yoyo/modules/knowledge/hybrid_context_builder.py`
- `src/yoyo/modules/knowledge/schemas.py`
- `src/yoyo/modules/qa/prompts.py`
- `src/yoyo/modules/qa/orchestrator.py`

---

### 2.9 LlamaIndex + pgvector backend scaffolding and ops
RAG is no longer just a prompt-level placeholder; it now has backend/readiness/index/query/admin scaffolding.

Key work:
- Added config for RAG backend
- Added LlamaIndex + pgvector dependencies
- Enabled pgvector migration
- Added document builders
- Added index service and query path
- Added index script
- Added `RAGIndexRun` model + admin APIs
- Added selective/mock-friendly rebuild request support:
  - `poi_name`
  - `doc_type`
  - `language`
  - `use_seed`
  - `limit`

Key files:
- `src/yoyo/core/config.py`
- `pyproject.toml`
- `alembic/versions/0007_enable_pgvector_extension.py`
- `src/yoyo/modules/knowledge/rag_backend.py`
- `src/yoyo/modules/knowledge/rag_documents.py`
- `src/yoyo/modules/knowledge/rag_index_service.py`
- `src/yoyo/modules/knowledge/rag_admin_service.py`
- `src/yoyo/modules/knowledge/rag_admin_schemas.py`
- `src/yoyo/api/v1/rag.py`
- `src/yoyo/db/models/rag.py`
- `alembic/versions/0008_add_rag_index_runs.py`
- `src/yoyo/scripts/build_rag_index.py`

Important status:
- QA can already prefer pgvector query results **if** backend is configured.
- Without config, the system safely degrades and still supports mock-data flows.

---

### 2.10 Guide SQL-first multi-segment content
Guide was explicitly kept SQL-first. Attraction records now store richer multi-segment guide content for guide playback/refresh.

Key work:
- Added `guide_segments_json` to attraction model
- Mock seed now generates 10+ guide segments per attraction
- Seed script writes guide segments to DB
- Guide generation now consumes multi-segment SQL content

Key files:
- `src/yoyo/db/models/attraction.py`
- `alembic/versions/0009_add_guide_segments_to_attractions.py`
- `src/yoyo/modules/knowledge/seed_postgres.py`
- `src/yoyo/scripts/seed_mock_knowledge.py`
- `src/yoyo/modules/knowledge/sql_retriever.py`
- `src/yoyo/modules/knowledge/schemas.py`
- `src/yoyo/modules/guide/content_builder.py`
- `tests/test_guide_sql_segments.py`
- `tests/test_guide_job_runtime.py`

Important design decision:
- Base attraction data and Guide SQL content currently live in the **same attraction record**, separated by fields, not by separate tables.

---

### 2.11 Unified Guide content cycle
The user decided “再讲一点 / 换一个” should be one user-facing capability, not two separate ones.

Implemented as:
- `action = cycle_content`
- backend decides how to continue within the current stop without advancing route state

Key work:
- Added guide content cycle schema/API
- Added stop-level content cursor/history in `guide_session.context_json`
- Cycle logic works on current stop only
- It does not advance `current_stop_index`
- Finished sessions reject guide content cycling

Key files:
- `src/yoyo/modules/guide/schemas.py`
- `src/yoyo/modules/guide/asset_service.py`
- `src/yoyo/api/v1/guide.py`
- `tests/test_guide_content_cycle.py`

Runtime state used:
- `stop_segment_cursor_by_stop_id`
- `played_segment_indices_by_stop_id`
- `last_refresh_action`
- `last_refresh_at`

---

### 2.12 QA structured-output expansion for trip_assistant / attraction_explain
The current session completed the next QA structured-output step for the remaining runtime intents.

Completed in this work item:
- Added structured schema definitions for `trip_assistant` and `attraction_explain`
- Switched both intents to JSON-only prompt contracts, matching the existing `translation` / `live_info` pattern
- Wired structured parsing in the QA generator for both intents
- Added orchestrator metadata projection for structured fields while keeping user-facing `answer` free-form
- Kept malformed structured output on the existing fallback/degraded paths instead of leaking bad JSON to users
- Added minimal non-blocking validator checks for route-aware trip guidance and grounded attraction explanations
- Added targeted QA tests for valid and malformed structured output for both intents
- Verified the QA suite passes after the change

Key files:
- `src/yoyo/modules/qa/schemas.py`
- `src/yoyo/modules/qa/prompts.py`
- `src/yoyo/modules/qa/generator.py`
- `src/yoyo/modules/qa/orchestrator.py`
- `src/yoyo/modules/qa/validators.py`
- `tests/test_qa.py`

Behavior now in place:
- `trip_assistant` can request and validate a JSON object with `answer`, `status`, `reason`, `route_focus`, `references_current_stop`, `references_next_stop`
- `attraction_explain` can request and validate a JSON object with `answer`, `status`, `reason`, `grounding`, `includes_history`, `includes_tips`
- if structured parsing fails, the system falls back to the existing route-aware / grounded degraded path instead of returning malformed model output

Verification completed:
- `tests/test_qa.py` -> **14 passed**

### 2.13 Completed itinerary edit protection
The current session also closed the next manual route-edit boundary item.

Completed in this work item:
- `POST /api/v1/planning/itineraries/{itinerary_id}/edits` now rejects edits when the itinerary is already marked `completed`
- the same route-edit entry now also rejects edits when runtime state shows there is no editable suffix left, even if the itinerary record has not yet been explicitly finished
- added a regression test proving that after the final stop is arrived + completed, further route edits are rejected with a clear 400 response

Key files:
- `src/yoyo/modules/planner/service.py`
- `tests/test_planner_edits.py`

Behavior now in place:
- if `current_stop_index >= len(stops)`, the route is treated as fully completed/frozen for manual editing
- completed itineraries no longer create new itinerary versions through the route-edit API

### 2.14 add_stop editable-suffix protection
The current session also tightened the remaining `add_stop` boundary for active trips.

Completed in this work item:
- `add_stop` now appends into the editable suffix rather than allowing reordering to disturb the completed route prefix
- route optimization and route engine application now preserve the frozen prefix and only reorder the editable portion when `add_stop` / `optimize_route` are used during an active trip
- added a regression test proving the current stop and completed prefix remain stable after adding a stop mid-trip

Key files:
- `src/yoyo/modules/planner/service.py`
- `tests/test_planner_edits.py`

Behavior now in place:
- for active trips, `stops[:editable_from_stop_index]` stays fixed during `add_stop`
- newly added stops are constrained to the editable portion of the route, with first-phase behavior still defaulting to append-to-tail semantics before suffix-only optimization

### 2.15 Public route-edit schema alignment
The current session also aligned the public route-edit request contract with the operations that are actually supported today.

Completed in this work item:
- tightened `RouteEditRequest` so each operation rejects unexpected operation-specific fields instead of silently accepting mixed payloads
- clarified the fullstack API contract so stable first-phase frontend operations are `replace_stop`, `remove_stop`, `reorder_stops`, `shorten_route`, and `add_stop`
- kept `optimize_route` as backend-supported but documented it as non-primary / not the recommended first-phase frontend control until product semantics are finalized more explicitly
- added a test proving `optimize_route` rejects unrelated fields such as `add_stop_name`

Key files:
- `src/yoyo/modules/planner/schemas.py`
- `docs/api-contracts-fullstack.md`
- `tests/test_planner_edits.py`

Behavior now in place:
- mixed route-edit payloads fail at request validation time instead of being loosely accepted
- the public contract now better matches current product guidance about which operations frontend should treat as stable versus provisional

### 2.16 Version-switch session/map/QA consistency tightening
The current session then completed the remaining version-switch consistency work.

Completed in this work item:
- active-session version switch now clears stale playback and guide-refresh context that may still point at the old route version
- current_position and trip lifecycle fields are left intact, while route-bound transient fields are reset conservatively
- `last_played_stop_id` is now also cleared when the current stop changes, not only when the old stop id disappears from the new route
- QA session-context loading now reuses `session current` instead of maintaining a separate raw current/next stop derivation path
- added fuller integration assertions for session/map state after version switch, including current/next stop, completed/editable boundaries, markers, polyline, and cleared transient context fields

Key files:
- `src/yoyo/modules/planner/service.py`
- `src/yoyo/modules/qa/orchestrator.py`
- `tests/test_a_validation_suite.py`
- `tests/test_qa.py`

Behavior now in place:
- route edit version switches no longer carry over stale `last_played_stop_index`, `last_playback_action`, `last_playback_updated_at`, `stop_segment_cursor_by_stop_id`, `played_segment_indices_by_stop_id`, `last_refresh_action`, or `last_refresh_at`
- active session context is closer to a single reliable source of truth before session/map/QA consumers read the new version
- QA now follows the same `current_stop` / `next_stop` / `playback_state` route context as `session current`, including terminal-state handling
- map payload assertions now verify that version-switch results propagate consistently to markers, polyline, navigation summary, and top-level current/next stop fields

Verification completed:
- `tests/test_a_validation_suite.py` + `tests/test_qa.py` -> **28 passed**

### 2.17 Guide structured-output validation
The current session then completed the next runtime Guide hardening step.

Completed in this work item:
- added internal structured schema for the Guide LLM bundle
- Guide generator now validates parsed JSON against the Guide bundle schema instead of only doing weak JSON parsing
- guide generation job now only passes validated LLM bundle output into `build_guide_bundle`, otherwise it falls back to the existing SQL/profile builder path while preserving generation metadata
- added focused runtime tests for valid and malformed Guide bundle output

Key files:
- `src/yoyo/modules/guide/schemas.py`
- `src/yoyo/modules/guide/generator.py`
- `src/yoyo/jobs/tasks/guide_generation.py`
- `tests/test_guide_job_runtime.py`

Behavior now in place:
- Guide runtime can now distinguish between parseable-but-invalid LLM output and validated structured bundle output
- malformed Guide bundle output no longer flows directly into the builder merge path as trusted LLM content
- the existing builder fallback remains the primary degraded path, so guide jobs can still succeed with stable bundle structure when LLM structured validation fails
- generation metadata now records whether the Guide bundle passed structured validation

Verification completed:
- `tests/test_guide_job_runtime.py` -> **2 passed**

### 2.18 Malformed-output and degraded-wording hardening
The current session then completed the next cross-runtime output-hardening step.

### 2.19 Test-planning and QA next-phase direction
A new review pass clarified that the project is now in a pre-release hardening stage rather than an initial build stage.

Key conclusions:
- The main product surface is already implemented across onboarding, planning, session/GPS/map, guide jobs/assets/content, comments/share-card, QA, and RAG admin.
- The next testing focus should be a full feature-to-test matrix covering unit, integration, smoke, degraded-mode, and E2E chain validation rather than only adding more ad hoc regression cases.
- QA remains the highest-risk module for the next phase, especially intent-boundary stability (`manual_route_edit_redirect`, `out_of_scope`, deep attraction explain vs trip assistant/live_info boundaries), translation quality/coverage, and fallback/degraded consistency.
- The intended routing direction remains translator-first -> high-precision rules -> small-model fallback classifier -> downstream pipelines, but the unified translation-preprocessor path is still ahead of full implementation and should become a dedicated backend work item.
- Translation is implemented as a QA intent today, but the next backend phase should separately address translator service readiness, route-time preprocessing, observability, and benchmark coverage.

Recommended next-phase backend priorities:
1. Build the complete feature test matrix and make it the release gate.
2. Strengthen QA routing and translation with dedicated routing-only and E2E benchmarks.
3. Add a unified translation-preprocessor layer before intent routing.
4. Expand degraded/fault-injection/performance verification for external dependencies (RAG, live_info, TTS, worker consistency).

Completed in this work item:
- added a shared lightweight sanitizer for user-visible LLM text
- QA structured answers now sanitize wrapper/fence noise before they are accepted as valid output
- Guide bundle merge now sanitizes intro/outro/card/stop-level text fields before using LLM values
- Guide JSON extraction no longer uses the high-risk first/last-brace rescue path and instead only falls back to fenced-object extraction
- QA degraded/unavailable/redirect wording was rewritten to sound more productized and less like internal system state
- Guide default intro/outro/narration/tip fallback wording was also tightened to remove template and internal-control phrasing
- added focused malformed post-processing and degraded-wording tests for QA and Guide runtime paths

Key files:
- `src/yoyo/modules/shared_text_sanitizer.py`
- `src/yoyo/modules/qa/generator.py`
- `src/yoyo/modules/qa/formatters.py`
- `src/yoyo/modules/qa/live_info.py`
- `src/yoyo/modules/qa/orchestrator.py`
- `src/yoyo/modules/guide/generator.py`
- `src/yoyo/modules/guide/content_builder.py`
- `tests/test_qa.py`
- `tests/test_guide_job_runtime.py`

Behavior now in place:
- schema-valid but wrapper-noisy QA answers are treated as malformed and fall back instead of leaking raw noise to users
- Guide bundle text fields now strip common wrapper/fence noise before merge, and empty/dirty values naturally fall back to SQL/profile builder text
- Guide runtime no longer accepts arbitrary prose by slicing from the first `{` to the last `}`
- fenced JSON remains supported as the only relaxed JSON extraction path for structured-output recovery
- degraded/unavailable/redirect responses now avoid exposing internal state phrases like `temporarily degraded`, `current product phase`, `route/context data is refreshed`, or template-style fallback wording

Verification completed:
- `tests/test_qa.py` + `tests/test_guide_job_runtime.py` -> **22 passed**

### 2.19 Module-level failure-mode coverage
The current session then completed the next failure/degradation coverage pass.

Completed in this work item:
- added QA runtime failure tests for translation and trip_assistant when runtime generation returns provider errors
- added Guide job failure-path tests for missing itinerary version and runtime LLM error fallback
- added live_search provider config coverage for unsupported provider selection
- added knowledge-level missing-real-data coverage and RAG fallback coverage for no-positive-chunk query results
- verified the current runtime hardening stack now has module-level regression protection across QA, Guide, live_info/live_search, knowledge retrieval, and runtime-LLM post-processing

Key files:
- `tests/test_qa.py`
- `tests/test_guide_job_runtime.py`
- `tests/test_live_search.py`
- `tests/test_knowledge_retrievers.py`
- `tests/test_rag_query.py`

Behavior now protected by tests:
- missing provider config
- LLM failure
- malformed structured output
- missing real data
- upstream provider errors

Verification completed:
- `tests/test_qa.py` + `tests/test_guide_job_runtime.py` + `tests/test_live_search.py` + `tests/test_knowledge_retrievers.py` + `tests/test_rag_query.py` -> **37 passed**

### 2.20 End-to-end integration flow expansion
The current session then completed the end-to-end regression coverage around the core travel/runtime flows.

Completed in this work item:
- strengthened the main happy-path integration flow so it now covers itinerary creation, automatic guide job enqueue, guide generation job execution, asset readiness, GPS arrival, playback progression, and synchronized session/map state updates in one test
- extended the same integration flow to include a manual route edit after playback progression, and then verified version switch, session remap, map consistency, and stale context cleanup in the same chain
- added dedicated session-aware QA integration coverage for three state-change patterns: GPS arrival (`triggered`), playback completion (current stop advances), and route version switch (answer text and metadata both follow the new current stop)
- this closes all three `6.3` integration-flow items without introducing new runtime behavior changes

Key files:
- `tests/test_a_validation_suite.py`
- `tests/test_guide_playback.py`
- `tests/test_qa.py`

Behavior now protected by integration tests:
- itinerary creation automatically enqueues a guide generation job and the generated asset can be consumed by the active session
- GPS/playback state changes propagate to `session current`, `map session`, and session-aware QA consistently
- manual route edit triggers version switch, session remap, map/session consistency, and QA route-context updates in end-to-end coverage

Verification completed:
- `tests/test_a_validation_suite.py` + `tests/test_guide_playback.py` + `tests/test_qa.py` -> **35 passed**

### 2.21 Guide 4.3 product decisions and implementation
The current session also completed the immediate Guide 4.3 decisions and implementation pass.

Decisions now recorded:
- frontend does not need a visible remaining-content count for this phase; `more_content_available` remains the user-facing signal
- Guide audio should move from placeholder semantics to a real TTS/media flow
- the user plans to provide the TTS API key later
- latency matters: if one attraction can expose around 10 explainable segments, the system should avoid synchronous full-batch generation on every `cycle_content` click and instead prioritize low-latency current-stop/current-batch generation with asynchronous completion for the rest

Completed in this work item:
- `cycle_content` selection now uses user profile signals (`answer_length_preference`, `interests`, `guide_style_preference`) to rank and choose stop segments instead of taking a fixed prefix only
- Guide audio contract now moves from `not_generated` placeholder semantics to a real TTS-oriented shape with provider/model/voice settings and per-segment audio status/url fields
- `cycle_content` now returns `audio_segments` for the selected batch and uses real TTS calls when an API key is configured, while staying low-latency by generating only the current batch on demand
- when no TTS API key is configured, audio is marked `unavailable` explicitly instead of implying a future placeholder generation state

Key files:
- `src/yoyo/core/config.py`
- `src/yoyo/modules/guide/content_builder.py`
- `src/yoyo/modules/guide/asset_service.py`
- `src/yoyo/modules/guide/schemas.py`
- `src/yoyo/modules/guide/tts.py`
- `src/yoyo/jobs/tasks/guide_generation.py`
- `tests/test_guide_content_cycle.py`
- `tests/test_guide_job_runtime.py`
- `tests/test_guide_playback.py`

Behavior now in place:
- content rotation is more personalized while keeping the current single-action `cycle_content` UX
- frontend still only needs `more_content_available`, not a visible remaining counter
- audio generation is now modeled as real batch-level TTS work rather than a frozen placeholder, with latency-aware on-demand generation for the currently returned batch

Verification completed:
- `tests/test_guide_content_cycle.py` + `tests/test_guide_job_runtime.py` + `tests/test_guide_playback.py` -> **11 passed**

### 2.22 QA RAG productionization semantics pass
The current session then completed the code/test semantics pass for QA RAG productionization.

Completed in this work item:
- strengthened RAG backend readiness semantics so embedding-key absence is treated as a backend misconfiguration rather than leaving `backend_ready` overly optimistic
- aligned index/query result payloads around clearer `availability`, `status`, and `reason` semantics
- hardened admin rebuild/index-run payloads so rebuild runs explicitly describe backend status, operation type, execution mode, and final result
- extended QA metadata so attraction/RAG answers expose top-level retrieval state (`rag_retrieval_mode`, `rag_backend_ready`, `rag_backend_reason`, `rag_query_status`, `rag_query_reason`) instead of forcing callers to inspect chunk-level internals only
- added/updated regression coverage for backend readiness, admin run payloads, RAG query fallback, knowledge no-data behavior, and QA top-level RAG metadata

Key files:
- `src/yoyo/modules/knowledge/rag_backend.py`
- `src/yoyo/modules/knowledge/rag_index_service.py`
- `src/yoyo/modules/knowledge/rag_admin_service.py`
- `src/yoyo/modules/knowledge/rag_admin_schemas.py`
- `src/yoyo/modules/knowledge/rag_retriever.py`
- `src/yoyo/modules/qa/orchestrator.py`
- `tests/test_rag_backend.py`
- `tests/test_rag_admin.py`
- `tests/test_rag_query.py`
- `tests/test_knowledge_retrievers.py`
- `tests/test_qa.py`
- `docs/api-contracts-fullstack.md`

Behavior now in place:
- configured vs degraded RAG states are easier to reason about from both admin APIs and QA metadata
- admin rebuild responses now better explain whether work was skipped, succeeded, or failed, and why
- QA answers that use RAG now carry top-level retrieval state suitable for frontend/debug consumers
- the remaining open gap is real-environment validation against a configured pgvector + embedding backend, not the scaffold semantics themselves

Verification completed:
- `tests/test_rag_backend.py` + `tests/test_rag_admin.py` + `tests/test_rag_query.py` + `tests/test_knowledge_retrievers.py` + `tests/test_qa.py` -> **36 passed**

### 2.23 RAG/TTS real-environment config checklist
The current session also added an explicit configuration checklist for the next real-environment validation step.

Completed in this work item:
- documented the exact `.env` values needed for real pgvector + embedding validation
- documented the exact `.env` values needed for real TTS validation
- recorded the minimal validation steps for both RAG and Guide audio flows
- linked the preparation checklist from README so the next pass can move directly from config to execution

Key files:
- `docs/b-stack-preparation-checklist.md`
- `README.md`

Behavioral impact:
- no runtime behavior changed in this step; it only makes the next real-environment validation pass more explicit and reproducible


Remaining follow-up after this step:
- benchmark runs still need fail-fast or invalid-marking behavior when required API keys are missing

### 2.24 Real-environment RAG and Qwen TTS validation
The current session then completed the remaining real-environment validation pass.

Completed in this work item:
- switched local PostgreSQL runtime to a pgvector-capable container image so the `vector` extension could actually be created
- fixed the PostgreSQL enum migration in `0005_add_pending_guide_sessions.py` so a fresh local upgrade can proceed without dropping enum types that are still referenced by live columns
- fixed the llama-index pgvector integration so the installed `PGVectorStore.from_params(...)` signature is used correctly in the real runtime
- completed a real rebuild/latest validation cycle with `status = succeeded` and `availability = ready`
- completed a real deep QA validation path using a real created guide session, confirming QA metadata now reports `retrieval_strategy = sql_then_rag`, `rag_backend_ready = true`, and `rag_query_status = ok`
- switched Guide TTS from the blocked ElevenLabs attempt to DashScope Qwen TTS and verified real project-level synthesis output through `src/yoyo/modules/guide/tts.py`

Key files:
- `docker-compose.yml`
- `alembic/versions/0005_add_pending_guide_sessions.py`
- `src/yoyo/modules/knowledge/rag_index_service.py`
- `src/yoyo/modules/guide/tts.py`
- `src/yoyo/core/config.py`
- `pyproject.toml`
- `README.md`
- `docs/b-stack-preparation-checklist.md`
- `docs/todo.md`

Behavior now in place:
- local development can now use a pgvector-enabled Postgres image instead of failing at extension creation time
- fresh migrations no longer fail when `guide_session_status` / `itinerary_status` enums are expanded during upgrade
- RAG rebuild/latest/admin semantics now hold in a real configured environment, not only in tests
- deep attraction QA requests can now execute against a real indexed pgvector backend and return `sql_then_rag` metadata with `rag_query_status = ok`
- Guide TTS now uses DashScope Qwen TTS and can produce a real generated audio artifact from the project runtime path

---

### 2.25 QA routing contract consolidation and multilingual routing direction
The current session then completed the next QA routing-contract consolidation pass.

Completed in this work item:
- narrowed `domain_guard` so it now behaves as a hard-deny-first coarse gate instead of participating in fine intent routing
- expanded `intent_router` into a fuller routing result contract with `intent`, `margin`, `needs_fallback`, `fallback_reason`, `runner_up_intent`, `boundary_topic`, and `out_of_scope_subtype`
- promoted `manual_route_edit_redirect` to a first-class intent instead of leaving route-edit redirect as a `trip_assistant` sub-branch in the orchestrator
- aligned weather / traffic / crowd handling so they now land in `out_of_scope` boundary subtypes while still returning productized boundary-redirect wording
- added focused routing regressions for hard-deny, route-edit redirect, follow-up inheritance, translation-vs-attraction conflict, and fallback-trigger signals
- confirmed the current routing strategy for Southeast Asia should use direct routing by default, with translate-to-English only as a low-confidence fallback path

Key files:
- `src/yoyo/modules/qa/domain_guard.py`
- `src/yoyo/modules/qa/intent_router.py`
- `src/yoyo/modules/qa/orchestrator.py`
- `src/yoyo/modules/qa/schemas.py`
- `src/yoyo/modules/qa/skill_registry.py`
- `src/yoyo/modules/qa/validators.py`
- `tests/test_qa_routing_regressions.py`
- `tests/test_qa.py`
- `tests/test_planner_handoff.py`

Behavior now in place:
- route-edit queries now return top-level `intent = manual_route_edit_redirect`
- boundary live topics now return top-level `intent = out_of_scope` plus `boundary_redirect`, `boundary_topic`, and `out_of_scope_subtype`
- router metadata is now ready for a future selective small-model fallback instead of forcing a full model-router rewrite first
- current multilingual routing direction is: Thai, Vietnamese, Indonesian, Malay, and Filipino first; direct routing by default; translate-to-English only when low-confidence signals require it

Verification completed:
- `tests/test_qa_routing_regressions.py` -> **13 passed**
- `tests/test_qa.py` + `tests/test_planner_handoff.py` -> **25 passed**

### 2.26 Selective QA router fallback hook
The current session then completed the first selective small-model router fallback integration.

### 2.27 Intent-recognition architecture decision update
A later product discussion then updated the intended routing architecture.

Decisions now recorded:
- multilingual queries should first pass through a translator and be normalized into Chinese before intent recognition
- the intent-recognition module should use **rules + small-model classifier** rather than pure rules or pure vector similarity
- the classifier should feed different downstream pipelines such as SQL, RAG, live search, redirect, and reject handlers
- rules remain important, but only as high-precision guardrails for hard deny / boundary / redirect / strong signals rather than the main semantic classifier

Documentation impact:
- `docs/qa-routing-strategy.md` now reflects the translator-first architecture
- `docs/routing-model-selection-plan.md` now treats the model-selection problem as Chinese classifier selection under translation normalization, rather than multilingual direct routing by default
- `docs/todo.md` and `README.md` now point to the same updated direction

Completed in this work item:
- added QA router fallback settings to runtime config
- added a dedicated `router_fallback.py` path that uses the shared runtime LLM stack for classification-only routing fallback
- kept the fallback scope intentionally narrow: it is only invoked when the rule router returns `needs_fallback = true` and the feature flag is enabled
- kept fallback output constrained to the existing routing label set instead of allowing free-form answer generation
- added regression tests proving fallback can override the rule result when enabled and is skipped entirely when disabled

Key files:
- `src/yoyo/core/config.py`
- `src/yoyo/modules/qa/router_fallback.py`
- `src/yoyo/modules/qa/orchestrator.py`
- `src/yoyo/modules/qa/schemas.py`
- `tests/test_qa.py`

Behavior now in place:
- selective routing fallback is now technically wired behind `qa_router_fallback_enabled`
- default configured fallback model target is `openai/gpt-5.4-nano`
- current fallback scope remains classification-only and does not replace the main QA answer generation path
- this keeps the system aligned with the intended architecture: rules first, model only for ambiguous routing cases

Verification completed:
- `tests/test_qa.py` + `tests/test_qa_routing_regressions.py` + `tests/test_planner_handoff.py` -> **40 passed**

### 2.28 Router-only routing benchmark and candidate sweep
The current session then completed the first dedicated routing benchmark pass for intent-classification evaluation.

Completed in this work item:
- added a router-only eval module at `src/yoyo/evals/routing.py` so benchmark scripts can directly reuse `evaluate_domain_support`, `score_intent`, and `resolve_router_fallback` without going through full `/api/v1/qa/ask`
- added `evals/datasets/routing_benchmark_cases.json` as the first dedicated routing dataset covering attraction explain, live-info conflicts, trip guidance, route-edit redirect, out-of-scope boundary topics, translation, and short follow-up cases
- added `evals/run_routing_benchmark.py` for single-candidate runs and `evals/run_routing_candidate_sweep.py` plus `evals/routing_candidates.yaml` for rules-only vs fallback-model sweeps
- updated `router_fallback.py` so benchmark runs can explicitly override fallback provider/model without changing the runtime default config path
- extended `evals/export_excel.py` with `routing_cases` and `routing_summary` sheets so router-only results can be exported alongside existing eval artifacts
- normalized the active route-edit benchmark part file away from the old `planner_handoff` label to the current `manual_route_edit_redirect` label

Behavior now in place:
- the project now has a dedicated router-only benchmark path for comparing rules-only and rules-plus-fallback routing behavior, latency, and cost before changing the production QA chain
- translator-first remains a documentation-level target and is still not wired into the runtime routing chain; the new benchmark measures the actual implemented chain instead
- current smoke results show the rules-only baseline at 11/14 intent-correct cases, while the `openai/gpt-5.4-nano` fallback candidate improved the same smoke set to 13/14 with better conflict handling

Verification completed:
- `tests/test_routing_benchmark.py` -> **4 passed**
- `tests/test_qa_routing_regressions.py` -> **13 passed**
- `PYTHONPATH=src python3 evals/run_routing_benchmark.py --dataset evals/datasets/routing_benchmark_cases.json --candidate-name rules_only ...` -> smoke passed
- `PYTHONPATH=src python3 evals/run_routing_candidate_sweep.py --dataset evals/datasets/routing_benchmark_cases.json --candidates evals/routing_candidates.yaml ...` -> smoke passed

### 2.29 First routing lexicon-expansion pass
The current session then completed the first phrase-level lexicon expansion for the rules router under the new benchmark setup.

Completed in this work item:
- expanded `src/yoyo/modules/qa/intent_router.py` with higher-value phrase variants for `translation`, `manual_route_edit_redirect`, `trip_assistant`, and `attraction_explain`
- intentionally kept the rules layer looser by avoiding new high-risk single-token triggers and by preserving more ambiguous cases for `needs_fallback` instead of forcing overconfident rule-only decisions
- added paired regression cases in `tests/test_qa_routing_regressions.py` for positive-hit vs overcatch controls such as translation phrase variants, route-edit variants, trip-assistant variants, and attraction-explain variants
- expanded `evals/datasets/routing_benchmark_cases.json` with matching benchmark pairs so lexicon gains can be measured against nearby false-positive risks instead of only on new positive examples

Behavior now in place:
- phrase variants like `把这句改成中文`, `把景山去掉，路线轻松点`, `故宫之后去哪`, and `天坛有什么特别` now route through the intended intent classes under the rules router
- obvious same-day live-info cases still keep `live_info` priority, while some ambiguous cases remain intentionally eligible for fallback rather than being hard-forced by rules
- the current benchmark now better reflects the user preference that the rule layer should prefer recall and low misclassification over aggressive self-confidence

Verification completed:
- `tests/test_qa_routing_regressions.py` + `tests/test_routing_benchmark.py` -> **25 passed**
- `PYTHONPATH=src python3 evals/run_routing_benchmark.py --dataset evals/datasets/routing_benchmark_cases.json --candidate-name rules_only_expanded_lexicon ...` -> passed
- updated rules-only benchmark summary: `evals/results/routing_rules_only_expanded_summary.json`
  - total cases: 22
  - intent-correct: 18
  - accuracy: 0.8182
  - boundary accuracy: 1.0
  - manual route-edit accuracy: 0.6667

### 2.30 100-case routing benchmark pass
The current session then added and ran a larger routing benchmark covering the whole intent-recognition module.

### 2.31 Guide real-chain 404 recheck
A later recheck of the real guide asset/content chain confirmed that the earlier `guide/content` 404 was not a persistent backend bug in the current repo state.

Completed in this work item:
- re-ran a full local real-environment chain with API + worker both running: itinerary create -> session create -> start -> asset poll -> content -> finish -> share-card
- verified that `GET /api/v1/guide/asset/{guide_session_id}` returned `asset_status = missing` for the first few polls and then switched to `ready` once the worker-finished guide job satisfied the `SUCCEEDED + READY` lookup condition
- verified that `POST /api/v1/guide/content/{guide_session_id}` succeeded once the asset reached `ready`, returning text segments plus `audio_segments = ready`
- confirmed from current code that asset lookup is keyed by `guide_session.itinerary_version_id` and only considers the latest job meeting `status == SUCCEEDED` and `asset_status == READY`

Behavior now clarified:
- the temporary `200 + asset_status = missing` response is the expected pre-ready state while the guide generation job is still in flight
- calling `guide/content` during that window can legitimately return `404 guide content not available`, because content requires the active asset `result` to exist already
- the real validation rule should therefore be: worker running -> poll asset until `ready` -> then call content, rather than treating the first `missing/404` as a product failure

Completed in this work item:
- added `evals/datasets/routing_benchmark_100_cases.json` with 100 labeled router-only cases covering all six intents, conflict-heavy phrasing, short follow-ups, and unrelated/non-travel queries that should be blocked or routed out
- ran the full routing module on the 100-case set with `rules_only_100`
- ran the same 100-case set with `rules_plus_fallback_gpt54nano_100` to measure how much the looser rule layer benefits from model fallback on ambiguous queries

Behavior now measured:
- `rules_only_100` reached 75 / 100 intent-correct cases, for overall accuracy `0.75`
- `rules_plus_fallback_gpt54nano_100` reached 85 / 100 intent-correct cases, for overall accuracy `0.85`
- fallback improved `needs_fallback_accuracy`, `manual_route_edit_accuracy`, and overall attraction-explain handling, while boundary accuracy remained a visible weak area for both settings in this larger benchmark

Verification completed:
- dataset: `evals/datasets/routing_benchmark_100_cases.json`
- rules-only summary: `evals/results/routing_rules_only_100_summary.json`
- rules+fallback summary: `evals/results/routing_rules_plus_fallback_gpt54nano_100_summary.json`
- exported workbook: `evals/results/routing_benchmark_100_results.xlsx`
- fallback usage on the 100-case run: 31 cases
- average latency for fallback-used cases: 2610.95 ms
- overall average latency for the full rules+fallback run: 809.45 ms

## 3. Documentation updated in this session

Updated repeatedly through the session:
- `README.md`
- `docs/architecture.md`
- `docs/contracts.md`
- `docs/todo.md`
- `docs/todo.zh-CN.md`
- `docs/b-stack-implementation-overview.md`

These docs now reflect:
- cognitive map positioning
- Amap as route engine only
- stop comments
- share card
- QA SQL-first + RAG fallback
- RAG admin/reindex path
- Guide SQL-first multi-segment content
- unified guide content cycling

---

## 4. Tests currently passing

The following suites were run successfully at the end of this session:
- `tests/test_onboarding_flow.py`
- `tests/test_planning_entry_modes.py`
- `tests/test_session_lifecycle.py`
- `tests/test_planner_edits.py`
- `tests/test_map_gps.py`
- `tests/test_comments.py`
- `tests/test_share_card.py`
- `tests/test_a_validation_suite.py`
- `tests/test_amap_route_engine.py`
- `tests/test_qa.py`
- `tests/test_rag_backend.py`
- `tests/test_rag_indexing.py`
- `tests/test_rag_query.py`
- `tests/test_rag_admin.py`
- `tests/test_guide_asset_latest.py`
- `tests/test_guide_job_runtime.py`
- `tests/test_guide_sql_segments.py`
- `tests/test_guide_content_cycle.py`

Current result at the end of the session:
- `tests/test_guide_content_cycle.py` + `tests/test_guide_playback.py` -> **6 passed**
- `tests/test_rag_backend.py` + `tests/test_rag_query.py` -> **6 passed**
- `tests/test_runtime_openrouter.py` + `tests/test_rag_backend.py` + `tests/test_guide_content_cycle.py` + `tests/test_guide_playback.py` + `tests/test_rag_query.py` -> **13 passed**

---

## 5. Current backend shape after this session

### Guide
- SQL-first
- no Guide-side RAG in main path
- richer multi-segment SQL content
- unified `cycle_content` action for short-form audio-friendly content loops

### QA
- SQL-first + first-phase RAG fallback
- can prefer pgvector/LlamaIndex query path when configured
- can still run in degraded/mock mode before full backend config

### Map
- cognitive map
- no dependency on a real rendered map
- route polyline from route engine
- stop summaries + comment stats

### Share / social
- stop comments
- share-card read model for finished trips

### Ops / admin
- RAG index run records
- rebuild + latest status APIs
- selective/mock-friendly rebuild requests

---

## 6. Recommended next TODO

### Highest-priority remaining items
1. **Harden manual route editing with runtime-aware constraints**
   - keep route edits manual only
   - freeze completed stops
   - keep the current stop editable
   - expose editability boundaries to session/map payloads

3. **Productionize the LlamaIndex + pgvector QA RAG path**
   - complete backend-enabled retrieval in a real configured environment
   - validate embedding + pgvector end-to-end
   - harden ingestion lifecycle
   - support operational indexing / rebuild strategy

### Reasonable next concrete implementation step
If continuing from this session, the most natural next step is:

> keep tightening manual route editing semantics, especially `add_stop`, completed-itinerary protection, and version-switch consistency across session/map/frontend state.

This keeps the runtime route-edit boundary aligned before deeper QA RAG or Guide productionization work continues.

---

## 7. Important decisions to preserve

- The map is a **cognitive map**, not a real map product.
- Amap is only a **route engine**, not the rendered map.
- Guide should remain **SQL-first**, not Guide-RAG.
- QA can continue toward **SQL-first + RAG fallback**.
- The user-facing Guide refresh behavior should remain **one unified capability**, not separate “再讲一点” and “换一个” buttons.
- Route editing is currently **manual only**; QA is not the route-edit entry point in the active product path.
- When the final stop is completed, the route should be treated as fully completed/frozen with no editable stops remaining.
- QA fallback behavior has been tightened for the current phase:
  - `translation` now returns an explicit degraded response instead of phrase-map fallback when runtime generation is unavailable
  - `trip_assistant` fallback now stays route-aware and action-oriented rather than sounding like a static template
  - `live_info` now returns explicit unavailable/degraded wording and metadata when provider config or upstream requests fail
  - `attraction_explain` no longer tells users to wait for the SQL knowledge store; when grounded detail is insufficient it now returns a clearer degraded response
- Attraction/profile retrieval now distinguishes better between production-oriented and local/test fallback behavior:
  - mock seed fallback remains allowed in local/test-oriented paths
  - production-oriented behavior should no longer silently mix in mock seed records when fallback is disabled
  - profile fallback still degrades explicitly to `derived_default` rather than pretending a mock profile is real data
- The next QA productionization step should use a **minimal-impact structured-output design**:
  - keep `answer` as free-form user-facing text
  - add small internal fields such as `status`, `reason`, and intent-specific validation fields
  - start with `translation`, `live_info`, `trip_assistant`, and `attraction_explain`
  - use rule/schema validation first rather than semantic judge-style validation in the main runtime path
- The first structured-output step is now in place for QA:
  - `translation` can request and validate a JSON object with `answer`, `status`, `reason`, `mode`
  - `live_info` can request and validate a JSON object with `answer`, `status`, `reason`, `not_confirmed`, `confidence`
  - if structured parsing fails, runtime falls back to the existing degraded path instead of leaking malformed output
