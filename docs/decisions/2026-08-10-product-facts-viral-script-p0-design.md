---
status: implemented
authority: regression-contract
---

# 商品事实＋爆款脚本 P0 设计规格

状态：已确认，可进入实施
日期：2026-08-10
目标仓库：`zjgulai/reverse_engineer_mode`
目标分支：`main`

## 1. 目标

构建一个可操作、可测试、可持续维护的完整 Web 产品工程，把商品来源转化为带证据的商品事实，再生成可校验、可追溯、可比较和可导出的结构化带货脚本。

P0 的完成标准不是“模型返回了一段文字”，而是以下闭环全部成立：

```text
商品录入或公开页面解析
→ 不可变商品快照
→ 带证据的事实提取
→ 人工确认、否决或锁定
→ 强类型脚本生成任务
→ 事实、时长、结构和禁用声明校验
→ 版本化脚本产物
→ Web 查看、比较和导出
```

## 2. P0 范围

### 2.1 包含

1. 手动录入商品。
2. 解析包含 Schema.org `Product` JSON-LD 的公开 HTTP/HTTPS 商品页。
3. 保存来源、原始内容摘要和不可变商品快照。
4. 建立商品事实台账，支持 `proposed / confirmed / rejected / locked` 状态。
5. 配置 15、30、45 秒脚本、语言、受众和创意结构。
6. 异步生成结构化脚本。
7. 校验脚本事实、时间轴、字段完整性和禁用声明。
8. 保存每一次脚本版本，不覆盖旧版本。
9. Web 展示任务状态、校验结果和版本差异。
10. 导出 JSON 和 Markdown。
11. 完整的本地开发环境、迁移、测试、构建、CI 和工程文档。

### 2.2 不包含

- 用户注册、登录、团队和多租户。
- 套餐、积分、支付和账务。
- 爆款榜单数据采集。
- 视频生成、字幕、配音和 TikTok 发布。
- 绕过目标站点访问限制、登录墙、反机器人或付费墙。
- 复制 Oumomo 的源码、私有提示词、训练数据或受保护媒体。

## 3. 架构选择

采用 React＋FastAPI 的单仓库模块化单体，业务状态统一落在 PostgreSQL，耗时任务由 Celery Worker 执行，Redis 只承担 broker/backend，不作为事实来源。

```text
React/Vite/TypeScript Web
          │ REST/OpenAPI
          ▼
FastAPI Application
          │
          ├── PostgreSQL：事实、任务、脚本和版本的唯一事实源
          ├── Redis：Celery broker/result backend
          └── Celery Worker
                 ├── ProductConnector
                 └── ScriptProvider
```

不使用 FastAPI 进程内 `BackgroundTasks` 执行商品抓取或 LLM 生成。FastAPI 官方文档指出重型、跨进程任务更适合 Celery 等队列；Celery 官方文档将 Redis 列为稳定 broker/backend。

## 4. 工程结构

```text
apps/
  api/
    pyproject.toml
    alembic.ini
    app/
      api/                 # FastAPI 路由、依赖、Problem Details
      application/         # 用例与事务边界
      domain/
        products/          # 商品快照、事实与状态规则
        scripts/           # 脚本、版本与校验规则
        jobs/              # 异步任务与幂等状态
      ports/               # Repository、Connector、Provider 接口
      adapters/
        db/                # SQLAlchemy repositories
        connectors/        # 手动和 Schema.org Product 连接器
        providers/         # 确定性和真实 LLM adapter
      worker/              # Celery app 和任务入口
      settings.py
      main.py
    tests/
      unit/
      integration/
  web/
    package.json
    src/
      api/                 # OpenAPI client 与错误合同
      components/          # 可复用基础组件
      features/
        products/
        facts/
        generations/
        scripts/
      routes/
      styles/
    tests/
      e2e/
migrations/
infra/
  docker-compose.yml
docs/
  architecture/
  development/
  superpowers/specs/
  superpowers/plans/
.github/workflows/ci.yml
.env.example
.gitignore
README.md
```

每个领域模块包含自己的实体、值对象、规则和 repository port。API 路由不直接执行 SQL 或调用模型；Celery 任务只负责恢复 application 用例并提交任务 ID。

## 5. 技术栈与版本策略

- Python 3.12。
- FastAPI、Pydantic v2。
- SQLAlchemy 2 async API、asyncpg、Alembic。
- PostgreSQL。
- Celery＋Redis。
- HTTPX，用于受控公开页面抓取。
- React＋Vite＋TypeScript。
- React Router、TanStack Query。
- 后端：pytest、pytest-asyncio、Ruff、mypy。
- 前端：Vitest、React Testing Library、Playwright、ESLint、TypeScript。
- Node.js 22.12 或更高的 22.x LTS；Vite 官方当前要求 Node.js 20.19+ 或 22.12+。
- npm 作为前端包管理器，不引入第二套包管理器。

依赖使用锁文件固定；升级必须通过测试、typecheck、build 和迁移验证。实现前以官方稳定版本为准，不使用 beta 版本。

## 6. 领域模型

### 6.1 ProductSource

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | UUID | 主键 |
| `source_type` | enum | `manual` 或 `schema_org_url` |
| `source_url` | text nullable | URL 来源必填 |
| `retrieved_at` | timestamptz | 服务端时间 |
| `content_digest` | char(64) | 规范化来源内容 SHA-256 |
| `raw_payload` | JSONB | 有大小上限的必要来源字段，不保存任意完整网页 |
| `parse_status` | enum | `pending / succeeded / failed` |
| `error_code` | text nullable | 稳定业务错误码 |

### 6.2 ProductSnapshot

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | UUID | 主键 |
| `source_id` | UUID | 外键 |
| `title` | text | 必填、去首尾空白 |
| `description` | text nullable | 纯文本 |
| `category_path` | JSONB | 字符串数组 |
| `images` | JSONB | 规范化公开图片 URL 数组 |
| `price_amount` | numeric nullable | 不使用浮点 |
| `price_currency` | char(3) nullable | ISO 4217 代码 |
| `canonical_digest` | char(64) | 规范化业务字段 SHA-256 |
| `created_at` | timestamptz | 不可变 |

同一来源重新解析时创建新快照。旧快照不更新；脚本版本始终绑定具体快照。

### 6.3 ProductFact

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | UUID | 主键 |
| `snapshot_id` | UUID | 外键 |
| `claim_type` | text | 例如 `feature / material / price / usage / audience` |
| `claim` | text | 面向脚本的事实表达 |
| `value` | JSONB | 类型化事实值 |
| `evidence_kind` | enum | `source_field / user_assertion` |
| `evidence_locator` | text | JSON path、字段名或用户证据标签 |
| `evidence_excerpt` | text | 有界纯文本证据 |
| `confidence` | numeric | 0 到 1 |
| `status` | enum | `proposed / confirmed / rejected / locked` |
| `updated_at` | timestamptz | 状态变化时间 |

只有 `confirmed` 或 `locked` 事实能支持可接受脚本中的商品声明。手工端点固定写入 `user_assertion/manual-form`，`source_field` 只能由受信 Connector 创建。事实证据字段创建后不可改写，`locked` 事实的任何变更都必须生成新事实记录。

### 6.4 CreativePattern

P0 内置版本化模式数据，不做后台管理页面。每个模式包括：

- `key`、`version`、`name`。
- `hook_type`。
- `phase_sequence`。
- `shot_roles`。
- 支持的目标时长。

初始提供七种结构：`problem_solution`、`demo_first`、`before_after`、`listicle`、`testimonial`、`myth_busting`、`offer_cta`。

### 6.5 Job

| 字段 | 类型 | 约束 |
|---|---|---|
| `id` | UUID | 主键 |
| `job_type` | enum | `product_import / script_generation` |
| `idempotency_key` | text | 与 job_type 联合唯一 |
| `state` | enum | 见状态机 |
| `input_digest` | char(64) | 创建后不可变 |
| `attempt_count` | integer | 从 0 开始 |
| `error_code` | text nullable | 稳定错误码 |
| `error_detail` | text nullable | 脱敏说明 |
| `created_at/started_at/finished_at` | timestamptz | 生命周期 |

### 6.6 ScriptGeneration 与 ScriptVersion

`ScriptGeneration` 保存商品快照、已确认事实 ID、用户配置、完整 CreativePattern 版本定义、provider/model、prompt contract 版本和输入摘要；Worker 不从部署时的最新 registry 重新解释旧任务。

`ScriptVersion` 保存：

```text
target_duration_seconds
language
audience
phases[]
  key, purpose, start_seconds, end_seconds
shots[]
  start_seconds, end_seconds, phase_key,
  voiceover, visual, action, caption, acceptance_shot,
  supported_fact_ids[]
titles[]
tags[]
shooting_list[]
validation_report
parent_version_id
created_at
```

同一次生成的修复结果使用 `parent_version_id` 关联。版本只能追加，不能覆盖。

## 7. 状态机与幂等

### 7.1 商品导入

```text
QUEUED → FETCHING → PARSING → SUCCEEDED
                           ↘ FAILED
```

### 7.2 脚本生成

```text
QUEUED → GENERATING → VALIDATING → SUCCEEDED
                │             ↘ VALIDATION_FAILED
                └──────────────→ FAILED
```

状态转换由服务端校验，客户端不能直接指定终态。

创建异步任务必须提供 `Idempotency-Key`。相同 job type、key 和 input digest 返回原任务；相同 key 配不同 input digest 返回 `409 IDEMPOTENCY_CONFLICT`。

Worker 重试只增加 attempt，不创建新逻辑 Job。`attempt_count` 同时作为执行 fencing token，所有中间态、失败态和结果写入都必须匹配启动时取得的 token；已经终态的任务不得回退。数据库/OS 瞬态错误不写业务 `FAILED`，而由 Celery 以指数退避重试并进入同一 fencing 路径。相同幂等请求若仍处于 `queued`，API 可安全重新发布任务，以修复数据库提交与 Broker 发布之间的进程崩溃窗口。

## 8. 商品解析与安全边界

URL 解析只支持公开 HTTP/HTTPS 页面和 Schema.org `Product` JSON-LD，不执行页面 JavaScript，不绕过访问控制。

抓取前后都执行：

1. 解析 URL，只允许 `http`、`https`。
2. 禁止 URL 用户信息、非标准端口和非公开主机。
3. 解析全部 A/AAAA 地址，阻止 loopback、private、link-local、multicast、reserved 和 unspecified 地址。
4. 默认不跟随重定向；如实现有限重定向，每一跳重新执行完整验证。
5. 连接、读取和总耗时均设置上限。
6. 限制响应体大小和允许的 HTML/JSON content type。
7. 在同一 DNS 快照内依次尝试已验证的公网地址，content type 采用精确 MIME 匹配。
8. Connector 提取和手工录入的图片数量、URL 长度均有上限，每张图片独立执行相同的公网 URL/DNS 策略。
9. 不把原始 HTML直接渲染到 Web。
10. 错误回退到手动录入，不调用 LLM 猜测缺失字段。

这些约束遵循 OWASP SSRF 防护的协议限制、IP 验证、DNS 解析和重定向防护原则。

## 9. AI Provider 合同

领域层只依赖：

```python
class ScriptProvider(Protocol):
    async def generate(self, request: ScriptGenerationRequest) -> ScriptDraft: ...
```

实现包括：

1. `DeterministicScriptProvider`：本地开发、测试和 E2E 使用，无外部调用，相同输入产生相同输出。
2. `OpenAICompatibleScriptProvider`：通过环境变量启用，要求强类型 JSON 输出；密钥不入库、不入日志。

Provider 输入只包含已选择的事实、用户配置和版本化 CreativePattern，不包含未确认事实或任意原始网页。

调用 Provider 前重新检查 selected facts；保存结果时在同一数据库事务中锁定并重读 facts。Provider 只能影响事实绑定的 voiceover/caption 与结构化时间轴，其余可见创意文案由服务端模板覆盖并再次校验。

首次响应不满足结构时允许一次格式修复，修复使用同一逻辑 Job 并记录 attempt。事实不受支持不是格式问题，不自动修复为另一个营销声明，而是进入 `VALIDATION_FAILED`。

## 10. 校验规则

### 10.1 结构完整性

- phases、shots、titles、tags 和 shooting_list 必须存在。
- 每个 shot 必须包含 voiceover、visual、action 和 acceptance_shot；caption 可为空字符串。
- phase key 必须被对应 shot 引用。

### 10.2 时间轴

- 第一镜从 0 秒开始。
- 镜头必须按时间排序，不能重叠。
- 相邻镜头间隙不超过 0.1 秒。
- 最后一镜结束时间与目标时长偏差不超过 0.5 秒。
- 英语口播使用 2.5 words/second 的保守上限；中文使用 4 characters/second。估算超过镜头时长即失败。该速率作为版本化配置保存，不写死在 UI。

### 10.3 事实支持

- 每个商品声明必须列出 `supported_fact_ids`。
- fact 必须属于当前 snapshot，且状态为 `confirmed` 或 `locked`。
- 脚本中的价格、功效、认证、材质、数量和用法不得从标题相似性推断。
- 没有事实支持的商品声明产生 blocking finding。
- voiceover/caption 必须逐字规范化匹配声明，声明必须逐字规范化匹配被引用事实。
- visual、action、acceptance_shot、phase purpose、titles、tags 和 shooting_list 必须来自服务端允许模板，否则产生 `CREATIVE_FIELD_UNTRUSTED`。

### 10.4 禁用声明

P0 阻断无法证实的医疗效果、保证性结果、虚构认证、虚假稀缺、虚构价格和竞品贬损。规则命中必须显示规则 ID、证据和脚本位置。

## 11. API 合同

主要端点：

```text
POST   /api/v1/products
POST   /api/v1/product-imports
GET    /api/v1/products
GET    /api/v1/products/{product_id}
POST   /api/v1/products/{product_id}/facts
PATCH  /api/v1/products/{product_id}/facts/{fact_id}
POST   /api/v1/products/{product_id}/script-generations
GET    /api/v1/jobs/{job_id}
GET    /api/v1/scripts/{script_id}
GET    /api/v1/scripts/{script_id}/versions
GET    /api/v1/scripts/{script_id}/versions/{version_id}
GET    /api/v1/scripts/{script_id}/versions/{version_id}/export?format=json|markdown
GET    /api/v1/creative-patterns
GET    /health/live
GET    /health/ready
```

创建异步任务返回 `202 Accepted`、Job resource 和 `Location`。错误使用 RFC 9457 Problem Details，并增加稳定的 `code`、`request_id` 和可选 `field_errors`。

## 12. Web 页面与交互

```text
/products
  商品列表、解析状态、新建入口

/products/new
  手动录入或公开 URL 导入

/products/:id
  快照、来源、事实台账、确认/否决/锁定

/products/:id/generate
  时长、语言、受众、CreativePattern 配置和事实预览

/jobs/:id
  queued/generating/validating/terminal 状态，刷新可恢复

/scripts/:id
  结构化脚本、校验 findings、版本选择和导出

/scripts/:id/compare?left=&right=
  字段级版本差异
```

Web 不展示模型私有推理，只展示输入事实、配置、任务事实、结构化产物和校验结果。所有阻断 finding 在结果顶部汇总，并能定位到具体 shot/field。

## 13. 错误处理

稳定错误类别：

- `UNSUPPORTED_SOURCE`
- `SOURCE_FETCH_BLOCKED`
- `SOURCE_FETCH_TIMEOUT`
- `SOURCE_TOO_LARGE`
- `PRODUCT_DATA_MISSING`
- `FACT_STATE_CONFLICT`
- `FACTS_NOT_READY`
- `IDEMPOTENCY_CONFLICT`
- `PROVIDER_UNAVAILABLE`
- `PROVIDER_RATE_LIMITED`
- `PROVIDER_OUTPUT_INVALID`
- `SCRIPT_VALIDATION_FAILED`
- `DEPENDENCY_UNAVAILABLE`

数据库、Redis 或 Provider 不可用时 fail-closed。页面提供恢复建议，但不得自动创建第二个逻辑任务。日志不包含 API key、完整原始网页、私有 URL 参数或模型供应商原始敏感响应。

## 14. 测试策略

### 14.1 后端单元测试

- canonical digest 稳定性。
- ProductFact 状态转换。
- locked fact 不可原地覆盖。
- 幂等键重放和冲突。
- Job 合法/非法状态转换。
- 脚本结构、时间轴、事实和禁用声明校验。
- DeterministicScriptProvider 合同。
- SSRF URL、IP 和重定向校验。

### 14.2 后端集成测试

- PostgreSQL repositories 和事务。
- Alembic 从空库升级到 head。
- FastAPI 成功与 Problem Details 合同。
- Celery 任务重复投递不产生重复版本。
- 进程重启后任务可从数据库恢复。

### 14.3 前端测试

- 商品录入表单。
- 事实确认、否决和锁定。
- 生成配置与缺失事实阻断。
- Job 轮询、刷新恢复和失败提示。
- 脚本字段、validation findings 和版本比较。

### 14.4 E2E

使用确定性 Provider 执行：

```text
手动创建商品
→ 新增并锁定事实
→ 提交 15 秒 problem_solution 脚本
→ 查看任务完成
→ 查看无 blocking finding 的脚本
→ 创建第二版本
→ 比较版本
→ 导出 JSON 和 Markdown
```

另一个 E2E 使用故意插入无证据声明的测试 Provider，证明结果进入 `VALIDATION_FAILED` 且 Web 明确阻断。

## 15. 项目治理

- 在 `main` 分支开发，不使用 worktree。
- 完成并通过验收后再创建提交并推送到 `origin/main`。
- `.env`、密钥、数据库、Redis 数据、下载内容、构建缓存和测试产物必须被 `.gitignore` 排除。
- `.env.example` 只包含无敏感值的配置名和安全默认值。
- CI 执行后端 lint、typecheck、unit/integration test，前端 lint、typecheck、unit test、build，以及 Alembic 迁移检查。
- README 必须包含启动、迁移、测试、真实 Provider 配置和故障排查。
- 长期架构知识记录在 `docs/architecture/`，并在根目录 `AGENTS.md` 要求后续任务先读取。

## 16. 本地运行与部署边界

本地提供 Docker Compose：

```text
web
api
worker
postgres
redis
```

一条文档化命令启动依赖与应用。API readiness 必须验证 PostgreSQL；Worker readiness 单独验证 Redis 和任务注册。P0 不承诺云生产部署，但容器、环境变量和健康检查必须保持可部署状态。

## 17. 验收标准

1. 新环境能按 README 启动 Web、API、Worker、PostgreSQL 和 Redis。
2. 用户能在 Web 手动录入商品，或解析受支持的公开 Schema.org Product 页面。
3. 商品快照不可变，事实有证据并能确认、否决和锁定。
4. 用户能创建脚本任务，刷新后仍能恢复同一 Job。
5. 相同幂等键和输入不会创建重复 Job 或 ScriptVersion。
6. 成功任务生成完整强类型脚本和校验报告。
7. 无依据商品声明进入 `VALIDATION_FAILED`，不会静默成为可接受版本。
8. 脚本版本不覆盖，能够比较并导出 JSON/Markdown。
9. 后端 lint、typecheck、测试和迁移检查通过。
10. 前端 lint、typecheck、测试和 production build 通过。
11. E2E 的成功路径与事实阻断路径通过。
12. 仓库不包含密钥、手机号、Cookie、Token、任务私有 ID 或媒体私有 URL。

## 18. 官方依据

- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [Celery Backends and Brokers](https://docs.celeryq.dev/en/latest/getting-started/backends-and-brokers/index.html)
- [Vite Getting Started](https://vite.dev/guide/)
- [SQLAlchemy asyncio](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [RFC 9457 Problem Details for HTTP APIs](https://www.rfc-editor.org/rfc/rfc9457.html)
- [OWASP SSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)

## 19. 已确认决策

- 独立新项目。
- Python 3.12＋FastAPI＋PostgreSQL。
- React＋Vite＋TypeScript Web。
- Redis＋Celery 持久异步任务。
- API-first，但 P0 必须同时提供可操作 Web。
- 完整项目治理、测试、迁移、CI 和文档。
- 完成后提交并推送到 `zjgulai/reverse_engineer_mode` 的 `main` 分支。
