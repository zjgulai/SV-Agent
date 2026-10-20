# Creative Comparison 实施门

每次任务先从代码、tests、routes、migration 和 Web negotiation 重新确认当前 gate。设计文档不是 runtime 证据。

## Gate v1：Product Truth comparison

- 两个 immutable Script Versions，同一 frozen generation。
- 一次 PostgreSQL statement 读取共享 current Fact observation。
- 分开返回 stored/live validation、Storyboard preflight、readiness 与完整 Difference Ledger。
- 外部 performance/experiment/asset sections 诚实为 unavailable。
- GET 只读、无 request-time LLM、无 ignored-directory scan。

## Gate D1：package contracts

- typed package models 与 missing-value semantics
- deterministic validator 与 canonical digest
- committed Synthetic Fixture
- unavailable/in-memory reader
- 不接 descriptor、binding registry、route 或 Web runtime

## Gate D2：reviewed runtime binding

只有以下条件齐备才可声称接入：

1. descriptor-bound reader，不接受任意 path。
2. append-only reviewed binding registry。
3. composite identity 与 recomputed Snapshot digest。
4. package schema/digest/scope/lifecycle/exposure validation。
5. duplicate active binding 与 invalid package 的 quarantine。
6. v2 Projection 与 deterministic Decision Brief。
7. closed `Accept` negotiation、`Vary: Accept`、server/Web 双 flag、合法 v1 fallback。
8. API、Web、sensitive-value、无写入/无网络回归测试。

## Gate D3 / D4

- D3：tenant identity、canonical Product Family/Model/Variant、RBAC、private evidence trace。
- D4：standalone Insight Hub/dashboard。

没有单独批准与实现证据时，不把 D3/D4 需求顺手并入 D2。

## 当前检查点

截至 2026-09-16 的工作区审计显示 v1 与 D1 代码/测试存在，D2-D4 尚不能视为已实现。该信息可能随工作区变化；执行时必须重验。
