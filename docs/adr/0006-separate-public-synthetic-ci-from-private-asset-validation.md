---
status: accepted
---

# 公开合成 CI 与私有资产验证物理隔离

Momcozy 真实素材库包含 gitignored 商业媒体与本地证据，不能交给公开仓库的 runner、cache 或 artifact。公开 GitHub-hosted CI 因此只执行可提交的 Synthetic Fixtures 与静态检查；真实库由受信任本机的只读 Private Gate 对 projection-digest-bound 固定基线、新鲜 Aggregate Index 和既有 canonical current release 做一致性验证，并只产生不含路径、标识或媒体 hash 的 Gate Receipt。

曾考虑让 public repository 使用 self-hosted runner 访问真实库，或只保留人工全库命令。前者会把 fork/PR 代码引入持有私有数据的执行环境，后者无法形成持续回归信号；两者都不满足边界。物理隔离的代价是公开 CI green 不能证明 244 个真实 Bundle 通过，本地 Gate Receipt 也不能证明 Commercial Approval、部署或生产验收。合法扩库必须单独评审并版本化更新固定基线；Private Gate 和调度器不得自动发布、修复、删除或更新基线。
