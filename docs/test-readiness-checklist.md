# Demo 测试清单

这份清单用于下次由 AI 或开发者快速接手，判断当前 demo 是否处于可测试状态，并按固定顺序执行关键验证。

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
```

## 4. 核心验证顺序

### 4.1 TTS 真实验证
可以直接通过项目内实现验证：
- 文件：`src/yoyo/modules/guide/tts.py`
- 预期：返回 `status = ready`，并在 `.generated_tts/` 写出音频文件

### 4.2 RAG admin 验证
按固定顺序调用：

1. `POST /api/v1/rag/index-runs/rebuild`
2. `GET /api/v1/rag/index-runs/latest`

预期关键字段：
- `status = succeeded`
- `availability = ready`
- `collection_name = yoyo_attraction_knowledge`

### 4.3 QA 深问验证
不要用伪造的 `guide_session_id`，必须先创建真实 itinerary + guide session。

推荐顺序：
1. `POST /api/v1/planning/itineraries`
2. `POST /api/v1/session/guide`
3. `POST /api/v1/qa/ask`

推荐问题：
- `Please give me the deeper history and background of the Forbidden City, not just a short intro.`

预期关键字段：
- `retrieval_strategy = sql_then_rag`
- `rag_backend_ready = true`
- `rag_query_status = ok`
- `intent = attraction_explain`

## 5. 关键测试建议

### 5.1 先跑的定向测试
```bash
.venv/bin/pytest tests/test_guide_content_cycle.py tests/test_guide_playback.py
.venv/bin/pytest tests/test_rag_backend.py tests/test_rag_query.py
```

### 5.2 若需要更高把握
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

## 7. 当前可视为已完成的 demo 主线

以下内容已经被真实环境或定向测试验证过，可作为当前 demo 的完成边界：

- Qwen TTS 可真实生成
- pgvector 扩展可用
- RAG rebuild/latest 可成功执行
- 深问 QA 可走 `sql_then_rag`
- todo 主线项已经基本收口，仅剩后续产品演进项

## 8. 下次 AI 接手建议顺序

1. 读：`CLAUDE.md`
2. 读：`README.md`
3. 读：`docs/architecture.md`
4. 读：`docs/contracts.md`
5. 读：`docs/todo.md`
6. 读：本文件 `docs/test-readiness-checklist.md`
7. 再决定是：
   - 做 demo 提测
   - 做剩余产品演进
   - 还是单独重构 eval/benchmark 测试方案
