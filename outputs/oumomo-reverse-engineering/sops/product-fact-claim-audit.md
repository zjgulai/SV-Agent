# 商品事实与声明审计 SOP

## Purpose

确保口播、字幕、标题、画面指令和包装文字中的每项商品声明都有同 Snapshot 的 confirmed/locked Fact 支持。

## Inputs

- Snapshot、Fact ledger、ScriptVersion、compiled prompt、OCR/ASR。
- supported_fact_ids、排除事实和 promotion 有效期。

## Preconditions

- 事实粒度为一个可验证命题；来源、excerpt、状态和时间明确。
- 手工事实标为 user_assertion；连接器事实标为 source_field。

## Steps

1. 抽取所有可见/可听声明：voiceover、caption、title、tag、visual、action、acceptance、包装 OCR。
2. 规范化文本并映射到 Fact ID；记录 exact、approved paraphrase 或 unsupported。
3. 验证 Fact 属于同 Snapshot 且状态为 confirmed/locked。
4. 检查数字、价格、成分、功效、认证、比较、稀缺和促销的有效期。
5. 检查 excluded fact 是否在任何字段复活。
6. unsupported 一律 blocking，不因 Job 成功或画面好看而放行。

## Evidence

- S-B01：基础脚本产生 focus/energy/taste 等无证据声明。
- S-T02：产生价格、糖、血糖、crash 和省钱比较。
- S-P01：测试 10% 折扣被扩写成 6 处真实促销语气。
- U-B01：发明 200mg caffeine、instant awake、no clumps 和包装。

## Stop Conditions

- 找不到 Snapshot/Fact 状态或编译后的实际 prompt。
- 包装/字幕/口播无法读取且无人工复核。
- 事实来源是标题、类别或模型推断而不是证据。

## Acceptance

- fact precision=100%；unsupported claim count=0。
- 所有 claim 有 Fact ID；excluded fact occurrence=0。
- 促销、价格和时变事实在目标市场/时间有效。

## Recovery

删除声明不是唯一方案：可新增证据并走 proposed→confirmed/locked，或改为非声明创意字段。禁止把模型猜测直接升级为 source_field。
