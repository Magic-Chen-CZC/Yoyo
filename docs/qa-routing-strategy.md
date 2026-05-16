# QA Routing Strategy

这份文档定义当前推荐的 QA 路由演进方向：**翻译器预处理 + 规则 + 小模型分类器 + 分处理管道**。
当前不再把“多语种 direct routing first”视为默认方案，而是统一先经过翻译器，把 query 转成中文后再进入意图识别模块。

## 1. 为什么需要新的路由策略

本轮问题定位表明：
- 单靠 prompt 不能稳定修复所有误判
- 纯规则路由在中文口语表达、边界型实时问题和多意图混杂问题上容易漂移
- 但直接把所有问题交给小模型路由，会增加时延、成本，并削弱可解释性

因此当前推荐方案不是“用模型替换规则”，而是：

> **规则优先 + 小模型只处理模糊题**

---

## 2. 推荐架构

### 第一层：translation preprocessor
目标：
- 当前收口实现：仅当 `user_language` 不是中文（`zh*`）时，query 才进入翻译器
- 设计硬约束：所有外语和东南亚语种 query 都要先转成中文 canonical query，再进入规则/分类器；不要为外语单独维护路由关键词库
- 将非中文 query 转成中文语义表示，再进入后续意图识别模块
- 保留原文、源语言、翻译后中文 query，方便 debug 与追踪

推荐原则：
- 翻译器是统一预处理层，不直接负责最终意图判断
- 后续所有规则与分类器默认围绕中文 query 工作
- 即使统一翻译到中文，也应保留原文作为审计与误判排查信息

### 第二层：domain guard / rule layer
目标：
- 只处理高精度规则：明显域外、明确边界、明确 redirect 类问题
- 不承担大部分模糊语义识别
- 对于不是高置信规则命中的问题，交给分类器承接

推荐原则：
- 规则层是护栏，不是主分类器
- 宁可少拦，也不要误杀旅游问题
- 它只做 high-precision hard deny / boundary / redirect / strong live-info signal
- 当前实现已开始收口为：`raw_query` 保留、表达归一化、`jieba` 分词、短语直命中、句式+关键词命中、boundary 检测、fallback 决策
- 归一化只负责统一表达，不直接产出意图标签
- follow-up 常见短句不再作为规则层信号；规则层只在高把握命中时 direct-pass，其余模糊 query 默认进入 fallback classifier
- 中文规则层不再维护英文词表；英文或其他非中文输入应先做 translator pivot，再复用同一套中文规则资产

### 第三层：intent classifier
目标：
- 负责完整分类，而不是只给一个“域内/域外”的粗判断
- 当前建议 intent 至少包括：
  - `attraction_explain`
  - `trip_assistant`
  - `translation`
  - `live_info`
  - `manual_route_edit_redirect`
  - `out_of_scope`

这里的关键点：
- `out_of_scope` 不能只靠规则层识别
- 模糊语义、多说法表达、多轮短 follow-up 应主要由分类器承接
- 当前代码层已经具备可观测 routing metadata：
  - `confidence`
  - `margin`
  - `needs_fallback`
  - `fallback_reason`

当前已经接入了一个**受配置控制**的小模型分类兜底 hook：
- 开关：`qa_router_fallback_enabled`
- 当前默认 provider/model：`openrouter` + `openai/gpt-5.4-nano`
- 只在 `needs_fallback = true` 时调用
- 只做 intent classification，不生成最终回答

### 第四层：pipeline router
分类完成后，不同 intent 进入不同处理管道，例如：
- `attraction_explain` -> SQL / RAG
- `trip_assistant` -> session context + SQL
- `live_info` -> official live search / source-aware live pipeline
- `manual_route_edit_redirect` -> product redirect handler
- `out_of_scope` -> boundary / reject handler
- `translation` -> translation pipeline

### 第五层：handler / answer assembly
路由完成后再进入对应 handler。

对于当前不应完整回答的问题：
- 不统一打成死板 out_of_scope
- `out_of_scope` handler 可以根据 subtype 或 travel-adjacent signal 输出更具体的收口文案
- `live_info` 由独立 API 解决；天气、交通、拥挤度不应混入同一产品语义

当前代码语义已经对齐到：
- `manual_route_edit_redirect` 现在是一级 intent，而不是 `trip_assistant` 内的后处理特判
- `weather_info` 已升级为正式 supported intent，走 Amap weather provider + 确定性 formatter，而不是继续留在 boundary / `out_of_scope`
- `navigation_text` 已升级为正式 supported intent，但当前不再只是 point-to-point intent：导航链路已收口为“规则优先槽位提取 -> GPS/current-stop origin hydration -> 北京地点库消歧 -> fallback 只补结构 -> Amap 坐标优先单段导航 -> multi-leg 聚合”，从而支持 `下一站怎么去`、`到X怎么走`、`从A到B怎么走`、`从A到B再到C`，并避免 `天坛` 这类同名地点漂到北京外；出行方式支持 `walking/driving/transit`，未指定时按直线距离 3km 阈值默认步行或公共交通
- crowd / queue / traffic status 仍保留为 `out_of_scope` boundary subtype，由 handler 输出边界式收口文案

---

## 3. 为什么不建议全量模型路由

### 3.1 成本与时延
每条 query 都先走模型路由，会带来：
- 额外推理成本
- 额外时延
- 端到端响应时间抖动

### 3.2 可解释性下降
规则路由的问题很容易 debug：
- 看命中了哪些关键词
- 看优先级和打分

全量模型路由会让：
- 错误更难复盘
- 稳定性问题更难定责

### 3.3 小模型本身也会漂
特别是在：
- 中文口语表达
- 多语种小语种
- live_info / attraction explain 边界题

因此最优路径不是“用模型替换规则”，而是“把模型留给规则最不稳定的灰区”。

---

## 4. 推荐的路由模型选型方向

当前推荐把 `openai/gpt-5.4-nano` 作为第一条小模型路由器基线。

理由：
- 在现有中文/英文边界问题里比 Gemini Flash 系列更稳
- 在 prompt 收紧后表现出较好的边界理解能力
- 适合做低成本但仍要求较强分类稳定性的 intent disambiguation

建议同时保留这些候选做 sweep：
- `openai/gpt-5.4-nano`
- `google/gemini-2.5-flash-lite`
- `google/gemini-2.5-flash`
- 后续可加入 Qwen 或其他多语种小模型候选

注意：
- 路由模型和最终回答模型不必一致
- 路由器的核心指标不是“写得多好”，而是：
  - intent precision
  - 边界稳定性
  - 多语种鲁棒性
  - 成本/时延

---

## 5. 路由测试集设计建议

建议新增一套**专用 routing benchmark**，不要直接复用生成质量测试集。

### 5.1 路由标签建议
- `attraction_explain`
- `trip_assistant`
- `translation`
- `live_info`
- `weather_info`
- `navigation_text`
- `manual_route_edit_redirect`
- `out_of_scope`

说明：
- 天气现在已经作为正式 supported intent 单独测试
- 文字导航现在已经作为正式 supported intent 单独测试，专项维度拆成：next-stop、destination-only with GPS、destination-only with current stop、explicit route、multi-leg aggregation、北京地点消歧、route-edit/trip boundary negative
- 交通拥堵 / 拥挤度 / 排队热度 继续作为 `out_of_scope` 的细分边界样本来测
- handler 层可以再根据 subtype 输出更具体的边界式收口文案

### 5.2 样本结构建议
每条样本至少包含：
- `case_id`
- `language`
- `query`
- `query_zh`（如适用）
- `expected_intent`
- `expected_boundary_behavior`
- `requires_session_context`
- `has_same_day_signal`
- `notes`

### 5.3 推荐板块
1. 中文 attraction explain 口语问法
2. 英文 attraction explain 与 live_info 边界题
3. trip assistant vs attraction explain 混合题
4. route edit redirect 题
5. 完全 out_of_scope 题
6. 天气 / 交通 / 拥挤度边界题
7. 多轮短 follow-up 题

---

## 6. 当前推荐结论

1. `domain_guard` 只做 hard deny，不再因为“弱旅游信号”提前拒答
2. `intent_router` 负责完整分类，并只把明确 boundary 题收口到 `out_of_scope`
3. weather / traffic / crowd 这类明确产品边界问题继续直接拒答，不进入 fallback
4. 其余规则未命中或低置信 query 应优先交给小模型兜底，而不是先落固定 `out_of_scope`
5. `live_info` 保留为独立 intent，但具体内容通过专门 API 处理

---

## 7. 后续执行建议

### 第一步
先把 `domain_guard` 重构成 high-precision hard deny only。

### 第二步
把 `intent_router` 改成完整分类器：
- attraction_explain
- trip_assistant
- translation
- live_info
- manual_route_edit_redirect
- out_of_scope

### 第三步
给 router 增加：
- `confidence`
- `margin`
- `needs_fallback`

### 第四步
只对模糊题接入小模型 routing fallback。
