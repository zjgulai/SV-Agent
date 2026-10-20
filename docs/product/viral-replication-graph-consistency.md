# Viral Replication：Understand 图谱一致性审计

审计批次：`VR-GRAPH-001`
审计日期：2026-09-23
审计性质：先只读 consistency audit，后完成经用户确认的 `VR-GRAPH-002/003` full graph refresh 与 review。

## 初始审计结论

初始审计时，旧 `.ua` 图谱的内部结构在有限 deterministic 检查下没有发现 critical integrity issue，但它不是当时工作树的完整图谱。

初始审计确认的状态：

- 项目处于 `main`，`HEAD=0ace8795300858376d3f21bb8f172963f0149458`，工作区已有大量 tracked/untracked changes。
- 当前 `.ua/meta.json` 和 `.ua/fingerprints.json` 仍对应 `2026-09-15` 的 `262` 文件快照。
- 当前 deterministic scan 发现 `282` 个有效文件，`filteredByIgnore=144`，复杂度为 `large`。
- 旧 fingerprints 和旧 graph 都缺少当前扫描中的 `22` 个文件。
- 这 `22` 个文件由 `19` 个 workflow pack 文件、`docs/contexts/viral-replication/CONTEXT.md`、`docs/product/viral-replication-execution.md` 和 `viral-replication-plan.html` 构成。
- 旧 fingerprints 和旧 graph 额外包含 `.ua/.understandignore`、`.ua/config.json` 两个当前 scanner 不纳入的路径。
- 当前扫描因为 `.ua/.understandignore` 中的规则而不纳入 `.agents/skills/`；本批已确认继续保持该排除策略，让 graph 聚焦项目代码、living docs 和 workflow pack。

## 旧 graph 的有限结构检查

旧 graph 当前包含：

- `929` nodes
- `2,287` edges
- `10` layers
- `12` tour steps

本批只运行了有限 deterministic 检查，结果如下：

- dangling edge：`0`
- duplicate node ID：`0`
- layer 引用不存在 node：`0`
- file-level node 缺失 layer：`0`
- layer 重复分配：`0`
- tour 引用不存在 node：`0`
- orphan nodes：`26`，作为 warning 保留

以上不等于完整 graph reviewer 通过。尚未重新运行 `assemble-reviewer`、`architecture-analyzer`、`tour-builder` 或 `graph-reviewer`。

## Ignore 与执行入口

当前已存在 `.ua/.understandignore`，因此按照 Understand skill 的流程，完整分析前需要先审阅并确认该文件的排除范围。

当前规则明确排除：

- `.agents/skills/`
- `.ua` 图谱产物
- 本地缓存、环境文件、数据库文件和大体积素材目录

本机可找到的 Understand 组件包括：

- `<understand-skill-root>/SKILL.md`
- `scan-project.mjs`
- `extract-import-map.mjs`
- `compute-batches.mjs`
- `merge-batch-graphs.py`
- `build-fingerprints.mjs`

本批在插件根目录和 package manifests 中没有找到可直接调用的完整 `understand` 或 `ua` orchestration CLI；能找到的是 viewer package 的 `understand-anything-viewer`，它负责查看已有 graph，不等于完整分析编排器。

## 已运行的可复核命令

```bash
rtk node <understand-skill-root>/scan-project.mjs \
  . \
  <temporary-output>/scan-result.json \
  --exclude-analysis-data
```

扫描结果：`filesScanned=282`、`filteredByIgnore=144`、`complexity=large`。

扫描输出已移入任务的可恢复临时隔离目录，未纳入 repository。

旧 graph 的有限结构检查使用只读 Python 校验，依据 graph 中的 `nodes`、`edges`、`layers`、`tour` 做引用完整性、重复 ID 和 layer coverage 检查。

## Full graph refresh 结果

用户确认继续排除 `.agents/skills/` 后，已完成 `VR-GRAPH-002` 和 `VR-GRAPH-003`：

- scan：`283` files，`filteredByIgnore=144`，complexity=`large`；
- import map：`321` internal edges；
- semantic batches：`29`，全部生成 fragment；
- assembled graph：`980` nodes、`2,024` edges；
- architecture：`8` 个中文 layers，`287` 个 file-level nodes 恰好覆盖一次；
- guided tour：`12` 步，order 连续且引用有效 node ID；
- inline validator：`0` critical issues、`63` warnings；
- graph reviewer：`approved=true`、`0` critical issues、`50` warnings；
- fingerprints：`283` files；
- meta：`analyzedFiles=283`；
- scan、graph、fingerprints、meta 文件集差异：`0`。

warnings 主要是孤立文档/config 节点和缺少 `documents` 关系的文档节点，不是 dangling edge、duplicate node、layer coverage 或 tour 引用错误。它们作为后续 graph quality backlog 保留。

当前持久产物已经更新：

- `.ua/knowledge-graph.json`
- `.ua/fingerprints.json`
- `.ua/meta.json`

旧版本已备份到：`/tmp/ai_video-graph-backup-20260923/`。

## VR-P4-001 incremental freshness 更新

`VR-P4-001` 新增 workflow、五个 fixture 和两份 forward-test 文档后，已在已验收的 full graph 基线上完成一次增量 freshness 更新：

- deterministic scan：`292` files，`filteredByIgnore=145`，complexity=`large`；
- import map：`321` internal edges；
- 增量语义包：9 个新增 workflow/fixture/forward-test 节点，13 条它们与既有文档的关系边；
- 持久 graph：`989` nodes、`2,037` edges、8 layers、12-step tour；
- file-level layer coverage：`292` 个扫描文件均恰好分配一次；
- inline validator：`0` issues、`62` warnings；
- graph validator：`0` issues、`49` warnings；
- fingerprints 与 meta：均为 `292` files，且 gitCommitHash 与当前 `HEAD` 一致。

这次更新复用此前 full refresh 已验证的 283 文件语义节点，只增量分析 P4 新增的 9 个文件，并重新扫描、解析 imports、恢复 file-set/fingerprint/meta 一致性和运行 graph validators。warnings 仍是孤立或关系稀疏的文档/config 节点，不包含 dangling edge、duplicate ID、file-level layer coverage 或 tour 引用错误。

## VR-P4-002 incremental freshness 更新

`VR-P4-002` 新增 conversion-action workflow、五个 fixture 和两份 forward-test 文档后，已在 P4-001 的已验收图谱基线上完成一次增量 freshness 更新：

- deterministic scan：`301` files，`filteredByIgnore=146`，complexity=`large`；`.agents/skills/` 继续按既有 `.ua/.understandignore` 规则排除。
- import map：`301` entries，`321` internal edges；batch 计算仍为 `29` batches。
- incremental merge：复用原有 `989` nodes / `2,037` edges 的语义基线，新增 `9` 个 file-level nodes 与 `13` 条明确 workflow/fixture/forward-test 关系，输出 `998` nodes、`2,050` edges。
- layers：仍为 `8` 层；`documentation=98`，`tooling-experiments=27`；tour 保持 `12` steps，未引入无锚点新步骤。
- structural validation：`0` dangling edges、`0` duplicate edges；最终 fingerprints 与 meta 均覆盖 `301` files，且 `gitCommitHash` 与当前 `HEAD` 一致。

扫描期间的 `16` 条 warning 都来自工作区原先已删除、但仍由 Git 索引列出的历史路径；它们不属于 P4-002 新增文件，且 scanner 保留其跳过记录。此处的 incremental update 只证明图谱导航与文件集的本地一致性，不证明 workflow 的运行时实现、Promotion 实际生效、外部 action path、媒体、平台表现或 production acceptance。

## VR-P4-003 incremental freshness 更新

`VR-P4-003` 新增 trend-native workflow、五个 fixture 和两份 forward-test 文档后，已在 P4-002 的已验收图谱基线上完成一次增量 freshness 更新：

- deterministic scan：`310` files，`filteredByIgnore=147`，complexity=`large`；`.agents/skills/` 继续按既有 `.ua/.understandignore` 规则排除。
- import map：`310` entries，`321` internal edges；batch 计算仍为 `29` batches。
- incremental merge：复用原有 `998` nodes / `2,050` edges 的语义基线，新增 `9` 个 file-level nodes 与 `13` 条明确 workflow/fixture/forward-test 关系，输出 `1,007` nodes、`2,063` edges。
- layers：仍为 `8` 层；`documentation=102`，`tooling-experiments=32`；tour 保持 `12` steps，未引入无锚点新步骤。
- structural validation：inline validator `0` issues、`62` warnings；file-set validator `0` issues、`49` warnings；warnings 仍是孤立或关系稀疏的既有文档/config 节点，不包含 dangling edge、duplicate ID、file-level layer coverage、import-map 或 tour 引用错误。
- fingerprints 与 meta：均覆盖 `310` files，且 `gitCommitHash` 与当前 `HEAD` 一致；scan、graph、fingerprints、meta 文件集差异为 `0`。

扫描期间保留的 `16` 条 `lstat` warning 都来自工作区原先已删除、仍由 Git 索引记录的历史路径；它们不属于 P4-003 文件。此处的 incremental update 只证明 trend-native 的 workflow/SOP、fixtures、forward tests、执行台账与 HTML 导航被同一文件集追踪；不证明 trend discovery、当前热度、音频/模板授权、平台兼容、template activation、上传、发布、原创审批、媒体质量或 production acceptance。

## VR-P4-004 incremental freshness 更新

`VR-P4-004` 新增跨机制 `07-media-integrity` workflow、五个媒体完整性 fixture 和两份前向测试文档后，已在 P4-003 的已验收图谱基线上完成一次增量 freshness 更新：

- deterministic scan：`319` files，`filteredByIgnore=148`，complexity=`large`；`.agents/skills/` 继续按既有 `.ua/.understandignore` 规则排除。
- import map：`319` entries、`94` 个含 import 文件、`321` internal edges；新加入的 workflow 文档/JSON fixture 不增加代码 import。
- incremental merge：复用 `1,007` nodes / `2,063` edges 的语义基线，新增 `9` 个 file-level nodes 与 `13` 条明确 workflow/fixture/forward-test 关系，输出 `1,016` nodes、`2,076` edges。
- layers：仍为 `8` 层；`documentation=106`，`tooling-experiments=37`；tour 保持 `12` steps，未引入无锚点新步骤。
- structural validation：inline validator `0` issues、`62` warnings；file-set validator `0` issues、`49` warnings；warnings 仍是孤立或关系稀疏的既有文档/config 节点，不包含 dangling edge、duplicate ID、file-level layer coverage、import-map 或 tour 引用错误。
- fingerprints 与 meta：均覆盖 `319` files，且 gitCommitHash 与当前 `HEAD` 一致；scan、graph、fingerprints、meta 文件集差异为 `0`。

扫描期间保留的 `16` 条 `lstat` warning 都来自工作区原先已删除、仍由 Git 索引记录的历史路径；它们不属于 P4-004 文件。此处的 incremental update 只证明 Media Integrity 的 workflow/SOP、fixture、前向复核、执行台账与 HTML 导航被同一文件集追踪；不证明真实 Artifact、技术/ASR/OCR/identity 审核、source/target rights、原创/法律意见、商业批准、平台兼容、账号/上传/发布、live 或 production acceptance。

## 2026-10-21 SV-Agent repository baseline refresh

Agent 项目目录重整与 bounded `SV-104A/B` 纯规划契约完成后，本轮重新执行了 full graph，而不是沿用旧增量结果：

- deterministic scan：`384` files，`filteredByIgnore=269`，complexity=`large`；私有 Momcozy 素材、站点构建副本、`.ua` 分析数据和历史 methodology bundle 继续排除；
- semantic analysis：`35` logical batches、`51` batch files；最终图覆盖 `384/384` 个扫描文件，分析阶段出现但被 scanner 排除的 `.ua` 控制文件节点不进入持久图；
- graph：`1,498` nodes、`2,818` edges，其中 `447` 条 `imports` 与 `10` 条 `tested_by`；
- architecture：`10` layers；`384` 个 canonical 文件节点和 `4` 个 Docker stage service 节点均恰好进入一层；
- tour：`13` steps、`49` 个有效 node references，沿 evidence-first 主线覆盖入口、Product Truth、Task/Run、纯规划、只读工具、workflow、决策投影、Storyboard gate 与验证闭环；
- assembly review：`pass`，`0` issues / `0` warnings；inline structural validator：`0` issues，保留 `64` 个 orphan richness warnings；
- full graph reviewer：`approved` with non-blocking warnings。对 `sv_agent_orchestration.py` 的一处能力夸大摘要已收窄为纯规划/前置条件评估，并明确不持久化 RunPlan、不推进状态、不执行步骤或更新 Evidence Graph；其余 warnings 仅涉及关系丰富度，不构成 dangling edge、文件缺失、层覆盖或 tour 引用错误；
- fingerprints 与 meta 覆盖同一 `384` 文件 source baseline；graph-only artifact commit 不改变该 source baseline。

该 graph 仍只是生成式导航和架构理解产物。它不证明 durable orchestration、授权运行时、部署、发布、真实素材验收、商业批准或 production acceptance。

## 下一 gate

完整刷新前必须完成以下决策和条件：

1. `VR-GRAPH-002/003` 已完成；后续如新增长期文档或路径，必须重新执行对应 freshness gate。
2. `.agents/skills/` 继续排除在项目结构 graph 之外，由 canonical skill discovery 管理。
3. graph reviewer 的 50 条非 critical warnings 可在后续 quality pass 中逐步补齐文档关系，但不阻塞 P4 workflow 设计。

当前状态：`full graph refreshed / graph review approved with non-critical warnings`。

## VR-GRAPH-002 preflight 与完成记录

本批在用户确认保持 `.agents/skills/` 排除后，已执行 deterministic preflight：

- scan：`283` files，`filteredByIgnore=144`，complexity=`large`；
- import map：`321` internal edges；
- semantic batches：`29`；
- 旧 graph 缺失文件：`23`；
- `extract-structure.mjs` 成功分析其中 `22` 个文件；`viral-replication-plan.html` 被 extractor 标记为 skipped；
- 未能进入 29 个 file-analyzer 的 semantic dispatch，因为当前工具环境没有可调用的 file-analyzer/orchestration MCP，且 sub-agent thread quota 已耗尽；
- 已将旧 `.ua` graph、fingerprints、meta、config 和 ignore 备份到 `/tmp/ai_video-graph-backup-20260923/`。

随后已补齐 semantic analysis、architecture、tour、assembly 和 graph reviewer；持久 graph 已在 fingerprint baseline 成功后更新，文件集一致性已通过。
