# SV-004 Experience POV：专项前向测试场景

## 目的

验证 deterministic fixture oracle 能在体验型复刻中保留单一 POV/体验变量，并把目标商品身份连续性作为独立门；主机制歧义或跨镜头身份未闭合时必须 fail closed。

## 输入场景

### Positive

- Reference source identity、digest、可复现播放和 analysis/adaptation scope 均已闭合。
- Decomposition 只抽象 POV、动作和感官功能，不复制来源人物、台词、声音或品牌表面。
- Control 与 Variant 固定 Product Snapshot、confirmed/locked Facts、平台、市场、时长、声音政策和授权素材。
- 唯一变化为 `experience_pov`，且每个镜头都绑定相同 target identity。

预期：`ready_for_next_gate`，无 blocker。

### Ambiguous

- 同一请求同时把 `experience-pov` 与 `narrative-transformation` 声明为不可分离的主机制。
- 其余来源、事实和合同字段均有效。

预期：`blocked`，稳定 failure code 为 `primary_mechanism_ambiguous`；必须拆成两个 Variant。

### Blocked

- 路由唯一选择 `experience-pov`，但跨镜头 target asset/颜色/组件身份无法与冻结对象一致绑定。
- 其余来源、事实、权利和单变量字段均有效。

预期：`blocked`，稳定 failure code 为 `experience_identity_continuity_unresolved`。

## 消费入口

- Fixture：`fixtures/SV-004-six-mechanism-oracle-matrix.json` 中 `experience-positive`、`experience-ambiguous`、`experience-blocked`。
- Runner：`python -m tools.viral_replication_oracle .agents/workflows/viral-replication/fixtures`。

## 验收边界

通过只表示本地合成合同的路由、处置和 failure code 可确定复现。它不证明真实感官体验、人物/商品相似度、媒体连续性、权利批准、部署、live 或 production acceptance。
