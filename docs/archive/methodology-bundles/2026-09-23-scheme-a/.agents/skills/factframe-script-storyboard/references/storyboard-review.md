# Storyboard Review SOP

## Preflight

同时读取 frozen generation、immutable Script Version 与当前 Product Facts。分别保留：

- fact-contract findings
- stored validation report
- current live validation report
- Storyboard-specific preflight

任何 blocker 都不能被旧的 acceptable 报告覆盖。

## Create / Approve

1. 在事务内锁定并重读相关 Facts。
2. 重新计算 preflight 与 binding digest。
3. 只有 ready 才追加 Storyboard；只追加，不 update/delete。
4. approve/reject 写 append-only Approval Event。
5. 读取时根据当前 Fact 状态派生 `stale`，不改写历史事件。

## Preview

Preview 是由 Storyboard 结构确定性产生的 animatic projection，只暴露允许的 image indexes 和结构字段。其 digest 必须稳定。它不是 RenderJob、媒体文件、品牌批准或发布结果。

## 回归重点

- Fact 在 create 与 approve 之间失效。
- stored/live/preflight finding 不相互覆盖。
- Storyboard 与 Approval update/delete 被数据库 trigger 拒绝。
- preview ordering/digest 确定。
- UI 状态刷新后正确显示 ready/blocked/stale。
