# 爆款视频深度洞察 · Insight Brief 输出模板

> 使用说明：复制本模板后逐项填写。方括号内容是待填字段，不是事实。指标层遵循项目
> `MeasurementState`：`observed` 时另填数值（`0` 是合法观测），其他状态用 `null`；
> `unavailable` 只用于 section/gate，不作为指标层状态。标题建议使用“[平台/窗口] 高表现候选洞察”，
> 只有在正文中明确范围时才使用“爆款”一词。

---

## 0. 文档控制卡

| 字段 | 值 |
|---|---|
| `schema_version` | `viral-video-deep-insight-v1` |
| `brief_id` | `[稳定 ID，不含隐私/凭据]` |
| `status` | `blocked` / `proceed_with_limits` / `ready_for_next_gate` |
| `action` | `revise` / `collect_evidence` / `test` / `hold` / `stop` |
| `prepared_at` | `[ISO-8601]` |
| `prepared_by` | `[角色或工具，不写私有推理]` |
| `evidence_level` | `Fact` / `Inference` / `Unknown`（结论证据强度） |
| `proof_level` | `local` / `CI` / `private` / `deployment` / `live` / `production`（验证层级） |
| `proof_boundary` | `[这份 brief 证明什么，不证明什么]` |

### 一句话结论

> 在 `[subject + platform + market + window]` 内，来源显示 `[直接观察]`；这只支持一个
> `[primary_mechanism]` 的 Creative Signal，当前最安全的动作是 `[action]`，因为 `[最大未知/门禁]`。

### 不可作出的结论

- `[例如：不能称为普遍 winner、不能声称 causal lift、不能证明权利或 production acceptance]`
- `[第二条]`

---

## 1. Decision Question：这份分析要帮助谁决定什么

**决策问题**

`[例如：是否值得为美国市场的 KleanPal Pro 设计一轮只改变 attention component 的对照测试？]`

**决策对象与时间约束**

- 决策人/团队：`[role]`
- 决策截止：`[date or unknown]`
- 可接受成本/风险：`[budget, rights, platform, time]`
- 不在本次决定内：`[render/publish/billing/production 等]`

---

## 2. Scope Card：主体、窗口、来源和复现性

### 2.1 Performance Subject Binding

| 字段 | 值 | binding state |
|---|---|---|
| Brand | `[brand]` | `[workspace context]` |
| Market / locale | `[market/locale]` | `[exact / unknown]` |
| Product Family | `[family]` | `exact_snapshot` / `reviewed_family_context` / `unresolved` / `conflict` |
| Model | `[model]` | `[value or unknown]` |
| Variant / SKU | `[variant/SKU]` | `[value or unknown]` |
| Target Product Snapshot | `[snapshot id + digest]` | `bound` / `not_bound` / `not_applicable` |

**整体 `SubjectRelation`**：`exact_snapshot` / `reviewed_snapshot_selection` /
`reviewed_family_context` / `unresolved` / `conflict`

> 规则：品牌、标题、类别或账号相似不构成 exact binding。若只能 source-scoped，必须在
> 结论和 guardrail 中重复说明，不能把外部表现自动绑定到目标商品。

### 2.2 Performance Window

| 字段 | 值 |
|---|---|
| Platform | `[TikTok / Instagram / YouTube / other]` |
| Observation window | `[start → end, timezone if known]` |
| Capture time | `[ISO-8601]` |
| Source locator | `[public locator or internal reference name; no private URL in public brief]` |
| Source digest / package digest | `[digest or unknown]` |
| Reference media digest | `[digest or not_applicable]` |
| Playability | `playable` / `unavailable` / `source_ambiguous` |
| Refreshability | `reproducible` / `unstable` / `not_tested` |
| Rights / authorization | `confirmed` / `restricted` / `unknown` |
| Collection / ranking method | `[observed / not disclosed / unknown]` |
| Paid / organic | `[observed / mixed / unknown]` |

### 2.3 Source register

| `source_ref` | Source kind | What it proves | Precision / limitations | Digest |
|---|---|---|---|---|
| `SRC-01` | `[report payload / post / local artifact / test]` | `[bounded statement]` | `[limits]` | `[hash or unknown]` |
| `SRC-02` |  |  |  |  |

---

## 3. Executive Signal：直接观察、信号与反转

### 3.1 Observed facts

| `observation_id` | 直接观察 | `source_ref` | Availability | 分母/口径 |
|---|---|---|---|---|
| `OBS-01` | `[exact value or timed observation]` | `SRC-01` | `observed` / `missing` / `unknown` / `not_reported` / `not_collected` / `not_applicable` / `redacted` / `source_ambiguous` | `[denominator/precision; observed value 0 remains 0]` |
| `OBS-02` |  |  |  |  |

### 3.2 Creative Signal（有限推断）

| `inference_id` | Bounded inference | 依据观察 | Disposition | 替代解释 |
|---|---|---|---|---|
| `INF-01` | `[可能通过何种功能降低何种摩擦]` | `OBS-01, OBS-02` | `cite` / `recompute` / `test` / `reject` | `[至少一个可证伪替代解释]` |

**最强信号**：`[一句话，不写 winner/causal]`

**最容易误读的表象**：`[例如 Top 10 集中度、账号总量、可播放、AI 摘要]`

**反转解释**：`[为什么该表象也可能由分发、口径、样本或身份造成]`

---

## 4. 时间化 Decomposition Map：内容到底怎样组织

没有发生的段落明确写 `not_present`；无法观察写 `unavailable`（字段/section availability）。每一行必须有时间范围、
source ref、surface availability 和“观察到的功能”，不能直接写效果。

| Beat | 时间范围 | Observation | Visual / Audio / Text grammar | 可观察功能 | Claim candidates | Source / availability |
|---|---|---|---|---|---|---|
| Hook | `[s–s]` |  |  | `[承诺/问题/信息缺口]` | `[ids or none]` |  |
| Pain / Tension | `[s–s]` / `not_present` |  |  |  |  |  |
| Intervention | `[s–s]` |  |  |  |  |  |
| Proof | `[s–s]` / `not_present` |  |  | `[现象，不写功效]` |  |  |
| Experience | `[s–s]` / `not_present` |  |  | `[POV/ASMR/动作连续性]` |  |  |
| Result | `[s–s]` / `not_present` |  |  | `[可见状态]` |  |  |
| CTA | `[s–s]` / `not_present` |  |  | `[邀请/行动路径]` |  |  |

### Attention grammar（仅表达观察）

| Component | Observation / time anchor | Status | 不可直接推出 |
|---|---|---|---|
| `hook_trigger` |  | `observed` / `unknown` / `not_present` | retention / views |
| `reveal_cadence` |  |  |  |
| `caption_cadence` |  |  |  |
| `visual_contrast` |  |  |  |
| `sonic_timing` |  |  |  |

### Proof device（如适用）

```text
input: [输入]
operation: [操作]
observed_phenomenon: [直接可见/可测现象]
allowed_conclusion: [允许的有限结论]
not_allowed: [efficacy/safety/medical/comparative claims not supported]
```

---

## 5. Why Might It Spread：假设矩阵

每一行必须同时填 Observation、Inference、Alternative、Falsifier/Test。没有证据就写 unknown，
不要靠“行业常识”补齐。

| Dimension key | Observation | Bounded inference | Alternative explanation | Falsifier / smallest test | Evidence state | Transferability |
|---|---|---|---|---|---|---|
| `source_context` |  |  |  |  |  |  |
| `performance_signal` |  |  |  |  |  |  |
| `audience_tension` |  |  |  |  |  |  |
| `attention_grammar` |  |  |  |  |  |  |
| `narrative_transformation` |  |  |  |  |  |  |
| `proof_demonstration` |  |  |  |  |  |  |
| `experience_pov` |  |  |  |  |  |  |
| `conversion_action` |  |  |  |  |  |  |
| `trend_native` |  |  |  |  |  |  |
| `product_truth` |  |  |  |  |  |  |
| `surface_originality` |  |  |  |  |  |  |
| `experimentability` |  |  |  |  |  |  |
| `media_integrity` |  |  |  |  |  |  |

> 反直觉审计至少选择三条并写在此表或附录：高播放≠因果、集中度≠贡献、CTA≠转化主机制、
> 标签/音频≠trend-native、物理演示≠功效、体验≠省时/疗效、品牌相似≠subject binding、
> 技术通过≠权利/发布、缺失≠0、n=1≠winner。

---

## 6. Primary Mechanism 与 Pattern Hypothesis

### 6.1 路由决定

- `primary_mechanism`：`narrative-transformation` / `proof-demonstration` /
  `experience-pov` / `attention-grammar` / `conversion-action` / `trend-native`
- 路由理由：`[哪一个可观察关系决定主要表达]`
- `secondary_mechanisms`：`[冻结的次级上下文]`
- 若无法拆分：`blocked: primary_mechanism_ambiguous`，并说明需拆的两个 Variant。

### 6.2 PatternHypothesis

**Observed presentation**：`[不带因果的观察句]`

**Invariant elements（功能）**

- `[功能 1 + source/time ref]`
- `[功能 2]`

**Replaceable elements（目标替换）**

- `[人物/场景/文案/声音/道具/目标素材]`

**Prohibited surface copy**

- `[原人物、原音乐、逐镜构图、品牌识别、未授权模板/素材、未证实 claim]`

**Unknowns**

- `[未能观察或无法绑定的字段]`

**Evidence scope**：`[local observation / reviewed package / experiment / other]`

---

## 7. Product Truth 与 Claim Register

每个 voiceover、caption、title、tag、OCR、视觉暗示、动作、CTA 和 Promotion 都要列出。参考片
的台词和 AI selling point 只能标为 `reported_product_claim`，不能直接成为目标事实。

| `claim_id` | 表面/时间 | Claim text or visual implication | Source | Snapshot | Fact ID | Target Fact state | Source disposition |
|---|---|---|---|---|---|---|---|
| `CLM-01` | `[VO/caption/OCR/visual/action/title/tag/promo]` |  |  |  |  | `confirmed` / `locked` / `unsupported` / `excluded` / `unknown` / `not_a_product_claim` | `exact` / `approved_paraphrase` / `reported_product_claim` / `ambiguous` / `expired_promotion` / `reject` / `collect_evidence` |

**Deny-set check**：

- selected Fact IDs：`[ordered list]`
- excluded Fact IDs：`[ordered list]`
- excluded resurrection count：`[0 or blocker]`
- Promotion Fact：`[独立 ID、市场、货币、有效期、value digest；没有则 null]`
- Fact mapping reviewer / timestamp：`[value]`

---

## 8. Adaptation Delta 与复刻合同草案

### 8.1 Control / Variant

| 字段 | Control | Variant | 是否冻结 |
|---|---|---|---|
| Product Snapshot / Facts |  |  |  |
| Platform / Market / Language |  |  |  |
| Duration / Pattern / shot budget |  |  |  |
| Provider / Model / Version |  |  |  |
| Target assets / sound policy |  |  |  |
| Rights / source-use scope |  |  |  |
| Budget / repeat count |  |  |  |
| **唯一 changed_creative_dimension** | `same` | `[only changed field]` | **否** |

**Contract/config digest**：`[digest or not frozen]`

**Stop conditions**：`[contract drift / unsupported claim / rights / terminal / ledger / media gate]`

**Expected observation**：`[预注册，不写保证]`

**Result semantics**：`[指标、分母、availability、最小样本、停止规则]`

若存在两个以上未批准差异，状态必须是 `blocked`，不能解释为 causal 或 winner。

---

## 9. Integrity & Readiness Scorecard

每门独立填写，不得用一门的通过替代另一门。

| Gate | State | Evidence / source | Blocker / limitation |
|---|---|---|---|
| Reference stability | `observed` / `unknown` / `blocked` / `unavailable` |  |  |
| Product truth | `preflight_evidence_collected` / `blocked` / `unavailable` |  |  |
| Contract isolation | `preflight_evidence_collected` / `blocked` / `unavailable` |  |  |
| Execution / terminal / ledger | `preflight_evidence_collected` / `blocked` / `unavailable` |  |  |
| Artifact traceability | `not_applicable_pending_artifact` / `blocked` / `unavailable` / `ready_for_next_gate` |  |  |
| Technical profile | `not_applicable_pending_artifact` / `blocked` / `unavailable` / `ready_for_next_gate` |  |  |
| Communicative surface / ASR / OCR | `preflight_evidence_collected` / `evidence_collected_pending_artifact_review` / `blocked` / `unavailable` |  |  |
| Target identity continuity | `preflight_evidence_collected` / `evidence_collected_pending_artifact_review` / `blocked` / `unavailable` |  |  |
| Source-use scope | `evidence_collected_for_internal_analysis_only` / `blocked` / `unavailable` |  |  |
| Originality delta | `evidence_collected_pending_artifact_review` / `blocked` / `unavailable` |  |  |
| Commercial / rights / platform / publish | `separate gate` |  |  |

**Proof-level statement**：

`[本报告只到 local / CI / private / deployment / live / production 的哪一层；较低层级不升级较高层级]`

---

## 10. Decision Brief：观察、推断、未知、行动、护栏

### Observations

- `OBS-…` `[带 source ref、窗口、availability]`

### Bounded inferences

- `INF-…` `[明确是 hypothesis/Creative Signal，带 supporting observations 和 disposition]`

### Unknowns

- `[缺失的方法、主体、时间、样本、事实、权利、平台或媒体字段]`

### Anomalies

- `[口径冲突、语言/单位错误、结构缺失、技术与事实不一致]`

### Next action

`[revise | collect_evidence | test | hold | stop]`

**动作理由**：`[最小可逆动作与预期证据]`

### Guardrails

- `[不能说什么]`
- `[必须先通过什么门]`
- `[哪些字段冻结，哪些变化会使本 brief 失效]`

### Limitations

- `[样本、平台、时间、方法披露、测量、权利、身份、媒体或模型限制]`

---

## 11. 交付前验收清单

- [ ] `Question`、subject、window、source digest 都可回指。
- [ ] Performance Subject Binding 不是 brand-only/fuzzy join。
- [ ] 指标层使用 `observed` + 数值 0 表示 observed zero；与 not reported/not collected/source ambiguous 分开；section/gate 才使用 unavailable。
- [ ] 时间化 DecompositionMap 能重建主机制；缺失段落显式 `not_present`。
- [ ] 只有一个 primary mechanism；不可分离时已 blocked。
- [ ] 每个“为什么”都有替代解释与 falsifier/test。
- [ ] PatternHypothesis 区分 invariant、replaceable、prohibited、unknown。
- [ ] Product claim 全部回到同一 Snapshot 的 confirmed/locked Fact；excluded resurrection=0。
- [ ] Control/Variant 只有一个 changed dimension，digest 和停止条件已写。
- [ ] 六道 Media Integrity gate、rights、source-use、originality 独立呈现。
- [ ] action 只使用五个允许值，proof level 未升级。
- [ ] 未写入私有推理、凭据、cookie、raw full webpage 或私有 URL。

---

## 12. 机器交接最小 JSON（可选）

需要被脚本校验或交接给下一个 workflow 时，使用以下字段语义。完整内容仍以本模板为人读
版本；JSON 不应包含 raw page、凭据、私有路径或模型私有推理。

```json
{
  "schema_version": "viral-video-deep-insight-v1",
  "status": "proceed_with_limits",
  "action": "test",
  "decision_question": "",
  "evidence_level": "Inference",
  "proof_level": "local",
  "subject": {
    "brand": "",
    "market": "",
    "product_family": "",
    "model": "",
    "variant": "",
    "binding_state": "exact_snapshot"
  },
  "performance_window": {
    "platform": "",
    "start": "",
    "end": "",
    "source_ref": "",
    "source_digest": ""
  },
  "observations": [
    {
      "id": "OBS-01",
      "text": "",
      "source_ref": "SRC-01",
      "availability": "observed",
      "value": 0
    }
  ],
  "inferences": [
    {
      "id": "INF-01",
      "text": "",
      "supporting_observation_ids": ["OBS-01"],
      "disposition": "test",
      "alternative_explanation": ""
    }
  ],
  "primary_mechanism": "experience-pov",
  "media_gates": [
    {"key": "artifact_traceability", "state": "not_applicable_pending_artifact", "evidence": ""},
    {"key": "technical_profile", "state": "not_applicable_pending_artifact", "evidence": ""},
    {"key": "communicative_surface", "state": "preflight_evidence_collected", "evidence": ""},
    {"key": "target_identity_continuity", "state": "preflight_evidence_collected", "evidence": ""},
    {"key": "source_use_scope", "state": "evidence_collected_pending_artifact_review", "evidence": ""},
    {"key": "originality_delta", "state": "evidence_collected_pending_artifact_review", "evidence": ""}
  ],
  "dimensions": [
    {"key": "source_context", "evidence_state": "observed", "transferability": "context_bound", "next_test": ""},
    {"key": "performance_signal", "evidence_state": "observed", "transferability": "context_bound", "next_test": ""},
    {"key": "audience_tension", "evidence_state": "unknown", "transferability": "unknown", "next_test": ""},
    {"key": "attention_grammar", "evidence_state": "unknown", "transferability": "unknown", "next_test": ""},
    {"key": "narrative_transformation", "evidence_state": "unknown", "transferability": "unknown", "next_test": ""},
    {"key": "proof_demonstration", "evidence_state": "unknown", "transferability": "unknown", "next_test": ""},
    {"key": "experience_pov", "evidence_state": "observed", "transferability": "portable_function", "next_test": ""},
    {"key": "conversion_action", "evidence_state": "unknown", "transferability": "unknown", "next_test": ""},
    {"key": "trend_native", "evidence_state": "unknown", "transferability": "unknown", "next_test": ""},
    {"key": "product_truth", "evidence_state": "unknown", "transferability": "unknown", "next_test": ""},
    {"key": "surface_originality", "evidence_state": "unknown", "transferability": "surface_bound", "next_test": ""},
    {"key": "experimentability", "evidence_state": "inferred", "transferability": "portable_function", "next_test": ""},
    {"key": "media_integrity", "evidence_state": "unknown", "transferability": "context_bound", "next_test": ""}
  ],
  "claims": [
    {
      "id": "CLM-01",
      "state": "confirmed",
      "fact_id": "",
      "snapshot_id": "",
      "source_ref": "SRC-01",
      "source_disposition": "exact"
    }
  ],
  "changed_creative_dimension": "",
  "unknowns": [],
  "guardrails": [],
  "source_refs": ["SRC-01"],
  "limitations": []
}
```

机器交接时必须完整提供上面列出的 13 个 `dimensions` 和 6 个 `media_gates`；示例中的空字符串
是待填值。`media_gates.state` 采用 `viral-media-integrity` 的原始状态，不把 `pass` 当成通用
通过：`not_applicable_pending_artifact`、`preflight_evidence_collected`、
`evidence_collected_pending_artifact_review`、`blocked`、`unavailable` 或 `ready_for_next_gate`。
