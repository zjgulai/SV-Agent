# 商品事实＋爆款脚本 P0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付一个可操作的 React Web 和 FastAPI/Celery/PostgreSQL 后端，使用户能建立带证据的商品事实，异步生成、校验、版本化并导出结构化爆款脚本。

**Architecture:** 单仓库模块化单体。PostgreSQL 是唯一业务事实源，Redis 只承担 Celery broker/backend；API 通过 application use cases 驱动纯领域模型和 repository/provider ports，Web 只消费 REST/OpenAPI 合同。

**Tech Stack:** Python 3.12、uv、FastAPI、Pydantic v2、SQLAlchemy 2、Alembic、PostgreSQL、Celery、Redis、HTTPX、React 19、Vite 8、TypeScript 6、React Router、TanStack Query、pytest、Vitest、Playwright、Docker Compose、GitHub Actions。

## Global Constraints

- 规格来源：`docs/superpowers/specs/2026-08-10-product-facts-viral-script-p0-design.md`。
- 只在 `main` 分支开发，不创建 worktree。
- Python 固定为 3.12；Node 固定为 `>=22.12 <23`，不以本机 Node 26 作为生产基线。
- 所有 shell 命令必须以 `rtk` 开头。
- 严格 TDD：每个生产行为先写测试并观察正确失败，再写最小实现。
- 不新增账号、计费、榜单、视频生成或 TikTok 发布。
- 不绕过目标站点权限；URL 连接器只处理公开 Schema.org Product 页面。
- PostgreSQL 保存事实；Redis 丢失不能改变商品、任务或脚本终态。
- 不记录或提交 API key、Cookie、Token、手机号、完整私有 URL、原始完整网页和本地数据库。
- 不做中间 commit；全部验收通过后按用户授权创建一次最终 commit 并推送 `origin/main`。

---

### Task 1: 后端工程骨架与健康检查

**Files:**
- Create: `.python-version`
- Create: `apps/api/pyproject.toml`
- Create: `apps/api/app/__init__.py`
- Create: `apps/api/app/settings.py`
- Create: `apps/api/app/api/health.py`
- Create: `apps/api/app/main.py`
- Create: `apps/api/tests/unit/test_health.py`

**Interfaces:**
- Consumes: 无。
- Produces: `app.main.create_app() -> FastAPI`、`GET /health/live`、`GET /health/ready`。

- [x] **Step 1: 创建测试配置并写健康检查失败测试**

`apps/api/tests/unit/test_health.py`：

```python
from fastapi.testclient import TestClient

from app.main import create_app


def test_liveness_reports_service_identity() -> None:
    response = TestClient(create_app()).get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "reverse-engineer-mode-api"}
```

`apps/api/pyproject.toml` 使用以下可解析约束，最终精确版本由 `uv.lock` 固定：

```toml
[project]
name = "reverse-engineer-mode-api"
version = "0.1.0"
requires-python = ">=3.12,<3.13"
dependencies = [
  "alembic>=1.19,<2",
  "asyncpg>=0.30,<1",
  "celery[redis]>=5.6,<6",
  "fastapi>=0.116,<1",
  "httpx>=0.28,<1",
  "pydantic-settings>=2.10,<3",
  "sqlalchemy>=2.0,<2.1",
  "uvicorn[standard]>=0.35,<1",
]

[project.optional-dependencies]
dev = [
  "mypy>=1.17,<2",
  "pytest>=8.4,<9",
  "pytest-asyncio>=1.1,<2",
  "pytest-cov>=6.2,<7",
  "ruff>=0.12,<1",
]

[tool.pytest.ini_options]
pythonpath = ["."]
asyncio_mode = "auto"

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.mypy]
python_version = "3.12"
strict = true
```

- [x] **Step 2: 运行测试并确认正确失败**

Run: `rtk uv sync --project apps/api --python 3.12 --all-extras`
Run: `rtk uv run --project apps/api pytest apps/api/tests/unit/test_health.py -q`
Expected: collection fails because `app.main` does not exist。

- [x] **Step 3: 写最小 FastAPI 实现**

`apps/api/app/api/health.py`：

```python
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def liveness() -> dict[str, str]:
    return {"status": "ok", "service": "reverse-engineer-mode-api"}


@router.get("/health/ready")
async def readiness() -> dict[str, str]:
    return {"status": "ok"}
```

`apps/api/app/main.py`：

```python
from fastapi import FastAPI

from app.api.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(title="Reverse Engineer Mode API", version="0.1.0")
    app.include_router(health_router)
    return app


app = create_app()
```

- [x] **Step 4: 验证后端基线**

Run: `rtk uv run --project apps/api pytest apps/api/tests/unit/test_health.py -q`
Expected: 1 passed。
Run: `rtk uv run --project apps/api ruff check apps/api`
Run: `rtk uv run --project apps/api mypy apps/api/app`

---

### Task 2: 商品快照、内容摘要与事实状态

**Files:**
- Create: `apps/api/app/domain/common/canonical.py`
- Create: `apps/api/app/domain/products/entities.py`
- Create: `apps/api/app/domain/products/errors.py`
- Create: `apps/api/tests/unit/domain/products/test_entities.py`

**Interfaces:**
- Consumes: Python 标准库。
- Produces: `canonical_digest(value) -> str`、`ProductSnapshot.create(...)`、`ProductFact.transition_to(status)`、`FactStatus`。

- [x] **Step 1: 写商品领域失败测试**

```python
from decimal import Decimal
from uuid import UUID

import pytest

from app.domain.products.entities import FactStatus, ProductFact, ProductSnapshot
from app.domain.products.errors import LockedFactError

SOURCE_ID = UUID("00000000-0000-0000-0000-000000000001")
SNAPSHOT_ID = UUID("00000000-0000-0000-0000-000000000002")


def test_snapshot_digest_is_stable_for_equivalent_fields() -> None:
    left = ProductSnapshot.create(
        source_id=SOURCE_ID,
        title=" Pulse Mix ",
        description="Energy powder",
        category_path=("Food", "Drink Mix"),
        images=("https://example.com/a.png",),
        price_amount=Decimal("19.90"),
        price_currency="USD",
    )
    right = ProductSnapshot.create(
        source_id=SOURCE_ID,
        title="Pulse Mix",
        description="Energy powder",
        category_path=("Food", "Drink Mix"),
        images=("https://example.com/a.png",),
        price_amount=Decimal("19.900"),
        price_currency="usd",
    )

    assert left.canonical_digest == right.canonical_digest


def test_locked_fact_cannot_be_changed_in_place() -> None:
    fact = ProductFact.create(
        snapshot_id=SNAPSHOT_ID,
        claim_type="material",
        claim="The pouch is resealable",
        value={"resealable": True},
        evidence_kind="user_assertion",
        evidence_locator="manual-form",
        evidence_excerpt="Resealable pouch",
        confidence=1.0,
    ).transition_to(FactStatus.LOCKED)

    with pytest.raises(LockedFactError):
        fact.transition_to(FactStatus.REJECTED)
```

- [x] **Step 2: 运行并确认缺少领域模块**

Run: `rtk uv run --project apps/api pytest apps/api/tests/unit/domain/products/test_entities.py -q`
Expected: collection fails because `app.domain.products` does not exist。

- [x] **Step 3: 实现不可变实体与规范化摘要**

使用 frozen dataclass；摘要输入必须把 Decimal 转为规范字符串、货币转大写、字符串去首尾空白、字典键排序，并以 UTF-8 JSON 计算 SHA-256。`ProductFact.transition_to()` 返回新实例；locked 状态的任何原地状态变化抛出 `LockedFactError`。

- [x] **Step 4: 验证商品领域行为**

Run: `rtk uv run --project apps/api pytest apps/api/tests/unit/domain/products/test_entities.py -q`
Expected: 2 passed。
Run: `rtk uv run --project apps/api pytest apps/api/tests/unit -q`

---

### Task 3: 脚本强类型合同与四类校验器

**Files:**
- Create: `apps/api/app/domain/scripts/models.py`
- Create: `apps/api/app/domain/scripts/validation.py`
- Create: `apps/api/app/domain/scripts/patterns.py`
- Create: `apps/api/tests/unit/domain/scripts/test_validation.py`

**Interfaces:**
- Consumes: `FactStatus` 和当前 snapshot 的 facts。
- Produces: `ScriptDraft`、`ScriptShot`、`ValidationFinding`、`ValidationReport`、`validate_script(draft, facts) -> ValidationReport`、`CREATIVE_PATTERNS`。

- [x] **Step 1: 写脚本校验失败测试**

```python
from uuid import UUID

from app.domain.scripts.models import ScriptDraft, ScriptPhase, ScriptShot
from app.domain.scripts.validation import validate_script

FACT_ID = UUID("00000000-0000-0000-0000-000000000010")


def test_validator_blocks_claim_without_supported_fact() -> None:
    draft = ScriptDraft(
        target_duration_seconds=15,
        language="en",
        audience="busy professionals",
        phases=[ScriptPhase(key="hook", purpose="Open", start_seconds=0, end_seconds=15)],
        shots=[ScriptShot(
            start_seconds=0,
            end_seconds=15,
            phase_key="hook",
            voiceover="This guarantees an energy boost.",
            visual="Show the pouch.",
            action="Hold the pouch.",
            caption="",
            acceptance_shot="Pouch name is readable.",
            supported_fact_ids=[],
            product_claims=["guarantees an energy boost"],
        )],
        titles=["A better routine"],
        tags=["routine"],
        shooting_list=["pouch"],
    )

    report = validate_script(draft, facts={})

    assert report.acceptable is False
    assert [(item.rule_id, item.path) for item in report.blocking] == [
        ("FACT_UNSUPPORTED", "shots[0].product_claims[0]"),
        ("CLAIM_GUARANTEE", "shots[0].voiceover"),
    ]
```

- [x] **Step 2: 运行并确认缺少脚本模块**

Run: `rtk uv run --project apps/api pytest apps/api/tests/unit/domain/scripts/test_validation.py -q`
Expected: collection fails because `app.domain.scripts` does not exist。

- [x] **Step 3: 实现脚本模型、七种模式和校验管线**

校验顺序固定为 structure、timeline、factuality、prohibited claims；findings 按 `(path, rule_id)` 排序，保证重复执行稳定。时间轴规则实现 0 秒起始、无重叠、间隙不超过 0.1 秒、终点偏差不超过 0.5 秒、英语 2.5 words/s、中文 4 chars/s。

- [x] **Step 4: 增加通过、时间轴失败和跨 snapshot fact 测试**

测试必须使用手工期望值，并证明：完整脚本可接受；镜头重叠产生 `TIMELINE_OVERLAP`；fact 不属于当前 snapshot 产生 `FACT_WRONG_SNAPSHOT`。

- [x] **Step 5: 验证脚本领域**

Run: `rtk uv run --project apps/api pytest apps/api/tests/unit/domain/scripts -q`
Expected: all passed。
Run: `rtk uv run --project apps/api mypy apps/api/app/domain`

---

### Task 4: PostgreSQL 模型、事务与首个迁移

**Files:**
- Create: `infra/docker-compose.yml`
- Create: `apps/api/alembic.ini`
- Create: `apps/api/app/adapters/db/base.py`
- Create: `apps/api/app/adapters/db/models.py`
- Create: `apps/api/app/adapters/db/session.py`
- Create: `apps/api/app/adapters/db/repositories.py`
- Modify: `apps/api/app/api/health.py`
- Create: `migrations/env.py`
- Create: `migrations/versions/0001_p0_core.py`
- Create: `apps/api/tests/integration/conftest.py`
- Create: `apps/api/tests/integration/test_product_repository.py`

**Interfaces:**
- Consumes: Task 2、Task 3 的领域对象。
- Produces: `ProductRepository`、`JobRepository`、`ScriptRepository` 的 SQLAlchemy 实现和 `async_sessionmaker`。

- [x] **Step 1: 写 repository 持久化失败测试**

```python
async def test_product_repository_appends_snapshot_without_overwriting_previous(
    product_repository: ProductRepository,
    sample_snapshot: ProductSnapshot,
) -> None:
    first = await product_repository.add_snapshot(sample_snapshot)
    second = await product_repository.add_snapshot(
        ProductSnapshot.create(
            source_id=sample_snapshot.source_id,
            title="Pulse Mix Updated",
            description=sample_snapshot.description,
            category_path=sample_snapshot.category_path,
            images=sample_snapshot.images,
            price_amount=sample_snapshot.price_amount,
            price_currency=sample_snapshot.price_currency,
        )
    )

    stored = await product_repository.list_snapshots(sample_snapshot.source_id)

    assert [item.id for item in stored] == [first.id, second.id]
    assert stored[0].title == "Pulse Mix"
```

`apps/api/tests/integration/conftest.py` 定义真实 PostgreSQL `async_engine`、每测试事务回滚的 `db_session`、`product_repository`，以及标题固定为 `Pulse Mix` 的 `sample_snapshot`；环境变量只从 `TEST_DATABASE_URL` 读取。

- [x] **Step 2: 启动依赖并确认测试因表缺失而失败**

Run: `rtk docker compose -f infra/docker-compose.yml up -d postgres redis`
Run: `rtk uv run --project apps/api pytest apps/api/tests/integration/test_product_repository.py -q`
Expected: fails because persistence tables/repository are absent。

- [x] **Step 3: 实现 SQLAlchemy 模型和 repository**

所有 JSON 字段使用 JSONB，价格使用 Numeric，枚举由应用校验并以字符串保存，时间统一为 timezone-aware UTC。repository 不执行隐式 commit；application transaction boundary 负责 commit/rollback。

- [x] **Step 4: 创建并应用 `0001_p0_core` 迁移**

迁移创建 product_sources、product_snapshots、product_facts、jobs、script_generations、script_versions，并建立 job type＋idempotency key 唯一约束与必要外键。

- [x] **Step 5: 验证迁移和 repository**

Run: `rtk uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head`
Run: `rtk uv run --project apps/api pytest apps/api/tests/integration/test_product_repository.py -q`
Run: `rtk uv run --project apps/api alembic -c apps/api/alembic.ini downgrade base`
Run: `rtk uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head`

同时把 `/health/ready` 改为执行 `SELECT 1`；集成测试证明 PostgreSQL 可用返回 200，dependency override 注入失败 session 时返回 503 `DEPENDENCY_UNAVAILABLE`。

---

### Task 5: 手动商品 API、Problem Details 与事实工作流

**Files:**
- Create: `apps/api/app/api/problems.py`
- Create: `apps/api/app/api/schemas/products.py`
- Create: `apps/api/app/api/routes/products.py`
- Create: `apps/api/app/application/products.py`
- Modify: `apps/api/app/main.py`
- Create: `apps/api/tests/integration/api/conftest.py`
- Create: `apps/api/tests/integration/api/test_products.py`

**Interfaces:**
- Consumes: `ProductRepository`、ProductSnapshot/ProductFact。
- Produces: `POST/GET /api/v1/products`、`POST/PATCH facts` 和 RFC 9457 `ProblemDetails`。

- [x] **Step 1: 写手动商品与 locked fact 冲突 API 失败测试**

```python
def test_create_manual_product_returns_snapshot_and_proposed_facts(client: TestClient) -> None:
    response = client.post("/api/v1/products", json={
        "title": "Pulse Mix",
        "description": "Resealable drink mix pouch",
        "category_path": ["Food", "Drink Mix"],
        "images": ["https://example.com/pulse.png"],
        "price": {"amount": "19.90", "currency": "USD"},
        "facts": [{
            "claim_type": "feature",
            "claim": "The pouch is resealable",
            "value": {"resealable": True},
            "evidence_excerpt": "Resealable drink mix pouch",
        }],
    })

    assert response.status_code == 201
    body = response.json()
    assert body["snapshot"]["title"] == "Pulse Mix"
    assert body["facts"][0]["status"] == "proposed"
```

- [x] **Step 2: 运行并确认路由缺失**

Run: `rtk uv run --project apps/api pytest apps/api/tests/integration/api/test_products.py -q`
Expected: 404 for `/api/v1/products`。

- [x] **Step 3: 实现 application use case、schemas 和路由**

`create_manual_product()` 在一个事务中创建 manual ProductSource、ProductSnapshot 和 proposed facts。状态冲突返回 `application/problem+json`，含 `type`、`title`、`status`、`detail`、`code`、`request_id`。

`apps/api/tests/integration/api/conftest.py` 使用 FastAPI dependency override 注入 Task 4 的真实测试 session，暴露 `client` fixture；每个测试结束后回滚，不用 mock repository。

- [x] **Step 4: 增加事实确认、否决、锁定与冲突测试**

证明 proposed→confirmed→locked 成功，locked→rejected 返回 `409 FACT_STATE_CONFLICT`，数据库仍保持 locked。

- [x] **Step 5: 验证商品 API**

Run: `rtk uv run --project apps/api pytest apps/api/tests/integration/api/test_products.py -q`
Run: `rtk uv run --project apps/api pytest apps/api/tests/unit apps/api/tests/integration -q`

---

### Task 6: SSRF 防护与 Schema.org Product 导入

**Files:**
- Create: `apps/api/app/adapters/connectors/ssrf.py`
- Create: `apps/api/app/adapters/connectors/schema_org.py`
- Create: `apps/api/app/ports/product_connector.py`
- Create: `apps/api/app/application/product_imports.py`
- Create: `apps/api/app/api/routes/product_imports.py`
- Create: `apps/api/tests/fixtures/product_page.py`
- Create: `apps/api/tests/unit/connectors/test_ssrf.py`
- Create: `apps/api/tests/unit/connectors/test_schema_org.py`
- Create: `apps/api/tests/integration/api/test_product_imports.py`

**Interfaces:**
- Consumes: Product application 和 Job repository。
- Produces: `SsrfGuard.validate(url) -> ValidatedPublicUrl`、`SchemaOrgProductConnector.fetch(url)`、`POST /api/v1/product-imports`。

- [x] **Step 1: 写 SSRF 和 JSON-LD 解析失败测试**

```python
@pytest.mark.parametrize("url", [
    "file:///etc/passwd",
    "http://127.0.0.1/product",
    "http://[::1]/product",
    "http://169.254.169.254/latest/meta-data",
    "http://user:pass@example.com/product",
])
async def test_ssrf_guard_blocks_non_public_targets(url: str) -> None:
    with pytest.raises(SourceFetchBlocked):
        await SsrfGuard(resolver=StaticResolver({
            "127.0.0.1": ["127.0.0.1"],
            "::1": ["::1"],
            "169.254.169.254": ["169.254.169.254"],
            "example.com": ["93.184.216.34"],
        })).validate(url)


def test_schema_org_parser_extracts_only_product_fields() -> None:
    product = parse_schema_org_product(PRODUCT_HTML_FIXTURE)

    assert product.title == "Pulse Mix"
    assert product.price_amount == Decimal("19.90")
    assert product.price_currency == "USD"
    assert "<script" not in product.description
```

`StaticResolver` 定义在测试文件内并实现与生产 resolver 相同的 `resolve(host) -> tuple[str, ...]` 合同；`PRODUCT_HTML_FIXTURE` 定义在 `apps/api/tests/fixtures/product_page.py`，包含完整、手工核对的 Schema.org Product JSON-LD。

- [x] **Step 2: 运行并确认连接器缺失**

Run: `rtk uv run --project apps/api pytest apps/api/tests/unit/connectors -q`
Expected: collection fails because connector modules do not exist。

- [x] **Step 3: 实现安全 guard、有限 fetch 和 JSON-LD parser**

只允许标准 80/443 端口，默认不跟随重定向，解析全部 A/AAAA，拒绝非 public IP；HTTPX 设置 connect/read/total timeout 和 1 MiB 上限，仅接受 HTML/JSON。parser 使用 Python HTMLParser 收集 `application/ld+json`，只保存 Product 必要字段。

安全拒绝统一映射为 `SOURCE_FETCH_BLOCKED`；连接超时、响应过大和缺少 Product 数据分别映射为 `SOURCE_FETCH_TIMEOUT`、`SOURCE_TOO_LARGE`、`PRODUCT_DATA_MISSING`。

- [x] **Step 4: 实现导入 Job API**

`POST /product-imports` 要求 `Idempotency-Key`，返回 202 和 Location；P0 API 在事务中创建 QUEUED Job，Celery 执行由 Task 7 接管。

- [x] **Step 5: 验证安全连接器和导入合同**

Run: `rtk uv run --project apps/api pytest apps/api/tests/unit/connectors apps/api/tests/integration/api/test_product_imports.py -q`

---

### Task 7: Job 幂等、Celery Worker 与确定性脚本 Provider

**Files:**
- Create: `apps/api/app/domain/jobs/entities.py`
- Create: `apps/api/app/domain/jobs/errors.py`
- Create: `apps/api/app/ports/script_provider.py`
- Create: `apps/api/app/adapters/providers/deterministic.py`
- Create: `apps/api/app/adapters/providers/openai_compatible.py`
- Create: `apps/api/app/worker/celery_app.py`
- Create: `apps/api/app/worker/tasks.py`
- Create: `apps/api/app/application/generations.py`
- Create: `apps/api/tests/unit/domain/jobs/test_job.py`
- Create: `apps/api/tests/unit/providers/test_deterministic.py`
- Create: `apps/api/tests/unit/providers/test_openai_compatible.py`
- Create: `apps/api/tests/integration/test_generation_worker.py`

**Interfaces:**
- Consumes: Product facts、CreativePattern、ScriptDraft/validator、repositories。
- Produces: `Job.transition_to()`、`SupportedFact`、`ScriptGenerationRequest`、`ScriptProvider.generate()`、`DeterministicScriptProvider`、`OpenAICompatibleScriptProvider`、Celery tasks `import_product(job_id)` 和 `generate_script(job_id)`。

- [x] **Step 1: 写 Job 状态和确定性 Provider 失败测试**

```python
def test_terminal_job_cannot_return_to_running() -> None:
    job = Job.new(JobType.SCRIPT_GENERATION, "key-1", "a" * 64)
    job = job.transition_to(JobState.GENERATING)
    job = job.transition_to(JobState.VALIDATING)
    job = job.transition_to(JobState.SUCCEEDED)

    with pytest.raises(InvalidJobTransition):
        job.transition_to(JobState.GENERATING)


async def test_deterministic_provider_returns_same_script_for_same_request() -> None:
    provider = DeterministicScriptProvider()
    request = ScriptGenerationRequest(
        snapshot_id=UUID("00000000-0000-0000-0000-000000000020"),
        title="Pulse Mix",
        facts=[SupportedFact(
            id=UUID("00000000-0000-0000-0000-000000000021"),
            claim="The pouch is resealable",
            claim_type="feature",
        )],
        target_duration_seconds=15,
        language="en",
        audience="busy professionals",
        creative_pattern_key="problem_solution",
    )

    first = await provider.generate(request)
    second = await provider.generate(request)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
```

- [x] **Step 2: 运行并确认模块缺失**

Run: `rtk uv run --project apps/api pytest apps/api/tests/unit/domain/jobs apps/api/tests/unit/providers -q`
Expected: collection fails because job/provider modules do not exist。

- [x] **Step 3: 实现状态机、provider port 和确定性实现**

确定性 Provider 必须从已确认 facts 生成保守口播，每个 product claim 都绑定 fact ID；相同输入 JSON 产生相同镜头与标题。七种 CreativePattern 至少共享同一强类型输出合同。

- [x] **Step 4: 实现 generation use case 和 Celery 任务**

use case 使用数据库 terminal-state guard；重复投递已终态 Job 时直接返回现有结果。Celery task 只接收 job UUID，不序列化完整业务 payload。

- [x] **Step 5: 实现并验证真实 Provider adapter**

`OpenAICompatibleScriptProvider` 使用注入的 HTTPX AsyncClient、base URL、model 和 API key，发送版本化 JSON schema，解析为 `ScriptDraft`。测试用 HTTPX MockTransport 返回完整供应商响应，分别验证成功、429→`PROVIDER_RATE_LIMITED`、超时→`PROVIDER_UNAVAILABLE`、非结构化响应触发一次修复后失败→`PROVIDER_OUTPUT_INVALID`；测试断言真实 adapter 的领域结果，不断言 transport 调用次数。

- [x] **Step 6: 验证重复投递和 Redis 丢失不改变事实**

Run: `rtk uv run --project apps/api pytest apps/api/tests/integration/test_generation_worker.py -q`
测试连续执行两次 `generate_script(job_id)`，断言只有一个 ScriptVersion；清除 Celery result 后 PostgreSQL 仍返回 SUCCEEDED。

---

### Task 8: 脚本、Job、版本比较与导出 API

**Files:**
- Create: `apps/api/app/api/schemas/scripts.py`
- Create: `apps/api/app/api/routes/jobs.py`
- Create: `apps/api/app/api/routes/scripts.py`
- Create: `apps/api/app/application/exports.py`
- Create: `apps/api/app/application/version_diff.py`
- Modify: `apps/api/app/main.py`
- Create: `apps/api/tests/integration/api/test_scripts.py`

**Interfaces:**
- Consumes: Task 7 generation service、ScriptRepository。
- Produces: script generation、Job 状态、版本列表/详情/比较、JSON/Markdown 导出端点。

- [x] **Step 1: 写生成幂等和 validation_failed API 失败测试**

```python
def test_repeated_generation_key_returns_same_job(client: TestClient) -> None:
    ready_product_id = create_ready_product(client)
    payload = {
        "target_duration_seconds": 15,
        "language": "en",
        "audience": "busy professionals",
        "creative_pattern_key": "problem_solution",
    }
    headers = {"Idempotency-Key": "script-001"}

    first = client.post(
        f"/api/v1/products/{ready_product_id}/script-generations",
        json=payload,
        headers=headers,
    )
    second = client.post(
        f"/api/v1/products/{ready_product_id}/script-generations",
        json=payload,
        headers=headers,
    )

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["id"] == second.json()["id"]
```

同一测试文件中的 `create_ready_product(client) -> str` 必须通过真实 API 创建商品、创建 fact 并执行 proposed→confirmed→locked，返回 product ID；不得直接写数据库绕过应用规则。

- [x] **Step 2: 运行并确认路由缺失**

Run: `rtk uv run --project apps/api pytest apps/api/tests/integration/api/test_scripts.py -q`
Expected: 404 for script generation endpoint。

- [x] **Step 3: 实现 routes、schemas、diff 和 export**

Markdown 导出顺序固定为 metadata、validation summary、phases、shots、titles、tags、shooting list。版本 diff 输出字段级 `added/removed/changed`，不比较数据库内部 ID 和 created_at。

- [x] **Step 4: 增加 JSON/Markdown、facts_not_ready 和 idempotency conflict 测试**

不同 input 使用同一 key 返回 `409 IDEMPOTENCY_CONFLICT`；无 confirmed/locked facts 返回 `409 FACTS_NOT_READY`；validation_failed 版本可查看但 `acceptable=false`。

- [x] **Step 5: 验证完整后端**

Run: `rtk uv run --project apps/api pytest apps/api/tests/unit apps/api/tests/integration -q`
Run: `rtk uv run --project apps/api ruff check apps/api migrations`
Run: `rtk uv run --project apps/api mypy apps/api/app`

---

### Task 9: React 工程骨架与商品事实工作台

**Files:**
- Create: `apps/web/package.json`
- Create: `apps/web/package-lock.json`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/vite.config.ts`
- Create: `apps/web/index.html`
- Create: `apps/web/src/main.tsx`
- Create: `apps/web/src/App.tsx`
- Create: `apps/web/src/api/client.ts`
- Create: `apps/web/src/routes/ProductsPage.tsx`
- Create: `apps/web/src/routes/NewProductPage.tsx`
- Create: `apps/web/src/routes/ProductDetailPage.tsx`
- Create: `apps/web/src/styles/index.css`
- Create: `apps/web/src/test/setup.ts`
- Create: `apps/web/src/test/TestApp.tsx`
- Create: `apps/web/src/test/server.ts`
- Create: `apps/web/src/test/handlers.ts`
- Create: `apps/web/src/routes/__tests__/products.test.tsx`

**Interfaces:**
- Consumes: Product REST 和 RFC 9457 合同。
- Produces: `/products`、`/products/new`、`/products/:id` 可操作页面。

- [x] **Step 1: 创建前端测试配置并写失败测试**

`apps/web/package.json`：

```json
{
  "name": "reverse-engineer-mode-web",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "engines": {"node": ">=22.12 <23"},
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "eslint .",
    "typecheck": "tsc -b --pretty false",
    "test": "vitest",
    "e2e": "playwright test"
  },
  "dependencies": {
    "@tanstack/react-query": "5.101.4",
    "react": "19.2.8",
    "react-dom": "19.2.8",
    "react-router-dom": "7.18.2"
  },
  "devDependencies": {
    "@eslint/js": "10.0.1",
    "@playwright/test": "1.62.1",
    "@testing-library/jest-dom": "7.0.1",
    "@testing-library/react": "16.3.2",
    "@testing-library/user-event": "14.6.3",
    "@types/react": "19.2.18",
    "@types/react-dom": "19.2.4",
    "@vitejs/plugin-react": "6.0.5",
    "eslint": "10.8.1",
    "eslint-plugin-react-hooks": "7.1.1",
    "eslint-plugin-react-refresh": "0.5.4",
    "globals": "17.9.0",
    "jsdom": "30.0.1",
    "msw": "2.15.0",
    "typescript": "6.0.3",
    "typescript-eslint": "8.67.0",
    "vite": "8.2.1",
    "vitest": "4.1.10"
  }
}
```

```tsx
it("creates a manual product and shows proposed facts", async () => {
  const user = userEvent.setup();
  render(<TestApp initialEntries={["/products/new"]} />);

  await user.type(screen.getByLabelText("商品名称"), "Pulse Mix");
  await user.type(screen.getByLabelText("商品描述"), "Resealable drink mix pouch");
  await user.click(screen.getByRole("button", { name: "保存商品" }));

  expect(await screen.findByRole("heading", { name: "Pulse Mix" })).toBeVisible();
  expect(screen.getByText("待确认事实")).toBeVisible();
});
```

使用 MSW 拦截 API，但断言真实 React 路由、表单状态和渲染结果，不断言 mock 调用次数。

`src/test/server.ts` 创建唯一 `setupServer`；`src/test/setup.ts` 在 beforeAll/afterEach/afterAll 中启动、重置和关闭；`TestApp` 组合 MemoryRouter、QueryClientProvider 和真实 routes，Task 10 继续复用同一测试入口。

- [x] **Step 2: 安装依赖并确认页面缺失**

Run: `rtk npm --prefix apps/web install`
Run: `rtk npm --prefix apps/web test -- --run src/routes/__tests__/products.test.tsx`
Expected: fails because `TestApp`/routes do not exist。

- [x] **Step 3: 实现应用 shell、API client 和商品页面**

API client 把非 2xx 统一解析为 `ProblemDetails`；页面提供 loading、empty、error 和 success 状态。事实台账每条显示 claim、证据、confidence 和状态，并提供确认、否决、锁定按钮。

- [x] **Step 4: 增加 URL 导入、locked 冲突和刷新恢复测试**

URL 导入只提交公开 URL；409 在事实条目旁显示服务端 detail；直接打开 `/products/:id` 能从 API 恢复页面。

- [x] **Step 5: 验证商品 Web**

Run: `rtk npm --prefix apps/web test -- --run`
Run: `rtk npm --prefix apps/web run lint`
Run: `rtk npm --prefix apps/web run typecheck`
Run: `rtk npm --prefix apps/web run build`

---

### Task 10: 脚本配置、任务进度、结果和版本比较 Web

**Files:**
- Create: `apps/web/src/routes/GenerateScriptPage.tsx`
- Create: `apps/web/src/routes/JobPage.tsx`
- Create: `apps/web/src/routes/ScriptPage.tsx`
- Create: `apps/web/src/routes/CompareVersionsPage.tsx`
- Create: `apps/web/src/features/generations/useJobPolling.ts`
- Create: `apps/web/src/features/scripts/ValidationPanel.tsx`
- Create: `apps/web/src/features/scripts/ScriptTimeline.tsx`
- Create: `apps/web/src/routes/__tests__/generation.test.tsx`
- Create: `apps/web/src/routes/__tests__/script.test.tsx`

**Interfaces:**
- Consumes: CreativePattern、generation、Job、script/version/diff/export API。
- Produces: `/products/:id/generate`、`/jobs/:id`、`/scripts/:id`、`/scripts/:id/compare`。

- [x] **Step 1: 写任务刷新恢复和阻断 finding 失败测试**

```tsx
it("restores a queued job and stops polling at validation_failed", async () => {
  render(<TestApp initialEntries={["/jobs/job-1"]} />);

  expect(await screen.findByText("正在生成")).toBeVisible();
  expect(await screen.findByText("脚本包含无证据声明")).toBeVisible();
  expect(screen.getByRole("status")).toHaveTextContent("校验未通过");
  expect(screen.getByRole("link", { name: "查看脚本" })).toHaveAttribute(
    "href",
    "/scripts/script-1",
  );
});
```

- [x] **Step 2: 运行并确认 generation routes 缺失**

Run: `rtk npm --prefix apps/web test -- --run src/routes/__tests__/generation.test.tsx`
Expected: fails because JobPage/useJobPolling do not exist。

- [x] **Step 3: 实现配置、轮询和结果组件**

轮询只在 QUEUED/FETCHING/PARSING/GENERATING/VALIDATING 状态运行；terminal 状态立即停止。配置页只列出 confirmed/locked facts，提交时生成稳定 idempotency key 并保存在 sessionStorage，刷新不重复创建逻辑任务。

- [x] **Step 4: 实现版本比较和导出链接**

比较页按 phases/shots/titles/tags 展示 added/removed/changed；blocking findings 置顶并定位到 shot path。导出使用后端 URL，不在前端重新拼 Markdown。

- [x] **Step 5: 验证完整 Web**

Run: `rtk npm --prefix apps/web test -- --run`
Run: `rtk npm --prefix apps/web run lint`
Run: `rtk npm --prefix apps/web run typecheck`
Run: `rtk npm --prefix apps/web run build`

---

### Task 11: Docker、E2E、CI、工程文档与最终发布

**Files:**
- Modify: `infra/docker-compose.yml`
- Create: `apps/api/Dockerfile`
- Create: `apps/web/Dockerfile`
- Create: `apps/web/playwright.config.ts`
- Create: `apps/web/tests/e2e/p0-success.spec.ts`
- Create: `apps/web/tests/e2e/p0-validation-failure.spec.ts`
- Create: `.github/workflows/ci.yml`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `README.md`
- Create: `AGENTS.md`
- Create: `docs/architecture/p0-architecture.md`
- Create: `docs/development/testing.md`

**Interfaces:**
- Consumes: 全部 P0 API、Worker 和 Web 行为。
- Produces: 一条命令本地栈、两条浏览器 E2E、CI、开发文档和可发布仓库。

- [x] **Step 1: 写成功路径与事实阻断 E2E**

成功路径必须通过 UI 完成手动商品、locked fact、15 秒 problem_solution、Job terminal、版本二、版本比较和 JSON/Markdown 导出。失败路径使用确定性 provider 对真实 guarantee claim 生成的脚本，断言 `validation_failed`、blocking finding 和不可接受标识。

- [x] **Step 2: 运行 E2E 并确认基础设施缺失**

Run: `rtk npm --prefix apps/web run e2e`
Expected: fails because full Compose services/baseURL are not configured。

- [x] **Step 3: 完成容器、环境和 CI**

Compose 包含 web、api、worker、postgres、redis，健康检查和依赖顺序明确；`.env.example` 使用 deterministic provider 安全默认值。CI 使用 PostgreSQL/Redis services，执行迁移、后端 lint/typecheck/tests、前端 lint/typecheck/tests/build 和 Playwright。

- [x] **Step 4: 写 README、AGENTS 和长期架构文档**

README 覆盖 prerequisites、复制环境、启动、迁移、测试、OpenAPI、真实 provider 环境变量和故障排查。`AGENTS.md` 要求后续任务先读设计规格、架构和测试文档，并保留 main/no-worktree/敏感数据规则。

- [x] **Step 5: 运行完整验收**

Run: `rtk docker compose -f infra/docker-compose.yml up -d --build`
Run: `rtk uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head`
Run: `rtk uv run --project apps/api ruff check apps/api migrations`
Run: `rtk uv run --project apps/api mypy apps/api/app`
Run: `rtk env TEST_DATABASE_URL=postgresql+asyncpg://reverse_engineer_mode:local-development-only@localhost:55432/reverse_engineer_mode uv run --project apps/api pytest apps/api/tests -q`
Run: `rtk npm --prefix apps/web run lint`
Run: `rtk npm --prefix apps/web run typecheck`
Run: `rtk npm --prefix apps/web test -- --run`
Run: `rtk npm --prefix apps/web run build`
Run: `rtk npm --prefix apps/web run e2e`
Run: `rtk git diff --check`

- [x] **Step 6: 执行发布前敏感信息与仓库范围审计**

确认 `.env`、数据库、Redis、node_modules、`.venv`、coverage、Playwright artifacts、`work/` 和无关 `outputs/oumomo-audit/` 未被跟踪。允许纳入本次逆向证据的范围仅为 `outputs/oumomo-reverse-engineering/`。

- [x] **Step 7: 创建唯一最终提交并推送**

Run: `rtk git add .github .dockerignore .gitignore .python-version .env.example AGENTS.md README.md apps docs infra migrations outputs/oumomo-reverse-engineering`
Run: `rtk git status --short`
Run: `rtk git commit -m "feat: build product facts and viral script P0"`
Run: `rtk git push -u origin main`

推送后以 `git status --short --branch`、`git log -1 --oneline` 和远端 `refs/heads/main` 验证，不以命令静默作为成功证据。
