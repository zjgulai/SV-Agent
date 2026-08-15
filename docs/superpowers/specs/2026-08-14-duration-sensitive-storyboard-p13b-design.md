# P1.3b 时长敏感默认分镜合同

## 决策与证据边界

本设计已获批准。它将新 generation 的默认结构升级为按时长变化的冻结
`PatternDefinition`，不改变事实选择、Provider 边界、CTA 限制或 audience 的只记录
语义。

干净室实验只支持以下 F 级结构观察：15 秒曾得到 3 阶段/4 镜头，45 秒曾得到
5 阶段/8 镜头；30 秒阶段数多次为 4，但镜头数曾为 4、5、6 和 8。来源是
`evidence/session-log.md` 的 Seq 006、008、035、062、063 及
`experiments/experiment-manifest.jsonl` 的 Z12、S-D15、S-D45。

因此下列 phase key、role、权重与 30 秒的 6 镜头，均是本项目为稳定、可验证产品
体验做出的确定性默认，**不是**对 Oumomo 私有固定逻辑的声称。未来真实实验可创建
新的 contract version，不能原地改变本合同。

## 冻结合同

新 generation 写入 `configuration.pattern_definition` 的
`contract_version` 为 `p1.3b`，registry version 为 `1.2`。完整对象仍进入
`input_digest`；不需要 migration，因为 configuration 是 append-only generation
事实。`p1.3a` 与 legacy `1.0` 只从各自持久化对象读取，绝不通过当前 registry
重新解释。

`problem_solution` 的精确计划如下。每行的整数预算和等于目标时长：

| 时长 | 阶段 | 镜头 phase 顺序 | 预算权重 |
| --- | --- | --- | --- |
| 15 秒 | hook, solution, cta | hook, solution, solution, cta | 2, 4, 5, 4 |
| 30 秒 | hook, problem, solution, cta | hook, problem, problem, solution, solution, cta | 3, 5, 5, 6, 6, 5 |
| 45 秒 | hook, problem, solution, proof, cta | hook, problem, problem, solution, solution, proof, proof, cta | 4, 5, 6, 7, 7, 6, 5, 5 |

其余六种 pattern 使用同样的 3/4、4/6、5/8 拓扑，但保留各自 server-owned
阶段语义，例如 `demo_first` 的 demo/proof/comparison、`before_after` 的
before/after、`listicle` 的 items/recap。这些名称及 role 不能由 Provider 或客户端
编辑。所有镜头仍须绑定一个 ordered selected Fact；CTA 始终是
`server_generic_no_offer`，不得生成价格、折扣或限时文案。

## 执行与校验

- compiler 仅接受 registry 声明的 15/30/45 秒和 `en`/`zh-CN`，并冻结完整 phases、
  shots、weight、语速、field policy 与 server-owned copy。
- Deterministic provider 根据每一镜 weight 计算时间窗，再按 phase 聚合范围；它不再
  假定 phase 数等于 shot 数。
- validator 分别比较 phase 序列和完整 shot `phase_key`/role 序列，按每一镜预算
  检查时长。少镜头、多镜头、重复或错序 phase、错误 role、超预算或超语速都只能得到
  validation failure。
- Web catalog 与生成页读取 API 返回的冻结合同。预览按 phase 分组并逐镜展示，确保
  30 秒的 6 镜头和 45 秒的 8 镜头都可见；它不增加创意编辑槽。

## 数据、回退与延期

本批不改数据库 schema、不回填或删除 generation，也不改变历史 ScriptVersion。
回退只需停止为新任务选择 `p1.3b` registry；已写入的 p1.3b generation 必须继续
按其持久化定义执行和导出。

仍明确延期：audience taxonomy 和可影响内容的场景/语气、promotion Fact 的来源与
有效期，以及任何真实渲染、报价、积分、发布或账户权限功能。

## 验收

1. 七种 pattern × 15/30/45 秒 × 两种语言均编译为 p1.3b，phase/shot 数为
   3/4、4/6、5/8，预算和精确等于时长。
2. `problem_solution` 三种时长精确匹配本设计表；registry 改动不影响已持久化的
   p1.3a/p1.3b 合同。
3. provider 产出完整计划，validator 接受正确计划并阻断 phase/role/镜头数/预算/语速
   偏差。
4. API catalog、Web 预览与 15/30/45 秒选择均显示全部 4/6/8 镜头。
5. backend lint/mypy/unit/integration、Web lint/typecheck/test/build 以及隔离 migration
   head 检查通过；集成环境不可用时必须明确报告，不能以 unit 结果替代。
