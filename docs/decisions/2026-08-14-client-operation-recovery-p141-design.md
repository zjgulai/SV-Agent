---
status: implemented
authority: regression-contract
---

# P1.4.1 客户端操作恢复合同

## 目标与证据

本切片处理“异步业务请求已被服务端接受，但浏览器因代理返回 HTML、损坏
JSON 或网络中断而不知道结果”的恢复问题。清洁室实验已观察到链接生视频
出现此类前端 JSON 解析失败而后台任务仍能完成的情况；因此页面不得把未知
结果引导为“重新生成”或生成新的幂等键。

本切片只覆盖现有两条异步入口：公开 URL 商品导入和事实脚本生成。

## 范围与非目标

包含：

- 版本化、浏览器 `sessionStorage` 内的 `OperationRecord`。
- 同一操作的幂等键、冻结请求 payload、请求摘要、已知 Job 路径、最后状态和
  最后读取时间。
- 2xx 非 JSON 与网络失败的稳定类型化错误；绝不保存或显示响应原文。
- 已知 `Location: /api/v1/jobs/{id}` 时直接进入该 Job；未知时仅允许
  “恢复原请求”，且重放完全相同的 body 和 `Idempotency-Key`。
- 轮询失败指数退避、页面隐藏暂停、显式重新连接，以及 terminal/dead-letter
  停止轮询。

不包含：数据库 migration、新 API、按 idempotency key 的查询、匿名任务重试、
tenant/auth、ProviderRun、积分、媒体、候选编辑器或真实 Oumomo 实验。

## OperationRecord

`sessionStorage` 中仅保留有限数量的下列记录，键名和 payload 都具有 `v1`
版本号：

```text
kind: product_import | script_generation
idempotency_key
request: frozen JSON body plus route identity
request_digest: deterministic local fingerprint
job_path: /jobs/{opaque-id} | null
state: submitting | unknown | recovering | accepted
last_known_job_state: nullable
last_read_at: nullable timestamp
created_at / updated_at
```

记录只在本浏览器会话中存在，不写 PostgreSQL、日志或分析事件。Job 路径只接受
同源、无 query/fragment、固定 `/api/v1/jobs/<opaque-id>` `Location`，避免将
响应头变成导航目标。

## 状态机

```text
submitting -- JSON 202 --> accepted(job_path)
submitting -- 2xx non-JSON + safe Location --> accepted(job_path)
submitting -- transport/unknown response --> unknown
unknown -- user chooses recover original --> recovering --> submitting
accepted -- Job poll --> accepted(last_known_job_state)
```

恢复绝不新建 key，不改变 payload，不调用新的 endpoint。已有服务端
`(job_type, Idempotency-Key, input_digest)` 合同负责把重放收束为同一 Job；
`Location` 是已知 Job 的恢复凭据，而非服务器返回 HTML 的替代解析源。

## 轮询合同

- 可见页面的首轮间隔为 1 秒；连续读取失败做有上限的指数退避。
- `document.visibilityState === "hidden"` 时停止间隔轮询；恢复可见后重新读取。
- Job terminal 或最新事件为 `dispatch_dead_lettered` 时停止自动轮询。
- UI 可提供“重新连接”，但其行为仅为 `GET` 同一 Job，不会触发生成或导入。

## 验收

1. 202 + HTML/坏 JSON + 合法 Location：只提交一次，页面跳到原 Job。
2. 无 Location 的网络失败：状态是 unknown；刷新后仍只可恢复原请求，且 key/body
   不变。
3. 恢复后的 202 只对应一个 Job；客户端不出现“重新生成”或新的扣费/任务语义。
4. Job 页能回写最后可观察状态；隐藏页、终态和 dead-letter 都不继续轮询。
5. 不新增后端接口、迁移或匿名写入口；Web lint、typecheck、unit、build 与后端
   既有幂等集成测试通过。
