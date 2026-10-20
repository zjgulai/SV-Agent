# 07 — BV-GATE-001 External rights, child-safety and connector preflight

**What to build:** 在任何原始媒体嵌入、创作者合作、音乐使用、外部数据连接或真实品牌声量实验之前，形成可审计的授权与安全 preflight。

**Blocked by:** `BV-P1-002` — Add second candidate and campaign benchmark lane

**Status:** awaiting_user_gate

- [x] 用户已明确授权执行本地 preflight；范围限定为证据合同、政策基线和脱敏记录
- [x] BV-002 / CB-001 已生成 `brand-voice-gate-preflight/v1` 脱敏记录，并按 planned use 分层
- [x] 公开政策基线已登记：Content Suite authorization、market-specific Branded Content、Commercial Content Disclosure
- [x] 当前站点仍为 metadata-only；无原始媒体、音频、评论抓取或 connector access
- [ ] 原始帖子身份、创作者/监护人许可和 source-use scope 已确认
- [ ] 音乐/声音商业使用权已确认或替换为 owned/licensed audio
- [ ] 儿童肖像、身份暴露、危险模仿和市场规则完成案例级审阅
- [ ] connector credential、scope、commercial_access 和 quota 已获明确授权
- [ ] external action、发布、投放和 Momcozy Brand Lift 设计获得单独批准

**Validation:** 本地部分接受 JSON contract、policy reference、source/unknown mapping、无媒体边界和浏览器 panel 检查；最终 gate 只接受授权文件、平台控制台证据或明确的人工审批记录。公开页面、模型判断或本地 gate receipt 不能替代。

**Local evidence:** `BV-002` 与 `CB-001` 均有可下载的脱敏 preflight record；状态分别保留 intimate-care / rights unknown 与 benchmark-only 限制。用户操作授权已记录为 `granted_to_prepare_preflight`，不升级为 third-party rights clearance。

**Next required evidence:** 原始帖子/权利主体、guardian/likeness consent、音乐/声音许可、market-specific child-safety review、connector scope/quota、发布/投放和独立 Brand Lift 批准。补齐前保持 `awaiting_user_gate`，不下载、不嵌入、不生成、不发布。

**Out of scope:** 在没有上述证据时继续下载、嵌入、生成、发布或投放。
