# P1 / P1.5 / P2 可执行路线

## 目标排序

```text
P1 事实驱动脚本工作台
  └─先解决用户可控、事实不漂移、版本可比较
      ↓
P1.5 可靠执行与 SaaS 边界
  └─再解决自动补投、历史、权限和规模化
      ↓
P2 Preview-first 视频流水线
  └─最后把已验收脚本编译成可验收媒体
```

排序依据：S-B01/S-T02/S-P01/S-O01/S-F01 证明脚本事实漂移是高频且低成本可修的核心问题；U-B01 证明直接进入视频会同时放大任务恢复、包装文字、事实与成本风险。

## P1：事实驱动脚本工作台

**目标**：把现有 P0 从“安全生成与查看器”升级成真正可操作的脚本工作台。

### P1.1 Fact selection contract（已实施）

- 生成前显式选择 Fact IDs，不再自动使用全部 confirmed/locked facts。
- 支持顺序、exclude IDs 和负约束；选择与排除列表均进入 generation digest。
- 每个 Fact 显示证据、状态和 Snapshot；服务端验证归属、去重、互斥和 selected 状态。
- Worker、派生版本、导出和 storyboard preflight 均重读同一冻结合同。

**验收**：重现 S-O01/S-F01：排序改变结构分配，排除的 blue/aesthetic fact 不得出现在 claim、标题、字幕或画面 acceptance contract。

### P1.1.1 只读 storyboard preflight（已实施）

- ScriptVersion 在进入任何预览或渲染工作之前，重读冻结的 selected/excluded fact contract，并重新运行现有事实、排除和创意字段校验。
- 输出固定的阶段/镜头、每镜事实 ID、纳入事实顺序、排除事实与 validation findings；结果只有 ready 或 blocked。
- 该切片不调用 Provider、不生成媒体、不写入数据库、不产生报价、积分或 RenderJob。它是 P2 的前置证据门，而不是视频预览或可发布资源。

**验收**：接受版本显示 ready 且保留事实顺序；阻断版本显示 findings 并明确不可进入渲染；路由、领域测试、API 集成测试和浏览器 E2E 都覆盖该门。

### P1.2 Candidate and editor

**P1.2a 事实重绑版本（本地已实施）**：工作台只允许把每个既有分镜重新绑定到 generation 冻结合同中的 confirmed/locked Fact；服务端从事实原句重建 voiceover、caption、product claim 和支持 Fact ID，并重新验证后追加 ScriptVersion。请求只包含 `fact_bindings` 和 Idempotency-Key；相同父版本、相同键和相同输入只返回同一 child，键复用但输入不同返回冲突。版本保存固定 `fact_rebind/local_operator/fact_rebind` provenance，数据库禁止半写或伪造该 provenance。

**明确未实施**：一次生成 2–3 个 candidate、phase/shot 时间编辑、标题/标签/自由口播编辑、人工等价表达、自由 author/reason，以及任何进入视频的动作。这些项目需要 P1.3 pattern/creative-slot 或 P1.5.3 tenant/approval 合同后另行批准，不能借 P1.2a 的事实重绑入口绕过。

**验收**：阻断父版本、排除/过期/非冻结事实、缺失或重复 shot index 都不能写 child；成功 child 仅在事实绑定字段发生变化，保留父版时间线与服务器创意字段；重复网络请求只产生一个版本，且可比较、导出和进入既有 storyboard preflight。

### P1.3 Pattern compiler

**P1.3a/P1.3b Pattern compiler（本地实施中）**：P1.3a 已冻结每个 generation 的完整 PatternDefinition。获得产品确认后，P1.3b 为新 generation 定义 15 秒 3 阶段/4 镜头、30 秒 4 阶段/6 镜头、45 秒 5 阶段/8 镜头的确定性默认；各 pattern 保留自己的 server-owned phase/role 语义。该 30 秒 6 镜头是本项目稳定默认，不宣称是站点的私有固定输出：实验中同为 4 阶段的镜头数出现了 4/5/6/8 方差。新 `p1.3b`/`1.2` 合同、预算、语速、字段归属与 CTA policy 都进入 generation 配置及输入摘要；Provider、renderer、validator、storyboard 和 rebind 均从持久化合同读取。旧 `1.0` 与 `p1.3a` generation 只使用各自保存的合同，绝不通过新版 registry 重解释。

**P1.3c audience/promotion（本地已实施）**：未来 generation 使用五个闭合 audience profile，且只改变冻结的 server-owned 场景、道具和拍摄槽；Provider 不接收 profile 或这些 copy。Promotion Fact 通过专用 API 以用户断言创建，当前仅支持 TikTok Shop US / America/Los_Angeles 的 percent/amount-off 窗口，并只能由服务器写入最终 CTA。它在 queue、Worker、版本保存、preflight 与 approval 重新检查；无效时失败关闭。自由受众、优惠码、价格比较、倒计时、限量、多市场、多渠道、报价、视频生成和发布仍未实施。

### P1.4 Recovery UX

- 客户端保存 operation key、Job URL、最后已知状态和最后读取时间。
- response parse/timeout 后进入 `unknown/recovering`，先按 key/Job 恢复，禁止直接再次提交。
- Polling 支持 backoff、页面隐藏暂停、手动重新连接和稳定 error code 对应动作。

**P1.4.1 本地已实施**：公开 URL 导入与事实脚本生成使用版本化浏览器会话
记录；202 非 JSON 仅在安全 Job `Location` 下打开既有任务，其他未知结果只能以
原 body 与原幂等键恢复。此实现不新增后端查询接口、数据库记录或匿名重试入口。

**验收**：模拟 U-B01 的 HTML/JSON 错误，页面不得出现“重新生成”；恢复同一 Job 后进入最终版本且 submit count 仍为 1。

**P1.4.2 本地验收闭环（已实施）**：Promotion Fact 不能进入 selected/excluded 事实集合；Web 对不在有效窗的 confirmed/locked Promotion 显示为不可选择。真实 PostgreSQL 测试覆盖 Provider 调用前和版本保存前失效，以及 storyboard preflight/approval 的失败关闭；Compose 浏览器测试覆盖最终 CTA 限制、否决后的 stale，以及真实后端受理后浏览器接收 HTML 202 或连接中断时的同键恢复。浏览器异常由路由注入制造，不能替代生产代理/部署验收。

### P1 完成门

- 现有后端、Web unit 与两条 E2E 全绿。
- 新增 fact order/exclude、promotion expiry、duplicate derive、unknown-response recovery E2E。
- 导出包含 selected/excluded facts、pattern definition/version、validator version 与完整 findings。

## P1.5：可靠执行、历史与 SaaS 权限

### P1.5.1 Transactional outbox and reconciler（本地已实施）

- Job 与 OutboxEvent 同事务提交；Publisher 以 lease/fencing 投递 Celery。
- Reconciler 仅扫描 queued Job 的 pending 或过期 delivery；运行中的 Worker 从不自动接管。
- P1.5.1b 已增加指数退避、`max attempts/max age` 与 Outbox dead-letter。broker 投递耗尽仍保留业务 Job 为 queued；恢复只能由部署内 operator command 创建下一投递周期，Web 不提供匿名重试。

**已落地边界**：Job、初始 JobEvent 与 OutboxEvent 同事务提交；API 只 nudge 当前 Job，独立 reconciler 用 lease/token 重投 pending 或过期 delivery。broker 不可用不再把业务 Job 伪造为 FAILED；耗尽后写 `dispatch_dead_lettered` 并停止投递。运行中的 Worker 不自动接管，避免重复外部调用。

### P1.5.2 ImportAttempt and JobEvent（本地已实施）

- `ProductSource` 保留稳定身份；每次抓取写 append-only ImportAttempt。
- Attempt 保存时间、规范 URL digest、DNS/IP digest、响应摘要、错误、Snapshot ID；不保存凭证或完整页面。
- 每次 Job 状态变更写 JobEvent，UI 展示事实阶段而不是假进度百分比。

**已落地边界**：每次 fetch 写 `started/parsed/terminal` immutable ImportAttempt；每个 Job 状态/attempt/delivery 变化写 immutable JobEvent。Job 页面和只读 API 只显示实际阶段、错误代码与摘要，不显示假进度、原始网页或 URL。

### P1.5.3 SaaS security

- User/Organization/Membership、tenant_id、资源所有权、RBAC。
- OAuth/session、CSRF/CORS、rate limit、审计 actor、secret rotation。
- 所有 product/job/script/export 查询强制 tenant scope；增加跨租户 integration tests。

### P1.5.4 Provider execution record

- append-only ProviderRun/Attempt：provider/model、contract version、input/output digest、latency、usage/cost、repair count、provider request ID hash、error。
- 优先使用供应商幂等键；没有外部幂等时在 UI 明示“内部防重复保存不等于防重复计费”。

### P1.5 完成门

当前仅完成 P1.5.1/1.2（含 P1.5.1b 投递死信）的本地可靠性门，不代表整个 P1.5（SaaS security 与 Provider execution record 仍未实施）完成。

- 杀死 API 于 DB commit/.delay 边界后，outbox 自动投递且只产生一个 Job。
- 杀死 Worker 于 GENERATING/VALIDATING 任意点，旧 token 无法覆盖新 attempt。
- 同一 URL 多次成功/失败导入均可重建时间线，旧 Snapshot 证据不被覆盖。
- tenant A 无法读取、猜测或导出 tenant B 的任何 UUID 资源。

## P2：Preview-first 视频流水线

**目标**：不复制 Oumomo 的“一键生成”黑盒；把视频拆成可预览、可验收、可恢复、可计费的阶段。

### P2.0 分镜审核与零成本预览（已实施，未部署）

- 先把 ready 的只读 preflight 冻结为 append-only `StoryboardVersion`，审批单独写 append-only `ApprovalEvent`；当前决定由最新事件和实时事实重检派生为 `approved`、`rejected` 或 `stale`。
- 预览为确定性 HTML animatic：只显示阶段、镜头、事实绑定、口播/字幕、验收描述和既有公开图片索引；不调用 Provider、不生成媒体、不创建 Job，也不出现报价、积分或发布。`0005` 为 storyboard 与 approval event 添加数据库不可变 trigger，审批事件以序列定义最新事件。
- 已新增两张表、不可变 trigger 与 migration；边界固定为“本地操作者批准”“批准仅进入未来报价前门禁”“无上传素材”。

详细合同和验收标准见 [`docs/decisions/2026-08-14-storyboard-approval-preview-p2-design.md`](../../../docs/decisions/2026-08-14-storyboard-approval-preview-p2-design.md)。

### P2.1 Media contract

- ScriptVersion → StoryboardVersion → RenderJob → MediaArtifact。
- 每个 shot 固化：时段、Fact IDs、spoken/caption、reference assets、visual acceptance、禁止文字、商品 identity anchors。
- Artifact 保存 sha256、mime、bytes、时长、尺寸、fps、codec、音频、provider/model/version 与父版本。

### P2.2 Cheap preview before render

- 先生成 storyboard/关键帧/低分辨率 preview；先做 OCR、包装文字、颜色/Logo、构图与事实检查。
- 人工批准 preview 后才获取不可变报价并触发高成本视频。
- 包装上不允许模型自由生成的精确文字必须使用合成 overlay/原始资产，不交给视频模型重绘。

**对应实验**：U-B01 场景和人物连续，但包装文字严重乱码，且 prompt 自相矛盾地要求“不得发明”同时发明包装与 200mg 功效。

### P2.3 Quote, ledger and operation recovery

- PreflightQuote 绑定 input digest、model、duration、resolution、count、expires_at。
- CreditReservation/Charge/Refund 与 RenderJob 分离；客户端只显示数据库账务事实。
- response 异常进入 recovery；按 operation key 找同一 Job，禁止二次扣费。

### P2.4 Media QA

- 技术：容器、codec、时长、尺寸、fps、音频、黑帧、冻结帧、响度。
- 内容：ASR 与批准口播、OCR 与允许文字、镜头结构、Fact 保持、包装/颜色/Logo、人物/手部一致性。
- 评分器用 D-00…D-05 受控降质校准；同文件重复波动和子分单调性不过关，不对外展示总分。

### P2.5 Project and publish boundary

- Project 聚合 source/snapshot/script/storyboard/render/artifact，但各资源仍有独立版本和状态。
- 发布只接受 `accepted` Artifact；先生成 PublishDraft，填写平台、账号、商品、标题、标签、AI 标识、隐私、排期和 preflight。
- OAuth、账号绑定和最终 publish 必须二次确认；保存外部 receipt 与可撤销状态。

**对应实验**：P-DRY 观察到 video、cover、account、title、tags、product、product name、precheck、AI label、schedule；这些应成为类型化 PublishDraft，而不是页面临时状态。

### P2 完成门

- 未接受 storyboard 不得创建付费 RenderJob。
- 不支持 Fact 的 spoken/caption/visual/OCR 会阻断 Artifact acceptance。
- HTML/JSON 错误、页面关闭、Redis 丢失后仍能恢复唯一 RenderJob 与账务。
- 发布 E2E 使用 fake provider；任何真实 OAuth/发布需要独立人工授权和外部 receipt 验收。

## 明确不做

- 不自研基础视频/图片/数字人模型；只做 adapter、router、quote、provenance 和 QA。
- 不复制“92.27% 去重成功率”“账号权重加持”等无法独立复现的主张。
- 不在 P1/P1.5 未完成前建设大而全的模型市场。
- 不把 Job `succeeded` 当成事实、视觉、音频或发布验收通过。
