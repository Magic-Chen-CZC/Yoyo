# QA Intent Routing Rule Design

这份文档说明 QA 规则路由的维护方案。当前只作为设计与规则资产，不直接改变 runtime 行为。

规则资产入口：

- `docs/qa-intent-keyword-library.yaml`
- `docs/qa-intent-rule-maintenance.md`

## 目标

规则层只处理高置信、可解释的路由。

不追求 rules-only 覆盖所有 query；低置信、冲突和表达异常的 query 应进入 router fallback 模型。

## 总体流程

```text
raw_query
  -> language preprocess / Chinese pivot
  -> normalize
  -> politeness stripping
  -> jieba + custom dictionary
  -> entity / slot extraction
  -> evidence extraction
  -> per-intent policy scoring
  -> conflict resolver
  -> direct pass or fallback model
```

## 中文 Pivot 硬约束

规则路由只消费中文标准问法。

所有外语、东南亚语种和中外混合 query，必须先进入 translator preprocess，生成 `pivot_text` 后再做 normalize、分词、实体槽位抽取和规则评分。后续规则库只维护中文关键词、中文句式和中文冲突策略，不为英文或小语种单独扩展 intent 词库。

这个约束的目的：

- 一套规则流程覆盖中文、英文和东南亚语言，避免多套关键词库漂移。
- 把外语质量问题收敛到翻译层，便于单独 benchmark `raw_query -> pivot_text` 的意图保持率。
- 解决 `hello, how do I get to Forbidden City` 这类 raw 英文在规则层被 `hello` 干扰的问题：它应先变成 `你好，怎么去故宫`，再由中文规则剥离礼貌词并命中 `navigation_text`。
- 人工排查仍保留 `raw_query`、`source_language`、`pivot_text`、`translation_confidence` 和 translator provider/model，不能只看 pivot 后文本。

显式翻译请求是例外中的特殊处理：路由仍基于中文 pivot 判断 `translation` intent，但后续执行翻译时必须保留 `raw_query` 里的原文片段、引号内容、目标语种和展示场景，避免 pivot 改写掉真正要翻译的文本。

## QueryFrame

建议后续 runtime 内部使用统一结构：

```python
QueryFrame(
    raw_text="hello, how do I get to Forbidden City?",
    pivot_text="你好，怎么去故宫？",
    normalized_text="你好 怎么 去 故宫",
    content_text="怎么 去 故宫",
    source_language="en",
    pivot_language="zh",
    tokens=["怎么", "去", "故宫"],
    politeness_prefix=["你好"],
    entities={"attractions": ["故宫"]},
    slots={"destination": "故宫"},
    translation={
        "provider": "xfyun_its",
        "model": "its",
        "confidence": 0.92,
        "raw_preserved": True,
    },
)
```

`content_text` 是关键：礼貌词只剥离，不参与 smalltalk 加分。

对中文原 query，`raw_text` 和 `pivot_text` 可以相同；对外语 query，后续所有规则字段都从 `pivot_text` 派生。

## Intent Policy

每个 intent 的规则由四类元素组成：

- `direct_phrases`：高置信短语，但仍需检查 deny / conflict
- `required`：直达必要条件
- `deny_if`：禁止直达条件
- `conflict_if`：需要进入冲突裁决或 fallback 的条件

关键词不是直接等价于 intent。比如 `你好` 只是 `politeness_prefix`，不是 smalltalk 证据。

## 句式结构层

当前规则不能只停留在关键词判断。测试里的错误主要集中在“关键词不足以表达意图”的句式上，因此应在分词后增加轻量 pattern / slot 层：

| intent | 必要句式/槽位 |
|---|---|
| `live_info` | `景点 + 今天/现在 + 能进/能进去/还能去/开放/闭馆/预约/买票` |
| `weather_info` | `地点? + 天气/下雨/温度/冷不冷/热不热/要不要带伞`；`适合去吗` 默认 fallback，除非同时有天气词 |
| `navigation_text` | `从A到B`、`A到B怎么走`、`去/到 + 景点 + 怎么走`、`附近交通怎么走` |
| `trip_assistant` | `下一站/当前站/现在到哪/还剩几站/路线走到哪里` |
| `manual_route_edit_redirect` | `不要去X了`、`把X去掉/提前/放到最后/换成Y` |
| `translation` | `翻译/译成/怎么说 + 引号文本/冒号后文本/这句话/给工作人员看` |

边界词不能早于槽位抽取直接拒绝。例如 `交通` 本身可能是 out-of-scope 边界，但 `故宫附近交通怎么走` 有明确路线问法，应进入 `navigation_text` 或 fallback，而不是直接拒绝。

## 多意图处理

多意图处理分两步：

1. 先抽证据，不立即选 intent
2. 再按冲突策略裁决

### smalltalk vs task

任务意图优先。

```text
你好 -> smalltalk
你好，请问故宫有什么历史 -> attraction_explain
hello, how do I get to Forbidden City -> navigation_text
谢谢，下一站去哪 -> trip_assistant
```

规则：

- 去掉礼貌词后内容为空，才允许 smalltalk 直达
- 去掉礼貌词后仍有景点、路线、翻译、天气、开放、行程等任务证据，smalltalk 不参与竞争

### live_info vs attraction_explain

```text
故宫今天开放吗 -> live_info
故宫有什么历史 -> attraction_explain
故宫今天有什么历史活动 -> fallback
```

规则：

- `same_day_time + live_operation + attraction_entity` 直达 `live_info`
- `attraction_entity + explain_action` 且没有 live operation，直达 `attraction_explain`
- 两边强证据同时存在，fallback

### weather_info vs live_info

```text
北京今天会下雨吗 -> weather_info
故宫今天开放吗 -> live_info
今天故宫适合去吗 -> fallback
```

规则：

- 有天气词：下雨、温度、天气、预报，优先 `weather_info`
- 有运营词：开放、闭馆、预约、门票，优先 `live_info`
- “适合去吗”这类含糊表达，fallback

### navigation_text vs trip_assistant

```text
从天安门怎么走到故宫 -> navigation_text
下一站去哪 -> trip_assistant
下一站怎么走 -> navigation_text
```

规则：

- 有明确路线动作和 route slot，直达 `navigation_text`
- 问当前站/下一站状态，直达 `trip_assistant`
- 下一站 + 走法/怎么走，属于 `navigation_text`
- 否定导航采用“否定操作词 + 导航目标词”的组合匹配，不维护 `别导航/不用导航/先别导航` 这类合成短语；例如 `别/不要/不用/不是问` 与 `导航/文字导航` 在短窗口内共现时，压低 `navigation_text`

### trip_assistant vs manual_route_edit_redirect

```text
下一站去哪 -> trip_assistant
把景山去掉 -> manual_route_edit_redirect
路线轻松一点 -> fallback
别改路线，下一站去哪 -> trip_assistant
```

规则：

- `route_edit_action + route_edit_object` 直达 `manual_route_edit_redirect`
- route edit negation 直接压低 edit 意图
- 只有“轻松一点/近一点/顺一点”但没有明确改动动作，fallback 或 trip advice

### translation vs attraction_explain

```text
帮我把“Where is the restroom?”翻给工作人员看 -> translation
用中文介绍一下故宫 -> attraction_explain
翻译介绍故宫 -> fallback
```

规则：

- 翻译动作 + quoted text / explicit text，直达 `translation`
- 景点实体 + 讲解动作，无待翻译文本，直达 `attraction_explain`
- 翻译动作和景点讲解动作混在一起且无明确文本，fallback

## Direct Pass 标准

建议每个 intent 必须满足：

- 必要条件满足
- 没有 deny condition
- 没有 unresolved conflict
- top score >= intent threshold
- margin >= intent margin

推荐初始阈值：

| intent | min_score | min_margin |
|---|---:|---:|
| smalltalk | 0.90 | 0.50 |
| translation | 0.70 | 0.20 |
| live_info | 0.65 | 0.20 |
| weather_info | 0.60 | 0.18 |
| navigation_text | 0.65 | 0.20 |
| trip_assistant | 0.60 | 0.18 |
| manual_route_edit_redirect | 0.65 | 0.20 |
| attraction_explain | 0.60 | 0.18 |
| out_of_scope | 0.75 | 0.25 |

`out_of_scope` 阈值应更高，避免过度拒绝旅游相关 query。

## Fallback 输入

规则不直达时，fallback 模型应看到规则证据：

```json
{
  "raw_query": "...",
  "pivot_query": "...",
  "content_text": "...",
  "entities": {},
  "slots": {},
  "candidates": [
    {"intent": "live_info", "evidence": ["same_day_time", "live_operation"]},
    {"intent": "attraction_explain", "evidence": ["attraction_entity"]}
  ],
  "conflict_reason": "live_vs_attraction_conflict"
}
```

Fallback 的职责是裁决，不是重新做开放式问答。

## 维护规则

- 新增关键词必须带至少一个正例和一个负例。
- 不能因为一个关键词直接新增 direct pass；必须写 required / deny / conflict。
- 小语种和英文 query 不单独堆规则，必须先走中文 pivot 后共享中文规则。
- 路由规则 benchmark 应测试两类输入：中文原文直路由、外语原文经过 translator pivot 后路由；不再用 raw 外语直接评估中文规则命中率。
- 每次规则调整后跑 routing benchmark，并看 confusion matrix。

## 推荐测试集

重点维护 hard negative：

- `你好，请问故宫有什么历史` -> `attraction_explain`
- `你好，今天故宫开放吗` -> `live_info`
- `hello, how do I get to Forbidden City` -> `navigation_text`
- `谢谢，下一站去哪` -> `trip_assistant`
- `今天故宫有什么历史活动` -> fallback
- `今天故宫适合去吗` -> fallback
- `下一站怎么走` -> `navigation_text`
- `下一站去哪` -> `trip_assistant`
- `把景山去掉` -> `manual_route_edit_redirect`
- `别改路线，下一站去哪` -> `trip_assistant`
- `帮我把“Where is the restroom?”翻给工作人员看` -> `translation`
- `翻译介绍故宫` -> fallback
- `现在故宫排队多久` -> `out_of_scope` boundary
