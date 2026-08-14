# 单变量实验 SOP

## Purpose

用可重复对照识别某个配置对输出的真实影响，避免把随机波动解释为功能机制。

## Inputs

- baseline fixture、control experiment_id、单一变量与候选值。
- 其余冻结配置、重复次数、预算、评分 rubric。

## Preconditions

- baseline 至少重复 2–3 次，能估计组内方差。
- 每次使用相同输入 bytes/digest、模型身份、分辨率、时长和 count。
- 变量、停止条件和结论等级在提交前写入 config snapshot。

## Steps

1. 生成 canonical config 与 digest。
2. 运行 baseline repeats；保存每次输出结构/哈希/时延。
3. 只改变一个字段并运行 treatment。
4. 对比组内方差与组间差异。
5. 结论标为 F、I-H、I-M 或 U；样本不足不得写因果。

## Evidence

- S-D15/S-D45：只改 duration，观察到 3/4 与 5/8 phase/shot 预算。
- S-T01/S-T02：只改类型，反常识模板显著增加无证据比较和功效声明。
- S-O01/S-F01：排序/删除不被严格遵守。

## Stop Conditions

- 模型身份/价格/输入无法冻结。
- baseline 没有重复且输出随机性未知。
- 变量之间发生联动或页面悄然重置配置。

## Acceptance

- control/treatment 只有一个 canonical field 不同。
- 每个输出可追溯到 config digest、任务 hash 与账务。
- 报告同时给组内波动、组间差异和样本限制。

## Recovery

发现配置漂移时废弃该 run 并标 invalid，不把它加入效果估计；预算不足时缩小为 2×2 最小矩阵并降级结论。
