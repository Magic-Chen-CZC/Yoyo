# Demo 产品测试方案

这份文档只负责测试范围、场景和优先级，不维护接口字段定义；接口字段与示例以 `docs/api-contracts-fullstack.md` 为准。
功能级测试总览请阅读 `docs/feature-test-guide.md`；执行顺序与 readiness 细节请阅读 `docs/test-readiness-checklist.md`。

## 1. 测试目标

本轮测试的目标不是覆盖未来所有产品演进，而是确认当前已锁定的 demo 主线已经稳定可测：

- Guest quick entry + questionnaire
- Planning / itinerary creation
- Session / GPS / cognitive map
- Guide SQL-first generation
- QA SQL-first + RAG fallback
- Manual route edit
- Comments / share-card
- Qwen TTS real generation
- pgvector-backed RAG rebuild/latest/query real validation

## 2. 测试范围

### P0：必须通过
- Guest quick entry
- Questionnaire
- Planning / itinerary creation
- Guide jobs create/get
- Session / GPS / cognitive map
- Guide asset / content generation + `cycle_content`
- Qwen TTS
- QA ask（含 out-of-scope）
- RAG rebuild/latest
- Manual route edit
- Share card / comments

### P1：建议覆盖
- 多入口建行程
- 版本切换后的 session/map 一致性
- Guide/QA 降级路径
- 无 key / provider 异常时的表现

### P2：本轮不作为阻塞
- benchmark 质量评测
- 多轮 QA 长记忆策略
- QA route-edit assistance 回归

## 3. 测试环境

### 3.1 必要环境变量
根目录 `.env` 至少确认：

```env
APP_ENV=local
DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/yoyo
REDIS_URL=redis://localhost:6379/0

LLM_PROVIDER=openrouter
LLM_MODEL=google/gemini-2.5-flash-lite
OPENROUTER_API_KEY=...
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

RAG_ENABLED=true
RAG_PGVECTOR_DSN=postgresql+psycopg2://postgres:postgres@127.0.0.1:5432/yoyo
RAG_EMBEDDING_PROVIDER=openrouter
RAG_EMBEDDING_BASE_URL=https://openrouter.ai/api/v1
RAG_EMBEDDING_MODEL=text-embedding-3-small
RAG_EMBEDDING_DIMENSION=1536
RAG_EMBEDDING_API_KEY=...

TTS_PROVIDER=dashscope
TTS_BASE_URL=https://dashscope.aliyuncs.com/api/v1
TTS_API_KEY=...
TTS_MODEL=qwen3-tts-flash
TTS_VOICE=Cherry
TTS_AUDIO_FORMAT=mp3
```

### 3.2 基础依赖
- Docker 已启动
- `docker-compose.yml` 使用：
  - `pgvector/pgvector:pg16`
  - `redis:7`

## 4. 启动步骤

```bash
docker compose up -d
.venv/bin/alembic upgrade heads
PYTHONPATH=src .venv/bin/python src/yoyo/scripts/seed_mock_knowledge.py
.venv/bin/uvicorn yoyo.app:app --host 127.0.0.1 --port 8000
```

## 5. 冒烟测试

### 5.1 健康检查
- `GET /api/v1/health`
- 预期：`code = 0`，`data.status = ok`

### 5.2 RAG readiness
- `GET /api/v1/rag/index-runs/latest`
- 预期：
  - 已 rebuild 时 `availability = ready`
  - 未 rebuild 时当前语义是 `404`，不是 500

### 5.3 Guide jobs readiness
- `POST /api/v1/guide/jobs`
- `GET /api/v1/guide/jobs/{guide_generation_job_id}`
- 预期：
  - create 成功
  - 初始 `status = queued`
  - 初始 `asset_status = pending`
  - 可按 id 查回

### 5.4 TTS 最小验证
- 先轮询 `GET /api/v1/guide/asset/{guide_session_id}`，直到 `asset_status = ready`
- 再调用一次 `POST /api/v1/guide/content/{guide_session_id}`
- 预期：
  - asset 未 ready 时，`guide/content` 当前语义应返回 `409 guide asset not ready`
  - asset ready 后，返回 `audio_segments`
  - 当前批次音频状态为 `ready` 或受控降级

## 6. 主流程测试

### 6.1 游客进入 + 问卷
步骤：
1. `POST /api/v1/guest/sessions`
2. `GET /api/v1/questionnaire/flows/current`
3. `POST /api/v1/questionnaire/submissions`

重点：
- guest session 创建成功
- 问卷固定 7 题
- `role_choice` 正常映射到 `guide_style_preference`

### 6.2 生成行程
覆盖三类入口：
- `template`
- `manual_poi`
- `ai_recommendation_selected`

重点：
- itinerary/version 创建成功
- stop 字段完整

### 6.3 guide session + 开始行程
步骤：
1. `POST /api/v1/session/guide`
2. `POST /api/v1/session/guide/{guide_session_id}/start`
3. `GET /api/v1/session/{guide_session_id}/current`
4. `GET /api/v1/map/session/{guide_session_id}`

重点：
- `pending -> active`
- `current_stop_index = 0`
- map/session 当前 stop 一致

### 6.4 session finish 与结束后 current 边界
优先级：P0
直白解释：结束行程后，状态必须收口干净；不能 finish 了但 current 接口返回一半旧状态、一半新状态。

步骤：
1. `POST /api/v1/session/guide/{guide_session_id}/finish`
2. `GET /api/v1/session/guide/{guide_session_id}`
3. `GET /api/v1/session/{guide_session_id}/current`

重点：
- `status = finished`
- context 里有 `trip_finished_at`
- `current` 返回结构稳定
- finished 后 itinerary 应进入 completed 语义

## 7. Guide 测试

### 7.1 Guide 任务创建与查询
优先级：P0
直白解释：先确认导览生成任务本身能创建、能查回，不然后面的 asset/content 都没有基础。

- `POST /api/v1/guide/jobs`
- `GET /api/v1/guide/jobs/{guide_generation_job_id}`
- 重点：
  - create 成功
  - 初始 `status = queued`
  - 初始 `asset_status = pending`
  - get 可按 id 查回
  - 真实环境里如果没有启动 worker，job 会持续停在 `queued`
  - 要验证真实 asset/content，需额外启动：`.venv/bin/arq yoyo.jobs.worker.WorkerSettings`

### 7.2 Guide 资产生成
优先级：P0
直白解释：确认系统拿到的是“当前真正应该给用户看的那份导览资产”，而不是旧的、失败的、或者还没完成的结果。

- `GET /api/v1/guide/asset/{guide_session_id}`
- 重点：
  - `asset_status = ready`
  - `guide_script` / `card` / `audio` 元数据存在
  - 返回轻量 `job` 元信息，便于判断当前 asset 状态来源
  - 取最新 `ready + succeeded` 的 job
  - 更新但仍 `pending` 的 job 不应覆盖已有稳定资产
  - 没有 ready success 时：
    - 生成中 -> `asset_status = pending`
    - 最新 job 失败 -> `asset_status = failed`
    - 当前 version 下没有 job -> `asset_status = missing`

### 7.3 `cycle_content`
优先级：P0
直白解释：点“再来一段讲解”时，只应该换内容，不应该偷偷把路线往前推进。

- 先确认 `GET /api/v1/guide/asset/{guide_session_id}` 已返回 `asset_status = ready`
- 再连续调用 `POST /api/v1/guide/content/{guide_session_id}` 2~3 次
- 重点：
  - 不推进 route state
  - 内容会轮换
  - `more_content_available` 合理
  - `audio_segments` 跟当前批次联动
  - 如果 asset 尚未 ready，当前应返回 `409 guide asset not ready`

### 7.4 finished session 下 Guide content / asset 边界
优先级：P0
直白解释：行程结束后，系统不该继续生成新的讲解内容；但如果之前已有可分享的导览资产，资产读取仍可能是允许的。

- 先 finish session
- 再调用：
  - `POST /api/v1/guide/content/{guide_session_id}`
  - `GET /api/v1/guide/asset/{guide_session_id}`
- 重点：
  - finished 后 content 不可用
  - 若已有 ready asset，asset 仍可能可读

### 7.5 Qwen TTS 真生成
优先级：P0
直白解释：确认不是占位音频，而是真的能生成给 demo 用的音频。

- 重点：
  - 生成真实音频文件
  - `status = ready`
  - 不阻塞主流程

## 8. GPS / Playback / Map 测试

### 8.1 GPS 到站
- `POST /api/v1/gps/update/{guide_session_id}`
- 重点：
  - `arrived = true`
  - 不自动推进 stop

### 8.2 Playback 状态流转
- `trigger`
- `play`
- `complete`
- `skip`

重点：
- 只有 `complete/skip` 推动 `current_stop_index`

### 8.3 Map 同步
检查：
- `markers`
- `navigation_summary`
- `current_stop`
- `next_stop`
- `completed/editable` 边界

## 9. QA 测试

### 9.1 Trip assistant
优先级：P0
直白解释：问“下一站去哪”“接下来做什么”时，要能根据真实 session 状态回答，而不是胡乱说。

示例：
- `What is my next stop?`
- `What should I do after Tiananmen Square?`

### 9.2 Attraction explain
优先级：P0
直白解释：深问景点时，要能走 SQL-first + RAG fallback，而不是只给一段很浅的介绍。

示例：
- `Please give me the deeper history and background of the Forbidden City, not just a short intro.`

预期：
- `intent = attraction_explain`
- `retrieval_strategy = sql_then_rag`
- `rag_backend_ready = true`
- `rag_query_status = ok`

### 9.3 Translation
优先级：P1
直白解释：翻译类问题要么给出清晰结果，要么明确告诉用户当前不能确认，不要吐脏格式。

示例：
- `Translate this into polite English: 这个景点几点关门`

### 9.4 Live info
优先级：P1
直白解释：实时信息类问题如果外部信息拿不到，也要优雅降级，不能把整个 QA 打崩。

示例：
- `What should I check before visiting the Forbidden City today?`

### 9.5 Out-of-scope 与 route-edit 边界
优先级：P0
直白解释：QA 只能回答导览相关问题，不能越界回答无关需求，也不能偷偷替用户改路线。

示例：
- `Write me a sorting algorithm`

预期：
- out-of-scope 时 `supported = false`
- `intent = out_of_scope`
- QA 不应直接改路线
- QA 不应返回 route-edit action

## 10. RAG 后台测试

### 10.1 rebuild
优先级：P0
直白解释：管理员点 rebuild 后，要能知道这次索引到底是成功、跳过还是出错，而不是只知道“调过接口了”。

- `POST /api/v1/rag/index-runs/rebuild`
- 预期：状态语义清晰，可区分 `skipped` / `succeeded` / `error`

### 10.2 latest
优先级：P0
直白解释：latest 要么返回最近一次记录，要么在还没建索引时明确告诉我们“现在没有记录”。

- `GET /api/v1/rag/index-runs/latest`
- 预期：
  - 未初始化时返回 `404`
  - 有记录后返回最近一次记录

### 10.3 QA 联动
优先级：P0
直白解释：RAG 后台状态不能只停留在 admin 接口，要确认 QA 真能用上。

- 必须使用真实 `guide_session_id`
- 深问后检查：
  - `retrieval_strategy = sql_then_rag`
  - `rag_backend_ready = true`
  - `rag_query_status = ok`

## 11. 手动改路线测试

### 11.1 当前 stop 可编辑
优先级：P0
直白解释：当前站和后续站还能改，但已经走完的那一段不能动。

- replace / remove / reorder / shorten / add_stop

### 11.2 已完成 stop 不可编辑
优先级：P0
直白解释：已经完成的路线前缀必须冻结，不能因为编辑把已完成路径重写掉。

- 修改 completed prefix 应返回受控错误

### 11.3 operation-specific schema 校验
优先级：P0
直白解释：不同 edit operation 只能带自己该带的字段，传错字段应该直接 422，而不是吞掉继续执行。

- 示例：`operation = optimize_route` 时传 `add_stop_name`
- 预期：返回 `422`

### 11.4 版本切换一致性
优先级：P1
直白解释：改路线会切新版本，但 session/map/QA 看到的当前路线必须还是同一套。

- itinerary_version 切换后 session/map/QA 要一致

### 11.5 最后一站完成后不可再编辑
优先级：P0
直白解释：整趟行程已经结束时，任何后续改路线都应该被拒绝。

- 这是关键回归点

## 12. 评论 / 分享测试

### 12.1 Stop comments
优先级：P1
直白解释：评论要能正常写入和读取，后续分享卡片也会依赖这些聚合信息。

- `GET / POST /api/v1/comments/stops/{stop_id}`

### 12.2 Share card
优先级：P0
直白解释：分享卡片不能只看一个布尔值，要确认“确实已经结束，并且分享文案完整”。

- 只有 finished session 才应 `is_shareable = true`
- finished 时还应检查：
  - `status = finished`
  - `trip_summary.completed_at` 有值
  - `subheadline = Trip complete — ready to share`

## 13. 异常与降级测试

### 13.1 缺 TTS key
优先级：P1
直白解释：没有 TTS key 时，主流程仍要能继续，不能因为音频不可用把 guide 内容整体打挂。

- Guide content 仍应返回文本
- `cycle_content` 返回的 `audio_segments[*].status = unavailable`
- 如果要看 guide job / asset 的总音频状态，API 和 worker 必须使用同一套降级环境；否则 asset 可能反映的是 worker 那边的配置

### 13.2 RAG disabled / 缺 key / DSN
优先级：P1
直白解释：RAG 不可用时，后台接口要明确给出状态，QA 也不能整体崩溃。

- rebuild 应明确失败或 skipped
- 当 `RAG_ENABLED=false` 时，rebuild 应返回 `status = skipped`、`reason = rag_disabled`
- QA 仍可能给出正常 SQL-grounded 回答；此时重点看元数据：`rag_backend_ready = false`、`rag_query_status = skipped`

### 13.3 LLM provider 错误
- 不应返回脏 JSON
- 用户应看到明确降级文案

### 13.4 外部 provider 异常
优先级：P1
直白解释：live search / tts / embedding provider 报错时，接口要明确告诉用户现在拿不到景点官网/官方通知类信息，但不能把主流程整体打崩。

- live search / tts / embedding provider 报错时不能让主流程整体 500
- 当前 `live_info` 不用于天气、交通、拥挤度，这些后续应接专门 API
- 真实验证已确认：当 Tavily key 缺失时，`live_info` 会返回：
  - `status = unavailable`
  - `reason = missing_provider_config`
  - `degraded = true`
  - `degraded_reason = missing_provider_config`
  - `confidence = low`
  - `sources[0].name = tavily_missing_key`
  - answer 会明确引导用户去官网或可靠渠道确认当日信息

## 14. 下一轮测试建议（发布前风险轮）

下一轮不要再把重点放在“主流程是否能跑通”，而是转成“上线或提测前最容易翻车的风险点”验证。

### 14.1 部署一致性测试（P0）
直白解释：确认 API、worker、`.env` 必须成套启动；不能 API 是一套配置、worker 是另一套配置。

重点：
- API 与 worker 同时正常启动
- API 缺 key / worker 正常
- API 正常 / worker 缺 key
- API 与 worker 使用不同 `.env` 时的表现

目标：
- 明确哪些状态由 API 决定，哪些状态由 worker 决定
- 避免把环境不一致误判成业务 bug

### 14.2 外部依赖故障注入（P0）
直白解释：把外部服务一个个打断，看系统是优雅降级还是直接炸掉。

重点：
- OpenRouter 不可用
- Tavily 不可用
- DashScope 不可用
- pgvector query / embedding provider 异常

目标：
- 不返回 500
- 有明确降级文案
- metadata 可诊断

### 14.3 状态切换回归（P0）
直白解释：真实 demo 最容易出错的不是单个接口，而是 start / GPS / playback / finish / version switch 混在一起时状态会不会乱。

重点：
- start -> GPS arrival -> playback complete -> next stop
- active -> route edit -> version switch -> QA/map 同步
- active -> finish -> share-card / guide content 边界
- 已 finish 后再触发 GPS / playback / content 的表现

目标：
- session / map / QA / share-card 始终看同一套状态

### 14.4 性能与时延测试（P1）
直白解释：不是做极限压测，而是确认 demo 体感不卡。

重点：
- guide job 首次成功耗时
- `cycle_content` 首包时延
- QA 深问时延
- RAG rebuild 耗时

目标：
- 找出 demo 演示时最容易卡住的步骤
- 给出演示前的超时预期和操作建议

## 15. 建议执行顺序

### 第一轮：演示前冒烟
1. health
2. rebuild/latest
3. guest -> questionnaire -> itinerary -> session
4. map/current
5. guide content + tts
6. qa ask

### 第二轮：主流程回归
1. template 入口
2. manual_poi 入口
3. ai_recommendation 入口
4. gps/playback/map
5. route edit
6. share/comments

### 第三轮：异常/降级
1. 去掉部分 key
2. provider 模拟失败
3. 看是否受控降级

### 第四轮：发布前风险轮
1. 部署一致性测试
2. 外部依赖故障注入
3. 状态切换回归
4. 性能与时延测试

## 16. 通过标准

### 必须满足
- 主流程闭环全通
- Qwen TTS 真生成成功
- RAG rebuild/latest 成功
- 深问 QA 元数据满足：
  - `retrieval_strategy = sql_then_rag`
  - `rag_backend_ready = true`
  - `rag_query_status = ok`
- route edit 边界符合产品约束
- 无明显 500

### 可暂不阻塞
- benchmark 全面质量评测
- 多轮 QA 长记忆策略
- 后续 planner realism 提升

## 17. 建议产出物

测试时建议沉淀：
1. 冒烟记录
2. 异常记录
3. 最终提测结论
4. 发布前风险轮记录（环境一致性 / 外部依赖 / 状态切换 / 时延）
5. QA benchmark 结果（区分 model-only 与 E2E 两套）

## 18. 下次 AI 接手建议顺序

1. `CLAUDE.md`
2. `README.md`
3. `docs/todo-phase-2.md`
4. `docs/phase-2-summary.md`
5. `docs/feature-test-guide.md`
6. `docs/architecture.md`
7. `docs/contracts.md`
8. `docs/test-readiness-checklist.md`
9. `docs/demo-test-plan.md`
