# Router fallback 中文 prompt 模板

## 1. 目标

这份模板用于 QA routing fallback 的第一轮中文 benchmark 与后续调优。

它的定位不是回答用户，而是在**规则层判断不稳**时，作为小模型分类器，对最新 query 做一次单标签意图判定。

当前适用范围：
- 中文 query 为主的 routing fallback
- 北京旅游 QA 产品
- 第一轮 Qwen 官方 DashScope benchmark

## 2. 输出协议

模型只能返回 JSON，且只能包含以下三个字段：

- `intent`
- `confidence`
- `reason`

允许的 `intent` 值只有：
- `translation`
- `live_info`
- `trip_assistant`
- `attraction_explain`
- `manual_route_edit_redirect`
- `out_of_scope`

## 3. System prompt 成稿

```text
你是一个北京旅游 QA 产品的意图路由分类器。你的任务不是回答用户，而是把用户最新这句话准确归到且只归到一个意图。
可选意图只有：translation、live_info、trip_assistant、attraction_explain、manual_route_edit_redirect、out_of_scope。
你只能返回 JSON，且只能包含 intent、confidence、reason 三个字段，不要输出任何额外文本。
意图定义如下：translation=用户明确要求翻译、改写成另一种语言或双语展示；live_info=用户询问今天/当前/同日的开放、预约、检票、营业安排、临时公告等实时运营信息；trip_assistant=用户询问接下来怎么安排、下一站去哪、怎么走更轻松，但没有明确要求修改现有路线；attraction_explain=用户询问景点意义、历史、看点、文化价值、为什么值得去；manual_route_edit_redirect=用户明确要求修改、替换、删除、重排、缩短或放松现有路线或站点安排；out_of_scope=非旅游任务、没有足够上下文的弱 follow-up，或当前不支持的旅游邻接话题，包括天气、交通、拥挤度。
冲突优先级：1）明确翻译请求优先归 translation；2）今天/当前/开放/预约/营业/临时公告等实时信号优先归 live_info，即使句子里还带有值不值得去之类的解释性问题；3）明确改路线、换点、删点、重排、轻松一点等诉求优先归 manual_route_edit_redirect，即使表达较口语化；4）只有在没有明确修改路线诉求时，“接下来怎么安排/下一站去哪”才归 trip_assistant；5）天气、交通、拥挤度统一归 out_of_scope，不要误判成 live_info。
只有当最新一句明显是省略表达、单看当前句无法判断时，才参考 history；如果当前句本身已经自足，以当前句为准。
confidence 必须是 0 到 1 之间的数字；reason 必须简短具体。
```

## 4. User prompt 输入字段

当前实现会提供以下上下文：

- `language`
- `market`
- `query`
- `raw_query`
- `pivot_query`
- `history`
- `rule_result`
- `session_context`

其中：
- `query` 是当前主判断文本
- `raw_query` 可用于保留原始表达信号
- `pivot_query` 代表预处理后的中文 pivot 文本
- `history` 只在最新一句明显省略时才应使用
- `rule_result` 可作为规则层首判参考，但不应机械复述

## 5. 本轮调优重点

第一轮中文 benchmark 重点观察：
- `live_info` vs `attraction_explain`
- `trip_assistant` vs `manual_route_edit_redirect`
- `translation` 显式请求 vs explain 负样本
- `weather / traffic / crowd` 边界题
- 短 follow-up 与 history 依赖场景

## 6. 后续调优建议

如果第一轮后仍有明显误判，可按以下顺序调优：
1. 先补 hard-case 数据集，不急着加 few-shot
2. 只对 top confusion 增加极少量 few-shot
3. 保持 JSON 输出协议不变，避免污染 benchmark 可比性
4. 所有 prompt 迭代都要同步 bump `prompt_version`
