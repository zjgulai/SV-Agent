# Primary Replication Mechanism Routing

对每个 Reference 只选择一个主机制。平台、语言、市场、商品和视频长度是约束字段，不是主类型。

```text
外部趋势/音频/平台梗是否决定主要表达？
  是 → trend-native
否则，促销/异议/CTA/行动是否决定主要表达？
  是 → conversion-action
否则，实验/对比/量化/物理演示是否决定主要表达？
  是 → proof-demonstration
否则，POV/ASMR/感官/日常情绪是否决定主要表达？
  是 → experience-pov
否则，Hook/镜头节奏/字幕节拍/视觉反差是否决定主要表达？
  是 → attention-grammar
否则 → narrative-transformation
```

## Tie rule

当两个机制无法通过一个可观察的 Creative Dimension 分离时，输出 `blocked: primary_mechanism_ambiguous`，并要求建立两个 Variant 或缩小问题。不得创建一个没有唯一变量的 hybrid workflow。

## Evidence rule

排名、播放量集中度、AI 摘要和表层相似度都不能单独决定主机制。主机制必须由 DecompositionMap 的可观察字段和 PatternHypothesis 的 invariant 支撑。
