# Yoyo 待办事项（中文参考版）

这是当前按 A/B 双轨拆分后的活动待办清单。

---

## 共享 / 协作事项
- [x] 将共享重叠契约写入 `docs/contracts.md`
- [x] 在 `docs/architecture.md` 中冻结共享的 `itinerary_version.plan_json` 契约
- [x] 在 `docs/architecture.md` 中冻结共享的 `guide_generation_job.result_json` 契约
- [x] 在 `docs/architecture.md` 中冻结共享的 `guide_session.context_json` 字段归属
- [x] 冻结 `session current` 接口的返回契约
- [x] 在 `docs/architecture.md` 中定义 GPS -> guide trigger 的交接行为
- [x] 定义 `planner_handoff` 的结构化 payload 契约
- [x] 确定下一轮 schema 变更的 migration 归属规则
- [x] 保持 `api/router.py` 的 wiring 变更尽量小且尽量晚
- [x] 在大范围 QA 验证前完成以上共享契约项

---

## A 轨：Planner / Session / Map / GPS

### A1. 路线编辑与版本管理
- [x] 增加 route edit 请求 schema
- [x] 实现 replace stop 操作
- [x] 实现 remove stop 操作
- [x] 实现 reorder stop 操作
- [x] 实现 shorten route 操作
- [x] 每次编辑都创建新的 `itinerary_version`
- [x] 编辑后切换 active itinerary version
- [x] 保持历史版本可查询
- [x] 增加版本切换测试

### A2. Session 运行时状态
- [x] 在 session runtime model 中加入 `current_stop_index`
- [x] 不再假设当前 stop 永远是第一个 stop
- [x] 根据 session state 计算 current stop
- [x] 根据 session state 计算 next stop
- [x] 增加 session progression 测试

### A3. GPS 与 geofence
- [x] 增加第一版距离计算 helper
- [x] 增加 per-stop arrival threshold
- [x] 用户进入阈值时标记为 arrived
- [x] 到达 stop 时更新 session runtime
- [x] 准备给 guide playback 的 trigger signal
- [x] 增加 geofence 逻辑测试

### A4. Map payload 改进
- [x] 保证 marker 字段稳定
- [x] 保证 polyline 字段稳定
- [x] 让 current/next stop 与 `current_stop_index` 对齐
- [x] 暴露更适合前端消费的 navigation summary
- [x] 增加 map payload 测试

### A5. 开发契约
- [x] 确保每个 stop 都有 `name/category/latitude/longitude/recommended_duration_minutes`
- [x] stop 契约变更时同步更新 `docs/architecture.md`

---

## B 轨：Guide / QA / Retrieval / Eval

### B1. QA 质量升级
- [x] 让 `planner_handoff` 返回结构化 route-edit intent
- [x] 强化 `trip_assistant` 的 route-aware 回答
- [x] 强化 `attraction_explain` 的回答格式
- [x] 将 `translation` 从 placeholder 模式升级出去
- [x] 增加按类别的回答格式测试

### B2. Live-info provider 集成
- [x] 引入 live-info provider abstraction
- [x] 增加 provider-backed source records
- [x] 在响应中保留 `updated_at` 和来源元数据
- [x] 增加 graceful failure / not-confirmed 行为
- [x] 增加带 source 的 live-info 响应测试

### B3. Guide generation 丰富化
- [x] 扩展 `result_json`，加入 guide script payload
- [x] 扩展 `result_json`，加入 card payload
- [x] 预留 TTS-ready 输出字段
- [x] 增加丰富 guide generation 输出的测试

### B4. Playback 与 guide asset 改进
- [x] 将 GPS trigger action 接到 playback transition
- [x] 增加 `trigger` 流程测试覆盖
- [x] 在 session context 中增加更丰富的 playback metadata
- [x] 确保 active guide asset 始终反映最新成功版本

### B5. 模型评测改进
- [x] 批量 query 生成
- [x] 多 provider eval runner
- [x] 成本 / 延迟汇总
- [x] 基础 rubric 评分
- [x] 支持批量多模型运行
- [x] 英文 81-query 数据集
- [x] 增强按类别的评分 rubric
- [x] 增加 comparative markdown 报告生成
- [x] 增加 category breakdown 报告
- [x] 增加 per-model 排名输出
- [x] 跑第一轮真实 benchmark

### B6. 第一轮真实 benchmark 执行
- [x] 准备带 provider key 的 `.env`
- [x] 确认第一轮 benchmark matrix
- [x] 运行 shortlisted models 的 English 81-query batch
- [x] 将结果保存到 `evals/results/`
- [x] 汇总 latency / cost / score 对比

---

## B 轨：SQL-first 收尾阶段
- [x] 采用 PostgreSQL 作为 B 轨 SQL-first 知识存储
- [x] 生成 50 条 mock PostgreSQL attraction/profile 数据
- [x] 为 QA 和 Guide generation 增加共享 SQL-first 知识层
- [x] 增加 PostgreSQL seed 脚本，并让 retriever 优先读数据库、mock 作为 fallback
- [x] 将 attraction knowledge 从静态 catalog 迁移到 PostgreSQL-backed retrieval
- [x] 增加 profile-aware guide generation
- [x] 为 QA 增加 hybrid retrieval（SQL + live info）
- [x] 将 `qa_messages` 接入多轮 QA 记忆
- [x] 扩展 `planner_handoff` 提取覆盖面
- [x] 丰富 guide generation 输出，加入 per-stop script 内容
- [x] 在不破坏 A/B ownership 边界的前提下升级 playback metadata
- [x] 更新 eval 架构以反映 SQL-first 阶段
- [x] 在 README 中补充当前 SQL-first 本地运行流程和 seed 步骤
- [x] 增加一份紧凑版的 B 轨第一轮模型选型测试文档
- [x] 在模型选型文档中加入第一轮 shortlist 和测试用例字段定义
- [x] 在模型选型文档中加入执行顺序和每条 case 的结果记录模板
- [x] 增加第一轮自动化评测专用的模型矩阵和可执行数据集
- [x] 记录未来真实数据接入时的 prompt-safe SQL 字段暴露边界
- [x] 在代码中落地 prompt-safe projection，并引入导览风格偏好控制
- [x] 增加共享运行时 LLM 层，供产品 QA 和 Guide generation 复用
- [x] 将 Guide generation 的文本字段接入运行时 LLM，并保留 deterministic fallback
- [x] 将 QA 的 attraction/trip/live/translation 输出接入运行时 LLM，并保留规则 fallback
- [x] 修复项目根 `.env` 加载问题，确保 eval/runtime 都能稳定读取 key
- [x] 在修复 key 加载后重新跑 round1 模型评测并导出最终 Excel
- [x] 基于 round1 结果增加一份 Gemini 第二轮聚焦测试文档
- [x] 增加 Gemini 第二轮可执行模型矩阵和数据集文件
- [x] 将 Gemini 第二轮数据集扩展到约 200 条，并补齐 judge-friendly metadata
- [x] 在 judge 接入前增加 hard-check 评分结构
- [x] 接入 `gpt-5.4-mini` judge 路径并生成 judge 结果文件
- [x] 扩展报告和 Excel，使其同时展示规则分和 judge 分
- [x] 跑完整的 Gemini 第二轮（200 条）并导出最终 Excel

## B 轨后续要做的事项
- [ ] 将 Gemini 第二轮数据集真正补齐到约 200 条，并保持 judge-friendly metadata 一致性
- [ ] 完整接入 `gpt-5.4-mini` judge，并稳定输出 judge 结果文件
- [ ] 在报告中同时展示规则分、judge 分和融合后的结论
- [ ] 导出带 judge 结果的最终 Excel 文件
- [ ] 继续优化 Gemini 在 `planner_handoff` 上的结构化理解稳定性
- [ ] 继续优化 Gemini 在 `live_info` 上的 same-day verify 和谨慎表达
- [ ] 继续优化 Gemini 在 `trip_assistant` 上的 route guidance 稳定性
- [ ] 继续优化 translation 的简洁性和少解释风格
- [ ] 接入真实 PostgreSQL attraction 数据替换 mock 数据
- [ ] 接入真实 PostgreSQL user profile 数据替换 mock 数据
- [ ] 最终确认 prompt-safe 字段暴露边界并落到真实数据流
- [ ] 恢复飞书 MCP 的用户授权，并把本地总结同步到飞书
- [ ] 补齐正式测试体系（单元测试、集成测试、回归测试）

## 当前建议
- A 轨默认视为已完成
- B 当前处于 SQL-first 收尾阶段
- 当前阶段用 PostgreSQL 存 attraction/profile 知识，实时变化仍由 live search 提供
- 当前阶段不做 RAG，后续只有在 SQL 知识不足时再考虑引入
- 每完成一个 B 轨实现阶段，都先更新这份 todo 再继续
