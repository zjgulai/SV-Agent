# `inverse_engineer` × Momcozy 爆款复刻融合方案

## 结论

`inverse_engineer` 不是视频生成或剪辑引擎。它可为 Momcozy 复刻工作台提供一条更严格的“来源—证据—假设—反例—晋级”治理链；现有 `ai_video` 能力则负责机制路由、事实绑定、复刻合同、媒体完整性和本地简报。两者的安全融合方式是新增适配层，而不是把未验收的 Reverse Core 伪装成可用后端。

## 能力分工

| 能力域 | `inverse_engineer` 可贡献的部分 | Momcozy 工作台承接 | 当前边界 |
| --- | --- | --- | --- |
| 来源接入 | 公开社媒 discover/fetch contract、来源身份、时间窗口、权限与配额 preflight | `ReferenceBundle` 的来源字段与可复现状态 | 本 Site 不调用真实 connector，不保存凭据 |
| 口径校准 | format/theme/hook/CTA/platform 信号；原生指标与跨平台指标分离；缺失值为 unavailable | `DecompositionMap` 与 `PatternHypothesis` 的观察层 | 标签不是因果结论，不从单个爆款推出通用规律 |
| 逆向推理 | Observation → ProposedClaim、Evidence Gap、问题树与反例思路 | `Finding` 的 observed / bounded inference / unknown 三分法 | Reverse Core、immutable snapshot、Capability Graph、Workflow IR 仍未验收 |
| 复刻执行 | 不提供媒体解码、ASR/OCR、镜头/音频分析或渲染 | 六个机制 workflow pack、`ReplicationContract`、`MediaIntegrityRecord` | 需另建媒体分析 Domain Pack，当前不生成成片 |
| 方法晋级 | counterexample、ablation、holdout、fresh-agent、专家审批框架 | 融合 TODO 与候选 Skill 卡 | 未通过全部门禁前只能是 candidate，不得 Skill Release |

## 融合工作流

1. **Scope & Contract**：记录输入种类、目标输出、市场/平台、权限和成功/停止条件。
2. **Snapshot & Provenance**：为公开参考建立不可变来源快照；把用户上传媒体与公开 URL 分开标记。
3. **Calibration**：确认发布时间、统计窗口、分母、平台原生口径、可播放性和 rights；缺口进入 Evidence Gap。
4. **Timed Decomposition**：沿时间线记录 hook、张力、证明、体验、字幕、声音、CTA 和 claim 候选。
5. **Creative Signal Coding**：独立编码 `format/theme/hook/cta/platform`，不把编码结果当作效果因果。
6. **Mechanism Route**：使用现有路由器锁定唯一主机制；并列主机制必须拆成不同 Variant。
7. **Fact Map**：只把 `confirmed` 或 `locked` 的 Momcozy 产品事实绑定到可见 claim。
8. **Replication Contract**：冻结 Control、Variant、唯一 Creative Dimension、预算、stop conditions 和外部动作边界。
9. **Media Integrity**：检查技术、身份连续性、来源范围、原创度与沟通表面；该门不授予发布或商业批准。
10. **Differential / Counterexample / Holdout**：比较 Variant 与 Control，记录反例和不可外推的部分；单一样本不晋级。
11. **Candidate Skill**：只有在 fresh-agent、专家审批和 release gate 完成后，才可形成可复用 Skill。

## Site MVP 的可用范围

- `标准复刻`：使用现有六个机制路由和共享产物链生成本地简报。
- `逆向增强复刻`：在同一简报中增加来源 URL、证据模式、校准/信号/反例/晋级任务，并将融合状态写成 `candidate_only`。
- `演示 / 本地草稿`、`公开只读 · 待适配器`、`私有资产 · 需本地 Gate`、`CI Synthetic Fixture`、`生产验收 · 未开放` 五种证据模式明确分层。
- 所有草稿保存在浏览器 localStorage；不连接外部 API、不导入私有素材、不发布、不计费、不处理订单或排名。

## 分阶段执行 TODO

### P0：证据契约对齐（当前批次完成 UI 表达）

- [x] 在网站展示 `ArtifactSnapshot` / `EvidenceUnit` / `ReferenceBundle` / `Finding` 的候选映射。
- [x] 将融合模式、证据模式和来源 URL 写入 `viral-replication-brief/v2`。
- [ ] 冻结跨仓库字段字典、来源类型、时效和 ACL 语义。

### P1：本地融合工作台（当前批次完成）

- [x] 增加融合架构轨道、状态标签和对象矩阵。
- [x] 增加四个逆向适配技能和一个逆向增强 workflow pack。
- [x] 增加可见的 P0–P4 执行 TODO 与停止条件。
- [x] 完成桌面/移动端本地交互验证。

### P2：只读来源适配器（下一批）

- [ ] 仅允许公开 HTTP/HTTPS 来源；先做 credential、OAuth、scope、commercial access、quota 和 rights preflight。
- [ ] 生成来源快照与 EvidenceUnit；不把 provider payload 直接写成产品事实。
- [ ] 为跨平台指标保留原生口径，禁止没有 normalized contract 的横向比较。

### P3：媒体分析 Domain Pack（独立项目）

- [ ] 设计视频/音频输入与权限边界。
- [ ] 实现 ASR、OCR、镜头切分、音频节奏和视觉信号的可复现产物。
- [ ] 人工确认后再编译脚本/分镜 JSON；渲染和平台适配另行评审。

### P4：评估、晋级与发布（未开放）

- [ ] 建立 counterexample、ablation、holdout、regression 与 fresh-agent acceptance。
- [ ] 专家审批前保持 `candidate_only`；不因 Site 预览、Gate receipt 或公开 CI 绿灯而晋级。
- [ ] 经过独立 release gate 后，才允许把候选 Workflow / Skill 纳入正式目录。

## 验收口径

本方案的“完成”仅表示融合信息架构、MVP 表单和边界已落地并通过本地静态/浏览器验证；不表示 `inverse_engineer` 的 Reverse Core 已实现，不表示真实来源连接器、视频处理、生成、发布或生产验收已经可用。
