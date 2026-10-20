# 06 — BV-P1-002 Add second candidate and campaign benchmark lane

**What to build:** 增加至少一个不同于 task-compression 的 baby social candidate，并把官方 paid/UGC/Brand Lift 活动作为独立 benchmark 展示，不跨轨道排名。

**Blocked by:** `BV-P1-001` — Add Social Resonance Map artifact contract

**Status:** verified_local

`BV-P1-001` 已通过本地验证，因此本票已进入执行并完成本地收口；执行仍限于公开来源的脱敏 metadata，不自动抓取、下载或托管儿童媒体。

- [x] 第二个 candidate 有独立来源、Performance Window、主体、指标状态和 rights/child-safety 状态
- [x] 至少一个 `campaign_awareness_benchmark` 卡片明确 paid/organic mixed、活动窗口和测量方法
- [x] `counterexample_hold` 可展示权利或安全阻断，但不生成仿拍建议
- [x] Case Archive 筛选和卡片不把不同轨道合并为一个 views 排名
- [x] 没有原始儿童媒体或未授权音频进入站点包

**Validation:** 案例 schema 校验、轨道筛选浏览器检查、来源/权利/状态审阅。

**Current implementation:**

- `BV-002` 使用 ARK record/19758 的 source-limited metadata projection；主机制为 `attention-grammar` / `single_reaction_reveal`，intimate-care 场景保持 `analysis_only`、`metadata_only`、`proceed_with_limits`。
- `CB-001` 使用官方 Nestlé Generations of Love case 与 TikTok Brand Lift guidance 的 benchmark projection；保留五市场窗口、UGC/boosted 分层和 Exposed/Control 方法，不迁移 reported lift。
- 两个案例在 Case Archive 中使用独立 tab、独立下载 JSON 和独立状态；不跨轨道排序，不托管原始视频/音频/儿童媒体。
- `counterexample_hold` 的权利/安全阻断规则继续由 spec、ledger 和 `BV-GATE-001` 展示；本批不生成仿拍建议。

**Local evidence:** JSON contract assertions、inline script parse、Markdown local-link check、Case Archive desktop/mobile browser smoke、JSON HTTP 200、无 console error、无横向溢出均已通过。外部 rights/child-safety/connector gate 仍保持 `blocked`。

**Out of scope:** 自动发现、全量 TikTok 抓取、发布和广告投放。
