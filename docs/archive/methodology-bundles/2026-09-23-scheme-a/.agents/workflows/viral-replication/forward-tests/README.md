# Forward Tests

前向测试用来验证一个没有预先修改项目代码的独立 agent，是否能沿 workflow pack 的路由、skill-map 和 stop conditions 得到受约束的输出。

运行时应提供：

- workflow pack 根目录；
- 对应 canonical skills；
- 对应的前向测试场景，例如 `VR-P3-006-proof-demo-case.md`、`VR-P4-001-attention-grammar-case.md` 或 `VR-P4-002-conversion-action-case.md`；
- 如需对照，再提供 `fixtures/` 目录。

评估只看是否遵守 artifact contract 和证据边界。不要把前向测试结果扩大解释为媒体质量、平台分发、转化 lift 或 production acceptance。

`VR-P4-001-attention-grammar-case.md` 只评估唯一 attention component、surface substitution、Fact binding、冻结 Pattern anchor 与合同隔离；[VR-P4-001-attention-grammar-result.md](VR-P4-001-attention-grammar-result.md) 保留首次 anchor blocker、修正和独立复测结果。

`VR-P4-002-conversion-action-case.md` 只评估唯一 conversion component、same-Snapshot Fact/Promotion binding、database-time validity、final CTA slot、provider exclusion、action-path state 与合同隔离；[VR-P4-002-conversion-action-result.md](VR-P4-002-conversion-action-result.md) 保留本地独立处置与其不能证明的外部行动/转化边界。

`VR-P4-003-trend-native-case.md` 只评估唯一 trend component、有界 signal observation、source audio/template/identity substitution、冻结 TrendAdmissionRecord、Fact binding 与合同隔离；[VR-P4-003-trend-native-result.md](VR-P4-003-trend-native-result.md) 必须将音频/模板权利、平台兼容、模板激活、上传/发布、完整原创审批、媒体质量和表现结论保留在独立 gate，不得写成本地 workflow 的能力。

`VR-P4-004-media-integrity-case.md` 只评估 `MediaIntegrityRecord` 的六个独立 gate、pending artifact 语义、full-surface claim mapping、target identity continuity、source-use matrix、原创差异的独立评审和 proof-level 边界；[VR-P4-004-media-integrity-result.md](VR-P4-004-media-integrity-result.md) 保留实际独立复测结论。它不得把 preflight、Asset Bundle/Index、Private Gate、技术探测或模型审阅扩大为版权、商业、平台、发布或 production acceptance。
