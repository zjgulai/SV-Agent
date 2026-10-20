# 04 — BV-P0-004 Validate P0 evidence and media boundary

**What to build:** 证明 P0 的用户路径和证据边界可被重新验证，并确认网站不会把 BV-001 误呈现为卖货视频、已证实爆款或获授权原片。

**Blocked by:** `BV-P0-003` — Deliver BV-001 Case Archive vertical slice

**Status:** verified_local

- [x] inline JavaScript 语法检查通过
- [x] Insight Brief validator 通过
- [x] `?view=cases&case=maternal-tiktok` 可定位到 BV-001
- [x] 第三个 tab、报告链接和 JSON 链接在静态服务器下可访问
- [x] 不存在原始 TikTok 视频、音频、儿童媒体、凭据、私有 ID 或 hash
- [x] 桌面/移动视口无横向溢出且无 `pageerror`
- [x] 测试记录区分 local、deployment、live、production proof level

**Validation:** buildless Site 独立静态服务器 + owner 浏览器/临时 Playwright harness；不要使用只覆盖 React app 的 e2e 配置替代。

**Out of scope:** 公开部署、匿名访问、商业批准、平台发布和真实 Brand Lift。
