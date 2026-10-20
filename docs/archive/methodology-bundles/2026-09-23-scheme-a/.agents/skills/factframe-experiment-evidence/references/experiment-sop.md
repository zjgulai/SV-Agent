# Oumomo Clean-room Experiment SOP

## 冻结清单

- research question 与允许的 decision use
- subject identity 与 provenance
- control / variant，仅改变一个声明的 dimension
- configuration、provider/model（若适用）与 runner version
- credit budget、reservation policy、stop rule
- expected artifacts、metrics 与 unavailable behavior

Manifest 变化必须形成新的 experiment identity，不能覆盖旧 run。

## Observation reconciliation

| 对象 | 核对内容 |
| --- | --- |
| Job | terminal state、attempt、safe failure code、timestamps |
| credit ledger | reserved、consumed、released、failed 的闭合关系 |
| artifact | stable id、type、digest、bounded metadata |
| score | exact observed value 或明确 missing reason |
| runner | version、frozen config、deterministic validator result |

Queue/progress UI、provider receipt 或余额截图不能单独证明闭合。

## Finding 模板

1. **Observation**：直接可复核的状态、值或 artifact。
2. **Inference**：限定 subject、source、dimension 与 observation window。
3. **Unknown**：缺失、失败、冲突、未采集或无法比较。
4. **Next action**：可逆实验、人工 review 或停止。
5. **Limitations**：不能支持 Product Fact、因果、winner、商业/生产结论。

## 投影到 Creative Comparison

生成 typed experiment package，而不是直接改 comparison response。绑定必须由 reviewed registry 完成；invalid/ambiguous package 保持 unavailable 或 quarantine。不要把 experiment score 合成通用总分。

## 验证

使用 `docs/research/oumomo/evidence-index.md` 路由到当前 validator、tests 和 runner。报告真实本地 run 与 Synthetic Fixture 的区别，不暴露 credentials、private task IDs、signed URLs 或 raw model reasoning。
