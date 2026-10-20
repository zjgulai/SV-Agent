---
status: accepted
---

# 版本化最终能力图谱，但不版本化中间产物

提交 `.ua/knowledge-graph.json`、`fingerprints.json`、`meta.json`、`config.json` 和 `.understandignore`，使架构导航可复核并支持增量更新；`.ua/intermediate/`、`tmp/` 和 `.trash-*` 保持可再生。`fingerprints.json` 是与扫描文件集绑定的结构基线，必须先成功生成，随后才能更新 `meta.json`。图谱只索引源码、文档和证据关系，任何能力声明仍须回链到代码、PostgreSQL、migration、测试或实验台账。
