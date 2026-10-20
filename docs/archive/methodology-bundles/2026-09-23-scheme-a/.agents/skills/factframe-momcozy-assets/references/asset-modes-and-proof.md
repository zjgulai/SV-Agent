# Momcozy Asset 工作模式与证明边界

## 模式矩阵

| 模式 | 读/写 | 目标 | 失败后 |
| --- | --- | --- | --- |
| `synthetic-ci` | committed fixture 读 | 验证工具与公开合同 | 不触碰真实库 |
| `publish-aggregate` | 私有源读、release/current 写 | 发布 immutable Aggregate release | 保留旧 current |
| `private-gate` | 私有库只读 | 对 fixed baseline/current 做本机复验 | 返回 stable code，不修复 |

## Aggregate 发布门

1. exact approved root 与 `.momcozy-aggregate-scope.json`。
2. 无 symlink、宽父目录、未知 schema、重复 identity、路径/hash/status 冲突或敏感投影。
3. 扫描前后源状态一致，否则 `SOURCE_CHANGED`。
4. canonical JSON/Markdown 与 `projection_digest`。
5. staging write + `fsync` + atomic move 至 digest release。
6. 同 digest 既有 release 必须 byte-identical。
7. release 完成后才 atomic replace current manifest。

## Private Gate 门

1. 使用固定 tracked baseline。
2. 逐级读取 owned、非 group/world writable 的 directory descriptor。
3. leaf 是 current-owner regular file、`nlink=1`、bounded size、非 group/world writable。
4. 验证 closed manifest、path/hash、release schema、internal digest 与 Markdown rerender。
5. fresh compile 两次并要求 digest/JSON/Markdown 一致。
6. 第二次编译后重读 current，确认 root inode/device 未替换。
7. 只报告 baseline/state/count receipt 或 stable failure code。

## 不能升级的声明

- Synthetic CI != real-library acceptance。
- Bundle structural validity != QA 或 Commercial Approval。
- `partial` Aggregate Index != release permission。
- Private Gate receipt != deployment 或 production acceptance。
- asset metadata != PostgreSQL Product Fact。

真实根目录、media、manifest 内容、hash、automation ID 与 receipt detail 都保持本地，不进入 tracked docs 或普通 capability graph。
