# Oumomo 清洁室逆向知识库

本文件是长期索引，不替代原始证据。所有结论必须回链到以下分层资料；没有证据的内容维持未知，不升级为产品事实。

## 资料分层与维护规则

| 层 | 路径 | 记录内容 | 写入规则 |
|---|---|---|---|
| 不可变事实时间线 | `evidence/session-log.md` | 每一步可观察状态、余额、停止条件 | 只追加；后续观察以新行修正终态，不改写历史中间态 |
| 机器校验台账 | `experiments/experiment-manifest.jsonl`、`job-state-events.jsonl`、`credit-ledger.csv` | 配置摘要、任务 hash、状态序列、预算与终态 | 每个收费任务都必须三处对账；只保存 hash，不保存任务原值 |
| 可复核产物 | `artifacts/`、`artifacts/hashes.csv`、`artifacts/scorecards.csv` | 本地媒体、输入、抽帧、ASR 与独立评分 | 先 hash 再分析；质量维度分开评分，空白代表未测 |
| 结论与边界 | `reports/` | 能力地图、实验结论、项目节点差距 | 明确 F/I/U 证据等级，不把技术完成等同商业可用 |
| 可执行过程 | `sops/`、`skills/` | 提交门禁、媒体质检、账务复核、证据校验 | 每次流程变更同步 SOP；校验器通过才可报告闭环 |

## 当前状态索引

| 编号 | 当前结论 | 可复用知识 | 不可外推的范围 |
|---|---|---|---|
| 商品事实 + 爆款脚本 | 本地 P1 已实现事实选择、排序、排除、可视字段校验；P2.0 已追加冻结 storyboard、零成本预览和本地审批事件 | 事实 allow-list、版本/导出、异步恢复、append-only 审批和渲染前重检是优先工程资产 | preview 不生成媒体；本地批准不代表多方、品牌或法律批准；需真实商品快照验证 |
| 爆款脚本站内实验 | 12+3 次均显示模型会扩写无依据功效、包装与比较 | 删除/排序 UI 不是强约束；事实门必须在服务端 | 样本是受控测试品，不代表所有商品类别 |
| 链接生视频 | 后端任务可在前端 JSON 解析错误后完成；成片存在包装/功效幻觉 | 前端应进入 unknown/recovering，不能自动重试；媒体与事实门分离 | 不代表链接解析或模型服务已可靠 |
| 图片模型 | GPT Image 2 在 2×2 的严格包装保真中优于 Nano Banana 2 | 字节格式校验与语义身份检查不可被 SSIM 代替 | n=2/模型，不能推断普遍模型优劣 |
| 爆款复刻 R-B01 / R3-P01 | R-B01 技术链路闭环但内容事实失败；R3-P01 重现最低价配置与报价，却被参考播放可观察性阻断 | 95% 非终态；用项目页恢复；页面资产导出可恢复下载缺陷；跨域 iframe 不是可播放证据 | n=1，参考跨会话稳定性、随机性与结构复现均未证明 |

## R-B01 的标准状态机

```text
配置冻结 → 单次提交 → 队列 10/30/45/60/80/95
→ 余额结算 → 项目持久 completed → 本地资产导出
→ ffprobe/抽帧/ASR → 技术门 + 事实门分别判定
```

`95%`、弹窗关闭、扣分、可播放都不是完成证明；只有持久终态与本地 artifact/hash 才能关闭任务。技术成功也不能覆盖事实失败。

## 后续执行顺序

1. 先用 P1 事实合同把“输入图不存在的性能主张”阻断在 storyboard/脚本阶段。
2. 对通过的脚本先创建 P2.0 审核版分镜；只有实时事实重检仍为 ready 且本地审批未 stale，才可以设计 P2.1 报价/RenderJob。
3. 复刻再实验前进行零积分预检：必须能读取或直接观察到同参考的播放状态，再验证刷新可重开、配置与报价不变、输入 hash 冻结；跨域 iframe 容器不构成播放证明。
4. 预检通过才做两次同配置重复；记录精确阶段时间、任务 hash、账务、媒体 hash 和独立质检。
5. 只有技术、事实、身份、文字、授权都通过的产物，才可进入发布或商业评估。

## 常用验证命令

```bash
rtk uv run --project apps/api python -m unittest discover -s tools/oumomo_experiments/tests -v
rtk uv run --project apps/api ruff check tools
rtk uv run --project apps/api mypy --explicit-package-bases tools/oumomo_experiments
rtk uv run --project apps/api python outputs/oumomo-reverse-engineering/skills/oumomo-clean-room-experiment-runner/scripts/validate_evidence.py outputs/oumomo-reverse-engineering --max-spend 980
```

校验器只验证证据结构、预算和敏感字段边界；它不替代真实站点可用性、模型质量或发布验收。
