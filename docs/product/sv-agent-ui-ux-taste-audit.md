# SV-Agent UI/UX Taste Audit

> 审计日期：2026-10-21  
> 范围：Task Inbox、New Task、Mission Control、Evidence & Artifacts，以及它们共享的 Web Shell  
> 方法：`design-taste-frontend` v2 的 App Screen 规则、源码 lint、1440 / 768 / 390 三档真实浏览器截图、源码与现有测试交叉核对  
> 本文是优化方案，不代表已经完成 UI 改造或发布。

## 结论先行

当前 UI 的最大问题不是“缺少装饰”，而是使用了错误的产品语法：它把一个高频操作、证据密集的 Agent 工作台，做成了带超大标题、eyebrow、渐变和悬浮按钮的营销页。

推荐把 UI 收敛到 **Framed Sheet**：SV-Agent 成为明确的产品主体；低彩度框架承载导航，白色工作面承载任务、决定和证据；颜色只花在当前数据、阻塞和一个主操作上。先修 Shell、信息层级和状态系统，再修每个页面的局部视觉。

三个最高杠杆改动：

1. 把营销页式 Shell 改成工作台式 Shell：22px 页面标题、固定产品与 Task 上下文、可折叠导航、无渐变和静态阴影。
2. 让每页最大的内容直接回答一个问题：Inbox 先显示“哪里需要我决定”，Mission Control 先显示“下一步安全动作”，Evidence 先显示“结论是否有足够证据”。
3. 建立统一状态系统：block-level loading / empty / error / stale；错误保留页面框架和上次有效数据；手机端始终有导航与 44px 操作目标。

## 审计边界与证据

审计运行的是当前 `main` 工作区中的真实前端代码。Web 在本地正常启动；API 进程可启动，但开发数据库返回 `DATABASE_UNAVAILABLE`。因此：

- New Task 的完整表单状态已由真实浏览器验证。
- Task Inbox、Mission Control、Evidence 的错误状态已由真实浏览器验证。
- 三个页面的已填充状态依据当前 React/CSS 源码和已有测试结构审计，未声称已经做过 populated-state 的视觉验收。

这一区分很重要：错误态截图是真实运行证据，但不能替代完整业务数据下的视觉验收。

### 可复现命令

```bash
rtk node "${CODEX_HOME:-$HOME/.codex}/skills/design-taste-frontend/scripts/lint.mjs" --app apps/web/src
rtk node "${CODEX_HOME:-$HOME/.codex}/skills/design-taste-frontend/scripts/inspect.mjs" --app http://127.0.0.1:4186/sv-agent/tasks/new --out /tmp/sv-agent-taste-audit/new-task
rtk node "${CODEX_HOME:-$HOME/.codex}/skills/design-taste-frontend/scripts/inspect.mjs" --app http://127.0.0.1:4186/sv-agent/tasks --out /tmp/sv-agent-taste-audit/task-inbox
rtk node "${CODEX_HOME:-$HOME/.codex}/skills/design-taste-frontend/scripts/inspect.mjs" --app http://127.0.0.1:4186/sv-agent/tasks/audit-task --out /tmp/sv-agent-taste-audit/mission-control
rtk node "${CODEX_HOME:-$HOME/.codex}/skills/design-taste-frontend/scripts/inspect.mjs" --app http://127.0.0.1:4186/sv-agent/tasks/audit-task/evidence --out /tmp/sv-agent-taste-audit/evidence
```

### 自动测量基线

| 范围 | 实际状态 | Taste 结果 | 主要问题 |
| --- | --- | --- | --- |
| 全部 Web 源码 | 静态扫描 | 9 FAIL / 65 WARN | 2 个渐变、1 个 UI emoji、6 个 placeholder 命中、52 个 eyebrow、6 个 shadow、1 个 glass |
| New Task | 完整表单 | 1 FAIL / 5 WARN | 按钮阴影、78px app title、cream palette、177px ragged row、首屏只出现 2/5 个业务块 |
| Task Inbox | 数据库失败态 | 1 FAIL / 3 WARN | 按钮阴影、78px app title、cream palette、micro-label |
| Mission Control | 数据库失败态 | 1 FAIL / 3 WARN | 手机标题三行、78px error title、首屏 33% 空洞 |
| Evidence | 数据库失败态 | 0 FAIL / 3 WARN | 78px error title、首屏 47% 空洞、cream palette |

### 工具可运行性与截图索引

`lint.mjs` 与 `inspect.mjs` 都在本次 checkout 上真实运行，不是根据历史报告推断：

- `lint.mjs` 正常完成扫描并因真实规则命中以非零状态退出，结果为 `9 FAIL / 65 WARN`；这不是脚本启动失败。
- 四次 `inspect.mjs` 都启动了真实浏览器，并分别生成 1440、768、390 三档 fold 截图和 `report.json`。
- New Task 成功进入完整表单。其余三页成功进入真实错误态；它们无法进入 populated state 的稳定原因是 API 返回 `DATABASE_UNAVAILABLE`，即本地 PostgreSQL 权威 Task store 不可用，而不是 inspector、路由或截图工具失败。

截图位于临时审计目录 `/tmp/sv-agent-taste-audit/`，不会提交到仓库；下面的相对路径均以该目录为根：

| 页面 | 1440 桌面证据 | 768 平板证据 | 390 手机证据 | 本次真实验证状态 |
| --- | --- | --- | --- | --- |
| New Task | `new-task/desktop-fold.jpg` | `new-task/tablet-fold.jpg` | `new-task/mobile-fold.jpg` | 完整表单 |
| Task Inbox | `task-inbox/desktop-fold.jpg` | `task-inbox/tablet-fold.jpg` | `task-inbox/mobile-fold.jpg` | `DATABASE_UNAVAILABLE` 错误态 |
| Mission Control | `mission-control/desktop-fold.jpg` | `mission-control/tablet-fold.jpg` | `mission-control/mobile-fold.jpg` | `DATABASE_UNAVAILABLE` 错误态 |
| Evidence & Artifacts | `evidence/desktop-fold.jpg` | `evidence/tablet-fold.jpg` | `evidence/mobile-fold.jpg` | `DATABASE_UNAVAILABLE` 错误态 |

完整页面证据还包括各目录下的 `desktop-page-01.jpg`、`tablet-page-01.jpg`、`mobile-page-01.jpg`。临时目录清理后，使用上面的可复现命令即可重建相同 viewport 证据；要验证 populated state，必须先提供可读的本地 PostgreSQL fixture。

### 五维问题矩阵

| 维度 | P0 | P1 | P2 | 当前证据 |
| --- | --- | --- | --- | --- |
| 视觉 | 44–78px 标题压过任务与决定；手机错误标题最多三行 | gradient、glass、eyebrow、静态 shadow 形成营销模板感 | radius、数字、ID 字体与列高尚未统一 | 四页三档截图；lint 的 title、gradient、shadow 命中 |
| 信息架构 | 页面最大元素没有回答页面问题；Mission 的 safe action、Evidence 的 conclusion 都不在首位 | Inbox 的决策优先级藏在卡片内；New Task 的即时约束摘要离提交点太远 | 长计划、tool activity、完整 graph 缺少逐层展开 | 截图、当前 React 结构与 CSS 顺序 |
| 交互状态 | 390px 导航被直接隐藏且无替代入口 | 网络错误没有一致的 Retry、last-good timestamp 和 block-level 恢复路径 | sticky rail 在窄屏只是下移，关键动作可能掉到长列表之后 | `index.css` mobile 规则与三个真实错误态 |
| 可访问性 | 移动标题挤压内容；深层路由失去主导航 | 10–11px tracked uppercase、触控目标与对比度需要系统复测 | details、radio、select、retry、Task row 需完整键盘走查 | lint micro-label 命中、源码字号、390 截图 |
| Agent-native 信任感 | Shell 以 FactFrame 为主身份，SV-Agent 的任务作用域与权威来源不够持续可见 | 原因、依据、non-effects、freshness 没有围绕每个下一动作成组显示 | Evidence Spine、confidence 与 evidence plane 的一致表达尚未形成 | Shell 截图、authority 文案、Mission/Evidence 源码 |

这里的 Agent-native 信任感不是增加拟人化文案，而是让用户在每次动作前都能回答：Agent 现在做什么、依据是什么、不会做什么、谁能批准、数据有多新。

## 共享 Shell 审计

### P0：产品身份不清

Shell 顶部始终把 `FactFrame` 作为主品牌，SV-Agent 只是一项导航。对已经被定义为原生 Agent 的产品，这会让用户不确定自己是在 FactFrame 的附属页面，还是在 SV-Agent 内工作。相关入口见 [`App.tsx`](../../apps/web/src/App.tsx)。

建议：

- 顶部或侧栏主标识改为 `SV-Agent`；`FactFrame` 作为 suite / powered-by 关系退到 workspace switcher 或帮助区。
- Shell 固定显示当前作用域：`Task subject / Task revision / Run revision / authority`，不靠每页重复说明。
- 用一个只属于本产品的标志性元素贯穿页面：**Evidence Spine**。它把七阶段路径、当前 Artifact、阻塞与人工决定连成一条可扫读的证据脊柱，而不是再增加一组卡片。

### P0：营销页层级压过工作内容

全局 `h1` 使用 44–78px，Mission Control 与 Evidence 仍分别使用最高 66px 和 64px。这让页面标题成为最大信息，而不是待处理决定、当前阻塞或证据结论。证据位置：

- [`index.css`](../../apps/web/src/styles/index.css) 的全局 `h1`、eyebrow、按钮样式。
- [`mission-control.css`](../../apps/web/src/features/sv-agent/styles/mission-control.css) 的 hero title。
- [`evidence-artifacts.css`](../../apps/web/src/features/sv-agent/styles/evidence-artifacts.css) 的 hero title。

建议采用 12 / 14 / 16 / 22 / 28 的主尺度：

- 页面标题 22px；手机 20–22px。
- Section 16px；正文 14px；meta 12px，任何可读文字不低于 11px。
- 28px 只给当前页面最重要的数据或决定，不给装饰性标题。
- 删除所有 `SV-AGENT · ...` eyebrow，把必要的 authority / mode 信息放进普通句式的 scope row。

### P0：手机端导航直接消失

当前 720px 以下将 `.topbar nav` 设为 `display: none`，没有 menu sheet 或 bottom navigation。用户进入深层 Task 页面后，只能依赖页面内的返回链接，不能稳定切换产品主区。

建议：

- 390px 使用 48px top bar：menu、当前页标题、一个主要操作。
- menu 打开全屏 sheet，包含 Inbox、New Task、当前 Task、Product Truth 与账户/帮助。
- 列表到详情保持返回时的滚动位置。
- 所有触控目标至少 44px；第一页列表行应在手机首屏 60% 以内开始。

### P1：视觉语言包含明确的生成式网页痕迹

当前全局存在 radial gradient、backdrop blur、静态按钮阴影、uppercase letter-spaced eyebrow；这些都被 Taste lint 捕获。主按钮的阴影在 New Task 和 Inbox 三档宽度都触发 FAIL。

建议：

- 取消渐变与 glass；静止元素不使用 shadow。
- surface 只通过一个 tone step 或 1px border 分层，二者不叠加。
- 主操作使用 near-black flat fill；lime / green 只用于主数据、当前阶段或一个选中状态。
- panel radius 统一为 8px；工作面 16px；control 6px。全站最多三档半径。

## 页面级审计

### 逐页优先级总览

| 页面 | P0：先恢复可用与信任 | P1：再重排任务层级 | P2：最后统一细节 |
| --- | --- | --- | --- |
| Task Inbox | 手机端必须有主导航；服务器失败区必须提供 Retry、last-good 时间并保留权威来源 | 用真实列表计算 needs-decision / blocked / running 摘要；subject、decision question、lane 与下一操作同一视线 | 11px uppercase meta 改为 12px sentence case；本地草稿进一步降级显示 |
| New Task | 手机端不能失去主导航；保存前必须持续看见“仅本地草稿、不会执行” | 压缩标题；把尚缺字段和约束摘要移到提交前；为长表单提供不遮挡内容的单一 sticky submit | 修正 177px ragged row；统一选择块尺寸、字段组间距与 completion 文案 |
| Mission Control | 错误留在 block 内并可重试；首屏必须先回答 next safe action、依据与 non-effects | blocker 紧随动作；Evidence Spine 承载七阶段、当前 Artifact 与人工决定 | plan / activity 改为 disclosure；统一 revision、freshness、ID 对齐 |
| Evidence & Artifacts | 错误时仍保留 Task identity、上次有效摘要和恢复动作；结论必须显示证据边界 | conclusion、缺口、gate readiness 先于完整 graph；plane 按对当前决定的影响排序 | 10px tags/details/code 提升到 12px；仅 ID 使用 mono，整理手机列表密度 |

共享 P0（SV-Agent 主身份、20–24px 标题、手机导航、统一错误恢复）只实现一次，由 Shell 与状态组件承载，不能在四页各自复制一套。

## Task Inbox

**页面问题：哪里现在需要我决定？**

当前最大元素是“Task 与决定收件箱”标题；真正的决策优先级藏在每个 Task card 的右列。这个顺序反了。页面在语义上做对了两件事：明确区分 PostgreSQL 权威记录与浏览器本地草稿；不把本地草稿冒充 Agent 运行状态。相关实现见 [`TaskInboxPage.tsx`](../../apps/web/src/routes/TaskInboxPage.tsx)。

需要调整：

- 首屏先出现按 lane 聚合的决策摘要，例如“2 个待决定 / 1 个被证据阻塞 / 3 个运行中”，数字必须由当前列表计算。
- Task row 的最大元素是 subject；其次是 decision question；lane 与下一操作放在同一视线，不再放进独立的右侧小卡逻辑。
- 默认只显示 4–6 个最高优先 Task，提供“查看全部”，不要用大标题占掉列表空间。
- 服务器错误必须在“已保存 Task”区块内保留 header、上次有效时间和 `重试` 操作。当前错误只有文字，没有可执行的 retry。
- 本地草稿保留单独区域，但视觉更轻；它不是与服务器 Task 对等的第二套 Inbox。

**风险**：`task-inbox-card-meta` 使用 11px uppercase tracking；它虽然没有触发当前 screenshot FAIL，仍低于长期可读性目标，应改成 12px sentence case。

## New Task

**页面问题：建立一个安全可运行的复刻 brief，还缺什么？**

安全边界表达是当前最强的部分：页面清楚说明“保存到当前浏览器”不等于创建 Task/Run/Job，也不会触发 provider、审批或发布。表单 label、focus outline 与错误聚焦机制也基本正确。

主要问题：

- 1440 首屏只出现 5 个业务块中的 2 个；78px 标题和大段说明消耗了工作区。
- 主表单与 320px preview 同行但相差 177px，形成 ragged row。
- preview 在手机端被移到整个表单之后，用户完成输入前看不到它，失去“即时约束摘要”的作用。
- “产品复刻 / 品牌声量”选择块面积过大，字段之间没有明确的完成度与错误摘要。
- 底部 Save 是长表单唯一执行点；手机用户修改顶部字段后需要穿过整个页面才能提交。

建议：

- 把 title 区压缩到一行标题 + 一行“本地草稿，不会执行”的状态条。
- 首屏按顺序呈现：目标轨道、主题、决策问题、参考链接、边界完整度；市场与窗口放在第二组。
- 桌面 preview 改成紧凑的“将记录 / 不会执行 / 尚缺字段”摘要，并随输入更新；手机端放在 submit 前，而不是页面最后。
- 手机端在底部提供 sticky action bar，但内容不遮挡最后一个字段；按钮仍只有一个。
- 不使用进度百分比，除非它从必填字段真实计算；可以使用“还缺 3 项”这种可验证状态。

## Mission Control

**页面问题：Agent 现在在哪里，为什么停在这里，我下一步可以安全地做什么？**

源码已经具备有价值的内容：agent explanation、七阶段路径、计划、activity、blockers、current artifact 和 next safe action。问题是布局仍以大 hero + 主列 + sticky side cards 组织，导致“下一步安全动作”不是首屏第一答案。

需要调整：

- title row 只保留 Task subject、状态、revision 与 freshness。
- 首屏第一个工作块固定为 `Next safe action`，旁边显示其依据引用和明确 non-effects。
- blocker 紧随其后；七阶段路径成为 Evidence Spine，不再作为一组大编号圆点和卡片主导页面。
- plan 与 tool activity 是下钻信息；默认显示关键摘要，详情通过 disclosure 展开。
- 980px 以下 side rail 不能简单整体移到主内容之后。含动作的 Next safe action 必须移到 activity 和长列表之前。

真实错误态也需要重做。当前“无法打开 Mission Control”在手机为三行 44px 标题，在桌面以 78px 红色占据主要空间。错误应该留在失败 block 内：`Mission Control / 数据截至 09:14 / 无法刷新 / 重试`，而不是把整个页面变成错误海报。

## Evidence & Artifacts

**页面问题：当前结论有多少证据，哪些证据缺失，能否进入下一道批准门？**

这个页面的信息结构最接近目标：先有 summary，再有 Artifact graph、独立 Evidence planes、comparison 与只读规则。Product Truth / Performance / Experiment / Asset 分面也比“统一信心分数”更可靠。

需要调整：

- 标题从 64px 降到 22px；summary 成为真正的最大块。
- summary 只保留三个可行动指标：结论状态、证据完整度、当前缺口；每个数值能追溯到 graph/plane。
- conclusion node 固定在 Evidence Spine 顶部，缺失 plane 紧挨结论显示；完整 graph 放下方。
- 目前大量 tags、details、code 使用 10px，低于 app-screen 11px 下限；统一到 12px，ID 可以使用 mono，但说明文本不能。
- 两列 Evidence plane 在手机改成列表是正确方向；需要保证排序按“最影响当前决定”而不是固定 schema 顺序。
- error state 同样应保留页面框架、Task identity 和上次有效摘要，而不是 78px 的错误标题。

## Taste 评分

评分只针对当前可见截图；Mission Control 与 Evidence 的 populated state 尚未视觉验证，因此不对其正常态给出虚假高分。

| 页面 / 状态 | Design | Usability | Creativity | Content | 原始总分 | Gate 后 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| New Task 完整表单 | 6.2 | 7.4 | 6.0 | 8.4 | 6.8 | 6.0（button-fx FAIL） |
| Task Inbox 数据库失败态 | 5.9 | 6.8 | 5.7 | 8.0 | 6.4 | 6.0（button-fx FAIL） |
| Mission Control 错误态 | 5.2 | 5.8 | 5.4 | 7.4 | 5.7 | 5.7（mobile headline FAIL） |
| Evidence 错误态 | 5.8 | 6.2 | 5.5 | 7.4 | 6.1 | 6.1（meter 通过，但只验证错误态） |

### ROUND 1

Seen in one second: 一个超大标题，而不是当前决定或证据。  
Idea: 用 FactFrame 的暖灰与荧光绿，把 SV-Agent 做成带安全说明的营销式工作台。  
Live thing: New Task 的本地草稿表单；其他页在当前环境只显示读取失败。  
Layout words by section: Shell=sticky topbar / Inbox=hero + stacked sections / New Task=hero + form + sticky rail / Mission=hero + main + sticky rail / Evidence=hero + summary + graph + rail。  
Caps applied: New Task 与 Inbox 有 inspector FAIL；Mission 手机标题超过两行。  
Top three problems:

1. 所有页面首先展示标题，而不是工作问题；修复为 22px title row，并让 next decision / safe action / evidence conclusion 成为最大内容。
2. 手机端导航消失；修复为 48px top bar + full-screen menu sheet，保留深层页面返回路径。
3. 渐变、glass、eyebrow 与静态 shadow 形成模板感；修复为 Framed Sheet、flat surfaces、data-only accent。

## 推荐方向：Framed Sheet

Taste Skill 实际抽取了两种适配方向：`achromatic-ledger` 与 `framed-sheet`。推荐后者。

- Direction：`Framed sheet`
- Seed：`1241940699`
- Redraw：无
- 选择理由：SV-Agent 是长时使用、跨 Inbox / Detail / Builder / Report 的 B2B 工作台；它需要稳定的导航框架和明确工作面，而不是全黑账本或营销页面。
- Style move：低彩度 L-frame + 8px inset white sheet + 1px edge + 16px sheet radius；静态元素无 shadow。
- Density：medium；统一 24px gutter。
- Type：建议 IBM Plex Sans；ID、Task/Run/Artifact refs 才使用 IBM Plex Mono。若不引入远程字体，应自托管或选择现有字体中真正支持 tabular figures 的替代，不把字体网络请求当成运行前提。
- Product face：框架使用低彩度 green-grey；现有 lime 只用于当前阶段、主数据或一个选中状态，色彩面积控制在 3% 内。
- Signature element：Evidence Spine，而不是新增装饰图形。

## 目标信息架构

```text
SV-Agent shell
├── Inbox
│   ├── Needs decision
│   ├── Blocked / needs evidence
│   ├── Running
│   └── Browser-local drafts
├── New task
│   ├── Goal and decision
│   ├── Reference and scope
│   ├── Market and observation window
│   └── Rights / child-safety boundary
└── Task workspace
    ├── Mission Control
    │   ├── Next safe action
    │   ├── Blocker and decision
    │   ├── Evidence Spine
    │   └── Plan / activity details
    └── Evidence & Artifacts
        ├── Conclusion and readiness
        ├── Missing evidence planes
        ├── Artifact dependency graph
        └── Audit details
```

这不是要求创建新的路由树；优先在现有 routes 与组件内重排，避免为了视觉重构改变业务合同。

## 可执行批次与 Todo

按下面顺序实施；后一批必须在前一批验收通过后开始，避免局部视觉改动掩盖 Shell 与状态问题。

### Batch A：P0 Shell 与状态门

**入口条件**：保留本报告的三档基线截图；准备一组可读、无私有资产的开发 PostgreSQL Task fixture，专门用于 populated-state 视觉复测。  
**退出条件**：Shell、导航、标题尺度、错误恢复和最小字号通过 1440 / 768 / 390；四页不再因共享 Shell 问题重复失败。

### P0：Shell 与可用性门

- [ ] 新建 app tokens：ground / surface / border / text / muted / accent / status；移除 gradient、glass、resting shadow。
- [ ] 将全站 app title 收敛到 20–24px；删除 SV-Agent 页面 eyebrow。
- [ ] 让 Shell 以 SV-Agent 为主身份，并固定显示 Task/Run scope。
- [ ] 增加 390px menu sheet 或 bottom navigation，不能再隐藏导航后不提供替代。
- [ ] 重构 block-level loading / empty / error / stale；所有网络错误有 Retry 和 last-good timestamp。
- [ ] 将所有可读文字提升到至少 11px；普通 meta 统一 12px。

### Batch B：P1 页面问题优先

**入口条件**：Batch A 的 `lint.mjs` 与四页 error-state inspector 为 0 FAIL。  
**退出条件**：每页首屏最大信息回答该页问题；full / sparse / empty / loading / error / stale 均有可辨认且可恢复的设计。

### P1：页面任务优先级

- [ ] Inbox 首屏先显示需要决定、被阻塞和运行中的真实计数；Task row 让 lane、原因和下一操作一起可见。
- [ ] New Task 压缩 heading，把约束摘要移到 submit 前；手机提供不遮挡内容的 sticky submit。
- [ ] Mission Control 把 Next safe action 和 blocker 放到首屏；Evidence Spine 取代大面积阶段卡片。
- [ ] Evidence 让 conclusion、缺口和 gate readiness 先于完整 graph；按决策影响排序 evidence planes。
- [ ] 为所有页面实现并单独预览 full / sparse / empty / loading / error / stale 状态。

### Batch C：P2 一致性与无障碍

**入口条件**：Batch B 的 populated-state 三档截图完成评审。  
**退出条件**：键盘、focus、对比度、字号、触控目标、数字对齐和 sticky 行为全部通过下方验收标准；新截图与本报告基线并排复核。

### P2：视觉与细节

- [ ] 统一 tabular numbers、日期、revision 与 ID 对齐；只给 ID/keys 使用 mono。
- [ ] 统一 panel 与 control radius，消除 border + shadow 双重分层。
- [ ] 检查 sticky rail 与主列高度，避免 ragged row 和 panel void。
- [ ] 用真实业务词替换开发者式英语标签；保留必要专有名词，不使用 uppercase tracked copy。
- [ ] 键盘走查 navigation、details、radio、select、retry、Task row 与 next action。

## 验收标准

1. `lint.mjs --app apps/web/src` 为 0 FAIL；每个 WARN 有书面、页面级理由。
2. 四条核心路由在 populated / empty / loading / error / stale 五类状态完成 1440、768、390 检查。
3. `inspect.mjs --app` 四页均为 0 FAIL；无 app title size、hidden mobile navigation、ragged row、panel void、button-fx。
4. 页面最大元素回答页面问题；首屏包含当前决定、下一安全动作或证据结论，而不是 hero 文案。
5. 手机端始终存在可用导航，触控目标至少 44px，首个工作行出现在首屏 60% 内。
6. 所有正文与 meta 达到 4.5:1；文字不低于 11px；focus-visible 清楚可见。
7. 数值使用 tabular figures，重复事实来自同一变量；zero、missing、stale 分别显示为 0、dash、freshness stamp。
8. 最终以真实 PostgreSQL fixture 复测 populated state；错误态通过不等于正常态验收。

## 保留项

以下现有能力应保留，不因视觉重构被弱化：

- PostgreSQL 与浏览器本地草稿的权威边界。
- “不会执行”的明确 non-effects。
- Product Truth、Performance、Experiment、Asset 独立证据面。
- Task/Run revision、Artifact ref、proof level 与 evidence level 的可追溯性。
- 原生表单 label、错误聚焦、`role="alert"` 与 focus-visible。

