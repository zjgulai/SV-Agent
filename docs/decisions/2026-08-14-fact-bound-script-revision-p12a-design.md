---
status: implemented
authority: regression-contract
---

# P1.2a 事实绑定脚本修订合同

## 目标

把当前“任意标题派生版本”替换为可操作、可比较、可重放的事实重绑定版本。
此切片只改变既有 ScriptVersion 各镜头所引用的已冻结事实；不调用 Provider、
不创建 Job、不生成候选、不进入媒体、计费、账号或权限范围。

## 明确边界

客户端不能提交 title、voiceover、caption、phase、时间线、visual、action、
acceptance、tag 或 shooting list。它只能提交覆盖父版本全部镜头的：

```text
fact_bindings[]: shot_index + fact_id
```

每个 `fact_id` 必须属于该 ScriptGeneration 的有序 `selected_fact_ids`，并且在
当前事务中仍属于同一 snapshot、状态为 `confirmed` 或 `locked`。`excluded`、未选
择、跨 snapshot、已拒绝或缺失事实均不可绑定。

服务端从父版本复制其结构和服务器持有的可见创意字段，仅对每个镜头写入：

```text
voiceover = fact.claim
caption = fact.claim
product_claims = [fact.claim]
supported_fact_ids = [fact.id]
```

随后用 generation 冻结的 pattern、selected/excluded 合同重跑 `validate_script`。
父版本本身必须 acceptable，新 child 也必须 acceptable；否则不写入任何版本。等价
表达、自由文案、时间线重排和真实身份 author 必须等 P1.2b/P1.5.3 的专门设计。

## API 与幂等

```text
POST /api/v1/scripts/{script_id}/versions/{parent_version_id}/derive
Idempotency-Key: required

{
  "fact_bindings": [
    {"shot_index": 0, "fact_id": "UUID"}
  ]
}
```

输入拒绝额外字段。service 对 `(parent_version_id, Idempotency-Key)` 计算规范输入
摘要，且数据库以同一组合唯一约束最终收束：相同 key/输入返回同一 child（200）；
相同 key/不同输入返回 `409 IDEMPOTENCY_CONFLICT`；新输入只可 append（201）。
并发冲突后必须重读并比较摘要，不能只做先查再插。

## 追加式溯源

`0009` 为 `script_versions` 增加 nullable provenance：

```text
revision_kind          # fact_rebind for P1.2a child
actor_kind             # fixed local_operator; client cannot fake author
reason_code            # fixed fact_rebind; no unbounded user note
operation_key          # never returned or exported
operation_input_digest
```

既有 generated/legacy rows 保持所有新字段为 null，绝不回填或更新。新事实重绑定行
必须完整填写固定 provenance，并受 `(parent_version_id, operation_key)` 唯一约束。`0010`
以显式 `IS NOT NULL` 收紧 guard：PostgreSQL 会把由 `NULL` 导致的 unknown CHECK
结果视为通过，因此任何 partial provenance 必须用追加迁移拒绝，不能回改已经应用的 `0009`。
输出和导出可带 parent、kind、actor、reason code、input digest，但不暴露 operation key。

## Web

脚本页读取 generation 的只读 fact contract（selected/excluded 的 id、claim、status、
snapshot），不访问最新 Product snapshot。每镜只有一个冻结事实选择器；页面显示
服务端将重建的事实原句。成功后定位新版本并可比较；网络错误的重复保存复用相同
请求签名对应的 `Idempotency-Key`。

## 数据迁移风险与验证

迁移只新增 nullable 列和唯一约束，不触碰现有 draft、validation report 或 append-only
trigger。downgrade 仅删除这批列/约束，因此只可在临时数据库执行。验收包括：

1. 事实重绑 child 的四个事实字段由服务器生成，父版本字节不变。
2. 相同 key/body、并发相同 key 都只得到一行；同 key/不同 body 为 409。
3. excluded、未选择、跨 snapshot、rejected fact、blocked parent 与额外字段均不得写入。
4. generation frozen fact contract 的顺序/状态可读，绝不混入最新 snapshot。
5. migration upgrade/downgrade/upgrade、API/Web 回归、lint/typecheck/build 全通过。
