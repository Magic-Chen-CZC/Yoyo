# Yoyo 待办事项（中文参考版）

这是当前集成分支的活动实施计划。

它替代了旧的 A/B 双轨 checklist，成为当前阶段的主待办文档。
当前阶段的重点不再是“从零补模块”，而是：
- 锁定第一阶段产品边界
- 支持前后端并行开发
- 去掉暂缓实现的 QA 改路线能力
- 为手动改路线补齐基于运行时状态的约束
- 持续推进 SQL-first + RAG fallback 后端的生产化收尾

---

## 0. 当前阶段已锁定的产品决策
- [x] 地图继续定义为**认知地图**，不是完整地图产品。
- [x] 高德继续只作为**路线引擎**，不是地图渲染层。
- [x] Guide 继续保持 **SQL-first**，不做 Guide-RAG。
- [x] QA 继续保持 **SQL-first + RAG fallback**。
- [x] Guide 刷新行为继续保持统一用户动作（`cycle_content`）。
- [x] 第一阶段 onboarding 继续采用 guest quick entry + 固定问卷。
- [x] itinerary 第一阶段入口继续保持 `template`、`manual_poi`、`ai_recommendation_selected`。
- [x] trip 生命周期继续采用 `pending`、`active`、`finished`。
- [ ] 去掉当前“通过 QA 改路线”的产品路径，当前阶段只保留**手动改路线**。
- [ ] 锁定手动改路线规则，只允许编辑**未完成的行程段**：
  - 已完成的 stop 固定
  - 当前 stop 仍可编辑
  - 后续 stop 可编辑

---

## 1. 当前分支上已经完成的能力

### 1.1 Onboarding 与用户画像
- [x] 游客快速进入 API
- [x] 固定版本化问卷流（`v1`，7 个问题）
- [x] 导游角色选择映射到 `guide_style_preference`
- [x] 问卷提交校验与用户画像映射

### 1.2 Planning 与路线创建
- [x] itinerary 创建支持 `template`、`manual_poi`、`ai_recommendation_selected`
- [x] 路线模板列表
- [x] AI 推荐接口
- [x] 手动 POI 选择输入
- [x] 版本化 itinerary 模型与 active version 切换

### 1.3 Session、GPS 与认知地图
- [x] 基于 `current_stop_index` 的 session runtime
- [x] 基于 per-stop threshold 的 GPS 到达检测
- [x] 到达后触发 playback 的基础行为
- [x] 稳定的 session current 返回结构
- [x] 稳定的认知地图 payload（markers / polyline / navigation summary）
- [x] map payload 中的 stop 知识摘要
- [x] map payload 中的评论统计

### 1.4 Guide、QA 与内容生成
- [x] 异步 guide generation job 链路
- [x] SQL-backed 多段导览内容
- [x] Guide 刷新的统一动作 `cycle_content`
- [x] QA 的 SQL-first + RAG fallback 骨架
- [x] QA 和 Guide 的 runtime LLM 文案生成路径
- [x] live-info provider abstraction 与来源元数据返回

### 1.5 社交与分享
- [x] stop 级评论 API
- [x] 已完成旅程的分享卡片聚合

### 1.6 运维与评测
- [x] RAG rebuild/latest 管理接口
- [x] LlamaIndex + pgvector 脚手架
- [x] batch eval / judge / comparative reporting 基础设施

---

## 2. P0 —— 当前阶段的边界重置与前后端契约收口

### 2.1 用当前阶段文档替换旧的 split-phase 工作文档
- [x] 将 `docs/todo.md` 重写为当前集成阶段的实施计划
- [ ] 保持 `docs/todo.zh-CN.md` 与新的 todo 结构同步
- [x] 更新 `README.md`，指向新的前后端契约文档
- [x] 更新 `docs/contracts.md`，使活跃契约与当前产品范围一致
- [x] 更新 `docs/architecture.md`，加入新的手动改路线语义
- [x] 更新 `docs/collaboration.md`，去掉过时的 A/B route-edit handoff 表述
- [x] 更新 `docs/current-session-summary.md`，不再把 QA 改路线当作当前 continuation point
- [x] 更新 `docs/b-stack-implementation-overview.md`，让 deferred items 与当前范围保持一致

### 2.2 新增一份完整的前后端接口定义文档
- [x] 新增 `docs/api-contracts-fullstack.md`
- [x] 记录统一 API 外层结构（`code`、`message`、`data`）
- [x] 覆盖当前前端会消费的全部第一阶段接口：
  - guest
  - questionnaire
  - planning
  - session
  - gps
  - guide
  - map
  - comments
  - share-card
  - qa
  - rag
- [x] 为每个接口补齐 request/response 示例
- [x] 为每个接口补齐状态语义与错误行为
- [x] 增加一节“手动改路线联调说明”
- [x] 标记哪些字段已经稳定，哪些仍是 first-phase provisional 字段

### 2.3 移除 QA 改路线产品路径
- [x] 从当前 QA runtime path 中移除 `planner_handoff`
- [x] 从 QA response metadata 中移除 `planner_handoff`
- [x] 删除 `planner_handoff` 相关的 QA skill / validator / formatter / schema 代码
- [x] 删除或重写仍依赖结构化 route-edit handoff 的 QA 测试
- [x] 清理所有仍将 QA route editing 当作当前产品能力的活跃文档

### 2.4 当前阶段仅保留手动改路线
- [x] 在当前文档中明确：`POST /api/v1/planning/itineraries/{itinerary_id}/edits` 是唯一 route-edit 入口
- [x] 在代码与文档里锁定当前规则：
  - 已完成 stop 固定
  - 当前 stop 可编辑
  - 后续 stop 可编辑
- [x] 确保已完成的 itinerary 不能再被继续编辑

---

## 3. P0 —— 基于运行时状态的手动改路线能力

### 3.1 路线编辑资格规则
- [ ] 从 session 进度中计算 route-edit 边界
- [ ] 对 active trip 统一使用 `current_stop_index` 作为主要编辑边界
- [ ] 明确 GPS arrival 本身**不会**冻结当前 stop
- [ ] 明确 playback `complete` / `skip` 才会推进 stop 完成状态
- [ ] 正确处理最后一个 stop 完成后的不可编辑语义

### 3.2 在 planning service 中落地编辑约束
- [x] 禁止对已完成 stop 做 `replace_stop`
- [x] 禁止对已完成 stop 做 `remove_stop`
- [x] 禁止 reorder 改动已完成前缀
- [x] 禁止 `shorten_route` 截掉当前 stop 或已完成前缀
- [x] 将 `add_stop` 限制在可编辑部分（第一阶段默认追加到尾部）
- [x] 让公开 route-edit schema 与实际支持的 operation 对齐（包括决定 `optimize_route` 的公开状态）

### 3.3 将可编辑边界暴露给前端
- [ ] 扩展 `session current` payload，加入 editability 字段
- [ ] 扩展 map marker payload，加入 completed/editable 状态
- [ ] 扩展 navigation summary，加入 completed/editable 边界信息
- [ ] 确保 route 版本切换后 session/map/frontend 的状态仍一致

### 3.4 保持版本化与 session remap 行为稳定
- [ ] 继续保持 route edit 为 version-based，而不是原地修改
- [ ] 当前 stop 变化时保留 current-stop remap 行为
- [ ] 当前 stop 变化后正确 reset playback state
- [ ] 确保 route edit 不会破坏已完成前缀

---

## 4. P1 —— 在边界收紧之后继续做 QA / Guide 生产化

### 4.1 去掉用户可见路径中的硬编码 QA fallback
- [x] 将 `translation` 的 phrase-map fallback 改成 runtime-LLM-first + 明确 degraded response
- [x] 将 deterministic `trip_assistant` 模板 fallback 改成更强的 route-aware 生成 + degraded 行为
- [x] 去掉 `attraction_explain` 面向用户的过渡态话术
- [x] 在配置缺失或上游失败时，让 `live_info` 返回明确 unavailable/degraded 响应
- [x] 收紧 attraction/profile fallback，避免面向生产路径静默混入 mock 数据

### 4.2 结构化输出与后处理加固
- [ ] 为 runtime QA response 增加 structured-output validation
  - [x] 第一步：translation structured-output 解析与校验
  - [x] 第一步：live_info structured-output 解析与校验
- [ ] 为 runtime Guide response 增加 structured-output validation
- [ ] 为 malformed LLM output 增加更安全的后处理
- [ ] 将 degraded-mode 响应明确化，而不是保留 placeholder 感
- [x] 先定义一版“最小影响风格”的 QA 结构化输出方案，覆盖：
  - `translation`
  - `live_info`
  - `trip_assistant`
  - `attraction_explain`
  并保持用户看到的 `answer` 仍是自由文本，结构字段只用于后端校验/状态判断

### 4.3 Guide 内容与资产流生产化
- [x] 基于以下用户画像优化 `cycle_content` 选择：
  - `answer_length_preference`
  - `interests`
  - `guide_style_preference`
- [x] 决定是否向前端暴露“剩余内容计数”
  - 当前决定：前端不显示剩余数量，继续使用 `more_content_available` 作为这一阶段的用户信号
- [x] 将 `audio` placeholder 语义升级为真实 TTS/media asset flow
  - 当前决定：接入一个真实 TTS 模型，API key 由用户后续配置
  - 时延要求：不要在每次 `cycle_content` 点击时同步生成整站所有音频，优先当前批次/当前 stop 的低时延生成，其余内容异步按需补齐

---

## 5. P1 —— QA RAG 路径生产化
- [ ] 在真实配置环境中补齐 backend-enabled pgvector retrieval
  - 代码/测试语义已完成收口；最终验证仍依赖真实 `rag_pgvector_dsn`、`rag_embedding_api_key` 和 `rag_enabled=true`
- [ ] 验证 embedding -> indexing -> query 的端到端链路
  - scaffold 与测试已覆盖 configured/degraded 分支，但最终端到端验证仍依赖真实后端环境与密钥
- [x] 加固 ingestion lifecycle 和 rebuild 行为
- [x] 明确 admin 侧 rebuild / index-run 的运维语义
- [x] 确保 QA metadata 能正确反映 configured / degraded 两类检索状态

---

## 6. P1 —— 测试与验收加固

### 6.1 Route / session / map 验证
- [ ] 增加“已完成 stop 不可编辑”的测试
- [ ] 增加“当前 stop 仍可编辑”的测试
- [ ] 增加“reorder 只能改后缀”的测试
- [ ] 增加“最后一个 stop 完成后剩余路线冻结”的测试
- [ ] 为 session current 的 editability 字段补测试
- [ ] 为 map marker 的 completed/editable 字段补测试

### 6.2 QA / Guide 失败路径覆盖
- [ ] 为 `qa`、`knowledge`、`live_info`、`guide` 和 runtime-LLM 后处理补模块级单测
- [ ] 为以下失败/降级场景补测试：
  - provider config 缺失
  - LLM 调用失败
  - structured output 异常
  - 真实数据缺失
  - 上游 provider 错误

### 6.3 端到端集成流
- [ ] 增加集成流：itinerary -> guide job -> GPS/playback -> session current/map
- [ ] 增加集成流：manual route edit -> version switch -> session remap -> map/session consistency
- [ ] 增加集成流：session-aware QA after route/session state changes
- [ ] 让 benchmark 在缺少必须 API key 时 fail fast 或标记 invalid

---

## 7. P2 —— 当前收口完成后的后续工作
- [ ] 等 planner 范围恢复后，将固定 starter planner source 升级成更真实的 planner source
- [ ] 决定多轮 QA 是继续 recent-turn-only，还是引入 conversation summary
- [ ] 等手动 route edit 能力稳定并完成验证后，再评估是否重新引入“QA 辅助改路线”能力

---

## 8. 当前推荐执行顺序
1. 重写 active docs（`todo`、`contracts`、`architecture`、`README`、collaboration docs）
2. 新增完整的前后端 API 契约文档
3. 删除 QA route-edit runtime 行为
4. 为手动 route edit 落地冻结规则
5. 将 editability 状态暴露到 session/map payload
6. 为新 route-edit 语义补测试 / 修测试
7. 再继续 QA / Guide / RAG 的生产化收尾

---

## 9. 未来 session 的工作规则
- 新 session 开始时，先阅读 `CLAUDE.md`、`README.md`、`docs/architecture.md`、`docs/contracts.md` 和本文件。
- 除非产品决策改变，不要把 QA route-edit execution 重新加回当前产品主路径。
- 每完成一个实现部分，都先更新这份 todo，再继续后续工作。
