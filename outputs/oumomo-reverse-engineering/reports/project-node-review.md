# 当前项目逐节点深度复盘

审查基线：2026-08-11 `main` 工作区。结论来自当前代码、迁移、测试入口与 Oumomo 实测；不把 README、营销文案或前端可见性当成实现完成。

## 总结

当前项目已经形成一个可运行的 P0：公开/手工商品输入 → 不可变商品快照 → 事实确认/锁定 → 幂等脚本任务 → Provider → 服务端创意合同 → 事实与结构校验 → 追加式脚本版本 → Web 查看、diff、导出。其核心优势是“事实门和执行可追溯”，不是生成文本的丰富度。

| 维度 | 当前判断 | 价值 | 技术壁垒 | 完成复杂度 |
|---|---|---:|---:|---:|
| 事实可信与版本追溯 | P0 最强节点 | ★★★★★ | ★★★★☆ | ★★★★☆ |
| 异步任务可靠性 | 已有 fencing、重投与数据库终态；仍缺 outbox/reconciler | ★★★★★ | ★★★★★ | ★★★★★ |
| 脚本事实校验 | 安全强、创意弱 | ★★★★★ | ★★★★☆ | ★★★★☆ |
| Web 工作台 | 主链可操作，编辑/恢复/历史不足 | ★★★★☆ | ★★☆☆☆ | ★★★☆☆ |
| URL 商品覆盖 | 安全边界强，真实电商覆盖窄 | ★★★☆☆ | ★★★★☆ | ★★★★☆ |
| 视频与发布 | 尚未进入当前工程范围 | ★★★★★ | ★★★★★ | ★★★★★ |

## 1. 输入与 HTTP 合同

**实现路径**：`apps/api/app/api/schemas/products.py`、`apps/api/app/api/schemas/scripts.py`、`apps/api/app/api/routes/products.py`、`apps/api/app/api/routes/product_imports.py`、`apps/api/app/api/routes/scripts.py`。

**输入 → 输出**：

- 手工商品、公开 URL、事实状态、生成配置 → Pydantic 类型和 RFC 9457 Problem Details。
- `Idempotency-Key` → 持久化 Job 与 `Location` 头。
- 脚本/版本读取 → 类型化 Draft、ValidationReport、diff 与下载。

**实际价值**：★★★★★；**技术壁垒**：★★★☆☆；**复杂度**：★★★☆☆。

**已覆盖失败**：字段长度、价格范围、未知商品/版本、事实未就绪、非法 pattern/时长、幂等冲突、Provider/Broker 不可用。

**开放缺口**：

- 无用户、组织、角色和资源所有权；任何可访问 API 的调用者可读取/修改全部资源。
- 派生版本 POST 没有幂等键；网络重试可追加重复版本。
- `derive` 只允许改一个标题，尚不是完整脚本编辑合同。
- Job API 没有事件时间线、取消、人工重试或恢复建议；客户端只能轮询当前快照。

## 2. 商品来源与 URL 导入

**实现路径**：`apps/api/app/adapters/connectors/ssrf.py`、`schema_org.py`、`application/product_imports.py`、`worker/tasks.py`。

**输入 → 输出**：公开、无凭证、无 query/fragment、标准端口 HTTP(S) URL → DNS 公网校验 → 固定 IP/SNI 下载 → 1 MiB 内的 HTML/JSON-LD → Schema.org Product 快照与 proposed facts。

**实际价值**：★★★★☆；**技术壁垒**：★★★★★；**复杂度**：★★★★☆。

**已覆盖失败**：私网/回环/多地址污染、DNS 超时、重绑定、代理和重定向、错误端口、过大响应、非白名单 MIME、HTTP/网络超时、无 Product 数据、并发同 URL 收敛。

**开放缺口**：

- `ProductSource.raw_payload`、digest、retrieved_at 和 parse 状态在再次导入时原地更新；旧 Snapshot 虽保留，但完整的每次抓取证据与失败历史没有保留。
- 缺少独立 `ImportAttempt`：看不到每次 DNS/IP、开始/结束时间、状态、错误和响应摘要。
- 仅取第一个 Product，且只覆盖标题、描述、品类、图片、价格；brand、SKU、variant、availability、shipping 等未建模。
- 整段 description 被提议为单一事实，粒度过粗。Oumomo 的 S-F01/S-O01 实验证明“删除/排序卖点”若没有细粒度事实和负约束会被模型重新生成。
- 禁止 query、redirect 和 JavaScript 的安全策略会排除大量真实商城链接；应增加受信连接器，不应放宽通用抓取器。
- 价格属于时变事实，目前没有有效期或重新确认策略。

## 3. 商品快照与事实台账

**实现路径**：`domain/products/entities.py`、`application/products.py`、`adapters/db/models.py`、`repositories.py`、迁移 `0002`/`0003`。

**输入 → 输出**：规范化商品字段 → canonical digest 与追加式 Snapshot；证据声明 → proposed/confirmed/rejected/locked Fact。

**实际价值**：★★★★★；**技术壁垒**：★★★★☆；**复杂度**：★★★★☆。

**已覆盖失败**：手工事实被服务端强制标记 `user_assertion/manual-form`；只有连接器可写 `source_field`；Snapshot 不可更新/删除；Fact 证据字段不可变、Fact 不可删除、locked 后不可再变更。

**开放缺口**：

- 非 locked Fact 的状态迁移没有状态图限制，rejected 可直接回 confirmed/locked；需要审计事件而不只是最后状态。
- `selected_fact_ids` 是 JSON 字符串数组，无数据库外键与同 Snapshot 约束；正确性依赖 Worker 重读。
- Web 没有“新增事实”“替代旧事实”“查看快照历史”“查看证据来源原文”的完整流程。
- 当前自动选择所有 confirmed/locked facts；用户不能明确选择、排序、排除或声明“禁止再生”的事实。

## 4. 生成命令与 CreativePattern

**实现路径**：`application/generations.py`、`domain/scripts/patterns.py`、`ports/script_provider.py`。

**输入 → 输出**：snapshot digest、全部就绪事实、时长、语言、受众、pattern、provider/model → immutable ScriptGeneration 与 Job。

**实际价值**：★★★★★；**技术壁垒**：★★★★☆；**复杂度**：★★★★☆。

**已覆盖失败**：未知 pattern、pattern 不支持时长、无可用事实、同 key 不同输入冲突；完整 pattern definition/version 被固化进 generation 和 input digest。

**开放缺口**：

- 七种 pattern 目前都是四阶段/四镜头骨架，缺少每个阶段的事实角色、证据槽、允许话术和验收规则。
- 没有 promotion 事实类型、优惠有效期和渠道约束。S-P01 证明未经验证的 `10%` 输入会被网站扩写成多处促销话术。
- 没有候选数、创意温度、语气、地域、负约束和受众安全边界的类型化合同。
- 没有 ProviderRun/attempt 记录；无法把 Provider 时延、修复次数、请求摘要和账单与业务 Job 分开审计。

## 5. Provider 适配层

**实现路径**：`adapters/providers/deterministic.py`、`openai_compatible.py`、`settings.py`。

**输入 → 输出**：类型化 ScriptGenerationRequest → strict JSON-schema ScriptDraft；最多一次格式修复。

**实际价值**：★★★★☆；**技术壁垒**：★★★★☆；**复杂度**：★★★★☆。

**已覆盖失败**：空 API key、超时、连接失败、429、非 JSON/错误 schema、额外字段、一次修复仍失败；错误映射为稳定业务代码。

**开放缺口**：

- “OpenAI-compatible” 单一协议不能表达不同 Provider 的 schema、seed、成本、内容安全和幂等能力。
- 在无供应商幂等的重试/Worker redelivery 中会再次调用外部 Provider；内部 fencing 可阻止重复保存，但不能阻止外部重复计费。
- 只保存最终 typed draft，不保存脱敏 request/response digest、provider request ID、token/cost/latency。
- deterministic Provider 适合验收，不代表真实生成质量；生产 Provider 尚无真实端到端接受证据。

## 6. 创意合同与事实校验

**实现路径**：`domain/scripts/creative_contract.py`、`models.py`、`validation.py`。

**输入 → 输出**：Provider Draft + persisted facts/pattern → 服务端覆盖非声明字段 → 结构、时间、事实、创意、禁词 Findings → acceptable/blocked。

**实际价值**：★★★★★；**技术壁垒**：★★★★★；**复杂度**：★★★★☆。

**已覆盖失败**：空结构、未知阶段、时间重叠/缝隙/不闭合、语速超限、每镜头无 claim、voiceover/caption 与声明不一致、Fact 不存在/跨 Snapshot/非就绪/claim 不匹配、非服务端 visual/action/title/tag/list、六类禁词。

**当前优势**：Oumomo 的 S-B01/S-T02/U-B01 都出现无证据功效、包装或价格扩写；本项目通过“原句事实绑定 + 服务端拥有其他可见文案”从结构上阻止这类漂移。

**开放缺口**：

- exact-match 事实门安全但非常僵硬，口播与字幕只能逐字复述事实，缺少“经人工批准的等价表达”。
- 每个镜头都必须有商品 claim，hook/transition/CTA 也被迫重复事实。
- visual/action/acceptance/title/tag 被覆盖为同一组通用模板，安全性高但商业创意价值低。
- 禁词仅为窄正则，不是完整政策/地区/品类规则系统；当前安全主要依赖 claim 精确绑定。
- 没有画面级可验证对象、OCR 文本、包装字段或媒体 acceptance contract。U-B01 的包装乱码不会被当前脚本校验覆盖。

## 7. Job、Celery 与失败恢复

**实现路径**：`domain/jobs/entities.py`、`application/dispatch.py`、`application/generations.py`、`worker/tasks.py`、`worker/celery_app.py`。

**输入 → 输出**：持久 Job UUID → DB 锁定与 fencing token → Worker 阶段迁移 → 数据库终态/结果。

**实际价值**：★★★★★；**技术壁垒**：★★★★★；**复杂度**：★★★★★。

**已覆盖失败**：首次提交、同输入重放、不同输入冲突、Broker 调用失败、普通重复投递、Celery redelivery/retry、Worker lost、stale Worker、GENERATING/VALIDATING 恢复、数据库/OS 暂态失败、terminal replay、Redis 结果丢失、Fact TOCTOU。

**开放缺口**：

- DB commit 到 `.delay()` 之间仍无 transactional outbox；相同请求重放可以补投，但客户端不再请求时 queued Job 没有自主恢复。
- 无后台 reconciler、stuck-at-95% 检测、最大运行时长或 dead-letter 策略；`max_retries=None` 可无限重试基础设施错误。
- Broker 首次失败被记为 terminal FAILED；同 idempotency key 不会再次投递，需要新的显式 retry contract。
- Job 只有最终 error 和时间戳，没有 append-only JobEvent/Attempt 供 UI 展示真实阶段。
- U-B01 实证前端错误后任务仍成功，因此客户端必须有 `unknown/recovering` 状态，当前 Web 只有 Job URL 已知后的恢复。

## 8. PostgreSQL、迁移与不可变性

**实现路径**：`adapters/db/models.py`、`repositories.py`、`migrations/versions/0001_*` 至 `0003_*`。

**输入 → 输出**：领域实体 → PostgreSQL JSONB/关系表、唯一约束、外键、trigger。

**实际价值**：★★★★★；**技术壁垒**：★★★★☆；**复杂度**：★★★★☆。

**已覆盖失败**：Snapshot/Generation/Version update/delete 被 trigger 拒绝；Fact delete 和证据更新被拒绝；locked 状态不可变；同 URL/同 idempotency key 唯一。

**开放缺口**：

- Job.result_id 与 selected_fact_ids 无关系型外键，错误只能在应用运行期发现。
- JSONB Draft/Validation/Pattern Definition 无数据库 schema version/check，后续演进需应用层迁移策略。
- ProductSource 与 Job 会原地更新；没有 append-only Attempt/Event 层。
- 无 tenant_id、行级所有权和审计 actor。

## 9. 版本、diff 与导出

**实现路径**：`application/version_diff.py`、`exports.py`、`api/routes/scripts.py`。

**输入 → 输出**：parent ScriptVersion → 新追加版本；任意同 Script 两版本 → field-level diff；Version → JSON/Markdown。

**实际价值**：★★★★☆；**技术壁垒**：★★★☆☆；**复杂度**：★★★☆☆。

**已覆盖失败**：跨 Script 比较/导出被拒绝；diff 忽略 ID/创建时间；导出包含 provider/model/pattern/input digest/validation。

**开放缺口**：

- 派生只修改标题，且前端固定生成 `Version 2`；从 Version 2 再派生会构造不符合 safe-title pattern 的标题。
- 派生版本没有 author、reason、operation idempotency 或 optimistic concurrency。
- diff 对数组按索引扁平化；镜头插入会造成大量噪声，缺少稳定 shot ID/语义 diff。
- 导出缺少 source/fact evidence bundle、完整 pattern definition 和校验器版本。

## 10. 安全、配置与可运维性

**实现路径**：`settings.py`、`api/health.py`、`api/problems.py`、Compose/Docker 配置。

**输入 → 输出**：环境配置和依赖状态 → readiness/liveness、稳定错误、Provider/Broker/DB 边界。

**实际价值**：★★★★☆；**技术壁垒**：★★★★☆；**复杂度**：★★★★☆。

**已覆盖失败**：数据库不可用、Provider 空/空白 key、敏感 key 仅环境变量、稳定错误不回显 URL、HTTPX 禁环境代理。

**开放缺口**：

- 无 authentication、authorization、rate limit、CSRF/CORS 明确策略、审计 actor 和秘密轮换流程。
- readiness 不验证 Redis/Broker 连通性，也不做 Provider 轻量探针；只能证明 DB 与静态配置可用。
- 无结构化 metrics/tracing、Job backlog/stuck/attempt 指标和告警。
- 迁移与应用版本没有生产部署/回滚接受证据。

## 11. Web 页面与用户工作流

**实现路径**：`apps/web/src/routes/*`、`features/generations/useJobPolling.ts`、`features/scripts/*`、`api/client.ts`。

**输入 → 输出**：商品创建/URL 导入、事实状态、生成配置 → Job 恢复 → 脚本时间线、校验、版本、diff、导出。

**实际价值**：★★★★☆；**技术壁垒**：★★☆☆☆；**复杂度**：★★★☆☆。

**已实现**：

- 商品列表、空态、新建、URL/手工双入口。
- Fact evidence/status 展示与状态按钮。
- 15/30/45 秒、语言、受众、七类结构选择。
- sessionStorage 幂等 key、PostgreSQL Job 轮询、终态跳转。
- 脚本时间线、Finding 定位、版本选择、diff、JSON/Markdown 下载。
- 非 JSON 代理错误有稳定 fallback，解决 Oumomo “HTML 被当 JSON”类崩溃。

**开放缺口**：

- 不是编辑器：不能编辑镜头、事实映射、标题/标签、受众或负约束后再校验。
- 不能选择、排序、删除或明确排除 facts；与 S-O01/S-F01 暴露的关键产品需求不匹配。
- URL import 成功后只进入最新商品；没有导入尝试与 Snapshot 历史视图。
- Polling 固定 1 秒，没有 exponential backoff、页面隐藏暂停、未知响应恢复、最后成功读取时间或手动重新连接。
- 多个错误页只给通用文案，未显示稳定 code/恢复动作；产品列表失败没有重试按钮。
- 无全局脚本版本列表，导航中的“脚本版本”仍是静态文本。
- 无移动端/键盘/屏幕阅读器专项验收，未接入 axe；当前只能说语义标签存在，不能宣称无障碍完成。

## 12. 测试与发布可信度

**实现路径**：`apps/api/tests`、`apps/web/src/routes/__tests__`、`apps/web/tests/e2e`、`docs/development/testing.md`。

**实际价值**：★★★★★；**技术壁垒**：★★★★☆；**复杂度**：★★★★☆。

**已覆盖范围**：真实 PostgreSQL integration、Provider MockTransport、SSRF、并发、append-only trigger、Celery fencing/retry/replay、Web real router/QueryClient/MSW、成功与 validation-failure E2E。

**开放缺口**：

- 测试绿色只能证明当前本地/CI 合同；尚无真实生产 Provider、真实 Broker 宕机恢复、部署、备份恢复和多租户隔离验收。
- E2E 只覆盖主成功和校验失败；未覆盖 URL import、Broker 失败、unknown-response 恢复、重复点击、移动端和无障碍。
- U-B01 表明“终态成功”不代表事实/包装/媒体质量成功；未来视频测试必须拆分 Job、事实、视觉、OCR、音频与发布 preflight。

## 建议优先级

1. **立即做 P1 脚本工作台**：事实选择/排序/排除、候选版本、可编辑结构、实时校验、恢复状态。
2. **随后做 P1.5 可靠与 SaaS 底座**：outbox/reconciler、ImportAttempt/JobEvent、完整 pattern、tenant/auth/RBAC。
3. **最后做 P2 preview-first 视频**：先冻结事实和脚本，先低成本 storyboard/关键帧/OCR，再决定是否调用昂贵视频模型。

不建议先复制 Oumomo 的模型聚合、数字人或“官方加权发布”营销层。当前最难且最有复用价值的是事实、版本、幂等、恢复和媒体验收合同。
