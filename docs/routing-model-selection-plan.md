# Routing Model Selection Plan

这份文档用于定义下一阶段的小模型分类器选型与专用测试集设计。当前策略已更新为：所有 query 先统一进入翻译器转成中文，再进入“规则 + 小模型分类器”的意图识别模块，因此这里的选型目标不再是 multilingual direct router，而是中文分类器。

## 1. 目标

下一阶段的目标不是再继续直接讨论“哪个小模型感觉更好”，而是建立一套可重复的 routing benchmark，比较：
- 纯规则
- 规则 + 小模型兜底
- 多个小模型候选
- direct route vs translate-then-route

## 2. 当前推荐架构

推荐路线：
- **翻译器先把 query 统一转成中文**
- **规则层只保留高精度护栏**
- **小模型分类器负责模糊语义承接**
- **分类后再进入不同处理管道**

不推荐：
- 立即全量切换到模型自由回答式路由
- 用纯关键词规则承担主分类职责
- 继续把 multilingual direct routing 作为默认主方案

## 3. 第一批 routing-model 候选

建议第一批至少比较：
- `openai/gpt-5.4-nano`
- `google/gemini-2.5-flash-lite`
- `google/gemini-2.5-flash`

后续可补：
- Qwen 系列中更偏多语种的小模型
- 其他具备多语种能力的小模型

## 4. routing benchmark 的任务标签

建议专门做路由标签，而不是只用最终回答标签：
- `attraction_explain`
- `trip_assistant`
- `translation`
- `live_info`
- `manual_route_edit_redirect`
- `out_of_scope`

说明：
- 天气 / 交通 / 拥挤度 当前先作为 `out_of_scope` 的边界子类来测
- 重点不是给它们单独主 intent，而是验证 router 能否稳定识别“旅游邻接但当前不完整支持”的问题

## 5. 单条 routing case 建议字段

- `case_id`
- `language`
- `query`
- `query_zh`（如适用）
- `expected_intent`
- `expected_boundary_behavior`
- `requires_session_context`
- `has_same_day_signal`
- `is_colloquial`
- `market`
- `notes`

## 6. 推荐数据集板块

### 6.1 中文边界题
目标：
- 验证中文口语 query 是否稳定

覆盖：
- attraction explain 深问
- practical tips
- family phrasing
- casual route guidance
- weather / traffic / crowd 边界

### 6.2 英文边界题
目标：
- attraction explain vs live_info
- trip assistant vs attraction explain
- out_of_scope precision

### 6.3 多轮短 follow-up
目标：
- `那这个呢`、`what about this one`、`and next?` 这类依赖历史的问题

### 6.4 route-edit redirect
目标：
- 路由器能不能稳定识别“需要 redirect，而不是执行”的问题

### 6.5 boundary-live-topic
目标：
- 不把天气/交通/拥挤度误识别成普通 live_info 或 attraction explain

## 7. 推荐执行顺序

1. 先建 routing-only dataset
2. 先跑中文 + 英文
3. 先比较纯规则 vs 规则 + 小模型兜底
4. 再决定是否上线模型兜底路由

## 8. 当前建议结论

- 当前值得做小模型分类器选型
- 分类器应服务于“规则 + 分类器 + 分处理管道”的架构，而不是独立替代全部规则和后续 pipeline
- 多语种 query 当前不再默认 direct routing，而是统一先翻译到中文，再进入同一套中文 intent benchmark
- 东南亚首批建议语种：泰语、越南语、印尼语、马来语、菲律宾语
- 后续 benchmark 应同时记录：原文、翻译后中文 query、intent 正确率、分类器成本/时延、以及不同 pipeline 的命中质量
- 2026-05-08 的 zh-hard v1 正式结果已落地：`rules_only=0.5694`，`qwen-flash=0.8611`，`qwen3.5-flash-2026-02-23=0.5694`，`qwen-turbo=0.8889`
- 当前第一轮推荐候选已经收口为 `qwen-turbo`；`qwen-flash` 可作为更便宜的次优备选；`qwen3.5-flash-2026-02-23` 在本轮配置下未产生有效 fallback 覆盖
- 正式报告请看 `docs/routing-zh-hard-benchmark-report-2026-05-08.md`
