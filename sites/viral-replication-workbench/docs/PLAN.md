# Momcozy 爆款复刻工作台：规划与执行 TODO

## 目标

把项目中已经落地的爆款复刻能力，整理成一个可被业务、创意与工程角色共同使用的入口：

- 用路由器先确定一个 `Primary Replication Mechanism`，避免把多个变量混成“灵感复刻”。
- 用共享技能把参考内容拆解、抽象、事实绑定、合同冻结、媒体完整性检查和实验评估串成一条证据链。
- 用一个可运行的 MVP 生成复刻简报；MVP 只保存浏览器本地草稿，不访问真实私有素材、不调用发布或交易接口。
- 让所有示例都明确标注为演示数据，不把观察、推断或未知误写成产品事实、胜负结论或生产验收。

## Brand Voice / Social Resonance 案例扩展（BV-P1-002 已本地收口）

用户已批准将案例档案从“产品复刻优先”扩展为独立的 `brand_voice_social` 轨道，用于 baby/parenting 社媒内容的品牌声量研究，而不是卖货或产品功效证明。

- 方案权威：[brand-voice-social-case-expansion-spec.md](brand-voice-social-case-expansion-spec.md)
- 本地 ticket frontier：[brand-voice-social-case-expansion-tickets.md](brand-voice-social-case-expansion-tickets.md)
- 单票目录：`docs/tickets/brand-voice-social/`
- 首个案例：既有 maternal TikTok Insight Brief，`proceed_with_limits`、`analysis_only`、`metadata_only`
- 当前 Goal：`01a04462-055e-7571-89ab-f8172a90be1f`；BV-P1-002 已完成本地验证，BV-GATE-001 的本地 preflight 已完成，当前 `awaiting_user_gate`（需案例级外部权利/儿童安全/连接器/行动批准证据）
- 不新增第七种 primary mechanism；品牌声量是目标/案例轨道包装层
- P0 不导入原始儿童媒体、音乐、凭据、私有标识或外部 connector，不自动部署或发布

执行循环已完成本批闭环：读取 Goal → 选择 BV-P1-002 → 接入 BV-002 baby reaction candidate 与 CB-001 Nestlé campaign benchmark → 运行 JSON/静态/浏览器验证 → 更新 ledger 和 frontier。BV-002 保留 `attention-grammar`、intimate-care safety review、metadata-only；CB-001 保留五市场窗口、UGC/boosted 分层与 Brand Lift 设计，但不迁移 lift。遇到来源、权利、儿童安全、连接器或发布门时继续停在 `blocked`/`awaiting_user_gate`。

## 已纳入的能力

### 核心技能

`viral-reference-intake`、`viral-content-decomposition`、`viral-pattern-abstraction`、`viral-replication-contract`、`viral-fact-mapping`、`viral-experiment-evaluation`、`viral-video-deep-insight`，以及六个机制技能：`viral-narrative-transformation`、`viral-proof-demonstration`、`viral-experience-pov`、`viral-attention-grammar`、`viral-conversion-action`、`viral-trend-native`。`viral-media-integrity` 作为跨机制的完整性门，不作为第八个主机制。

本次融合增加四个 `inverse_engineer` 适配技能：`reverse-artifact-calibration`、`reverse-creative-signal-coding`、`reverse-counterexample-holdout`、`reverse-skill-promotion`。它们只描述证据编排与晋级边界，不把 `inverse_engineer` 的 Reverse Core 或 Skill Factory 误报为已上线运行时。

### 工作流包

叙事转化、证明演示、体验 POV、注意力语法、转化动作、趋势原生、媒体完整性。每个复刻只绑定一个主机制；若存在无法拆开的并列主变量，状态必须停在 `primary_mechanism_ambiguous`，拆成两个 Variant。

### 共享产物

`ArtifactSnapshot`（候选上游）→ `ReferenceBundle` → `EvidenceUnit`（候选上游）→ `DecompositionMap` → `PatternHypothesis` → `FactMap` → `ReplicationContract` → `MediaIntegrityRecord` → `Finding/Scorecard`。缺失测量值保持 `unavailable`，不得用 0 代替。

### 融合边界

`inverse_engineer` 当前可贡献的是：公开社媒来源的只读 connector contract、来源/口径校准、`format/theme/hook/cta/platform` 创意信号编码、证据绑定的候选结论、counterexample/holdout/promotion 的治理框架。它当前不提供视频解码、ASR/OCR、镜头切分、音频节奏分析、脚本/分镜生成、渲染或发布；Reverse Core、immutable snapshot、Capability Graph、Workflow IR 与 Skill Release 仍是草稿或未验收能力。网站因此把融合模式标为 `candidate_only`，所有真实连接器都必须先经过 credential / scope / commercial_access / quota preflight。

## 执行 TODO

- [x] 创建独立的 buildless Site 源目录，避免触碰现有脏工作区。
- [x] 完成 Momcozy 品牌化的工作台 UI、机制路由器、技能目录、SOP 说明、证据边界与简报生成器。
- [x] 增加首屏、导航和分享链接三种“使用入口”，让用户可以直接进入复刻工作台。
- [x] 让简报字段、路由答案与草稿状态在浏览器本地保存；提供复制和 JSON 下载。
- [x] 增加融合架构、对象映射、逆向增强复刻模式、证据模式与分阶段执行 TODO。
- [x] 让简报 JSON 带上 `sourceUrl`、`fusionMode`、`evidenceMode` 和 `fusion` 边界字段。
- [x] 增加“案例档案”入口：纳入 KleanPal Pro 主案例与 Oumomo 历史黑盒基线的阶段时间线、视频产物、关键帧、脱敏中间 JSON 与本地完整库边界。
- [x] 补充每个技能的适用场景、进入信号、不适用边界、执行步骤、完成标准、停止条件、常见误读与交接对象；纳入 `viral-video-deep-insight`，使站内技能数与本地目录一致。
- [x] 补充每个工作流的适用场景、识别信号、唯一主变量、不适用边界、关键产物、交接节点与完成判定；保留可展开的最小 SOP 与守门规则。
- [x] 增加独立的“爆款视频深度洞察”页面：用一条公开母婴 TikTok 高表现候选演示 evidence-scoped Insight Brief、13 维度、单变量测试与 Skill 说明。
- [x] 增加 `BV-001` 的 Brand Voice 案例档案、Social Resonance Map、缺失值语义与脱敏 JSON 下载；不抓取评论、不托管原始儿童媒体。
- [x] 增加 `BV-002` baby/parenting social candidate（ARK record/19758）与 `CB-001` Nestlé campaign-awareness benchmark；两条轨道独立展示、不可跨轨道排名。
- [x] 对视频标注 `reference`、`intermediate`、`accepted`、`not-adopted`、`final_screening` 角色，并保留失败候选的停止原因。
- [x] 用本地 Chrome DevTools 验证 BV-002/CB-001 案例切换、Social Resonance/Benchmark panel、JSON 下载入口、桌面/移动端无横向溢出且无 console error；既有产品案例的媒体/摘要验证沿用历史记录。
- [x] 读取 Sites 项目状态，创建一次私有 Site 并保存项目 ID。
- [x] 通过 source helper 推送 `dist/index.html` 与托管清单。
- [x] 使用完整 commit SHA 部署私有版本，轮询到终态。
- [x] 验证部署 URL、静态响应、托管包内容和私有站点状态；不宣称商业批准、生产验收或真实素材验证。
- [ ] 在当前桌面浏览器完成带登录态的远端点击验收（若浏览器连接可用）；本地 HTTP、内联脚本语法、案例媒体元数据和源包校验已通过。
- [ ] 接入只读公开来源适配器（必须先通过 credential / scope / commercial_access / quota preflight）。
- [x] `BV-P1-002` 增加第二个 baby social candidate 与 campaign benchmark lane；保持跨轨道不排名，来源未闭合则停留 candidate/hold。
- [x] `BV-GATE-001` 建立脱敏 `brand-voice-gate-preflight/v1`、planned-use 矩阵和政策基线；用户操作授权只允许准备 preflight，不升级为第三方权利授权。
- [ ] `BV-GATE-001` 收集案例级 rights / child-safety / connector / publish / Brand Lift 证据；未闭合前不得抓取、下载、嵌入、仿拍或发布。
- [ ] 单独建设媒体分析 Domain Pack；未完成前不把“复刻”描述为生成成片。
- [ ] 通过 counterexample、ablation、holdout、fresh-agent 与专家审批后，才允许候选技能晋级为 release。

## 明确不在 MVP 范围

- 不导入或展示 Momcozy 私有资产 Bundle、内部 ID、hash、凭据或 Gate Receipt；案例档案只展示经筛选的本地研究媒体与脱敏摘要，不代表私有资产库或发布授权。
- 不实现真实视频生成、社交发布、广告投放、计费、订单、外部 CTA 跳转或排行榜。
- 不把公开研究报告或示例输入升级为市场份额、因果效果、医疗功效或性能承诺。
- 不覆盖现有应用代码、数据库、迁移和用户未提交的工作区改动。

## 验收标准

1. 访客可以从导航进入工作台、技能、工作流和证据边界四个面板。
2. 路由器对单一“是”答案给出一个主机制；多项“是”明确阻断并提示拆 Variant。
3. 用户可以填写参考内容、目标品牌、平台、市场并生成一份带状态和证据边界的简报。
4. 简报可以复制或下载为 JSON，刷新页面后草稿仍保留在本地。
5. 站点可在私有 Sites URL 打开，部署到终态后再报告 URL。
6. 融合模式明确区分 `ready`、`candidate_only`、`not_evaluated`，且不接触真实私有素材、凭据或外部发布动作。

## 本次验证记录

- `dist/index.html` 的内联 JavaScript 通过 `vm.Script` 语法检查。
- 本地静态服务器返回 HTTP 200，响应内容与源文件一致。
- 本地 Chrome 验证首屏有 4 个工作台入口，`?view=workbench` 分享链接会自动定位到工作台。
- 本地 Chrome/Playwright 验证融合页包含 5 个流程节点、4 个逆向技能、5 个执行 TODO；桌面与移动视口无横向溢出且无 `pageerror`。
- 本地 Chrome/Playwright 验证 `reverse-enhanced` + `public-readonly` 会生成 `viral-replication-brief/v2`，包含 `sourceUrl` / `candidate_only`，刷新后模式仍保留。
- 本地 Chrome/Playwright 验证技能卡可搜索/筛选并展开详细说明（18 张技能卡），工作流卡可展开适用场景与交接信息（8 个工作流包）；桌面与移动视口无横向溢出且无 `pageerror`。
- 本地静态服务器验证 `deep-insight.html` 与入口页均返回 HTTP 200；入口内联 JavaScript 通过 `vm.Script` 语法检查，独立报告包含来源、状态、13 维度、六道媒体门与 Skill 说明。
- Sites source helper 生成了包含 `dist/index.html` 和托管清单的部署包；源 checkout 保持干净。
- Sites 私有部署状态为 `succeeded`；远端匿名 `curl` 返回 403，符合 owner-only 访问边界。
