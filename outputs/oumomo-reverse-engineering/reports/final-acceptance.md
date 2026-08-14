# Oumomo 逆向蒸馏最终验收

验收时间：2026-08-11，持续复验至 2026-08-14。分支：`main`。本报告只证明本地工程、Compose 部署和本轮黑盒证据，不证明远端生产、真实 Provider、TikTok 发布或生产接受。

## Outcome

核心交付已形成：网站能力图谱、13 个零积分探针、现有媒体取证、12 个脚本单变量/重复实验、1 个 URL-to-video 付费恢复实验、4 个图片模型重复实验、5 个条件门、受控降质语料、发布 dry-run、逐节点工程复盘、P1/P1.5/P2 路线、9 份 SOP、1 个前向验证 Skill，以及已实现的 P1 事实选择合同和 P2.0 分镜审核预览。

## Credit acceptance

- 初始余额：980。
- 脚本：12 × 10 = 120。
- U-B01：1 × 50 = 50。
- 图片模型：GPT Image 2（2 × 2）+ Nano Banana 2（2 × 3）= 10。
- 其他门禁/dry-run：0。
- 累计净扣：180。
- 初始验收关账余额：800；后续 AV-B01、S2-* 与 R-B01 的单次受控实验后，当前页面余额为 670，完整时间线见 `evidence/session-log.md`。
- Evidence validator：pass；ledger continuity：pass；重复扣费：0。

## Experiment acceptance

| Group | Result |
|---|---|
| Z00–Z12 | 13 个免费探针完整；明确 pass/fail/blocked/inconclusive |
| M-EX01 | 既有复刻媒体技术/帧/ASR/OCR/镜头取证；事实判 fail |
| S-B01…S-F01 | 12 个任务均 succeeded；12 个 feature verdict 均因事实/控制缺陷 fail |
| U-B01 | Job succeeded、扣分正确、Artifact 完整；frontend boundary、包装与事实 fail |
| T-GATE | 历史价格门通过；当时上传权限阻断；模板仍无有效 A/B |
| I-GPT-01/I-GPT-02 | 两次 succeeded；严格包装身份均 pass；实际 PNG 1254×1254 |
| I-NANO-01/I-NANO-02 | 两次 succeeded；严格包装身份均 fail；实际 JPEG 1024×1024，和 `.png`/页面媒体类型声明冲突 |
| AV-GATE | 75 > 30 cap；blocked |
| VM-GATE | 具体 8 模型可见；参考图上传阻断；blocked |
| Q-GATE/D-GATE | 项目选择跨路由错误；blocked、零扣分 |
| P-DRY | 字段合同 pass；停止于 OAuth/发布前 |

## Deliverables

- `reports/project-node-review.md`：API、导入、事实、生成、Provider、校验、Job、DB、安全、Web、版本与测试 12 节点。
- `reports/p1-p2-roadmap.md`：P1 脚本工作台、P1.5 可靠/SaaS、P2 preview-first 视频。
- `sops/`：9 份 Purpose/Inputs/Preconditions/Steps/Evidence/Stop Conditions/Acceptance/Recovery SOP。
- `skills/oumomo-clean-room-experiment-runner/`：SKILL、2 个 references、validator、OpenAI metadata。
- `fixtures/scoring-degradations/`：D-00…D-05 与 manifest。
- `artifacts/`：脚本、媒体、4 张图片模型原始产物、2×2 对比网格、hash 与 scorecard。

## Verification

- Tool unit tests: 14 passed.
- 2026-08-12 复验：工具测试 18/18、证据校验器通过、敏感信息扫描通过、`git diff --check` 通过、`apps/api/tests` 全量 81/81、前端 lint/typecheck/3 个测试文件 11 项、Web build、E2E 2/2、docker full-stack up/down 验证链路完整。
- Ruff: `apps/api migrations tools` passed.
- mypy: API 53 source files passed; experiment tools 9 source files passed.
- Web lint/typecheck: passed.
- Web unit: 3 files / 11 tests passed.
- Web production build: passed.
- Skill Creator quick validation: passed.
- Evidence validator: passed.
- SOP structure: passed.
- Spend validator: 180.
- Backend integration: with PostgreSQL/Redis started and TEST_DATABASE_URL set, `apps/api/tests` 全量通过（81 个用例）。
- Full-stack E2E: 触发通过（2/2）；仍未触发 OAuth 与发布链路脚本。

## 2026-08-14 工程续验

- P1 已把 selected/excluded Fact 的顺序、互斥、状态、摘要和导出接入生成与派生版本；不再允许“自动选全部”的隐式合同。
- P2.0 已实现追加式 `StoryboardVersion`、确定性 HTML animatic、追加式 approval event 和事实降级后的 `stale` 派生状态；没有 RenderJob、Provider、媒体、积分或发布副作用。
- `0005_storyboard_approval_preview` 已在项目库升级；一次性数据库验证了 `0002 → 0005 → base → 0005` 回滚链路并删除测试库。
- 当前验证：后端 97/97、前端 lint/typecheck、Vitest 14/14、production build、Playwright 2/2；Compose 中 PostgreSQL、Redis、API、Worker 与 Web 均为健康状态。

## Remaining blockers

1. Template A/B remains blocked until same-product stable templates and pre-submit quotes are available.
2. Browser local-file access is now enabled, but the same-reference video-model matrix was not executed in this stage; its input and quote must be revalidated before spending.
3. Quality-score calibration and dedup before/after cannot run through existing-project selection until the cross-route defect is fixed; the local-upload route still needs a fresh zero-credit revalidation.
4. Avatar matrix remains intentionally blocked by the approved price cap；浏览器控件级取证已恢复，但 R-* 与部分 U-* 条件实验续费前仍需要新一轮可控播放/上传复验。
5. No OAuth, TikTok account binding, real scheduling or publishing was authorized.

## Recommended build decision

Proceed with P1.5 “transactional outbox + ImportAttempt/JobEvent + tenant boundary” only after a dedicated design approval. Do not start with model aggregation, Avatar or opaque dedup/weight claims. The current project already owns facts, immutable versions, validation, fenced jobs, fact selection/order/exclusion and P2.0 review; the next paid-video capability still requires P1.5 reliability plus a separately approved P2.1 media/quote/billing design.
