# SV-Agent Web Feature Guide

本文件只补充本目录及其子目录的规则；全局规则仍以[根 `AGENTS.md`](../../../../../AGENTS.md)为准。

## Authority

- [SV-Agent Native Agent specification](../../../../../docs/product/sv-agent-native-agent-spec.md)
- [SV-Agent UI/UX audit](../../../../../docs/product/sv-agent-ui-ux-taste-audit.md)
- [Development and testing](../../../../../docs/development/testing.md)

## Local invariants

- 这里是 read-only Native Shell 的 feature state/styles，不是业务事实源。PostgreSQL projection 与 browser-local draft 必须持续分栏、分语义显示。
- Task Inbox、Mission Control 与 Evidence 只消费 GET projection；New Task 只保存本标签页的本地 brief，不创建或修改 PostgreSQL Task/Run/Approval。
- `sessionStorage` envelope 必须 versioned、bounded、closed-parse 且 fail-soft。Storage denial/corruption 只能降级本地草稿，不能遮蔽 authoritative projection 或制造成功保存提示。
- Storage key、schema version、field contract 和 v1/v2 compatibility 是用户数据合同；修改时必须带显式迁移/兼容策略与 targeted tests。
- Rights、child safety 与 Human Approval 保持 unresolved human gates；UI preview、Agent recommendation 和 persisted fact 都不能代替人工决定。
- Product Truth、Performance、Experiment 与 Asset evidence 保持分离；missing、unknown、unavailable、quarantined、blocked 与 error 不合并。
- 保持 desktop/tablet/mobile navigation、loading/empty/error/retry、focus、keyboard 和 reduced-motion 行为可用。

## Validation

```bash
rtk npm --prefix apps/web test -- --run src/routes/__tests__/task-inbox.test.tsx src/routes/__tests__/new-task.test.tsx src/routes/__tests__/mission-control.test.tsx src/routes/__tests__/evidence-artifacts.test.tsx
rtk npm --prefix apps/web run lint
rtk npm --prefix apps/web run typecheck
rtk npm --prefix apps/web run build
```

视觉或 responsive 改动还要按 UI/UX audit 在真实 desktop、tablet 与 mobile 视口复核。

## Hard boundaries

- 本目录不新增 POST/PATCH/DELETE、provider/Tool dispatch、Run/Job start、approve/reject、render、publish 或 social action。
- 不把 `sessionStorage`、mock、prototype 或 last-good UI state 提升为 PostgreSQL authority。
- 不在 UI、日志或错误态暴露 raw payload、digest、locator、filesystem path、credential、private identifier 或模型 private reasoning。
