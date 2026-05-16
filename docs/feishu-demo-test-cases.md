# Yoyo Demo 测试说明（飞书版）

这份文档给产品、测试、演示同学直接使用。
目标不是研究代码，而是快速知道：**这次 demo 要测什么、为什么测、优先级是什么、看到什么结果才算通过。**

## 1. 使用说明

- **P0**：必须通过。这里挂了，demo 不建议继续。
- **P1**：建议覆盖。P0 都过了再补这些。
- **P2**：本轮不阻塞，只做记录。

---

## 2. 基础可用性

### 2.1 健康检查
- 优先级：**P0**
- 在测什么：服务是不是活着，基本接口能不能通。
- 怎么测：`GET /api/v1/health`
- 通过标准：返回 `code = 0`，`data.status = ok`

### 2.2 Guest quick entry
- 优先级：**P0**
- 在测什么：游客能不能直接进入系统，不需要先注册登录。
- 怎么测：`POST /api/v1/guest/sessions`
- 通过标准：创建成功，返回 guest session 信息。

### 2.3 Questionnaire
- 优先级：**P0**
- 在测什么：问卷能不能正常拿到、正常提交，用户偏好能不能存下来。
- 怎么测：
  - `GET /api/v1/questionnaire/flows/current`
  - `POST /api/v1/questionnaire/submissions`
- 通过标准：
  - 当前问卷是固定 7 题
  - `role_choice` 正常映射到 `guide_style_preference`

---

## 3. 行程与 Session 生命周期

### 3.1 创建 itinerary
- 优先级：**P0**
- 在测什么：能不能把用户选择变成一条真正的行程。
- 怎么测：`POST /api/v1/planning/itineraries`
- 通过标准：
  - itinerary 创建成功
  - version 创建成功
  - stops 信息完整

### 3.2 多入口建行程
- 优先级：**P1**
- 在测什么：三种入口都能正常产出行程，不是只支持一种。
- 覆盖入口：
  - `template`
  - `manual_poi`
  - `ai_recommendation_selected`
- 通过标准：三类入口都能创建有效 itinerary。

### 3.3 创建 guide session
- 优先级：**P0**
- 在测什么：行程创建后，能不能进入导览 session。
- 怎么测：`POST /api/v1/session/guide`
- 通过标准：
  - session 创建成功
  - 初始状态为 `pending`

### 3.4 启动行程
- 优先级：**P0**
- 在测什么：用户开始行程后，系统状态会不会正确切到 active。
- 怎么测：`POST /api/v1/session/guide/{guide_session_id}/start`
- 通过标准：
  - `pending -> active`
  - `current_stop_index = 0`

### 3.5 结束行程
- 优先级：**P0**
- 在测什么：行程结束后，系统能不能干净收口。
- 怎么测：
  - `POST /api/v1/session/guide/{guide_session_id}/finish`
  - `GET /api/v1/session/{guide_session_id}/current`
- 通过标准：
  - `status = finished`
  - context 中有 `trip_finished_at`
  - current 接口返回结构稳定

---

## 4. Guide 任务、资产与内容

### 4.1 创建 guide job
- 优先级：**P0**
- 在测什么：导览生成任务能不能被正常创建。
- 怎么测：`POST /api/v1/guide/jobs`
- 通过标准：
  - 创建成功
  - 初始 `status = queued`
  - 初始 `asset_status = pending`
- 真实验证补充：如果只启动 API、不启动 worker，job 会一直停在 `queued`。

### 4.2 查询 guide job
- 优先级：**P0**
- 在测什么：创建后的任务能不能按 id 查回。
- 怎么测：`GET /api/v1/guide/jobs/{guide_generation_job_id}`
- 通过标准：能查到对应 job。

### 4.3 读取 guide asset
- 优先级：**P0**
- 在测什么：系统拿给用户看的导览资产，是不是当前真正该展示的那一份。
- 怎么测：`GET /api/v1/guide/asset/{guide_session_id}`
- 通过标准：
  - `asset_status = ready`
  - 有 `guide_script` / `card` / `audio` 元数据
  - 取最新 `ready + succeeded` 结果

### 4.4 忽略未完成的新 job
- 优先级：**P0**
- 在测什么：如果新 job 还在 pending，系统不能把旧的稳定资产挤掉。
- 怎么测：构造“旧 ready + 新 pending”的场景后读 asset。
- 通过标准：仍返回旧的稳定 asset。

### 4.5 没有 ready asset 时的表现
- 优先级：**P0**
- 在测什么：没有成功资产时，系统要明确告诉我们“现在没有”，不能乱返回旧数据。
- 怎么测：构造 failed / pending 但无 ready 的场景后读 asset。
- 通过标准：返回 `asset_status = missing`。

### 4.6 cycle_content
- 优先级：**P0**
- 在测什么：点击“再来一段讲解”时，只换内容，不推进路线。
- 怎么测：连续调用 `POST /api/v1/guide/content/{guide_session_id}` 2~3 次
- 通过标准：
  - 内容会轮换
  - `current_stop_index` 不推进
  - `more_content_available` 合理

### 4.7 finished 后 content / asset 边界
- 优先级：**P0**
- 在测什么：行程结束后，不该继续生成新讲解；但如果之前已经有 ready 资产，资产读取仍可能允许。
- 怎么测：
  - finish session
  - 再调 content 和 asset
- 通过标准：
  - content 不可用
  - ready asset 仍可能可读

### 4.8 Qwen TTS 真生成
- 优先级：**P0**
- 在测什么：音频是不是“真生成”，不是占位结果。
- 怎么测：调用 `POST /api/v1/guide/content/{guide_session_id}`
- 通过标准：
  - 返回 `audio_segments`
  - 音频状态为 `ready` 或受控降级
  - 真配置下可落真实音频文件
- 真实验证补充：正常环境下，guide asset 的总音频状态目前会先显示 `pending`，但 `cycle_content` 已经能返回当前批次 `audio_segments = ready`。

---

## 5. GPS / Playback / Map

### 5.1 GPS 到站
- 优先级：**P0**
- 在测什么：定位到站时，系统能不能正确识别“已经到了”。
- 怎么测：`POST /api/v1/gps/update/{guide_session_id}`
- 通过标准：
  - `arrived = true`
  - 不自动推进 stop

### 5.2 Playback 状态流转
- 优先级：**P0**
- 在测什么：播放相关动作会不会把路线推进逻辑搞乱。
- 覆盖动作：
  - `trigger`
  - `play`
  - `complete`
  - `skip`
- 通过标准：只有 `complete / skip` 推进 `current_stop_index`

### 5.3 Map 同步
- 优先级：**P0**
- 在测什么：地图、session、导航摘要看到的是不是同一条路线状态。
- 怎么测：`GET /api/v1/map/session/{guide_session_id}`
- 通过标准：
  - `markers`
  - `navigation_summary`
  - `current_stop`
  - `next_stop`
  - completed/editable 边界一致

---

## 6. QA 问答

### 6.1 Trip assistant
- 优先级：**P0**
- 在测什么：问“下一站去哪”“接下来做什么”时，能不能根据真实 session 回答。
- 示例：
  - `What is my next stop?`
  - `What should I do after Tiananmen Square?`
- 通过标准：回答与当前路线状态一致。

### 6.2 Attraction explain
- 优先级：**P0**
- 在测什么：深问景点时，能不能走 SQL-first + RAG fallback，而不是只给浅层介绍。
- 示例：`Please give me the deeper history and background of the Forbidden City, not just a short intro.`
- 通过标准：
  - `intent = attraction_explain`
  - `retrieval_strategy = sql_then_rag`
  - `rag_backend_ready = true`
  - `rag_query_status = ok`

### 6.3 Translation
- 优先级：**P1**
- 在测什么：翻译问题要么给清楚答案，要么明确说现在不能确认。
- 示例：`Translate this into polite English: 这个景点几点关门`
- 通过标准：
  - 无脏 JSON
  - 无奇怪模板残留
  - 降级时文案明确

### 6.4 Live info
- 优先级：**P1**
- 在测什么：实时信息失败时也不能把整个 QA 打崩。
- 示例：`What should I check before visiting the Forbidden City today?`
- 通过标准：外部 provider 异常时受控降级。

### 6.5 Out-of-scope 拒答
- 优先级：**P0**
- 在测什么：QA 只处理导览相关问题，越界问题要明确拒答。
- 示例：`Write me a sorting algorithm`
- 通过标准：
  - `supported = false`
  - `intent = out_of_scope`

### 6.6 QA 不改路线
- 优先级：**P0**
- 在测什么：QA 不能偷偷替用户执行 route edit。
- 通过标准：
  - QA 不直接改路线
  - 不返回 route-edit action

---

## 7. RAG 管理

### 7.1 latest 未初始化
- 优先级：**P0**
- 在测什么：还没建索引时，系统能不能明确说“现在没有记录”。
- 怎么测：`GET /api/v1/rag/index-runs/latest`
- 通过标准：返回 `404`，不是 `500`。

### 7.2 rebuild
- 优先级：**P0**
- 在测什么：管理员点 rebuild 后，系统能不能正确记录这次任务结果。
- 怎么测：`POST /api/v1/rag/index-runs/rebuild`
- 通过标准：状态可区分：
  - `skipped`
  - `succeeded`
  - `error`
- 真实验证补充：在正常环境里，rebuild 已真实返回 `succeeded + ready`；在 `RAG_ENABLED=false` 环境里，rebuild 已真实返回 `skipped + rag_disabled`。

### 7.3 latest 已有记录
- 优先级：**P0**
- 在测什么：建完索引后，latest 能不能正确返回最近一条记录。
- 怎么测：先 rebuild，再 `GET /api/v1/rag/index-runs/latest`
- 通过标准：返回最近一次记录。

### 7.4 QA 联动
- 优先级：**P0**
- 在测什么：RAG 不是只在 admin 接口里成功，而是 QA 真能用上。
- 怎么测：真实 guide session 下深问景点。
- 通过标准：QA 元数据里体现 `sql_then_rag` 路径。
- 真实验证补充：正常环境里，真实 QA 已返回 `retrieval_strategy = sql_then_rag`、`rag_backend_ready = true`、`rag_query_status = ok`；在 `RAG_ENABLED=false` 时，QA 仍可正常回答，但元数据会变成 `rag_backend_ready = false`、`rag_query_status = skipped`。

---

## 8. 手动改路线

### 8.1 当前 stop 可编辑
- 优先级：**P0**
- 在测什么：当前站和后续站还能改，用户还有调整空间。
- 覆盖操作：
  - replace
  - remove
  - reorder
  - shorten
  - add_stop
- 通过标准：当前 stop 和未来 stop 可编辑。

### 8.2 已完成 stop 不可编辑
- 优先级：**P0**
- 在测什么：已经走完的路线前缀必须冻结，不能被新编辑改掉。
- 通过标准：修改 completed prefix 返回受控错误。

### 8.3 operation-specific 字段校验
- 优先级：**P0**
- 在测什么：不同操作只能带自己的字段，传错应直接拦下。
- 示例：`operation = optimize_route` 时传 `add_stop_name`
- 通过标准：返回 `422`。

### 8.4 版本切换一致性
- 优先级：**P1**
- 在测什么：改路线后切了新版本，但 session/map/QA 还是要看到同一条路线。
- 通过标准：切版本后 session/map/QA 一致。

### 8.5 最后一站完成后不可再编辑
- 优先级：**P0**
- 在测什么：整个行程结束后，任何编辑都应该被拒绝。
- 通过标准：completed itinerary cannot be edited。

---

## 9. 评论与分享

### 9.1 Stop comments
- 优先级：**P1**
- 在测什么：评论是否能正常写入、读取，并供分享卡片聚合使用。
- 怎么测：`GET / POST /api/v1/comments/stops/{stop_id}`
- 通过标准：评论可写可读，数量统计正常。

### 9.2 Share card 基本可分享性
- 优先级：**P0**
- 在测什么：只有真正结束的 session 才能分享。
- 怎么测：`GET /api/v1/share-card/session/{guide_session_id}`
- 通过标准：只有 finished session 才 `is_shareable = true`。

### 9.3 Share card finished 一致性
- 优先级：**P0**
- 在测什么：分享卡片不能只看一个布尔值，要确认结束文案和完成时间也齐全。
- 通过标准：
  - `status = finished`
  - `is_shareable = true`
  - `trip_summary.completed_at` 有值
  - `subheadline = Trip complete — ready to share`

---

## 10. 异常与降级

### 10.1 缺 TTS key
- 优先级：**P1**
- 在测什么：没有 TTS key 时，主流程还能不能继续。
- 通过标准：
  - Guide content 仍返回文本
  - 音频 `unavailable`
- 真实验证补充：在缺 TTS key 的降级实例里，`cycle_content` 已真实返回文本，且 `audio_segments[*].status = unavailable`。

### 10.2 RAG disabled / 缺 key / DSN
- 优先级：**P1**
- 在测什么：RAG 配置不完整时，不该把 QA 或 admin 接口整体打崩。
- 通过标准：
  - rebuild 明确失败或 skipped
  - QA 不崩
- 真实验证补充：在 `RAG_ENABLED=false` 的降级实例里，`rebuild` 已真实返回 `skipped + rag_disabled`；QA 仍可正常回答，但元数据会显示 `rag_backend_ready = false`、`rag_query_status = skipped`。

### 10.3 LLM provider 错误
- 优先级：**P1**
- 在测什么：模型服务异常时，不能返回脏 JSON 或一堆内部错误。
- 通过标准：
  - 不返回脏 JSON
  - 用户看到明确降级文案

### 10.4 外部 provider 异常
- 优先级：**P1**
- 在测什么：live search / tts / embedding provider 出问题时，主流程不能整体 500。
- 通过标准：接口受控降级，不整体崩溃。
- 真实验证补充：在缺 Tavily key 的降级实例里，`live_info` 已真实返回：`status = unavailable`、`reason = missing_provider_config`、`degraded = true`、`confidence = low`，并明确引导用户去官网或可靠渠道确认当日信息。

---

## 11. 建议执行顺序

### 第一轮：P0 自动化
先跑：
```bash
.venv/bin/pytest tests/test_guide_job_runtime.py tests/test_rag_admin.py tests/test_session_lifecycle.py tests/test_qa.py tests/test_planner_edits.py
```

### 第二轮：P0 边界回归
再跑：
```bash
.venv/bin/pytest tests/test_guide_asset_latest.py tests/test_guide_content_cycle.py tests/test_share_card.py
```

### 第三轮：API 冒烟
重点：
1. health
2. rag latest / rebuild / latest
3. itinerary / guide session / start / finish
4. guide job / guide asset / guide content
5. qa ask
6. share-card

### 第四轮：异常与降级
再拆 key、provider、外部依赖做降级验证。

---

## 12. 结果记录模板

| 测试项 | 优先级 | 结果 | 备注 | 是否阻塞 |
|---|---|---|---|---|
| 示例：Guide job 可创建 | P0 | 通过 / 失败 |  | 是 / 否 |

