# 开发问题复盘

用于记录开发过程中暴露出的具体问题，方便后续复盘。

写法保持极简：每条只写 **问题 / 原因 / 改进方案**。

## 2026-05-16 英文用户答案翻译降级兜底漏触发

- 问题：英文用户问当前/下一站时，内部确定性回答是中文模板，但包含 `Tiananmen Square`、`Forbidden City` 等英文景点名；当回答翻译 provider 降级时，语言对齐兜底没有触发，导致英文请求拿到中文句子。
- 原因：兜底判断使用“包含中文且不包含拉丁字母”，而中英混排的站点名会让判断误以为答案已有英文。
- 改进方案：只要中文处理链路给英文用户返回的答案含 CJK，就触发语言对齐兜底；同时为行程站点类中文模板增加简单英文兜底格式，保留 current/next stop 名称和 route 语义。

## 2026-05-16 自动记录规则范围收口

- 问题：文档入口拆分后，如果把 `dev-retrospective.md` 也要求每次小测试都更新，会让复盘文档变成流水账，反而降低后续阅读价值。
- 原因：此前“自动记录进度”的表述过宽，把连续性进度记录和问题复盘记录混在一起。
- 改进方案：规则已收口为两层：`phase-2-summary.md` 和 `todo-phase-2.md` 负责常规进度连续性；`dev-retrospective.md` 只在策略变化、明确问题归因、回归、可复用解决方案或维护规则变化时更新。

## 2026-05-16 文档入口过载与平铺问题

- 问题：根 `README.md` 承载了过多 QA、导航、评测和历史 benchmark 细节，`docs/` 下大量文档平铺，后续 AI 接手时难以判断哪些是当前入口、哪些是专题规范、哪些只是历史报告。
- 原因：前期每轮 QA hardening 和 benchmark 都按单文档追加，README 又同步记录详细结论，缺少 `docs/README.md` 和专题索引承接从属关系。
- 改进方案：根 README 收敛为总入口；新增 `docs/README.md`、QA、routing、intent-rules、navigation、live-info、translation、prompts、evals、testing、project、tracks 等索引。当前先不移动原文件，保留旧链接稳定；后续可按专题目录做物理迁移并统一更新链接。

## 2026-05-07 translation / routing 问题补记

- 问题：显式 translation 在 `id` / `ms` / `fil` 等小语种场景下曾出现整批失败，暴露出 source language 策略与真实产品流不一致。  
  原因：实现一度试图根据正文内容临时推断 source language，但真实产品流里用户会先选定自己的语言；继续依赖正文检测只会让少数边缘 case 把主路径复杂化。  
  改进方案：显式 translation 已收口为默认信任 `user_language`，不再依赖正文语种推断；“界面语言 A、正文语言 B” 的少数 case 暂不处理，后续如有真实需求再单独设计。

- 问题：routing preprocess 后，translation 指令句会漂到 `out_of_scope`。  
  原因：预翻译后只保留中文表面句子，translation 的原始指令信号没有继续参与路由判断。  
  改进方案：已改为 routing 时继续保留 raw query 信号，不再只依赖 pivot 后文本。

- 问题：routing preprocess 后，部分 `manual_route_edit_redirect` 会漂到 `trip_assistant` 或 `out_of_scope`。  
  原因：翻译后的中文更像普通行程咨询句，route-edit 操作语义被弱化。  
  改进方案：已改为 route-edit 路由同时结合 raw query 与 pivot query，并补回归测试锁定行为。

- 问题：plain MT 显式翻译分支对 usage 字段和 formatter fallback 路径存在隐式假设。  
  原因：默认 translator 切到 XFYun 后，旧测试开始命中 plain MT 路径，暴露出 usage 字段兼容性和未定义 `response` 的缺口。  
  改进方案：已放宽 usage 读取方式，并修掉 formatter fallback 分支里的未定义变量。

- 问题：Khmer `live_info` case 本轮出现一次真实 timeout degraded。  
  原因：provider 预处理调用超时，导致 routing 前置翻译直接失败。  
  改进方案：保留 degraded 记录，并在后续继续复核 timeout 分布与超时配置。 

- 问题：显式翻译链路一度为了修 benchmark 临时补了词汇级 source language 推断，策略变得过重。  
  原因：当时为了快速收口 `id/ms/fil -> zh` 的评测失败，先走了正文词表识别，但这条路径对真实产品价值有限，也难长期维护。  
  改进方案：本轮已移除这层临时检测，显式翻译统一按用户所选语言发给 provider，并用测试锁定当前语义。

- 问题：translation benchmark 一度允许缺失语种字段和极端多语样本混入，导致复跑结果既不稳也不代表真实产品输入。  
  原因：runner 之前对 `user_language/source_language/target_language/direction` 仍保留 fallback 推断，数据集里也混入了不符合当前产品语义的复杂 case。  
  改进方案：已把 benchmark 数据口径收紧为每条 case 显式声明语种字段、去掉极端多语混合 case，并让 runner 对缺字段与方向不一致直接 fail-fast；复跑后主结果已收口到 2 条 isolated provider 异常。

- 问题：plain MT 出现 isolated degraded case 时，benchmark 结果里缺少上游错误细节与重试轨迹，难以直接判断是 timeout、连接抖动还是 provider 业务错误。  
  原因：translator 层虽然已有高层 degraded 语义，但 benchmark per-case 结果没有把 `llm_error/raw_text` 和每次尝试的上下文完整落盘；同时 plain MT 单次等待上限过长，偶发抖动会直接把单条 case 拖到十几秒。  
  改进方案：已补齐 per-case 错误观测字段（`llm_error`、`raw_text`、`structured_output_valid`、`attempt_count`、`retry_performed`、`attempts`），并把 plain MT 收口为“单次 `1s` 超时 + 最多 `1` 次顺序重试”，仅对 retryable 上游故障触发。

- 问题：QA routing 之前会先对原始 query 跑一轮完整规则路由，再在 preprocess 后对 `effective_query` 再跑一轮，链路重复且对东南亚小语种原文规则命中价值有限。  
  原因：早期为了保护显式 translation 与少量英文主链路，保留了“原文首轮路由 + preprocess 后二次路由”的折中设计；但当前多语种方向已经收口为中文 pivot 统一路由，这层原文规则已变成额外复杂度。  
  改进方案：本轮改为方案 A：仅信任请求里的 `language` 字段判断是否中文；中文直接路由，其余语言统一先 pivot 到中文后只跑一次规则路由。

- 问题：用户选择中文，但正文里包含大量外语时，当前 routing 会直接按中文路径处理，可能绕过 preprocess。  
  原因：当前方案 A 仅信任请求里的 `language` 字段判断是否中文，尚未额外处理“中文界面 + 混合外语正文”输入。  
  改进方案：

- 问题：QA routing 之前会把弱旅游信号或规则未命中的 query 过早打成 `out_of_scope`，导致很多本应交给 fallback 判别的句子直接被固定拒答文案截断。  
  原因：`domain_guard` 曾把弱旅游信号直接判成 unsupported，`intent_router` 也用 `weak_travel_signal_before_out_of_scope` 作为默认兜底，规则层承担了过多“主分类器”职责。  
  改进方案：本轮已收口为仅保留 hard deny 与明确 boundary 拒答；其余弱信号 / 未命中 query 默认继续视为 supported，并交给 intent router + fallback 承接，避免过早拒答。

- 问题：router-only benchmark runner 与 `resolve_router_fallback(...)` 的签名在新增 `raw_query/pivot_query` 后出现漂移，真实跑带 fallback 的 candidate sweep 时可能直接因参数不匹配报错。  
  原因：runtime orchestrator 已升级为传入 `raw_query` 与 `pivot_query`，但 `src/yoyo/evals/routing.py` 里的 benchmark 调用还停留在旧签名。  
  改进方案：已让 benchmark runner 与 runtime 调用保持一致，统一显式传入 `raw_query` 和 `pivot_query`，并用 zh-hard benchmark 测试覆盖该链路。

- 问题：通用 Excel 导出器会把所有 `*_summary.json` 都当成单个 summary 对象，遇到 `routing_sweep_summary.json` 这种列表结构时直接报错。  
  原因：`evals/export_excel.py` 早期默认 summary 文件全是单对象，没有兼容 sweep 汇总这种数组输出。  
  改进方案：已在导出器里跳过非 dict summary，保持通用导出能力不被 routing sweep 结果破坏。

- 问题：routing benchmark rerun 完成后，阶段总结、历史 session 日志和正式报告一度仍停留在旧数字，导致文档结论与 `evals/results/routing_zh_hard_v1/` 中的最新产物不一致。  
  原因：rerun 之后缺少一个固定的“结果回写”步骤，benchmark 产物、报告和 README 入口没有在同一轮同步刷新。  
  改进方案：后续每次 rerun 完成后，立即同步更新正式报告、`docs/phase-2-summary.md`、`docs/current-session-summary.md`、`docs/todo-phase-2.md` 与 README 入口，避免文档漂移。

- 问题：`rules + selective fallback` 的 `qwen-turbo` 结果只有 `0.8889`，但额外做的 `pure_fallback_qwen_turbo` 对照实验却达到 `0.9861`，说明当前残余错例并不主要来自模型本体。  
  原因：规则模块仍会把一部分模糊 query 过早直接通过，或没有把足够多的边界句子交给 fallback；因此 selective fallback 的主要瓶颈转移到了规则口径和触发策略，而不是模型分类能力本身。  
  改进方案：下一轮优先重设计规则模块，重点复查 direct-pass 条件、fallback 触发条件，以及 `translation` / soft route-edit / travel-adjacent `out_of_scope` 的边界定义，并持续保留 pure fallback turbo 作为对照基线。

- 问题：把 router 从旧常量打分迁到 `jieba` + 共享规则资产时，translation 过抓、短 follow-up fallback 丢失、以及英文 route-stop 查询被 route-edit 误抓。  
  原因：初版新规则骨架把“语言词/对象词”与“动作词”耦合得不够严，还错误地试图用 follow-up 词库和英文词表去弥补本该由 preprocess-first 架构承接的问题。  
  改进方案：已收口为 translation 只有动作词主导时才强命中，follow-up 常见短句从规则层移除，中文规则资产不再维护英文词表；英文 trip-assistant 用例改为显式 mock preprocess 后再测，并用 routing regression + benchmark + focused QA tests 锁定行为。

- 问题：router-only benchmark 在代码和 runtime 语义已变化后，仍可能沿用旧路由口径，导致测试能跑但结论不可信。  
  原因：benchmark runner 一度没有对齐 orchestrator 的 hard deny override，也没有在非中文 case 上复用 `query_zh` / pivot 中文语义；另外单独补跑 pure fallback 时还因为 DashScope key 没传进运行时，第一次结果实际上全部退回规则输出。  
  改进方案：已让 benchmark runner 与 runtime 显式共用 `raw_query/pivot_query/query_zh` 语义，并补了 benchmark 单测锁定；pure fallback 基线也改为在带 key 环境下单独重跑后再写入报告，避免把无效 rerun 误当成模型结论。

- 问题：QA 行为测试在切到 preprocess-first 架构后，部分英文用例仍默认直接进入中文规则层，导致 zero-score query 被优先级 tie-break 错误吸到 `manual_route_edit_redirect`。  
  原因：测试前提还停留在“英文可直路由”的旧语义，而当前 router 在所有候选分数都为 0 时会按 intent priority 选最高项；同时部分 session-aware current-stop case 的默认 pivot 中文句也不够强。  
  改进方案：已把 zero-score router 兜底收口为 `out_of_scope`，并在 `tests/test_qa.py` 中统一补上英文 query 的默认 preprocess mock；同时补齐 Amap weather/navigation client 单测和 stop-name 对齐逻辑，最终确认 `tests/test_qa.py`、`tests/test_qa_routing_regressions.py`、`tests/test_amap_*` 全部通过。

- 问题：`navigation_text` 已支持点到点导航，但对 `去X怎么走`、`下一站怎么去` 和 `A->B->C` 这类真实产品问法仍缺少统一槽位语义，导致下游只能围绕单段 `origin/destination` 做弱解析。  
  原因：最初接入时优先完成 provider、formatter 和 supported intent 主链路，`hybrid_context_builder.py` 里仅保留了非常轻量的 `从A到B` 抽取，fallback 也还停留在 intent classification。  
  改进方案：本轮已把导航收口为“规则直提槽位 + fallback 结构化提取 + multi-leg 聚合”链路，新增导航槽位 schema、连续 legs 聚合、next-stop / destination-only / multi-leg 回归测试，并继续保留 route-edit / trip-assistant 边界。

- 问题：导航 hard-case benchmark 首轮剩余 `接下来怎么走？` 与 `去故宫再去景山怎么走？` 两条错例，说明 follow-up navigation phrasing 和 destination-only multi-leg 仍有规则缝隙。  
  原因：intent router 里 `接下来` 同时触发了 `trip_assistant` 进度信号，`_fallback_reason()` 也把该短语继续视为 navigation/trip conflict；同时 `_extract_destination_segments(...)` 先删 `去` 再切 `再去`，导致多段 destination-only 句子被洗坏，且 hydrate 阶段没有给 `multi_leg` 场景补回 `current_stop_name`。  
  改进方案：已补 follow-up navigation phrase 优先级与 conflict 豁免，修正 destination-only multi-leg 的分隔顺序，并让 `multi_leg` 也能从 session context 回填 origin；复跑后导航 benchmark 已收口到 `14/14=1.0`。

- 问题：导航能力刚接到主链路时，只靠单测和 API 行为测试很难看出真实槽位提取边界，尤其是 `next_stop` / `trip_assistant` 与 destination-only multi-leg 的残余错例。  
  原因：之前缺少一套专门针对导航槽位的 hard-case benchmark，导致实现虽然能通过回归，但没有独立数字来暴露边界退化点。  
  改进方案：本轮已新增 `navigation_hard_cases_v1` 数据集和 `run_navigation_benchmark.py`；首轮本地结果 `12/14` 已明确暴露两条当前真实缺口，后续继续围绕这些 case 收口规则和槽位切分。

- 问题：E2E QA benchmark 之前只能跟随服务端默认模型，切换 gemini / qwen / doubao 做主链路横评时需要改环境或重启服务，跑数口径不稳定。  
  原因：`/api/v1/qa/ask` 请求体此前不接受主链路 `provider/model` override，benchmark runner 也没有多模型 sweep 入口。  
  改进方案：本轮已让 `/api/v1/qa/ask` 支持 request-level `llm_provider` / `llm_model`，并在 shared runtime 中注册 `volcengine` / `doubao` provider；`run_e2e_qa_benchmark.py` 也已支持 `--sweep` 和聚合 Excel 导出，后续可在单次服务启动下做 apples-to-apples 横评。

- 问题：QA 主链路里，session-aware trip-assistant 的“当前路线 / 当前站点”查询会偶发漂到生成式回答，导致答案虽然可读，但不稳定包含当前 stop 名称与 route-aware 语义。  
  原因：这类英文 query 会先走 translator pivot，再进入 trip_assistant 结构化生成；如果只看 pivot 后中文句子，部分“当前站位”意图会被误当成普通行程建议，或者在 LLM 成功分支里产生不稳定措辞。  
  改进方案：本轮已把明确的 current-route/current-stop 状态查询从 trip_assistant 生成式路径中剥离，改为直接基于 session context 生成确定性回答；同时保留 `next route stop` 等 query 继续走结构化 trip_assistant 分支，并用 `tests/test_qa.py` / `tests/test_qa_routing_regressions.py` / `tests/test_rag_query.py` 61 条回归锁定行为。

- 问题：E2E benchmark 一度直接把 `real_rag_corpus_v1_zh.json` 当成当前上线 RAG truth，导致数据集里的深问 case 超前于 runtime 实际可检索能力。  
  原因：外部中文语料已经存在，但运行时建索引链路当前仍只使用 `rag_documents.py` 生成的 scaffold 文档，且 doc_type 只覆盖 `history/practical_notes/photo_spot_notes/family_notes`。  
  改进方案：已把 E2E 数据集收口到 current runtime truth，`real_rag_corpus_v1_zh.json` 暂只作为参考语料；后续如要恢复 `正阳门/中轴线/architecture/curation` 等深问 case，先补通 runtime ingestion 再扩 benchmark。

- 问题：RAG 深问在真实 E2E 中一度持续退回 `sql_only`，即使 backend/index 已 ready。  
  原因：RAG query filter 有两层错误叠加：`rag_retriever.py` 会注入当前 runtime 文档并不存在的 `poi_aliases` filter；`rag_index_service.py` 又把 `language/doc_type` 这类 list filter 用标量 `!=` 直接比较，导致有效向量结果被过滤空。  
  改进方案：已移除不存在的 `poi_aliases` filter，并把 metadata filter 收口为 list/scalar membership 匹配；新增 `tests/test_rag_backend.py` 与 `tests/test_rag_query.py` 锁定行为，且在 fallback-on `8002` 服务上定向复测 `E2E-RAG-001/002/003` 均已恢复 `sql_then_rag`。

- 问题：benchmark 最优模型结论与产品主链路最终选型可能不一致，导致默认配置、README、readiness 文档仍停留在旧模型口径。  
  原因：E2E sweep 的阶段性最优是 `qwen-plus`，但产品最终决定改为 `Doubao Mini` 非思考模式；若只记录 benchmark 结论而不同步默认配置入口，后续 session 很容易继续沿旧默认值运行。  
  改进方案：把“benchmark 结论”和“正式默认选型”分开记录；一旦产品决策落锤，同轮必须同步 `src/yoyo/core/config.py`、README、readiness 文档与阶段摘要，避免代码默认值和文档入口继续漂移。

- 问题：适合 Gemini 一类模型的英文长 prompt，直接迁移到 Doubao Mini 这类非思考小模型上，容易带来 token 浪费和输出漂移。  
  原因：旧 prompt 把能力边界、grounding 规则和输出要求写成长段英文说明，同时把 attraction / profile / session / rag / dialogue 较完整地塞进 user prompt；对小模型来说，上下文冗余越大，越容易答偏或格式不稳。  
  改进方案：已把 `src/yoyo/modules/qa/prompts.py` 收口为中文短结构：system prompt 仅保留“角色 / 能力边界 / SQL-RAG grounding / 输出格式”四段；user prompt 继续按 intent 分流，但 attraction、RAG chunks、dialogue 和 session 字段都先裁剪后再送入模型，先用定向回归锁住行为，再继续观察真实链路质量。

- 问题：如果只强调“小模型短 prompt”，但不把字数控制、长回复格式和历史窗口写成显式规则，生成长度和上下文使用仍会漂。  
  原因：模型会自然倾向于在知识性问题上展开，若没有统一约束，可能出现回答忽长忽短、长回复不分段、或只看最近 2~3 轮而忽略稍早对话。  
  改进方案：已把 `answer` 长度规则写入主回答 prompt：默认 300 字以内，能短答就短答；历史/文化深问可适度长，但长回复必须分 2~3 段。同时把主回答的 dialogue history 窗口扩到最近 10 轮，并把当前 prompt 单独沉淀到 `docs/qa-prompt-doubao-v4.md`，便于后续继续改文稿。

- 问题：`trip_assistant` 已成功调用 Doubao，但结构化结果会因缺失 `reason`、枚举字段带空白、或布尔值写成字符串而被整体判成 `structured_output_valid=false`，随后直接退回 formatter fallback。  
  原因：Doubao 小模型在 JSON 输出上存在轻微格式漂移，而 parser 之前按严格 schema 直接验证，没有给这类 near-valid 输出留极小的归一化缓冲。  
  改进方案：已同时收紧 prompt 输出契约，并在 `src/yoyo/modules/qa/generator.py` 增加有边界的 payload normalizer，只修复缺失 `reason`、首尾空白和字符串布尔值；其余非法结构继续 fail-closed。

- 问题：显式 translation 在真实主链路里一度仍频繁落到 `missing_translation_text`，即使 `_parse_explicit_translation_query(...)` 本身已补了中文模式。  
  原因：translation intent 实际上传给 `translate_for_qa(...)` 的是 pivot 后的 `effective_query`，原始 query 里的引号短句和英文正文在 preprocess 后已经被改写，导致后续 extraction 逻辑看不到真正要翻译的文本。  
  改进方案：已把 `src/yoyo/modules/qa/orchestrator.py` 改为 translation intent 优先传 `raw_query`，并在 `src/yoyo/modules/translator/service.py` 增加保守兜底提取，确保“译成中文 / 给工作人员看”问法能真正进入 plain MT。 

- 问题：translation service 已按“默认译成中文”收口后，`src/yoyo/modules/qa/rule_assets.py` 里仍残留“翻成英文 / 用英文怎么说”这类旧直短语和归一化规则，导致规则层语义与主链路产品定义不完全一致。  
  原因：前一轮主要先修了 runtime translation 成功路径与 Doubao 结构化问题，规则资产层还保留着更早的英文目标语义。  
  改进方案：本轮已把 rule assets 的 translation 归一化、direct phrases 和 language keywords 一并收口到“翻成中文 / 给工作人员看”，并用 `tests/test_qa_routing_regressions.py` 的定向回归锁定行为。 

- 问题：真实 QA 冒烟里，weather/navigation/route-edit/out-of-scope 这些非生成式意图仍返回英文文案，看起来像主模型没收口，但实际问题在短路 formatter。  
  原因：这些 intent 直接走 `formatters.py` / `orchestrator.py` 的确定性分支，绕过了 Doubao 主回答链路，因此即使主 prompt 已中文化，旧英文 fallback 文案仍会原样暴露给用户。  
  改进方案：后续每次修 QA 主链路时，都要把“短路分支的用户可见文案”与“生成式 prompt 文案”一起检查；本轮也已把相关回归断言全部改成中文并重新跑通。  

- 问题：显式 route 句式 `从天安门怎么走到故宫？` 会把 `怎么走` 残留在 `origin_name`，导致真实导航回答出现污染槽位。  
  原因：`hybrid_context_builder.py` 之前在 `从A到B` 规则路径里只做了粗粒度切分，没有对地点片段额外清洗导航动作残片。  
  改进方案：已补轻量 `place-fragment` 清洗并用 `tests/test_navigation_slot_extraction.py` 锁定显式 route / destination-only / multi-leg 三类行为。 

- 问题：`帮我把‘Where is the restroom?’翻给工作人员看` 在中文界面下虽然已正确路由到 `translation`，但 plain-MT 仍会把源语言硬绑成 `user_language=zh`，把英文原句错误发成 `zh -> zh`。  
  原因：`_plain_mt_translate_for_qa(...)` 之前直接把 `source_language = user_language`，没有区分“界面语言”和“显式翻译原句语言”；在 `show_to_local` 场景下，这会把中文界面里的英文 quoted text 误标成中文源语言。  
  改进方案：已把 explicit QA translation 的 source-language 选择收口成：若 `user_language` 与 `target_language` 同语种，则传 `None` 让 provider auto-detect；否则继续沿用 `user_language`。同时补了 translator 与 QA 两侧回归，锁定 `language=zh + 英文 quoted text + show_to_local` 行为。 

- 问题：`我现在到哪一站了？` 在带真实 `guide_session_id` 的主链路里会误落到 `live_info`，看起来像 session context 没生效。  
  原因：实际不是 session context 缺失，而是规则层只抓到了 `现在` 这种 live 弱信号，没有把“哪一站 / 当前站 / 现在到哪”识别成 trip-status 强信号；同时 navigation/trip conflict 兜底也没有给当前站点状态问法开豁免。  
  改进方案：已补 trip-assistant 直短语与关键词、增加 current-stop status conflict 豁免，并新增路由与 API 级回归锁住；同时把 `format_trip_assistant_answer(...)` 的确定性 fallback 文案中文化，避免该短路链路继续暴露英文回答。 

- 问题：weather target fallback 已经接入后，新增回归测试一度仍失败，看起来像主链路实现没生效。  
  原因：实际不是 runtime 逻辑错误，而是测试替身与真实 schema/方法签名漂移：builder 级 fake weather 返回值不满足 `WeatherContext` 校验，API 级 monkeypatch `AmapRouteClient.get_weather` 时又漏了实例方法的 `self` 参数。  
  改进方案：测试替身尽量返回真实 schema 实例，实例方法 monkeypatch 也要对齐 `self` 签名；当前 weather 定向回归 `pytest tests/test_qa.py -k "weather" -v` 已恢复 `3 passed`。 

- 问题：weather fallback 模型如果同时看到 query 和 session context，容易把上下文当成强信号，覆盖用户明说的地点。  
  原因：初版 prompt 只说明了“优先抽地点”，但没有显式声明“显式地点优先于 session_context”“上下文只作弱提示”的优先级。  
  改进方案：prompt 里直接固化优先级：先看 `query/raw_query/pivot_query` 的显式地点，再把 `session_context` 作为省略问法弱提示；并明确禁止上下文覆盖用户显式地点。 

- 问题：`language=en` 但 query 同时包含英文指令和中文原句时，QA orchestrator 会把整句直接当中文处理，导致 mixed-language translation query 绕过 preprocess-first 链路并误落到 `out_of_scope`。  
  原因：`_should_treat_query_as_zh(...)` 之前只要发现英文请求里含有 CJK 字符，就直接按中文直路由，没有再区分这是不是“英文指令 + 中文原句”的显式翻译场景。  
  改进方案：已把该判断收口为“仅当 `language=en` 且全文不含拉丁字母时才视作 CJK 直路由”；mixed-language query 继续走 translation preprocess / routing 主链路，并用 `tests/test_qa.py -k "translation"` 回归锁定。 

- 问题：QA playground 一度点击一次“发送 QA 请求”就先跑 `preview` 再跑 `ask`，同时页面默认还预填了大量 `session/profile/attraction/dialogue_history` override，导致真实体验同时表现为“慢”和“答偏”。  
  原因：playground 初版把“联调预览”和“真实问答”耦合到同一个按钮里，又为了展示能力预填了过重的默认 payload，结果页面本身就人为叠加了额外请求成本和上下文噪音。  
  改进方案：已把 Ask 改成只调用一次 `/api/v1/qa/ask`，Preview 保持独立；默认表单改为最小 payload，仅在用户显式填写或切 preset 后才注入 `context.qa_playground`。同时补出 `metadata.latency_ms` 分段耗时和页面摘要区，后续再遇到“慢/答偏”时可以先区分是 playground 问题还是 QA 主链路问题。 

- 问题：`context_build_ms` 之前只统计整段上下文构建总时间，排查天气/导航慢链路时看不出究竟慢在景点/profile 查询、slot fallback、Amap 调用还是 RAG。  
  原因：`build_hybrid_context(...)` 一直把多种内部/外部上下文获取动作打包成单个阶段，orchestrator 只暴露了总时长，没有把子步骤埋点透传到 metadata。  
  改进方案：已在 `build_hybrid_context(...)` 内补细分埋点，并把结果通过 `metadata.latency_ms.context_build_breakdown_ms` 暴露出来；后续性能分析优先看 breakdown，再判断是否真的加载了不必要上下文或只是某个外部依赖抖动。

- 问题：天气问句在旧链路里常常要串行打两次模型，一次做 router fallback，另一次再做 weather slot fallback，导致 routing 看起来不慢但整条链路被额外拉长。  
  原因：旧实现把“天气意图判定”和“天气地点抽取”拆成了两个独立 fallback 阶段；当规则没抽到地点时，即使 router fallback 已经基本知道用户在问天气，也还要在 context build 阶段再打一轮模型。  
  改进方案：已收口为 router fallback 在 `weather_info` 时一次同时返回 `intent + weather_location_name`；只有规则已命中天气且已抽到地点时才跳过 fallback，其他情况统一走这一次 router fallback，后续 weather target 解析直接复用该结果，不再额外调用第二次 weather-slot fallback 模型。

- 问题：原 E2E QA benchmark 只能比较总体请求时延，无法判断慢在翻译预处理、路由 fallback、上下文构建、回答生成还是回答回译。  
  原因：runner 只记录外层 HTTP wall time，没有把 `/api/v1/qa/ask` 返回的 `metadata.latency_ms` 与 context build breakdown 平铺到 case 明细和模型汇总里。  
  改进方案：已新增全链路多语言 benchmark 数据集与 qwen-turbo / Doubao Mini sweep 配置，并扩展 `evals/run_e2e_qa_benchmark.py`，按 case 和聚合维度输出 `preprocess/routing/context_build/generation/postprocess` 及 RAG / 天气 / 导航 / attraction / profile lookup 子阶段耗时。

- 问题：本轮全链路 benchmark 前置检查里，`alembic upgrade head` 因多个 head 失败，8000 端口也出现占用但不可连接的状态。  
  原因：当前迁移分支存在 `0002_add_guide_playback_state` 与 `0009_add_guide_segments_to_attractions` 两个 head；本地 8000 端口状态不稳定，不能默认作为 benchmark 服务端口。  
  改进方案：benchmark 前置步骤改为 `.venv/bin/alembic upgrade heads`，并在端口探测失败时使用备用端口启动 API；本轮实际在 `127.0.0.1:8001` 完成 health、QA、RAG、planning API 检查和 qwen-turbo / Doubao Mini sweep。

- 问题：第一版 `e2e_model_sweep_results.xlsx` 虽然导出了机器字段和中间 JSON，但人工评审时需要横向找原 query、最终 answer、阶段结果和总时延。  
  原因：`cases` / `review_cases` 仍按数据字段组织，最终回答和链路结果没有排在前面，也没有把各阶段结果压缩成人可扫读的摘要。  
  改进方案：已把 `review_cases` 重排为人工主表：原始 query、中文释义、最终 answer、总时延、结论、意图、模型，以及预处理/路由/SQL/RAG/实时信息/天气/导航/生成/翻译/回译的结果和耗时，并加冻结表头、筛选和长文本换行。

- 问题：qwen-turbo 全链路 benchmark 中，`live_info` case 的 context build 明显偏慢，单次外部搜索约 `2.6s-3.5s`。  
  原因：每次同类“今日开放/营业/公告”问题都会重新请求 live search provider，缺少按日期、景点和 live 信息类型复用的短缓存。  
  改进方案：已在 `build_live_info_payload(...)` 外围接入 Redis 短缓存，cache key 收口为 `{beijing_date, attraction, info_type}`，并为普通结果、闭馆公告和 provider 失败分别设置 TTL；metadata 和 E2E 导出现在会暴露 `live_info_cache_hit`、`live_info_info_type` 等字段。

- 问题：现有规则路由容易把单个关键词当成 intent 证据，典型例子是“你好，请问故宫有什么历史”可能被寒暄词干扰。  
  原因：规则资产仍偏关键词加分模型，没有把礼貌前缀、任务主体、实体槽位、必要条件、禁止条件和冲突裁决分层维护。  
  改进方案：已先补出不接入 runtime 的规则维护资产：`docs/qa-intent-keyword-library.yaml` 与 `docs/qa-intent-routing-rule-design.md`。新方案把规则拆成 QueryFrame、politeness stripping、entity/slot evidence、intent policy、conflict resolver 与 fallback 裁决，后续接入前先用 router-only benchmark 验证 hard-negative。

- 问题：如果继续给英文和东南亚语言分别维护路由关键词，规则库会重复膨胀，且 raw 英文里的 `hello/hi` 仍可能干扰 smalltalk 判断。  
  原因：外语 query 的意图判断不应该在规则层直接解决；项目已经有 translator preprocess，规则层应只消费统一的中文 canonical query。  
  改进方案：已把规则路由设计收口为“外语先转中文，再进入中文规则评分”；关键词资产明确 `scoring_language=zh`，非中文词条只作为历史/调试参考，不作为第二套路由词库扩展方向。

- 问题：规则库后续如果靠人工不断补关键词，会快速变成不可解释、不可回归的经验规则堆。  
  原因：错例来源可能在 translator、规则、fallback 或下游链路，不能把所有问题都归因到词库缺失。  
  改进方案：已新增 `docs/qa-intent-rule-maintenance.md` 和 100 case 日常维护集 `evals/datasets/routing_rule_maintenance_100_cases.yaml`，并跑出首轮 rules-only 基线报告 `docs/routing-rule-maintenance-benchmark-2026-05-15.md`；后续规则调整必须带正例、负例、冲突例和 benchmark 回归。

- 问题：只靠 100 条维护集仍可能把规则调成“看起来通过、但遇到长口语和多意图就误直达”的状态。  
  原因：原维护集覆盖了主要 intent，但复杂否定、多意图、边界词污染、外语 pivot 后中文和 session-aware 表达还不够密。  
  改进方案：已新增 200 条复杂 hard cases，并用 `evals/datasets/routing_rule_all_300_cases.yaml` 汇总成 300 条长期回归集；同时给 runner 增加 `safe_accuracy`、`direct_pass_precision`、`false_direct_pass_cases` 指标。本轮修复后 300 条合集达到 `accuracy=0.90`、`safe_accuracy=0.95`、`direct_pass_precision=1.0`、`false_direct_pass=0`。

- 问题：300 条 routing 回归集仍不足以压出“规则直达很准、但复杂边界召回不足”的细分缺口，特别是能力询问混任务词、`开放到几点` 误触发 route-edit、`不用查 + 开不开` 这类否定结构。  
  原因：规则层仍以关键词/短语加分为主，部分中文结构需要额外的冲突裁决和否定识别；如果只补简单 case，会掩盖这些边界。  
  改进方案：已新增 `evals/build_routing_rule_hard_500_dataset.py` 和 500 条 hardcase，并通过 `routing_rule_all_800_cases.yaml` 汇总成长期回归集；本轮同步把修复落到主链路 `intent_router.py` / `rule_assets.py`，最终 500 hard 与 800 all 都达到 `safe_accuracy=1.0`、`direct_pass_precision=1.0`、`false_direct_pass=0`。

- 问题：导航请求里 `天坛` 等同名/短名景点可能被高德自由 geocode 解析到北京以外，且 `下一站怎么去` / `到X怎么走` 没有显式区分 GPS 起点、current stop 起点和 query 显式起点。  
  原因：旧导航 slot 只保留地点名字符串，缺少本地北京地点注册表、坐标直传、adcode 校验和可审计的 place_id；fallback 模型也容易被误用成地点最终裁决器。  
  改进方案：已新增 `place_resolver.py` 维护北京导航地点库，slot schema 增加 `origin_place/destination_places`，destination-only 与 next-stop 优先用 GPS/current stop，explicit route 保持 query 起点优先；高德 client 支持坐标直传并对 geocode 结果做北京范围校验。本轮新增 100 条导航专项 case，slot-only benchmark 达到 `pass_rate=1.0`。

- 问题：复杂口语导航问法初跑只有 `pass_rate=0.81`，例如“故宫好美啊，想去X怎么走”“从故宫出来...从这里到X”“别推荐路线替换方案，接着去X怎么走”会被 trip-assistant、manual-route-edit 或错误起点解析干扰。  
  原因：导航规则只覆盖了较干净的 `从A到B` / `去X怎么走`，没有处理嵌入式目的地标记、前置叙事里的多个 `从`、`当前站` 与 GPS 的语义差异，也没有把 `分段路线` 作为导航动作。  
  改进方案：已把嵌入式目的地问法纳入主链路导航优先级，显式路线改为右侧 `从` 候选优先，`当前站/现在这个站` 回填 `current_stop_name`，`这里/我这儿` 保留 GPS；新增复杂混合 100 case 后 base 100 与 complex 100 均达到 `pass_rate=1.0`。

- 问题：补强导航召回后，800 条通用路由合集一度出现 11 条 false direct pass，集中在“别导航，下一站去哪”、条件式改路线和停车场边界。  
  原因：嵌入式目的地规则把否定导航词也当成导航强信号；天气词在 `如果下雨，就把X挪到明天` 中压过了改路线动作；停车场/车位请求里 `怎么走` 又把 out-of-scope 边界拉回导航。  
  改进方案：已补 `别导航/先别导航/别急着导航` 导航否定、`就把 + 改路线动作 + 景点` 条件式改路线形态，以及 parking boundary 优先级；复跑 800 条合集达到 `safe_accuracy=1.0`、`direct_pass_precision=1.0`。

- 问题：`transit` 只作为公共交通大类时，用户明确说公交仍可能拿到地铁方案，或明确说地铁却拿到纯公交方案，人工看表会发现 pass 结果与真实体验不一致。  
  原因：槽位层没有保留公交/地铁偏好，高德返回解析也只判断是否有公共交通步骤，没有校验最终乘车类型是否满足用户显式偏好。  
  改进方案：已新增 `transit_preference=bus/subway/public_transport`，高德 transit 查询按偏好筛选方案，formatter 按最终车辆类型展示 `公交/地铁/公交+地铁`，benchmark 导出偏好与车辆类型并把偏好不满足计为不合理结果；真实高德 300 复跑仍保持 `pass_rate=1.0`。

- 问题：真实高德结果里，`332路(前门--地铁北宫门站)` 这类公交线路会被标成包含地铁，导致地铁偏好 case 可能误通过并显示 `公交+地铁`。  
  原因：车辆类型识别直接扫描整条线路名，终点站名里的“地铁”被当成线路类型信号。  
  改进方案：已改为优先读取高德 `busline.type`，无 type 时只检查括号前的线路主体名，并补回归测试锁定公交到地铁站不算地铁方案。

- 问题：导航否定如果继续按 `别导航/先别导航/不用导航` 合成短语维护，会把“否定方式”和“被否定对象”绑死，后续每加一个表达都要复制多条组合规则。  
  原因：否定词和业务对象词属于两类独立资产，合并维护会让词库膨胀，也更容易遗漏 `别急着导航` 这类口语变体。  
  改进方案：已把导航否定改成 `NEGATION_OPERATOR_KEYWORDS` + `NAVIGATION_NEGATION_TARGET_KEYWORDS` 的短窗口组合判断；当前只把 `导航/文字导航` 作为导航否定对象，避免 `别改路线，从A到B怎么走` 被误伤；同时给 `别的` 加边界保护，避免 `不用推荐别的景点，导航到X怎么走` 被误判为导航否定。

- 问题：公共交通问法此前被当作地铁/公交边界拒答，且用户未指定出行方式时只能走配置默认步行，长距离景点间路线不符合实际使用预期。  
  原因：导航 schema 只有 `walking/driving`，Amap client 没接 `/v3/direction/transit/integrated`；默认 mode 在槽位解析前就固定，无法利用已解析地点坐标做距离判断。  
  改进方案：已把导航 mode 扩展为 `walking/driving/transit` 并增加 `mode_source`；显式出行方式优先，未指定方式时用 hydration 后的连续路段最大直线距离做 3km 阈值判断，超过默认公共交通，否则默认步行；Amap client 已接入 transit endpoint，导航 benchmark 的旧公交边界 case 已同步改为 supported transit case。

- 问题：近期 QA 规则讨论分散在多个设计文档、benchmark 报告和 retrospective 条目里，新会话续接时不容易快速看到“问题是什么、最终规则是什么、改哪里”。  
  原因：专题文档适合保存细节，但缺少一个轻量的中心决策日志；README 也只列入口，没有把规则变更的 problem/solution 关系集中起来。  
  改进方案：已新增 `docs/qa-rule-decision-log.md`，把外语转中文、寒暄冲突、规则直达/fallback、live_info 缓存、导航槽位、多段拆分、同名消歧、否定词拆分、公共交通和 3km 默认方式等规则按“问题 / 解决方式 / 维护位置”汇总；README 和 phase summary 已加入口。

- 问题：300 条真实高德导航 benchmark 初跑中，multi-leg 出现较多 `provider_request_failed`，会把连续压测造成的 provider/network 抖动混入“高德路线能力”指标。  
  原因：runner 连续快速请求真实高德，multi-leg 单 case 又会短时间内多次调用路径规划；Amap client 请求层此前没有重试，runner 也没有 case 间隔。  
  改进方案：`AmapRouteClient._get_json(...)` 已增加 3 次轻量重试，`evals/run_navigation_benchmark.py` 已增加 `--case-delay-ms`、高德时延和路线质量导出；最终 300 条复跑达到意图准确率 `1.0`、槽位准确率 `1.0`、高德合理返回率 `0.95`，剩余失败均为 3km 内显式 transit 无公交/地铁方案。

- 问题：3km 内显式公交/地铁导航如果没有公共交通方案，真实高德会返回空路线，用户看到的是导航失败而不是可执行路线。  
  原因：旧链路把 `transit + empty_navigation_payload` 直接作为 degraded 返回，没有做产品级兜底；benchmark 也没有导出最终用户回复，人工看表只能看状态字段。  
  改进方案：已在导航主链路增加 `transit` 空结果转 `walking` 重查，最终话术为“当前没有合适的公共交通，返回给你步行方案。”且不暴露 provider 名称；benchmark 新增 `amap_final_answer`、`amap_final_mode` 和 fallback 标记，真实 300 条复跑达到 `pass_rate=1.0`。

- 问题：`从颐和园到北海公园坐公交/地铁` 在结果表里看起来像全程步行，multi-leg 也只展示每段前三个细分动作，人工检查时不容易看出真实路线。  
  原因：transit 结果中“步行到站”可能有十几条细分 step，formatter 只取前三条导致关键 `乘坐...` 步骤被截掉；同时 provider 层也没有校验 transit payload 是否真的包含乘车段。  
  改进方案：formatter 现在会为公共交通路线强制保留乘车步骤，多段路线增加路线总览和每段距离/耗时；Amap transit payload 如果完全没有乘车步骤则视为无合适公共交通并走步行兜底。修复后 300 条真实 benchmark 仍为 `pass_rate=1.0`，且所有 `final_mode=transit` 的最终回复都包含 `乘坐`。

- 问题：SQL/RAG 分流用宽泛“历史/讲解”词触发 RAG 时，会让 SQL mock 数据已经覆盖的景点基础问答也进入 RAG，既重叠又增加时延。  
  原因：旧 fallback 判定没有把“SQL 已覆盖字段”和“SQL 未覆盖深问”拆开，只按 attraction_explain 的深浅关键词粗略触发。  
  改进方案：已把 RAG 触发收口到中轴线、象征意义、建筑秩序、深层历史/策展等 SQL 未覆盖问题；SQL 直接字段保持 `sql_only`。当前 mock 数据外但仍属于北京景点的问题允许用模型常识回答并标记 `model_knowledge`，后续真实 SQL/RAG 数据拆分完成后再调整测试期望。

- 问题：真实高德 300 条 benchmark 在沙箱内初跑全部 `provider_request_failed`，表面看像高德链路全挂。  
  原因：本地沙箱限制外网 DNS，真实 Amap API 请求无法解析域名；链路自身在放开网络后可正常返回。  
  改进方案：真实高德 benchmark 必须在允许外网访问的运行环境执行；本轮放开网络后复跑 `navigation_slot_hard_300_cases` 达到 `pass_rate=1.0`，并确认 332 路这类公交到地铁站场景不再误判为 subway。

- 问题：E2E hardcase 中，`第一次用这个导游，简单说说你会怎么回答问题`、`能力边界` 等能力说明类 query 被 fallback 漂到 `out_of_scope` 或 `trip_assistant`，导致 smalltalk 通过率初跑只有 `0.705`。  
  原因：smalltalk 词库只覆盖寒暄和少量身份问法，没有把“能力说明/第一次使用/你会怎么回答问题”作为高置信 capability query；同时 fallback 对这类多任务词样例容易按业务词重新分类。  
  改进方案：已把能力说明短语加入主路由规则，并允许高置信 capability query 规则直达；smalltalk 200 条重跑达到 `200/200`，p50 约 `6.7ms`。

- 问题：`不要把它误当成改路线`、`不用操作行程`、`不要删除任何景点` 这类元否定在 E2E hardcase 中仍可能触发 `manual_route_edit_redirect`。  
  原因：规则层看到了“改路线/操作行程/删除”这些强词，但否定保护没有覆盖“这是元说明，不是业务动作”的句式；部分 trip-assistant 场景还会因 `trip_vs_edit_conflict` 进入 fallback，被模型覆盖成改路线。  
  改进方案：已补 route-edit negation 词库，并对 `trip_assistant + route_edit_negation` 增加 fallback 保护；trip_assistant 200 条重跑达到 `200/200`。

- 问题：越南语等外语包裹的 `Python 爬虫` case 在翻译预处理后丢失硬拒绝关键词，后续误进 `live_info`；`帮我订票并付款` 也被实时票务词带进 live_info。  
  原因：domain guard 只看翻译后的 effective query，没有同时保留 raw query；路由边界也缺少“代订/付款/下单”这类交易执行型旅游邻接规则。  
  改进方案：domain guard 现使用 `effective_query + raw_query + pivot_query` 合并文本；新增 `transaction_boundary`，把代订、付款、下单、直接支付归 out_of_scope。out_of_scope 200 条重跑达到 `200/200`。

- 问题：主链路 qwen-turbo 1800 条 E2E benchmark 中，整体通过但 navigation_text 的 p95/max 明显高，最慢 case 达 `46518ms`。  
  原因：真实高德导航查询是串行外部依赖，多段路线和个别步行/公交查询会出现 30s+ provider 长尾；该链路没有回答生成耗时，主要慢在 `navigation_lookup_ms`。  
  改进方案：本轮先记录为非阻塞性能风险，Excel 已导出每条 case 的 `navigation_lookup_ms` 和最终 answer；后续建议给单段高德调用增加更严格的超时、缓存或 degraded 兜底上限。

- 问题：步行导航回复虽然有距离和转向，但缺少“走到哪里再转”的节点信息，长路线还会被截断成“后续按现场导航”。  
  原因：Amap walking step 中的 `orientation/polyline` 没有透传，formatter 只读 raw instruction 并对纯步行固定取前 5 步。  
  改进方案：已保留 step `polyline/end_location/orientation`，用终点逆地理补 `turn_location_text`，最终展示“沿路名/方向步行约 N 米，到路口/POI 附近，转向”；纯步行不再固定截前 5 步，并新增真实高德 turn point smoke。

- 问题：多样地点 smoke 中，`正阳门` 被高德自由 geocode 到朝阳同名建筑，`水立方` 简称 geocode 失败，导致路线目标错或不可用。  
  原因：本地导航地点库只覆盖少量核心景点，Amap client 直接调用时没有先查本地注册坐标。  
  改进方案：已扩充北京 POI 注册库，并让 Amap client 在无显式 GPS 时也先用本地坐标，再退到 geocode；复跑 8 条多地点真实高德 smoke 全部 `available`。

- 问题：用北京旅游网景区 CSV 批量扩展导航白名单时，短名/泛名条目可能被高德 geocode 到错误地点，例如园林短名、商业街、楼宇或同名商户。  
  原因：geocode 对短词和泛称没有足够的旅游语义约束；如果再自动生成去后缀 alias，会让 `史家胡同` 这类普通地名误命中 `史家胡同博物馆`。  
  改进方案：已新增 `evals/build_navigation_place_registry.py`，采用 POI 文本检索优先、北京 adcode 校验、地址/行政区匹配、商业类型降权、近分候选进审核；生成库不自动生成简称 alias。本轮纳入 127 个高置信景区，23 个低置信/歧义项留在 `evals/results/navigation_place_registry_geocode_20260516.json` 审核清单，并补 `tests/test_navigation_place_registry.py` 锁定注册规模和低置信不入库。

- 问题：`正阳门餐厅`、`正阳门北京环球金融中心` 这类 query 里包含核心景点 alias，如果继续允许注册 alias 子串直达，会把用户想去的商户/楼宇误导航到景点。  
  原因：运行时地点解析只区分 exact alias 和 substring alias，没有先检查商业、楼宇地址、附近指代等歧义信号；QA 多轮记忆也没有把“上轮澄清候选”和“本轮选第几个”串起来。  
  改进方案：已在 `PLACE_AMBIGUITY_KEYWORDS` 维护分类歧义词库，命中后返回 `registered_alias_with_ambiguity_signal` 而不是核心景点；导航取数层会在 direction 前返回 `status=clarification` 和候选列表；orchestrator 支持最近一轮导航澄清后的 `第1个/选第一个/候选名称` 续接，并回填候选坐标继续路线规划。

- 问题：地点澄清后的用户回复不一定是编号，可能说“上面的、下面的、中间的”；也可能说出不存在的编号，例如只有两个候选却说选第三个。  
  原因：如果把这类选择交给 LLM 兜底，模型可能擅自猜测候选或坐标，破坏导航链路的可审计性。  
  改进方案：已把澄清选择续接做成确定性规则：上面=第 1 个，下面/最后=最后一个，奇数候选的中间=正中，偶数候选的中间和编号越界都继续澄清；补回归锁定不发起错误路线规划。

- 问题：仅靠确定性规则仍会漏掉少量澄清回复，比如用户说“我说的是那个吃饭的地方，不是景点”，同时也可能在上一轮澄清后突然问天气或景点讲解。  
  原因：普通 intent fallback 只有最近历史原文，不知道上一轮候选的结构化列表；如果另建窄澄清通道，又可能把新意图误压回导航。  
  改进方案：已复用当前 router fallback 模型配置，在存在 pending navigation clarification 且规则未解析出选择时，动态注入结构化候选列表；fallback 输出同时包含真实 intent 与 `clarification_action`，只允许选择已有候选编号，不允许编坐标。新意图正常路由，低置信或无法判断则继续澄清。

- 问题：导航之外的 weather、live_info、translation、trip_assistant 等后续也可能需要澄清，如果每个 intent 各自写完整 fallback 链路会重复；但如果用一个大模型 prompt 统一处理所有澄清，又会把不同业务 schema 混在一起。  
  原因：澄清有通用语义（第几个、上面、下面、是否换话题），但澄清对象是强业务类型：导航选地点，天气选地点/日期，翻译选文本/语言，不能互相复用执行 schema。  
  改进方案：架构记录为 typed clarification state：每个 intent 自己维护 pending state 和规则澄清；fallback runtime/model 配置共用，但 prompt 按 clarification 类型动态注入，模型只允许选择或补全该 state 的字段。导航地点澄清作为第一版实现，后续其他 intent 按同一模式扩展。
