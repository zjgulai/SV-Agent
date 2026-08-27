# Momcozy Local Asset Archive

这个目录只包含可提交的归档工具和测试，不包含任何商业媒体、平台任务标识、浏览器状态或账号数据。

## 目录职责

- `contracts.py`：定义每个本地商业素材包必须具备的文件、哈希和隐私边界。
- `validate.py`：验证单个素材包或整个素材库的结构与敏感字段约束。
- `archive_batch.py`：将已经通过正常项目页下载的图片或 ZIP 导出包拆分成“一图一文件夹”的可追溯素材包。
- `tests/`：覆盖完整素材包、敏感标识拒绝、单组归档和 ZIP 安全解包。

真实输出必须保存在被 Git 忽略的 `outputs/momcozy-content-assets/`。每个素材目录只保存 `asset.*`、`prompt.md`、`recipe.json`、`provenance.json`、`qa.md` 与 `hashes.sha256`；不得写入原始平台任务 ID、签名 URL、Cookie、授权头或账号信息。

## 验证

```bash
rtk uv run --project apps/api python -m unittest discover -s tools/momcozy_assets/tests -v
rtk uv run --project apps/api ruff check tools/momcozy_assets
rtk uv run --project apps/api python -m tools.momcozy_assets.validate outputs/momcozy-content-assets/<batch-root>
```

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
