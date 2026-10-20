# Public Sites

`sites/` 只承载经过审查、可公开展示的静态体验。它不是业务事实源，也不代表部署、商业批准或生产验收。

## Viral Replication Workbench

`viral-replication-workbench/` 是无构建依赖的公开案例与工作流站点。父仓库跟踪：

- `README.md`：站点边界与本地预览说明；
- `docs/`：站点规格、案例扩展方案和 tickets；
- `dist/`：经筛选的静态页面、去敏结构化案例和展示媒体。

本地 Sites 绑定文件 `.openai/hosting.json` 被明确排除。修改后必须分别验证本地静态文件和实际公开 URL；仓库构建通过不等于线上字节已更新。
