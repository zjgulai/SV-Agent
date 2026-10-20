# 外部证据绑定与投影

## 绑定键

```text
Product Snapshot id
+ recomputed canonical Snapshot digest
+ typed evidence context
+ reviewed package identity and lifecycle
```

品牌名、商品标题、category、文件名、向量相似度或“看起来同款”都不能建立绑定。`reviewed_snapshot_selection` 只能形成 partial、source-scoped hypothesis；canonical identity 才是 exact。

## Package 验证顺序

1. 从受控 descriptor 读取唯一候选。
2. 验证 schema/version 与 canonical digest。
3. 验证 subject scope、observation window、source、lifecycle、exposure policy。
4. 验证 safe values、枚举、bounds 与 missing semantics。
5. 拒绝或 quarantine unknown digest、重复 active binding、scope mismatch 和 unsafe projection。
6. 只投影 public-safe typed fields；内部 quarantine 原因不上普通 response。

## Missing semantics

- `observed_zero`：测量存在且值为零。
- `not_reported`：来源未报告该字段。
- `not_collected`：本次流程没有采集。
- `source_ambiguous`：来源或主体映射不唯一。
- `unknown`：已知无法得出值。
- `unavailable`：整个证据包或 reader 当前不可用。

不要用 `0`、空字符串、空数组或一个 generic `missing` 抹平差异。

## Decision Brief 规则

- Observation：只陈述 typed evidence 中直接存在的事实。
- Inference：使用 bounded、source-scoped、非因果措辞。
- Unknown：保留缺失和冲突。
- Action：可逆的人工审查或下一步采集。
- Guardrail：Product Truth blocker、绑定限制、时间窗、非因果说明。

使用 server-owned `text_key` 和 typed args 确定性编译，稳定排序；`observed_at` 不进入 canonical digest。外部 evidence 不能改变 Product Truth blockers、Difference Ledger、validation 或 Storyboard state。
