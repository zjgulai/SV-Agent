# 05 — BV-P1-001 Add Social Resonance Map artifact contract

**What to build:** 在不依赖销售指标的情况下，让品牌声量案例能够表达父母张力、识别感、情绪回报、参与提示和评论/分享证据的来源与缺失状态。

**Blocked by:** `BV-P0-004` — Validate P0 evidence and media boundary

**Status:** verified_local

- [x] `SocialResonanceMap` 字段与 `BrandAwarenessBrief` 对齐
- [x] 评论主题、分享/保存、UGC 和 profile action 都带状态、分母和采集窗口
- [x] 观察、有限推断、替代解释和未知分开显示
- [x] 不把情绪词频、点赞率或 views 升级为 Brand Lift
- [x] 产物为脱敏 JSON，可被案例详情下载或查看

**Validation:** fixture 校验、缺失值语义测试、第二审阅者可重建测试。

**Local evidence:** `social-resonance-map.json` contract check、Insight Brief validator、inline script parse、desktop/mobile browser smoke、JSON/report HTTP 200、no console error。

**Out of scope:** 自动评论抓取、情感因果模型、平台 connector 和投放。
