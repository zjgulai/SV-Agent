# P1.4.2：事实脚本工作台验收闭环

## 目标与范围

本批只补 P1 已实施合同的真实验收链路：Promotion Fact 隔离、失效关闭，以及客户端对已受理但不可解析/不可达响应的恢复。它不增加账号、租户、计费、视频渲染、发布或新的业务数据模型。

## 不变量

- Promotion Fact 绝不能出现在 `selected_fact_ids` 或 `excluded_fact_ids`；它只能作为独立的 `promotion_fact_id`，且仅 `offer_cta` 的最终 CTA 可持有服务器渲染文本。
- Web 对 confirmed/locked 但不在有效时间窗的 Promotion Fact 显示为不可选择；服务端仍以 PostgreSQL `statement_timestamp()` 为最终裁决。
- Promotion 在 Provider 调用前、版本保存前、storyboard preflight 和 approval 重新检查。失效或被否决时，Job 以 `PROMOTION_NOT_ACTIVE` 失败，不能创建版本；已有 approval 派生为 `stale`。
- 202 响应的 JSON 解析失败只可从安全 `Location` 打开既有 Job。传输失败后的恢复必须逐字重放原 body 与同一个 `Idempotency-Key`，不得创建新 Job。

## 验收方法

1. 真实 PostgreSQL API/Worker 测试覆盖 Promotion 不能进入 selected/excluded、调用 Provider 前失效、保存前 TOCTOU 失效及 storyboard approval stale。
2. Provider 单测以非空 Promotion 证明外部请求不包含 Promotion、audience 或 server-owned contract。
3. Compose + Playwright 覆盖有效 Promotion 只在最终 CTA，否决后 preflight blocked/approval stale；另覆盖真实后端先受理、浏览器端伪造 HTML 202 与 transport failure 后的同键恢复。
4. 保留 P0 成功/校验失败 E2E，且所有 Web、后端、lint/typecheck/build 通过后才记录本地验收。

## 失败边界

浏览器路由注入只用于制造代理 HTML/网络断开等客户端边界；Job 创建、幂等收束和状态读取都走真实 Compose API/PostgreSQL。该验收不声称验证生产代理、真实外部 Provider 或部署环境。
