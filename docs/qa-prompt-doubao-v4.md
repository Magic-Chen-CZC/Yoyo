# QA Prompt for Doubao Mini v4

本文件记录当前主链路 `src/yoyo/modules/qa/prompts.py` 的 Doubao Mini 版本 prompt 结构，方便后续单独修改。

## 1. 目标
- 保持 JSON 输出契约
- `answer` 默认控制在 300 字以内
- 能简洁回答时尽量短
- 历史背景、文化解释等知识性问题可适当更长
- 长回复必须分 2~3 段，自然成段，不用 markdown 标题或项目符号
- 主回答携带最近 10 轮内对话作为上下文

## 2. System prompt 结构

### 2.1 通用基座
1. 角色：北京旅游问答助手
2. 能力边界：支持景点讲解、行程建议、旅行翻译、官方 live info、天气、文字导航
3. 不支持范围：编程、通用百科、法律、医疗、金融、拥挤度、人流量、排队热度、泛交通拥堵、无依据实时事实
4. Grounding 规则：
   - SQL 优先：景点简介、稳定事实、实用提醒、路线/会话状态
   - RAG 补充：更深历史、象征、建筑、中轴线背景
   - SQL/RAG 冲突时优先 SQL
   - 上下文不足时明确说明
5. 输出规则：
   - `answer` 用用户语言
   - 默认 300 字以内
   - 能短答时优先短答
   - 历史/文化深问可适度长一些
   - 长回复必须分 2~3 段
   - 不输出思考过程
   - 只输出一个 JSON 对象

### 2.2 intent 专属规则
- `translation`
  - 旅行短句翻译、双语展示、简短改写
  - 字段：`answer, status, reason, mode`
- `live_info`
  - 同日/近时段官方运营信息
  - 字段：`answer, status, reason, not_confirmed, confidence`
- `trip_assistant`
  - 当前路线推进、下一站建议、节奏建议、轻量安抚
  - 字段：`answer, status, reason, route_focus, references_current_stop, references_next_stop`
- `attraction_explain`
  - 景点介绍、看点、历史、文化价值、游览建议
  - 字段：`answer, status, reason, grounding, includes_history, includes_tips`

## 3. User prompt 结构

### 3.1 固定部分
1. 任务信息：`intent / user_language / query`
2. 判定规则：
   - 不要自行改 intent
   - 不要把普通景点问法改成 live_info
   - 不要因为中文口语或短句就判 out_of_scope
   - 不要补造路线状态、景点事实、实时事实
   - 只能使用提供的上下文

### 3.2 按 intent 注入上下文
- `translation`
  - `profile`
  - `recent_dialogue`
- `live_info`
  - `attraction`
  - `live_info`
  - `profile`
- `trip_assistant`
  - `session`
  - `attraction`
  - `profile`
  - `dialogue`
- `attraction_explain`
  - `attraction`
  - `profile`
  - `rag_support`
  - `dialogue`
- 其他通用路径
  - `session`
  - `attraction`
  - `profile`
  - `dialogue`

### 3.3 风格与输出要求
- `guide_style`
- 只返回一个 JSON
- JSON 前后不要有额外文本
- `answer` 简洁自然，可直接展示
- `answer` 默认 300 字以内
- 长回复必须自然分段

## 4. 上下文裁剪规则
- attraction list 字段取前 4 项
- `short_intro` / `history` 截断到 220 字
- profile list 字段取前 4 项
- session 只保留关键字段
- dialogue 取最近 10 轮，每条内容截断到 120 字
- live_info `sources` 取前 2 条
- rag 只保留前 3 个 chunk，每个 chunk 文本截断到 220 字

## 5. 当前版本号
- `prompt_version = qa-zh-v4-{intent}`

## 6. 对应代码文件
- `src/yoyo/modules/qa/prompts.py`
