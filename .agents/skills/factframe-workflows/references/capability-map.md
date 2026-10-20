# FactFrame 能力与证据编排图

## 主业务链

```text
Product Source
  -> immutable Product Snapshot
  -> governed Product Fact
  -> frozen Script Generation contract
  -> provider draft
  -> server-owned creative enforcement
  -> deterministic validation
  -> append-only Script Version
  -> live Storyboard preflight
  -> append-only Storyboard / Approval Event
  -> read-only Creative Comparison Projection
  -> typed external evidence
  -> deterministic Decision Brief
```

`Job -> JobEvent + Outbox -> Celery Worker -> reconciler/recovery` 是贯穿导入与生成的执行控制面，不是业务事实来源。

## 四个证据平面

| 平面 | 可产生 | 不可产生 |
| --- | --- | --- |
| Product Truth | eligible fact、claim blocker | performance winner、causal lift |
| Performance | observation、signal、source-scoped hypothesis | Product Fact、自动推荐 winner |
| Experiment | frozen-run observation、reviewed finding | 通用规律、生产接受 |
| Asset | Bundle/Index validity、QA 状态、Private Gate receipt | Product Fact、Commercial Approval |

外部证据进入 comparison 前必须经过各自 package validator、reviewed subject binding、lifecycle/exposure policy；不可直接写入 Product Truth。

## 证明层级

| 证据 | 能证明 | 不能证明 |
| --- | --- | --- |
| unit/static | 局部规则、类型、确定性 | PostgreSQL、broker、浏览器集成 |
| disposable PostgreSQL integration | schema、事务、锁、trigger | 真实 provider、deployment |
| Compose/E2E | 本地完整用户路径 | production proxy、真实外部服务 |
| public CI | exact committed checkout | dirty worktree、私有库 |
| Private Gate | 本机私有库与固定 baseline/current | 商业批准、部署 |
| capability graph | 代码与文档导航 | runtime、数据质量、上线状态 |
| deployment/live check | 指定目标当时可达 | 商业批准、长期稳定性 |

## 跨上下文任务检查

1. 是否有精确 subject identity？
2. 是否混淆 Snapshot、Model/Variant、Bundle 或 report selection？
3. 是否把外部 observation 升级成 Fact、winner 或因果？
4. 是否改写 append-only 历史？
5. 是否需要新增数据、权限、曝光或部署 gate？
6. 最终声明由哪一层当前证据支持？

## 权威入口

- `docs/index.md`
- `CONTEXT-MAP.md`
- `docs/architecture/system-overview.md`
- `docs/development/testing.md`
- `docs/product/capability-model.md`
- `docs/product/insight-performance-projection-design.md`
