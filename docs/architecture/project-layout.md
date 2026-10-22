# SV-Agent Project Layout

Status: current repository contract
Last reviewed: 2026-10-21

## 结论

SV-Agent 采用 CRAFT 启发的 Agent 项目组织方式，但不复制一套空壳目录。项目把“稳定的人类约束、证据、Agent 指令、执行计划和可运行产物”分开，同时保留现有 Python、React、Alembic、CI 和部署路径，避免仅为改名破坏 imports、测试和历史链接。

参考模型来自 [rekallai/craft](https://github.com/rekallai/craft)：`specs/`、`references/`、`prompts/`、`plans/` 和 `build/` 分别承载规格、参考资料、可复用提示、执行计划和构建产物。本项目使用下表中的现有目录表达同样的职责。

## 目录职责

| CRAFT 角色 | SV-Agent 目录 | 这里放什么 | 不放什么 |
| --- | --- | --- | --- |
| Agent guide | `AGENTS.md`, `README.md`, `docs/index.md` | 入口、不可变规则、任务路由 | 运行事实、私有凭据 |
| Specs | `docs/product/`, `docs/architecture/`, `docs/contexts/`, `docs/adr/`, `docs/decisions/` | 产品合同、架构、领域语言、长期决策 | 任务流水账、生成媒体 |
| References | `docs/research/`, 受控的 `outputs/` | 有来源、主体、时间窗和限制的研究证据 | PostgreSQL 业务事实、私有素材全文 |
| Prompts | `.agents/skills/`, `.agents/workflows/` | 可发现的 Skills、SOP、路由和验证脚本 | 动态下载插件、隐藏推理 |
| Plans | `docs/product/*tickets*.md`, `docs/product/roadmap.md`, `docs/archive/implementation-plans/` | 当前票据与路线图；已完成或停止的历史计划 | 把历史计划当当前权限 |
| Build | `apps/`, `tools/`, `migrations/`, `infra/`, `sites/` | API、Web、确定性工具、schema、运行环境、公开站点 | 私有素材库和本地托管绑定 |
| Generated navigation | `.ua/knowledge-graph.json`、`.ua/fingerprints.json`、`.ua/meta.json`、`.ua/config.json`、`.ua/.understandignore` | 能力图谱、指纹、元数据、配置和扫描边界 | `.ua/intermediate/`、`.ua/tmp/`、`.ua/.trash-*`、验收结论 |

## 顶层结构

```text
SV-Agent/
├── AGENTS.md                 # Agent 的安全规则和任务路由
├── CONTEXT-MAP.md            # 领域上下文地图
├── .agents/                  # Skills 与可执行 workflow packs
├── .github/                  # 公开 CI
├── .ua/                      # 受控的生成式能力导航
├── apps/                     # FastAPI 和 React 产品运行时
├── docs/                     # living specs、research、reports 与 archive
├── infra/                    # 本地/CI 基础设施定义
├── migrations/               # PostgreSQL schema 历史
├── outputs/                  # 明确允许跟踪的证据台账；多数私有输出被忽略
├── sites/                    # 经审查的公开静态体验
└── tools/                    # 确定性验证器、资产门与 workflow oracle
```

## SV-Agent 当前局部结构

- API application implementation 已收拢到 `apps/api/app/application/sv_agent/`，调用方从明确 submodule 导入。
- Web browser-local state 在 `apps/web/src/features/sv-agent/state/`，feature styles 在 `apps/web/src/features/sv-agent/styles/`。
- 五个 page implementation 仍保留在 `apps/web/src/routes/`；只有共享层稳定并建立删除 ticket 后才继续移动。
- Domain、migration、Momcozy asset tools 与 Web feature 各有短 scoped `AGENTS.md`，它们只增加局部规则。

## Agent 进入路径

1. 从 `AGENTS.md` 和 `docs/index.md` 确认权限、事实源和相关文档。
2. 用 `CONTEXT-MAP.md` 选择领域语言，再读对应 living spec 或 ADR。
3. 通过 `.agents/workflows/` 选择工作流，并由 `.agents/skills/` 执行单一能力。
4. 对 `apps/`、`tools/` 或 `sites/` 做最小实现；迁移只进入 `migrations/`。
5. 按 `docs/development/testing.md` 验证；路径或长期文档变化后刷新 `.ua/`。

## 不可破坏的边界

- PostgreSQL 仍是唯一业务事实源；文档、研究输出、站点和能力图谱都不能替代它。
- `.agents/` 描述 Agent 如何工作，不授予 render、publish、rights、commercial 或 production 权限。
- `outputs/momcozy-content-assets/` 是本地 Private Gate，不进入公开仓库。
- `sites/viral-replication-workbench/` 只包含经筛选的公开静态内容；本地 `.openai/hosting.json` 不纳入版本控制。
- `docs/archive/` 保存历史，不是当前 TODO；产品能力状态以 `docs/product/sv-agent-implementation-tickets.md` 为准，目录整理状态以 `docs/architecture/sv-agent-project-layout-proposal.md` 为准。
- 不建立重复的 `specs/`、`references/`、`prompts/`、`plans/` 或 `build/` 门面目录。需要调整职责时，先更新本文件、`docs/index.md` 和相关测试。
