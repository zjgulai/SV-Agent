# Experiment Evidence

定义 clean-room 能力实验如何记录观察、成本和证据强度。实验结论用于决策，不自动成为产品事实或生产可用性证明。

## Language

**Experiment**:
在冻结配置和停止条件下，为回答一个明确问题而执行的一组观察。
_Avoid_: Test run, exploration

**Observation**:
实验过程中可直接看到或由工具测得的状态，不包含对原因的推断。
_Avoid_: Finding, conclusion

**Experiment Manifest**:
一次实验的配置摘要、任务摘要、预算和证据引用清单。
_Avoid_: Log file, report

**Job State Event**:
实验对象在一个时点的可观察执行状态记录。
_Avoid_: Progress guess

**Credit Ledger**:
付费实验中报价、余额变化和费用连续性的对账记录。
_Avoid_: Cost estimate

**Artifact**:
从实验中取得并通过 hash 绑定的本地可复核产物。
_Avoid_: Preview, remote URL

**Scorecard**:
对 Artifact 的独立质量维度评分；未测维度保持未知。
_Avoid_: Overall quality

**Evidence Level**:
结论的证据等级：Fact、Inference 或 Unknown。
_Avoid_: Confidence score

**Terminal State**:
由持久状态和本地证据共同确认的实验终态；进度百分比或扣费不构成终态。
_Avoid_: 95 percent complete

**Finding**:
由一个或多个 Observation 支持、明确标注范围和限制的实验结论。
_Avoid_: Product Fact, universal capability

**Creative Comparison Contract**:
冻结 Control、Variant、唯一 Creative Dimension、Product Snapshot、平台、市场和停止条件的不可变比较合同。
_Avoid_: A/B test, prompt comparison

**Creative Dimension**:
Creative Comparison Contract 中唯一允许变化的创意属性；其他差异必须被明确阻断。
_Avoid_: Free-form change, experiment variable
