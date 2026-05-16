# Yoyo 功能测试说明

这份文档是当前 Yoyo 后端能力的**功能级测试说明文档**。

它要回答三件事：
1. 这个功能是做什么的？
2. 这个功能当前是怎么做的？
3. 这个功能应该怎么测试？

它**不会替代**其他测试文档，而是把它们串起来：
- `docs/api-contracts-fullstack.md` -> API 契约与字段语义的事实来源
- `docs/demo-test-plan.md` -> 当前测试范围与优先级
- `docs/test-readiness-checklist.md` -> 执行顺序、环境准备与 smoke 检查
- `docs/e2e-qa-benchmark.md` -> QA 专项 E2E benchmark 方法
- `docs/test-rounds-log.md` -> 历史测试轮次记录

---

## 1. 测试文档分工

### API contracts
- 文档：`docs/api-contracts-fullstack.md`
- 作用：定义 request/response 契约、字段结构、运行时语义

### Demo 测试计划
- 文档：`docs/demo-test-plan.md`
- 作用：定义当前测试范围、优先级和主要场景

### Test readiness checklist
- 文档：`docs/test-readiness-checklist.md`
- 作用：定义执行顺序、环境准备和 smoke 验证清单

### QA E2E benchmark
- 文档：`docs/e2e-qa-benchmark.md`
- 作用：通过真实 `/api/v1/qa/ask` 链路评估 QA 表现

### Test rounds log
- 文档：`docs/test-rounds-log.md`
- 作用：沉淀历史测试结果与轮次结论

### 功能测试说明
- 文档：`docs/feature-test-guide.md`
- 作用：按功能逐项说明当前实现和测试方法

---

## 2. 测试矩阵总表（当前基础版）

| 功能 | 主要接口 / 入口 | 测试层级 | 当前状态 | 优先级 |
|---|---|---|---|---|
| Guest quick entry 与 questionnaire | `guest` / `questionnaire` APIs | 集成 / 链路 | 已覆盖 | P0 |
| Planning 与 itinerary creation | `planning` APIs | 集成 / 链路 | 已覆盖 | P0 |
| Session lifecycle | `session` APIs | 集成 / 链路 | 已覆盖 | P0 |
| GPS、playback 与 cognitive map | `gps` / `guide playback` / `map` APIs | 集成 / 链路 | 已覆盖 | P0 |
| Manual route edit | `planning edits` API | 集成 / 链路 / 边界 | 已覆盖 | P0 |
| Guide jobs、guide assets、cycle content 与 TTS | `guide` APIs + worker | 集成 / 链路 / 降级 | 部分覆盖，仍需真实环境加固 | P0 |
| QA ask | `qa` API | 集成 / 链路 / benchmark | 部分覆盖，仍需继续优化 | P0 |
| Translator（preprocess / postprocess / bilingual translation） | `qa` API + shared translator runtime | 单元 / 集成 / 降级 | 已建立第一轮自动化覆盖，仍需真实环境验证 | P0 |
| RAG admin 与 retrieval | `rag` APIs | 集成 / 降级 / 链路 | 部分覆盖，仍需真实环境验证 | P0 |
| Comments 与 share-card | `comments` / `share-card` APIs | 集成 / 链路 | 已覆盖 | P1 |
| Degraded 与外部依赖行为 | 多 provider / worker / config | 降级 / fault-injection / smoke | 部分覆盖，仍需继续加固 | P0 |
| Benchmark 与 E2E QA validation | evals / `/api/v1/qa/ask` | benchmark / E2E | 已建立基线，已支持多模型 sweep，仍需继续扩充 | P1 |

### 测试层级说明
- **单元测试**：验证局部逻辑、schema、状态判断、格式化与 fallback 决策。
- **集成测试**：通过模块协作或 API 调用验证主要行为。
- **链路测试**：按真实业务顺序串联多个模块验证状态一致性。
- **smoke / readiness**：验证当前环境是否可启动、可提测、可演示。
- **degraded / fault-injection**：验证 provider 缺失、配置错误、上游失败时的行为。
- **benchmark / E2E**：验证 QA 质量、路由准确率、真实系统链路表现。

### 当前状态标记说明
- **已覆盖**：已有较完整的自动化或文档化验证基础。
- **部分覆盖**：已有一部分验证，但仍存在明显空白或需要真实环境加固。
- **待补充**：尚未形成稳定验证面，后续需要补齐。

---

## 2.1 Translator（preprocess / postprocess / bilingual translation）

### 功能基本描述
这个功能负责把翻译从单一 QA intent 扩展成共享能力层。
它既服务于 multilingual query 的前置翻译，也服务于普通 QA 回答的回译，以及显式翻译请求的双语输出。

### 功能当前做法
- 当前共享 translator 覆盖三条路径：
  - query preprocessing：外语 query -> 中文 pivot
  - answer postprocess：内部中文回答 -> 用户语言
  - explicit QA translation：显式翻译请求 -> 用户可直接展示给本地人的双语输出
- 当前普通 QA 仍保留原有 intent routing 与 downstream handler，只是在需要时吃中文 pivot query。
- 显式 translation 不与普通 answer postprocess 共用 prompt，而是单独走产品翻译语义。

### 测试方法
- 验证 translator disabled 时会进入明确 degraded / fail-open 语义。
- 验证非中文 query 经过 pivot 后仍能命中正确 intent，并在回答阶段翻回用户语言。
- 验证显式 translation 请求可输出 bilingual lines。
- 验证 answer translation 失败时保留 degraded metadata；若用户语言为英文且内部答案仍为中文，应触发保守语言一致性兜底，避免直接把纯中文答案回给英文用户。
- 相关测试：
  - `tests/test_translator.py`
  - `tests/test_qa.py`
  - `tests/test_qa_routing_regressions.py`

### 测试分层
- 单元测试：translator schema、structured output、disabled / degraded 行为
- 集成测试：`/api/v1/qa/ask` 里的 preprocess / postprocess / explicit translation 路径
- 链路测试：multilingual query -> route -> downstream answer -> translate back
- smoke / readiness：provider 配置正确时能走通翻译链路
- degraded / fault-injection：provider 缺失、timeout、invalid structured output

### 当前覆盖状态
- 自动化覆盖：已建立第一轮基础覆盖
- 真实环境验证：已完成一轮 XFYun ITS 修复后复跑，`product_translation` 提升到 `4.69/5`、`routing_preprocess` 提升到 `4.74/5`
- 当前判断：**部分覆盖**

### 本轮执行重点
- 重点确认 translator 不会破坏原有 QA 主链路
- 重点确认 bilingual translation intent 的输出结构
- 重点确认 preprocessing fail-open 与 answer postprocess degraded 语义
- 重点确认 preprocess 后仍保留 raw query 信号，避免 multilingual translation 指令句和 manual route edit 漂移到错误 intent
- 重点确认 `帮我把‘Where is the restroom?’翻给工作人员看` 这类 display 场景在真实服务重启后仍稳定命中 `translation`
- 重点确认英文 deep-explain query 不会被 router fallback 误判成 `out_of_scope`，例如把紫禁城、中轴线、仪式、象征系统等深问保留在 `attraction_explain`
- 重点确认 `out_of_scope` / hard deny 早返回也会补齐 `latency_ms`，便于 playground 和 benchmark 统一解释链路耗时

---

## 2.2 QA live_info cache

### 功能基本描述
这个能力用于降低 `live_info` 的外部搜索延时。`live_info` 只处理同日或近时段的景点官方运营信息，如开放、闭馆、预约、检票、临时公告。

### 功能当前做法
- `build_live_info_payload(...)` 会先按 `日期 + 景点 + info_type` 查 Redis 缓存。
- 缓存 miss 时才调用 live search provider。
- provider 返回后写入标准化 payload，而不是缓存原始 provider response。
- provider 失败结果只短 TTL 缓存，避免短暂上游故障污染后续查询。
- Redis 不可用时静默 miss，不阻断 QA。

### 测试方法
- 同一景点、同一天、同一 `info_type` 的重复查询应命中缓存。
- 首次请求应记录 `live_info_cache_hit=false`，重复请求应记录 `live_info_cache_hit=true`。
- 临时闭馆/公告类 TTL 应短于普通开放信息。
- provider 降级结果只允许短 TTL 缓存。
- 不同 `info_type` 不应共用缓存，例如“今天开放吗”和“需要预约吗”。
- 相关测试：
  - `tests/test_live_search.py`
  - `tests/test_qa.py -k "live_info"`

### 当前覆盖状态
- 自动化覆盖：已覆盖 cache hit、cache miss 写入、key 归一、live_info API 回归
- 真实环境验证：待下一轮 live_info E2E benchmark 复测
- 当前判断：**部分覆盖**

---

## 2.3 Benchmark 与 E2E QA validation

### 功能基本描述
这个能力负责在真实 `/api/v1/qa/ask` 链路上做 QA 横评，而不是只看局部单测或 router-only benchmark。
它现在同时覆盖两条用途：
- intent / answer / metadata 的 E2E 质量验证
- 主链路回答模型的多模型横评（如 gemini / qwen / doubao）

### 功能当前做法
- 当前已有：
  - `evals/run_e2e_qa_benchmark.py`
  - `evals/datasets/e2e_qa_benchmark_cases.json`
- 本轮新增：
  - `/api/v1/qa/ask` 请求体可选 `llm_provider` / `llm_model`
  - E2E runner 可通过 request-level override 在单次服务启动下切换主链路模型
  - `--sweep` 模式可顺序跑多模型并聚合导出 Excel
  - 示例 sweep 配置：`evals/datasets/e2e_model_sweep_example.json`
  - 全链路多语言时延数据集：`evals/datasets/e2e_qa_fullchain_multilingual_v1.json`
  - qwen-turbo vs Doubao Mini sweep 配置：`evals/datasets/e2e_fullchain_qwen_doubao_sweep.json`
  - E2E runner 现已平铺输出 `preprocess_ms`、`routing_ms`、`context_build_ms`、`generation_ms`、`postprocess_ms` 和 RAG / 天气 / 导航 / attraction / profile lookup 子阶段耗时
- 当前 shared runtime 已支持：
  - `openrouter`
  - `dashscope`
  - `volcengine` / `doubao`

### 测试方法
- 先跑单模型 smoke，确认 `/api/v1/qa/ask` 在带 `llm_provider` / `llm_model` 时仍正常返回。
- 再跑 sweep，比较各模型的：
  - intent 命中率
  - pass rate
  - 平均时延
  - estimated total cost
- 同时检查 weather_info / navigation_text / translation / live_info / route-edit redirect 等主要 intent 是否都在数据集里覆盖。
- 当前 E2E 数据集的 grounding 口径应明确按 runtime truth 维护：SQL 题只依赖当前 SQL / seed 字段；RAG 题只依赖 `rag_documents.py` 当前真实会建索引的四类文档（`history` / `practical_notes` / `photo_spot_notes` / `family_notes`）。`real_rag_corpus_v1_zh.json` 现阶段仅作为参考语料，不应直接当作已上线 retrieval truth。
- 相关文件：
  - `evals/run_e2e_qa_benchmark.py`
  - `evals/datasets/e2e_qa_benchmark_cases.json`
  - `evals/datasets/e2e_model_sweep_example.json`

### 测试分层
- benchmark / E2E：真实 `/api/v1/qa/ask` 链路
- 集成测试：request-level model override 是否正确透传到 QA generator
- degraded / fault-injection：缺 key、provider 错误、模型不可用时的返回语义

### 当前覆盖状态
- 自动化覆盖：已补 request-level override 回归
- benchmark 基础设施：已支持 sweep 与 Excel 聚合
- 当前判断：**部分覆盖**

### 本轮执行重点
- 重点确认 request-level override 不破坏默认主链路
- 重点确认 gemini / qwen / doubao 三组模型可以在同一套 E2E 数据上 apples-to-apples 对比
- 重点确认新增 weather_info / navigation_text case 会进入正确 intent，而不是被旧数据集遗漏
- 重点确认全链路多语言 benchmark 能在中文、英文和东南亚语种下同时暴露准确率、总时延和每段链路时延

---

## 3. Guest quick entry 与 questionnaire

### 功能基本描述
这个功能负责在完整登录体系之外启动第一阶段用户流程。
它会创建 guest 身份、返回固定问卷，并保存问卷驱动的用户画像信息。

### 功能当前做法
- 主要接口：
  - `POST /api/v1/guest/sessions`
  - `GET /api/v1/questionnaire/flows/current`
  - `POST /api/v1/questionnaire/submissions`
- 当前 questionnaire 固定为 `v1`。
- `role_choice` 会在内部映射到 `guide_style_preference`。
- 输出结果会作为 planning、guide 和 QA 个性化的第一阶段画像基础。

### 测试方法
- 验证 guest session 能成功创建，并返回稳定的 guest 标识。
- 验证 questionnaire flow 的结构、固定版本和题目数量。
- 验证提交不完整答案时会被正确拒绝。
- 验证有效提交会正确创建或更新用户画像。
- 相关测试：
  - `tests/test_onboarding_flow.py`
  - `tests/test_api_flow.py`

### 测试分层
- 单元测试：questionnaire schema、答案校验、profile 映射
- 集成测试：guest session / questionnaire flow / questionnaire submission API
- 链路测试：guest -> questionnaire -> profile -> planning 前置链路
- smoke / readiness：接口可达、返回结构正确
- degraded / fault-injection：当前不是重点

### 当前覆盖状态
- 自动化覆盖：较完整
- 真实环境验证：需求较低
- 当前判断：**已覆盖**

### 本轮执行重点
- 作为第一轮正式执行测试的起点
- 重点确认：创建 guest、读取问卷、提交问卷三步在当前环境无回归

---

## 3. Planning 与 itinerary creation

### 功能基本描述
这个功能负责通过当前第一阶段的几种入口创建 itinerary。
它是后续 session、guide、map 和 QA 流程的起点。

### 功能当前做法
- 主要接口：
  - `GET /api/v1/planning/templates`
  - `POST /api/v1/planning/recommendations`
  - `POST /api/v1/planning/itineraries`
  - `GET /api/v1/planning/itineraries/{itinerary_id}`
  - `GET /api/v1/planning/itineraries/{itinerary_id}/versions`
- 当前支持的入口类型：
  - `template`
  - `manual_poi`
  - `ai_recommendation_selected`
- 系统使用 versioned itinerary，而不是直接维护一份可原地修改的路线状态。

### 测试方法
- 验证三种入口模式都能成功创建有效 itinerary。
- 验证 itinerary version 能被正确创建和读取。
- 验证 stop payload 结构完整。
- 验证非法输入会被稳定拒绝。
- 相关测试：
  - `tests/test_planning_entry_modes.py`
  - `tests/test_api_flow.py`

### 测试分层
- 单元测试：模板/推荐输入结构、planning request 校验
- 集成测试：templates / recommendations / itineraries / versions API
- 链路测试：planning -> itinerary creation -> version readback
- smoke / readiness：创建 itinerary 成功并可查回
- degraded / fault-injection：推荐与路线能力在缺少外部依赖时仍不崩溃

### 当前覆盖状态
- 自动化覆盖：较完整
- 真实环境验证：仍可补一轮 smoke
- 当前判断：**已覆盖**

### 本轮执行重点
- 重点确认三种入口都可正常建 itinerary
- 重点确认 itinerary version 与 stop payload 没有回归

---

## 4. Session lifecycle

### 功能基本描述
这个功能负责控制 guide session 的运行时生命周期。
它是整条出行执行链路的状态主干。

### 功能当前做法
- 主要接口：
  - `POST /api/v1/session/guide`
  - `GET /api/v1/session/guide/{guide_session_id}`
  - `POST /api/v1/session/guide/{guide_session_id}/start`
  - `POST /api/v1/session/guide/{guide_session_id}/finish`
  - `GET /api/v1/session/{guide_session_id}/current`
- session 状态明确区分为：`pending`、`active`、`finished`。
- 运行时状态通过 session context 和 `current_stop_index` 语义维护。
- `session current` 是前端和下游消费者的主要运行时真相源。

### 测试方法
- 验证 session create/start/finish 的状态流转。
- 验证 `current` 在 finish 前后都返回稳定结构。
- 验证 `trip_started_at` 和 `trip_finished_at` 的写入。
- 验证 route version 切换后运行时状态仍保持一致。
- 相关测试：
  - `tests/test_session_lifecycle.py`
  - `tests/test_api_flow.py`
  - `tests/test_a_validation_suite.py`

### 测试分层
- 单元测试：状态字段与上下文字段判断
- 集成测试：session create / start / finish / current API
- 链路测试：planning -> session -> start -> finish -> current
- smoke / readiness：session 能创建且 current 稳定返回
- degraded / fault-injection：当前不是首要重点

### 当前覆盖状态
- 自动化覆盖：较完整
- 版本切换后一致性：已有验证
- 当前判断：**已覆盖**

### 本轮执行重点
- 重点确认 start / finish / current 三个关键状态接口行为稳定

---

## 5. GPS、playback 与 cognitive map

### 功能基本描述
这个功能负责处理运行时位置变化、播放进度推进，并把这些状态投影到 cognitive map payload 中。

### 功能当前做法
- 主要接口：
  - `POST /api/v1/gps/update/{guide_session_id}`
  - `POST /api/v1/guide/playback/{guide_session_id}`
  - `GET /api/v1/map/session/{guide_session_id}`
- GPS 到站检测只标记到站，不会单独推进路线完成状态。
- playback 的 `complete` 和 `skip` 才会推动 stop progression。
- map payload 会暴露 current/next stop 以及 completed/editable marker 状态。

### 测试方法
- 验证远距离与近距离 GPS 上报的行为差异。
- 验证 arrival trigger 不会自动推进路线。
- 验证只有正确的 playback action 才会更新 `current_stop_index`。
- 验证 map payload 始终与 session state 保持一致。
- 相关测试：
  - `tests/test_map_gps.py`
  - `tests/test_guide_playback.py`
  - `tests/test_a_validation_suite.py`

### 测试分层
- 单元测试：arrival 语义与 playback 状态推进规则
- 集成测试：gps update / playback / map session API
- 链路测试：session -> gps -> playback -> current/map
- smoke / readiness：地图和运行时状态能正常联动
- degraded / fault-injection：当前主要看状态稳定，不以外部 provider 为核心

### 当前覆盖状态
- 自动化覆盖：较完整
- 真实环境验证：仍可做一轮联动 smoke
- 当前判断：**已覆盖**

### 本轮执行重点
- 重点确认 GPS 到站不自动推进
- 重点确认 playback 和 map/session 状态一致

---

## 6. Manual route edit

### 功能基本描述
这个功能是当前产品边界下唯一的 route-edit 路径。
它允许用户在行程中做受控的路线修改，同时保留已经完成的进度。

### 功能当前做法
- 主要接口：
  - `POST /api/v1/planning/itineraries/{itinerary_id}/edits`
- 当前支持的 operation 包括：
  - `replace_stop`
  - `remove_stop`
  - `reorder_stops`
  - `shorten_route`
  - `add_stop`
  - `optimize_route`（后端支持，但不是当前主要前端入口）
- 当前产品规则：
  - completed stops 冻结
  - current stop 可编辑
  - future stops 可编辑
- edit 走 version-based 模式，而不是原地修改。
- active session 下的 route edit 必须在 version switch 后保持与 session/map/QA 一致。

### 测试方法
- 验证每一种支持的 operation 在合法 editable suffix 上能正常工作。
- 验证 completed prefix 上的编辑请求会被拒绝。
- 验证 completed itinerary 不能再次被编辑。
- 验证 request validation 能拒绝混合 operation-specific payload。
- 验证 active session 下 edit 后的 version switch 一致性。
- 相关测试：
  - `tests/test_planner_edits.py`
  - `tests/test_a_validation_suite.py`
  - `tests/test_qa.py`

### 测试分层
- 单元测试：edit boundary、operation-specific request 校验
- 集成测试：planning edits API
- 链路测试：active session 下 edit -> version switch -> current/map/QA 一致性
- smoke / readiness：关键 edit 场景可成功或被正确拒绝
- degraded / fault-injection：当前不是主要依赖外部 provider 的区域

### 当前覆盖状态
- 自动化覆盖：较完整
- 高风险边界：已覆盖但仍值得在正式执行时优先复核
- 当前判断：**已覆盖**

### 本轮执行重点
- 重点确认 completed prefix 冻结规则
- 重点确认 version switch 后 session/map/QA 一致

---

## 7. Guide jobs、guide assets、cycle content 与 TTS

### 功能基本描述
这组功能负责生成 guide 内容、存储和返回当前 guide asset、支持站点内内容轮换，并在配置完整时返回真实 TTS 媒体输出。

### 功能当前做法
- 主要接口：
  - `POST /api/v1/guide/jobs`
  - `GET /api/v1/guide/jobs/{guide_generation_job_id}`
  - `GET /api/v1/guide/asset/{guide_session_id}`
  - `POST /api/v1/guide/content/{guide_session_id}`
- Guide generation 是 async 的，完整真实链路依赖 worker 进程。
- `guide/asset` 当前会区分 `pending / ready / failed / missing`，用于表达生成中、可用、失败和当前无资产四种状态。
- `guide/asset` 还会返回轻量 `job` 元信息，帮助前端和测试直接看出当前状态来自哪个 job、当前 job 状态是什么、是否带有失败原因。
- Guide 继续保持 SQL-first，同时具备 structured runtime generation 和 deterministic fallback。
- `cycle_content` 只切换 current stop 内容，不推进路线状态。
- TTS 在有配置时走真实 provider；缺配置时返回明确的 unavailable / degraded 语义。

### 测试方法
- 验证 guide job 的创建和查询语义。
- 验证最新稳定 ready asset 的选择规则。
- 验证 `cycle_content` 会轮换内容但不移动路线。
- 验证 asset 未 ready 时，content 会返回明确的未就绪语义，而不是把等待窗口误判成资源不存在。
- 验证 finished session 会拒绝内容生成，但在合适情况下仍可暴露已有 ready asset。
- 验证 TTS 在已配置时能返回真实音频，在未配置时能返回稳定的 degraded 语义。
- 相关测试：
  - `tests/test_guide_job_runtime.py`
  - `tests/test_guide_asset_latest.py`
  - `tests/test_guide_content_cycle.py`
  - `tests/test_guide_playback.py`
  - `tests/test_runtime_openrouter.py`

### 测试分层
- 单元测试：guide bundle 解析、asset 选择规则、fallback 语义
- 集成测试：guide jobs / guide asset / guide content / playback API
- 链路测试：planning -> guide job -> worker -> asset -> content
- smoke / readiness：worker 存在、guide asset 可读、content 可轮换
- degraded / fault-injection：TTS 缺 key、worker 未起、runtime 失败时的行为

### 当前覆盖状态
- 自动化覆盖：较强
- 真实环境验证：仍需继续加固
- 当前判断：**部分覆盖**

### 本轮执行重点
- 重点确认 worker 参与下的真实 guide 链路
- 重点确认 TTS 与 finished-session 边界

---

## 8. QA ask

### 功能基本描述
这个功能负责回答出行过程中的旅游相关问题，以及更广义的导览产品问答。

### 功能当前做法
- 主要接口：
  - `POST /api/v1/qa/ask`
  - `POST /api/v1/qa/preview`
  - `GET /api/v1/qa/playground`
- 当前 intent 空间包括：
  - `attraction_explain`
  - `trip_assistant`
  - `translation`
  - `live_info`
  - `weather_info`
  - `navigation_text`
  - `manual_route_edit_redirect`
  - `out_of_scope`
- 当前方向是：translator-first -> high-precision rules -> small-model fallback classifier -> downstream handlers。
- 当前实现已经暴露 routing metadata，并保持 route edit 为 redirect-only，而不是执行修改。
- QA 在有配置时走 SQL-first retrieval + RAG fallback。
- 导航当前已进一步收口为：规则优先提槽位（`next-stop` / `destination-only` / `explicit route`）-> fallback 结构化提取复杂/多地点导航 -> Amap 单段导航 -> multi-leg 聚合输出。

### 测试方法
- 验证每种支持 intent 的 routing 行为。
- 验证 out-of-scope 与 boundary handling 始终明确。
- 验证 session-aware QA 会正确读取当前运行时上下文。
- 验证 deep attraction 问题在 configured 和 degraded retrieval 模式下的行为。
- 验证 translation 和 provider-failure 路径不会把 malformed output 直接暴露给用户。
- 验证导航槽位提取链路：`下一站怎么去`、`去故宫怎么走`、`从天安门到故宫怎么走`、`从天安门到故宫再到景山怎么走`。
- 验证 route-edit / trip-assistant 不会被导航槽位规则误抓。
- 验证 QA playground 可手动覆盖 `session/profile/attraction/dialogue_history`，并通过 `preview` 看到实际 resolved query、hybrid context 和 prompt 预览。
- 验证 playground 默认请求是最小 payload：未显式填写 override 时，不应默认注入 `context.qa_playground`。
- 验证 `发送 QA 请求` 只调用一次真实 `/api/v1/qa/ask`，不会再额外串行触发 preview。
- 验证 ask 返回的 `metadata.latency_ms` 包含 `preprocess/routing/context_build/context_build_breakdown_ms/generation/postprocess/total`，且页面摘要区能直接展示链路与耗时信息。
- 验证 `context_build_breakdown_ms` 能拆出景点/profile 查询、weather target 解析、weather/navigation provider 调用、RAG 查询、prompt projection 等子步骤，便于直接判断慢点是否来自不必要的上下文加载。
- 验证天气链路遵守最新规则：只有规则已判 `weather_info` 且已抽到地点时才不走 fallback；否则必须进入 router fallback，并由同一次 fallback 同时给出 `intent + weather_location_name`。
- 验证 weather target 解析不再单独调用第二次 weather-slot fallback 模型；当 `context_build_breakdown_ms.weather_target_source = fallback` 时，`weather_target_fallback_ms` 应保持 `0`，因为地点已经在 routing 阶段得到。
- 相关测试：
  - `tests/test_qa.py`
  - `tests/test_qa_playground.py`
  - `tests/test_qa_routing_regressions.py`
  - `tests/test_routing_benchmark.py`
  - `tests/test_navigation_slot_extraction.py`
  - `tests/test_a_validation_suite.py`
  - `docs/e2e-qa-benchmark.md`
- 2026-05-08 补记：routing benchmark 已新增 zh-hard v1 基线，测试侧会优先围绕 `routing_benchmark_cases_zh_hard_v1.json` 验证 summary 字段、冲突切片与 boundary 回归。
- 2026-05-08 新增补记：规则层已开始切到 `jieba` 分词 + 共享规则资产，routing 回归应额外覆盖归一化表达、双语展示类 translation、中文强信号 direct-hit，以及公共交通导航、parking / air-quality 等 travel-adjacent boundary case。
- 2026-05-09 收口补记：follow-up 常见短句不再作为规则层信号；英文 query 的相关 QA 集成测试应通过 preprocess mock 先 pivot 成中文，再验证 trip-assistant / live-info 等路由行为，而不是继续假设中文规则层直接理解英文词表。
- 2026-05-09 同轮继续补记：`weather_info` 与 `navigation_text` 已正式接入 QA 主链路，`tests/test_qa.py` 现已补齐 supported/degraded 行为覆盖；同时新增 `tests/test_amap_weather_client.py` 与 `tests/test_amap_navigation_client.py`，把 Amap weather / text navigation 的 provider 成功与降级语义单独锁定。
- 2026-05-09 同日晚些时候继续补记：导航已进一步从 point-to-point 返回升级为“规则直提槽位 + fallback 结构化提取 + multi-leg 聚合”，并新增 `tests/test_navigation_slot_extraction.py` 锁定多地点拆段行为。
- 2026-05-13 补记：天气地点解析现已补上 `rule -> fallback -> default city` 三段式覆盖；`tests/test_qa.py` 新增/修正了“显式地点走 fallback 抽取”和“无显式地点时回退 itinerary `city_code`”两类回归，定向执行 `pytest tests/test_qa.py -k "weather" -v` 当前为 `3 passed`。
- 2026-05-13 同轮继续收紧了 weather fallback prompt：明确 `query/raw_query/pivot_query` 中的显式地点优先，`session_context` 仅作弱提示，不允许覆盖用户明说的地点；收紧后 weather 定向回归仍保持 `3 passed`。

### 测试分层
- 单元测试：routing 规则、structured output、fallback 语义、边界判断
- 集成测试：`/api/v1/qa/ask` 的主要 intent 与 metadata
- 链路测试：session-aware QA、SQL-first + RAG fallback、route-edit redirect
- smoke / readiness：真实 QA ask 能返回稳定结构
- degraded / fault-injection：provider 缺失、RAG disabled、translation/provider failure
- benchmark / E2E：routing benchmark 与真实 `/api/v1/qa/ask` E2E benchmark

### 当前覆盖状态
- 自动化覆盖：已有较完整基础
- 质量与边界稳定性：仍需继续优化
- 当前判断：**部分覆盖**

### 本轮执行重点
- 重点确认最弱 intent 与边界题
- 重点确认 translation、degraded、session-aware QA 的真实行为

---

## 9. RAG admin 与 retrieval

### 功能基本描述
这个功能负责 retrieval backend 的 readiness、rebuild 流程，以及 QA 侧可观测的 retrieval 状态。

### 功能当前做法
- 主要接口：
  - `GET /api/v1/rag/index-runs/latest`
  - `POST /api/v1/rag/index-runs/rebuild`
- 系统在配置完整时走 pgvector-backed 路径。
- rebuild 流程支持 selective 的 seed/mock-friendly 参数。
- QA metadata 会反映 retrieval 当前是 ready、skipped、unavailable 还是 active。

### 测试方法
- 验证 `latest` 在 rebuild 前后的行为。
- 验证 rebuild 在 configured 和 disabled 模式下的语义。
- 验证 query 行为和 retrieval metadata。
- 验证 degraded / misconfigured readiness 不会导致系统崩溃。
- 相关测试：
  - `tests/test_rag_admin.py`
  - `tests/test_rag_query.py`
  - `tests/test_rag_backend.py`
  - `tests/test_rag_indexing.py`

### 测试分层
- 单元测试：readiness 判断、metadata 映射、rebuild 状态语义
- 集成测试：rag latest / rebuild API
- 链路测试：rebuild -> latest -> QA deep ask retrieval metadata
- smoke / readiness：真实环境 latest / rebuild 可执行
- degraded / fault-injection：rag disabled、缺 DSN、缺 embedding key、backend 不可用

### 当前覆盖状态
- 自动化覆盖：已有基础
- 真实环境验证：仍需继续补强
- 当前判断：**部分覆盖**

### 本轮执行重点
- 重点确认 configured / disabled 两种真实语义
- 重点确认 retrieval metadata 与 QA 行为一致

---

## 10. Comments 与 share-card

### 功能基本描述
这两个功能负责提供轻量社交输入，以及一套 finished-trip 分享出口。

### 功能当前做法
- 主要接口：
  - `GET /api/v1/comments/stops/{stop_id}`
  - `POST /api/v1/comments/stops/{stop_id}`
  - `GET /api/v1/share-card/session/{guide_session_id}`
- comment 统计会流入 map 和 share-card payload。
- share-card 当前只面向 finished trip。

### 测试方法
- 验证 comment create/list 行为。
- 验证 comment summary 能正确传播到下游 read model。
- 验证 finished 与 unfinished share-card 的差异行为。
- 验证 trip 完成后的 share-card payload 一致性。
- 相关测试：
  - `tests/test_comments.py`
  - `tests/test_share_card.py`
  - `tests/test_map_gps.py`

### 测试分层
- 单元测试：share-card 聚合规则、comment summary 逻辑
- 集成测试：comments / share-card API
- 链路测试：trip finish -> comments summary -> share-card consistency
- smoke / readiness：share-card 在 finished trip 下可读
- degraded / fault-injection：当前不是首要重点

### 当前覆盖状态
- 自动化覆盖：较完整
- 当前判断：**已覆盖**

### 本轮执行重点
- 重点确认 finished trip 的 share-card 一致性

---

## 11. Degraded 与外部依赖行为

### 功能基本描述
这部分行为用于保证在外部 provider 或可选依赖不可用时，产品仍然可理解、可诊断、不会静默失败。

### 功能当前做法
- 主要外部依赖区域包括：
  - route engine
  - Amap weather / text navigation provider
  - runtime LLM
  - RAG backend
  - live info provider
  - TTS provider
  - guide worker availability
- 当前产品有意识地暴露 explicit 的 degraded / unavailable / skipped 状态，而不是静默失败。

### 测试方法
- 验证 missing key、disabled config 和 upstream error 的行为。
- 验证在需要时 API 与 worker 环境一致。
- 验证 degraded answer 仍然明确且可用。
- 真实环境与轮次级验证请配合：
  - `docs/test-readiness-checklist.md`
  - `docs/demo-test-plan.md`
  - `docs/test-rounds-log.md`
- 相关测试：
  - `tests/test_live_search.py`
  - `tests/test_runtime_openrouter.py`
  - `tests/test_rag_backend.py`
  - `tests/test_guide_job_runtime.py`
  - `tests/test_qa.py`
  - `tests/test_amap_weather_client.py`
  - `tests/test_amap_navigation_client.py`
  - `tests/test_amap_route_engine.py`

### 测试分层
- 单元测试：degraded / unavailable / skipped 状态语义
- 集成测试：缺配置时 API 返回结构与 metadata
- 链路测试：真实环境下 API / worker / provider 组合行为
- smoke / readiness：确认当前环境至少具备可演示能力
- degraded / fault-injection：本模块本身就是重点

### 当前覆盖状态
- 自动化覆盖：已有基础
- 真实环境与故障注入：仍需继续加固
- 当前判断：**部分覆盖**

### 本轮执行重点
- 重点确认 provider 缺失、环境不一致、上游失败三类情况

---

## 12. Benchmark 与 E2E QA validation

### 功能基本描述
这一层测试评估的不只是“系统能不能跑”，还包括 QA 栈在真实问题上的可接受程度。

### 功能当前做法
- 当前存在两层 benchmark：
  - model-only benchmark
  - 通过 `/api/v1/qa/ask` 执行的真实 E2E QA benchmark
- E2E benchmark 会把 routing、retrieval、provider 行为、session context 和 degraded logic 一起覆盖。

### 测试方法
- 使用 `docs/e2e-qa-benchmark.md` 查看数据集结构、执行顺序和判定规则。
- 使用 `docs/test-rounds-log.md` 查看历史结论和薄弱点。
- 使用 routing-focused tests 与 benchmark cases 衡量下一轮 QA 改进效果。
- 相关测试 / 文档：
  - `tests/test_routing_benchmark.py`
  - `tests/test_eval_scoring.py`
  - `tests/test_evals.py`
  - `docs/e2e-qa-benchmark.md`
  - `docs/test-rounds-log.md`

### 测试分层
- 单元测试：评分与 benchmark 汇总逻辑
- 集成测试：benchmark runner 与结果输出逻辑
- 链路测试：真实 `/api/v1/qa/ask` E2E 跑数
- benchmark / E2E：本模块本身就是重点

### 当前覆盖状态
- 基线：已建立
- 数据集与轮次深度：仍需继续扩充
- 当前判断：**部分覆盖**

### 本轮执行重点
- 本轮不作为第一批功能回归起点
- 作为 QA 质量验证和发布前补充验证使用

---

## 14. 本轮建议执行顺序
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
11. Benchmark 与 E2E QA validation（作为后置质量验证）

## 15. 建议阅读方式
- 当你想按功能理解“当前系统怎么测”时，读这份文档。
- 当你想先看整体覆盖状态和优先级时，先看上面的“测试矩阵总表”。
- 当你想直接开始这一轮功能测试时，按“本轮建议执行顺序”往下执行。
- 当你想看本轮测试范围和优先级时，读 `docs/demo-test-plan.md`。
- 当你想按顺序执行验证、检查环境和 smoke 时，读 `docs/test-readiness-checklist.md`。
- 当你想评估 QA 效果而不是一般功能正确性时，读 `docs/e2e-qa-benchmark.md`。
