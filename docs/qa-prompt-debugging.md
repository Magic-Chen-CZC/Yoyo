# QA Prompt Debugging Notes

这份文档用于记录当前 QA 提示词的结构、目标、调试观察点与后续调参入口，方便持续迭代。

## 1. 当前提示词入口

核心文件：
- `src/yoyo/modules/qa/prompts.py`
- `src/yoyo/modules/qa/generator.py`
- `src/yoyo/modules/qa/orchestrator.py`

关键调用链：
1. `orchestrator.py` 判断 intent 并调用 `generate_qa_answer(...)`
2. `generator.py` 通过 `build_qa_generation_request(...)` 构造请求
3. `prompts.py` 生成 `system prompt` 与 `user prompt`

当前 prompt version：
- `qa-{intent}-v2`

## 2. v2 设计目标

本轮 v2 主要解决以下问题：
1. 英文景点介绍类问题被误漂到 `live_info`
2. 中文旅游问句因为口语化、简短而被误判成 `out_of_scope`
3. user prompt 直接拼接大字典导致小模型抓错重点
4. 当前产品需要允许轻量闲聊，而不是只答严格导览问题

## 3. v2 system prompt 的核心原则

### 3.1 产品能力边界
支持的核心能力：
- attraction explanation
- trip assistant / route guidance
- translation
- live info（仅限景点官网/官方通知、开放时间、预约、临时闭馆等）

### 3.2 允许轻闲聊
允许以下轻量对话：
- greetings
- pleasantries
- short reassurance
- brief travel-adjacent chit-chat

目的：
- 避免产品显得过于机械
- 避免把轻量、旅行邻接的自然交流都打成 `out_of_scope`

### 3.3 明确禁止的行为
- 不要把普通景点介绍问题转成 `live_info`
- 不要把中文旅游问题因为表达口语化而转成 `out_of_scope`
- 不要假装 QA 能直接执行 route edit
- 不要把 `live_info` 扩展到天气、交通、拥挤度
- 不要编造 attractions / route state / real-time facts / user preferences

## 4. intent-specific prompt 设计

### translation
目标：
- 支持短旅游句子和常见旅行场景翻译
- 不因为 query 太短而拒绝

结构化返回：
- `answer`
- `status`
- `reason`
- `mode`

### live_info
目标：
- 只在用户明确问 same-day official info 时启用
- 避免吞掉普通 attraction explain

结构化返回：
- `answer`
- `status`
- `reason`
- `not_confirmed`
- `confidence`

### trip_assistant
目标：
- 使用真实 session context
- 允许旅行邻接型轻闲聊
- 路线修改只做 redirect，不做执行

结构化返回：
- `answer`
- `status`
- `reason`
- `route_focus`
- `references_current_stop`
- `references_next_stop`

### attraction_explain
目标：
- 支持 casual / conversational attraction questions
- 普通景点介绍、为什么值得去、怎么玩、深历史都归到这一类
- 不要自动漂去 `live_info`

结构化返回：
- `answer`
- `status`
- `reason`
- `grounding`
- `includes_history`
- `includes_tips`

## 5. v2 user prompt 结构

v2 不再直接把一大段 Python dict 平铺给模型，而是按以下结构组织：

1. `Task`
2. `Decision rules`
3. 按 intent 裁剪后的上下文
4. `Answer style`
5. `Output`

### 5.1 按 intent 裁剪上下文
- `translation`
  - 只给 profile 和少量对话历史
- `live_info`
  - 给 attraction facts、live info、profile
- `trip_assistant`
  - 重点给 session facts、attraction、profile、dialogue
- `attraction_explain`
  - 重点给 attraction、profile、rag、dialogue

这样做的原因：
- 减少噪音
- 降低小模型被无关上下文带偏的概率
- 让模型先读到“任务和规则”，再读事实

## 6. 重点观察指标

后续调试时建议重点看这些指标：

### 6.1 意图漂移
重点观察：
- attraction explain 是否被误答成 `live_info`
- 中文旅游 query 是否被误答成 `out_of_scope`
- trip assistant 是否误答成 attraction explain

### 6.2 结构化输出稳定性
在 `generator.py` 中重点观察：
- `structured_output_valid`
- `structured_output_type`
- `fallback_used`

### 6.3 metadata 语义是否稳定
重点观察：
- `intent`
- `supported`
- `retrieval_strategy`
- `rag_backend_ready`
- `rag_query_status`
- `manual_route_edit_redirect`
- `degraded`
- `degraded_reason`

### 6.4 闲聊边界是否合适
重点观察：
- greetings / thanks / reassurance 是否被自然承接
- 是否开始过度回答与旅游无关的话题

## 7. 推荐调试顺序

1. 先看 `out_of_scope` 和 `live_info` 的误判率是否下降
2. 再看中文 attraction explain 是否恢复正常
3. 再看 profile personalization 是否更稳定
4. 最后观察 casual / chit-chat 是否自然但不过界

## 8. 本轮建议重点 case

建议优先回归：
- `E2E-SQL-001`
- `E2E-SQL-002`
- `E2E-SQL-003`
- `E2E-SQL-004`
- `E2E-LIVE-001`
- `E2E-LIVE-003`
- `E2E-LIVE-004`
- `E2E-OOS-001`
- `E2E-OOS-002`

原因：
- 这些 case 最能反映 prompt 是否还在把 attraction 问题漂向 live_info，或把中文旅游 query 漂向 out_of_scope。

## 9. 后续可继续调的方向

### 9.1 如果 attraction 仍漂向 live_info
继续强化：
- attraction explain prompt 里的反误判规则
- intent router 规则而不只是 generation prompt

### 9.2 如果中文问题仍漂向 out_of_scope
继续强化：
- system prompt 中对 casual Chinese tourism query 的说明
- intent router 对中文 query 的规则样本

### 9.3 如果闲聊放得太开
可以改成：
- 只允许 travel-adjacent chit-chat
- 更短地收口回旅游上下文

### 9.4 如果结构化输出仍不稳
可以继续：
- 缩短 user prompt
- 降低上下文噪音
- 进一步约束每个 intent 的 JSON 样式

## 10. 当前建议

先不要一次性再扩很多逻辑。
优先验证：
- v2 prompt 是否改善意图边界
- 尤其是 attraction explain / live_info / out_of_scope 之间的边界

如果 v2 仍不够，再考虑把 intent router 的规则和 prompt 一起收紧。
