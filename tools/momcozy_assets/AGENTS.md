# Momcozy Asset Tool Guide

本文件只补充本目录的规则；全局规则仍以[根 `AGENTS.md`](../../AGENTS.md)为准。

## Authority

- [Tool behavior and entrypoints](README.md)
- [Public synthetic CI / Private Gate ADR](../../docs/adr/0006-separate-public-synthetic-ci-from-private-asset-validation.md)
- [Momcozy Asset Intelligence context](../../docs/contexts/momcozy-asset-intelligence/CONTEXT.md)
- [Development and testing](../../docs/development/testing.md)

## Local invariants

- 本目录只跟踪工具、固定 baseline 与 synthetic tests；真实商业媒体始终留在 gitignored Private Gate。
- `private_gate.py` 是真实库只读验收 Interface：两次 fresh compile、固定 baseline 与 canonical current release 必须一致。成功只报告安全 `baseline/state/count` receipt，失败只报告稳定 failure code。
- `aggregate_index.py` 会发布 immutable release 并切换 current；`archive_batch.py` 会创建 Asset Bundle。二者都是独立写入门，不属于 Private Gate。
- 固定 baseline 只在独立扩库评审中版本化更新；普通验证、自动化和 Private Gate 不更新 baseline。
- Public CI 只验证 committed synthetic fixtures 与 fail-closed contracts；它不会读取真实库，也不能替代 real-library Gate Receipt。
- Gate Receipt 只证明当次技术一致性，不代表 Commercial Approval、发布、部署、runtime 或 production acceptance。

## Validation

默认只运行公开安全的 synthetic/static gates：

```bash
rtk uv run --project apps/api python -m unittest discover -s tools/momcozy_assets/tests -v
rtk uv run --project apps/api ruff check tools/momcozy_assets
rtk uv run --project apps/api python -m mypy --explicit-package-bases tools/momcozy_assets/aggregate_index.py tools/momcozy_assets/contracts.py tools/momcozy_assets/private_gate.py
```

只有用户明确授权真实库只读验证时，才运行：

```bash
rtk uv run --project apps/api python -m tools.momcozy_assets.private_gate outputs/momcozy-content-assets/<approved-scoped-root>
```

## Hard boundaries

- Private Gate 任务不得 archive、publish、repair、delete、扩大 scope、更新 baseline 或修改 current release。
- 不把真实库挂载、复制、缓存或上传到 public CI、tracked docs、artifacts 或能力图谱。
- 不输出 absolute path、Bundle ID、manifest/Prompt/QA 正文、media、hash、credentials、private identifier 或本地 automation 信息。
- 只读验证不串联 `validate`、`aggregate_index` 或 `archive_batch`，也不把 public CI green 或 Gate Receipt 描述成商业或上线许可。
