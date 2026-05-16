# Yoyo 第二阶段总结

这份文档是当前阶段的**活动总结与续接摘要**。

请结合以下文档一起阅读：
1. `AGENTS.md`
2. `README.md`
3. `docs/README.md`
4. `docs/todo-phase-2.md`
5. `docs/dev-retrospective.md`

不要再把 `docs/current-session-summary.md` 当作默认当前总结；那个文件现在只作为历史 session 日志保留。
`docs/dev-retrospective.md` 现在作为开发问题复盘入口保留，只在有策略变化、明确问题归因、回归或可复用解决方案时追加记录。

当前自动记录规则：每次发生实质开发、调试、benchmark、规则调整或架构决策，都要在同一轮同步更新 `docs/phase-2-summary.md` 和 `docs/todo-phase-2.md`；`docs/dev-retrospective.md` 只在有策略变化、明确问题归因、回归、可复用解决方案或维护规则变化时更新，不为每次小测试单独追加。如果文档入口或阅读路径变化，还要同步 `README.md` 和 `docs/README.md`。

## 1. 第二阶段的目标
项目已经完成了最初的后端搭建和第一阶段 hardening。
当前阶段的重点转为：
- 重置文档入口，让后续 session 能直接落到当前活动文档
- 把当前活动文档与历史日志分开
- 为现有产品面补上一份功能级测试说明文档
- 为下一轮 QA 改进做准备，尤其是 routing accuracy、translation readiness 和 release-oriented verification

## 2. 当前项目状态
当前已经落地的产品能力包括：
- guest quick entry 与 questionnaire
- planning 与 itinerary versioning
- manual route editing
- session lifecycle、GPS、playback 与 cognitive map
- guide jobs、guide assets、cycle content 与 TTS 流程
- comments 与 share-card
- 带 SQL-first + RAG fallback 语义的 QA ask
- RAG admin 的 rebuild / latest 流程

这意味着当前主要工作已经不再是“从零补齐核心模块”，而更接近：
- 文档重组
- 测试整理
- QA 质量提升
- 发布前加固

## 3. 当前优先级
### P0
- 切换默认工作文档到第二阶段文档集
- 建立功能级测试说明文档
- 把旧 todo / 旧 session summary 标记为 archive / history
- 让次级入口文档与新的阅读顺序保持一致

### P0 当前状态
- 第二阶段活动文档集已经创建：
  - `docs/todo-phase-2.md`
  - `docs/phase-2-summary.md`
  - `docs/feature-test-guide.md`
- `AGENTS.md` 与 `README.md` 已经优先指向第二阶段工作集
- 2026-05-16 已继续做一轮文档入口治理：根 `README.md` 收敛为短总入口，新增 `docs/README.md`、`docs/qa/README.md`、`docs/qa/routing/README.md`、`docs/qa/intent-rules/README.md`、`docs/qa/navigation/README.md`、`docs/evals/README.md`、`docs/testing/README.md` 等专题索引。当前先不移动原始文档，避免破坏旧链接；后续可按索引目录逐步物理迁移。
- 2026-05-16 已明确保留自动记录方式：每轮实质开发 / 调试 / benchmark / 规则调整都要同步刷新 `phase-2-summary` 和 `todo-phase-2`；`dev-retrospective` 只记录策略变化、问题归因和解决方案，普通小测试不写。
- `docs/todo.md` 与 `docs/current-session-summary.md` 已被明确标记为 archive / history 文档
- 次级入口文档现在也已经引用第二阶段工作集和功能级测试说明文档
- 当前给用户阅读的第二阶段文档已切换为中文表达，必要术语保留英文

### P1
- 定义下一轮 QA 改进计划
- 把 translation readiness 单独作为后端工作项
- 准备下一轮 test matrix 和面向发布的验证轮次

### 续接简短交接（2026-05-07）
- 共享 translator、东南亚小语种扩展、translation benchmark schema、数据集矩阵和 Excel 导出已经完成。
- HY-MT 与 XFYun ITS 的真实 benchmark 已完成，XFYun provider_error 也已修复。
- 当前正式决策已经收口：后续默认翻译器使用 `xfyun_its` / `its`，HY-MT 仅保留为历史 benchmark 对照，不再作为正式 translator 方案。
- 默认配置已切到：`src/yoyo/core/config.py`、`.env`、`.env.example`。
- 中文 benchmark 总结文档已落地：`docs/translation-benchmark-summary-2026-05-07.md`。
- 如果开新 session，先按默认顺序读：`AGENTS.md` -> `README.md` -> `docs/README.md` -> `docs/todo-phase-2.md` -> `docs/phase-2-summary.md`。
- 当前最自然的下一步，不是继续改 translator 主体，而是继续 `docs/todo-phase-2.md` 里还没完成的 translation P1：
  - `4.3` 规划 translation 相关验证维度
  - 重点收口：纯 translation 质量、translation 后 routing 稳定性、provider 缺失 / degraded 行为、bilingual translation 场景质量

### P1 建议先做的顺序
1. 先把 `docs/feature-test-guide.md` 整理成 test matrix 基础表
2. 再把 QA 改进范围拆成 routing / translation / degraded / E2E 四个工作包
3. 然后明确下一轮发布前验证的执行清单、结果记录方式和 blocking 判定口径

## 4. 下一阶段的 QA 重点

> 状态说明（2026-05-04）：以下 QA 工作包当前作为已识别输入保留，但暂不继续推进。用户计划先完成面向东南亚小语种的语言改动，再由用户本人单独设计并执行 QA 测试。

下一轮 QA 改进应继续保持以下方向明确：
- routing 继续朝这个结构收敛：
  - translator preprocessor
  - high-precision rule layer
  - small-model fallback classifier
  - downstream handlers
- translation 需要同时被视为：
  - 一个面向用户的 QA 能力
  - 一个 routing 预处理能力的 readiness 问题
- 结合最新真实环境复核后，当前 QA 风险最高的区域更准确地变为：
  - `trip_assistant` 中文口语问法
  - live_info 与 attraction-explain 的混合问句边界
  - session-aware follow-up 的 retrieval 连续性
  - translation metadata / observability 一致性
- 已在真实环境获得较稳定验证的区域包括：
  - `manual_route_edit_redirect`
  - `weather_info`
  - `navigation_text`
  - traffic / crowd 边界题
  - hard out-of-scope 拒答

### 4.1 当前建议的 QA 工作包

#### 工作包 A：routing 方案收口
目标：先把下一轮改动范围讲清楚，再决定具体实现切口。
- 明确保持目标结构：translator preprocessor -> high-precision rules -> small-model fallback classifier -> downstream handlers
- 明确本轮优先做“范围收口与验证设计”，而不是直接重写整条 QA 流程
- 把 rules only、rules + fallback classifier、translate-then-route 作为下一轮主要对比方案

#### 工作包 B：routing accuracy
目标：优先处理当前最弱的 intent 和边界题。
- 最新真实环境复核结果：
  - `manual_route_edit_redirect` 已比历史 benchmark 结论更稳定
  - weather / traffic / crowd 边界题当前真实行为稳定
  - `trip_assistant` 中文口语问法（如“下一个去哪里？”）仍会误落到 `out_of_scope`
  - `故宫今天开放吗，顺便讲讲值不值得去` 这类 mixed query 仍会漂向 `attraction_explain`
- 重点盯住：
  - attraction-explain 与 trip-assistant 边界
  - live_info 与边界题区分
  - live_info 与 attraction-explain 混合题
- 2026-05-08 已完成首轮 zh-hard v1 rerun：`rules_only=0.5694`，`qwen-flash=0.8611`，`qwen3.5-flash-2026-02-23=0.5694`，`qwen-turbo=0.8889`。当时结论是：`qwen-turbo` 最优，`qwen-flash` 次优；`qwen3.5-flash-2026-02-23` 在该轮 fallback 上未产生有效覆盖。
- 2026-05-09 在完成 benchmark/runtime 对齐、translator routing prompt 收紧、translation/live mixed-intent fallback、以及 route-edit negation 收口后，已补跑同口径 keyed v2 rerun：`rules_only=0.7222`（52/72）、`rules_plus_fallback_qwen_flash=1.0`（72/72）、`rules_plus_fallback_qwen_turbo=0.9861`（71/72）、`rules_plus_fallback_qwen35_flash_0223=0.7222`（52/72）。
- 同轮也按正确带 key 口径补做了 apples-to-apples `routing_pure_fallback_qwen_turbo`：`0.9861`（71/72），`fallback_used_cases=72`，平均时延 `943.88ms`。这意味着当前最新结果已经满足“规则 + fallback 不低于纯模型”目标；其中 `qwen-flash` selective fallback 这一轮达到 `1.0`，甚至优于同轮 pure fallback turbo。
- 当前 keyed v2 rerun 下，`qwen-turbo` selective fallback 的唯一残余错例是 `RZH-TA-012`：`如果中间先吃点东西，后面接哪个点更合理？`；该 case 在 selective fallback 与 pure fallback turbo 下都误判成 `manual_route_edit_redirect`，说明它已经主要是 fallback 分类边界，而不是规则层过早 direct-pass。
- 因此当前主要结论进一步收口为：规则层这轮改动已经把 benchmark/runtime 语义对齐、mixed-intent 触发与弱词污染问题基本压住；下一轮若继续优化，优先盯 `trip_assistant` vs `manual_route_edit_redirect` 的 fallback prompt / few-shot，而不是重新放松中文规则资产。
- 2026-05-08 当前代码已开始落第一轮规则层重构：引入 `jieba`，新增共享 `src/yoyo/modules/qa/rule_assets.py`，把归一化词库、直短语、意图关键词、boundary 词库和 hard-deny 词库从 router 常量中抽离；`intent_router` 也已切到“表达归一化 -> `jieba` 分词 -> 短语命中 / 关键词命中 / boundary 检测 -> fallback 决策”的新骨架。
- 同轮后续又进一步收紧了规则口径：去掉 follow-up 词库与相关触发，不再把常见短句当作稳定意图信号；中文规则层也不再维护英文词表，非中文 query 统一先做中文 pivot 再进规则层。
- 当前 direct-pass 原则已明确收口为“只有高把握才命中，否则交给 fallback classifier”，并已通过 routing regression、focused QA integration 与 routing benchmark 回归锁定。
- 最新 keyed v2 结果、对齐修复、失败样本分析与 pure fallback 对照结论现已同步到 `docs/routing-zh-hard-benchmark-report-2026-05-08.md`。
- 下一轮 case 设计优先覆盖：
  - 中文口语问法
  - 英文边界问法
  - 多轮短 follow-up
  - route-edit redirect 题
  - 天气 / 交通 / 拥挤度边界题
- 2026-05-08 已补出首版 `routing_benchmark_cases_zh_hard_v1.json`：72 条、全中文、六类 intent 全覆盖，重点覆盖 live/explain 冲突、trip/edit 冲突、translation 负样本、边界题与 follow-up。

#### 工作包 C：translation readiness
目标：把 translation 从“现在能答一部分”推进到“可以支撑后续 routing 设计”。
- 最新实现状态（2026-05-07）：后端已经落下一层共享 translator，覆盖三条路径：
  - query preprocessing：外语 query -> 中文 pivot
  - answer postprocess：内部中文回答 -> 用户语言
  - explicit QA translation：显式翻译请求，支持双语展示输出
- 当前显式 translation 已收口为默认按用户所选语言作为 source language；极少数“界面语言 A、正文语言 B”的 case 暂不额外检测。
- 2026-05-08 QA routing 进一步收口：当前按方案 A 仅信任请求里的 `user_language`；若 `user_language` 为中文（`zh*`）则不做 preprocessing，否则统一先 pivot 到中文再路由一次。用户选中文但正文含大量外语的混合输入问题先记录，后续迭代再处理。
- 2026-05-08 同轮继续收口 rules/fallback 分工：移除“弱旅游信号直接 `out_of_scope`”兜底，只保留 hard deny 与 weather/traffic/crowd 这类明确 boundary 拒答；其余规则未命中的 query 继续交给 intent router 与 fallback 模型判别，避免被固定拒答文案过早截断。
- 2026-05-09 同轮继续收口：天气与文字导航已从设计计划进入正式实现，当前 QA 主链路已支持 `weather_info` 与 `navigation_text` 两个 intent；对应 provider、formatter、validator、Amap client 与 API/route regression 测试都已补齐，并通过 `tests/test_qa.py`、`tests/test_qa_routing_regressions.py`、`tests/test_amap_weather_client.py`、`tests/test_amap_navigation_client.py`、`tests/test_amap_route_engine.py` 回归验证。
- 2026-05-09 同日晚些时候，导航又从“点到点文字导航”进一步收口为槽位优先：规则层已开始直接提取 `next-stop`、`destination-only`、`explicit route` 三类高把握槽位；复杂或多地点表达可进入 fallback 结构化提取；下游则把多地点拆成连续 legs 逐段复用 Amap 单段导航并聚合输出。对应新增回归已覆盖 `去故宫怎么走`、`下一站怎么去`、`从天安门到故宫再到景山怎么走`，以及 `tests/test_navigation_slot_extraction.py` 的 multi-leg 聚合校验。
- 2026-05-10 本轮继续补了首版导航 hard-case benchmark 基线：新增 `evals/datasets/navigation_hard_cases_v1.json`、`evals/run_navigation_benchmark.py` 和 Excel 导出。
- 2026-05-11 已继续修完首轮导航残余错例：`接下来怎么走` 现已作为 follow-up navigation phrase 稳定命中 `navigation_text`；`去故宫再去景山怎么走` 也已正确拆成 destination-only multi-leg，并从 session context 回填 origin。复跑后导航 benchmark 已收口到 `14/14=1.0`，`intent_correct_rate=1.0`，`slot_correct_rate=1.0`。
- 同轮还把 E2E QA benchmark 升级为可做主链路模型横评：`/api/v1/qa/ask` 现支持 request-level `llm_provider` / `llm_model` override，`evals/run_e2e_qa_benchmark.py` 新增 `--sweep` 模式，且共享 LLM runtime 已注册 `volcengine` / `doubao` provider，可直接对比 `gemini`、`qwen`、`doubao` 主链路回答模型。
- 同轮继续收口了 QA 主链路里 benchmark 语义、景点解析与 SQL/RAG 分工：
  - E2E benchmark 失败 case 口径已对齐真实产品语义：天气改判 `weather_info`，改路线改判 `manual_route_edit_redirect`，交通/拥挤度统一保持 boundary `out_of_scope`
  - `src/yoyo/modules/knowledge/attraction_retriever.py` 与 `src/yoyo/modules/qa/orchestrator.py` 已补中文景点 alias 解析，单轮 query 也能解析 `故宫` / `故宫博物院` / `天安门` / `景山公园` / `正阳门`
  - `src/yoyo/modules/knowledge/rag_retriever.py` 已从英文单语过滤收口到 `zh+en` 双语过滤，并按深问信号优先拉 `history/symbolism/architecture/curation`
  - `src/yoyo/modules/qa/retrieval.py`、`src/yoyo/modules/qa/prompts.py`、`src/yoyo/modules/qa/router_fallback.py` 已显式编码 SQL-first vs RAG-support 语义；后续白名单维护项已回写 todo
  - 为避免 session-aware trip-assistant 漂移，本轮还把“当前路线/当前站点”问句从生成式路径中剥成确定性 session 回答，同时保留 “next route stop” 这类 query 继续走结构化 trip-assistant 分支
  - 2026-05-11 又继续把 E2E benchmark grounding 口径收紧到当前 runtime truth：`evals/datasets/e2e_qa_benchmark_cases.json` 已升到 `v3`，RAG 深问 case 不再直接依赖 `real_rag_corpus_v1_zh.json` 里的 `正阳门/中轴线/architecture/curation` 语料，而是只依赖运行时当前真实会建索引的四类文档（`history` / `practical_notes` / `photo_spot_notes` / `family_notes`）；`real_rag_corpus_v1_zh.json` 现阶段仅保留为参考语料，待 runtime ingestion 真正接通后再扩回更深 case
  - 同日继续修复了 RAG 深问未命中的真实故障：问题不在主链路 attraction 透传，而在 RAG metadata filter。`rag_retriever.py` 之前会向 pgvector 查询注入 `poi_aliases` filter，但当前 runtime 建索引文档并不写该字段；`rag_index_service.py` 也用错误的 `metadata != filter_value` 直接比较 list filter，导致 `language/doc_type` 这类 list 条件会把有效向量结果过滤空。
  - 修复后，`rag_retriever` 已移除不存在的 `poi_aliases` filter，`rag_index_service` 已支持 list/scalar membership 匹配；新增回归 `tests/test_rag_backend.py` 与 `tests/test_rag_query.py` 均通过（8 passed）。
  - 在修复后的 fallback-on `8002` 服务上，三条深问定向复测已全部恢复：`E2E-RAG-001/002/003` 均返回 `retrieval_strategy=sql_then_rag`、`rag_query_status=ok`、`rag_backend_ready=true`、`grounding=sql_then_rag`。
  - 随后又基于修复后的 `8002` 服务完整重跑了一轮 fallback E2E sweep，三模型最新结果如下：
    - `qwen-plus`：`avg_score=4.4333`，`pass_rate=0.90`，`intent_correct_rate=0.9333`，`avg_latency_ms=2624`
    - `gemini-2.5-flash-lite`：`avg_score=4.3667`，`pass_rate=0.90`，`intent_correct_rate=0.9333`，`avg_latency_ms=4194`
    - `doubao-seed-mini`：`avg_score=4.3667`，`pass_rate=0.8667`，`intent_correct_rate=0.90`，`avg_latency_ms=3013`
  - 这轮 rerun 的新结论原本是：修好 RAG filter 后，`qwen-plus` 已反超成为当前 fallback-on 主链路下质量/时延综合最优的候选；Gemini 在分数上接近，但时延明显更高；Doubao 时延介于两者之间，但通过率仍略低。
  - 但 2026-05-11 当晚已按最新产品决策切换主链路默认模型：`src/yoyo/core/config.py` 默认值已从 `openrouter/google/gemini-2.5-flash-lite` 改为 `volcengine/doubao-seed-2-0-mini-260428`，按非思考模式运行；request-level `llm_provider/llm_model` override 与 benchmark sweep 仍保留，用于后续继续横评和 prompt 调优。
  - 随后又完成了首轮 Doubao Mini prompt 收口：`src/yoyo/modules/qa/prompts.py` 已改成中文优先的短结构，system prompt 收口为“角色 / 能力边界 / SQL-RAG grounding / 输出格式”四段；user prompt 继续按 intent 分流，但 attraction、RAG chunk、dialogue history 与 session 字段都做了首轮裁剪，避免小模型被冗余上下文拖偏。
  - 2026-05-11 当晚又继续补了第二轮 prompt 约束：保持 JSON 输出契约不变，但显式要求 `answer` 默认控制在 300 字以内、能短答就优先短答；历史/文化深问允许适度放长，但长回复必须自然分成 2~3 段。同时，主回答 prompt 传入的 dialogue history 已扩到最近 10 轮，并将当前版本单独固化到 `docs/qa-prompt-doubao-v4.md`，方便后续直接改文稿而不必先翻代码。
  - 2026-05-12 已继续修完 Doubao 主链路的两处明确阻塞点：一是 `trip_assistant` 成功调用 Doubao 后仍会因轻微格式漂移触发 `structured_output_valid=false`；二是显式 translation 在 plain MT 路径下经常还没真正请求 provider 就先退回 `missing_translation_text`。
  - 当前 `trip_assistant` 已通过“双侧收口”恢复稳定：`src/yoyo/modules/qa/prompts.py` 对 Doubao 输出增加了更硬的 JSON 约束（完整字段、`reason=null`、布尔字段显式写 true/false、给出紧凑示例），`src/yoyo/modules/qa/generator.py` 则新增有边界的 payload 归一化，仅修复缺失 `reason`、字符串空白与 `"true"/"false"` 这类近似正确输出；其余非法结构仍继续 fail-closed。
  - 显式 translation 也已按产品定义重新收口为“默认译成中文；给工作人员看时走中文双语展示”。`src/yoyo/modules/translator/service.py` 现已补强 `把“...”翻成中文`、`这句话用中文怎么说：...`、`帮我把“...”翻给工作人员看` 等低歧义问法，并在解析失败时先做一次保守兜底提取。更关键的是，`src/yoyo/modules/qa/orchestrator.py` 已改为 translation intent 优先把 `raw_query` 而不是 pivot 后的 `effective_query` 传给 `translate_for_qa(...)`，从而避免原始引号短句在 routing preprocess 后丢失。
  - 本轮定向回归已全部通过：`tests/test_translator.py`（17 passed）与 `pytest tests/test_qa.py -k "trip_assistant or translation" -v`（12 passed）。
  - 真实服务冒烟也已确认当前主链路行为收口：`把“Where is the restroom?”翻成中文` 现在返回 `洗手间在哪里？`，metadata 为 `intent=translation`、`execution_path=plain_mt`、`provider=xfyun_its`、`target_language=zh`；`我下一站去哪？` 现在可稳定走 `volcengine/doubao-seed-2-0-mini-260428` 的结构化成功路径，不再因轻微格式漂移退回 formatter fallback，只是在缺少 session/route context 时仍会返回 route-aware clarification。
  - 同轮也已把 `src/yoyo/modules/qa/rule_assets.py` 的 translation 规则语义同步收口到当前产品定义：归一化、直短语与语言关键词不再围绕“翻成英文”展开，而是默认围绕“翻成中文 / 给工作人员看”组织；对应路由回归 `tests/test_qa_routing_regressions.py` 已通过 `24 passed`。
  - 同日晚些时候又继续收口了真实 QA 短路链路的残余问题：`src/yoyo/modules/qa/formatters.py` 的 weather / navigation / translation / manual route edit fallback 文案与 `src/yoyo/modules/qa/orchestrator.py` 的 out-of-scope / boundary redirect 文案已统一中文化；`src/yoyo/modules/knowledge/hybrid_context_builder.py` 也补上了显式 route 槽位片段清洗，修复 `从天安门怎么走到故宫？` 会把 `怎么走` 污染进 origin 的问题。
  - 对应定向回归已通过：`pytest tests/test_qa.py -k "weather or navigation or route_edit or out_of_scope or translation" -v`（14 passed）、`pytest tests/test_navigation_slot_extraction.py -v`（3 passed）、`pytest tests/test_translator.py -k "show_to_local or bilingual or zh_suffix" -v`（4 passed）。
  - 当前这一轮的真实环境确认结果已进一步收口：天气、导航、manual route edit redirect 与 boundary out_of_scope 四条请求都已在重启后的 `8017` 新实例上验证通过；`帮我把‘Where is the restroom?’翻给工作人员看` 也已确认不再误判成 `out_of_scope`，而是稳定进入 `translation`。
  - bilingual display 剩余的唯一真实问题已从“路由错误”收口为“provider 上游异常”：`src/yoyo/modules/translator/service.py` 已修正 plain-MT 显式翻译的 source-language 选择逻辑，避免在 `language=zh` 但正文为英文原句时错误固定成 `zh -> zh`；当前真实退化仅因为 `xfyun_its` 连续返回 `500 Internal Server Error`，metadata 已显示 `source_language=null`、`target_language=zh`、`execution_path=provider_error`。
  - 2026-05-12 又继续修了一条 session-aware trip status 残余路由问题：`我现在到哪一站了？` 现已稳定命中 `trip_assistant`，不再误落到 `live_info`；同时 `format_trip_assistant_answer(...)` 的确定性 fallback 文案也已同步中文化。
  - 新增回归已锁住这条主链路：`tests/test_qa_routing_regressions.py::test_intent_router_routes_current_stop_status_query_to_trip_assistant` 与 `tests/test_qa.py::test_trip_assistant_current_stop_status_query_uses_session_context`；本轮定向 pytest 通过 `6 passed`。
  - 2026-05-13 又继续把 weather target fallback 收尾到可回归状态：当前天气地点解析已形成 `rule -> fallback -> default city` 三段式，fallback 未命中时会回退到当前 itinerary `city_code` 对应城市；同时已修正 `tests/test_qa.py` 里的 weather 替身实现，使 builder 级 mock 对齐 `WeatherContext`，API 级 monkeypatch 对齐 `AmapRouteClient.get_weather(self, ...)` 实例方法签名。定向回归 `pytest tests/test_qa.py -k "weather" -v` 当前为 `3 passed`。
  - 同轮还继续收紧了 `src/yoyo/modules/qa/router_fallback.py` 里的 weather slot fallback prompt：当前已明确 `query/raw_query/pivot_query` 中的显式地点优先，`session_context` 只允许作为弱提示，且不能覆盖用户明说的地点；收紧后同一组 weather 定向回归仍保持 `3 passed`。
  - 针对本轮改动的定向回归已继续通过：`tests/test_qa.py`（36 passed）；此前 targeted 回归 `tests/test_qa.py tests/test_qa_routing_regressions.py tests/test_rag_query.py` 仍保持通过（61 passed）
  - 2026-05-14 已新增首版 QA 手动联调页：`GET /api/v1/qa/playground`，并补了 `POST /api/v1/qa/preview` 用于预览 resolved query、intent router、hybrid context 与生成式 prompt。当前 playground 支持覆写 `guide_session/session_context`、`profile`、`attraction`、`dialogue_history` 等 prompt 变量，并把覆写状态写入 `metadata.playground`，方便前端/产品直接手动联调翻译、路由、session-aware QA 与回答链路。
- 同日又修复了一条 mixed-language translation 回归：`language=en` 但 query 同时包含英文指令和中文原句时，orchestrator 之前会因为“只要含中文就按中文直路由”而跳过 routing preprocess，导致 `Please translate: 请帮我拍张照片` 误落到 `out_of_scope`。当前已收口为“仅当英文请求不含拉丁字母时才视作 CJK 直路由”，因此 mixed-language 显式翻译会继续走 preprocess-first / translation 主链路；定向回归 `pytest tests/test_qa.py -k "translation" -vv` 已恢复 `7 passed`。
- 同日晚些时候继续修了 QA playground 的真实可用性问题：页面上的 `发送 QA 请求` 按钮不再先跑 `preview` 再跑 `ask`，而是只发一次真实 `/api/v1/qa/ask`；默认表单也收紧成最小 payload，只在用户显式填写或切 preset 后才把 `context.qa_playground` override 注入后端，避免默认 `session/profile/attraction/dialogue_history` 噪音把问题问偏。同时 `src/yoyo/modules/qa/orchestrator.py` 已补出 `metadata.latency_ms` 分段耗时（`preprocess/routing/context_build/generation/postprocess/total`），playground 结果区也新增链路摘要与耗时摘要，便于直接定位“慢在页面还是慢在 QA 主链路”。对应回归已通过：`pytest tests/test_qa_playground.py -vv`（4 passed）与 `pytest tests/test_qa.py -k "translation or trip_assistant" -vv`（14 passed）。
- 2026-05-15 又继续把 `context_build_ms` 从黑盒总时长拆成细分埋点：`context_build_breakdown_ms` 现会暴露 `attraction_lookup_ms`、`profile_lookup_ms`、`live_info_lookup_ms`、`weather_target_resolution_ms`、`weather_lookup_ms`、`navigation_slot_resolution_ms`、`navigation_lookup_ms`、`rag_lookup_ms`、`prompt_projection_ms` 等字段，并补充 `weather_target_source` / `navigation_slot_source` 这类来源标记。这样后续再看天气或导航链路的慢点时，就能直接区分是规则/slot 解析慢、fallback 模型慢、Amap 慢，还是 RAG / 其他上下文查询慢，而不再只看到一个总的 `context_build_ms`。
- 2026-05-15 同轮又继续收口了天气 fallback 主链路：当前只有“规则已命中 `weather_info` 且规则已抽到地点”这一种情况才会跳过 fallback；只要规则没命中天气，或虽然命中天气但地点没抽出来，都会进入 router fallback。更关键的是，fallback 现在会在同一次路由模型调用里同时返回 `intent` 与 `weather_location_name`，orchestrator 会把该地点写入 routing session context，后续 `build_hybrid_context(...)` 直接复用，不再单独发起第二次 weather slot fallback 模型调用。因此新的时延语义也更清晰：若 `weather_target_source=fallback`，其模型成本主要体现在 `routing_ms`，而不是 `context_build_ms`；对应 `weather_target_fallback_ms` 现在应为 `0`。针对这次收口新增/修正后的定向回归已通过：`pytest tests/test_qa.py -k "weather or router_fallback" -vv`（9 passed）、`pytest tests/test_routing_benchmark.py -vv`（6 passed）。
- 2026-05-15 已继续设计并落地一轮全链路多语言 QA E2E benchmark：新增 `evals/datasets/e2e_qa_fullchain_multilingual_v1.json` 与 `evals/datasets/e2e_fullchain_qwen_doubao_sweep.json`，用于对比 `dashscope/qwen-turbo` 和 `volcengine/doubao-seed-2-0-mini-260428`。本轮覆盖中文、英文和泰语、越南语、印尼语、马来语、菲律宾语、缅甸语、高棉语、老挝语，并覆盖 smalltalk、hard deny、boundary、translation、SQL、SQL+RAG、live_info、weather_info、navigation_text、session-aware trip_assistant、manual_route_edit_redirect 等链路。`evals/run_e2e_qa_benchmark.py` 也已扩展为输出 `preprocess_ms`、`routing_ms`、`context_build_ms`、`generation_ms`、`postprocess_ms`，以及 RAG / 天气 / 导航 / attraction / profile lookup 子阶段耗时；Excel 额外新增按语言、功能类别、intent、operation 聚合的 latency sheet。
- 2026-05-16 已按最新产品口径继续收口 SQL/RAG 分流：SQL 存储的景点基础介绍、实用提示、位置和适合人群等直接走 SQL，不再因为“历史/介绍”等宽泛词触发 RAG；只有中轴线、象征意义、建筑秩序、深层历史/策展等 SQL 未覆盖深问才触发 RAG。当前 mock 数据之外但仍属于北京景点的问题，可由模型常识回答并在 metadata 标记 `model_knowledge`，后续真实 SQL/RAG 数据拆分完成后再收回到结构化数据链路。
- 同轮已完成导航 bus/subway 修复后的真实高德 300 条复跑：在需要外网权限的有效运行下，`navigation_slot_hard_300_cases` 达到 `pass_rate=1.0`、`intent_correct_rate=1.0`、`slot_correct_rate=1.0`、`amap_reasonable_rate=1.0`；34 条公共交通空结果按规则转步行兜底，且未再出现公交线路因终点站名包含“地铁”而被误判成 subway 的样本。
- 同日继续扩展导航地点白名单：基于下载目录的 `北京旅游网_修复版景区列表(2).csv` 调用高德 POI/geocode 生成 `navigation_place_registry_generated.py`，主链路注册地点从 20 个扩到 147 个，其中北京旅游网高置信景区 127 个，23 个低置信/歧义项留在审核 JSON，不进入主链路。地点置信度策略已记录为：高置信旅游 POI 直达，商业/地址歧义和未注册多候选进入澄清。
- 同轮已把地点澄清接入 QA 主链路：`正阳门餐厅` 等商业/地址歧义不再因核心 alias 子串命中而直达景点；导航上下文会返回 `status=clarification`、候选列表和原 slot，formatter 输出候选让用户选；用户下一句 `选第一个/第2个/候选名称` 会由 orchestrator 识别为导航澄清续接，并用选中候选坐标继续路线规划。
- 澄清续接继续收口为规则优先：`上面的` 选第 1 个，`下面/最后` 选最后一个，奇数候选的 `中间` 选正中，偶数候选的 `中间` 与编号越界继续二次澄清；不让 LLM 直接猜坐标。
- 同轮继续补齐澄清 fallback：当规则无法解析用户是否在选候选时，router fallback 会收到结构化 `pending_clarification`，同时判断真实 intent 与候选选择动作；若用户改问天气/景点/实时开放等新任务则正常路由，若选择候选则只返回已有候选编号，低置信继续澄清。
- 澄清能力的后续架构已记录：每个 intent 维护自己的 typed clarification state 与规则澄清；fallback runtime/model 配置共用当前 router fallback，但 prompt 按 clarification 类型动态注入，避免一个大 prompt 混淆导航地点、天气地点、翻译语言和 live 信息类型。
- 2026-05-15 已补出 QA intent 规则日常维护手册与首轮 100 case 维护集：`docs/qa-intent-rule-maintenance.md`、`evals/datasets/routing_rule_maintenance_100_cases.yaml`、`docs/routing-rule-maintenance-benchmark-2026-05-15.md`。首轮 rules-only 结果为 `82/100`，但 direct-pass 为 `43/43` 且 false direct pass 为 `0`；当前缺口主要集中在天气句式、live 入园句式、trip 状态问法、route-edit 顺序/删除句式和 runtime 景点实体覆盖。
- 同日继续追加了 200 条复杂 hard cases，并通过 `evals/datasets/routing_rule_all_300_cases.yaml` 整理成 300 条合集。新增 runner 安全指标 `safe_accuracy`、`direct_pass_precision`、`false_direct_pass_cases`，并修复一轮高置信规则缺口后，最终 `200 complex` 达到 `accuracy=0.865`、`safe_accuracy=0.94`、`direct_pass_precision=1.0`、`false_direct_pass=0`；`300 all` 达到 `accuracy=0.90`、`safe_accuracy=0.95`、`direct_pass_precision=1.0`、`false_direct_pass=0`。详细报告见 `docs/routing-rule-complex-benchmark-2026-05-15.md`。
- 同日又继续生成 500 条更复杂的 routing hardcase，并通过 `evals/datasets/routing_rule_all_800_cases.yaml` 把此前 300 条与新增 500 条汇总为长期回归集。新增脚本 `evals/build_routing_rule_hard_500_dataset.py` 覆盖长口语、多意图、否定边界、smalltalk 能力询问混任务词、navigation/trip、trip/edit、live/explain、weather/live、translation/explain 与 unsupported boundary 正负例；本轮同步修进主链路 `src/yoyo/modules/qa/intent_router.py` 和 `src/yoyo/modules/qa/rule_assets.py`。最终 `500 hard` 达到 `accuracy=0.924`、`safe_accuracy=1.0`、`direct_pass_precision=1.0`、`false_direct_pass=0`；`800 all` 达到 `accuracy=0.935`、`safe_accuracy=1.0`、`direct_pass_precision=1.0`、`false_direct_pass=0`。详细报告见 `docs/routing-rule-hard-500-benchmark-2026-05-15.md`。
- 同日继续按导航专项方案收口 `navigation_text` 槽位链路：新增 `src/yoyo/modules/knowledge/place_resolver.py` 作为北京导航地点库，`NavigationSlotResult` / `NavigationSlotPayload` 现保留 `origin_place` 和 `destination_places`，包含 `place_id`、坐标、adcode 和 source。规则层覆盖 `下一站怎么去`、`到X怎么走`、`从A到B`、`从A到B再到C`，destination-only / next-stop 优先使用 `session_context.current_position` GPS 起点；fallback 模型只做结构补充，不最终决定同名地点。高德 client 已支持已知坐标直传，未注册地点 geocode 时增加北京范围校验，避免 `天坛` 漂到外地。新增 100 条导航专项集 `evals/datasets/navigation_slot_100_cases.json`，最终 `pass_rate=1.0`、`intent_correct_rate=1.0`、`slot_correct_rate=1.0`；旧 `navigation_hard_cases_v1` 仍保持 `14/14=1.0`。设计与报告见 `docs/navigation-slot-routing-design.md`、`docs/navigation-slot-benchmark-2026-05-15.md`。
- translator 现已具备独立配置入口：
  - provider / model 选择
  - timeout
  - fail-open
  - pivot language
  - answer translation enable
  - bilingual translation enable
- translation metadata / observability 现已开始按命名空间收口：
  - `intent_router.preprocessing`
  - `answer_translation`
  - `translation`
- 2026-05-07 本轮新增收口：
  - translation benchmark 的 per-case / summary schema 已补齐 token、cost、run metadata 和平铺评分字段
  - 东南亚小语种首轮支持已扩到 `ms`、`fil/tl`、`my`、`km`、`lo`
  - translation datasets 已从 smoke 样本扩成“语种 × 提问类型 × 翻译方向”矩阵
  - Excel 导出链路已新增 `translation_cases` 与 `translation_model_compare` sheet
  - HY-MT 与 XFYun ITS 两模型的真实 benchmark 已完成并补出中文总结文档；修复 XFYun 凭证缺失后，当前整轮结论已收口为：XFYun 在 product translation 与 routing preprocess 两套数据上都优于 HY-MT，且时延显著更低
  - 2026-05-07 当前正式决策已进一步收口：放弃 HY-MT 作为后续 translator 候选，产品后续正式使用 XFYun ITS 作为默认翻译器；HY-MT 结果仅保留为历史 benchmark 对照
  - 针对 XFYun 未返回 token 用量的问题，当前已按字符计费口径补做成本估算：本轮 1770 字符、约 0.07965 元，总体单条平均成本约 0.00043 元，其中短文本约 0.00016 元/条、长文本约 0.00068 元/条
- 下一轮验证至少覆盖：
  - translation 输出质量
  - translation 后 routing 稳定性
  - provider 缺失与 degraded 行为
  - bilingual translation 场景的产品输出质量
- 2026-05-07 已追加一轮 XFYun ITS 真实验证，作为上述四类维度的第一轮落地样本：
  - `product_translation`：136 case，平均分 `4.39/5`，平均时延 `209ms`，无 degraded case
  - `routing_preprocess`：48 case，平均分 `4.27/5`，平均时延 `587ms`，其中 1 个 Khmer `live_info` case 因预处理超时进入 degraded
  - bilingual display：8 case，平均分 `4.0/5`，当前可用但明显弱于 direct translation
  - 当前最弱环节已从“纯翻译质量”收口为“翻译进入产品链路后的意图保持”，尤其是 translation 指令句、`manual_route_edit_redirect` 与少数 `trip_assistant` 小语种问法
- 2026-05-07 同轮已继续完成一轮严格显式语种口径下的修复后复跑：
  - `product_translation`：136 case，平均分进一步提升到 `4.69/5`，剩余 `2` 个 isolated `provider_error` degraded case（`product-009`、`product-025`）
  - `routing_preprocess`：48 case，平均分进一步提升到 `4.74/5`，无 degraded case
  - 本轮修复已确认收口的点：translation 指令句在 preprocess 后已稳定命中 `translation`；显式 translation 已进一步收口为默认信任 `user_language`，不再依赖正文语种推断
  - 当前剩余薄弱点进一步缩小为：部分 `manual_route_edit_redirect` 仍会漂到 `trip_assistant` / `out_of_scope`，以及少数 Burmese / Khmer / Lao 的 trip-assistant pivot 中文仍不够稳
  - benchmark 数据口径也已正式收紧：每条 case 都必须显式声明 `user_language/source_language/target_language/direction`，并去掉极端多语混合 case；runner 对缺字段和方向不一致直接 fail-fast
- 2026-05-07 同日继续补完 plain MT 的错误观测与抗抖动收口：
  - benchmark per-case 结果现在会持久化上游错误与重试轨迹字段：`llm_error`、`raw_text`、`structured_output_valid`、`attempt_count`、`retry_performed`、`attempts`
  - plain MT 默认采用“单次 `1s` 超时 + 最多 `1` 次顺序重试”的策略；只对 retryable 上游故障（如 timeout / 连接错误 / provider 5xx）触发，不对鉴权或确定性 4xx 错误重试
  - 已补并跑通回归：`tests/test_translator.py`（12 passed）与 `tests/test_translation_benchmark.py`（6 passed）

#### 工作包 D：QA 发布前验证
目标：让 QA 侧验证从零散回归走向可重复的发布前检查。
- 下一轮验证清单应覆盖：
  - routing accuracy
  - translation verification
  - degraded / fallback consistency
  - session-aware QA consistency
  - release-oriented E2E verification
- 输出物应至少包括：
  - 本轮执行清单
  - 结果记录入口
  - blocking / non-blocking 判定结果

## 5. 下一阶段的测试重点
当前测试体系已经具备：
- API contracts
- demo test plan
- readiness checklist
- QA benchmark 文档
- rounds log

当前缺的是一层按功能组织的测试说明。
这就是 `docs/feature-test-guide.md` 的职责。

下一轮面向发布的验证应重点覆盖：
- 按功能逐项验证
- degraded / fault-injection 检查
- worker / API 环境一致性
- QA routing 与 translation 检查
- 主链路时延感知与响应性检查
- live_info Redis 缓存命中/失效检查，重点确认同景点同日同 `info_type` 重复请求能降低外部搜索时延
- QA intent rule redesign 已形成维护资产：`docs/qa-intent-routing-rule-design.md` 与 `docs/qa-intent-keyword-library.yaml`；最新设计已明确外语和东南亚语种必须先翻成中文 canonical query，规则评分只维护中文词库/句式；后续接入 runtime 前，先用 router-only benchmark 验证 smalltalk/task、live/explain、weather/live、navigation/trip、trip/edit、translation/explain 六类冲突。
- navigation_text 槽位链路已补复杂混合 100 case：覆盖“故宫好美啊，下面要去哪里”“想去/等会去/接着去X怎么走”“从这里到X”“当前站到X”“多段分段路线”和公共交通模式。当前已支持 `walking/driving/transit`，显式方式优先；未指定方式时按已解析坐标直线距离 3km 阈值默认步行或公共交通。最新 base 100 与 complex 100 均为 `pass_rate=1.0`，产物见 `docs/navigation-slot-benchmark-2026-05-15.md`。
- 近期商讨过的 QA 规则已集中整理到 `docs/qa-rule-decision-log.md`，按“问题 / 解决方式 / 维护位置”记录，后续规则变更优先追加该日志。
- navigation_text 已新增 300 条复杂 hardcase 并连接真实高德复跑：意图准确率 `1.0`、槽位准确率 `1.0`。初跑高德合理返回率为 `0.95`，剩余失败集中在 3km 内显式公交/地铁无方案；现已在主链路增加 `transit + empty_navigation_payload -> walking` 兜底，最终复跑 `pass_rate=1.0`、`amap_reasonable_rate=1.0`。后续又修正了公共交通回复只截取步行到站前三步的问题：最终回复现在会保留 `乘坐...` 步骤，多段路线显示路线总览和每段距离/耗时。最新一轮又把 `transit` 细分成 `bus/subway/public_transport`：公交请求过滤含地铁方案，地铁请求优先含地铁方案，benchmark 导出 `actual_transit_preference`、`amap_final_transit_vehicle_types` 和 `amap_transit_preference_satisfied`；真实高德 300 复跑仍为 `pass_rate=1.0`、`amap_reasonable_rate=1.0`，严格偏好过滤后 `amap_mode_fallback_cases=28`。报告见 `docs/navigation-hard-300-amap-benchmark-2026-05-15.md`。
- 2026-05-16 已把步行导航最终回复补成结构化分段：Amap client 保留 `orientation/polyline/end_location` 并批量逆地理 step 终点，formatter 输出“沿路名/方向步行约 N 米，到路口/POI 附近，转向”，纯步行不再硬截前 5 步。本轮同时补充中国国家博物馆、孔庙和国子监、鸟巢、水立方、798、将台、北京动物园、五塔寺等北京 POI 到导航地点库，避免简称/同名自由 geocode。真实高德 turn point smoke 8 条全 available，结果在 `evals/results/navigation_turnpoint_smoke_20260516.json`。
- 2026-05-16 已完成主链路默认 `qwen-turbo` 的 1800 条 E2E QA hard benchmark，不再跑 Doubao。数据集为 `evals/datasets/e2e_qa_intent_hard_1800_cases.json`，覆盖 9 个 intent、每个 intent 200 条，语言覆盖中文、英文和 8 个东南亚语种。最终 `pass_rate=1.0`、意图准确率 `1.0`、平均总时延 `1699.57ms`、p95 `4796.13ms`。人工评审 Excel 已导出到 `evals/results/e2e_intent_hard_1800_qwen_default_20260516/e2e_qwen_default_intent_hard_1800_results.xlsx`，其中 `review_cases` 包含原 query、中文释义、最终 answer、中间结果和各环节时延。报告见 `docs/e2e-qa-intent-hard-1800-qwen-2026-05-16.md`。
- 同轮 E2E 修复已落主链路：smalltalk 能力说明类问法规则直达；`不用操作行程/不要误当成改路线/不要删除任何景点` 作为 route-edit 否定保护；domain guard 保留 raw query 防止外语翻译吞掉 `Python/爬虫` 硬拒绝信号；`订票/付款/下单/代买` 归交易型 out-of-scope 边界。对应规则追加到 `docs/qa-rule-decision-log.md` 的 QA-RULE-022 至 QA-RULE-025。

### 5.3 最新非 QA 风险轮补记
- 最新一轮非 QA 真实环境测试已再次验证：guide/worker 真链路、GPS/playback 状态切换、route edit 后 version switch、share-card finish 边界都能跑通。
- 已通过重启 API / worker 后的复测确认：此前 observed 的 `finished session -> guide/content = 404` 并不是当前代码语义 bug，而是运行进程未与当前源码对齐导致的部署一致性问题。
- 在按当前源码重启后，finished session 下 `guide/content` 已恢复为当前预期语义：`409 guide session finished`。
- 因此，这个风险项当前已从“语义待确认”收口为“部署流程注意事项”：后续继续发布前风险轮时，必须先确认 API / worker 已按当前源码重启。

### 5.1 发布前验证的定义完成标准
开始正式测试前，应至少满足以下定义完成状态：
- 功能测试说明已具备功能、测试分层、当前覆盖状态和本轮执行重点
- QA 工作包已拆成 routing / translation / degraded / E2E 四类
- 本轮执行顺序已明确
- 发布前验证的输出物已明确：
  - 测试矩阵
  - 执行清单
  - 结果记录入口
  - blocking / non-blocking 判定口径

### 5.2 blocking / non-blocking 判定口径
- **blocking**：会阻止开始提测或继续发布验证的问题，例如主链路失败、接口结构错误、状态流转错误、环境不可启动、关键 provider 语义错误
- **non-blocking**：不影响当前主链路验证，但需要记录并后续修复的问题，例如补充 benchmark 深度、局部 wording 优化、非关键边界体验问题

## 6. 阅读与续接规则
新 session 继续工作时，使用以下顺序：
1. `AGENTS.md`
2. `README.md`
3. `docs/README.md`
4. `docs/todo-phase-2.md`
5. `docs/phase-2-summary.md`
6. `docs/feature-test-guide.md`

开始执行前，优先从 `docs/todo-phase-2.md` 中尚未完成的 P1 项继续，不要再从旧的 `docs/todo.md` 续写当前阶段工作。

只有在需要追溯历史背景时，再回头读旧文档：
- `docs/todo.md` -> 上一阶段归档
- `docs/current-session-summary.md` -> 历史 session 日志
