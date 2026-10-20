# 03 — BV-P0-003 Deliver BV-001 Case Archive vertical slice

**What to build:** 用户可以从 Case Archive 进入 BV-001，看到“品牌声量 / 非卖货 / 来源受限 / 仅分析”状态，阅读核心观察和限制，并跳转既有深度洞察报告及脱敏 JSON。

**Blocked by:** `BV-P0-001`, `BV-P0-002`

**Status:** verified_local

- [x] Case Archive 有第三个 maternal TikTok / brand voice 入口
- [x] 案例卡和概要显示 track、intent、proof level、rights scope、child-safety、media state 和 next action
- [x] 详情页说明“观察 → 机制假设 → 替代解释 → 下一道门”
- [x] 空媒体状态明确写出“无授权原片，仅展示 metadata/report”
- [x] 深度洞察报告和 JSON 下载链接可用
- [x] 非 KleanPal 案例不会继承 Oumomo 的媒体/文案说明

**Validation:** 本地静态服务器下直接打开案例深链接，检查 tab 切换、报告链接、JSON 链接和空媒体 UI。

**Out of scope:** 轨道全量筛选、第二批案例、评论主题图、外部发布和 Sites 部署。
