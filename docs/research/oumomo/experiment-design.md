# Oumomo 积分实验、逆向复盘与知识沉淀系统设计

> **Status:** Historical clean-room research design. Current evidence and limitations are routed through [evidence-index.md](evidence-index.md).

状态：用户已确认
日期：2026-08-11
积分硬上限：980
执行方式：正常产品 UI、可见任务状态、积分账本和用户自有产物的 clean-room 黑盒实验

## 1. 目标

本轮不是为了耗尽积分，而是用每一笔积分换取可区分、可复验、可进入工程实现的结论。最终交付必须同时覆盖：

1. 当前 P0 每个实现节点的代码级复盘、价值、壁垒、复杂度和缺口。
2. Oumomo 当前可见能力的完整图谱、状态机、输入输出合同和计费边界。
3. 对爆款脚本、爆款复刻、链接生视频、模板、数字人、视频/图片模型、去重和质量检测的对照实验。
4. 输入夹具、配置快照、任务状态、积分变化、生成产物和离线媒体分析的证据链。
5. 可直接执行的 SOP、经验规则和一个经过实际失败与前向验证的 Skill。
6. 基于实测证据的 P1/P2 产品路线，不以营销声明或模型猜测代替事实。

成功不是“生成了很多内容”，而是：

```text
假设
→ 冻结输入与配置
→ 只改变一个变量
→ 记录报价并单次提交
→ 恢复同一任务到终态
→ 对账积分
→ 保存并分析自己的产物
→ 区分事实、推断和未知
→ 得到可实现、可测试的工程合同
```

## 2. 已知基线

### 2.1 当前工程

当前工程已经实现：

- 手动商品与受限 Schema.org Product URL 导入。
- 不可变 ProductSnapshot 和证据型 ProductFact 台账。
- confirmed/locked 事实门禁。
- 15/30/45 秒、七种 CreativePattern 的异步脚本生成。
- Job 幂等、attempt fencing、terminal replay、TOCTOU 复检和 Redis 非事实源。
- 强类型脚本、事实/时间轴/禁用声明校验。
- append-only ScriptVersion、diff、JSON/Markdown 导出。
- React Web、Docker Compose、CI、迁移和自动化测试。

最高价值节点是事实证据链、异步任务可靠性和不可变版本；主要缺口是：

- Web 无法新增细粒度事实、上传商品图或选择本次生成使用的事实。
- 版本功能不是完整脚本编辑器，时间线、旁白、画面和拍摄清单不可编辑。
- 缺少项目、素材、任务、脚本和待办的统一工作区。
- 后端缺 transactional outbox、毒 DataError 隔离和 ImportAttempt 独立状态。
- CreativePattern 只验证 phase 顺序，尚未验证 shot role 与 phase timeline。
- exact-text 事实绑定安全但限制营销表达，需要建立“事实不变、表达可变”的受控合同。
- 无 auth、tenant、rate limit 和 audit event，不能直接作为公网 SaaS 边界。

### 2.2 既有 Oumomo 实验

既有证据账本已经完成：

- 2 次爆款脚本生成，共扣 20 分；验证 30 秒与 15 秒会触发结构重规划。
- 1 次爆款复刻最低档生成，扣 30 分；产物为 15.104 秒、496×864 MP4。
- 1 次链接生视频提交探测；因 HTML 被客户端按 JSON 解析而未创建业务任务、未扣分。
- 榜单地区、品类、GMV、AI 生成过滤的零积分探测。

已知高价值缺陷：

- 脚本第二次生成覆盖第一次结果，但重复扣分，缺少版本历史。
- 爆款复刻在参考视频不可播放时仍允许付费。
- 复刻提示词编译器会自动加入无证据的能量、口味和用量声明。
- 链接生视频曾存在提交响应合同错误和不可恢复的 disabled 状态。
- 榜单 GMV 筛选结果与未筛选卡片数值发生矛盾。

本轮不得为重复这些结论而消耗积分。

## 3. 范围分解

这是一个研究系统，不是一次性脚本。按顺序拆成四个独立阶段：

### Phase A：零积分能力与状态盘点

盘点所有目标能力的表单、必填项、默认值、错误态、配置选项、报价、任务入口、项目恢复和输出入口。任何功能未走到明确报价前，不进入付费实验。

### Phase B：450 分核心因果实验

- 爆款脚本：12 次，预算 120。
- 爆款复刻：6 次，预算 180。
- 链接生视频：最多 5 次，预算 150。

### Phase C：530 分条件实验

- 模板真实效应：最高 120。
- 数字人一致性：最高 150。
- 视频模型路由：最高 180。
- 图片模型差异：最高 60。
- 视频质量评分校准：最高 20。

Phase C 的每个模块只有在报价、输入、模型或模板身份、最低有效重复次数都明确时才获得预算。未使用积分保留，不转移给无有效设计的重复生成。

### Phase D：证据分析与知识固化

对自己的产物执行元数据、帧、ASR、OCR、镜头、事实声明、结构相似度和媒体质量分析；据此更新复盘报告、SOP、经验规则和 Skill。

## 4. 证据等级

| 标记 | 定义 | 允许结论 |
|---|---|---|
| F | UI、任务、余额、产物或离线分析直接观察 | 可写为已证实行为 |
| I-H | 至少两类独立事实支持 | 可写为高置信工程推断 |
| I-M | 单一稳定模式支持 | 只能写为候选解释 |
| U | 不可观察、证据不足或冲突 | 必须保持未知 |
| Vendor claim | 网站营销或帮助说明 | 标注为官方宣称、未独立验证 |

不能从黑盒现象确认私有提示词、训练数据、具体内部模型、模型温度、向量数据库或源码实现。

## 5. 统一实验合同

每次实验必须记录：

```text
experiment_id
hypothesis_id
feature
control_experiment_id
replicate_index
observed_at
route_without_sensitive_query
input_fixture_ids[]
input_sha256[]
config_canonical_json
config_digest
single_changed_variable
visible_model_or_mode
quote_before_submit
credit_before
credit_after
ledger_delta
submit_count
job_id_hash
state_sequence[]
stage_timestamps[]
terminal_state
visible_error_signature
artifact_sha256
mime
bytes
width
height
fps
duration
codec
audio_present
script_structure
fact_claims[]
supported_fact_ids[]
unsupported_claims[]
asr_ref
ocr_ref
shot_boundary_ref
frame_grid_ref
quality_scores
pairwise_similarity
verdict
confidence
redactions
notes
```

任务 ID 只保存不可逆哈希。不得保存 Cookie、Token、请求头、手机号、账号标识、签名媒体 URL、完整私有 URL、原始完整网页或模型私有推理。

## 6. 公共执行门禁

### Gate 0：账户与账本

- 记录余额 980、现有项目数、任务数和已有产物指纹。
- 连续刷新确认余额与任务状态稳定。
- 任何历史扣费未对清时暂停新任务。

### Gate 1：免费探路

- 空输入、错误输入、站内示例和合法公开输入分别走到提交前。
- 记录错误、必填、默认配置、模式、时长、清晰度、数量和报价。
- 任何错误输入创建任务或扣分即停止该模块。

### Gate 2：夹具冻结

- 商品使用无真实品牌、无价格、无功效声明的合成 SKU。
- 使用一张白底主图和三张多角度图两套夹具。
- 参考视频只使用站内授权或公开可正常播放、允许分析的内容。
- 每个夹具计算 SHA-256，实验期间不改写。

### Gate 3：报价与单次提交

- 提交前记录配置、报价、余额和预期扣费。
- 只点击一次；页面无反馈时先查任务队列、项目和余额。
- 禁止通过重复点击解决未知状态。

### Gate 4：任务终态与对账

- 记录状态序列、阶段时间和最终状态。
- 刷新后必须恢复同一任务。
- 成功必须存在可播放、可访问、可分析的产物。
- 失败必须对清积分、退款和任务状态后才能继续。

### Gate 5：离线验收

- 只分析自己的产物。
- 保存媒体哈希、元数据、抽帧、ASR、OCR 和镜头边界。
- 输出与商品事实、参考结构和配置逐项对照。

## 7. 核心实验设计

### 7.1 爆款脚本：12 次，120 分

冻结同一商品、事实、参考集合和基础配置：

1. 完全相同基线生成 3 次，测随机性、版本覆盖和重复扣费。
2. 15 秒和 45 秒各 1 次，测结构压缩与扩展。
3. 选择两个结构差异最大的 script type，各 1 次。
4. 改变语言 1 次。
5. 改变目标受众 1 次。
6. 增加优惠信息 1 次。
7. 只改变卖点顺序 1 次。
8. 删除一个商品事实 1 次，检查输出是否继续使用该事实。

主要指标：商品事实精确率、无证据声明数、phase/shot 序列、Hook 时间、时长误差、字段完整率、重复输出方差、编辑持久化和版本独立性。

### 7.2 爆款复刻：6 次，180 分

前置条件：参考视频可稳定播放并能提取 Hook、镜头、节奏和 CTA。

1. 同参考、同商品图、空提示词基线重复 3 次。
2. 商品图从 1 张变成 3 个角度，1 次。
3. 空提示词改为事实约束提示词，1 次。
4. 只更换参考视频，1 次。

主要指标：参考 Hook 偏差、镜头角色序列、CTA、商品包装/颜色/文字跨镜头一致性、ASR/OCR、无证据卖点、生成耗时、积分和重复输出差异。

没有可播放参考视频时不得扣分；不能把“生成成功”写成“结构复刻成功”。

### 7.3 链接生视频：最多 5 次，150 分

1. 先用站内示例或合成手工商品走到明确报价。
2. 第一条最低档基线作为旧提交故障回归测试。
3. 若成功，再提交 2 次完全相同配置，使相同配置总样本数达到 3。
4. 只改变受众 1 次。
5. 只改变图片数量或语言 1 次。

若第一条再次出现 HTML/JSON 解析错误、无 job、永久 disabled 或扣费不明，立即停止本模块，剩余预算不使用。

## 8. 条件实验设计

### 8.1 模板效应

同商品、同模型、同参数：模板 A 两次、模板 B 两次。只有模板间结构差异显著大于同模板随机差异，才能证明模板是有效控制变量；否则只能判定为 UI 包装。

### 8.2 数字人

只使用站内授权数字人，不上传真人面部或声音。保持脚本、声音、背景和模型固定，Avatar A 三次、Avatar B 两次。检查身份、口型、手部与商品接触、视线、面部漂移、声音和跨镜头一致性。

### 8.3 视频模型路由

相同 prompt、参考图、比例、时长和分辨率，每个可见模型至少重复 2 次。模型名、报价、时延和产物参数必须可观察。若页面只显示 Mini/快速/高质，只能记录为质量模式，不能推断具体供应商模型。

### 8.4 图片模型

同 prompt、商品图、比例和输出数量，每个模型至少重复 2 次。比较商品文字、颜色、构图、场景遵循、人物/手部和多图一致性。

### 8.5 视频质量评分

从自己的成片制作原片、强压缩、错比例、静音、音画错位、关键画面受损六类样本。若评分免费，每类重复 3 次；若收费，预算必须能容纳至少两个组、每组两次。验证重复稳定性、严重度单调性、子分敏感性和修改建议可操作性。

### 8.6 去重

优先复用脚本、复刻和链接视频的三次完全重复，不额外制造付费任务。计算视频感知相似度、镜头序列、ASR/OCR n-gram、音频指纹和事实保持率。没有显式去重开关或前后对照时，只能报告输出多样性，不能断言存在去重算法。

### 8.7 发布

只做 dry-run：项目→发布入口→字段→隐私→排期→预览。在 OAuth、账号绑定和最终发布动作前停止。任何真实发布需要新的明确授权。

## 9. 全局停止条件

1. 已净扣积分加当前报价会超过 980。
2. 实时报价变化或超过模块预算信封。
3. 一次点击后响应未知，且任务/积分无法对清。
4. 付费失败但退款或任务状态未确认。
5. 出现 403、429、验证码或安全拦截。
6. 页面要求记录凭证、Cookie、Token 或个人信息。
7. 复刻参考视频不可播放。
8. 链接生视频再次出现旧提交契约错误。
9. 页面显示成功但产物不可播放或严重不符。
10. 同一基线 3 次已经稳定，不继续重复。
11. 同一结论 3 次仍冲突，停止局部实验并审查状态、缓存与失败边界。
12. 出现严重无证据功效、认证、价格或安全声明，暂停该能力的后续生成。
13. 到达 OAuth、账号绑定或最终发布动作。

## 10. 产物结构

```text
outputs/oumomo-reverse-engineering/
  experiments/
    experiment-manifest.jsonl
    credit-ledger.csv
    job-state-events.jsonl
    config-snapshots/
  fixtures/
    fixture-manifest.json
    product-facts/
    product-images/
    reference-videos/
    scoring-degradations/
  artifacts/
    media/
    frame-grids/
    asr/
    ocr/
    shot-boundaries/
    hashes.csv
    scorecards.csv
  reports/
    project-node-review.md
    capability-map.md
    experiment-findings.md
    p1-p2-roadmap.md
  sops/
  skills/
```

签名 URL、完整任务 ID、账号信息和第三方受保护媒体不进入上述目录。

## 11. SOP 交付

至少形成以下 SOP：

1. `paid-job-safe-submit`：报价、余额、单击、任务恢复和禁止重复提交。
2. `credit-reconciliation`：报价、任务、终态、净扣费和退款对账。
3. `single-variable-experiment`：冻结配置、唯一变量、重复次数和结论等级。
4. `product-fact-claim-audit`：商品事实到脚本、字幕、口播和画面的绑定。
5. `ai-media-qc`：元数据、抽帧、ASR、OCR、镜头和商品一致性。
6. `template-effect-benchmark`：模板内方差与模板间效应。
7. `model-router-benchmark`：模型、价格、时延、质量和稳定性。
8. `quality-score-calibration`：受控降质、重复评分和子分敏感性。
9. `publish-dry-run`：只验证字段和状态，不授权、不发布。

## 12. Skill 设计与验证

最终只创建一个主 Skill：`oumomo-clean-room-experiment-runner`。详细功能知识放入 references，确定性账本校验放入 scripts；不为单次观察创建多个碎片 Skill。

Skill 必须遵循 RED-GREEN-REFACTOR：

1. 在没有 Skill 的新上下文中运行基线场景，记录遗漏的报价、对照、账务或停止条件。
2. 写最小 SKILL.md，只修复真实基线失败。
3. 使用相同和变体场景前向验证。
4. 修复新发现的歧义并重新验证。
5. 运行结构验证脚本，确认 frontmatter、命名和引用有效。

Skill 不保存 Oumomo 私有接口、凭证或推测实现；它教会未来 Agent 安全地进行积分任务、单变量实验、证据分层和产物验收。

## 13. 当前项目后续路线

实验结论进入现有工程时按以下顺序：

### P1：事实驱动脚本工作台

- 新增/拆分 ProductFact、图片和快照历史。
- 用户显式选择本次生成使用的事实。
- 完整结构化脚本编辑和 append-only 派生版本。
- 项目、商品、素材、任务和脚本统一工作区。
- 有证据来源的模板库和表现力/相似度评分。

### P1.5：生产可靠性

- transactional outbox 与 publisher/reconciler。
- ImportAttempt 独立状态和永久/瞬态错误分类。
- phase timeline、shot role、版本化 speaking rate。
- auth、tenant、rate limit 和 audit event。

### P2：预览优先的视频流水线

```text
ScriptVersion
→ Storyboard JSON
→ 低成本预览
→ 人工编辑/批准
→ 积分预留
→ Render Job
→ Media QC
→ 接受、局部重试或退款
→ 导出
```

在脚本事实、模板效应和 preview 质量没有稳定前，不直接建设全量视频模型平台。

## 14. 验收标准

1. 所有付费实验有唯一假设、控制组、报价、任务、积分和产物证据。
2. 总净扣积分不超过 980，且不存在未知重复扣费。
3. 失败任务在继续前完成账务与终态对账。
4. 核心模块达到计划重复数，或有明确停止证据。
5. 每个能力结论标注 F、I-H、I-M、U 或 Vendor claim。
6. 自有媒体产物具备哈希、元数据、帧、ASR/OCR 或适用的替代证据。
7. 项目节点复盘覆盖输入、领域、API、异步任务、Provider、校验、持久化、安全、Web、迁移和测试。
8. 形成 9 份可执行 SOP，并以实际事件记录验证步骤完整性。
9. 主 Skill 先有无 Skill 的失败基线，再通过前向场景和结构校验。
10. P1/P2 路线中的每一项都能追溯到代码缺口或本轮实验事实。
11. 不记录敏感身份、认证信息、私有推理或未经授权的第三方媒体。
12. 不执行真实 TikTok 发布、OAuth 或账号绑定。
