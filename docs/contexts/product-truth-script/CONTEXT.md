# Product Truth & Script

定义从商品来源观察到可审计脚本与 Storyboard 的业务语言。这个上下文只接受可追溯事实，不把模型输出或素材画面当作商品真相。

## Language

**Product Source**:
商品信息的有界来源身份，可被再次观察并产生新的 Product Snapshot。
_Avoid_: Page, raw website, product record

**Product Snapshot**:
某一时点对 Product Source 的不可变观察，后续观察必须形成新版本。
_Avoid_: Current product, mutable product data

**Product Fact**:
绑定 Product Snapshot、证据和状态的商品声明或结构化值。
_Avoid_: Claim copy, model fact, marketing fact

**Confirmed Fact**:
已经过人工确认、可以进入候选声明集合的 Product Fact。
_Avoid_: Approved claim

**Locked Fact**:
已冻结、不能原地改变且可以支持最终声明的 Product Fact。
_Avoid_: Final copy

**Selected Fact**:
按明确优先级进入一次 Script Generation 的 Confirmed Fact 或 Locked Fact。
_Avoid_: Prompt context

**Excluded Fact**:
被明确禁止出现在一次 Script Generation 可见内容中的 Product Fact。
_Avoid_: Negative prompt

**Creative Pattern**:
版本化的脚本阶段、镜头角色、时间预算和 server-owned creative copy 合同。
_Avoid_: Template, style prompt

**Script Generation**:
冻结 Product Snapshot、Selected Fact、Excluded Fact 和 Creative Pattern 的一次生成意图。
_Avoid_: Job, prompt run

**Script Version**:
一次 Script Generation 下不可变、带完整 Validation Report 的脚本结果。
_Avoid_: Editable script, draft overwrite

**Storyboard**:
由可接受 Script Version 投影出的不可变审核对象，不代表 RenderJob 或媒体成品。
_Avoid_: Render, video, animatic job

**Storyboard Approval**:
对特定 Storyboard 内容与实时事实状态的本地审核事件；事实变化后可以失效。
_Avoid_: Publish approval, legal approval

**Promotion Fact**:
独立于商品声明、带有效期且只允许出现在指定 CTA 位置的促销合同。
_Avoid_: Product Fact, generic discount copy
