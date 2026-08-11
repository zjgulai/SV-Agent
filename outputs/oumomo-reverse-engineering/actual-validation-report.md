# Oumomo 四功能黑盒逆向蒸馏实测报告

日期：2026-08-10
范围：爆款榜单、爆款复刻、链接生视频、爆款脚本生成
方法：正常 UI 操作、可见 DOM、被动请求路径/字段结构、任务状态、余额和输出内容对照。未读取 Cookie、Token、请求头或个人数据，未重放接口、枚举隐藏参数或绕过权限。

## 0. 结论先行

### 最推荐复刻：爆款脚本生成

这是四项中价值、技术壁垒和实施复杂度比值最优的一项。

- 实际价值：★★★★★
- 技术壁垒：★★★☆☆
- 实施复杂度：★★★☆☆
- 当前可验证性：★★★★★
- 建议优先级：P0

推荐复刻的不是“一个大模型输入框”，而是以下闭环：

1. 商品链接解析与证据化商品事实；
2. 商品品类与卖点规范化；
3. 爆款结构检索与模板选择；
4. 强类型脚本生成；
5. 时间轴、分镜、口播、画面、动作、字幕和验收镜头；
6. 事实校验、时长校验、版本化与导出；
7. 生成结果与投放表现反馈。

不建议第一阶段复刻完整“链接生视频”或“爆款复刻”。它们需要视频生成模型路由、素材一致性、异步任务、计费、失败恢复和媒体质检，技术复杂度高一个数量级，而本次实测已经暴露提交失败、视频不可用和上传前置依赖。

### 本轮实际执行结果

| 功能 | 实测状态 | 实际扣分 | 关键结论 |
|---|---:|---:|---|
| 爆款榜单 | 已完成多组筛选与排序验证 | 0 | 两级品类和 URL 状态设计清晰，但高 GMV 筛选存在确定性错误 |
| 爆款脚本生成 | 完成 30s 基线与 15s 单变量对照 | 20 | 输出结构完整、约 16 秒完成；第二次生成复用并覆盖同一任务 |
| 链接生视频 | 完成解析和配置，生成提交失败 | 0 | 商品事实抽取成功；生成卡死且返回 HTML 被当作 JSON 解析 |
| 爆款复刻 | 已完成 1 次 Mini/480P/15s 基线任务并抽检成片 | 30 | 约 239 秒完成；商品外观保持较好，但参考视频不可播放，结构复刻无法对照，且自动文案出现无依据卖点 |

余额从 1,030 变为 980：两次脚本生成各扣 10 积分，单次爆款复刻扣 30 积分，合计 50 积分。链接生视频失败未扣分。

## 1. 证据等级

- **F（Fact）**：本轮页面、可见输出、任务状态或余额直接证实。
- **I-H（High-confidence inference）**：由多个可见状态和请求序列共同支持。
- **I-M（Medium-confidence inference）**：符合现象，但缺少服务端或模型内部证据。
- **U（Unknown）**：黑盒测试无法确认。
- **Vendor claim**：仅为官网文案，不能当作技术事实。

## 2. 实测总能力图谱

```text
爆款数据层
├── 地区、两级品类、GMV、内容来源、时间窗口
├── 销量/浏览量排序
├── 卡片指标、收藏、参考视频选择
└── 数据质量与时间边界

商品理解层
├── TikTok/FastMoss 链接规范化
├── 商品标题、图片、品类抽取
├── 核心卖点抽取与人工编辑
└── 图片管理与受众/优惠补充

创意规划层
├── 爆款样本匹配
├── Hook/痛点/产品介入/实测/结果/CTA
├── 脚本类型、时长和语言控制
├── 分阶段时间轴与镜头结构
└── 标题、标签和拍摄准备

视频生产层
├── 参考视频结构复刻
├── 商品图/素材融合
├── Mini/快速/高质路由
├── 480P/720P、15s/30s、数量
└── 异步生成、项目管理、编辑与导出

平台基础设施
├── 任务初始化、轮询、任务结果
├── 积分报价与扣费
├── 项目列表与任务队列
├── 上传、媒体存储和预览
└── 日志、故障恢复和幂等性
```

## 3. 爆款榜单与筛选

### 3.1 可见功能与参数语义（F）

- 地区：美国、印度尼西亚、越南、泰国、菲律宾、马来西亚、英国、日本、韩国、加拿大、法国、德国、阿联酋、墨西哥、西班牙、意大利、巴西。
- 一级品类：30 个；选择一级品类后出现二级品类。
- GMV：全部、`<$1000`、`$1000-$1万`、`$1万-$5万`、`>$5万`。
- 视频类型：全部、AI生成、用户原创。
- 发布日期：全部、近 7/14/28/60/90/180 天。
- 排序：销量、浏览量。
- 卡片字段：文案/封面、品类、视频类型、发布日期、销量、销售额、浏览量、收藏入口、复刻入口。

筛选状态进入 URL，已经验证的参数包括：

```text
region=US | GB
date_type=7
l1_cid=14
gmv=10000,50000
gmv=50000,-1
is_aigc=1
```

这说明筛选状态是可分享、可刷新和可审计的，而不是只存于临时组件状态。（F）

### 3.2 已验证行为

1. 美国、近 7 天、按销量排序时，第一页显示 12 个结果。（F）
2. 切换英国后约 3–5 秒加载英国结果。（F）
3. “美妆个护”需要先选一级品类，再选二级区域中的“全部”，最后产生 `l1_cid=14`。（F）
4. 美妆筛选后，12 个结果全部显示为美妆个护。（F）
5. `$1万-$5万` 对应 `gmv=10000,50000`，能返回 12 个结果。（F）
6. “AI生成”对应 `is_aigc=1`；本次全地区、全日期无结果。（F，不能由此断言数据源没有 AI 视频）

### 3.3 确定缺陷

**高 GMV 筛选错误（严重级别：高）**

- 未筛选榜单明确存在 `$7.688万`、`$6.104万`、`$6.598万` 等大于 `$5万` 的记录。
- 选择 `>$5万` 后，URL 正确变为 `gmv=50000,-1`。
- 单独使用该筛选以及与美妆品类组合，均稳定返回 0 条和“未找到匹配项”。
- 相邻区间 `$1万-$5万` 正常返回结果。

结论：不是“当前没有高 GMV 数据”，而是高概率存在上界 `-1` 处理、货币单位、查询条件或索引转换错误。（F + I-H）

其他缺陷：

- 筛选加载需要 2.5–5 秒，期间缺少清晰的结果级 loading/skeleton，容易被误判为空结果。（F）
- 首个高销量参考视频在复刻配置 iframe 中显示 `Video currently unavailable`，但仍允许进入复刻付费流程。（F）
- 排序仅有销量和浏览量，没有 GMV、CTR、CVR、2 秒/6 秒留存或互动率。（F）
- 卡片没有数据更新时间、来源、货币换算口径或指标置信度。（F）

### 3.4 与成熟工程的差距

TikTok Top Ads 官方能力包含 Region、Industry、Objective、Likes、Time frame、语言、格式，并支持 Reach、CTR、2 秒观看率、6 秒观看率、CVR 和逐秒表现分析。Oumomo 当前更像“带货销量榜”，缺少创意归因和转化漏斗，无法回答“为什么爆”。

参考：[TikTok Top Ads Dashboard](https://ads.tiktok.com/help/article/how-to-use-the-top-ads-dashboard?lang=en)、[TikTok One Top Ads insight](https://ads.tiktok.com/help/article/about-top-ads-insight-in-tiktok-one?lang=en)

### 3.5 评分

| 维度 | 星级 | 说明 |
|---|---:|---|
| 实际价值 | ★★★★☆ | 能显著降低选题成本 |
| 数据壁垒 | ★★★★☆ | 真正壁垒是合法、持续、可校验的数据，而非筛选 UI |
| 实现复杂度 | ★★★☆☆ | UI 简单，采集、归一化和质量治理较难 |
| 当前可信度 | ★★☆☆☆ | 高 GMV 错误直接影响核心决策 |

## 4. 爆款脚本生成

### 4.1 实测工作流（F）

```text
示例商品链接
→ task_init
→ init_status 轮询
→ init_info 取商品信息
→ 用户检查/编辑 3 个卖点
→ 配置时长、脚本类型、语言、受众、优惠
→ submit_task
→ task_status 轮询
→ 结构化脚本结果
```

观察到的请求路径：

```text
GET  /api/product_script/const_info
POST /api/product_script/task_init
GET  /api/product_script/init_status?task_no=...
GET  /api/product_script/init_info?task_no=...
POST /api/product_script/submit_task
GET  /api/product_script/task_status?task_no=...
GET  /api/user/get_func_point
```

仅记录字段结构、不记录值。`task_init`：

```json
{"product_url":"string"}
```

`submit_task`：

```json
{
  "task_no": "string",
  "sell_points": "string",
  "refer_videos": "string",
  "lang": "string",
  "promotions": "string",
  "target_group": "string",
  "duration": "number",
  "script_type": "number"
}
```

### 4.2 商品理解结果（F）

示例商品被识别为冲调饮品，输出商品标题、三级品类和 3 个卖点。卖点支持拖动排序、修改、新增和删除。链接解析约 10 秒，未扣分。

可配置项：

- 时长：15s、30s、45s。
- 类型：场景实测、痛点解决、口播种草、开箱展示、对比测评、教程教学、反常识避坑。
- 语言：英语、西班牙语、西班牙语（墨西哥）、法语、葡萄牙语、普通话、越南语、泰语、印尼语、德语、日语、韩语、马来语。
- 可选：目标人群、优惠信息。

### 4.3 30s 基线结果（F）

- 完成时间：约 16.5 秒。
- 结构：4 个阶段、6 个镜头。
- 主链：场景痛点 → 产品介入 → 使用实测 → 结果展示/CTA。
- 每个镜头包含：时间段、Phase、Shot、Voiceover、Visual、Action、Caption，部分镜头包含 Acceptance Shot。
- 附带：Materials Prep、Key Shot Requirements、Execution Notes、3 个标题、5 个标签。

### 4.4 15s 单变量对照（F）

只把时长从 30s 改为 15s，其余输入保持一致：

- 完成时间：约 16.1 秒。
- 结构压缩为 3 个阶段、4 个镜头。
- 保留疲惫痛点、冲调展示、200mg 咖啡因、无糖和 CTA。
- 删除 30s 版本中的独立产品介绍和部分结果展示镜头，将卖点合并进实测镜头。
- 请求中的 `duration` 从 30 变为 15，`script_type` 保持 1。

结论：时长不是简单截断文本，而是触发结构级重新规划。（F + I-H）

### 4.5 缺陷与风险

- 两次付费生成复用同一个 `task_no` 和详情 URL，第二次结果覆盖第一次；项目管理角标只增加 1，但余额扣了两次 10 积分。（F）
- 缺少脚本版本历史、差异对比、候选方案和回滚。（F）
- 30s 生成进度显示匹配 `TOP 4`，最终结果却写 `Top10 样本共性`，依据口径不一致。（F）
- 页面宣称基于 1000 万/百亿级数据，但没有给出样本 ID、数据时间、检索分数或可追溯证据。（Vendor claim + U）
- 同一商品的核心卖点在解析页与结果页发生措辞变化，说明生成链路会二次改写事实；缺少字段级来源与事实锁定。（F + I-H）
- 15s 结果中参考品类出现英文路径，而商品卡仍显示中文路径，分类体系没有完全统一。（F）

### 4.6 与成熟工程的差距

成熟的 URL-to-video/广告脚本流程通常先给出多个脚本候选，允许选择、编辑、预览，再进入渲染；结果和项目是版本化的。Creatify 的公开流程明确包含多脚本候选、DIY 脚本、风格/avatar/voice 选择、编辑器和预览后渲染。Oumomo 当前脚本结构质量不错，但版本管理和证据链明显不足。

参考：[Creatify URL-to-video workflow](https://creatify.ai/blog/how-to-create-video-ads-with-ai)

### 4.7 评分

| 维度 | 星级 | 说明 |
|---|---:|---|
| 实际价值 | ★★★★★ | 可直接转化为拍摄任务和视频生成输入 |
| 技术壁垒 | ★★★☆☆ | 壁垒主要在商品事实、检索语料和质量校验 |
| 实现复杂度 | ★★★☆☆ | 可先用结构化 LLM 工作流落地 |
| 当前稳定性 | ★★★★☆ | 两次均成功，但版本覆盖是严重产品缺口 |

## 5. 链接生视频

### 5.1 已证实工作流

```text
TikTok/FastMoss 商品链接
→ GET /api/link_video/get_product_info?product_url=...
→ 商品标题、品类、图片、3 个卖点
→ 编辑卖点/补充白底图
→ 语言、受众、模式、清晰度、时长、数量
→ 生成任务
→ 项目管理/编辑/导出（本轮未进入）
```

商品解析成功，结果与脚本生成功能一致，说明两项功能很可能共享商品理解组件。（F + I-H）

观察到的配置：

- 图片：自动提取 1 张，可补充至 9 张。
- 模式：Mini、快速、高质。
- 清晰度：480P、720P。
- 时长：15s、30s。
- 数量：至少支持 1。
- 输入：语言和目标人群。
- 实测最低报价：Mini + 480P + 15s + 1 个 = 30 积分。
- Mini + 720P + 15s + 1 个 = 50 积分。

官网 FAQ 声称默认 Seedance 2.0，并可切换 Sora 2、Veo 3.1、Gemini Omni、Kling V3；本轮配置 UI 只显示质量模式，没有证实各模式与具体模型的路由关系。（Vendor claim + U）

### 5.2 生成故障（严重级别：阻断）

点击“立即生成 30 积分”后：

1. 页面进入 `/zh/url-to-video/workspace?...`；
2. 按钮持续为“生成视频中…”且禁用；
3. 未观察到业务任务提交接口；
4. 39 秒后仍没有任务 ID、进度或失败提示；
5. 控制台记录：返回内容以 `<!DOCTYPE ...` 开始，但客户端尝试按 JSON 解析；
6. 余额保持 1,010，没有扣分。

这是提交阶段的响应契约/路由错误，不是视频模型生成超时。（F + I-H）

### 5.3 与成熟工程的差距

Creatify 的公开 API 把流程拆成链接抓取、脚本、预览、最终渲染，并提供 job ID、轮询或 webhook；预览 URL 能先展示不同布局，再决定最终渲染。TikTok Symphony 也强调 preview、script、avatar、editor、translate/dub 和 export 的端到端组合。

Oumomo 当前的主要问题不是模型选择少，而是提交契约不稳定、没有可见 job ID、错误无法恢复、没有明确预览计费边界。

参考：[Creatify API URL-to-video](https://docs.creatify.ai/use-case/url-to-video)、[TikTok Symphony Creative Studio](https://ads.tiktok.com/help/article/about-symphony-creative-studio?lang=en)

### 5.4 评分

| 维度 | 星级 | 说明 |
|---|---:|---|
| 实际价值 | ★★★★★ | 成功时能显著缩短视频生产周期 |
| 技术壁垒 | ★★★★☆ | 商品理解、脚本、素材匹配、视频生成和后处理的组合壁垒 |
| 实现复杂度 | ★★★★★ | 多模型、媒体任务、计费和质检都很重 |
| 本轮可靠性 | ★☆☆☆☆ | 核心生成提交失败 |

## 6. 爆款复刻

### 6.1 已证实工作流

```text
榜单/链接选择参考视频
→ 原视频 iframe 预览
→ 上传 1–9 张白底商品图（强制）
→ 可选 2000 字复刻提示词
→ 比例、时长、语言、生成模式、清晰度、数量
→ 2–5 分钟异步任务
→ 项目管理查看
```

可见配置与报价：

- 比例：当前为 9:16。
- 时长：15s，页面标注新增 30s。
- 模式：Mini、快速、高质。
- 清晰度：480P、720P。
- 默认快速 + 720P + 15s = 75 积分。
- Mini + 720P + 15s = 50 积分。
- Mini + 480P + 15s = 30 积分。

### 6.2 基线任务实测结果

测试图：`evidence/fixtures/pulse-mix.png`。这是一张本轮自制的白底合成商品图，不包含真实品牌、价格、功效或认证信息。

- 开启 Chrome 扩展的本地文件访问后，商品图上传成功，UI 从 `0/9` 变为 `1/9`。（F）
- 冻结配置为 `9:16 / 15s / 英语 / Mini / 480P / 1 个`，不填写可选提示词；按钮报价 30 积分。（F）
- 只点击一次生成；任务队列只增加 1 条爆款复刻任务，没有重复任务。（F）
- 可见进度序列为 `5% → 45% → 55% → 70% → 80% → 95% → 已完成`，从点击到完成约 239 秒，落在页面承诺的 2–5 分钟内。（F）
- 任务页余额在生成期间仍显示 1,010；进入项目管理后刷新为 980，净扣 30 积分。说明余额 UI 存在延迟刷新，但账务结果与报价一致。（F）
- 项目管理新增 1 个“爆款复刻”项目，提供预览、下载、重新生成和 TikTok 官方发布入口。（F）
- 成片为 CDN MP4，媒体元数据为 15.104 秒、496×864；与“15s”一致，但实际像素尺寸不是字面上的 480×854/864。（F）
- 在约 4 秒、6 秒和 15 秒三个可见帧抽检中，白/蓝包装、闪电标识及 `PULSE MIX` 文字保持稳定，未观察到明显换色或 Logo 漂移。（F）
- 原参考视频从配置到生成结束始终显示 `Video currently unavailable`，所以无法验证钩子、镜头序列、节奏和 CTA 是否真的继承原片。（F）

项目页暴露了一份生成提示词，固定分为 `environment / character / action / dialogue / constraints`。这证明产品图和参考结构并非直接交给最终视频模型，而是先经过中间创意计划/提示词编译层。（F + I-H）

该编译层存在明显事实安全问题：在用户只上传无文字功效说明的商品图、且未填写提示词时，系统自行生成了“real energy boost”“flavor is amazing”“one scoop”“game changer”等口播。它还写入“Reference image is for character identity only”，与本例纯商品图语义冲突，表现出通用模板泄漏。（F）

### 6.3 价值与壁垒

爆款复刻真正的技术壁垒不是“把参考视频丢给模型”，而是：

1. 参考视频时间轴、镜头、动作、字幕、语音和 CTA 的多模态分解；
2. 区分可复用结构与不可复制的具体表达；
3. 把新商品的外观、材质和文字稳定地保持在跨镜头视频中；
4. 音画同步、人物手持、物理接触和产品文字一致性；
5. 版权、肖像和平台重复内容风险控制；
6. 用可量化的结构相似度和视觉原创度做双重验收。

### 6.4 与成熟工程的差距

Creatify 将“参考广告分析”明确拆成 Hook、节奏、场景结构和 CTA flow，并围绕新产品生成新版本；TikTok Symphony 提供 reference-to-video、产品 avatar、editor 和平台内导出。Oumomo 当前配置很简洁，而且本轮确实生成了可播放成片；但仍没有在付费前展示结构拆解、继承/改写边界、事实声明检查或原创度/产品一致性预检。它甚至允许在参考视频不可播放时继续扣费生成。项目页虽然展示最终提示词，却没有逐条标注哪些内容来自商品事实、参考视频或模型补全。

参考：[Creatify Features](https://creatify.ai/features)、[TikTok Symphony Suite](https://ads.tiktok.com/business/en-US/blog/tiktok-symphony-ai-creative-suite)

### 6.5 评分

| 维度 | 星级 | 说明 |
|---|---:|---|
| 实际价值 | ★★★★☆ | 对成熟投放团队很有价值 |
| 技术壁垒 | ★★★★★ | 多模态理解和跨镜头产品一致性困难 |
| 实现复杂度 | ★★★★★ | 生成、合成、审核、版权和评测都很重 |
| 当前可验证性 | ★★★★☆ | 任务、扣费、成片和提示词已验证；原片失效导致结构复刻仍不可验 |

## 7. 推定的 AI 组件与证据边界

| 组件 | 证据 | 状态 |
|---|---|---|
| URL 规范化与站点适配器 | 两项功能均能解析同一 TikTok Shop 链接 | F |
| 商品事实抽取器 | 标题、图片、分类、卖点结构化输出 | F |
| 分类体系映射 | 三级类目与中英文类目混用 | F，具体模型 U |
| 卖点生成/重写器 | 解析页与结果页卖点措辞发生变化 | I-H |
| 爆款样本检索器 | 进度和结果显示 Top4/Top10/Top50 | F，真实检索与样本 U |
| 结构选择器 | 不同时长生成不同阶段和镜头数 | I-H |
| 结构化脚本生成器 | 稳定输出固定字段 | F |
| 标题/标签生成器 | 输出 3 标题、5 标签 | F |
| 视频模式路由器 | Mini/快速/高质影响价格 | F，实际模型映射 U |
| 异步任务编排器 | task_init/submit/status 与项目列表 | F |
| 复刻提示词编译器 | 项目页暴露 environment/character/action/dialogue/constraints | F，输入归因与具体模型 U |
| 媒体输出与项目资产 | 复刻项目提供 MP4、封面、下载、重生成和发布入口 | F |
| 积分计费器 | 两次脚本生成扣 20，单次复刻扣 30 | F |
| 视频质检器 | 页面没有暴露自动质检结果；本轮仅做三帧人工抽检 | 自动质检 U |
| 原创度/版权检查 | 仅有营销承诺，没有测量结果 | Vendor claim/U |

不能从黑盒现象确认具体 LLM、视觉模型、Embedding 模型、向量数据库、模型温度、系统提示词或训练数据。复刻工程应采用 clean-room 设计，不以猜测冒充事实。

## 8. 推荐的 clean-room 实施框架

### Phase 1：商品事实与脚本 P0

```text
Connector Registry
→ Product Snapshot
→ Fact/Evidence Graph
→ Selling Point Editor
→ Creative Pattern Retriever
→ Typed Script Planner
→ Factuality & Duration Validator
→ Versioned Script Artifact
```

必要数据对象：

```text
ProductSnapshot
  id, source_url, title, category_path, images[], price,
  facts[{claim, evidence_url, evidence_text, confidence}]

CreativePattern
  hook_type, phase_sequence[], shot_archetypes[],
  target_duration, category, evidence_video_ids[]

ScriptVersion
  product_snapshot_id, input_config, phases[], shots[],
  titles[], tags[], validation_report, parent_version_id
```

### Phase 2：榜单与证据检索 P1

- 只接入有权使用、口径可解释的数据。
- 原始指标与换算指标分开保存。
- 所有时间窗口使用明确时区、闭开区间和快照时间。
- 查询前后执行数据质量约束，例如 `GMV > 50000` 必须能包含未筛选结果中的相同记录。
- 增加 CTR、CVR、2s/6s retention、engagement、样本量和置信区间。

### Phase 3：预览优先的视频流水线 P2

```text
ScriptVersion
→ Storyboard JSON
→ Low-cost Preview
→ Human Edit/Approve
→ Credit Reservation
→ Render Job
→ Media QC
→ Accept or Refund/Retry
→ Export
```

关键状态机：

```text
DRAFT
→ PARSING
→ READY_FOR_CONFIG
→ PREVIEWING
→ PREVIEW_READY
→ USER_APPROVED
→ CREDIT_RESERVED
→ RENDERING
→ QC
→ SUCCEEDED | FAILED_REFUNDABLE | FAILED_NONREFUNDABLE
```

所有提交必须带 `idempotency_key`。客户端重试不得重复扣费或创建重复任务。返回体必须有稳定的 JSON content type、错误码、job ID 和恢复建议。

## 9. 复刻优先级与投入判断

| 模块 | 价值 | 壁垒 | 复杂度 | 推荐 |
|---|---:|---:|---:|---|
| 商品事实 + 结构化脚本 | 5 | 3 | 3 | 立即做 |
| 榜单筛选 UI | 3 | 1 | 1 | 有数据源时做 |
| 榜单数据管线 | 5 | 5 | 4 | 有合法数据优势才做 |
| 低成本 storyboard preview | 5 | 4 | 4 | 脚本稳定后做 |
| 参考结构拆解 + typed storyboard/prompt compiler | 5 | 4 | 3 | 脚本闭环后优先做 |
| 链接生最终视频 | 5 | 4 | 5 | 第二阶段后期 |
| 爆款复刻成片 | 4 | 5 | 5 | 最后做 |

推荐 MVP：

1. 支持 2–3 个电商链接来源；
2. 商品事实带证据来源，可人工锁定；
3. 7 类脚本结构，15/30/45 秒；
4. 每次生成 3 个候选，不直接覆盖；
5. 每个镜头输出 Voiceover/Visual/Action/Caption/Acceptance Shot；
6. 版本历史、diff、回滚和 JSON/Markdown 导出；
7. 先用 storyboard/低成本 preview 验证，再接视频模型。

## 10. 验收指标

- 商品解析成功率、字段覆盖率、事实错误率。
- 首次可用脚本时间、脚本接受率、平均修改量。
- 时长误差、镜头字段完整率、禁用/不实 claim 命中率。
- 版本覆盖率必须为 0；所有付费生成可回溯。
- 任务提交成功率、P95 排队与生成时间、重复扣费率。
- 视频产品一致性、文字可读性、手持/物理交互缺陷率。
- 每个可接受素材成本，而不是每次生成成本。
- 上线后用 CTR/CVR/2s/6s retention 做真实反馈闭环。

## 11. 剩余验证边界

1. 找到一条可稳定播放、允许分析的参考视频，再做原片与成片的 Hook、镜头序列、节奏和 CTA 对照；本轮不能据成片成功推断“复刻结构”已成立。
2. 若要估计随机性，需要用完全相同输入再生成一次；这将再消耗 30 积分，本轮没有扩大预算。
3. 若要核验音频口播、OCR、编码和文件下载，需要单独执行媒体下载与离线质检；本轮只验证了浏览器可播放、媒体元数据和三帧视觉一致性。
4. 链接生视频应先确认服务端不再返回 HTML 解析错误，再重新提交；未修复前不建议重复尝试。

## 12. 官方参考

- [Oumomo 用户指南](https://www.oumomo.ai/zh/user-guide)
- [Oumomo 积分与退款规则](https://www.oumomo.ai/refunds)
- [Oumomo 服务条款](https://www.oumomo.ai/terms)
- [TikTok Top Ads Dashboard](https://ads.tiktok.com/help/article/how-to-use-the-top-ads-dashboard?lang=en)
- [TikTok One Top Ads insight](https://ads.tiktok.com/help/article/about-top-ads-insight-in-tiktok-one?lang=en)
- [TikTok Symphony Creative Studio](https://ads.tiktok.com/help/article/about-symphony-creative-studio?lang=en)
- [Creatify URL-to-video API](https://docs.creatify.ai/use-case/url-to-video)
- [Creatify URL-to-video workflow](https://creatify.ai/blog/how-to-create-video-ads-with-ai)
- [Creatify Features](https://creatify.ai/features)
