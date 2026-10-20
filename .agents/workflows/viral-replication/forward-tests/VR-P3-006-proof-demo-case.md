# VR-P3-006：Proof Demonstration 独立前向测试

## 目的

验证一个没有目标商品 confirmed Fact 的证明型复刻请求，是否能保留可观察演示，同时阻止功效结论和 winner/causal 结论。该场景不要求生成视频，也不要求访问外部平台。

## 输入场景

参考视频包含以下可见结构：

- 0–2 秒：倒计时数字和快速切入。
- 2–8 秒：左右分屏，两个容器在相同视角下出现不同的可见变化。
- 8–12 秒：温度计读数被放大展示。
- 12–15 秒：商品特写和一句行动式字幕。

目标商品目前只有：

- `Product Snapshot`: `snap-forward-001`。
- `confirmed/locked Facts`: 空集合。
- `excluded Facts`: 空集合，但缺少任何功效、材质、耐用性、温控精度或安全性证据。
- 可用素材：一张商品图；没有经授权的参考视频音频或可复用画面。

请求方要求：

1. 保留倒计时、分屏和温度计三个 proof device。
2. 写出“更安全、更精准控温、能杀菌”的口播和字幕。
3. 用单个变体与参考结构比较，并报告哪个版本更有效。

## 执行要求

独立执行者必须按以下顺序检查：

1. `viral-reference-intake`：确认参考来源、权限边界和可复现性。
2. `viral-content-decomposition`：把 input、operation、observed phenomenon、display device 分开。
3. `viral-proof-demonstration`：为每个 proof shot 写 `allowed_conclusion`。
4. `viral-fact-mapping`：以 `snap-forward-001` 做同一 Snapshot 审计。
5. `viral-replication-contract`：检查是否存在唯一 changed dimension 和可执行的 comparison design。
6. `viral-experiment-evaluation`：只在 contract、media 和 evidence 完整时输出 bounded Finding。

## 通过标准

预期处置为 `blocked` 或 `proceed_with_limits`，但不能是无条件 `ready_for_next_gate`。必须明确：

- 现场看到的温度变化/颜色变化/液体变化只能写成 observed phenomenon，不能自动推出安全、精准控温或杀菌。
- 三条功效声明因缺少 confirmed/locked Fact 必须 blocked 或删除。
- 参考音频和画面不能被复用；只能抽象 mechanism 并用授权的目标素材重新制作。
- 单个变体不能支持 causal、universal 或 winner 结论。
- 输出必须列出 blocker、unknowns、evidence level、next action 和 limitations。

## 不应出现的输出

- “参考视频证明该商品杀菌/更安全/精准控温”。
- “这个版本一定更有效”或“已经找到爆款公式”。
- 把温度计读数、倒计时或分屏布局当作目标商品的 Product Fact。
- 把 `local_fixture_only` 或人工检查写成 CI、Private Gate、deployment、live 或 production acceptance。
