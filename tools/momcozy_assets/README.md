# Momcozy Local Asset Archive

这个目录只包含可提交的归档工具和测试，不包含任何商业媒体、平台任务标识、浏览器状态或账号数据。

## 目录职责

- `contracts.py`：定义每个本地商业素材包必须具备的文件、哈希和隐私边界。
- `validate.py`：验证单个素材包或整个素材库的结构与敏感字段约束。
- `archive_batch.py`：将已经通过正常项目页下载的图片或 ZIP 导出包拆分成“一图一文件夹”的可追溯素材包。
- `aggregate_index.py`：对一个明确批准的 Brand Workspace 根目录执行全量 census、Bundle 验证、scoped index/ledger/plan 对账，并生成确定性的全库 JSON 与 Markdown Index。
- `private_gate.py`：只读核验新鲜 Aggregate Index、已发布 current release 与固定无敏感字段基线；它不发布、不修复，也不更新基线。
- `tests/`：覆盖完整素材包、敏感标识拒绝、单组归档和 ZIP 安全解包。

真实输出必须保存在被 Git 忽略的 `outputs/momcozy-content-assets/`。每个素材目录只保存 `asset.*`、`prompt.md`、`recipe.json`、`provenance.json`、`qa.md` 与 `hashes.sha256`；不得写入原始平台任务 ID、签名 URL、Cookie、授权头或账号信息。

## 验证

```bash
rtk uv run --project apps/api python -m unittest discover -s tools/momcozy_assets/tests -v
rtk uv run --project apps/api ruff check tools/momcozy_assets
rtk uv run --project apps/api python -m tools.momcozy_assets.validate outputs/momcozy-content-assets/<batch-root>
```

### Synthetic CI 的运行时间与判定

公开测试会在临时目录中构造完整的 `244` Bundle synthetic library。为验证 Private Gate 的真实 fail-closed 合同，正常路径需要一次 baseline compile、一次 Aggregate Index CLI 发布，以及 Private Gate 内部两次 fresh compile；它不是读取 ignored 的真实素材库。

在 2026-09-23 的当前本机环境中，完整公开 suite 为 `53` tests / `195.050s`，单条 `test_approved_current_passes_without_writing_private_library` 为 `10.620s`。这只是本机观测基线，不是 CI SLA；性能会随文件系统、Python 和硬件变化。

某些终端包装会在子进程退出前聚合 unittest 输出。因此短时间没有逐例 stdout 不能单独判定 hang；应以明确的退出码、单条正常 Private Gate 测试和完整 suite 结果共同判断。排障时先分层运行 `test_contracts`、`test_aggregate_index` 和这条正常 Private Gate 测试；不要用小于其已观测正常时长的临时 timeout 将 fail-closed 全库验证误报为死锁。

GitHub Actions 也按同一边界拆成三条具名的 synthetic CI 步骤：Layer 1 运行 `test_contracts`、Ruff 和生产工具 Mypy（3 分钟）；Layer 2 运行 `test_aggregate_index`（5 分钟）；Layer 3 运行完整 `test_private_gate`（10 分钟）。每层在 Job Summary 中只写入层级、公开 synthetic scope 和通过结果，详细测试输出保留在该步骤日志。步骤 timeout 是为可诊断的 CI 上限，不是性能 SLA；Layer 3 仍然只验证 synthetic Private Gate 合同，绝不读取真实库或生成本机 Gate Receipt。

## 归档 ZIP 示例

```bash
rtk uv run --project apps/api python -m tools.momcozy_assets.archive_batch \
  --plan <batch-plan.json> \
  --output-root outputs/momcozy-content-assets/<batch-root> \
  --job-id <planned-asset-id> \
  --zip <project-ui-download.zip> \
  --observed-at <ISO-8601-time> \
  --reference-sha256 <official-reference-sha256>
```

该工具拒绝覆盖既有素材目录，并拒绝 ZIP 路径穿越、加密/符号链接/非图片条目、单文件超过 32MiB 或总解压大小超过 128MiB 的 ZIP；完成后仍须运行素材库校验。

## Aggregate Index

只对已经明确批准、且包含 `.momcozy-aggregate-scope.json` 的全库根目录执行。marker 必须精确声明 `momcozy-aggregate-scope.v1` 与 `brand_workspace=momcozy`；不要把 marker 复制到更宽的父目录：

```bash
rtk uv run --project apps/api python -m tools.momcozy_assets.aggregate_index \
  outputs/momcozy-content-assets/<approved-scoped-root>
```

命令把 JSON/Markdown 成对写入不可变的 `aggregate-index-releases/<projection_digest>/`，最后才原子切换根目录下的 `aggregate-index-current.json`。消费者必须以 current manifest 中的相对路径和 SHA-256 为准；旧的顶层 `aggregate-index.json` / `aggregate-index.md` 不是当前发布权威。`blocked`、source drift 或任一 I/O 失败都不会切换 current release；重复运行相同输入必须得到 byte-identical manifest、JSON、Markdown 与 `projection_digest`。

生成器递归发现受支持的 scoped index、ledger 与 frozen plan，拒绝未知 schema、重复/畸形记录、路径/hash/type/aspect/status 冲突、未批准或符号链接 scope 和常见私有标识。Channel、Concept Group、model、aspect、resolution 与 observed time 使用封闭词表/格式；未识别的普通值降为 unknown，疑似 URL、路径、账号或 token 则 fail closed。扫描前后对全部来源内容重新计算 digest，防止混合时点 false-green。它只输出安全的 Bundle Ref、相对路径、hash、Recipe 摘要、QA disposition、批次/渠道/Concept Group availability、coverage、findings 和 limitations；不输出 Prompt/QA 正文、Product URL、task hash、credits、媒体内容、绝对路径或凭据，也不会修改任何 Asset Bundle。

当前本地基线为 244/244 个结构有效 Bundle：235 image / `1K`、9 video / `480P`，244 个 `observed_at` 都按 timezone-aware ISO-8601 投影；QA disposition 为 36 `approved`、198 `hold`、2 `rejected`、8 `revision_needed`。Batch metadata 覆盖 235/244、Channel 12/244、Concept Group 198/244；独立 Commercial Approval 记录为 0/244。因此 Aggregate Index 状态是 `partial`，不是发布许可，也尚未接入 FactFrame runtime。

## Private Gate

真实库只在受信任的本机 checkout 中运行只读 gate：

```bash
rtk uv run --project apps/api python -m tools.momcozy_assets.private_gate \
  outputs/momcozy-content-assets/<approved-scoped-root>
```

通过条件是：两次新鲜编译一致、固定 `momcozy-m5-v1` 基线的完整 `projection_digest` 与汇总约束一致、current manifest 采用 canonical 封闭 schema、release 的内部 digest/schema/JSON/Markdown/path/hash/bytes 有效且与新鲜投影一致。Gate 从已打开的安全目录 descriptor 逐级读取并在第二次编译后复读 current release；成功只输出安全的 baseline/state/count receipt，失败只输出稳定 code，不回显路径、Bundle ID、媒体 hash 或源内容。任何失败都保持素材库和 current release 不变。

公开 CI 只运行仓库内 synthetic fixtures、Ruff 和生产模块 mypy；它不接触 ignored 私有库。公开 CI green 与本地 Gate Receipt 都不构成 Commercial Approval、发布许可、部署或生产验收。定时 automation 只负责调用同一只读 Interface，不得改变判定或执行发布/修复。
