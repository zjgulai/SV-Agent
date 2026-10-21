# SV-Agent 项目目录整理方案

状态：SV-ORG-101 已实施，后续门待批准
审计日期：2026-10-21  
实施状态：SV-ORG-000 与 SV-ORG-101 已完成；未执行 checkout、adapter 或 Web 路径搬移

## 结论

SV-Agent 以当前 repository root 为 Git 根，`origin` 指向
`https://github.com/zjgulai/SV-Agent.git`。SV-Agent 不是落在某一个子文件夹里的独立应用；它是
一条跨仓库的 vertical slice：运行代码在 `apps/`，Agent 能力在 `.agents/`，规格和证据在
`docs/` / `outputs/`，确定性工具在 `tools/`，数据库历史在 `migrations/`，公开静态体验在
`sites/`，生成式导航在 `.ua/`。

保留这套顶层结构，不新增 `specs/`、`prompts/`、`plans/`、`build/`、`.claude/` 或第二棵
`SV-Agent/` 门面树。SV-ORG-101 已把 API application implementation 收拢到
`application/sv_agent/` package；调用方盘点没有发现动态导入、entry point 或已声明的仓库外 caller，
因此同批更新全部 imports，不保留旧 flat-module façade。PostgreSQL adapter 与 Web feature 是否继续
收拢，仍分别受后续 ticket 和独立批准门约束。

Git 仓库身份已经是 `SV-Agent`，但本地 checkout 文件夹名尚未与仓库名对齐。这只是物理路径，不应通过在
其中再建一层 `SV-Agent/` 来修正。若要把 checkout 文件夹改名，必须作为独立运维 ticket：先形成
干净提交，停止本地服务，再核对 Codex saved project、IDE、脚本和本地定时验证中的绝对路径，完成改名后
逐一恢复。当前存在依赖该路径的本地验证任务，因此本批不改 checkout 名称。

## 参考结构的准确解读

[Swadesh Kumar 的原帖](https://x.com/swadeshkumar_/status/2112044803244659196)没有要求复制一套
固定目录树。它提出五项仓库能力：

1. 用一个短入口文件说明 purpose、repo map、规则和命令；
2. 把重复工作沉淀为 reusable skills；
3. 用 hooks / automation 固化不能遗忘的 guardrails；
4. 用 `docs/` 提供 progressive context；
5. 在高风险模块附近放 local instruction file。

这些角色在本项目中的等价映射如下：

| 原帖角色 | 本项目权威位置 | 当前判断 |
| --- | --- | --- |
| Repo memory | `README.md`、`AGENTS.md`、`docs/index.md` | 已存在；保持短入口和路由，不再增加 `CLAUDE.md` 副本 |
| Reusable skills | `.agents/skills/` | 已存在；FactFrame 与 Viral Replication skills 已按能力拆分 |
| Workflows | `.agents/workflows/viral-replication/` | 已存在；包含路由、artifact contracts、fixtures 和 forward tests |
| Guardrails | `AGENTS.md`、`.github/workflows/ci.yml`、数据库约束、测试与验证器 | 已存在；不要建立未被任何 runner 执行的装饰性 hooks 目录 |
| Progressive context | `docs/`、`CONTEXT-MAP.md` | 已存在；living docs 与 archive 已分开 |
| Local instructions | 尚未在 SV-Agent 高风险代码目录落地 | 建议在结构稳定后添加少量 scoped `AGENTS.md`，不复制根规则全文 |

因此，参考结构带来的主要缺口不是顶层文件夹，而是：

- SV-Agent application locality 已由 SV-ORG-101 闭合；后续改动必须保持 package Interface 无副作用；
- PostgreSQL models/repositories 分散为三个同前缀文件；
- Web 的 route、feature state 和 CSS 分处两层，页面内部的 feature locality 不够；
- 高风险目录还没有 scoped local guide；
- 当前大量未提交变更不适合同时进行路径搬移。

## 当前实际落点

| 职责 | Canonical location | 当前内容与边界 |
| --- | --- | --- |
| 项目身份与入口 | `README.md`、`AGENTS.md`、`docs/index.md` | 项目目的、任务路由、规则、测试入口 |
| 产品与架构合同 | `docs/product/sv-agent-*.md`、`docs/architecture/`、`docs/adr/0007-*` | Native Agent spec、实施 tickets、运行和授权决策 |
| 领域语言 | `CONTEXT-MAP.md`、`docs/contexts/viral-replication/` | 五个上下文及 Viral Replication 语言 |
| Domain | `apps/api/app/domain/sv_agent/` | Task/Run、planning、reviewing、ToolRun、canonical artifact contracts |
| Application | `apps/api/app/application/sv_agent/` | orchestration、read tools、Task Inbox、Mission Control、Evidence Workspace；package initializer 不导入 implementation |
| HTTP interface | `apps/api/app/api/routes/sv_agent.py`、`apps/api/app/api/schemas/sv_agent.py` | 目前只有只读 SV-Agent HTTP projection 和 browser-local brief 配套契约 |
| PostgreSQL adapter | `apps/api/app/adapters/db/sv_agent_*.py` | models、repository、ToolRun journal adapter |
| Port | `apps/api/app/ports/sv_agent_tool_journal.py` | 已有 ToolRun journal seam；不要为目录美观制造没有第二 adapter 的 port |
| Migration | `migrations/versions/0012_sv_agent_persistence.py` | 13 个 additive `sv_*` 表及不可变/当前头约束的历史事实 |
| Web product | `apps/web/src/routes/*Task*Page.tsx`、`MissionControlPage.tsx`、`EvidenceArtifactsPage.tsx` | Task Inbox、New Task、Mission Control、Evidence & Artifacts 页面 |
| Web feature support | `apps/web/src/features/sv-agent/` | local draft state 与页面 CSS |
| Skills | `.agents/skills/viral-*`、`.agents/skills/factframe-*` | 单一能力 instructions；不是运行时代码 |
| Workflow packs | `.agents/workflows/viral-replication/` | 七类执行路线、shared contracts、fixtures、forward tests |
| Offline compatibility | `tools/viral_replication/`、`tools/viral_replication_oracle/` | canonical validator compatibility export 与确定性 oracle |
| Evidence | `docs/research/`、受控 `outputs/` | 研究证据；不是 PostgreSQL 业务事实源 |
| Public static surface | `sites/viral-replication-workbench/` | 已审核公开静态体验；不是 SV-Agent runtime Web |
| Generated navigation | `.ua/knowledge-graph.json` 等 | 导航与新鲜度；不证明运行、部署或验收 |

## 保留不动的顶层结构

```text
SV-Agent/                         # Git repository root
├── README.md                     # why + human quick start
├── AGENTS.md                     # rules + task routing
├── CONTEXT-MAP.md                # bounded-context map
├── .agents/
│   ├── skills/                   # reusable capability instructions
│   └── workflows/                # executable SOP packs and fixtures
├── .github/workflows/            # executable CI guardrails
├── .ua/                          # generated navigation only
├── apps/                         # deployable API and Web
├── docs/                         # living specs, ADRs, research and archive
├── infra/                        # local/CI infrastructure
├── migrations/                   # append-only database history
├── outputs/                      # scoped evidence; mostly private/ignored
├── sites/                        # reviewed public static surfaces
└── tools/                        # deterministic validators and oracles
```

这棵树已经同时满足 CRAFT 角色和原帖的 why / map / rules / workflows。复制一棵语义相同的目录只会
让 Agent 面对两套 authority，降低而不是提高可导航性。

## 推荐的运行代码目标形状

### API：先收拢 application，保持四层 seam

```text
apps/api/app/
├── domain/sv_agent/              # 已经集中；继续作为纯领域 Module
├── application/sv_agent/         # 推荐新增 package
│   ├── orchestration.py
│   ├── evidence_workspace.py
│   ├── mission_control.py
│   ├── task_inbox.py
│   └── read_tools/
│       ├── contracts.py
│       ├── errors.py
│       ├── execution.py
│       ├── handler.py
│       └── registry.py
├── ports/
│   └── sv_agent_tool_journal.py   # 保持；只有真实可替换 dependency 才增加 port
├── adapters/db/sv_agent/          # 第二阶段、可选
│   ├── models.py
│   ├── repository.py
│   └── tool_run_repository.py
└── api/
    ├── routes/sv_agent.py         # 保持 HTTP interface 的一个入口
    └── schemas/sv_agent.py
```

这个形状选择“小 interface / 最大 locality”：HTTP callers 只知道 `TaskInbox`、`MissionControl`、
`EvidenceArtifactWorkspace` 等 application Interface；read-tool 内部 contracts 不再散在共享 application
目录。Domain、application、port、adapter 和 HTTP interface 仍各自保留，不把它们合并成一个巨型
`agent/` package。

`application/sv_agent/` 的 dependency 主要是 in-process domain rule 与 local PostgreSQL query。
目录移动本身不应顺手引入新的 port。只有 production adapter 与 test/in-memory adapter 都真实存在时，
seam 才值得进入 external Interface。

### Web：feature 内聚，router 保持薄

```text
apps/web/src/
├── features/sv-agent/
│   ├── api/                       # typed client projections, no global re-export forest
│   ├── components/                # shared Agent-only visual primitives
│   ├── pages/                     # four current SV-Agent pages
│   ├── state/                     # bounded browser-local drafts only
│   └── styles/                    # page/feature styles and tokens
└── routes/                        # router adapters; migration后只保留路由装配
```

第一阶段可以继续保留现有 route files，不为“目录整齐”改变行为。若后续页面共享状态、组件和视觉 token
达到稳定复用，再用 `git mv` 把实现移入 feature，并让 route file 只装配/导出页面。临时兼容 facade
必须带删除 ticket，不永久维护双入口。

## Current → Target 映射

| Current | Target | 动作 | 兼容策略 |
| --- | --- | --- | --- |
| `application/sv_agent_orchestration.py` | `application/sv_agent/orchestration.py` | 已完成 `git mv` | 仓库内 callers 已更新；无外部 caller 证据，不保留旧 façade |
| `application/sv_agent_{task_inbox,mission_control,evidence_workspace}.py` | `application/sv_agent/{task_inbox,mission_control,evidence_workspace}.py` | 已完成 `git mv` | HTTP route 与 tests 已同批更新 |
| `application/sv_agent_tool_*.py`、`sv_agent_read_tool_execution.py` | `application/sv_agent/read_tools/` | 已完成 `git mv` | `read_tools/__init__.py` 无副作用；callers 从明确 submodule 导入 |
| `adapters/db/sv_agent_models.py` 等 | `adapters/db/sv_agent/` | 第二阶段可选 move | 保留一版旧 module re-export；migration 不移动 |
| `features/sv-agent/*.css` | `features/sv-agent/styles/` | Web 阶段 move | 页面 import 同批更新 |
| `features/sv-agent/browser*Drafts.ts` | `features/sv-agent/state/` | Web 阶段 move | 不改变 storage key/version |
| SV-Agent route page implementations | `features/sv-agent/pages/` | 达到共享阈值后再 move | `routes/` 暂作 router adapter；稳定后删除 facade |
| `tools/viral_replication/artifact_contracts.py` | 保留原位 | 不移动 | 它是 deployable domain validator 的明确 compatibility export |
| `.agents/skills/viral-*` | 保留原位 | 不移动 | Skill 是能力 Interface，不是 API runtime implementation |
| `.agents/workflows/viral-replication/` | 保留原位 | 不移动 | SOP、fixtures 与 forward tests 是 workflow authority |
| `sites/viral-replication-workbench/` | 保留原位 | 不移动 | Public static artifact 与 runtime Web 必须物理区分 |
| `outputs/*` | 保留各证据根 | 不搬、不批量清理 | ignored 不等于垃圾；需要 provenance-aware 明确授权 |
| `.ua/*` tracked files | 原位重生成 | 不手工搬节点 | 路径变动后完整刷新并校验 |

## 不应移动或合并的内容

- 不把 `.agents/skills/` 放进 `apps/api`。Skill instructions 与 runtime implementation 的 authority 不同。
- 不把 `docs/research/` 或 `outputs/` 放进 PostgreSQL adapter。研究证据不是业务事实。
- 不把 `sites/viral-replication-workbench/` 合并到 `apps/web`。它是审核后的静态发布面，不是当前 Agent UI。
- 不移动既有 migration 文件；数据库历史路径是审计记录。
- 不把 `tools/momcozy_assets/`、`tools/oumomo_experiments/` 合并成通用 Evidence 工具包。它们属于不同上下文。
- 不把 canonical validator 重新移回 `tools/`。可部署权威位于
  `apps/api/app/domain/sv_agent/artifact_contracts.py`，tools 仅兼容导出。
- 不创建全局 `Evidence` 或 `Provider` 万能 package；各上下文的事实语义和权限不相同。
- 不创建 `.claude/` 作为 `.agents/` 的副本。若需要 Claude 兼容入口，应由工具配置指向同一份 authority，
  而不是复制内容。

## Local instruction 文件建议

只在隐藏复杂度足以改变操作规则的目录增加 scoped `AGENTS.md`：

1. `apps/api/app/domain/sv_agent/AGENTS.md`：纯领域、无 SQLAlchemy/FastAPI、artifact 和 Task/Run
   不变量、禁止 private reasoning；
2. `migrations/AGENTS.md`：append-only 历史、只在 disposable database 验证 rollback；
3. `tools/momcozy_assets/AGENTS.md`：Private Gate、只读、禁止真实库进入 CI/图谱；
4. `apps/web/src/features/sv-agent/AGENTS.md`：read-only public surface 与 browser-local draft 边界。

这些文件应链接回根 `AGENTS.md`，只写局部增量，不复制全局规则。它们属于后续独立 ticket，不能和大规模
路径 move 同批落地，否则很难判断是规则变化还是路径变化导致回归。

## 垃圾候选与证据资产的区别

可以在获得精确清理授权后删除的本地生成物：

- `.DS_Store`；
- `**/__pycache__/`；
- `.pytest_cache/`、`.mypy_cache/`、`.ruff_cache/`；
- `apps/api/.venv/`、`apps/web/node_modules/`（可由 lockfile 重建）；
- `.ua/.trash-*`、`.ua/tmp/` 和除约定 scan result 外的 intermediate scratch；
- 非发布目标的临时截图、browser report 与 test output。

不能仅因被 gitignore 就判定为垃圾：

- `outputs/momcozy-content-assets/`；
- `outputs/kleanpal-pro-replication/`；
- `outputs/oumomo-reverse-engineering/` 及 scoring degradation；
- `sites/viral-replication-workbench/dist/`（它是明确跟踪的公开发布 artifact）；
- `.ua/knowledge-graph.json`、`fingerprints.json`、`meta.json` 和 config/ignore contract。

本方案不执行任何删除。

## 分阶段实施 tickets

### SV-ORG-000 — 建立干净迁移基线

- 先审查并提交或明确搁置当前 SV-201～SV-204 的未提交修改；
- 记录 `git status --short --branch` 与完整测试结果；
- 禁止在当前 dirty set 上同时做路径 move，否则无法区分业务改动和 import 回归；
- 验收：迁移批次只有路径/引用/文档/图谱变化，没有行为差异。

### SV-ORG-010 — 本地 checkout 名称对齐（可选）

- 只把仓库根从物理文件夹名 `ai_video` 改为 `SV-Agent`，不创建嵌套目录；
- 先列出并更新 Codex saved project、IDE workspace、本地服务和自动化中的绝对路径引用；
- 与源码目录整理分批执行，避免把环境失联误判为 import 或运行时回归；
- 验收：新路径可打开、Git remote/branch/history 不变，既有本地自动化和验证命令在新路径可读运行。

### SV-ORG-101 — Application locality

状态：已完成（2026-10-21）。

- 新建 `apps/api/app/application/sv_agent/`；
- 用 `git mv` 收拢 orchestration、三类 read projection 与 read-tool implementation；
- 保持 domain、ports、adapters 和 HTTP interface 不动；
- 更新 application/API/test imports；
- 对旧 import 是否保留 compatibility re-export 做调用方盘点；若保留，写明移除版本；
- 验收：接口行为、stable error code、事务 ownership 和 projection byte semantics 不变。

### SV-ORG-102 — PostgreSQL adapter locality（条件式）

- 只有 SV-Agent DB 文件继续增长或出现第二类 caller 时才执行；
- 收拢 `models.py`、`repository.py`、`tool_run_repository.py`；
- 不移动 migration，不改变 metadata registration；
- 不以目录重构为理由增加 hypothetical port；
- 验收：Alembic head、13 张表、triggers、Task CAS、append-only journal 和 replay 不变。

### SV-ORG-201 — Web feature locality

- 先移动 state 和 styles，再决定 pages 是否进入 feature；
- route paths、storage envelope version/key、GET-only 网络边界保持不变；
- 路由 adapter 若保留，必须有删除 ticket；
- 验收：四个页面在 desktop/tablet/mobile 的 navigation、empty/error/loading 与 read-only 行为不变。

### SV-ORG-301 — Scoped local guides

- 按上一节增加四个短 local `AGENTS.md`；
- 每个文件只写局部 invariants、验证命令和禁止事项；
- 根 `AGENTS.md` 与 `docs/index.md` 增加路由，不复制全文；
- 验收：从任一高风险目录进入都能找到唯一上游 authority。

### SV-ORG-401 — Navigation and cleanup

- 更新 `docs/architecture/project-layout.md`、`docs/index.md`、所有相对链接和测试命令；
- 完整重生成 `.ua`，拒绝 dangling/duplicate edges、stale meta 和旧 path fingerprints；
- 仅删除已列明的可重建垃圾，逐类执行，不使用 broad ignored-file clean；
- 验收：源码、文档、图谱和实际 import path 一致。

## 验证清单

每个 move ticket 至少完成：

```bash
rtk git diff --check
rtk uv run --project apps/api ruff check apps/api migrations
rtk uv run --project apps/api python -m mypy apps/api/app
rtk env TEST_DATABASE_URL=postgresql+asyncpg://reverse_engineer_mode:local-development-only@localhost:55432/rem_test uv run --project apps/api python -m pytest apps/api/tests -q
rtk npm --prefix apps/web test -- --run
rtk npm --prefix apps/web run lint
rtk npm --prefix apps/web run typecheck
rtk npm --prefix apps/web run build
```

路径或长期文档变化还必须：

- 重生成 `.ua/knowledge-graph.json`、`fingerprints.json` 和 `meta.json`；
- 比较 graph / fingerprints / meta 的路径集合；
- 验证 dangling edge、duplicate edge、layer 和 tour 问题均为 0；
- 检查所有旧 import、Markdown link、测试命令和 Docker build context；
- 构建 API Docker image，证明新 package 被部署上下文包含。

## Rollback

目录整理不触碰数据库 schema 或持久化数据。每个 ticket 单独提交，rollback 采用反向 `git mv` 和 import
恢复；不使用数据库 downgrade。若兼容 facade 已发布，先恢复 facade，再回退 implementation path，避免
外部 caller 在回退窗口中断裂。图谱始终在代码路径稳定后最后生成；rollback 后重新生成，不能把旧图谱
文件直接覆盖回来。

## 当前冲突边界

初次审计时工作区存在 SV-201～SV-204 未提交实现，因此先由 SV-ORG-000 建立了两个本地基线提交。
SV-ORG-101 随后只执行 application 路径、import、architecture test、测试命令和图谱同步；没有混入行为、
数据库、adapter、Web、垃圾删除、push 或部署变更。当前后续边界仍是 SV-ORG-102、SV-ORG-201、
SV-ORG-301 与 SV-ORG-401，各自需要独立批准和可回滚提交。
