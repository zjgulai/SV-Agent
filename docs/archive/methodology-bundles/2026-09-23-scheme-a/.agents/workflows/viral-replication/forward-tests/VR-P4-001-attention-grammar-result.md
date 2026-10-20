# VR-P4-001 Attention Grammar：独立前向测试结果

## 场景

场景入口：[VR-P4-001-attention-grammar-case.md](VR-P4-001-attention-grammar-case.md)。测试只验证 workflow 的文档级 artifact、frozen Pattern anchor、Fact binding 和合同隔离；不生成媒体，不调用 provider，也不使用平台数据。

## 第一次独立判定：blocked

初始场景将 `1.6–2.4s` 的 `caption_cadence` 观察只绑定到 `shot=1, solution/demo`。但 frozen Pattern 的 `shot=0` 覆盖 `0.0–2.0s`，该观察跨越 2.0 秒边界。

- disposition：`blocked`
- blocker：`attention_pattern_anchor_mismatch`
- 修正：把观察改为 `1.6–2.0s`，并绑定 `shot=0, hook/problem, budget=2s`。

这次红灯证明 attention adaptation plan 需要逐条检查时间范围与 frozen shot window，而不能只记录一个近似 phase。

## 修正后的独立判定：ready for next local gate

独立评估使用修正后的完整合同字段，未提供预期 disposition。结论是：attention-grammar 的内部受控方案可以进入下一本地合同/事实约束 gate。

| 检查项 | 结果 | 依据 |
| --- | --- | --- |
| primary mechanism | `attention-grammar` | 观察对象是 Hook、caption cadence 和 reveal cadence；没有趋势、促销、proof、experience 或 narrative 主导信号。 |
| selected component | `caption_cadence` | Control 为 0.8/1.6 秒两条等义 fact-bound 字幕；Variant 为 0.8/1.2/1.6 秒三条等义 fact-bound 字幕。 |
| time/Pattern anchors | 通过 | 0.0–0.8、0.8–1.6、1.6–2.0 秒均完整落在 `shot=0` 的 0.0–2.0 秒 window；2.4–5.0 秒完整落在 `shot=1` 的 2.0–6.0 秒 window。 |
| contract isolation | 通过 | Snapshot、Fact 集合、平台、市场、15 秒时长、语言、Pattern、模型、目标素材、声音政策、Hook、reveal cadence、visual contrast 和预算冻结；唯一变化为 `caption_cadence`。 |
| Product Truth | 通过 | 目标文案“屏幕显示温度读数”绑定 confirmed `fact-temperature-display-confirmed`；excluded Facts 为空。 |

## 仍然成立的限制

- `retention_rate=not_reported`，不能推导留存、观看、转化、causal lift 或 winner 结论。
- 场景只有 fixture digest 和 `obs://` refs，不能证明媒体已生成、字幕已实际呈现、平台已接收、内容已发布或 production acceptance。
- `view_count=18000` 没有按 Control/Variant 归属，不能用于条件间比较。

## 结果

```text
disposition: ready_for_next_gate
scope: local contract and fact-bound Script/Storyboard validation only
evidence_level: local_fixture_only
blocked claims: platform performance, causal attribution, media proof, deployment, live, production
```

下一 gate 必须补充条件级 Artifact/Media QA 和有范围的执行记录；如需评价平台效果，还要先建立可归属的指标窗口和比较设计。
