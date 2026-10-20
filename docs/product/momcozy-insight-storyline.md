# Momcozy Insight Storyline

## North star

Momcozy 是首要 Brand Workspace，FactFrame 仍是平台身份。故事线服务产品、品牌策略和 Creative Ops：它要说明“我们知道什么、凭什么知道、能够安全做什么、下一步应花什么成本验证”，而不是生成一份看起来完整但无法复核的营销报告。

## Story arc

### 1. Observe the signal

从有界商品来源、现有素材库、渠道需求、Content Performance Observation 或 clean-room 实验提出一个明确问题。记录 subject、时间窗、平台、配置和缺失数据；热度与排名只能产生 Creative Signal，不能自动成为偏好或因果结论。

**Decision:** 是否有足够信息建立一个可检验假设？

### 2. Establish product truth

将 Momcozy 商品观察固化为 Product Snapshot，并把候选声明拆成 Product Fact。只有 confirmed/locked facts 可以进入可接受声明；rejected 或显式 excluded facts 构成 deny-set。

**Decision:** 哪些商品主张可以安全进入脚本，哪些必须阻断？

### 3. Compile the creative hypothesis

将外部 Content Direction 拆成明确的 relief transformation、visible proof、POV/ASMR 等实验维度，再用 Creative Pattern 冻结时长、阶段、镜头角色、受众 profile 和 Promotion Fact 位置。创意差异必须由版本化合同表达，而不是依靠排名或无法比较的自由 prompt。

**Decision:** 本轮到底在测试结构、受众、促销还是素材表达？

### 4. Execute and validate

Job/Outbox/Worker 提供可恢复执行历史；Provider 只控制 fact-bound voiceover/caption，server-owned fields 在落库前覆盖并验证。失败必须区分 delivery、provider、validation 和 business terminal state。

**Decision:** 结果是否真实完成、可重放、事实可接受？

### 5. Review before media spend

可接受 Script Version 进入 Storyboard preflight、冻结 Storyboard 和本地 approval。Preview 只生成 typed shot cards/image indexes，不产生视频，也不授予发布许可。

**Decision:** 是否值得进入下一次付费素材实验？

### 6. Learn from experiments and assets

Oumomo evidence 回答外部能力、成本和失败边界；Momcozy Asset Bundle 回答具体素材的 provenance、QA 和复用状态。两者通过 insight card 反馈 roadmap，但不改变 Product Fact。

**Decision:** ship、revise、collect more evidence，还是 stop？

## Current Momcozy evidence baseline

- 本地 validator 当前确认 244 个结构有效 Asset Bundles。
- Batch E-A 记录 12 个完成任务，其中 10 张图片通过内部选择 QA，2 个视频为 `revision-needed`；其报告在该批次结束时保留 396 credits。
- 后续 Batch F 记录 198 张图片、396 → 0 的连续账务，并把全库计数推进到 244 bundles。
- Batch F 的逐文件 QA 仍为 `hold`，代表结构和抽样基线已通过，不代表 198 张素材获得商业批准。
- 本地 Aggregate Index 已覆盖 244/244 个 Bundle，并可靠报告 QA disposition；Batch metadata 为 235/244、Channel 12/244、Concept Group 198/244。缺失项保持 unknown，且全部独立 Commercial Approval 仍不可用。

## Example decision narrative

```text
Question
  Which Momcozy M5 visual concepts are ready for PDP candidate review?

Observed
  244 bundles validate structurally.
  Batch F contains explicit PDP concept groups and per-bundle provenance/QA.

Inference
  The archive is operationally reusable for candidate selection.

Unknown
  Channel/Concept Group coverage and per-file Commercial Approval remain incomplete.

Action
  Use the Aggregate Index to identify evidence-complete PDP candidates, then run brand review per file.

Guardrail
  Do not publish any `hold` asset or convert generated wording into a Product Fact.
```

## Leap performance evidence closure

The public LeapAI report body and getter-only structured payload were audited for `momcozy-德国-奶瓶清洗暖奶器`, covering 2026-08-21 through 2026-08-27:

- 22 videos produced 10,312 views and 37 likes across Instagram, TikTok and YouTube;
- YouTube contributed 5,290 views from 6 videos, TikTok 4,115 from 9 and Instagram 907 from 7;
- the Top 10 contributed 8,878 views, or 86.09% of the observed total;
- the strongest overlapping Creative Signals were manual-to-automation relief, visible performance proof and POV/ASMR embodiment;
- the source did not disclose collection, deduplication, ranking, paid/organic, snapshot or AI review methods.

The integration rule is now closed:

| External observation | Evidence level | Project capability | Disposition |
|---|---|---|---|
| Windowed platform/video totals | Direct report payload | Content Performance Observation | Cite with source/window and missing-value caveat |
| Top 10 ordering and concentration | Direct report ranking; formula unknown | Creative Signal backlog | Test; do not install as a default |
| Content Direction and key takeaway | AI-derived interpretation | Creative Pattern hypothesis | Recompile into controlled dimensions |
| Core selling point | Reported Product Claim | Product Fact allow/deny gate | Require confirmed/locked match or reject |
| Hook/Clip/CTA and visual fields | AI-derived structured output | Script/Storyboard candidate | Validate language, units, completeness and evidence |

Subject identity remains a first-class gate. The Leap slice describes a Germany bottle-washer/warmer subject, while the private M5 Aggregate Index describes a wearable-pump asset workspace. They may coexist in the Momcozy Brand Workspace storyline, but they cannot support the same Product Snapshot, Model or Variant decision through a brand-name join. Until canonical Product Family/Model/Variant identity exists, a separate reviewed binding registry may select a Performance package by frozen Snapshot id + recomputed canonical digest + evidence context only as source-scoped hypothesis context; that selection does not prove target identity equivalence.

This produces the fused storyline:

```text
Leap observation and video decomposition
  → FactFrame claim gate
  → versioned creative hypothesis
  → Oumomo reproducible experiment
  → Momcozy Asset Bundle and Storyboard review
  → ship / revise / collect / stop
```

The bounded source and detailed limitations are recorded in [LeapAI Public Report Evidence](../research/leap/public-report-evidence.md).

## Selected product projection

The first productized story shape is a read-only Decision Brief inside the existing Creative Comparison Lab, not a standalone KPI dashboard:

```text
Question
  Are these two immutable candidates reviewable under the same fact contract?

Observation
  Exact, windowed values from an explicitly bound reviewed package.

Inference
  A named Creative Signal with a test/recompute/cite/reject disposition.

Unknown
  Missing method, source ambiguity, identity mismatch, experiment evidence or Commercial Approval.

Action
  revise / collect evidence / test / stop

Guardrail
  No ranking, external claim or generated asset becomes Product Fact or publication permission.
```

The complete schema, permission, UX and rollback design is in [Insight & Performance Decision Brief Projection Design](insight-performance-projection-design.md). Current runtime evidence remains unavailable.
