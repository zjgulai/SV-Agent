---
status: implemented
authority: regression-contract
---

# P1.5.1b Outbox 死信与运维恢复合同

## 目的与范围

本切片只约束 `OutboxEvent -> broker` 的投递恢复。它为持续不可用的
broker 增加指数退避、最大尝试次数、最大投递周期年龄和死信状态，防止
独立 reconciler 每五秒热循环。

不处理运行中的 `fetching`、`parsing`、`generating` 或 `validating` Job，
不限制 Celery/Provider 的执行期重试，也不增加 tenant、认证、计费或
ProviderRun。这些边界需要执行 lease、外部幂等或 SaaS 权限合同，不能用
投递死信代替。

## 状态与事实

```text
pending -- claim --> leased -- accepted --> published
   ^                   |
   |                   +-- broker error / lease expired --> pending (backoff)
   |
dead <--- delivery attempts or cycle age exhausted ---+
   |
   +-- deployment-channel operator command --> pending
```

- `dead` 是 `OutboxEvent` 的协调状态，绝不是 `JobState`。业务 Job 保持
  `queued`，因此 broker 故障不会伪装成商品导入或脚本生成失败。
- 每次死信写不可变的 `JobEvent(dispatch_dead_lettered)`；恢复写
  `JobEvent(dispatch_manual_retry_scheduled)`。两个事件都保留 `queued`
  作为实际 Job 状态。
- 每个投递周期以 `delivery_cycle_started_at` 和
  `delivery_attempt_count` 计量。人工恢复清零当前周期的尝试数，递增
  `manual_retry_count`，历史由 `JobEvent` 和死信字段保留。
- 错误码固定为 `OUTBOX_MAX_DELIVERY_ATTEMPTS` 或
  `OUTBOX_MAX_DELIVERY_AGE`。不存储 broker 原始异常、URL、网页或自由文本。

## 安全操作边界

当前没有 tenant/auth/RBAC。因此不存在 HTTP retry endpoint，也不存在 Web
重试按钮。恢复只能在部署内通过：

```bash
python -m app.worker.reconciler retry-dead-letter \
  --job-id <uuid> --confirm DEAD_LETTER_RETRY
```

命令仅接受 `dead + queued` 的 OutboxEvent；`published`、活跃 lease、运行中
或终态 Job 一律拒绝。命令随后只 nudge 同一 outbox，正常 reconciler 仍负责
投递。Web 仅展示“投递暂停，需运维恢复”，不会给匿名访客提供写操作。

## 数据库合同

`0008_outbox_dead_letter` 追加以下投递投影字段：

- `delivery_cycle_started_at timestamptz not null`
- `manual_retry_count int not null default 0`
- `last_manual_retry_at timestamptz null`
- `dead_letter_code varchar(64) null`
- `dead_lettered_at timestamptz null`

扩展 `delivery_state` 为 `pending|leased|published|dead`，保留 intent 字段
（事件、任务、payload、digest、创建时间）不可变。数据库约束和 trigger
保证：活跃 lease 仅可在 `leased`；`published` 不可重开；`dead` 必须带死信
码和时间且不带 lease；只有递增 `manual_retry_count`、清零当前周期尝试数的
`dead -> pending` 才允许发生。时间判定使用 PostgreSQL
`statement_timestamp()`，避免多进程机器时钟差异。

## 默认运行策略

- 最大尝试次数：10
- 最大投递周期年龄：3600 秒
- 首次退避：5 秒
- 最大退避：300 秒

退避以当前周期失败次数计算，且不改变 Job 状态。所有值可由 `REM_`
环境配置覆盖，配置本身有范围校验。

## 验收

1. 连续 broker 失败达到限次或限时后，OutboxEvent 为 `dead`，Job 仍为
   `queued`，只追加一次死信事件。
2. `dead` 后 reconciler 不再调用 dispatcher；未到 `available_at` 的
   pending 任务也不会重新 claim。
3. 过期 lease 才可参与死信，未过期 lease 不得被接管或提前死信。
4. 部署内命令只恢复 `dead + queued`，重置当前周期并追加恢复事件；其他
   状态拒绝。
5. 旧 lease token 在死信、恢复或新 lease 后不能发布。
6. 迁移在全新临时数据库执行 upgrade -> downgrade -> upgrade；intent 与
   JobEvent 的不可变性回归通过。
