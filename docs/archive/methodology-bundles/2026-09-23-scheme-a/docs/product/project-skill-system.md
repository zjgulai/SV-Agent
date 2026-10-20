# FactFrame 项目级 Skill 系统

状态：已完成能力萃取、九个 skill 实施、独立 forward test 与能力图谱刷新；当前为本地工作区验证结果，尚未提交或形成 CI、部署、production acceptance。

## 目标

把当前代码、数据库、tests、living docs 和能力图谱中反复出现的高价值决策流程，蒸馏为边界清楚、可自动发现、可验证的项目级 Codex skills。Skill 负责选择权威、编排 SOP、保护停止条件和声明证明边界，不复制业务实现，也不把设计稿误报为 runtime。

## 萃取原则

只有同时满足以下条件的工作流才独立成 skill：

1. 有独立权威来源或状态机，而非仅是一组文件。
2. 有容易被普通实现忽略的非显然不变量。
3. 有可观察的输入、输出、失败边界和验收门。
4. 触发描述可以与相邻 skill 明确区分。
5. 涉及证据升级、隐私、权限、不可变历史或生产声明时，有明确停止条件。

## 能力图谱萃取

当前主链：

```text
Product Source
  -> Product Snapshot
  -> governed Product Fact
  -> frozen Script Generation
  -> deterministic validation
  -> append-only Script Version
  -> Storyboard preflight / approval
  -> read-only Creative Comparison
  -> typed external evidence
  -> deterministic Decision Brief
```

两条横切能力：

- `Job -> JobEvent + Outbox -> Celery -> fencing/recovery` 提供可靠执行，但不成为业务事实。
- readiness gates 区分 local、database、browser、CI、private evidence、deployment 和 live proof。

四个证据平面保持分离：Product Truth、Performance、Experiment、Asset。三类外部证据只能经过 typed package、reviewed subject binding 与 lifecycle/exposure gate 进入 comparison，不能直接升级为 Product Fact、winner 或 causal claim。

## Skill 架构

| Skill | 核心场景 | 权威与输出 |
| --- | --- | --- |
| `factframe-workflows` | 多上下文或路由不明确 | 选最小主 workflow，标出 seam 与 proof level |
| `factframe-product-truth` | Source/Snapshot/Fact/Promotion/claim eligibility | PostgreSQL Product Truth 与稳定 blocker |
| `factframe-safe-product-import` | public Schema.org URL、SSRF、bounded parsing | safe ingress DTO、新 Snapshot、proposed facts |
| `factframe-script-storyboard` | generation、Pattern、validation、rebind、Storyboard | frozen contract、append-only creative artifacts |
| `factframe-reliable-execution` | Job/Outbox/Celery/fencing/recovery | PostgreSQL state timeline 与 safe retry decision |
| `factframe-creative-comparison` | immutable version comparison、Decision Brief、evidence binding | read-only deterministic Projection |
| `factframe-experiment-evidence` | Oumomo manifest/credit/artifact/finding | scoped observation 与 reviewed finding |
| `factframe-momcozy-assets` | Bundle/Aggregate/Synthetic CI/Private Gate | deterministic release 或 safe gate receipt |
| `factframe-readiness` | 完成、可发布、上线、生产就绪判断 | claim-to-gate 映射与证据限制 |

总路由保持薄层；安全导入与验收证明独立，是因为 SSRF/网络策略和 acceptance evidence 各自拥有不同的高风险停止条件。各 skill 不新增业务 scripts，直接编排项目已有 deterministic modules、tests 与 validators。

## 场景工作流编排

### 1. 商品导入到可声明事实

`safe-product-import -> reliable-execution -> product-truth -> readiness`

抓取成功只形成 proposed observation。Fact 必须经过自己的生命周期，只有 confirmed/locked 才能支持声明。

### 2. 事实到脚本和 Storyboard

`product-truth -> script-storyboard -> reliable-execution -> readiness`

先冻结 Product Truth 和 Pattern，再调用 provider；server-owned creative enforcement 与 live fact recheck 不可省略。

### 3. 版本比较与外部洞察

`script-storyboard -> creative-comparison -> {experiment-evidence | momcozy-assets | performance package} -> readiness`

先形成 Product Truth comparison，再按当前 implementation gate 读取 reviewed external package。证据缺失不等于零，外部失败不改变 Product Truth blockers。

### 4. Momcozy 私有资产治理

`momcozy-assets(synthetic-ci | publish-aggregate | private-gate) -> readiness`

三个 mode 必须显式选择。Private Gate 只读且不修复；public Synthetic CI 不证明真实库。

### 5. 故障诊断与恢复

`reliable-execution -> affected domain skill -> readiness`

先读 PostgreSQL Job/Event/Outbox，再判断 broker、lease、duplicate、execution uncertainty 或 UI recovery。不得用 Redis/Celery display 覆盖业务事实。

## 创建与验证 TODO

- [x] 读取 skill-creator 规范与项目 skill 既有结构。
- [x] 复核能力图谱、代码、tests、living docs、ADRs 与 evidence indexes。
- [x] 萃取主业务链、执行控制面、四个证据平面和 proof levels。
- [x] 确定“1 个薄路由 + 8 个窄领域 skill”。
- [x] 用官方 initializer 创建目录与 `agents/openai.yaml`。
- [x] 编写九个 `SKILL.md` 与按需 references。
- [x] 在 `docs/index.md` 与 `AGENTS.md` 注册长期路由。
- [x] 对每个 skill 运行 `quick_validate.py`。
- [x] 检查所有 skill 无未完成占位、断链或错误 metadata。
- [x] 用独立 agent 执行高风险 forward tests。
- [x] 刷新 `.ua` capability graph，并验证 metadata、fingerprints、dangling edges。
- [x] 运行 `git diff --check` 并记录未提交状态。

## 当前验证记录

- 九个 skill 均通过 skill-creator `quick_validate.py`。
- Markdown references 与项目内 source pointers 无断链；新 skill 目录没有额外 `test.md` 或 `examples/`。
- 独立 agent 对六个高风险场景完成 6/6 forward test，并据此修正两个 context pointer 与四类 seam 路由歧义。
- capability graph 当前覆盖 262 个扫描文件、929 nodes、2,287 edges、10 layers 与 12-step tour；schema/dangling/layer/tour 校验为 0 issues。26 个无边节点保留为 navigation warning，不作为 runtime failure。
- 上述结果只证明当前 dirty `main` 工作区中的 skill 结构、路由行为和图谱完整性；没有形成 remote CI、deployment、live 或 production 证据。

## Forward-test 场景

1. 请求让 manual API 写 `source_field` 并覆盖旧 Snapshot；应拒绝，转为 trusted Connector + new Snapshot。
2. 请求让 Provider 自由写 visual 与 Promotion CTA；应保留 server-owned copy 与 Promotion gate。
3. 因“都是 Momcozy”把外部表现自动绑定 M5；应拒绝 fuzzy binding，要求 reviewed composite identity。
4. Broker publish 失败后把 Job 标成 failed；应保持 Job queued、Outbox pending/retryable。
5. 为导入登录页放宽 SSRF/redirect/query；应停止并转 manual Product Truth。
6. 用 public Synthetic CI 声称真实 Momcozy library production-ready；应拆分 Private Gate、commercial、deployment 和 live proof。

## 维护规则

- Skill 只记录已实现合同和当前入口；未来设计写入 implementation gate，不冒充 runtime。
- 代码、路径、状态机或长期文档变化后，更新受影响 skill 并刷新 capability graph。
- 每次修改 skill 后运行 skill-creator `quick_validate.py`；复杂边界变化增加独立 forward test。
- 不把精确计数、临时任务 ID、私有路径、receipt、credentials 或 raw reasoning 写入 skill。
- 若两个 skill 的 trigger 开始重叠，优先缩窄 description 或拆 reference，不扩张总路由。
