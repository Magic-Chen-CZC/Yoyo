# Navigation Slot Routing Design

这份文档记录 QA `navigation_text` 意图下的槽位提取、地点解析、高德调用和后续维护规则。

## 目标

导航链路只解决“怎么走 / 怎么去 / 文字路线 / 路线步骤”问题，支持步行、驾车和公共交通文字路线；不负责路线编辑、不回答实时路况/拥挤度/停车位，也不替代 `trip_assistant` 做行程策略判断。

核心原则：

- 规则优先处理稳定句式。
- fallback 模型只补结构歧义，不最终决定地点。
- 地点解析必须经过北京景点库 / 北京范围校验，避免同名地点漂到外地。
- GPS / current stop / explicit origin 的优先级必须清楚。

## 主链路

```text
query
-> intent_router 判定 navigation_text
-> _resolve_navigation_slots(...)
   -> 规则槽位提取
   -> 规则 miss 时调用 resolve_navigation_slot_fallback(...)
   -> _hydrate_navigation_slots(...) 统一补 GPS/current_stop/地点解析
-> NavigationSlotPayload
-> get_navigation_context(...)
   -> 单段调用 AmapRouteClient.get_text_navigation(...)
   -> multi_leg 按 origin -> dest1 -> dest2... 多段调用并聚合
   -> transit 空结果时按步行重查并聚合最终回答
```

## 四类核心请求

| 类型 | 示例 | request_kind | origin 来源 | destination 来源 |
|---|---|---|---|---|
| 下一站 | `下一站怎么去` | `next_stop` | 优先 GPS，其次 `current_stop_name` | `next_stop_name` |
| 目的地型 | `到故宫怎么走` | `destination_only` | 优先 GPS，其次 `current_stop_name` | query 中的目的地 |
| 显式起终点 | `从天安门到故宫怎么走` | `explicit_route` | query 显式起点 | query 显式终点 |
| 多段 | `从天安门到故宫再到景山怎么走` | `multi_leg` | query 显式起点，若是 `从这里` 则用 GPS/current stop | 按表达顺序拆多个目的地 |

## 出行方式槽位

`NavigationSlotResult` / `NavigationSlotPayload` 现在维护：

- `mode`: `walking` / `driving` / `transit`
- `mode_source`: `explicit` / `distance_default` / `config_default` / `fallback`
- `transit_preference`: `bus` / `subway` / `public_transport` / `null`

规则：

- 用户明确说 `步行/走路/走过去`，mode 固定为 `walking`。
- 用户明确说 `开车/驾车/自驾/打车`，mode 固定为 `driving`。
- 用户明确说 `公交/公交车/坐公交`，mode 固定为 `transit`，`transit_preference=bus`。
- 用户明确说 `地铁/坐地铁/几号线`，mode 固定为 `transit`，`transit_preference=subway`。
- 用户只说 `公共交通/换乘/坐车`，mode 固定为 `transit`，`transit_preference=public_transport`。
- 显式方式优先，不被距离默认策略覆盖。
- 未指定方式时，先完成 origin/destination hydration，按连续路段的最大直线距离判断：单段超过 3000 米默认 `transit`，否则默认 `walking`。
- 如果缺少可用坐标，保守回退 `config_default`，当前默认仍是 `walking`。

这里刻意使用直线距离而不先查真实路线距离。真实路线距离需要先调用一次高德路线规划；但 mode 选择本身又决定调用 walking / driving / transit 哪个 endpoint。为避免多一次外部查询和循环依赖，默认策略只用已解析坐标做快速判定。

## 规则与 fallback 分工

规则负责：

- `下一站怎么去 / 下一站怎么走 / 接下来怎么去 / 接下来怎么走`
- `去X怎么走 / 到X怎么去 / 导航到X / 我想去X`
- `想去X怎么走 / 等会去X怎么走 / 接着去X怎么走 / 下面到X怎么去`
- `从A到B / 从A怎么走到B / 从A前往B`
- `从A到B再到C / 去A再去B`
- `分段路线 / 分段说 / 文字步骤`
- 出行方式抽取：步行 / 驾车 / 公交地铁
- 常见北京景点别名归一化
- GPS origin 和 current stop origin 的确定性补全

fallback 模型负责：

- 规则没有覆盖的口语结构
- 复杂语序或翻译 pivot 后的非标准表达
- 判断 `unknown`，避免把改路线、删点、换点、重排误抽成导航槽位

fallback 不负责：

- 决定同名地点属于哪个城市
- 擅自补不存在的地点
- 覆盖用户显式 origin/destination

## 地点解析

地点解析入口是 `src/yoyo/modules/knowledge/place_resolver.py`。

需要维护的核心库：

- `REGISTERED_NAVIGATION_PLACES`
  - `place_id`
  - canonical `name`
  - 中文 `display_name`
  - aliases
  - latitude / longitude
  - Beijing adcode
- `CURRENT_LOCATION_REFERENCES`
  - `这里`
  - `这儿`
  - `当前位置`
  - `我这里`
  - `我这儿`

`当前站 / 当前站点 / 现在这个站` 不等同于 GPS，它表示“按当前行程站点作为起点”，应回填 `session_context.current_stop_name`。只有 `这里 / 我这儿 / 当前位置 / 当前定位` 这类定位词才优先使用 `session_context.current_position`。

显式路线解析采用右侧 `从` 候选优先。这样 `我从故宫出来以后有点分不清方向，现在按手机定位算，从这里到景山怎么走` 会使用后半句 `从这里到景山`，不会把前置叙述里的 `从故宫出来` 误当路线起点。

新增景点时必须补：

1. 中文名、英文名和常见别名。
2. 北京坐标。
3. 北京 adcode。
4. 至少 1 条 destination-only case。
5. 如果是同名风险地点，至少 1 条 disambiguation case。

当前已注册重点景点：

- 天安门广场
- 故宫
- 景山公园
- 天坛 / 祈年殿
- 颐和园
- 圆明园
- 北海公园
- 什刹海 / 后海
- 南锣鼓巷
- 雍和宫
- 恭王府
- 正阳门 / 前门
- 中国国家博物馆 / 国家博物馆 / 国博
- 孔庙和国子监博物馆 / 孔庙 / 国子监
- 鸟巢 / 国家体育场
- 水立方 / 国家游泳中心
- 798艺术区
- 将台地铁站
- 北京动物园
- 五塔寺 / 北京石刻艺术博物馆

当前注册规模：

- 手工核心库：20 个，维护在 `src/yoyo/modules/knowledge/place_resolver.py` 的 `CORE_NAVIGATION_PLACES`。
- 北京旅游网生成库：127 个，维护在 `src/yoyo/modules/knowledge/navigation_place_registry_generated.py`。
- 主链路总注册数：147 个，`REGISTERED_NAVIGATION_PLACES = CORE + VISITBEIJING`。
- 生成来源：`/Users/czc/Downloads/北京旅游网_修复版景区列表(2).csv`。
- 生成脚本：`evals/build_navigation_place_registry.py`。
- 审核结果：`evals/results/navigation_place_registry_geocode_20260516.json`，其中 23 个低置信 / 歧义项未进入主白名单。

## 地点置信度与澄清策略

导航地点解析按“能安全直达就直达，不安全就澄清”的原则处理。

高置信旅游 POI：不澄清，直接导航。

- 典型来源：手工核心库精确别名命中、北京旅游网生成库精确名称命中、SQL mock 景点已注册坐标命中。
- 当前置信度：核心库精确命中 `1.0`；已知景点别名 `0.98`；mock 已注册景点 `0.95`；注册别名子串命中 `0.94`。
- 示例：`去正阳门`、`前门城楼怎么走` 在北京导游产品上下文里默认指向核心景点 `zhengyangmen`。

中置信但仍可直达：通常是生成库精确名称，且生成脚本已经确认北京 adcode、名称/地址匹配和 provider 类型不是明显商业类。

- 生成库入库门槛：高德 POI 文本候选分数 `>=70` 且没有近分歧义候选；或带原始地址的 geocode 分数 `>=76`。
- 生成库不自动生成简称 alias，只接受 CSV 景区全名，避免 `史家胡同` 误命中 `史家胡同博物馆` 这类过度泛化。

低置信或商业/地址歧义：澄清，不硬套景点坐标。

- 触发信号：餐厅、咖啡、酒店、商场、写字楼、公司、门店、分店、大厦、金融中心、楼宇、附近那个、地址、几号楼等商业或地址语义。
- provider 类型如果是 `餐饮服务`、`购物服务`、`商务住宅`、`公司企业`、`金融保险服务`，降低置信度。
- 示例：`去正阳门餐厅`、`正阳门北京环球金融中心`、`附近那个正阳门` 不应该直接套核心景点坐标。

未注册地点 + 高德返回多个同名候选：澄清。

- 如果最佳候选和第二候选都在北京，第二候选分数 `>=62` 且分差 `<=8`，判为 `ambiguous_close_candidates`。
- 如果只有低分 POI 或弱 geocode，判为 `needs_review` / `geocode_candidate`，不进入注册库。
- 澄清回复形态：
  `我找到几个“正阳门”相关地点：1. 正阳门，东城区，景点/城楼；2. 正阳门(北京环球金融中心)，朝阳区，楼宇/商户；3. 正阳门某餐饮店，某区。你要去哪个？`

当前实现状态：

- 已实现：高置信注册地点直达；低置信北京旅游网候选不入主白名单；未注册地点保留为 `geocode_candidate`，置信度 `0.45`。
- 已实现：商业/地址歧义词命中时，即使文本里包含核心景点 alias，也不做子串直达。例如 `正阳门餐厅` 不再直接命中核心景点 `zhengyangmen`，而是进入 `registered_alias_with_ambiguity_signal`。
- 已实现：`get_navigation_context(...)` 在路线规划前检查低置信地点；如果命中商业/地址歧义，或高德 POI 候选存在多个同名/近似候选，返回 `NavigationContext.status=clarification` 和 `clarification.candidates`，不发起 direction 查询。
- 已实现：QA formatter 会把候选展示给用户，并提示可回复 `第1个 / 选第一个`。
- 已实现：QA orchestrator 会读取最近一轮 assistant 的 `metadata.navigation.clarification`；如果用户下一句是 `选第一个 / 第2个 / 候选名称`，直接判为 `navigation_text`，把选中的候选坐标回填到原 slot，再继续正常路线规划。
- 第一层已实现：澄清续接不让 LLM 猜坐标，先用确定性规则归一化用户选择：
  - `上面的 / 最上面 / 选上面的` -> 第 1 个候选。
  - `下面的 / 最下面 / 最后一个` -> 最后 1 个候选。
  - `中间的` 在奇数候选时选正中间；偶数候选时继续澄清，因为中间有两个。
  - 编号越界时继续澄清，例如只有 2 个候选但用户说 `选第三个`，回复“当前只有 2 个候选，没有第 3 个。请重新选择候选编号。”
  - 如果用户直接说候选名称或地址片段，则按候选名匹配。
- 第二层已实现：规则未命中但存在 pending clarification 时，复用当前 router fallback 模型配置，向 fallback prompt 动态注入结构化 `pending_clarification`。fallback 仍先判断用户最新句子的真实 intent；如果用户切换到天气、开放信息、景点讲解、翻译等新任务，则输出新 intent 和 `clarification_action=not_a_selection`，不会强行继续导航。
- 第二层输出只允许在候选内选择：`clarification_action=selected/needs_clarification/not_a_selection`，`selected_index` 必须指向已有候选；置信度低于 `0.75`、编号越界或模型返回 `needs_clarification` 时，都进入第三层继续澄清。
- 第三层已实现：最终回复层根据 `NavigationContext.status=clarification` 输出可执行澄清话术，不调用路线规划，不让 LLM 生成坐标或路线。越界、偶数中间、低置信 fallback 都会返回“请重新选择候选编号或完整地点名称”。

## 通用澄清架构原则

导航地点澄清是第一版 typed clarification state。后续其他 intent 如果需要澄清，不应把所有逻辑塞进一个通用大 prompt，而应保持：

```text
intent router
-> detect pending_clarification
-> clarification resolver
   -> 通用选择语义：第几个 / 上面 / 下面 / 名称匹配 / 是否换话题
   -> intent-specific rules：每个 intent 自己解释可选对象和槽位
   -> shared fallback runtime：复用当前 fallback 模型配置，但按 clarification 类型动态注入 prompt
-> selected：回到对应 intent handler
-> switched_intent：按新 intent 走主链路
-> unclear：继续澄清
```

分工：

- 每个 intent 维护自己的 typed clarification state 和规则澄清。
- fallback 模型配置可以共用当前 router fallback runtime，不需要每个 intent 单独配模型。
- fallback prompt 不能共用一个泛化大 prompt，必须按 clarification 类型动态注入结构化 pending state。
- 模型只允许选择或补全当前 pending state 允许的字段，不能直接编业务结果、坐标、天气或路线。

当前建议的 typed state：

| intent | typed clarification state | 规则优先处理 |
|---|---|---|
| `navigation_text` | 地点候选、原始 slot、候选坐标、起终点、出行方式 | 第几个、上/中/下、候选名称、起点/终点、步行/公交/地铁 |
| `weather_info` | 天气地点候选、日期范围 | 今天/明天/后天、哪个景点、哪个城市 |
| `live_info` | 景点候选、信息类型 | 开放、预约、门票、临时公告 |
| `translation` | 待翻译文本、source/target language | 引号文本、翻成中文、给工作人员看 |
| `trip_assistant` | 当前行程上下文、偏好选择 | 轻松点、多逛点、下一站、当前站 |
| `manual_route_edit_redirect` | 修改动作、目标站点、替换候选 | 删除哪个、换成哪个、重排哪一段 |

这个架构的边界是：通用层只负责“用户是否在回应上一轮澄清”和“是否切换新意图”；业务层负责解释候选含义和执行。这样能避免天气地点、导航地点、翻译语言等 schema 互相污染。

歧义关键词维护：

- 维护位置：`src/yoyo/modules/knowledge/place_resolver.py` 的 `PLACE_AMBIGUITY_KEYWORDS`。
- 当前按类别维护：`commercial`、`lodging`、`building_address`、`nearby_reference`、`facility`。
- 新增关键词必须配套正负例：
  - 正例：`正阳门餐厅怎么走` 应澄清。
  - 正例：`正阳门北京环球金融中心怎么走` 应澄清。
  - 负例：`正阳门怎么走` 应直达核心景点。
  - 负例：`国家游泳中心怎么走` 虽含 `中心`，但完整命中注册 alias，仍应直达。
- 不建议把过泛词直接加入歧义库，例如单独的 `门`、`中心`、`街` 很容易误伤真实景点名；需要放入组合词，如 `金融中心`、`购物中心`、`小吃街`。

## 高德调用策略

已知景点和 GPS origin 优先用坐标调用 direction，避免自由 geocode。即使调用方没有传 `origin_place/destination_place`，Amap client 也会先查本地北京导航地点库；只有未注册地点才进入高德 geocode。

注意：当用户只说“从某景点到某景点”且没有 GPS / 门区信息时，注册坐标只能代表一个默认 POI anchor，不等于用户实际所在门口。产品侧有 GPS 时应优先 GPS；没有 GPS 时，最终回复可以在 LLM 润色层提醒“以当前定位/实际出口为准”。

当前 mode 与高德 endpoint 对应关系：

- `walking`: `/v3/direction/walking`
- `driving`: `/v3/direction/driving`
- `transit`: `/v3/direction/transit/integrated`

公共交通细分：

- `bus` 使用 `strategy=5`，也就是不乘地铁模式；同时解析返回结果，拒绝包含地铁乘车段的方案。
- `subway` 使用推荐模式请求后，优先选择包含地铁乘车段的方案；如果同时包含公交接驳，最终回复标为 `公交+地铁`，不只写 `地铁`。
- `public_transport` 接受公交、地铁或公交+地铁混合方案。
- 车辆类型识别优先看高德 `busline.type`。如果没有 type，只看括号前的线路主体名；不要扫括号里的起终点站名，避免把 `332路(前门--地铁北宫门站)` 这类普通公交误判成地铁。
- benchmark 导出 `actual_transit_preference`、`amap_requested_transit_preference`、`amap_final_transit_vehicle_types`、`amap_transit_preference_satisfied`，防止“公交 case 返回地铁”仍被误算 pass。

高德官方 Web 服务路径规划文档说明该 API 提供步行、公交、驾车查询接口；公交规划需要 `origin`、`destination` 和 `city`，当前 city 固定为 `北京`，strategy 默认 `0`（最快捷模式）。官方文档入口：https://lbs.amap.com/api/webservice/guide/api/direction

高德请求层有 3 次轻量重试，用于降低真实 benchmark 或线上偶发 provider/network 抖动。benchmark 跑真实高德时建议加 `--case-delay-ms`，避免把连续压测式请求造成的 provider 失败误判成路线能力问题。

公共交通兜底规则：

- 用户显式要求公交/地铁，或系统按 3km 阈值默认选择 `transit` 时，先查公共交通。
- 如果公共交通返回 `empty_navigation_payload`，说明当前没有合适公共交通方案；主链路会立即用同一组起终点重查 `walking`。
- 如果公共交通 payload 标记为可用但解析后没有任何 `乘车/乘坐` 步骤，也按无合适公共交通处理，避免把纯步行路线误当成公交/地铁方案。
- 对用户的最终话术按偏好细分：公交请求使用 `当前没有合适的公交方案，返回给你步行方案。`；地铁请求使用 `当前没有合适的地铁方案，返回给你步行方案。`；公共交通泛化请求使用 `当前没有合适的公共交通，返回给你步行方案。`
- 最终回答不暴露 provider 名称；内部 metadata 保留 `requested_mode=transit`、`final_mode=walking/mixed`、`mode_fallback_used=true` 和 `mode_fallback_reason=transit_empty_use_walking` 方便排查。
- multi-leg 按腿兜底：哪一段公共交通为空，就只对该段重查步行；整体 `final_mode` 如果混合了 transit 和 walking，则记为 `mixed`。

最终回复格式：

- 多段路线必须显示 `路线总览：A -> B -> C`。
- 每段必须显示出行方式、距离和耗时。
- 公共交通路线不能只截取“步行到站”的前三步；即使乘车步骤排在后面，也要把首个公交/地铁 `乘坐...` 步骤纳入最终回复。
- 纯步行路线保留完整 step，不再固定截前 5 步。
- 步行 step 优先展示结构化文本：`沿{road}{orientation}步行约 {distance} 米，到{turn_location_text}，{action}`。
- `turn_location_text` 来自 step `polyline` 终点的高德逆地理结果，优先级为：路口 `roadinters` -> 近距离 POI -> 近距离道路 -> 门牌/语义描述。
- 如果逆地理或结构化字段不足，才回退到高德原始 `instruction`。

只有未注册地点才进入高德 geocode。geocode 必须：

- 带 `city=北京`。
- 校验返回 `adcode` 前缀为 `110`，或 province/city/formatted_address 明确是北京。
- 非北京结果直接 degraded，不继续 direction。

这条规则用于防止 `天坛` 被解析到广西等外地同名地点。

真实高德检查默认不在 benchmark 里自动执行。需要真实 API 时显式加：

```bash
PYTHONPATH=src .venv/bin/python evals/run_navigation_benchmark.py \
  --dataset evals/datasets/navigation_slot_100_cases.json \
  --output-cases evals/results/navigation_slot_100_amap_cases.json \
  --output-summary evals/results/navigation_slot_100_amap_summary.json \
  --excel-output evals/results/navigation_slot_100_amap_results.xlsx \
  --check-amap
```

## 维护指标

导航专项 benchmark 重点看：

- `intent_correct_rate`
- `slot_correct_rate`
- `pass_rate`
- `actual_origin_place_id`
- `actual_destination_place_ids`
- `origin_place_source`
- `destination_place_sources`
- `actual_mode`
- `actual_mode_source`
- `amap_checked_cases`
- `amap_reasonable_cases`
- `amap_final_answer`
- `amap_final_mode`
- `amap_mode_fallback_used`
- `amap_mode_fallback_reason`
- `actual_transit_preference`
- `amap_requested_transit_preference`
- `amap_final_transit_vehicle_types`
- `amap_transit_preference_satisfied`
- `turn_location_hit_count`（步行 turn point smoke 结果中统计）

规则改动验收：

- `navigation_slot_100_cases.json` 必须保持 `pass_rate=1.0`，除非有明确产品口径调整。
- 旧 `navigation_hard_cases_v1.json` 必须保持 `pass_rate=1.0`。
- 复杂混合集 `navigation_slot_complex_100_cases.json` 必须保持 `pass_rate=1.0`，用于防止游览评价、闲聊、否定改路线、行程安排词抢走导航意图。
- 新增 alias / place 必须补 benchmark case。
- 新增 fallback 行为必须保证不会把 route-edit / trip-assistant 边界误抽成导航。

新增规则时至少检查这几类负例：

- `故宫好美啊，下面要去哪里比较顺？不用给路线。` 应归 `trip_assistant`。
- `别急着导航，先告诉我按现在行程下一站应该去哪。` 应归 `trip_assistant`。
- `别推荐路线替换方案，接着去X怎么走？` 应归 `navigation_text`。
- `从故宫到天坛坐地铁，几号线换乘？不是问步行路线。` 应归 `navigation_text`，mode 应为 `transit`。
- `开车去天坛，停车场怎么走、还有没有车位？` 应归 `out_of_scope`。
- `从这里到X怎么走？` 应保留 GPS 起点。

导航否定维护规则：

- 否定词与对象词分开维护：`NEGATION_OPERATOR_KEYWORDS` 维护 `别/不要/不用/不是问`，`NAVIGATION_NEGATION_TARGET_KEYWORDS` 维护 `导航/文字导航`。
- runtime 用短窗口组合判断 `否定词 + 导航对象词`，不要继续新增 `别导航/先别导航/不用导航` 这种合成短语。
- 暂不把 `路线` 放入导航否定对象词，避免 `别改路线，从A到B怎么走` 被误压成非导航。
- `别` 有边界保护：`别的景点` 里的 `别` 不算否定词，避免误伤 `不用推荐别的景点，导航到X怎么走`。

## 当前测试集

- 100 条专项集：`evals/datasets/navigation_slot_100_cases.json`
- 生成脚本：`evals/build_navigation_slot_100_dataset.py`
- 复杂混合 100 条：`evals/datasets/navigation_slot_complex_100_cases.json`
- 复杂混合生成脚本：`evals/build_navigation_slot_complex_100_dataset.py`
- benchmark runner：`evals/run_navigation_benchmark.py`
- 最新报告：`docs/navigation-slot-benchmark-2026-05-15.md`
- 步行 turn point smoke：`evals/run_navigation_turnpoint_smoke.py`
- 最新步行 turn point 真实高德结果：`evals/results/navigation_turnpoint_smoke_20260516.json`（8/8 available，全部 case 有 turn point 命中）
