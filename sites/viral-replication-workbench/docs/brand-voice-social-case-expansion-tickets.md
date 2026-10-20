---
status: active-bv-gate-001-awaiting-user-gate
scope: site-only
tracker: local-markdown-no-external-tracker-configured
goal: 01a04462-055e-7571-89ab-f8172a90be1f
last_updated: 2026-10-11
---

# Brand Voice Social Case Expansion — Ticket Ledger

这是站点内的可追踪 ticket ledger，不是假装已经发布到 GitHub、Linear 或其他外部 tracker 的 issue 列表。当前项目没有配置外部 tracker，因此每个 ticket 同时保存在 `docs/tickets/brand-voice-social/` 的单票文件中；本文件负责依赖、frontier 和验证收口。

## Execution State

- Goal：`01a04462-055e-7571-89ab-f8172a90be1f`
- Goal status：`complete`（local preflight complete；外部 gate awaiting user evidence）
- Current frontier：`BV-GATE-001`（`awaiting_user_gate`；本地 preflight 已完成，外部证据仍缺失）
- Scope：站点案例档案、脱敏数据投影、静态/浏览器验证
- Branch：`main`
- Root worktree：已有与本任务无关的 dirty changes，保持不动
- Site worktree：nested `sites/viral-replication-workbench`，开始执行前为 clean `main`
- Deployment：`not_requested`
- Commit：`not_requested`
- Private assets：`not_accessed`
- External connectors：`not_accessed`

## State vocabulary

```text
proposed -> ready -> in_progress -> verified_local -> awaiting_user_gate -> done

proposed -> blocked | hold
```

`done` 只代表当前 ticket 的行为、验证和证据边界都完成；不代表部署、发布、商业批准、生产验收或真实社媒效果。

## Dependency Map

```text
BV-P0-001  Freeze case taxonomy and BrandAwarenessBrief contract
    ├──> BV-P0-002  Register BV-001 source-limited case projection
    │        └──> BV-P0-003  Deliver Case Archive vertical slice
    │                 └──> BV-P0-004  Validate P0 static/browser boundary
    └──> BV-P1-001  Add social-resonance artifact contract
             └──> BV-P1-002  Add second candidate and benchmark lane

BV-P1-002 ──> BV-GATE-001  External rights / child-safety / connector preflight
```

只有所有 `Blocked by` 已通过且没有未决 hard gate 的 ticket 才能进入 `in_progress`。本批只推进站点内的脱敏案例投影；外部权利、儿童安全和连接器 gate 不因本地验证而自动开放。

## Frontier policy

每一轮 loop 只处理当前唯一 frontier：

1. 读取 Goal、spec 和本 ledger；
2. 选择一个状态为 `ready` 且所有 blocker 已验证的 ticket；
3. 冻结该 ticket 的输入、输出和 stop conditions；
4. 只实施一个可演示的 vertical slice；
5. 运行 ticket 的静态/浏览器/文档验证；
6. 只有真实验证通过才更新为 `verified_local` 或 `done`；
7. 若遇到外部来源、权利、儿童安全、连接器或发布门，更新为 `awaiting_user_gate`/`blocked`，停止推进。

## Ticket Index

| ID | Title | Status | Blocked by | Evidence |
| --- | --- | --- | --- | --- |
| `BV-P0-001` | Freeze brand-voice social case contract | `verified_local` | None | 本 spec、单票文件、diff/validator |
| `BV-P0-002` | Register BV-001 source-limited case | `verified_local` | `BV-P0-001` | case-record + Insight Brief validator |
| `BV-P0-003` | Deliver BV-001 Case Archive vertical slice | `verified_local` | `BV-P0-001`, `BV-P0-002` | Site static UI + deep link |
| `BV-P0-004` | Validate P0 evidence and media boundary | `verified_local` | `BV-P0-003` | Static + desktop/mobile browser checks |
| `BV-P1-001` | Add Social Resonance Map artifact contract | `verified_local` | `BV-P0-004` | 脱敏 JSON + UI + browser smoke |
| `BV-P1-002` | Add second candidate and campaign benchmark lane | `verified_local` | `BV-P1-001` | BV-002 + CB-001 metadata、benchmark panel、source-limited JSON |
| `BV-GATE-001` | External rights, child-safety and connector preflight | `awaiting_user_gate` | `BV-P1-002` | 本地 preflight record；仍需外部授权/连接器输入 |

## Ticket status notes

### BV-P0-001

规格已写入并通过文档结构、术语交叉、Insight Brief validator 和 nested Site `git diff --check`。完成后不允许新增第七种 primary mechanism。

### BV-P0-002

只引用现有 `maternal-tiktok/data/insight-brief.json`；不得覆盖、补写或提升其中的 unknown。已增加脱敏 `case-record.json` 作为站点投影，不是新的原始媒体包。

### BV-P0-003

这是 P0 的第一个可演示 vertical slice：用户从 Case Archive 进入 BV-001，看到品牌声量状态、来源边界、非卖货目标、报告链接和脱敏 JSON；空媒体区明确显示“无授权原片”。已在本地静态服务器和 owner 浏览器路径验证。

### BV-P0-004

已验证 `?view=cases&case=maternal-tiktok`、第三个 tab、报告链接、两个 JSON HTTP 200、无原片托管、390px 移动视口无横向溢出和无 console error。不能用 React app 的 e2e 配置代替 buildless Site 验收。

### BV-P1-001

`SocialResonanceMap` 已写入脱敏 JSON 并接入 BV-001 详情页；评论/分享语义保留 `not_reported` / `not_collected`。已通过 contract、缺失值语义、desktop/mobile UI、HTTP 200 和 console smoke，状态为 `verified_local`。不新增 primary mechanism，不把评论情绪升级为因果或 Brand Lift。

### BV-P1-002

本批锁定两个 source-limited 投影：`bv-002-baby-reaction-diaper-change`（ARK record/19758，`attention-grammar` / `single_reaction_reveal`，intimate-care 风险）与 `bv-benchmark-nestle-generations-of-love-2024`（五市场活动、UGC + Brand Lift benchmark）。两者必须按 `brand_voice_social` 与 `campaign_awareness_benchmark` 分轨，不得按 views、lift 或 engagement 跨轨道排名；benchmark 只提供设计字段，不提供 Momcozy 结果。

P1-002 还保留 `counterexample_hold` 的阻断展示规则：来源/权利/儿童安全未闭合时只展示 metadata、未知项和停止条件；本批不新增独立仿拍 card。

### BV-GATE-001

用户已授权执行本地 preflight，因此已登记 `brand-voice-gate-preflight/v1`、公开政策基线和 planned-use 矩阵。当前仍需要来源主体、原始帖子、音乐、儿童肖像、创作者授权、商业披露和 connector 访问范围等外部输入；授权用户准备 preflight 不等于第三方权利闭合。未获得这些证据前保持 `awaiting_user_gate`，不下载、不嵌入、不生成、不发布。

## Loop closeout rule

本轮只在以下条件成立时结束：

- `BV-P0-001` 已完成本地验证；
- 当前 frontier 已移动到下一个未阻塞 ticket，或已明确记录阻断原因；
- 本 ledger、spec 和站点 PLAN 的状态一致；
- 没有将本地验证误报为部署、发布或生产验收。

P1-002 的本地闭环已完成。BV-GATE-001 的本地 preflight 也已完成：两个 preflight JSON 可解析；案例页显示 gate 状态、已证明项和缺失项；政策引用与来源边界已登记；新案例目录无原始媒体；桌面/移动端无横向溢出、无 console error。最终 gate 仍需外部权利、儿童安全、连接器和发布/实验批准，不能由本地循环自动推进。
