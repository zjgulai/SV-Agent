# SV-Agent Domain Guide

本文件只补充本目录及其子目录的规则；全局规则仍以[根 `AGENTS.md`](../../../../../AGENTS.md)为准。

## Authority

- [Task runtime and authorization ADR](../../../../../docs/adr/0007-sv-agent-task-runtime-and-authorization.md)
- [Viral Replication context](../../../../../docs/contexts/viral-replication/CONTEXT.md)
- [Development and testing](../../../../../docs/development/testing.md)

## Local invariants

- 保持纯领域边界：允许标准库、Pydantic 与 `app.domain.*`；I/O、ORM、HTTP、worker、broker、provider 和浏览器状态留在外层。
- 保持 Task、Run、Job 分离。Task 是持续目标，Run 是绑定 Task revision 的有界尝试，Job 只是技术执行；技术成功不能写成笼统业务 `succeeded`。
- 保持 `GoalTrack`、`PrimaryMechanism`、`CreativeDimension`、RunPlan 与 ReplicationPlan 的 closed-contract 差异；RunPlan 必须绑定 Task/Run revision、版本、input digest 与 checkpoint。
- Artifact、Approval、runtime lineage 与 ToolRun 必须保留精确 revision、digest 和 handle；Agent recommendation 永远不是 Human Decision。
- 领域值优先 immutable，状态迁移必须显式。修改 enum value、event type、schema version、artifact type、approval gate 或 stable error identifier 时，同批更新 ADR/context、兼容性说明和测试。
- 只保留 typed factual state。Missing、unknown、unavailable、quarantined 与 limitation 必须显式，不能默认提升为 ready、pass 或 approved。

## Validation

```bash
rtk uv run --project apps/api python -m pytest apps/api/tests/unit/domain/sv_agent -q
rtk uv run --project apps/api ruff check apps/api/app/domain/sv_agent apps/api/tests/unit/domain/sv_agent
rtk uv run --project apps/api ruff format --check apps/api/app/domain/sv_agent apps/api/tests/unit/domain/sv_agent
rtk uv run --project apps/api python -m mypy apps/api/app/domain/sv_agent
```

若改动 persistence-facing envelope、Artifact、Approval 或 runtime record，继续执行 testing guide 的 SV-Agent persistence/journal 与相关 PostgreSQL integration gates。

## Hard boundaries

- 本目录不得导入 `app.adapters`、`app.api`、`app.worker`、FastAPI、SQLAlchemy、Celery、Redis 或 provider SDK，也不得执行数据库/网络 I/O、commit 或调度。
- 不持久化 private reasoning、credentials、private URL、absolute path、raw media 或未类型化任意 payload。
- 不以本目录改动开启 durable execution、公开写路由、自动审批、render 或 publish 能力。
