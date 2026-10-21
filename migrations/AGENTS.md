# Migration Guide

本文件只补充 `migrations/` 的规则；全局规则仍以[根 `AGENTS.md`](../AGENTS.md)为准。

## Authority

- [Development and testing](../docs/development/testing.md)
- [System architecture](../docs/architecture/system-overview.md)
- [SV-Agent runtime and authorization ADR](../docs/adr/0007-sv-agent-task-runtime-and-authorization.md)
- 其他 schema 变更读取拥有该 schema 的 [`docs/decisions/`](../docs/decisions/)

## Local invariants

- `versions/` 是 append-only schema 历史：已提交 revision 不改名、不重排、不重写；修正通过新的后继 revision 表达。
- 新 revision 使用当前唯一 Alembic head 作为 `down_revision`，并保持 ORM model、`Base.metadata` 可发现性、migration 与拥有该 schema 的 PostgreSQL integration tests 同批一致。
- 保留 PostgreSQL trigger、`RESTRICT` FK、check constraint、sequence、current-head guard、CAS 与 append-only ledger 语义。
- 默认 expand-first：先增加兼容 schema，再启用 reader/writer。数据删除、搬移或 backfill 必须先有独立批准的迁移与恢复方案。
- Application/deployment database 只做 forward migration。Downgrade 只是新建 disposable PostgreSQL 上的结构测试，不是 production rollback。

## Validation

```bash
rtk uv run --project apps/api python -m alembic -c apps/api/alembic.ini heads
rtk uv run --project apps/api ruff check migrations
```

每个新 revision 都按 testing guide 的 disposable database recipe 验证完整往返：

```bash
rtk env REM_DATABASE_URL=<new-disposable-postgresql-url> uv run --project apps/api python -m alembic -c apps/api/alembic.ini upgrade <previous_revision>
rtk env REM_DATABASE_URL=<new-disposable-postgresql-url> uv run --project apps/api python -m alembic -c apps/api/alembic.ini upgrade head
rtk env REM_DATABASE_URL=<new-disposable-postgresql-url> uv run --project apps/api python -m alembic -c apps/api/alembic.ini downgrade <previous_revision>
rtk env REM_DATABASE_URL=<new-disposable-postgresql-url> uv run --project apps/api python -m alembic -c apps/api/alembic.ini upgrade head
```

随后运行受影响 constraint、trigger、CAS 或 repository 的真实 PostgreSQL integration tests；SQLite 和 unit test 不能替代该门。

## Hard boundaries

- 不对 application、development 或 deployment database 执行 downgrade，也不依赖默认 URL 运行破坏性命令。
- 不删除约束或 guard 来让测试通过，不在 migration 中伪造历史 Task、Run、actor、Approval 或隐式 backfill。
- Fresh-database CI green 与 disposable downgrade 都不代表已有数据兼容性、production rollback 或 production acceptance。
