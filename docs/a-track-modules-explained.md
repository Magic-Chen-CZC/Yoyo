# A 轨道五个模块说明

这份文档面向项目成员和评审同学，解释 `docs/todo.md` 中 A 轨道五个模块分别负责什么，以及这次分支里我们到底做了哪些工作。

相关分支：
- `feature/a-track-stabilization-and-validation`

相关总览文档：
- `docs/architecture.md`
- `docs/contracts.md`
- `docs/a-track-branch-notes.md`

---

## 先说整体：A 轨道在系统里负责什么

A 轨道对应的是这条用户链路里的“路线和运行时骨架”：

1. 用户先得到一个 itinerary
2. itinerary 对应一个具体的 `itinerary_version`
3. 用户开始导览时会创建一个 `guide_session`
4. session 里会记录当前走到第几站、用户当前位置、是否已经到站、播放状态
5. 地图接口和 session current 接口都从这套运行时状态里读数据
6. 如果用户改路线，系统要新建版本、切换活动版本，并且让正在进行的 session 尽量平滑跟过去

所以 A 轨道不是单一模块，而是一组围绕“路线版本 + 会话运行时 + GPS + 地图输出”的能力集合。`docs/todo.md` 里把这部分拆成了五块：A1 到 A5。

---

## A1. 路线编辑与版本管理

### 这个模块是干什么的

A1 解决的是“路线不是一成不变的”这个问题。

用户可能会说：
- 把某一站换掉
- 删除某一站
- 把顺序调一下
- 把整条路线缩短一点

这类需求不能直接覆盖原路线，因为：
- 历史版本要保留，方便回溯
- guide 资产和 QA 上下文都绑定到具体版本
- 正在运行的 session 也要知道自己关联的是哪一个版本

所以 A1 的职责就是：
- 接收结构化的路线编辑请求
- 基于当前 active version 生成一个新版本
- 保留旧版本可查询
- 切换 itinerary 的当前版本指针
- 同步处理正在运行的 session 跟版问题

### 这次做了什么

这次新增了两个核心接口：
- `POST /api/v1/planning/itineraries/{itinerary_id}/edits`
- `GET /api/v1/planning/itineraries/{itinerary_id}/versions`

新增支持的四种编辑操作：
- `replace_stop`
- `remove_stop`
- `reorder_stops`
- `shorten_route`

新增了统一的路线编辑请求模型，支持这些字段：
- `operation`
- `target_stop_id` / `target_stop_name`
- `replacement_stop_id` / `replacement_stop_name`
- `ordered_stop_ids`
- `target_stop_count`
- `created_by`

同时加了一层 stop catalog/resolver，目的不是让调用方上传完整 stop payload，而是让编辑接口只传目标 stop id 或名字，系统自己去解析规范 stop 数据。

### 这次定下来的规则

- 每次编辑都从当前 active `itinerary_version` 出发
- 每次编辑都会新建一个 `itinerary_version`
- 旧 active version 会被归档成 `archived`
- `itinerary.current_version_id` 会切到新版本
- 历史版本仍然可以通过 versions 接口查询

### 这块的关键文件

- `src/yoyo/api/v1/planning.py`
- `src/yoyo/modules/planner/service.py`
- `src/yoyo/modules/planner/schemas.py`
- `src/yoyo/modules/planner/stop_catalog.py`

### 你可以怎么理解它

可以把 A1 看成“路线编辑的版本控制层”。

它解决的不是单纯改 JSON，而是：
- 路线如何演进
- 版本如何切换
- 运行中的 session 如何不被编辑操作搞坏

---

## A2. Session 运行时状态

### 这个模块是干什么的

A2 负责“用户当前正在跑哪一站”这件事。

之前最容易出问题的地方是，系统会默认：
- 第一站永远是当前站

但这在真实导览里明显不成立，因为用户会：
- 播放完第一站后进入第二站
- 改路线后当前站顺序可能变化
- 删除当前站后当前站需要重新映射

所以 A2 的职责就是把 session 从“静态路线视角”切换成“运行时状态视角”。

### 这次做了什么

这次把 `current_stop_index` 明确纳入 session runtime 语义，并统一放在：
- `guide_session.context_json`

同时新增了统一的 runtime helper，避免在不同地方散着读 `context_json`。

`session current` 响应也补了两个关键字段：
- `current_stop_index`
- `has_next_stop`

现在 `GET /api/v1/session/{guide_session_id}/current` 会基于 `current_stop_index` 来计算：
- `current_stop`
- `next_stop`

而不是默认取 stops 里的第一个和第二个。

### 这次定下来的规则

- `current_stop_index` 是 session current 和 map current/next stop 的共同来源
- session 当前站必须从运行时状态推导，不能写死成第一站
- 路线编辑后，active session 要跟到新版本
- 如果新版本仍包含原当前 stop，就按 stop id 重映射
- 如果当前 stop 已经被删掉，就按旧索引做安全 clamp

### 这块的关键文件

- `src/yoyo/modules/session/runtime.py`
- `src/yoyo/modules/session/service.py`
- `src/yoyo/modules/session/schemas.py`

### 你可以怎么理解它

A2 相当于“导览播放的导航状态机骨架”。

如果没有这块，GPS、地图、播放进度都会各算各的，最后一定会乱。

---

## A3. GPS 与 Geofence

### 这个模块是干什么的

A3 解决的是“系统怎么知道用户到了某一站”。

这个判断不能只看 stop id，也不能靠手工点按钮，而是要基于用户上报的位置和当前站坐标来算距离。

所以 A3 的职责是：
- 接收 GPS 更新
- 计算用户到当前 stop 的距离
- 根据阈值判断是否到站
- 更新 session runtime
- 给 guide playback 发出触发信号

### 这次做了什么

这次加了：
- 统一距离计算 helper，使用 haversine
- 每个 stop 的 `arrival_threshold_meters`
- GPS 更新返回里的距离和阈值信息

`GPSUpdateRead` 现在会带出：
- `distance_to_current_stop_meters`
- `arrival_threshold_meters`
- `current_stop_index`

系统行为也被稳定下来：
- 每次 GPS 更新都写入 `current_position`
- 进入阈值时，如果还没标记过当前 stop，就写 `last_arrived_stop_id`
- 如果当前播放状态是 `not_triggered`，到站后会切到 `triggered`
- GPS 到站不会直接推进 `current_stop_index`

### 这次定下来的规则

- 到站判断公式是：
  - `distance_to_current_stop_meters <= arrival_threshold_meters`
- 如果 stop 没单独配置阈值，默认 `200` 米
- GPS 负责“判断到站并触发”
- GPS 不负责“切到下一站”

### 这块的关键文件

- `src/yoyo/modules/session/service.py`
- `src/yoyo/modules/session/runtime.py`
- `docs/architecture.md`

### 你可以怎么理解它

A3 可以理解成“从真实世界位置进入播放状态机的入口层”。

它只负责把“人到了没”这件事判断清楚，再把结果交给播放逻辑；它自己不越权推进站点。

---

## A4. 地图载荷改进

### 这个模块是干什么的

A4 负责给前端地图一份稳定、好用、不会乱飘的数据结构。

地图不是简单把 stops 原样吐出去就够了，前端还需要知道：
- 哪个 marker 是当前站
- 哪个 marker 是下一站
- polyline 的顺序是什么
- 还剩多少站
- 有没有下一站

所以 A4 的职责就是把 session/runtime 语义变成前端可直接消费的 map payload。

### 这次做了什么

这次稳定了地图接口：
- `GET /api/v1/map/session/{guide_session_id}`

明确了 marker 字段：
- `id`
- `name`
- `category`
- `latitude`
- `longitude`
- `order`
- `is_current`
- `is_next`

明确了 polyline 字段：
- `stop_id`
- `order`
- `latitude`
- `longitude`

新增了 `navigation_summary`：
- `current_stop_index`
- `stop_count`
- `remaining_stop_count`
- `has_next_stop`

同时保留：
- `current_stop`
- `next_stop`
- `current_position`

### 这次定下来的规则

- 地图里的 `current_stop` 和 `next_stop` 必须复用 session runtime 的推导结果
- 地图不能自己再去默认“第一个 marker 是当前站”
- 地图返回结构要稳定，方便前端直接接入

### 这块的关键文件

- `src/yoyo/modules/map/service.py`
- `src/yoyo/modules/map/schemas.py`
- `src/yoyo/api/v1/map.py`

### 你可以怎么理解它

A4 本质上是“把运行时导航状态翻译成前端地图语言”的那一层。

它的核心价值不是计算复杂，而是保证口径统一和字段稳定。

---

## A5. Contract Hygiene

### 这个模块是干什么的

A5 虽然名字看起来不像功能模块，但它非常重要。

它解决的是“共享数据结构不能边写边漂移”的问题。因为 A 和 B 是并行开发的，如果 stop contract 经常变，后面会连锁影响：
- planner
- session current
- map payload
- guide generation
- QA

所以 A5 的职责是：
- 把 stop contract 固定下来
- 把关键接口契约写进文档
- 确保运行结果和文档是一致的

### 这次做了什么

这次明确冻结了 stop 的关键字段：
- `id`
- `name`
- `category`
- `latitude`
- `longitude`
- `recommended_duration_minutes`
- `arrival_threshold_meters`

同时把这些约定写回了：
- `docs/architecture.md`
- `docs/contracts.md`

我们还补了一组 A5 验收测试，专门确认：
- `plan_json.stops[*]` 字段是完整的
- `session current` 的关键字段齐全
- `map payload` 的关键字段齐全
- 文档约定和运行时输出一致

### 这块的关键文件

- `docs/architecture.md`
- `docs/contracts.md`
- `tests/test_a_validation_suite.py`

### 你可以怎么理解它

A5 是“协作边界的卫生层”。

它的重点不是功能多炫，而是避免后面团队开发时出现“接口没说清楚、各自脑补、联调时全炸”的情况。

---

## 这五块是怎么串起来工作的

把 A1-A5 连起来后，完整链路是这样的：

1. planner 创建 itinerary 和第一个 `itinerary_version`
2. 用户进入导览，创建 `guide_session`
3. A2 根据 `current_stop_index` 计算当前站和下一站
4. A4 把这套运行时状态变成地图 payload
5. A3 接收 GPS 更新，判断有没有进入当前站 geofence
6. 如果到站，A3 只把播放状态推进到 `triggered`
7. 用户播放讲解并 `complete` 或 `skip`
8. session 才真正推进到下一站
9. 如果用户中途改路线，A1 新建路线版本并让 active session 跟过去
10. A5 确保上面这些共享结构在文档和实现里一致

---

## 这次除了功能实现，还做了哪些保障工作

除了把五块功能做出来，这次还补了三类保障：

### 1. 验收测试

新增了 A 轨道专门验收集：
- `tests/test_a_validation_suite.py`

覆盖内容包括：
- A1 路线编辑成功和失败场景
- A2 session progression
- A3 geofence 到站判断
- A4 map payload 稳定性
- A5 contract 字段校验
- 整条链路的集成 happy path 和失败场景

### 2. 压力与重复验证

新增了两个脚本：
- `scripts/run_a_validation.py`
- `scripts/run_a_live_blackbox_stress.py`

分别用于：
- 基于 pytest 的 A 验收重复运行和报告输出
- 对真实运行中的服务做黑盒压力验证

### 3. 真实数据库兼容修复

在 live 黑盒压测过程中，我们还发现并修了一个真实环境问题：
- PostgreSQL enum 落库值与 SQLAlchemy enum 映射不一致
- `guide_sessions` 缺少 `playback_state` 迁移

为此补了：
- `src/yoyo/db/enums.py`
- `alembic/versions/0002_add_guide_playback_state.py`

这一步很重要，因为它保证了 A 轨道不是只在测试环境里通过，而是真实 PostgreSQL 环境里也能跑通。

---

## 这次工作的最终结果

从交付角度看，这次 A 轨道完成了三件大事：

1. 把路线编辑、session、GPS、地图这几块真正连成了一个统一运行时
2. 把共享 contract 明确写进文档并稳定下来
3. 把验证从“能跑一次”升级成“有验收集、有压力脚本、有 live 黑盒确认”

如果后面有人接手这个分支，建议优先看：
- `docs/architecture.md`
- `docs/a-track-branch-notes.md`
- `docs/a-track-modules-explained.md`
- `tests/test_a_validation_suite.py`

这样会最快理解 A 轨道现在的设计和边界。
