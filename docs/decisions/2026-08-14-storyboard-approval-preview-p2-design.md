---
status: implemented
authority: regression-contract
---

# P2.0 分镜审核与零成本预览设计

状态：已确认、已实施；已完成本地数据库、全量回归与浏览器 E2E 验证，尚未部署  
日期：2026-08-14  
范围：持久化分镜审核与确定性预览；不包含 RenderJob、视频模型、素材上传、报价、积分、账务、账号或发布。

## 1. 目标

把当前只读的 `StoryboardPreflight` 升级为可追溯、可恢复的“审核版分镜”，让事实已经通过校验的 `ScriptVersion` 能被人工明确接受或拒绝，并在支付或渲染之前展示零成本、确定性的预览。

```text
ScriptVersion
→ 重新运行事实/排除/创意合同预检
→ append-only StoryboardVersion
→ deterministic HTML/SVG animatic
→ append-only ApprovalEvent
→ 未来报价前门禁
```

本切片的完成不代表可以生成视频；它只生成可审阅的结构化预览合同。

## 2. 已确认边界

- 事实、商品快照、脚本版本和新分镜版本都必须追加式保存；历史记录不更新、不删除。
- 创建分镜和写批准事件都必须重新读取 selected/excluded fact contract，并重跑现有校验。
- 任一 selected fact 不再为 `confirmed` 或 `locked` 时，历史批准必须显示为 `stale`，不得作为未来报价或渲染前提。
- 预览只使用 ScriptVersion 的时间线、文本合同和现有公开快照图片索引；图片加载失败时显示占位，不得冒充身份或包装验收通过。
- 当前没有认证与多用户能力，因此批准仅代表“本地操作者决定”，不代表法律、品牌或多人协作审计。

## 3. 明确不做

- 不创建 `RenderJob`、Celery 任务、Provider adapter、媒体二进制文件或对象存储。
- 不调用图片/视频模型，不做关键帧生成，不做 OCR、ASR、账务、报价、预留或退款。
- 不新增用户、组织、权限、外部账号、OAuth 或社交发布。
- 不把 `approved` 解释为已获报价、已付款、可渲染或可发布。

## 4. 持久化合同

### 4.1 `storyboard_versions`

每次创建均为新行，引用一个不可变 `script_version_id`。建议字段：

| 字段 | 约束与用途 |
|---|---|
| `id` | UUID 主键 |
| `script_version_id` | 外键，`RESTRICT` 删除 |
| `snapshot_id` | 创建时冻结的商品快照 |
| `selected_fact_ids` / `excluded_fact_ids` | 有序 JSONB 列表，复刻预检事实合同 |
| `draft` | 预检通过时的 phases/shots/titles/tags/shooting list JSONB |
| `validation_report` | 预检时的完整报告 JSONB |
| `preflight_digest` | 当前事实合同和校验输入的 canonical SHA-256 |
| `storyboard_digest` | 整个冻结 payload 的 canonical SHA-256 |
| `preview_contract_version` | 固定为 `p2.0-animatic-v1` |
| `operation_key` | 对同一创建操作做幂等重放 |
| `created_at` | 数据库时间 |

`(script_version_id, operation_key)` 唯一。创建时只有 `StoryboardPreflight.status=ready` 才能写入；同 key 且 digest 相同返回原记录，digest 不同返回 `IDEMPOTENCY_CONFLICT`。

### 4.2 `storyboard_approval_events`

审批不是 `StoryboardVersion` 的可变列，而是追加事件。建议字段：

| 字段 | 约束与用途 |
|---|---|
| `id` | UUID 主键 |
| `storyboard_id` | 外键，`RESTRICT` 删除 |
| `decision` | `approved` 或 `rejected` |
| `reason` | 可选、去首尾空白、最长 500 字符 |
| `storyboard_digest` | 审批所针对的冻结版本 |
| `preflight_digest` | 审批瞬间重新验证后的输入摘要 |
| `validation_report` | 审批瞬间重新验证报告 |
| `operation_key` | 审批操作幂等键 |
| `event_sequence` | 数据库序列；在单一 storyboard 内确定“最新事件”的全序 |
| `created_at` | 数据库时间 |

`(storyboard_id, operation_key)` 唯一。最新事件是当前决定；读取时若当前重检失败，则派生状态为 `stale`，而非重写历史事件。

两个新表均需 PostgreSQL `BEFORE UPDATE OR DELETE` 拒绝 trigger，与现有 snapshot、generation、script version 的不可变规则一致。

## 5. API 合同

```text
POST /api/v1/scripts/{script_id}/versions/{version_id}/storyboards
GET  /api/v1/storyboards/{storyboard_id}
GET  /api/v1/storyboards/{storyboard_id}/preview
POST /api/v1/storyboards/{storyboard_id}/approval-events
GET  /api/v1/storyboards/{storyboard_id}/approval
```

- 两个 `POST` 均要求 `Idempotency-Key`；路由只管理事务和 RFC 9457 Problem Details，application service 管理重检、锁和持久化。
- 创建与批准在同一事务中锁定所需 facts，避免事实在 preflight 与写入之间降级导致的 TOCTOU。
- `GET /preview` 返回确定性的结构化 animatic（shot card、时段、支持事实、口播/字幕、验收描述、可选快照图片索引）；Web 负责绘制 HTML/SVG，不保存媒体文件。
- 稳定错误码：`STORYBOARD_NOT_FOUND`、`STORYBOARD_NOT_READY`、`STORYBOARD_APPROVAL_STALE`、`IDEMPOTENCY_CONFLICT`。

## 6. Web 工作流

```text
事实约束分镜预检
  ├─ blocked：只显示 findings，不显示创建或批准动作
  └─ ready：创建审核版分镜
              → 查看 animatic
              → 批准 / 拒绝并写原因
              → 显示 approved / rejected / stale
```

页面必须明确显示“批准仅能进入未来报价前门禁；当前不提供报价、渲染或发布”。预览展示的商品图只是快照引用，不是生成成片或视觉质检结果。

## 7. 验收标准

1. 只有 ready preflight 能创建 `StoryboardVersion`；blocked 版本返回 `STORYBOARD_NOT_READY` 且无写入。
2. 创建与审批的重复请求只返回同一记录；不同 digest 的同 key 返回冲突。
3. 创建和批准都在事务内重检事实状态、excluded deny-set 与全文校验；事实降级期间无法写批准。
4. 批准后任一 selected fact 降级，读取结果为 `stale`；历史 event 不被修改。
5. 两张表的 update/delete 均由真实 PostgreSQL trigger 拒绝。
6. 相同 `StoryboardVersion` 始终导出相同 preview digest；预览不调用 Provider、不创建 Job、不出现报价或账务记录。
7. Web 刷新后能恢复 approval 状态；全程没有“生成视频”“充值”“发布”入口。
8. 后端 unit/integration、前端 unit/typecheck/build、Playwright E2E、迁移 upgrade/downgrade 均按 `docs/development/testing.md` 通过。

## 8. 实施前需用户确认的决定

1. 接受本切片新增两张追加式表及一次 migration。
2. 接受当前批准只代表本地操作者决定，不引入用户身份或多人审批。
3. 接受 approved 仅作为未来报价前门禁，绝不直接触发 Render。
4. 接受预览仅引用既有公开快照图片，上传和素材资产管理延后至 P2.1。

确认后按“模型 → migration/trigger → repository/application → API → Web → 测试 → 文档”顺序实施；P2.1 的报价、RenderJob、媒体 QA 与账务必须另行设计和批准。

## 9. 实施记录

- 已新增 `0005_storyboard_approval_preview`：两张表均使用 `RESTRICT` 外键、操作幂等唯一键和 PostgreSQL `BEFORE UPDATE OR DELETE` 拒绝 trigger；审批事件另有数据库序列，避免以时间戳推断最新决定。
- 预检摘要绑定 script version、冻结 generation input、snapshot、事实状态与顺序、脚本草案、冻结 pattern/version/phase sequence；预览摘要只包含快照图片索引，绝不保存或返回原始图片 URL。
- `approved` 仍只表示本地人工决定可作为未来报价门禁；没有任何 RenderJob、Provider、媒体、账务或发布调用。
