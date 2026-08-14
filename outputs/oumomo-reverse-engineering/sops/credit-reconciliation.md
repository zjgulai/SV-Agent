# 积分对账 SOP

## Purpose

把报价、提交、任务、终态和余额拆成可验证事实，发现重复扣费、延迟刷新和退款缺口。

## Inputs

- credit-ledger.csv、实验 manifest、任务事件。
- quote、credit_before、credit_after、submit_count、terminal_state。

## Preconditions

- 页面已登录且余额可读取。
- 账本使用统一时区与 experiment_id；不保存账号、手机号或凭证。

## Steps

1. 提交前刷新并读取余额两次；不一致则停止。
2. 记录 quote 和预计 delta。
3. 任务创建后记录实际余额；UI 未刷新时进入项目页再读一次。
4. terminal 后再次读取，计算 `delta=after-before`。
5. 对比 quote、submit_count、Job 数、Artifact 数和 refund。
6. 运行 `ledger_total`，确认累计净扣不超过总预算。

## Evidence

- 12 个 S-*：120 分，逐次 -10。
- U-B01：-50 在任务完成前发生；最终成功未二次扣分。
- I-GPT-01/02：各 -2；I-NANO-01/02：各 -3；四次均单击且有独立 Job/Artifact。
- 当前合计 180，980→800。

## Stop Conditions

- 页面余额与账本末行不同。
- delta 不等于报价且无可见退款/折扣原因。
- 一个 experiment_id 对应多个任务或 submit_count>1。

## Acceptance

- 每行 before + delta = after。
- 前一行 after 等于后一行 before。
- 当前页面余额=账本末行 after；累计净扣≤批准预算。

## Recovery

冻结后续付费任务，按 operation key/Job/项目反查；新增“未知扣分”事实行而不是修改旧行。退款后另记 adjustment，不覆盖原 charge。
