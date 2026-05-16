# Demo 测试清单

这份清单用于下次由 AI 或开发者快速接手，判断当前 demo 是否处于可测试状态，并按固定顺序执行关键验证。
功能级测试总览请阅读 `docs/feature-test-guide.md`；测试范围与优先级请阅读 `docs/demo-test-plan.md`。

如果你是前端同学，建议先看 `docs/frontend/README.md`，再结合 `docs/api-contracts-fullstack.md` 使用这份清单做联调验证。

## 1. 目标

当前 demo 的目标不是“所有后续产品演进都完成”，而是确认以下主线已经稳定可测：

- Guest quick entry + questionnaire
- Planning / itinerary creation
- Session / GPS / cognitive map
- Guide SQL-first generation
- QA SQL-first + RAG fallback
- Manual route edit
- Comments / share-card
- Qwen TTS real generation
- pgvector-backed RAG rebuild/latest/query real validation

## 2. 环境准备

### 2.1 必要环境变量
项目使用根目录 `.env`。

至少确认以下变量存在且正确：

```env
APP_ENV=local
DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/yoyo
REDIS_URL=redis://localhost:6379/0

LLM_PROVIDER=volcengine
LLM_MODEL=doubao-seed-2-0-mini-260428
VOLCENGINE_API_KEY=...
VOLCENGINE_BASE_URL=https://ark.cn-beijing.volces.com/api/v3

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

### 2.2 本地依赖
当前 `docker-compose.yml` 使用：
- `pgvector/pgvector:pg16`
- `redis:7`

启动前确认 Docker 已运行。

## 3. 启动步骤

在仓库根目录执行：

```bash
docker compose up -d
.venv/bin/alembic upgrade heads
PYTHONPATH=src .venv/bin/python src/yoyo/scripts/seed_mock_knowledge.py
.venv/bin/uvicorn yoyo.app:app --host 127.0.0.1 --port 8000
.venv/bin/arq yoyo.jobs.worker.WorkerSettings
```

## 4. 核心验证顺序

### 4.1 TTS 真实验证
可以直接通过项目内实现验证：
- 文件：`src/yoyo/modules/guide/tts.py`
- 预期：返回 `status = ready`，并在 `.generated_tts/` 写出音频文件

### 4.2 RAG admin 验证
按固定顺序调用：

1. `GET /api/v1/rag/index-runs/latest`
2. `POST /api/v1/rag/index-runs/rebuild`
3. 再次 `GET /api/v1/rag/index-runs/latest`

预期关键字段：
- 首次 `latest` 在未初始化时返回 `404`，这是当前预期语义
- rebuild 后 `latest` 可读
- 返回体包含 `backend = llamaindex_pgvector`
- 状态要能区分 `skipped` / `succeeded` / `error`

### 4.3 Guide job 验证
按固定顺序调用：
1. `POST /api/v1/guide/jobs`
2. `GET /api/v1/guide/jobs/{guide_generation_job_id}`

预期关键字段：
- create 成功
- 初始 `status = queued`
- 初始 `asset_status = pending`
- get 可按 id 查回

注意：
- 只启动 API 服务不够，guide job 会停在 `queued`
- 要验证 guide asset / content 的真实链路，必须同时启动 worker：`.venv/bin/arq yoyo.jobs.worker.WorkerSettings`

### 4.4 Session finish 边界验证
推荐顺序：
1. `POST /api/v1/session/guide`
2. `POST /api/v1/session/guide/{guide_session_id}/start`
3. `POST /api/v1/session/guide/{guide_session_id}/finish`
4. `GET /api/v1/session/{guide_session_id}/current`

预期关键字段：
- session 能正确流转到 `finished`
- context 中有 `trip_finished_at`
- finished 后 `current` 仍返回稳定结构，不应脏掉

### 4.5 QA 深问与边界验证
不要用伪造的 `guide_session_id`，必须先创建真实 itinerary + guide session。

推荐顺序：
1. `POST /api/v1/planning/itineraries`
2. `POST /api/v1/session/guide`
3. `POST /api/v1/qa/ask`

推荐问题：
- 深问：`Please give me the deeper history and background of the Forbidden City, not just a short intro.`
- 越界：`Write me a sorting algorithm`

预期关键字段：
- 深问路径：`retrieval_strategy = sql_then_rag`
- `rag_backend_ready = true`
- `rag_query_status = ok`
- `intent = attraction_explain`
- 越界问题：`supported = false`，`intent = out_of_scope`

### 4.6 Route edit schema 边界验证
重点验证：
- completed itinerary 不可再编辑
- operation-specific 非法字段应直接 `422`

示例：
- `operation = optimize_route` 时不应接受 `add_stop_name`

## 5. 关键测试建议

### 5.1 最小必跑套件
```bash
.venv/bin/pytest tests/test_guide_job_runtime.py tests/test_rag_admin.py tests/test_session_lifecycle.py tests/test_qa.py tests/test_planner_edits.py
```

这组优先覆盖：
- guide job runtime
- rag admin 核心语义
- session start/finish
- QA out-of-scope
- route edit 参数与完成态边界

### 5.2 建议补跑的边界套件
```bash
.venv/bin/pytest tests/test_guide_asset_latest.py tests/test_guide_content_cycle.py tests/test_share_card.py
```

这组优先覆盖：
- guide asset 选择语义
- finished session 下 guide content / asset 边界
- share-card finished 一致性

### 5.3 若需要更高把握
再跑：
```bash
.venv/bin/pytest tests/test_runtime_openrouter.py tests/test_guide_content_cycle.py tests/test_guide_playback.py tests/test_rag_backend.py tests/test_rag_query.py
```

## 6. 已知注意事项

### 6.1 不要再把 benchmark 作为当前 demo 完整性的阻塞项
`eval/benchmark` 路径已经修到：
- 缺少 provider API key 时会 fail fast 或记成 invalid

但更完整的 benchmark 测试方案需要后续单独设计，不应阻塞当前 demo 提测。

### 6.2 Fresh migration 的历史问题
如果本地是从老容器/老数据库状态延续而来，遇到迁移问题时优先检查：
- `0005_add_pending_guide_sessions.py`
- `0007_enable_pgvector_extension.py`
- `alembic_version` 表字段长度是否足够容纳长 revision id

### 6.3 QA 验证必须使用真实 guide session
否则 `qa_messages.guide_session_id` 外键会失败。

### 6.4 finished session 下 content / asset 的分叉是预期语义
当前实现里：
- finished 后 `POST /api/v1/guide/content/{guide_session_id}` 当前应返回 `409 guide session finished`
- 但如果之前已有 ready guide asset，`GET /api/v1/guide/asset/{guide_session_id}` 仍可能可读

不要把这两者表现不同误判成 bug。

### 6.4.1 guide asset 未 ready 时的当前语义
当前实现里：
- worker 仍在生成 guide job 时，`GET /api/v1/guide/asset/{guide_session_id}` 应返回 `200` 且 `asset_status = pending`
- 如果最新 job 已失败且当前没有 stable ready asset，`guide/asset` 应返回 `asset_status = failed`
- 如果当前 version 下还没有任何 job，`guide/asset` 应返回 `asset_status = missing`
- 这时如果立刻调用 `POST /api/v1/guide/content/{guide_session_id}`，当前应返回 `409 guide asset not ready`
- 真实链路测试时，应先轮询 asset 到 `ready`，再验证 content

### 6.5 share-card 的 finished 要看完整一致性
不要只看 `is_shareable = true`。
还要一起确认：
- `status = finished`
- `trip_summary.completed_at` 有值
- `subheadline = Trip complete — ready to share`

### 6.6 做异常/降级真实验证时，API 和 worker 要共用同一套环境
尤其是：
- TTS 缺 key
- RAG disabled / 缺 DSN / 缺 embedding key

如果只把 API 服务切到降级环境，但 worker 仍跑在正常环境，guide job / asset 看到的总状态可能会混入 worker 配置，不适合拿来做最终降级结论。

### 6.7 RAG disabled 的真实语义
本地真实验证已确认：
- `POST /api/v1/rag/index-runs/rebuild` 会返回 `status = skipped`、`reason = rag_disabled`
- QA 仍可能给出正常 SQL-grounded 回答
- 此时应重点检查元数据：`rag_backend_ready = false`、`rag_query_status = skipped`

### 6.8 live_info provider 缺失时的真实语义
本地真实验证已确认：
- 当 Tavily key 缺失时，`live_info` 会返回 `status = unavailable`
- `reason = missing_provider_config`
- `degraded = true`
- `confidence = low`
- `sources` 中会出现 `tavily_missing_key`
- answer 会明确引导用户去官网或可靠渠道确认当日信息

### 6.9 live_info 的当前定义域
当前 `live_info` 只面向：
- 景点官方网站信息
- 官方公告/通知
- 官方开放 / 预约 / 临时闭馆信息

当前**不**通过联网搜索处理：
- 天气
- 交通
- 拥挤情况 / 人流情况

这些内容后续应接专门 API，而不是继续扩到普通联网搜索。

### 6.9 当前存在两套 QA benchmark
- `evals/run_eval.py` 那套是 model-only benchmark，只测模型裸答能力
- 新增的 E2E QA benchmark 是直接打 `/api/v1/qa/ask`，会经过真实 API、session context、SQL/RAG/live_info provider 等系统链路

不要把这两套结果混在一起解读。

## 7. 当前可视为已完成的 demo 主线

以下内容已经被真实环境或定向测试验证过，可作为当前 demo 的完成边界：

- Qwen TTS 可真实生成
- pgvector 扩展可用
- RAG rebuild/latest 可成功执行
- 深问 QA 可走 `sql_then_rag`
- todo 主线项已经基本收口，仅剩后续产品演进项

## 8. 下一轮测试建议（发布前风险轮）

如果当前 demo 已可提测，下一轮建议改做“发布前风险轮”，优先级如下：

1. 部署一致性测试
   - API / worker / `.env` 必须成套验证
2. 外部依赖故障注入
   - OpenRouter / Tavily / DashScope / pgvector 分开打断
3. 状态切换回归
   - start / GPS / playback / finish / version switch 穿插验证
4. 性能与时延测试
   - guide job / `cycle_content` / QA 深问 / rebuild 的体感时延

## 9. 下次 AI 接手建议顺序

1. 读：`CLAUDE.md`
2. 读：`README.md`
3. 读：`docs/todo-phase-2.md`
4. 读：`docs/phase-2-summary.md`
5. 读：`docs/feature-test-guide.md`
6. 读：`docs/architecture.md`
7. 读：`docs/contracts.md`
8. 读：本文件 `docs/test-readiness-checklist.md`
9. 再决定是：
   - 做 demo 提测
   - 做发布前风险轮
   - 做剩余产品演进
   - 还是单独重构 eval/benchmark 测试方案
