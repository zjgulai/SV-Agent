# 发布 Dry-run SOP

## Purpose

验证发布字段、校验和停止点，不授权账号、不绑定商品、不创建真实发布。

## Inputs

- 已接受的 MediaArtifact/项目。
- 目标平台、title、tags、product、AI label、privacy、schedule 草案。

## Preconditions

- 有权使用视频与商品；Artifact 已通过事实和媒体 QA。
- 明确本轮无 OAuth、无账号绑定、无最终 publish 权限。

## Steps

1. 打开发布页，选择已有项目但不上传私有素材。
2. 记录视频/封面、账号、标题、标签、商品、产品名、预检、AI 标识、立即/定时字段。
3. 记录必填、格式、字符限制、默认值和预览状态。
4. 到达 `立即授权`、账号绑定、商品授权或最终发布按钮前停止。
5. 保存字段合同和 stopped_before 状态，不保存账号信息。

## Evidence

- P-DRY：U-B01 项目选择成功，页面保留在发布路由；观察到 10 类字段，并在 TikTok OAuth 和发布前停止。
- 去重/质检选择会错误跳路由，发布选择器没有复现该缺陷。

## Stop Conditions

- 页面要求 OAuth、二维码、账号凭证、商品授权或外部确认。
- 任何按钮/文案路径都不允许触发发布、排期或外发消息；出现此类触发即刻停止。
- Artifact 未通过事实/媒体 QA。

## Acceptance

- PublishDraft 字段、required/optional、默认值和停止点完整。
- 外部账号、商品和平台状态零变更；积分零扣。
- 不宣称发布成功、官方加权或账号权重提升。

## Recovery

关闭/离开页面，确认项目仍为未发布且无定时任务。若误入 OAuth，立即返回且不授权；若已进入外部账号页面，停止并由用户在平台端核验与恢复状态。
