# 安全 URL 导入：网络与持久化门

## 请求链

```text
API validation
  -> queued Job + Outbox intent
  -> Worker revalidation
  -> bounded DNS resolution
  -> validated-IP connection with original Host/SNI
  -> exact MIME and bounded body
  -> JSON / JSON-LD Product parser
  -> bounded ingress DTO and image filtering
  -> Product Source reuse + new Snapshot + proposed facts
```

## 必须保留的拒绝面

- unsupported scheme 或非标准端口
- username/password、query、fragment
- loopback、private、link-local、multicast、reserved 或 mixed public/private DNS
- redirect、environment proxy、DNS rebinding 风险
- DNS/connect/read/total timeout 或 body 超限
- MIME prefix collision，例如把 `application/jsonp` 当 JSON
- JavaScript-only、登录态或 arbitrary crawl
- 图片 URL 未独立重验

## 持久化边界

允许保存：normalized source identity、投影字段、canonical digest、阶段、稳定错误码、可选 Snapshot ID。

禁止保存：完整网页、response headers、Cookie、DNS/IP 细节、signed/token URL、connector exception 原文、private network identity。

## 失败映射

外部异常应映射为稳定、无 URL 的业务错误。不要把连接失败包装成空商品，也不要因 parser 部分成功而确认 Product Fact。

## 验证焦点

- `apps/api/tests/unit/connectors/test_ssrf.py`
- `apps/api/tests/unit/connectors/test_schema_org.py`
- `apps/api/tests/integration/api/test_product_imports.py`
- `apps/api/tests/integration/api/test_execution_timeline.py`

用 `$factframe-reliable-execution` 验证 Job/Outbox/Celery 行为；用 `$factframe-product-truth` 验证 Snapshot/Fact 状态。
