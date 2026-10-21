# SV-Agent 视频生成模型选型与适配方案

> 审计日期：2026-10-21  
> 结论类型：本地只读清点 + 官方文档研究 + 待批准实施方案  
> 当前交付状态：**未调用任何模型、未产生费用、未验证运行时、未批准视频生成产品范围**

## 1. 结论先行

SV-Agent 的第一版视频生成能力应通过一个独立的 `VideoGenerationProvider` 接入 TokenHub，而不是复用当前面向文本的 `ScriptProvider`，也不应把 Magpie 中名为 `vod` 的通用模型供应商直接当作腾讯云 VOD AIGC API。

推荐的模型组合如下：

| 层级 | 模型 | 主要任务 | 采用条件 |
| --- | --- | --- | --- |
| 主力 | `minimax-video-h3` | 多参考素材、人物/产品一致性、首尾帧、需要 2K 的重点镜头 | 通过付费 smoke test、素材权利与隐私门 |
| 主力 | `kling-video-v3` | 通用 T2V/I2V、多镜头叙事、原生音频、最高 4K 的成片候选 | 通过付费 smoke test；显式选择音频与成本档 |
| 快速草稿 | `minimax-video-h3-max` | 首帧/首尾帧草稿、低成本多版本探索 | 只请求 480P/768P；禁止依赖其不支持的多模态参考能力 |
| 快速草稿 | `kling-video-v3-turbo` | 文生/图生的快速预览和成本敏感批次 | 不要求原生音频和多镜头 |
| 专项主力 | `kling-video-motion-control-v3.0` | 将参考动作迁移到已授权的单个主体 | 不允许无提示降级到普通 I2V；失败后回到人工决策 |
| 专项主力 | `pixverse-video-c1` | 高速运动、强动态、特效型短视频、结构化分镜 | 通过动态场景专项质量基准 |
| 备选/实验 | `pixverse-video-v6.0`、`vidu-video-q4-preview`、`kling-video-v3-omni`、`wand-vega-video-1.0-lite` | 多镜头、参考主体、复杂多模态、规模化生产等专项能力 | 先刷新 capability snapshot，再分别做低成本 smoke test 与合规审查 |
| 兼容备选 | MiniMax v2.3、Kling v2.5/v2.6、Vidu q2/q3、PixVerse v5.6、HY Video 1.5 | 已有任务回放或主力不可用时的受控降级 | 只在参数语义、成本档和质量门等价时启用 |
| 默认禁用 | `yt-video-humanactor` | 单图驱动真人/人像 | 未完成肖像权、未成年人保护和滥用风险设计前不得进入自动路由 |

这不是一次“选一个最强模型”的决策。爆款复刻同时包含结构复刻、主体一致性、动作迁移、动态特效、首尾帧控制和批量探索；最稳妥的产品形态是**按任务能力路由、按风险审批、按实际效果持续评测**。

## 2. 范围与证据口径

### 2.1 本次做了什么

- 只读检查 Magpie.app 安装信息、Magpie 本地 provider registry 和模型目录缓存。
- 只记录 provider 名称、公开模型 ID、数量、开关/配置存在性和缓存时间；没有复制密钥、账号、私有 URL 或完整配置。
- 用腾讯云 TokenHub、VOD 官方文档核对模型能力、调用方式、计费、地域和数据处理边界。
- 结合当前 SV-Agent 的范围和事实源边界，提出 adapter、路由、预算、异步执行、证据链和后续 tickets。

### 2.2 四层状态必须分开

| 状态 | 含义 | 本次能否证明 |
| --- | --- | --- |
| discovered | provider 或模型出现在本地 registry/cache | 能 |
| configured | provider 存在非空凭据字段与 base API 配置 | 能证明“字段存在”，不能证明值有效 |
| selected / not explicitly disabled | 模型在 Magpie 的已选列表；provider 无显式禁用标记 | 能证明本地选择状态 |
| runtime-verified | 发起真实请求，任务成功，并取得可读取、可探测的媒体文件与费用回执 | **不能；本次未做外部或付费调用** |

因此，下文的“已配置”“已选择”都不能解释为“可调用”“已开通额度”“已通过内容审核”或“适合生产”。TokenHub 官方建议用鉴权后的 `/v1/models` 获取当前可调用模型和状态；该调用也留到受控 smoke gate 执行。[TokenHub API 使用说明，2026-10-20](https://cloud.tencent.com/document/product/1823/130078)

## 3. 本地 Magpie 清点

### 3.1 安装与快照

| 项目 | 安全清点结果 | 证据 |
| --- | --- | --- |
| Magpie.app | 已安装；版本 `0.1.1255` | `/Applications/Magpie.app/Contents/Info.plist`，只读字段检查 |
| provider registry | `tokenhub` 与 `vod` 均存在、均未显式禁用、均有 credential/base API 字段 | `~/.config/magpie/providers.json`，仅字段存在性与计数检查；文件修改于 2026-10-18 |
| TokenHub | provider registry 有 106 个本地模型 ID，103 个处于 Magpie 已选列表；其中 25 个 ID 可由官方模型目录归为视频生成或动作驱动候选 | 同上；另一个于 2026-10-15 获取的模型目录 cache 有 117 个条目，说明 registry 与 catalog 不是同一状态层 |
| VOD | provider registry 与 2026-10-15 cache 均有 68 个模型 ID并处于已选列表；没有任何 ID 能与本次核对的腾讯云 VOD AIGC 视频生成版本表建立安全映射 | 同上 |

本地 `tokenhub` 已选择的 25 个视频候选 ID：

- WAND：`wand-vega-video-1.0-lite`
- MiniMax：`minimax-video-h3`、`minimax-video-h3-max`、`minimax-video-v2.3`、`minimax-video-v2.3-fast`
- Kling：`kling-video-v3`、`kling-video-v3-turbo`、`kling-video-v3-omni`、`kling-video-o1`、`kling-video-v2.6`、`kling-video-v2.5-turbo`、`kling-video-motion-control-v3.0`、`kling-video-motion-control-v2.6`
- PixVerse：`pixverse-video-v6.0`、`pixverse-video-v5.6`、`pixverse-video-c1`
- Vidu：`vidu-video-q4-preview`、`vidu-video-q3`、`vidu-video-q3-pro`、`vidu-video-q3-turbo`、`vidu-video-q2`、`vidu-video-q2-pro`、`vidu-video-q2-turbo`
- HY / YT：`hy-video-v1.5`、`yt-video-humanactor`

这些公开 ID 均能在腾讯云当前模型目录中找到相应家族或精确 ID；目录同时明确区分当前 canonical ID 与已经下线的旧前缀 ID。[TokenHub 模型列表，2026-10-21](https://cloud.tencent.com/document/product/1823/130051) [旧版本视觉模型迁移指引，2026-08-21](https://cloud.tencent.com/document/product/1823/135600)

### 3.2 关于本地 `vod` 的关键判断

本地 provider 名叫 `vod`，但当前 registry 中只看到通用模型 ID 和通用 chat/responses 类 provider 字段；没有 `CreateAigcVideoTask`、VOD `ModelName`/`ModelVersion` 或媒体资产生命周期配置的本地证据。因此：

1. 不能把“Magpie 中存在 `vod` provider”写成“腾讯云 VOD AIGC 已接通”。
2. 不能把 VOD 的 68 个已选模型写成 68 个视频模型。
3. 若将来需要 VOD AIGC，应做独立 `TencentVodAigcAdapter`，按官方任务 API 与数据结构集成，而不是复用本地通用 provider。[VOD CreateAigcVideoTask，2026-09-07](https://cloud.tencent.com/document/api/266/126239)

本地 DSH/Magpie settings 中也存在一个名为 `vod` 的配置块，但本次只读证据只足以把它识别为聊天模型 relay 配置入口；其中没有 VOD AIGC 任务契约。**同名不是同一服务**：`settings.yaml` 中的 `vod` relay、Magpie provider registry 的 `vod`，以及腾讯云 `CreateAigcVideoTask` 必须作为三个独立对象审计，任何一层的 configured/enabled 都不能传递成另一层的 runtime-verified。

在当前项目和只读检查的 Magpie-Horch 源码树中，也没有检索到 `CreateAigcVideoTask` 或 `VideoGenerationProvider` 的实现；当前项目只有面向脚本生成的 `ScriptProvider`。这是“源码中未找到”的证据，不能反推 Magpie.app 二进制内部一定没有未公开实现。

### 3.3 本次未读取和未验证的内容

- 未显示、复制或验证任何 key、secret、账号、完整 endpoint 或私有 URL。
- 未读取可能包含提示词、媒体或会话数据的调用缓存。
- 未执行 `/v1/models`、视频生成、状态轮询、下载或媒体探测。
- 未确认当前账号的模型 entitlement、余额、并发、实际地域、ZDR、内容策略或账单状态。
- 未验证 Magpie UI 能否以视频模型的专用 endpoint/schema 正确提交任务。模型 ID 出现在通用 provider 列表不代表 Magpie 已实现生视频交互。

## 4. 官方能力矩阵

下表是官方文档能力，不是本地运行结果。`unknown` 表示本次官方资料没有足够证据，不能用营销描述补齐。

| 模型 | T2V / I2V | 一致性/参考 | 首尾帧 | V2V/编辑 | 音频/口型 | 时长、清晰度、画幅 | 异步形态 | SV-Agent 判断 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `minimax-video-h3` | 是 / 是 | 最多可组合参考图、视频、音频；适合主体与风格约束 | 是 | 参考视频输入；是否等同任意视频编辑为 unknown | 原生立体声；独立 lip-sync 未见本指南证明 | 4–15s；768P/2K；含 9:16 等 | `task_id` + polling；官方常见 1–3 分钟 | 参考密集型主力 |
| `minimax-video-h3-max` | 是 / 是 | 不支持 H3 的多模态参考 | 首帧/尾帧 | 否/unknown | 官方模型表未证明独立 lip-sync | 5–15s；480P/768P | 同上 | 草稿主力；参数必须严格校验，防止静默降档 |
| `kling-video-v3` | 是 / 是 | 可使用元素体系保持主体；元素 API 需单独接入与权利控制 | 图生以首帧为主；尾帧能力按具体 endpoint 再确认 | 普通 V3 非通用 V2V 编辑 | 原生音频；音色/口型属于额外接口 | 3–15s；720P/1080P/4K；T2V 支持 9:16 | 异步任务 | 通用叙事和高质量成片主力 |
| `kling-video-v3-turbo` | 是 / 是 | 基础图像约束 | unknown | 否/unknown | 官方指南明确不支持 V3 的 audio/multi-shot 字段 | 3–15s；720P/1080P | 异步任务 | 快速预览 |
| `kling-video-v3-omni` | 是 / 是 | 多模态输入、主体/音色体系 | 依 endpoint | 支持参考视频和基础视频改写 | 原生音频；可组合额外口型/音色接口 | 最高档位依具体 endpoint | 异步任务 | Phase 2 实验；契约面太宽，不进最小 MVP |
| `kling-video-motion-control-v3.0` | 专用动作控制 | 形象参考图 + 动作参考视频；支持引用 1 个主体 | 不适用 | 动作迁移，不是任意 V2V | unknown | 随参考动作 3–30s；720P/1080P | 异步任务 | 动作复刻专项主力 |
| `pixverse-video-v6.0` | 是 / 是 | 最多 7 项参考图；支持多镜头 | 是 | 通用编辑能力 unknown | 文档/计费存在有声档；独立 lip-sync unknown | 1–15s；360P–1080P；含 9:16 等 8 种画幅 | 任务 ID + polling；常见 1–5 分钟 | 通用多镜头实验备选 |
| `pixverse-video-c1` | 是 / 是 | 参考图、结构化分镜 | 是 | 通用编辑能力 unknown | 有声档；独立 lip-sync unknown | 1–15s；360P–1080P；含 9:16 | 同上 | 高速运动和特效专项主力 |
| `vidu-video-q4-preview` | 指南覆盖 I2V / reference | 多图片或具名 subjects，可输出音画 | 本次指南未证明尾帧 | unknown | 音画同出；独立 lip-sync unknown | 具体档位/时长随 endpoint | `task_id` + polling；常见 1–5 分钟 | 参考一致性实验备选 |

能力来源：[MiniMax 生视频调用指南，2026-10-16](https://intl.cloud.tencent.com/zh/document/product/1300/83715)、[Kling 生视频调用指南，2026-10-16](https://intl.cloud.tencent.com/zh/document/product/1300/83714)、[PixVerse 生视频调用指南，2026-10-16](https://intl.cloud.tencent.com/zh/document/product/1300/83713)、[Vidu 生视频调用指南，2026-10-16](https://intl.cloud.tencent.com/zh/document/product/1300/84817)。

### 4.1 旧版本与其他本地候选

| 模型组 | 官方现状 | 处理方式 |
| --- | --- | --- |
| MiniMax v2.3 / v2.3-fast | 当前目录仍列出；fast 更偏快速、低成本 | 只做成本基准和兼容 fallback，不成为新任务默认 |
| Kling v2.5-turbo / v2.6 / O1 | 当前 canonical ID 仍列出；O1 偏多模态参考，v2.6 有音画能力 | 作为受控实验或兼容 route；不要与已下线的 `kl-video-*` 混淆 |
| Vidu q2/q3 canonical IDs | 当前目录仍列出；官方迁移表将旧 `vd-video-*` 映射到这些 canonical ID | 可做人物表情、主体一致性与低成本对照；详细请求 schema 与运行可用性需 smoke 验证 |
| HY Video 1.5 | 当前 canonical ID 是 `hy-video-v1.5`；旧 `hy-video-1.5` 已迁移 | 只保留实验 route；拒绝旧 ID |
| WAND Vega Lite | 当前目录称其适合低成本、多模态参考和批量生产 | 缺少本次已核对的完整调用指南，保持实验状态 |
| YT HumanActor | 单图驱动人物 | 默认禁用；属于高肖像/身份滥用风险 |

`hunyuan-turbos-vision-video-20250728` 一类名称包含 `video` 的模型属于视频理解，不属于生成模型，绝不能进入 generation router。[TokenHub 视频理解，2026-08-27](https://cloud.tencent.com/document/product/1823/136957)

## 5. 成本、时延、地域与商业边界

### 5.1 可用于预算预估的官方参考价

以下为 2026-10-21 官方价格页的参考单价，不是合同报价；实际以任务提交前控制台、套餐和账单为准。[TokenHub 模型价格，2026-10-21](https://cloud.tencent.com/document/product/1823/130055)

| 模型/规格 | 参考价 | 5 秒单次输出粗估，不含重试/额外输入 |
| --- | --- | --- |
| H3 Max 768P | 0.50 元/秒 | 2.50 元 |
| H3 768P 输出 | 0.50 元/秒；参考视频与超量参考图另计 | 2.50 元起 |
| H3 2K 输出 | 0.80 元/秒；参考输入另计 | 4.00 元起 |
| Kling V3 720P 无声 / 有声 | 0.60 / 0.90 元/秒 | 3.00 / 4.50 元 |
| Kling V3 1080P 无声 / 有声 | 0.80 / 1.20 元/秒 | 4.00 / 6.00 元 |
| Kling Motion Control V3 720P / 1080P | 0.90 / 1.20 元/秒 | 4.50 / 6.00 元 |
| PixVerse C1 720P 无声 / 有声 | 0.2933 / 0.38129 元/秒 | 约 1.47 / 1.91 元 |

H3 官方给出的常见任务时间是 1–3 分钟；PixVerse 与 Vidu 常见 1–5 分钟。这只是供应商文档范围，不是 SV-Agent 的 SLO，真实 P50/P95 必须由 smoke 和小流量运行得到。[MiniMax 指南](https://intl.cloud.tencent.com/zh/document/product/1300/83715) [PixVerse 指南](https://intl.cloud.tencent.com/zh/document/product/1300/83713) [Vidu 指南](https://intl.cloud.tencent.com/zh/document/product/1300/84817)

### 5.2 地域与数据处理

TokenHub 按地域提供接入，不支持跨地域、跨站点直接调用；具体部署必须与已开通地域一致。[TokenHub API 使用说明](https://cloud.tencent.com/document/product/1823/130078) 本地实际配置地域不写入本报告，部署 gate 需要在 secret-bearing 环境内核对。

官方隐私与数据处理文档说明，服务会处理客户输入、生成内容和相关元数据；未启用符合条件的 ZDR 时，部分数据通常可能保留最多 30 天，并要求调用方取得处理个人数据所需的合法依据和同意。[TokenHub 隐私政策，2026-08-13](https://intl.cloud.tencent.com/zh/document/product/1300/78952) [数据处理和安全协议，2026-09-11](https://intl.cloud.tencent.com/zh/document/product/1300/78953)

因此，含婴幼儿、家长、真实人物、声音或家庭场景的参考素材，必须先完成：来源证明、监护人/肖像/声音授权、地域与保留策略确认、可撤回机制和审计记录。技术可生成不等于有权生成或发布。

### 5.3 商业使用与安全

- 模型指南未单独给出可覆盖所有素材与输出的商业权利保证。商业使用、知识产权、赔偿、品牌和广告合规在本次证据中为 `unknown`，需要法务结合 [TokenHub 服务条款](https://intl.cloud.tencent.com/zh/document/product/1300/78985) 与实际合同复核。
- 供应商内容审核通过不等于 Momcozy 品牌安全、事实准确、Media Integrity 或发布批准。
- 未成年人、真人、声音克隆、口型和 HumanActor 必须比普通产品镜头使用更高等级审批；默认拒绝未证明权利的第三方人像素材。

## 6. 按任务路由，而不是按“最强模型”路由

| `intent` | 首选 route | 备选 route | 不允许自动 fallback 的条件 |
| --- | --- | --- | --- |
| `hero.controlled_product` | H3 2K：参考素材或首尾帧是硬约束；Kling V3：多镜头/原生音频是硬约束 | 不跨这两类硬约束自动互换 | 产品外观、关键帧、多镜头、音频任一验收语义改变 |
| `variants.low_cost` | H3 Max，768P，5–6s | MiniMax v2.3-fast 或 PixVerse C1 的低清档，需先通过等价性基准 | 预算、关键帧、画幅或声音要求不能保持 |
| `draft.first_last` | H3 Max，768P，5–6s | MiniMax v2.3-fast（只有参数能力等价时） | 尾帧、画幅或成本上限不能保持 |
| `replicate.reference_consistency` | H3，768P/2K，4–15s | Vidu Q4 或 Vidu q3，仅在各自 smoke 通过后 | 参考视频/音频、主体数量、权利策略发生变化 |
| `multimodal.2k` | H3 2K | 无自动备选 | 2K 或多模态参考是硬约束 |
| `story.multi_shot_audio` | Kling V3 | Kling V3 Turbo 仅在用户明确接受“无原生音频/无多镜头”后 | 音频、多镜头或 4K 是任务硬约束 |
| `motion.transfer` | Kling Motion Control V3 | 无自动备选 | 普通 I2V 不能等价替代动作迁移 |
| `dynamic.high_motion` | PixVerse C1 | H3 或 Kling V3，需人工确认语义变化 | 特效/动作 adherence 是验收条件 |
| `story.reference_video_edit` | Kling V3 Omni（Phase 2） | 无自动备选 | 视频改写不是“参考视频生成”的同义词 |
| `social.vertical_9x16` | 在上述能力 route 中锁定 9:16 | 同等能力模型 | 不得为了可用性偷偷改成 16:9 |
| `portrait.humanactor` | 禁用 | 无 | 未完成身份、肖像、年龄与同意门 |

路由器只接受结构化 `capability_intent`，不能直接接受 UI 传来的任意 provider/model。产品层先表达“要完成什么”，policy 层再根据 capability snapshot、预算、地域、权利和 runtime health 选择精确版本。

## 7. Provider Port 与 adapter 契约

### 7.1 为什么必须是新 port

当前 `ScriptProvider` 处理文本脚本与结构化输出；视频生成是长任务、计费任务、媒体任务，具有提交、轮询、过期下载、文件探测、资产权利、内容审核与费用对账等不同失败面。复用文本 provider 会把这些差异藏在字符串响应里，破坏当前 PostgreSQL 事实源和 append-only 执行边界。

现有项目已经有可复用的 Job 可靠执行基线：`(job_type, idempotency_key)` 唯一、同 key 不同 input digest 冲突、Job/初始事件/outbox intent 同事务写入、worker 使用 attempt fencing、每次状态变化追加 `JobEvent`。视频任务应扩展这套模式，而不是另建一个只存在于 Celery/Redis 的状态机；但外部视频任务还必须增加当前基线尚未实现的 provider idempotency reconciliation 与不可变 `ProviderRun` cost/provenance ledger。详见 [system overview](../architecture/system-overview.md)。

建议新增逻辑边界，而不是先新增供应商耦合：

```text
Application Use Case
  -> VideoGenerationPolicy (rights, moderation, budget, capability route)
  -> VideoGenerationProvider port
       -> TokenHubVideoAdapter       [MVP]
       -> TencentVodAigcAdapter      [Phase 2, separate approval]
       -> FakeVideoProvider          [tests]
  -> ProviderRun / Attempt ledger    [PostgreSQL, append-only]
  -> Controlled media storage
  -> Media Integrity + HumanApproval
```

### 7.2 建议契约

`VideoCapabilitySnapshot`

- `provider`, `model_id`, `observed_at`, `source`, `status`
- `t2v`, `i2v`, `first_frame`, `last_frame`, `reference_images`, `reference_video`, `reference_audio`
- `motion_control`, `video_edit`, `native_audio`, `lip_sync`
- `duration_range`, `resolutions`, `aspect_ratios`, `max_reference_assets`
- `region`, `polling_profile`, `output_url_ttl`, `price_snapshot_ref`

`VideoGenerationRequest`

- 内部 `task_id/run_id`、`ReplicationContract`/Storyboard/FactMap 版本引用
- `capability_intent`，而非任意 model string
- prompt/storyboard digest；输入资产只传受控对象引用与 digest
- 每个输入的权利类别、主体类型、年龄/真人风险、同意证据引用
- `duration`, `resolution`, `aspect_ratio`, `audio_policy`
- `budget_ceiling`, `max_attempts`, `idempotency_key`, `moderation_policy_version`

`ProviderSubmission`

- `provider`, `model_id`, `capability_snapshot_id`, `provider_task_ref`
- `submitted_at`, `attempt_no`, `quoted_max_cost`, `request_digest`
- provider task reference 必须作为私密运行字段保存，不进入公开日志或文档

`ProviderStatus`

- 统一为 `queued | running | succeeded | failed | cancelled | unknown`
- 保留原始 provider status/error 的受控引用，不暴露密钥或签名 URL

`VideoArtifactReceipt`

- 内部对象存储引用、媒体 SHA-256、容器/编码、时长、分辨率、画幅、音轨探测结果
- provider/model/capability snapshot、实际费用、重试次数、生成时间
- 输入 provenance、审核结果、Media Integrity 结果、人工接受状态
- 技术成功、内容验收、商业批准、发布批准必须是不同字段

### 7.3 稳定错误码

- `VIDEO_PROVIDER_UNAVAILABLE`
- `VIDEO_PROVIDER_RATE_LIMITED`
- `VIDEO_INPUT_UNSUPPORTED`
- `VIDEO_CONTENT_REJECTED`
- `VIDEO_RIGHTS_REQUIRED`
- `VIDEO_BUDGET_EXCEEDED`
- `VIDEO_TASK_UNKNOWN`
- `VIDEO_OUTPUT_EXPIRED`
- `VIDEO_OUTPUT_INVALID`

## 8. 运行治理

### 8.1 Capability discovery

1. 部署启动或受控刷新时，通过 provider 官方模型列表读取当前 online 状态。
2. 与版本化的 allowlist 和 adapter capability map 求交集；provider 返回的未知模型不能自动进入路由。
3. 保存只含公开 ID/能力/时间的 snapshot，不保存 key、endpoint 或账号。
4. 每个生成任务钉住 snapshot；模型目录变化不能改变进行中的任务。
5. 发现下线、字段变化或价格越级时自动关闭对应 route，进入人工复核。

TokenHub 当前可观测视频请求数、视频秒数、成功率和任务时长等指标，但 SV-Agent 仍需保存自己可审计的请求/任务/文件事实。[TokenHub 模型监控](https://cloud.tencent.com/document/product/1823/130089)

### 8.2 异步与幂等

- `submit` 与 `poll` 分离；worker 采用有上限的指数退避与 jitter，并遵守各模型建议轮询间隔。
- 提交成功但响应丢失时，先按 idempotency/request digest 与现有 attempt 对账；不能直接再提交一个付费任务。
- Redis/Celery 只负责调度；PostgreSQL 的 append-only `ProviderRun`/`Attempt` 才是事实源。
- provider 返回临时 URL 后立即下载到受控存储，执行 hash 和 `ffprobe` 类探测；不持久化公开或签名 URL。H3 与 PixVerse 官方均提示结果 URL 有限期，最长 12 小时量级。[MiniMax 指南](https://intl.cloud.tencent.com/zh/document/product/1300/83715) [PixVerse 指南](https://intl.cloud.tencent.com/zh/document/product/1300/83713)

### 8.3 Budget policy

- 提交前形成 price snapshot 与最坏费用估算；超过单次上限时拒绝，而不是自动降画质。
- 限制单任务 variants、总时长、自动重试和日预算；不得把 provider retry 当免费操作。
- fallback 只有在模型、参数、成本等级和语义都属于预先批准的 equivalence class 时才自动执行。
- 记录实际 `total_tokens`/费用回执并与内部估算对账；价格页只是预算输入，不能替代账单。

### 8.4 Provenance、moderation 与人审

- 输出必须绑定 `ReplicationContract`、事实映射、镜头脚本、prompt 版本、输入 digest、模型版本和 provider attempt。
- 生成前检查素材来源、权利、真人/儿童/声音风险和 prompt；生成后检查媒体完整性、人物/产品变形、品牌事实、字幕/包装文字和不当内容。
- 对 baby/family 内容启用增强 policy：不使用来历不明的儿童人像，不做未经授权的脸/声音克隆，不把供应商“成功”状态视作发布许可。
- 现有 [SV-Agent Native Agent 规格](../product/sv-agent-native-agent-spec.md) 和 [实施 tickets](../product/sv-agent-implementation-tickets.md) 明确未授权视频生成/发布；本方案必须通过新的范围、provider/privacy/billing 批准后才能实施。

## 9. TokenHub 与 VOD 的分工

| 维度 | TokenHub 专用视频 adapter | 腾讯云 VOD AIGC adapter |
| --- | --- | --- |
| MVP 适配 | 更合适：本地已有 provider 配置和完整视频模型目录，官方有模型专用异步 API | 暂不进入 MVP |
| 模型路由 | 直接按公开 model ID 与模型专用 endpoint | 按 `ModelName`、`ModelVersion` 与 VOD SceneType 数据结构 |
| 媒体生命周期 | 输出通常是短期 URL，SV-Agent 必须自行转存和探测 | 与 VOD 媒体资产、临时/永久输出、后续处理更紧密 |
| 复杂能力 | 多家模型统一入口，但不同家族 schema 仍需 adapter 内显式映射 | 官方接口覆盖 Kling、Vidu、Hailuo、PixVerse 等，并包含更丰富的 VOD 数据结构 |
| 风险 | Magpie 通用 provider 不代表视频 schema 已适配；需独立代码和付费验证 | 新云产品权限、SubApp、媒体留存、回调、安全与计费面更大 |
| 决策 | **Phase 1** | **Phase 2，单独 ADR 与批准门** |

VOD 官方 `CreateAigcVideoTask` 是后付费任务，默认并发为 1，并公开列出 Hailuo、Kling、Vidu、Hunyuan、Mingmou、GV、OS、PixVerse 等家族与版本；这些事实只能证明 VOD 产品能力，不能证明本机 Magpie `vod` provider 已接通。[VOD CreateAigcVideoTask](https://cloud.tencent.com/document/api/266/126239) [VOD 数据结构](https://cloud.tencent.com/document/product/266/31773)

VOD 官方接口当前公开的版本面如下；它比 MVP 需要的范围大得多，且仍然全部属于“官方可选项、非本地运行证明”：

| VOD `ModelName` | 官方公开版本示例 | 本方案处理 |
| --- | --- | --- |
| Hailuo | 02、2.3、2.3-fast、H3、H3-Regen、H3-Max | 若 Phase 2 采用，先与 TokenHub MiniMax/Hailuo 命名和参数逐项映射，禁止仅按名字猜测等价 |
| Kling | 1.6、2.0、2.1、2.5、2.6、O1、3.0、3.0-Omni、3.0-turbo、scene | Phase 2 只开放已通过 TokenHub 质量基准且 VOD schema 已验证的版本 |
| Vidu | q2/q3 系列、scene、avatar、lip-sync 等 | avatar/lip-sync 保持默认禁用，需额外身份与声音权利门 |
| PixVerse | v5.6、v6、c1 | 可作为 Phase 2 媒体托管路线对照，不自动替代 TokenHub route |
| Hunyuan / Mingmou / GV / OS | 1.5/3D、1.0、3.1 系列、2.0 等 | MVP 不选；能力、价格、地区和安全全部重新评估后再增加 |

## 10. MVP 验收矩阵

### 10.1 付费 smoke test 前置门

任何 smoke call 都会产生外部状态和费用，必须另行明确批准。批准前至少确认：

- 供应商、地域、账号、预算、模型 entitlement 与数据保留策略；
- 测试素材不含私密客户资产，或已取得可审计授权；
- 输入和输出落入受控存储；日志不会记录 key、签名 URL 或原始私密素材；
- 设定每模型 1 次、5–6 秒、720P/768P 的硬上限，不允许自动重试；
- 失败也保留稳定 failure code、任务引用和费用事实。

### 10.2 最小 smoke matrix

| Route | 最小样本 | 必须验证 |
| --- | --- | --- |
| H3 Max 首尾帧 | 1 个 9:16、5s、768P | 首尾帧遵循、无静默分辨率降级、任务轮询、实际费用、文件可读 |
| H3 多参考 | 1 组已授权的产品/人物合成 fixture、5s、768P | 参考素材数量、主体一致性、音频策略、费用与临时 URL 转存 |
| Kling V3 多镜头 | 1 个 9:16、5s、720P 无声 | 多镜头结构、画幅、费用、媒体探测 |
| Kling V3 原生音频 | 同一脚本 1 次有声 | 音轨存在、同步、内容安全、增量费用 |
| Motion Control V3 | synthetic character + synthetic motion、3–5s | 动作 adherence、单主体约束、720P、不可等价 fallback |
| PixVerse C1 动态 | 1 个高速动作/特效 fixture、5s、720P | 动态质量、首尾帧/参考语义、耗时与成本 |

一次 API `succeeded` 不是通过。每个样本还要保存并核验：真实媒体文件、digest、`ffprobe` 结果、实际任务时长、实际费用、审核结果和人工评分。

### 10.3 质量评测维度

每个 route 使用相同输入集做至少三轮不同 seed/attempt 的离线评测，避免单样本幸运值：

- 主体/产品一致性
- 动作与运镜 adherence
- 时间连续性与物理合理性
- 镜头语法与爆款结构保真度
- 产品文字、包装与事实准确性
- 音画同步与人声可用性
- 不当内容、儿童/家庭安全与品牌风险
- 端到端 P50/P95、成功率、可恢复失败率、实际元/可接受镜头

“元/生成秒”不能单独决定胜负；最终主指标应是“元/通过人工与 Media Integrity 双门的可用镜头”。

## 11. 实施 tickets 与批准门

| Ticket | 交付物 | 完成标准 | 批准门 |
| --- | --- | --- | --- |
| SV-VID-000 Scope/ADR | 明确视频生成、存储、账单、隐私、发布仍分离；选 TokenHub 为 Phase 1 | ADR 被批准；不改现有只读范围含义 | 产品 + 架构 + 隐私 + 财务 |
| SV-VID-001 Safe capability inventory | secret-safe discovery、版本化 allowlist/capability snapshot | 能识别 current/unknown/deprecated；日志无秘密 | 安全审查 |
| SV-VID-002 Provider port | 上述 request/status/receipt/error 契约 + fake adapter | contract tests 覆盖异步状态、错误和成本拒绝 | 架构审查 |
| SV-VID-003 ProviderRun ledger | PostgreSQL append-only run/attempt、idempotency、outbox/recovery | 崩溃恢复不重复付费；Redis 清空后事实仍在 | 数据模型审查 |
| SV-VID-004 TokenHub adapters | H3/H3 Max、Kling V3/Turbo、Motion V3、PixVerse C1 的显式 schema adapters | 每家族独立 contract tests；不使用万能 JSON passthrough | Provider/安全审查 |
| SV-VID-005 Controlled media intake | rights metadata、受控 URL/Base64、下载/转存/hash/probe | 临时 URL 不落公开日志；过期/损坏有稳定错误码 | 隐私/安全审查 |
| SV-VID-006 Budget & moderation | quote gate、单次/日预算、pre/post moderation、child/portrait policy | 超预算/无权利素材在提交前被拒绝 | 财务 + 品牌 + 法务 |
| SV-VID-007 Paid smoke gate | 上述最小矩阵及真实 receipt | 每 route 有成功或稳定 failure code；无自动重试 | **另行付费调用授权** |
| SV-VID-008 Offline routing eval | 固定 fixtures、盲评、成本/时延/质量榜 | 形成 main/fallback/disabled 的数据化阈值 | 产品验收 |
| SV-VID-009 Limited UI | capability intent、预算预览、审批、进度和产物验收 | 用户看见模型选择原因、费用上限与非发布状态 | UX + 产品批准 |
| SV-VID-100 VOD Phase 2 | `TencentVodAigcAdapter`、媒体生命周期与事件处理 ADR | 与 Magpie `vod` provider 明确隔离；独立 smoke | 新 provider/privacy/billing 批准 |

## 12. 当前未知项与停止线

以下项目在真实 smoke 或合同审查前必须保持 `unknown`，不能在产品页写成已支持：

- 当前 key 是否有效、账号是否有视频模型 entitlement、余额和并发额度；
- Magpie 通用 provider 是否实现了每个视频家族的专用 API schema；
- 每个模型的真实 P50/P95、审核失败率、结果 URL 行为和账单一致性；
- webhook 支持。本次核对的 TokenHub 模型指南只证明 polling；没有证据时不设计为 webhook-first；
- 所有参考素材和输出的商业使用权、第三方权利与赔偿范围；
- baby/family 真实素材的地域、保留、年龄、监护人同意和撤回流程；
- VOD direct 的账号权限、SubApp、媒体留存、事件回调和生产费用；
- lip-sync、声音克隆、HumanActor 的产品许可与滥用防护。

命中任一停止线时，不得“先试一下”：缺权利证明、预算未批准、地域/保留未知、模型 capability 不匹配、provider 状态 unknown、幂等无法保证、结果无法落入受控存储，均应在提交前失败。

## 13. 决策建议

1. 先批准或否决 SV-VID-000；在此之前，本文件只是研究方案，不改变当前 SV-Agent 产品范围。
2. 若批准，先实现 fake adapter、capability snapshot、账本和预算门，再写真实 provider client。
3. TokenHub MVP 只开放六条明确 route：H3、H3 Max、Kling V3、Kling V3 Turbo、Motion V3、PixVerse C1。
4. VOD、Kling Omni、Vidu Q4、WAND Vega、HumanActor 均不在最小 MVP 自动路由中。
5. 最终模型层级以 SV-VID-007/008 的真实媒体、成本和人工盲评结果更新；本次官方规格比较不能替代运行评测。

