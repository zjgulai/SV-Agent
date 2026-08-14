# 付费任务安全提交 SOP

## Purpose

确保任何付费生成只提交一次，并在前端异常时先恢复旧任务，避免重复扣分。依据 U-B01：页面报 HTML/JSON 错误，但后台任务已扣 50 分并最终成功。

## Inputs

- experiment_id、功能、冻结后的输入/config digest。
- 可见报价、当前余额、单次/矩阵预算上限。
- operation/idempotency key、任务查询入口。

## Preconditions

- 报价在点击前可见且不超过批准上限。
- 余额已读取，账本末行与页面余额一致。
- 输入不含真实人脸、声音、凭证、Cookie、私有 URL 或未授权素材。
- 已定义成功、失败、unknown、退款与强制停止条件。

## Steps

1. 记录 credit_before、quote、config digest 和 submit_count=0。
2. 生成并持久化唯一 operation key；冻结按钮与输入。
3. 只点击一次；立即把 submit_count 记为 1。
4. 保存 Location/任务入口；任务 ID 只保存 SHA-256。
5. 前端响应正常时按 Job 查询；响应解析失败/超时时进入 `unknown/recovering`。
6. unknown 时查询任务队列、项目和同 operation key，禁止再次点击。
7. 只有确认不存在 Job、没有扣分且停止规则允许时，才能新建一次独立实验。

## Evidence

- S-B01…S-F01：每次一击、每次精确扣 10。
- U-B01：一击后报错，860→810，Job 后续成功；证明前端错误不能作为重试依据。

## Stop Conditions

- 报价隐藏、变化或超过 cap。
- 余额不一致、出现未知扣分、任务身份不明确。
- 首次响应为 HTML/JSON 错误、重复任务或无幂等恢复入口。
- 输入授权、数据来源或发布权限不明确。

## Acceptance

- submit_count=1；quote、扣分和任务可对账。
- terminal state 来自持久任务/项目，而非按钮提示或 Redis 结果。
- 失败/unknown 后无重复提交和重复扣费。

## Recovery

关闭当前提交入口，使用 operation key、Job URL、任务队列和项目恢复。超过观察窗口仍无终态时保留 `unknown`，人工复核账务；不得把“卡 95%”改写成失败。
