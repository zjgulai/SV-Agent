# FactFrame 验收证明矩阵

| Gate | 适用 claim | 必要条件 | 不能证明 |
| --- | --- | --- | --- |
| static / Ruff / Mypy | import、lint、类型合同 | 当前工作区运行 | database、runtime |
| unit | 纯领域规则、validator、determinism | 覆盖具体反例 | PostgreSQL、broker、browser |
| disposable PostgreSQL integration | transaction、lock、trigger、repository/API | 明确 disposable URL 与当前 migration | provider、deployment |
| migration replay | upgrade/downgrade/upgrade | 新建 disposable database | 历史生产数据迁移 |
| Web unit/build | UI projection、state rendering、bundle | 当前 API contract fixture | browser/server integration |
| Compose + Playwright | 本地整栈关键路径 | isolated services 与 fresh schema | production proxy/provider |
| public CI | exact committed checkout | run/commit identity 一致 | dirty tree、private evidence |
| Private Gate | 本机 real library 对 fixed baseline/current | exact approved local root | commercial approval、deploy |
| deployment | artifact 在目标环境完成发布 | artifact/target/run identity | live route、长期健康 |
| live verification | 指定 endpoint 当时可访问且 bytes/behavior 符合 | target、time、expected identity | commercial approval、持续 SLA |

## 选择规则

- 文档或 skill 改动：结构校验、链接/占位标记检查、相关 skill forward test；若改变长期导航则刷新 capability graph。
- domain validator：unit；若数据库同时防护则加 PostgreSQL integration。
- repository、transaction、trigger、Outbox：真实 PostgreSQL integration。
- API + Web 可见行为：API integration、Web unit；关键旅程再加 Compose/Playwright。
- migration：disposable upgrade；只有回滚合同需要时才 downgrade/upgrade。
- private evidence：public fixture 与 Private Gate 分开记录。
- deploy/production：必须有 remote artifact/run/target/live evidence，不能由本地测试推断。

## 汇报模板

```text
结论：accepted | partially accepted | not accepted
待证明 claim：...
当前证据：command / target / result / timestamp-or-commit
能证明：...
不能证明：...
下一安全 gate：...
```

所有命令从当前 `docs/development/testing.md` 获取。若工作区仍 dirty，明确说测试对应工作区而非某个远端 commit。
