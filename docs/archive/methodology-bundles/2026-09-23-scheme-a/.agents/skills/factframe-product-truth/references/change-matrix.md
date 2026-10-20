# Product Truth 变更矩阵

| 变更类型 | 先读 | 必须证明 |
| --- | --- | --- |
| Source / manual intake | Product Truth context、API route、application service | manual provenance 固定；重复输入行为明确 |
| Snapshot | domain entity、repository、migration | append-only；identity 与 canonical digest 不混淆 |
| Product Fact | domain state machine、repository、database trigger | proposed/confirmed/locked 合法转换；locked/evidence 不可变 |
| selected/excluded | generation contract、validator | ordered、unique、disjoint、same Snapshot |
| Promotion Fact | Promotion decision、database-time query | 独立字段、有效期、不能进入普通 fact sets |
| trusted connector | port、adapter、worker | connector trust 边界；只产生 proposed observation |
| schema/migration | latest migration、integration fixtures | upgrade；必要时仅 disposable DB downgrade/upgrade |

## 高风险反例

- manual request 自称 `source_field`
- 为复用 digest 更新旧 Snapshot
- confidence 达阈值自动 confirmed
- selected 与 excluded 交集或跨 Snapshot
- Promotion 通过普通 claim binding 进入任意 shot
- repository 内部 commit，导致跨 repository 事务破裂
- 为兼容旧数据放宽 trigger 或 validator

## 最小验证集

1. 受影响 domain unit test。
2. 真实 PostgreSQL repository/API integration。
3. append-only/locked/selection 的数据库级拒绝测试。
4. `apps/api/tests/unit/test_architecture.py`。
5. `ruff check` 与 `mypy apps/api/app`。

完整命令以 `docs/development/testing.md` 为准；不要复制旧的绿色结果作为当前证据。
