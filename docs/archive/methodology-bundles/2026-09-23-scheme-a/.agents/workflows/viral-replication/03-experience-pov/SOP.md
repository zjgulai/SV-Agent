# Experience POV Replication SOP

## Trigger

当复刻价值主要来自第一视角、ASMR、感官触点、动作连续性、日常场景或情绪缓解时使用。

## Preconditions

- POV、感官和动作连续性可以从商品功效声明中独立出来。
- 商品 identity 的参考素材、组件、颜色和场景限制明确。
- 声音、字幕、人物和道具的权利状态可说明。

## Steps

1. 建立 ReferenceBundle，保留声音、画面、字幕和来源 scope。
   - 完成标准：没有把可听到的宣传语默认视为事实。
2. 用 `viral-content-decomposition` 建立 POV/sensory/continuity map。
   - 完成标准：每个体验 cue 有时间范围、作用、表层表达和可替换字段。
3. 用 `viral-pattern-abstraction` 分离体验机制与品牌表层。
   - 完成标准：可以替换人物、道具、场景和台词而保留体验功能。
4. 读取 `viral-experience-pov` 编译目标商品的 POV 和动作连续性。
   - 完成标准：不新增未被 Facts 支持的功效、舒缓或安全性主张。
5. 读取 `viral-fact-mapping`，单独审计口播、字幕、标题和包装文字。
   - 完成标准：体验语言、商品声明和 unknown 状态分离。
6. 用 `factframe-script-storyboard` 生成/审核 fact-bound Script/Storyboard。
   - 完成标准：shot continuity、商品组件、可见/可听 claim 的验收条件都已写入冻结合同输入；尚无 artifact 时不得伪造 ASR/OCR 结果。
7. 冻结 ReplicationContract，执行重复实验并记录方差。
   - 完成标准：primary experience dimension 是唯一变化，其他配置字段一致。
8. 用 `viral-media-integrity` 建立/复核 `MediaIntegrityRecord`。
   - 完成标准：身份/连续性、声画表达与来源使用范围分别核对；artifact-dependent gate 在 preflight 保持 pending，artifact review 也不自动代表权利或发布批准。

## Stop conditions

- POV/ASMR 机制与未证实功效无法分开。
- 商品 identity 在镜头间变化或参考素材授权未知。
- 关键 ASR/OCR 不可用且没有人工复核路径。
- 模型自由添加体验者健康、育儿、安全或比较性结论。
- 把沉浸感、播放量或情绪评价写成产品效果证明。
- 把 Asset QA、可播放或模型相似度当作 source-use、原创、商业、平台或发布许可，或任一 Media Integrity Gate 无法以有范围证据闭合。

## Outputs

ReferenceBundle、experience DecompositionMap、PatternHypothesis、POV adaptation、ReplicationContract、Script/Storyboard、`MediaIntegrityRecord` 和 bounded Finding。
