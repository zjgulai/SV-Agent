# LeapAI Public Report Evidence

## Evidence identity

- **Source:** [LeapAI public report](https://leap-ai-delta.vercel.app/public-report/c89da8a0-681f-42ed-91b2-8a3062f19ac8)
- **Page title:** `LeapAI - AI-powered TikTok Video Analysis`
- **Report subject:** `momcozy-德国-奶瓶清洗暖奶器`
- **Displayed window:** 2026-08-21 through 2026-08-27
- **Platforms:** TikTok, Instagram and YouTube
- **Capture:** public page body and getter-only Next.js Server Action payloads inspected on 2026-08-27; no login, private data or mutation action used

This file is a bounded evidence summary, not a copy of the full webpage. Values preserve UI precision and use exact getter payload values where available; UI and payload differences remain explicit.

## Direct observations

| Observation | Observed value | Evidence note |
|---|---:|---|
| Published videos | 22 | Reconciles to 7 Instagram + 9 TikTok + 6 YouTube |
| Total views | 10,312 | UI rounds this to 10.3K |
| Total likes | 37 | Reconciles to 3 + 12 + 22 |
| Total comments | 0 | Platform rows display `-`; zero versus unavailable is unresolved |
| Total shares | 0 | No platform-level share table is visible |
| Social accounts | 20 | Reconciles to 4 + 6 + 10 |
| Total followers | 17 | TikTok returns 7 and YouTube 10; Instagram payload returns 0 while UI displays `-` |
| Average followers | 1 | Page rounds 17 / 20 despite unresolved Instagram zero-versus-unavailable semantics |

| Platform | Accounts | Followers | Videos | Views | Likes | Comments |
|---|---:|---:|---:|---:|---:|---:|
| Instagram | 4 | 0 / UI `-` | 7 | 907 | 3 | 0 / UI `-` |
| TikTok | 6 | 7 | 9 | 4,115 | 12 | 0 / UI `-` |
| YouTube | 10 | 10 | 6 | 5,290 | 22 | 0 / UI `-` |

The report also exposes cumulative daily trends with overall/platform comparison and line, area and bar views:

| Date | Cumulative views | Likes | Videos | Reported engagement rate |
|---|---:|---:|---:|---:|
| 2026-08-21 | 2,660 | 6 | 6 | 0.0023 |
| 2026-08-22 | 3,055 | 8 | 6 | 0.0026 |
| 2026-08-23 | 3,450 | 10 | 10 | 0.0029 |
| 2026-08-24 | 4,222 | 10 | 10 | 0.0024 |
| 2026-08-25 | 5,697 | 16 | 14 | 0.0028 |
| 2026-08-26 | 9,931 | 36 | 22 | 0.0036 |
| 2026-08-27 | 10,312 | 37 | 22 | 0.0036 |

The structured series covers 2026-08-21 through 2026-08-27, while accessible chart labels showed 2026-08-20 through 2026-08-26. This presentation mismatch must be resolved before reproducing the chart. Payload `newViews`, `newLikes` and `newVideos` fields are all zero, so they do not explain the cumulative calculation.

## Top 10 content directions

| Rank | Content direction | Platform | Displayed views | Displayed likes | Reusable signal |
|---:|---|---|---:|---:|---|
| 1 | 告别繁琐手洗，拥抱智能便捷 | YouTube | 1,284 | 7 | Manual-versus-automation contrast |
| 2 | 用实验验证产品效果 | YouTube | 1,096 | 5 | Physical analogy as proof device |
| 3 | 直观展示加热速度，强化产品效率 | YouTube | 1,062 | 6 | Countdown, temperature and split-screen feedback |
| 4 | 第一人称视角展示产品加热效率 | YouTube | 1,033 | 3 | POV plus unexpected heat demonstration |
| 5 | 从繁琐到便捷的对比，突出产品解放双手 | TikTok | 858 | 5 | Problem/solution transformation |
| 6 | 第一视角展示，强调便利性 | TikTok | 828 | 0 | POV, capacity and simple operation |
| 7 | 创意展示产品通用性 | TikTok | 825 | 4 | Tangible temperature feedback and alternate-use demo |
| 8 | 将繁琐的清洁过程转化为 ASMR 式舒缓体验 | YouTube | 814 | 1 | Sensory treatment of routine work |
| 9 | 用户痛点戏剧化，突出产品高效解决方案 | TikTok | 797 | 0 | Pain dramatization plus digital feedback |
| 10 | 沉浸式 ASMR 体验，打造轻松育儿日常 | TikTok | 281 | 1 | Stress-reduction framing and hands-free process |

The Top 10 total 8,878 views (86.09% of 10,312) and 32 likes (86.49% of 37). This is a concentration signal, not a causal contribution estimate. Five ranked videos are YouTube and five are TikTok; no Instagram video appears in the Top 10.

## Evidence-backed synthesis

The ten directions overlap across three testable creative dimensions:

1. **Relief transformation:** manual work versus automated, hands-free convenience.
2. **Visible proof:** countdowns, temperature displays, split screens and physical analogies make performance legible.
3. **Embodied experience:** POV and ASMR make routine childcare feel immediate and emotionally lighter.

These are Creative Signals. They do not prove that automation, proof devices or ASMR caused the observed views, because the report does not expose controls for account size, posting time, paid distribution, video length, creative quality or platform recommendation effects.

## Claim safety review

The report's generated selling-point summaries include high-temperature disinfection, killing bacteria, precise temperature control, temperature retention and alternate uses such as cooking an egg or melting butter. They remain `Reported Product Claim` values:

- an egg demonstration does not prove sterilization or bacterial kill efficacy;
- melting butter may demonstrate heat transfer but may also imply an off-label use;
- precise temperature and retention claims require source-backed specifications;
- none may enter a script unless mapped to a current confirmed/locked Product Fact.

The structured analysis also contains direct output-quality failures that justify FactFrame's typed validators:

- one `voiceOver.zh` value is German rather than Chinese;
- one Clip/CTA contains unrelated English lyric fragments;
- one ranked storyboard contains only a Hook and omits Clip/CTA structure;
- one temperature value uses `%` instead of `°C`;
- some key takeaways claim higher engagement or credibility even though comments and shares are zero and no causal comparison is supplied.

These are language, schema, unit, completeness and evidence-support findings. They remain AI-derived output defects, not Product Facts or private model reasoning.

## Capability mapping

| Leap capability | Verified page evidence | FactFrame/Momcozy mapping | Disposition |
|---|---|---|---|
| Multi-platform aggregation | KPI cards and platform table | Performance Window + Platform Breakdown | Cite with window and missing-value caveat |
| Workspace and asset slicing | Brand/product/date/platform, creator/favorite and sort controls | Bounded source and comparison contract | Reuse the filter vocabulary; define ownership and snapshot semantics separately |
| Trend visualization | Exact cumulative daily series plus chart/platform controls | Observation series candidate | Recompute before productization; resolve chart-axis and bucket semantics |
| Ranked video directions | Top 10 cards with platform, views and likes | Creative Signal backlog | Test; never install as a default pattern from rank alone |
| Selling-point extraction | Core-selling-point summaries per video | Reported Product Claim | Fact-gate or reject |
| Creative insight extraction | Key-insight summaries per video | Hypothesis input for Creative Pattern | Convert into versioned experiment dimensions |
| Storyboard decomposition | Bilingual Hook/Clip/CTA, voice-over, sentence pattern, scene, location, technique and live-action fields | Typed Script/Storyboard candidate | Recompile from confirmed facts; do not copy as trusted output |
| Script handoff | Visible `生成脚本` action | Script Generation candidate | Require selected/excluded facts and deterministic validation |
| Asset operations | Visible download/edit actions | Momcozy Asset Bundle candidate | Preserve provenance and approval boundary |
| Excel export | Visible export control | Reproducible evidence intake candidate | UI presence verified; exported bytes not tested |

The public brand selector returns eight Momcozy market/product workspaces across Germany, France, the United States and the United Kingdom. This verifies multi-market workspace organization, but only the Germany bottle-washer/warmer report above was analyzed; cross-market comparisons were not performed.

## Data transport boundary

The initial public GET returns the report shell and route metadata. Hydrated data is delivered by getter-only Next.js Server Actions for brands, aggregate brand data and analyzed Top videos. The public bundle also contains additional getters and a mutation action; this audit did not call update, edit, generation, download or export operations. The existence of an action in client code is not evidence that it works, is authorized or belongs in the integrated product scope.

## Method and scope limitations

The page does not disclose upstream collection source, deduplication rules, ranking formula, organic/paid split, account sampling rationale, data snapshot time, timezone, missing-value handling, analysis model, prompt, human review or confidence calibration. Payloads contain the requested date filter and each video's `posted_at`, but no `sampleSize`, `createdAt`, `snapshotAt` or ingestion timestamp. The repeated `中` and `1 / 1` labels are visible but undefined. Therefore:

- displayed aggregates are source observations, not independently reproduced metrics;
- Top 10 ordering is report-defined, not a universal Momcozy benchmark;
- the seven-day Germany/product slice must not be generalized to other markets, products or periods;
- comments, shares and follower averages must retain their unresolved missing-versus-zero semantics.
