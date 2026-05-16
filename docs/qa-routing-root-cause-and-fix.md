# QA Routing Root Cause and Fix

这份文档记录本轮 QA 误判问题的归因、修复点和后续调试建议。

## 1. 现象

在 E2E benchmark 和人工抽样中，出现了两类明显异常：

### 1.1 本应支持的问题被统一打成兜底拒答
典型问题：
- `如果带家人去天坛，应该怎么安排会更轻松？`
- `去天安门前，有哪些实用注意事项？`
- `带家人去故宫，给我一个简短建议。`
- `不要只给我简介，详细讲讲天安门背后的历史脉络和象征意义。`
- `请详细讲讲正阳门在北京中轴线和城市空间上的意义。`
- `我接下来应该去哪里，或者先做什么？`

错误表现：
- 被统一回复成：
  - `I can help with Beijing tour topics such as attractions, itinerary guidance, translation, and travel info.`

### 1.2 旅游邻接但当前不支持的问题也被统一打成同一句兜底拒答
典型问题：
- `今天去故宫的交通会不会很堵？`
- `北京今天会不会下雨？`

这类问题严格说不属于当前可完整支持能力，但直接用统一 out-of-scope 文案，产品表现过于生硬，也不利于后续扩展边界式处理。

---

## 2. 归因结论

### 结论：这不是纯 prompt 问题，根因主要在系统层，prompt 只是放大器

最终归因拆成两层：

#### 2.1 系统层根因（主因）
1. `domain_guard` 关键词覆盖不足
   - 很多中文景点问法没有被纳入支持范围
   - 尤其是：`天坛`、`正阳门`、`注意事项`、`中轴线`、`象征意义`、`带家人`、`怎么安排`

2. `intent_router` 对 attraction / live_info / out_of_scope 边界过于粗糙
   - attraction explain 的中文触发词不够
   - live_info 对 same-day official info 和边界型实时问题的区分不够
   - traffic / weather / crowd 这类旅游邻接实时问题没有单独边界处理策略

3. orchestrator 过早使用统一兜底拒答
   - 一旦 `domain_guard` 拒绝，直接返回统一 out-of-scope 文案
   - 导致“完全无关问题”和“旅游邻接但当前不支持问题”被混成同一种回应

#### 2.2 prompt 层问题（次因）
1. 老 prompt 对 attraction explain / live_info 边界约束不够
2. 对 casual Chinese tourism query 的保护不够强
3. user prompt 原来是大字典平铺，容易让小模型抓错重点

但 prompt 不是主因，因为：
- 在进入 LLM 之前，系统层已经可能把问题挡掉或分错流
- 同一个 prompt 改动只对部分模型有效，说明上游规则仍然是关键瓶颈

---

## 3. 本轮修复内容

### 3.1 修复 `domain_guard`
文件：
- `src/yoyo/modules/qa/domain_guard.py`

修复点：
- 扩充中文景点和旅游关键词：
  - `北京`
  - `故宫`
  - `故宫博物院`
  - `天安门`
  - `景山`
  - `景山公园`
  - `天坛`
  - `正阳门`
  - `前门`
  - `接下来`
  - `先做什么`
  - `历史`
  - `讲讲`
  - `介绍`
  - `注意事项`
  - `中轴线`
  - `象征意义`
- 增加旅游邻接动态主题识别：
  - `weather / rain / 天气 / 下雨`
  - `traffic / congestion / 交通 / 堵`
  - `crowd / busy / 拥挤 / 人多`
- 对“动态主题 + 旅游锚点”问题放行，而不是直接 out-of-scope

### 3.2 修复 `intent_router`
文件：
- `src/yoyo/modules/qa/intent_router.py`

修复点：
- 扩展 `attraction_explain` 触发词：
  - `worth visiting`
  - `how should i visit`
  - `practical tips`
  - `family`
  - `what should i know`
  - `历史`
  - `注意事项`
  - `值得去`
  - `怎么安排`
  - `带家人`
  - `象征意义`
  - `中轴线`
- 扩展 `trip_assistant` 中文线索：
  - `先做什么`
- 将 `live_info` 的强优先条件收紧为真正 same-day / official 信号
- 对 traffic / weather / crowd 增加 boundary live topic 信号
- 当 query 含边界型实时主题时，不再默认让 attraction_explain 优先

### 3.3 修复 orchestrator 的边界收口策略
文件：
- `src/yoyo/modules/qa/orchestrator.py`

修复点：
- 新增 `_detect_boundary_topic(query)`
  - 识别 `weather` / `traffic` / `crowd`
- 新增 `_boundary_topic_message(query)`
- 对旅游邻接但当前不支持的实时问题：
  - 不再返回统一 out-of-scope 文案
  - 改为更具体的边界式回答：
    - 当前不可靠支持该实时主题
    - 建议使用专门 live service
    - 仍可继续帮用户处理景点、行程、翻译、官方景点通知
- 对完全无关问题（如编程）：
  - 仍保持统一 out-of-scope 兜底

### 3.4 prompt 侧已做的配套修复
文件：
- `src/yoyo/modules/qa/prompts.py`
- `docs/qa-prompt-debugging.md`

修复点：
- 升级到 `qa-{intent}-v2`
- 明确 attraction explain / live_info 边界
- 明确 casual Chinese tourism query 不应轻易 out_of_scope
- 允许 travel-adjacent light chit-chat
- user prompt 改成结构化模板并按 intent 裁剪上下文

---

## 4. 归因判断：prompt vs 系统

### 4.1 哪些是系统问题
- 中文景点 query 被统一拒答
- traffic / weather 这种旅游邻接 query 被统一兜底拒答
- attraction explain / live_info 的规则边界过粗

这些问题在进入 LLM 前就已经发生，因此属于系统层主因。

### 4.2 哪些是 prompt 问题
- 进入生成后 attraction explain 漂向 live_info
- 对 casual Chinese tourism phrasing 的稳健性不够
- 小模型在大字典 prompt 下抓错重点

这些问题属于 prompt 层次因。

### 最终判断
- **主因：系统层（domain_guard + intent_router + orchestrator）**
- **次因：prompt 层（system prompt / user prompt 结构）**

---

## 5. 本轮新增验证

新增测试：
- `tests/test_qa_routing_regressions.py`
  - 验证中文 attraction explain 问题被支持
  - 验证 traffic / weather 边界问题被识别为旅游邻接问题
  - 验证中文深讲解问题不再漂去 attraction 之外的 intent
- `tests/test_qa.py`
  - 增加 weather / traffic 的 API 边界收口测试

当前最小回归结果：
- `32 passed`

---

## 6. 修复后的产品行为预期

### 应正常回答
- `如果带家人去天坛，应该怎么安排会更轻松？`
- `去天安门前，有哪些实用注意事项？`
- `带家人去故宫，给我一个简短建议。`
- `不要只给我简介，详细讲讲天安门背后的历史脉络和象征意义。`
- `请详细讲讲正阳门在北京中轴线和城市空间上的意义。`
- `我接下来应该去哪里，或者先做什么？`

### 应边界式收口，不应统一拒答
- `今天去故宫的交通会不会很堵？`
- `北京今天会不会下雨？`

### 应继续统一 out-of-scope
- `Write me a sorting algorithm.`

---

## 7. 后续建议

### 优先级 1
重新跑针对中文 attraction explain / live_info boundary / out_of_scope 的 E2E 子集，确认系统层修复已经实打实降低误判。

### 优先级 2
继续分模型调 prompt：
- GPT 可保留较完整 v2
- Gemini Flash / Flash Lite 更适合更短、更硬的 lite prompt

### 优先级 3
继续优化 scoring：
- 当前 `missing_expected_phrase` 过多，说明 scorer 对字面词过敏
- 后续应降低对精确词命中的依赖，提升语义容错

### 优先级 4
把当前路由演进到“规则优先 + 小模型兜底”而不是纯规则或纯模型：
- 规则继续处理明显案例
- 小模型只处理 attraction/live_info、trip_assistant/attraction_explain、边界实时问题等模糊题
- 单独设计 routing benchmark，而不是只看最终回答质量
- 当前代码层已先把这一层前置为可观测规则结果：`margin`、`needs_fallback`、`fallback_reason`，并把 `manual_route_edit_redirect` 提升为一级 intent，便于后续只在灰区样本上接小模型

### 优先级 5
面向东南亚扩展时，先做 multilingual routing evaluation：
- 高资源语言优先 direct routing
- 低资源语言再做 translate-to-English fallback
- 先比较 direct-route vs translate-then-route，再决定最终架构

---

## 8. 一句话总结

这次问题的主因不是“模型没答对”，也不只是“prompt 写得不够好”，而是：

**系统在进入 LLM 之前就把一部分中文旅游 query 和旅游邻接 query 过早挡掉或分错流了。**

prompt 优化有帮助，但只有先修系统层边界，prompt 的收益才会稳定显现。
