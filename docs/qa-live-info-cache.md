# QA Live Info Cache

`live_info` 只用于同日或近时段的景点官方运营信息，例如开放、闭馆、预约、检票、临时公告。它会调用外部 live search provider，因此是 QA 链路里最容易抬高 P95 的环节之一。

## 当前链路

1. `build_hybrid_context(...)` 在 `intent == live_info` 时调用 `get_live_info_context(...)`
2. `get_live_info_context(...)` 调用 `build_live_info_payload(...)`
3. `build_live_info_payload(...)` 先查 Redis 缓存，miss 后才调用 live search provider
4. 返回 payload 会继续转换为 `LiveInfoContext`，并进入 QA prompt / metadata

## Cache Key

缓存 key 由业务语义组成，而不是直接使用原始 query：

```text
qa:live_info:v1:{beijing_date}:{subject_slug}:{info_type}
```

当 `info_type == general` 时，会追加 query hash，避免过粗复用。

`info_type` 当前按轻量规则归类：

- `opening`：开放、开门、营业、能去、open、opening 等
- `hours`：几点、开放时间、营业时间、hours、time 等
- `ticketing`：预约、预订、门票、ticket、reservation、booking 等
- `closure_notice`：闭馆、关闭、暂停开放、公告、notice、closure 等
- `general`：其他 live_info 查询

## TTL

配置项：

- `LIVE_INFO_CACHE_ENABLED=true`
- `LIVE_INFO_CACHE_TTL_SECONDS=900`
- `LIVE_INFO_CACHE_NOTICE_TTL_SECONDS=300`
- `LIVE_INFO_CACHE_FAILURE_TTL_SECONDS=60`

默认策略：

- 普通可用结果：15 分钟
- 临时公告/闭馆类：5 分钟
- provider 降级或不可用：1 分钟

Redis 不可用时，缓存层会静默 miss，并进入短暂进程级 backoff，避免每个请求都额外等待 Redis 连接失败。

## Metadata

`live_info` metadata 会暴露：

- `live_info_cache_hit`
- `live_info_cache_key`
- `live_info_cached_at`
- `live_info_cache_ttl_seconds`
- `live_info_info_type`

E2E benchmark 的 `review_cases` / `cases` 会把这些字段纳入 live_info 中间结果，方便检查缓存是否命中。

## 测试建议

1. 首次请求同一景点今日开放信息，应 `cache_hit=false`
2. 短时间重复请求同一景点同一 `info_type`，应 `cache_hit=true`
3. provider 降级结果不应长时间缓存
4. 不同 `info_type` 不应共用缓存，例如“今天开放吗”和“需要预约吗”
