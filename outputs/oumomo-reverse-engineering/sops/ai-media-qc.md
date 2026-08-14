# AI 媒体质检 SOP

## Purpose

把“视频生成成功”拆成技术、声音、文字、镜头、商品身份和事实六个独立验收门。

## Inputs

- 自有/获授权媒体、Artifact hash、批准 ScriptVersion、reference assets。
- ffprobe、抽帧、ASR、OCR、shot boundary 与 Fact ledger。

## Preconditions

- 只处理本地可控或已授权媒体；签名 URL 不落盘。
- 先记录源 hash；工具不可用必须标 unavailable。

## Steps

1. ffprobe：mime、bytes、duration、width/height、fps、codec、audio。
2. 每秒抽帧与镜头边界；检查黑帧、冻结、跳变和构图。
3. ASR 对比批准口播；OCR 对比允许字幕/包装文字。
4. 检查商品颜色、Logo、材质、组件、数量和跨镜头 identity。
5. 检查人物、手部、道具、背景和动作连续性。
6. 调用 product-fact-claim-audit；任一 unsupported claim 阻断。
7. 填 scorecard；未独立测的维度留空，不估分。

## Evidence

- U-B01：15.104s、720×1280、24fps、H.264/AAC；人物/厨房连贯，但包装文字乱码、事实失败。
- M-EX01：商品可识别但口播收益均无证据。

## Stop Conditions

- 媒体来源/授权不明。
- hash 变化、下载不完整、工具输出错误。
- ASR/OCR 不可用且关键声明无法人工核对。

## Acceptance

- 技术字段符合目标合同。
- 批准口播/字幕匹配，禁止文字为 0。
- 商品 identity 与 reference 达标，unsupported claims=0。

## Recovery

工具 unavailable 时保留原 artifact 和 hash，换用人工双人复核或另一工具；不得伪造空结果。失败项生成新 Storyboard/RenderVersion，不覆盖旧 Artifact。
