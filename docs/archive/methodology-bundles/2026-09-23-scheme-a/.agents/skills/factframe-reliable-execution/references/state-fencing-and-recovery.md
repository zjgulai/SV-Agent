# Job、Outbox 与恢复状态机

## 权威链

```text
canonical request
  -> PostgreSQL Job
  -> append-only JobEvent
  -> transactional Outbox intent
  -> lease-bound publish
  -> opaque Job UUID message
  -> Worker reload + execution fencing
  -> append-only terminal result/event
```

## 投递与执行不可混淆

- Outbox `pending/leased/dead` 描述投递，不是业务 Job 终态。
- broker publish 成功不等于 Worker 执行成功。
- Celery result backend 不是业务事实。
- 过期 publisher 必须因 lease token 不匹配而无法确认。
- `attempt_count` 是执行 fencing token，不是展示计数。
- 普通 duplicate 与 broker redelivery/Celery retry 的恢复资格不同。

## 诊断清单

1. Job type、idempotency key、input digest 是否一致？
2. Job 当前状态与最后一个 JobEvent 是否一致？
3. Outbox 是否 pending、有效 leased、expired 或 dead？
4. 当前 publisher 是否仍持有 token？
5. Worker 是否从 PostgreSQL 重载输入并拥有当前 execution token？
6. 失败是 domain、connector/provider、SQLAlchemy/OSError，还是未知中断？
7. replay 是否会重复外部 side effect？
8. UI 恢复是否绑定精确 persisted operation？

## Operator recovery

只对 `Outbox=dead` 且 `Job=queued` 的精确目标创建新 delivery cycle。使用固定 confirmation token，记录 operator action，禁止匿名 HTTP retry。不要自动接管运行中状态。

## 验证焦点

- Job domain unit tests 与 Celery config。
- `test_reliable_execution.py` 的 broker failure、lease、redelivery、fencing、terminal replay。
- Product import 与 execution timeline integration。
- 跨浏览器恢复时再运行 Web unit/Compose E2E。

绿色 integration 不能证明真实 broker/provider 已恢复，也不能证明 exactly-once。
