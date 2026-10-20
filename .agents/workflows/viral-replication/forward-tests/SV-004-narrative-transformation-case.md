# SV-004 Narrative Transformation：专项前向测试场景

## 目的

验证 deterministic fixture oracle 能把“问题—介入—结果”作为唯一叙事变量处理，并在主机制歧义或结果事实未闭合时 fail closed。测试只消费 synthetic fixture，不生成脚本、媒体或平台动作。

## 输入场景

### Positive

- Reference source identity、digest、可复现播放和 analysis/adaptation scope 均已闭合。
- Decomposition 形成可回指的 `problem → intervention → result` 叙事弧。
- Control 与 Variant 固定 Product Snapshot、confirmed/locked Facts、平台、市场、时长、素材和权利范围。
- 唯一变化为 `narrative_arc`；目标台词、人物和画面均为独立表面，不复制来源表达。

预期：`ready_for_next_gate`，无 blocker。

### Ambiguous

- 同一请求同时把 `narrative-transformation` 与 `experience-pov` 声明为不可分离的主机制。
- 其余来源、事实和合同字段均有效。

预期：`blocked`，稳定 failure code 为 `primary_mechanism_ambiguous`；必须拆成两个 Variant。

### Blocked

- 路由唯一选择 `narrative-transformation`，但结果段没有绑定同一 Snapshot 的 eligible Fact，也无法形成可审核的 problem/intervention/result 闭环。
- 其余来源和单变量字段均有效，避免由相邻错误掩盖叙事 blocker。

预期：`blocked`，稳定 failure code 为 `narrative_arc_incomplete`。

## 消费入口

- Fixture：`fixtures/SV-004-six-mechanism-oracle-matrix.json` 中 `narrative-positive`、`narrative-ambiguous`、`narrative-blocked`。
- Runner：`python -m tools.viral_replication_oracle .agents/workflows/viral-replication/fixtures`。

## 验收边界

通过只表示本地合成合同的路由、处置和 failure code 可确定复现。它不证明参考内容表现、叙事因果、媒体质量、权利批准、部署、live 或 production acceptance。
