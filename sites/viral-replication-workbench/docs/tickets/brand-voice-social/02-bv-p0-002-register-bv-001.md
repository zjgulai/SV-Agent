# 02 — BV-P0-002 Register BV-001 source-limited case

**What to build:** 将已有 maternal TikTok Insight Brief 投影为第一个 `brand_voice_social` 案例记录，保留其来源限制、unknown、媒体门和下一步 action，不创建新的事实或媒体。

**Blocked by:** `BV-P0-001` — Freeze brand-voice social case contract

**Status:** verified_local

- [x] BV-001 使用稳定 case id、brand-awareness 目标和单一 primary mechanism
- [x] 第三方来源、Performance Window、reported metric 和 capture limitation 有 source register
- [x] likes/comments/shares/completion、paid/organic、原始帖子和权利保持 unknown/not_reported
- [x] `media_state` 为 metadata-only 或 external-link，不新增原始儿童视频、音频或图片
- [x] `next_action=collect_evidence`，不能写成 winner、causal 或 Brand Lift
- [x] 既有 Insight Brief JSON 未被覆盖或补写

**Validation:** 运行既有 Insight Brief validator，并检查投影字段与原 brief 的 status/action/primary mechanism 一致。

**Out of scope:** 新的 TikTok 抓取、原始帖子恢复、授权媒体和 Momcozy 目标片。
