# 模型路由基准 SOP

## Purpose

比较不同可见模型的价格、时延、稳定性和质量，为采购/路由决策提供证据，而不是复述供应商定位。

## Inputs

- 相同 prompt bytes、reference image hash、ratio、duration、resolution、count。
- model/provider identity、version、quote、两次以上重复。

## Preconditions

- 页面显示具体模型名；Mini/快速/高质只能算 mode。
- 每模型至少重复 2 次，总预算不超 cap。
- 同一参考素材上传成功且授权明确。

## Steps

1. 对每模型记录 capability 与 immutable quote。
2. 按固定顺序运行，保留 operation key 和 ledger。
3. 记录时延、成功率、technical profile、prompt adherence、OCR、商品/人物一致性。
4. 分别计算组内方差和模型间差异。
5. 对下载物做文件签名识别，不信任扩展名或响应 Content-Type；记录实际尺寸与编码。
6. 形成 route policy：质量门、成本门、失败回退和不支持项。

## Evidence

- VM-GATE：观察到 8 个模型；默认 Seedance 2.0/480P/10s/9:16 报 30。
- AV-GATE：Avatar 最低可见报价 75，超过 30 cap。
- T-GATE：GPT Image 2=2、Nano Banana 2=3；2×2 共 10，历史上传权限阻塞已关闭。
- I-GPT-01/02：两次均保留全部包装文字/标识并通过严格身份门；组内 SSIM 0.807526，说明构图仍有明显方差。
- I-NANO-01/02：组内 SSIM 0.989005，但一次删除包装白线，两次都改变包装比例；远端 `.png`/`image/png` 实际为 JPEG。

## Stop Conditions

- 模型身份、输入或报价不可冻结。
- file upload/授权失败。
- 供应商响应异常且 operation recovery 不明确。

## Acceptance

- 每模型至少 2 个可验证 Artifact；相同 config digest；文件签名、尺寸、hash 齐全。
- 报告同时包含价格、时延、失败率、事实、OCR 和媒体 QA。

## Recovery

输入门失败时不改用不同素材凑样本；记录 blocked。模型任务 unknown 时先恢复旧 Job，不自动切模型导致双重计费。重复相似度高不等于商品身份正确，任何真实标识丢失都必须单独触发 review/reject。
