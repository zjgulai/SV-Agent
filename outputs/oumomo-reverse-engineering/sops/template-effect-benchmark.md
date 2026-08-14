# 模板效果基准 SOP

## Purpose

区分模板的真实结构效应与模型随机波动，评估模板是否值得复刻。

## Inputs

- 同一商品事实、参考图、prompt、模型、时长、比例、分辨率。
- Template A/B 的稳定 ID/version、报价、每组至少 2 次重复。

## Preconditions

- 两模板可在相同输入上运行，身份/version 可见。
- 每次报价≤30，总预算在批准矩阵内。
- baseline 输入与评分 rubric 已冻结。

## Steps

1. 各模板先记录 preview、结构、version 和 quote。
2. A 重复 2 次、B 重复 2 次；每次安全单击。
3. 比较组内镜头/文本/视觉方差。
4. 比较组间 hook、phase、CTA、事实保持和媒体 QA。
5. 只有组间差异持续大于组内方差才归因于模板。

## Evidence

- T-GATE：模板报价必须上传后才出现，无法形成已批准的同商品 A/B，因此零扣分 blocked。
- 脚本 S-T01/S-T02 可作为“类型影响声明风险”的低成本先验，但不能替代视频模板实验。

## Stop Conditions

- 模板 ID/version、同一模型或报价不可见。
- 模板偷偷改变时长、模型、输入图或数量。
- 无重复、无对照或总预算超限。

## Acceptance

- 2×2 最小矩阵完整；所有非 template 字段 digest 相同。
- 报告给组内/组间差异和事实/质量门，不只给主观好看。

## Recovery

报价隐藏时停在上传/确认前；保存 blocked evidence。模板内容更新后视为新 version，不与旧结果混组。
