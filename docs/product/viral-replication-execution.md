# Viral Replication：方案 A 执行台账

状态：已批准方案 A；Wave 0 的 workflow/skill/P3 本地验证和 Understand full graph 已完成；`VR-P4-001 attention grammar`、`VR-P4-002 conversion action`、`VR-P4-003 trend native` 与 `VR-P4-004 media integrity` 的 canonical skill、workflow、fixtures、前向复核和图谱 freshness 更新已完成。`VR-P4-004` 仅建立 document-level 的 `MediaIntegrityRecord` 和 local preflight/artifact-review gate，不代表已审阅真实媒体或取得权利、商业、平台、发布或 production acceptance。Git 提交、远端 CI、部署与 production 状态必须分别验证。

2026-10-07：本方案的**首个端到端真实复刻案例**已跑通并按有界证据收口——Momcozy KleanPal Pro（主机制 experience-pov；独立 workflow 工件，未经应用内 ScriptVersion/StoryboardVersion 通道；含 TikTok 热度有界核验，结论：不得声称爆款）。案例入口为本地 ignored 产物 `outputs/kleanpal-pro-replication/2026-10-04-us-white/CASE-INDEX.md`（汇报页 `report/kleanpal-case-brief.html`）。该案例不改变本批完成定义，也不构成权利、商业、平台或发布结论。

## 目标

在 FactFrame 现有 Product Truth、Script/Storyboard、Creative Comparison、Experiment Evidence、Asset Intelligence 和 Readiness 结构上，建立“共享核心 skills + workflow packs”的爆款复刻能力族。

复刻的对象是可验证的创意机制，不是原视频的表层复制。每次复刻必须绑定一个 `Primary Replication Mechanism` 和一个 `Replication Contract`。

## 已批准结构

```text
.agents/
├── skills/                         # Codex 可发现的 canonical skills
│   ├── factframe-*/                 # 既有 FactFrame skills
│   └── viral-*/                     # 本能力族的窄 skills
└── workflows/viral-replication/     # workflow 级 SOP 与 skill-map
    ├── README.md
    ├── routing-decision-tree.md
    ├── shared-artifact-contracts.md
    ├── shared-scorecard.md
    └── <workflow>/SOP.md
```

workflow 文件夹通过 `skill-map.md` 引用 canonical skills，不复制 `SKILL.md`。这样既满足每个 workflow 对应多个 skills，也保持单一权威、可发现和可验证。

## MECE 类型

| ID | 主机制 | 首批状态 | 核心验收 |
| --- | --- | --- | --- |
| `narrative-transformation` | 问题—转折—解决—结果 | Wave 1 | 叙事关系保持，商品主张重新 fact-bind |
| `proof-demonstration` | 实验、对比、量化、物理演示 | Wave 1 | 可观察现象与结论分离，proof claim=0 unsupported |
| `experience-pov` | POV、ASMR、感官与动作体验 | Wave 1 | 连续性、体验语言和商品事实分离 |
| `attention-grammar` | Hook、信息揭示/镜头节奏、字幕节拍、视觉反差、声音时序 | Wave 2，`VR-P4-001` 已完成 | 单一 attention component 可迁移，表层相似和因果越权风险受控 |
| `conversion-action` | 异议、促销、CTA、行动路径 | Wave 2，`VR-P4-002` 已完成本地文档/fixture 验证 | 唯一 conversion component、Promotion Fact、数据库时间有效期、CTA slot/provider ownership 与 action-path 状态完整 |
| `trend-native` | 趋势、音频、平台梗、挑战模板 | Wave 3，`VR-P4-003` 已完成本地文档/fixture 验证 | 唯一 Trend Component、有界趋势观察、冻结 TrendAdmissionRecord 与 source substitution 可复核；真实权利、平台兼容、原创批准和发布仍是独立 gate |

主类型由“复刻成功最依赖的唯一机制”决定；其余只能作为 secondary mechanisms。不可分离的双机制必须拆成两个 Variant。

## Skill 责任矩阵

### 共享核心

| Skill | 输入 | 输出 | 不负责 |
| --- | --- | --- | --- |
| `viral-reference-intake` | 来源、URL/媒体、权限信息 | ReferenceBundle | Product Fact、媒体生成 |
| `viral-content-decomposition` | ReferenceBundle | DecompositionMap | 目标商品真实性 |
| `viral-pattern-abstraction` | DecompositionMap | PatternHypothesis | 自动判定因果 |
| `viral-replication-contract` | Hypothesis、Facts、实验配置 | ReplicationContract | 真实 provider 调用 |
| `viral-fact-mapping` | Snapshot、Facts、参考声明 | claim mapping、deny-set | 将模型猜测升级成 Fact |
| `viral-media-integrity` | frozen Contract、fact-bound Storyboard、artifact/source/asset evidence | 六个互斥 integrity gate 的 `MediaIntegrityRecord` | 媒体生成、版权/法律意见、商业/平台/发布批准 |
| `viral-experiment-evaluation` | Contract、Artifacts、Ledger | Finding、Scorecard | 生产发布结论 |

### 既有能力复用

- 商品事实：`factframe-product-truth`
- 脚本与分镜：`factframe-script-storyboard`
- 可靠执行：`factframe-reliable-execution`
- 比较和外部证据：`factframe-creative-comparison`
- 实验和账务：`factframe-experiment-evidence`
- 私有资产：`factframe-momcozy-assets`
- 完成与证明边界：`factframe-readiness`

### 类型专属

- narrative：叙事弧、痛点转化、时长预算
- proof：proof device、实验协议、声明审计
- experience：POV 触点、感官连续性、商品 identity QA
- attention：Hook grammar、节拍迁移、表层差异审计
- conversion：异议/CTA、Promotion Fact、促销风险
- trend：有界趋势观察、source substitution 与 TrendAdmissionRecord
- cross-cutting media integrity：artifact/技术/声画/身份/来源使用范围/原创差异六道独立 gate

## Ticket 分层

### P0：领域和路由基础

- `VR-P0-001` 建立 Viral Replication context 与术语表。
- `VR-P0-002` 建立六类 primary mechanism 判定树与互斥规则。
- `VR-P0-003` 在现有 `factframe-workflows` 增加复刻路由和 seam 说明。
- `VR-P0-004` 建立 ReferenceBundle、DecompositionMap、PatternHypothesis、ReplicationContract 的 artifact contract。

验收：任意参考内容能得到唯一主类型；无法判定时稳定输出 blocked/需要拆分，而不是生成 hybrid SOP。

### P1：共享核心 skills

- `VR-P1-001` `viral-reference-intake`。
- `VR-P1-002` `viral-content-decomposition`。
- `VR-P1-003` `viral-pattern-abstraction`。
- `VR-P1-004` `viral-replication-contract`。
- `VR-P1-005` `viral-fact-mapping`。
- `VR-P1-006` `viral-experiment-evaluation`。

验收：每个 skill 有窄 description、清楚 inputs/outputs/stop conditions、可按需加载的 references，并通过 `quick_validate.py`。

### P2：第一批 workflow

- `VR-P2-001` `01-narrative-transformation` SOP。
- `VR-P2-002` `02-proof-demonstration` SOP。
- `VR-P2-003` `03-experience-pov` SOP。
- `VR-P2-004` 为三类 workflow 编写 skill-map、happy path 和 blocked path。

验收：三类 workflow 能串联共享 skills，并把目标事实重新绑定；不得复制参考台词或把观察升级成功效事实。

### P3：证据和 adversarial tests

- `VR-P3-001` 参考不可播放/刷新不稳定 fixture。
- `VR-P3-002` observed zero / unavailable / source ambiguous fixture。
- `VR-P3-003` unsupported claim 与 excluded fact resurrection fixture。
- `VR-P3-004` 多变量漂移 fixture。
- `VR-P3-005` 版权/授权未知 fixture。
- `VR-P3-006` 独立 agent forward test。

验收：所有高风险样本 fail closed，且 finding 能指出具体 blocker 和 proof level。

### G0：Understand consistency gate

- `VR-GRAPH-001` 只读核对 ignore、扫描文件集、旧 graph/meta/fingerprints 和插件执行入口；本批已完成。
- `VR-GRAPH-002` 在入口与 ignore 策略确认后执行完整 Understand pipeline；已完成。
- `VR-GRAPH-003` 运行 assemble、layer、tour、dangling reference 和 graph reviewer 验收；已完成。

验收：`knowledge-graph.json`、`fingerprints.json`、`meta.json` 与同一文件集一致，并且 graph reviewer 没有未处理 critical issue。deterministic scan 单独通过不能替代该 gate。

### P4：后续机制

- `VR-P4-001` attention grammar：已新增 canonical `viral-attention-grammar`、`04-attention-grammar` workflow、attention component partition、五个 P4 fixture 和独立前向测试。首次测试捕获 `attention_pattern_anchor_mismatch`，修正后可进入 local contract / fact-bound Script/Storyboard gate；任何 performance、causal、media、platform 或 default Pattern 升级请求仍保留 evidence blocker。
- `VR-P4-002` conversion action：已新增 canonical `viral-conversion-action`、`05-conversion-action` workflow、`objection_resolution`/`promotion_contract`/`cta_invitation`/`action_path` 的互斥 component partition、五个 P4 fixture 和独立前向测试。当前 runtime 只允许 frozen CTA policy：generic CTA 不带 offer，Promotion 只允许经独立字段、数据库时间校验后由服务端渲染到最终 CTA；action path 只能是受控 binding 或 `not_applicable`，外链、下单、账号、billing、真实转化和发布保持范围外。
- `VR-P4-003` trend native：已新增 canonical `viral-trend-native`、`06-trend-native` workflow、`trend_signal_binding`/`trend_semantic_frame`/`template_grammar`/`audio_function` 的互斥 component partition、五个 P4 fixture 和独立前向测试。权利、平台兼容和原创差异统一冻结为文档级 `TrendAdmissionRecord`，不是 Creative Dimension 也不是 runtime entitlement；当前只允许 `execution_capability=not_implemented` 与受限本地 artifact/合同 gate，音频/模板授权、平台验证/操作、完整原创审批、媒体生成和发布继续移交独立 gate。
- `VR-P4-004` media QA、原创度和权利门：已新增 canonical `viral-media-integrity`、`07-media-integrity` workflow、六道独立 integrity gate、五个相邻边界 fixture 和前向复核。它把 artifact traceability、technical profile、communicative surface、target identity continuity、source-use scope、originality delta 固化为 `MediaIntegrityRecord`；`preflight` 只允许 `not_applicable_pending_artifact` 和 `proceed_with_limits`，`artifact_review` 也只代表受限本地审计。Momcozy Bundle/Index/Private Gate、工具 probe、模型相似度或 QA disposition 不能跨层成为来源授权、法律、商业、平台、发布或 production 证明。

验收：先有证据和 fixture，再允许 workflow 宣称可用；不把未来 RenderJob、billing 或 social publishing 偷渡进本次范围。

## Wave 0 当前执行

- [x] 读取项目文档、上下文、现有 skills、Oumomo SOP 和当前 dirty 状态。
- [x] 形成方案 A 的完整 HTML 方案。
- [x] 完成垃圾候选审计并将明确生成垃圾移到可恢复隔离目录。
- [x] 写入 Viral Replication context。
- [x] 写入 workflow pack 目录和三份首批 SOP。
- [x] 写入六个共享核心 skills。
- [x] 执行 skill quick validation（9 个首批 skills 全部通过）。
- [x] 更新 `docs/index.md`、`CONTEXT-MAP.md` 和现有路由 skill。
- [x] 运行 HTML 结构、workflow 文件完整性和 `git diff --check`。
- [x] 写入五个 P3 adversarial fixtures 和 VR-P3-006 独立前向测试场景。
- [x] 完成 VR-P3-006 独立 agent forward test；结果为 blocked，实际 blocker 已固化为 local fixture evidence。
- [x] 完成最终 Understand deterministic scan；当前扫描 `filesScanned=282`、`filteredByIgnore=144`、复杂度 `large`，workflow pack 文件 19 个已纳入。
- [x] 完成最终 Understand deterministic import map 和 batch 计算；内部 import edges `321`，语义 batches `25`。
- [x] 完成 `VR-GRAPH-001` 只读 consistency audit；旧 graph 内部有限检查无 critical issues，但与当前文件集存在 22 个文件差异。
- [x] 完成 Understand-Anything full graph review；`.agents/skills/` 按确认继续排除，graph reviewer `approved=true`，0 critical issues、50 warnings。
- [x] 完成 `VR-P4-001 attention grammar`：独立前向测试、最终验证和图谱 freshness 更新。首次 Pattern anchor blocker 与修正结果已保留。
- [x] 完成 `VR-P4-002 conversion action`：独立前向测试、Promotion/CTA/provider/action-path 边界夹具、文档级 workflow 与图谱 freshness 更新。
- [x] 完成 `VR-P4-003 trend native`：独立前向测试、趋势组件/TrendAdmissionRecord、source audio/template substitution、平台 capability 与原创差异交接夹具、文档级 workflow 与图谱 freshness 更新。
- [x] 完成 `VR-P4-004 media integrity`：canonical skill、07 cross-cutting workflow、MediaIntegrityRecord 六道互斥 gate、五个相邻边界 fixture、preflight 前向复核和图谱 freshness 更新；尚未访问或批准任何真实 media/asset/platform。

## 完成定义

本批完成不等于生成视频、发布内容或 production ready。完成定义只包括：

1. 文档和 skills 结构可发现、可路由、可验证；
2. 三类首批 workflow 的输入、输出、stop conditions 和 handoff 明确；
3. 高风险 fixture 能证明 fail-closed 行为；
4. 所有结论保留 local、CI、private、deployment、live 和 production proof level；
5. 没有删除或覆盖已有 Oumomo、Momcozy、archive 或 dirty 业务证据。

当前 graph 状态：VR-GRAPH-001 完成初始一致性审计；VR-GRAPH-002/003 的全量基线已完成并经 graph reviewer `approved=true`。在 P4-001、P4-002、P4-003、P4-004 的长期 workflow 文档加入后，当前增量图谱为 `319` files、`1,016` nodes、`2,076` edges、`8` layers、`12`-step tour；两项 deterministic validator 均为 `0` issues，文件集/fingerprint/meta 一致性为 0 差异。`.agents/skills/` 按确认继续排除在项目结构 graph 外。详细证据见 `docs/product/viral-replication-graph-consistency.md`。

## 不在本批范围

RenderJob、真实 video generation、账号、billing、社交发布、winner scoring、causal attribution、独立 Insight Hub、自动 Product Fact promotion，以及任何生产数据迁移。
