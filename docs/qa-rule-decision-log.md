# QA Rule Decision Log

这份文档集中记录近期 QA 规则讨论的结论。写法保持简单：每条只保留问题、解决方式和维护位置，后续改规则时优先追加这里，再更新对应设计文档或测试集。

## 维护原则

- 每次规则变更必须说明原问题，不只记录“加了什么词”。
- 能确定的高精度规则放主链路；不确定、歧义或低置信问题交给 fallback 模型。
- 规则改动必须同步补正例、负例和冲突例。
- README 只放入口，细节放本文件和对应专题文档。

## 决策记录

| 规则编号 | 问题 | 解决方式 | 维护位置 |
|---|---|---|---|
| QA-RULE-001 | 外语、东南亚语种如果各自维护关键词，会导致词库膨胀，也会让 `hello/hi` 等礼貌词干扰 smalltalk。 | 所有非中文 query 先翻成中文 canonical query，再进入同一套中文规则和 fallback 流程。 | `docs/routing-model-selection-plan.md`、`docs/qa-intent-routing-rule-design.md` |
| QA-RULE-002 | `你好，请问故宫有什么历史` 这类句子可能因为“你好”误路由到寒暄。 | 礼貌前缀只作为弱信号；只要有明确任务主体、景点实体或任务句式，任务意图优先于 smalltalk。 | `src/yoyo/modules/qa/intent_router.py`、`docs/qa-intent-keyword-library.yaml` |
| QA-RULE-003 | 单纯关键词直达容易误路由，多意图句子尤其明显。 | 规则层只做高置信 direct pass；低置信、冲突或未覆盖句式进入 fallback 模型。 | `docs/qa-intent-routing-rule-design.md`、`docs/qa-intent-rule-maintenance.md` |
| QA-RULE-004 | 多意图 query 可能在翻译、实时信息、讲解、路线调整、导航之间冲突。 | 按冲突策略裁决：显式翻译优先；实时开放/预约/公告优先 live_info；明确改路线优先 route_edit；明确点到点怎么走优先 navigation_text；仅问下一步安排才归 trip_assistant。 | `docs/qa-intent-routing-rule-design.md`、`src/yoyo/modules/qa/intent_router.py` |
| QA-RULE-005 | 规则库如果只堆关键词，会不可解释、不可回归。 | 按 intent 维护关键词、必要条件、禁止条件、句式结构、冲突策略；新增规则必须配 benchmark case。 | `docs/qa-intent-keyword-library.yaml`、`evals/datasets/routing_rule_all_800_cases.yaml` |
| QA-RULE-006 | `live_info` 多次问同一景点同一类今日信息时，外部搜索重复、时延高。 | 加 Redis 短缓存，key 使用 `{date, attraction, info_type}`；结果、闭馆公告、provider 失败分别设置 TTL，并在 metadata 暴露 cache hit。 | `docs/qa-live-info-cache.md`、`src/yoyo/modules/qa/live_info_cache.py` |
| QA-RULE-007 | 导航请求里 `下一站怎么去`、`到X怎么走`、`从A到B` 的起点来源不同，不能混在一起。 | 导航槽位分为 next_stop、destination_only、explicit_route、multi_leg；destination-only/next-stop 优先 GPS，再 current_stop；explicit_route 保留用户显式起点。 | `docs/navigation-slot-routing-design.md`、`src/yoyo/modules/knowledge/hybrid_context_builder.py` |
| QA-RULE-008 | `从A到B再到C` 这类多段导航，高德文字导航接口按单起点/单终点查询，不能把后三个地点塞成一个目的地。 | 抽取为有序 destinations，下游拆成 A->B、B->C、C->D 多次调用，再聚合成一个答案。 | `src/yoyo/modules/knowledge/navigation_retriever.py`、`tests/test_navigation_slot_extraction.py` |
| QA-RULE-009 | `天坛` 等短名/同名地点可能被高德自由 geocode 解析到北京以外。 | 先走北京地点注册表和坐标直传；未注册地点才 geocode，并校验北京 adcode/province/city。 | `src/yoyo/modules/knowledge/place_resolver.py`、`docs/navigation-slot-routing-design.md` |
| QA-RULE-010 | `别导航，下一站去哪` 不能把“下一站”误判成导航；但 `别改路线，从A到B怎么走` 仍应是导航。 | 否定词和对象词分开维护：`NEGATION_OPERATOR_KEYWORDS` + `NAVIGATION_NEGATION_TARGET_KEYWORDS`；短窗口组合判断，只把“导航/文字导航”作为导航否定对象。 | `src/yoyo/modules/qa/intent_router.py`、`src/yoyo/modules/qa/rule_assets.py` |
| QA-RULE-011 | 用户明确说步行、打车、地铁时，不能再被系统默认方式覆盖。 | 导航 mode 增加 `mode_source`；显式方式优先，支持 `walking/driving/transit`。 | `src/yoyo/modules/qa/schemas.py`、`src/yoyo/modules/knowledge/schemas.py` |
| QA-RULE-012 | 用户未指定出行方式时，长距离景点间默认步行体验差。 | 槽位 hydration 后用连续路段最大直线距离判断：超过 3km 默认公共交通，否则默认步行。 | `src/yoyo/modules/knowledge/hybrid_context_builder.py`、`tests/test_navigation_slot_extraction.py` |
| QA-RULE-013 | 用真实路线距离判断默认方式会额外调用高德，增加一个查询环节，也会先遇到“还没决定 mode”的循环依赖。 | 默认方式只用已解析坐标的直线距离判断；真实路线距离只在 mode 决定后由高德查询。 | `docs/navigation-slot-routing-design.md` |
| QA-RULE-014 | 地铁/公交问法以前被当作不支持边界拒答。 | 公共交通已纳入 `navigation_text`，调用高德 `/v3/direction/transit/integrated`；traffic/crowd/parking/air-quality 等仍按边界维护。 | `src/yoyo/modules/integrations/amap/client.py`、`evals/datasets/navigation_slot_100_cases.json` |
| QA-RULE-015 | 只看总体 pass/fail 不方便人工检查槽位、mode 和中间结果。 | benchmark 明细导出 query、intent、origin、destinations、place_id、mode、mode_source、slot_debug 和 Excel。 | `evals/run_navigation_benchmark.py`、`docs/navigation-slot-benchmark-2026-05-15.md` |
| QA-RULE-016 | 真实高德 benchmark 连续请求时，瞬时 provider/network 抖动会污染高德返回准确性指标。 | Amap 请求层加 3 次轻量重试；真实 benchmark 支持 `--case-delay-ms`，并导出 intent/slot/amap/total 时延和高德距离/耗时/腿数/步数。 | `src/yoyo/modules/integrations/amap/client.py`、`evals/run_navigation_benchmark.py`、`docs/navigation-hard-300-amap-benchmark-2026-05-15.md` |
| QA-RULE-017 | 3km 内显式公交/地铁请求可能没有合适公共交通方案，直接把 provider 空结果返回给用户会显得失败。 | 若请求 mode 为 `transit` 且路线 provider 返回 `empty_navigation_payload`，主链路自动重查 `walking`，最终回答使用“当前没有合适的公共交通，返回给你步行方案。”，不暴露 provider 名称；benchmark 导出 `amap_final_answer`、`amap_final_mode` 和 fallback 标记。 | `src/yoyo/modules/knowledge/navigation_retriever.py`、`src/yoyo/modules/qa/formatters.py`、`evals/run_navigation_benchmark.py` |
| QA-RULE-018 | 公交/地铁路线的前置“步行到站”可能有很多细分步骤，最终回复只截前三步会让公交 case 看起来像全程步行。 | 公共交通最终回复必须保留关键乘车步骤；如果 transit payload 中完全没有乘车步骤，则按无合适公共交通处理并走步行兜底。多段路线增加路线总览和每段距离/耗时。 | `src/yoyo/modules/integrations/amap/client.py`、`src/yoyo/modules/qa/formatters.py`、`tests/test_navigation_slot_extraction.py` |
| QA-RULE-019 | `transit` 只作为公共交通大类不够，用户明确说“公交”时不能返回地铁，明确说“地铁”时也不能退成纯公交，否则表格 pass 但产品体验错。 | 导航槽位新增 `transit_preference=bus/subway/public_transport`；公交请求高德公交规划使用不乘地铁策略并过滤含地铁方案，地铁请求优先选择含地铁方案，公共交通请求允许公交/地铁/混合。最终回复按实际乘车类型显示“公交 / 地铁 / 公交+地铁”，benchmark 导出请求偏好、最终车辆类型和偏好满足标记。 | `src/yoyo/modules/knowledge/hybrid_context_builder.py`、`src/yoyo/modules/integrations/amap/client.py`、`src/yoyo/modules/knowledge/navigation_retriever.py`、`src/yoyo/modules/qa/formatters.py`、`evals/run_navigation_benchmark.py` |
| QA-RULE-020 | 公交线路名里可能包含地铁站名，例如 `332路(前门--地铁北宫门站)`；如果直接扫整条线路名，会把普通公交误判成地铁。 | 车辆类型识别优先使用高德 `busline.type`；只有缺少 type 时，才看括号前的线路主体名，不扫描括号内起终点站名。subway 偏好不能因为公交终点站名带“地铁”而误通过。 | `src/yoyo/modules/integrations/amap/client.py`、`tests/test_amap_navigation_client.py` |
| QA-RULE-021 | SQL 与 RAG 的边界如果只靠“历史/讲解”关键词，会让 SQL 已经有的景点基础介绍也触发 RAG，造成链路重叠和额外时延。 | 景点问答先查 SQL：基础介绍、位置、开放/实用提示、适合人群等 SQL 已覆盖字段保持 `sql_only`；只有用户问到中轴线、象征意义、建筑秩序、深层历史/策展等 SQL 未覆盖深问时才触发 RAG。若是北京景点但当前 mock SQL/RAG 都没有记录，可走模型常识回答并标记 `model_knowledge`，后续真实数据补齐后再回收。 | `src/yoyo/modules/knowledge/fallback_router.py`、`src/yoyo/modules/qa/prompts.py`、`src/yoyo/modules/qa/orchestrator.py`、`tests/test_rag_query.py`、`tests/test_qa.py` |
| QA-RULE-022 | `第一次用这个导游`、`你会怎么回答问题`、`能力边界` 等能力说明问法会被 fallback 漂到 `out_of_scope` 或 `trip_assistant`。 | 能力说明、打招呼、身份/能力边界类短语归入 smalltalk/capability；高置信 capability query 规则直达，不再让 fallback 覆盖成其他业务意图。 | `src/yoyo/modules/qa/intent_router.py`、`src/yoyo/modules/qa/rule_assets.py`、`tests/test_qa_routing_regressions.py` |
| QA-RULE-023 | `不要把它误当成改路线`、`不用操作行程`、`不要删除任何景点` 这类元否定会因为包含“改路线/删除/行程”而误触发 `manual_route_edit_redirect`。 | 将 route-edit 否定表达和元指令加入否定库；当 query 已明确是下一步安排且含 route-edit 否定时，保持 `trip_assistant`，不交给 fallback 覆盖成改路线。 | `src/yoyo/modules/qa/intent_router.py`、`src/yoyo/modules/qa/rule_assets.py`、`tests/test_qa_routing_regressions.py` |
| QA-RULE-024 | 外语预处理可能丢失 raw query 中的硬拒绝信号，例如越南语包裹的 `Python 爬虫` 被翻译成泛化中文后误进 live_info。 | domain guard 使用 `effective_query + raw_query + pivot_query` 合并文本做边界判断，保留原始 query 的 `python/爬虫/抓取` 等硬拒绝信号。 | `src/yoyo/modules/qa/orchestrator.py`、`src/yoyo/modules/qa/domain_guard.py`、`tests/test_qa_routing_regressions.py` |
| QA-RULE-025 | `帮我订票/直接付款/代买/下单` 属于交易执行，不应因为含“票/今晚”进入 `live_info`。 | 新增 `transaction_boundary`：代订、付款、支付、下单、演出票等归 `out_of_scope`；live_info 只处理开放、预约、门票信息查询，不执行交易。 | `src/yoyo/modules/qa/rule_assets.py`、`src/yoyo/modules/qa/intent_router.py`、`tests/test_qa_routing_regressions.py` |
| QA-RULE-026 | 步行导航只展示高德 raw instruction 或前 5 个 step 时，用户看不到每次转向发生在什么路口/地点，也容易出现“后续按现场导航”的不可执行回复。 | 步行 route 保留 `orientation/polyline/end_location`，对每个 step 终点批量逆地理，最终按“沿路名/方向步行约 N 米，到节点附近，转向”展示；纯步行路线不再硬截前 5 步。 | `src/yoyo/modules/integrations/amap/client.py`、`src/yoyo/modules/qa/formatters.py`、`tests/test_navigation_slot_extraction.py` |
| QA-RULE-027 | `正阳门`、`国家博物馆`、`水立方` 等简称/同名 POI 交给高德自由 geocode 可能误解析或失败，导致路线目标错或不可用。 | 扩充北京导航地点库，Amap client 在无显式 GPS 时也先用本地注册坐标，只有未注册地点才 geocode；本轮补充中国国家博物馆、孔庙和国子监、鸟巢、水立方、798、将台、北京动物园、五塔寺。 | `src/yoyo/modules/knowledge/place_resolver.py`、`src/yoyo/modules/integrations/amap/client.py`、`tests/test_amap_navigation_client.py`、`evals/run_navigation_turnpoint_smoke.py` |
| QA-RULE-028 | 白名单扩展如果直接信任高德 geocode，会把短名/泛名景点解析到错误商业楼、住宅或同名 POI；但完全不扩库又会让大量旅游网景点继续走低置信 geocode。 | 白名单生成采用高德 POI 文本检索优先、带地址 geocode 兜底、商业类型降权、近分候选进入澄清/审核；本轮从北京旅游网 CSV 纳入 127 个高置信景区，23 个低置信或歧义项不入库。高置信旅游 POI 直达，商业/地址歧义和未注册多候选进入用户澄清；最近一轮 assistant clarification 支持用户回复“第1个/选第一个/候选名称”后继续路线规划。 | `evals/build_navigation_place_registry.py`、`src/yoyo/modules/knowledge/place_resolver.py`、`src/yoyo/modules/knowledge/navigation_retriever.py`、`src/yoyo/modules/qa/orchestrator.py`、`tests/test_navigation_place_registry.py`、`tests/test_navigation_slot_extraction.py`、`docs/navigation-slot-routing-design.md` |
| QA-RULE-029 | 地点澄清后，用户可能说“选上面的/下面的/中间的”，也可能在只有 2 个候选时说“选第三个”；如果交给 LLM 猜，会有错误坐标风险。 | 澄清续接先用确定性选择规则：上面=第 1 个，下面/最后=最后一个，奇数候选中间=正中，偶数候选中间和编号越界继续澄清；LLM 不直接决定坐标。 | `src/yoyo/modules/qa/orchestrator.py`、`src/yoyo/modules/knowledge/hybrid_context_builder.py`、`src/yoyo/modules/knowledge/navigation_retriever.py`、`tests/test_navigation_slot_extraction.py` |
| QA-RULE-030 | 仍会有少量澄清回复规则解析不到，例如用户夹杂闲聊后说“我说的是吃饭那个”，同时用户也可能在同一轮切换到天气/景点讲解等新意图。 | 复用当前 router fallback 模型配置，但动态注入结构化 `pending_clarification`；fallback 同时判断真实 intent 与候选选择动作，只能返回候选编号，不能编坐标。若是新意图则 `not_a_selection` 并正常路由；若低置信、越界或需要继续确认，则最终回复层继续澄清。 | `src/yoyo/modules/qa/router_fallback.py`、`src/yoyo/modules/qa/orchestrator.py`、`src/yoyo/modules/knowledge/navigation_retriever.py`、`tests/test_navigation_slot_extraction.py` |
| QA-RULE-031 | 澄清能力如果按每个 intent 重复写一套完整模型链路，会增加配置和维护成本；如果用一个泛化大 prompt 统一做，又容易让天气地点、导航地点、翻译语言等 schema 互相污染。 | 架构收口为“每个 intent 单独 typed clarification state + intent-specific 规则澄清 + 共用 fallback 模型配置”。fallback prompt 按 pending clarification 类型动态注入，只能选择/补全该 state 允许字段；通用层只判断是否回应澄清或切换新意图。 | `docs/navigation-slot-routing-design.md`、后续 `src/yoyo/modules/qa/orchestrator.py` / clarification resolver 抽象 |

## 后续追加格式

新规则按下面格式追加到表格：

```text
| QA-RULE-XXX | 问题 | 解决方式 | 维护位置 |
```

如果是 bug 修复，还要同步在 `docs/dev-retrospective.md` 追加 problem / cause / improvement。
