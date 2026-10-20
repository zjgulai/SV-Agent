// Variant C is the selected direction; A/B remain switchable primary-source references until the prototype can be archived.
import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { PrototypeSwitcher, PrototypeVariantKey } from "../features/prototype/PrototypeSwitcher";
import "../features/prototype/decision-workbench.css";

type Decision = "ship" | "revise" | "collect" | "stop" | null;
type EvidenceKind = "direct" | "derived" | "unknown" | "blocked" | "passed";
type GateState = "ready" | "blocked" | "needs_evidence" | "passed";
type WorkbenchState = {
  variant: PrototypeVariantKey;
  selectedDecisionId: string;
  activeJourneyNode: string;
  journeyMode: "business" | "audit";
  creativeView: "script" | "storyboard" | "asset";
  highlightDifferences: boolean;
  proposedDecision: Decision;
};

const DECISION_ITEMS = [
  { id: "claim", label: "Reported Claim 未匹配事实", meta: "Claim Gate", note: "阻断" },
  { id: "experiment", label: "Relief hook 实验合同已就绪", meta: "Experiment", note: "可比较" },
  { id: "asset", label: "素材仍处于 hold", meta: "Asset QA", note: "待复核" },
];

const EVIDENCE = [
  { kind: "direct" as EvidenceKind, source: "Leap observation", title: "22 videos · 10,312 views", body: "德国奶瓶清洗暖奶器工作区，2026-08-21 至 08-27；上游采集与排序方法未披露。" },
  { kind: "blocked" as EvidenceKind, source: "Fact gate", title: "“杀菌” Claim 未获支持", body: "Reported Product Claim 没有匹配 confirmed / locked Product Fact，不能进入脚本。" },
  { kind: "derived" as EvidenceKind, source: "Oumomo experiment", title: "能力证据，不是市场证据", body: "冻结配置可复现 Hook 结构；它不证明商品事实，也不证明平台效果。" },
  { kind: "unknown" as EvidenceKind, source: "Momcozy asset", title: "fixture-bundle-047 · hold", body: "Bundle、Recipe、hash 已存在；品牌 QA 与 Aggregate Index 仍缺失。" },
];

const JOURNEY = [
  { id: "signal", label: "Leap Signal", state: "passed" as GateState, detail: "观察到 manual-to-automation relief、visible proof 与 POV/ASMR 三类方向。", needs: "保留对象、平台、时间窗与方法缺口。" },
  { id: "claim", label: "Claim Gate", state: "blocked" as GateState, detail: "外部 AI 提取的“杀菌”卖点没有匹配可用 Product Fact。", needs: "删除该表达，或补充可审核商品证据。" },
  { id: "contract", label: "Experiment", state: "ready" as GateState, detail: "只改变 Hook framing：功能说明 → hands-free relief。", needs: "冻结 control、variant、平台与停止条件。" },
  { id: "evidence", label: "Oumomo", state: "passed" as GateState, detail: "验证供应商在固定配置下能够稳定生成结构化 Hook。", needs: "不得将能力可复现误写为市场有效。" },
  { id: "storyboard", label: "Storyboard", state: "ready" as GateState, detail: "零成本 typed preview 已绑定 Pattern 与事实 allow-list。", needs: "重新验证所有 visible Claim。" },
  { id: "asset", label: "Asset QA", state: "needs_evidence" as GateState, detail: "候选 Bundle 结构有效，但文件级状态仍为 hold。", needs: "完成品牌复核并建立全库 Aggregate Index。" },
  { id: "decision", label: "Decision", state: "blocked" as GateState, detail: "当前不能 Ship；允许 Revise、Collect evidence 或 Stop。", needs: "Claim Gate 与 Asset QA 同时通过。" },
];

function EvidenceStatus({ kind, children }: { kind: EvidenceKind | GateState; children: React.ReactNode }) {
  return <span className={`prototype-status prototype-status-${kind}`}>{children}</span>;
}

function DecisionActions({ value, onChange }: { value: Decision; onChange: (value: Decision) => void }) {
  return (
    <div className="prototype-action-row" aria-label="原型决策动作">
      <button className="prototype-action" type="button" disabled title="Claim Gate 与 Asset QA 尚未通过">Ship</button>
      <button className="prototype-action" type="button" aria-pressed={value === "revise"} onClick={() => onChange("revise")}>Revise</button>
      <button className="prototype-action" type="button" aria-pressed={value === "collect"} onClick={() => onChange("collect")}>Collect evidence</button>
      <button className="prototype-action" type="button" aria-pressed={value === "stop"} onClick={() => onChange("stop")}>Stop</button>
    </div>
  );
}

function PrototypeStateInspector({ state }: { state: WorkbenchState }) {
  return (
    <details className="prototype-state" open>
      <summary>Prototype state · 所有 action 仅更新内存</summary>
      <pre>{JSON.stringify(state, null, 2)}</pre>
    </details>
  );
}

export function VariantA({ state, setState }: { state: WorkbenchState; setState: React.Dispatch<React.SetStateAction<WorkbenchState>> }) {
  const selected = DECISION_ITEMS.find((item) => item.id === state.selectedDecisionId) ?? DECISION_ITEMS[0];
  return (
    <section aria-labelledby="variant-a-title">
      <div className="prototype-section-title">
        <div><p className="prototype-kicker">Variant A · Decision inbox</p><h2 id="variant-a-title">先处理最重要的决定</h2></div>
        <p>验证问题：FactFrame 应不应该首先成为 Creative Ops 的决策队列，而不是分析 Dashboard？</p>
      </div>
      <div className="decision-inbox">
        <aside className="decision-queue">
          <p className="prototype-kicker">Decision queue · 无自动排序</p>
          <div className="decision-queue-list">
            {DECISION_ITEMS.map((item) => <button key={item.id} className="decision-queue-item" type="button" aria-pressed={selected.id === item.id} onClick={() => setState((current) => ({ ...current, selectedDecisionId: item.id }))}><span>{item.meta}</span><strong>{item.label}</strong><small>{item.note}</small></button>)}
          </div>
        </aside>
        <main className="decision-brief">
          <div className="decision-brief-header"><div><p className="prototype-kicker">Selected · {selected.meta}</p><h2>{selected.label}</h2></div><EvidenceStatus kind="blocked">Ship blocked</EvidenceStatus></div>
          <div className="decision-quadrants">
            <article><h3>Observation</h3><p>Top 10 占观察窗口总 views 的 86.09%；relief、visible proof 与 POV/ASMR 反复出现。</p><EvidenceStatus kind="direct">Direct report</EvidenceStatus></article>
            <article><h3>Inference</h3><p>“从手动劳动到自动化释放”值得进入受控 Hook 实验，但排名不能证明因果。</p><EvidenceStatus kind="derived">Hypothesis</EvidenceStatus></article>
            <article><h3>Unknown</h3><p>采集、去重、paid/organic、排名公式、AI 模型与人工复核方法没有披露。</p><EvidenceStatus kind="unknown">Method gap</EvidenceStatus></article>
            <article><h3>Action</h3><p>删除未支持的杀菌表达；冻结唯一变量；完成 Bundle 品牌 QA 后重新评估。</p><DecisionActions value={state.proposedDecision} onChange={(decision) => setState((current) => ({ ...current, proposedDecision: decision }))} /></article>
          </div>
          <div className="decision-gate"><strong>为什么不能 Ship？</strong><span>Reported Claim 未通过 confirmed/locked Fact Gate；候选素材状态为 hold。</span></div>
        </main>
        <aside className="decision-evidence">
          <p className="prototype-kicker">Evidence rail</p>
          <div className="evidence-stack">{EVIDENCE.map((item) => <article className="prototype-card evidence-item" key={item.source}><header><small>{item.source}</small><EvidenceStatus kind={item.kind}>{item.kind}</EvidenceStatus></header><h3>{item.title}</h3><p>{item.body}</p></article>)}</div>
        </aside>
      </div>
    </section>
  );
}

export function VariantB({ state, setState }: { state: WorkbenchState; setState: React.Dispatch<React.SetStateAction<WorkbenchState>> }) {
  const active = JOURNEY.find((item) => item.id === state.activeJourneyNode) ?? JOURNEY[0];
  return (
    <section aria-labelledby="variant-b-title">
      <div className="prototype-section-title">
        <div><p className="prototype-kicker">Variant B · Evidence journey</p><h2 id="variant-b-title">沿证据链定位阻断</h2></div>
        <p>验证问题：“Signal 不是 Fact”能否由界面结构自然表达，而不依赖培训？</p>
      </div>
      <div className="journey-shell">
        <div className="journey-toolbar"><span className="prototype-muted">Momcozy · Germany · 2026-08-21—08-27</span><div className="journey-mode" aria-label="旅程视图"><button type="button" aria-pressed={state.journeyMode === "business"} onClick={() => setState((current) => ({ ...current, journeyMode: "business" }))}>Business view</button><button type="button" aria-pressed={state.journeyMode === "audit"} onClick={() => setState((current) => ({ ...current, journeyMode: "audit" }))}>Audit view</button></div></div>
        <div className="journey-flow">{JOURNEY.map((item) => <button key={item.id} className="journey-node" type="button" aria-pressed={active.id === item.id} onClick={() => setState((current) => ({ ...current, activeJourneyNode: item.id }))}><EvidenceStatus kind={item.state}>{item.state.replace("_", " ")}</EvidenceStatus><strong>{item.label}</strong><small>{item.needs}</small></button>)}</div>
        <p className="journey-loop">↶ Revise 返回 Experiment · Collect evidence 返回 Claim Gate · 绿色节点不代表生产验收</p>
        <div className="journey-inspector">
          <section><p className="prototype-kicker">Active node · {state.journeyMode}</p><h2>{active.label}</h2><p className="lede">{active.detail}</p><ul><li>当前状态：{active.state}</li><li>进入下一阶段前：{active.needs}</li><li>所有外部对象只通过 immutable reference / digest 关联。</li></ul></section>
          <section><p className="prototype-kicker">Trace</p><h2>来源与边界</h2><div className="journey-source-list"><div><span>Upstream</span><strong>{active.id === "signal" ? "Leap public report" : "前一 gate 的冻结输出"}</strong></div><div><span>Authority</span><strong>{active.id === "claim" ? "PostgreSQL Product Fact" : active.id === "asset" ? "Asset Bundle + QA" : "Bounded evidence"}</strong></div><div><span>Cannot prove</span><strong>市场因果、商品真相或发布许可</strong></div></div><DecisionActions value={state.proposedDecision} onChange={(decision) => setState((current) => ({ ...current, proposedDecision: decision }))} /></section>
        </div>
      </div>
    </section>
  );
}

const SCRIPT_ROWS = [
  { phase: "Hook", control: "一天里，你还要手洗多少次？", variant: "把双手从重复清洗里还给自己。", changed: true, blocked: false },
  { phase: "Clip", control: "原型事实示例：支持自动清洗循环。", variant: "原型事实示例：支持自动清洗循环。", changed: false, blocked: false },
  { phase: "CTA", control: "查看完整流程。", variant: "杀灭全部细菌，立即入手。", changed: true, blocked: true },
];

export function VariantC({ state, setState }: { state: WorkbenchState; setState: React.Dispatch<React.SetStateAction<WorkbenchState>> }) {
  return (
    <section aria-labelledby="variant-c-title">
      <div className="prototype-section-title">
        <div><p className="prototype-kicker">Variant C · Creative comparison lab</p><h2 id="variant-c-title">只比较一个创意变量</h2></div>
        <p>验证问题：Signal-to-Experiment Compiler 能否让创意比较可信，而不是变成另一个自由编辑器？</p>
      </div>
      <div className="experiment-contract"><div><span>Hypothesis source</span><strong>Leap Creative Signal · manual-to-automation relief</strong></div><div><span>Single variable</span><strong>Hook framing</strong></div><div><span>Platform</span><strong>YouTube / TikTok</strong></div><div><span>Stop condition</span><strong>Claim 或 QA 阻断</strong></div><div><span>Contract</span><strong>Frozen · fixture-v1</strong></div></div>
      <div className="creative-lab-toolbar"><div className="creative-view-tabs" aria-label="创意对比视图">{(["script", "storyboard", "asset"] as const).map((view) => <button key={view} className="prototype-action" type="button" aria-pressed={state.creativeView === view} onClick={() => setState((current) => ({ ...current, creativeView: view }))}>{view}</button>)}</div><button className="prototype-action" type="button" aria-pressed={state.highlightDifferences} onClick={() => setState((current) => ({ ...current, highlightDifferences: !current.highlightDifferences }))}>Highlight differences</button></div>
      <div className="creative-split">
        {(["Control", "Variant"] as const).map((column) => <section className="prototype-card creative-column" key={column}><header><strong>{column}</strong><EvidenceStatus kind={column === "Control" ? "passed" : "blocked"}>{column === "Control" ? "contract valid" : "claim blocked"}</EvidenceStatus></header><div className="creative-frame">{SCRIPT_ROWS.map((row) => { const isVariant = column === "Variant"; const className = isVariant && row.blocked ? "creative-blocker" : state.highlightDifferences && row.changed ? "creative-difference" : ""; return <article className={className} key={row.phase}><p className="prototype-kicker">{row.phase} · {state.creativeView}</p><h3>{isVariant ? row.variant : row.control}</h3><p>{state.creativeView === "script" ? "Visible copy 与 Product Claim 的绑定检查。" : state.creativeView === "storyboard" ? "镜头、视觉和时间合同的只读预览。" : "候选 Bundle、hash、Recipe 与 QA 的只读投影。"}</p><span className="creative-claim">{row.blocked && isVariant ? "unmatched reported claim" : "fixture-fact-locked-01"}</span></article>; })}</div></section>)}
      </div>
      <div className="creative-lab-bottom">
        <section className="prototype-card difference-ledger"><div className="prototype-section-title"><div><p className="prototype-kicker">Difference ledger</p><h2>冻结差异</h2></div><DecisionActions value={state.proposedDecision} onChange={(decision) => setState((current) => ({ ...current, proposedDecision: decision }))} /></div><table><thead><tr><th>Field</th><th>Control</th><th>Variant</th><th>Gate</th></tr></thead><tbody><tr><td>Hook framing</td><td>Problem question</td><td>Hands-free relief</td><td>Allowed variable</td></tr><tr><td>Product facts</td><td>1 locked fixture</td><td>+1 unmatched claim</td><td>Blocked</td></tr><tr><td>Asset QA</td><td>reviewed fixture</td><td>hold</td><td>Needs evidence</td></tr></tbody></table></section>
        <aside className="prototype-card creative-evidence"><p className="prototype-kicker">Evidence drawer</p><h2>灵感不是证明</h2><ul><li>Leap：只作为 Hypothesis source。</li><li>FactFrame：决定 Claim 是否可用。</li><li>Oumomo：验证能力与失败边界。</li><li>Asset Bundle：决定素材是否可复用。</li></ul></aside>
      </div>
    </section>
  );
}

export function DecisionWorkbenchPrototypePage() {
  const [searchParams] = useSearchParams();
  const requested = searchParams.get("variant")?.toUpperCase();
  const variant: PrototypeVariantKey = requested === "A" || requested === "B" ? requested : "C";
  const [state, setState] = useState<WorkbenchState>({ variant, selectedDecisionId: "claim", activeJourneyNode: "claim", journeyMode: "business", creativeView: "script", highlightDifferences: true, proposedDecision: null });
  const visibleState = useMemo(() => ({ ...state, variant }), [state, variant]);

  return (
    <div className="prototype-workbench">
      <div className="prototype-banner"><span>Prototype · read only · fixture data</span><span>不调用 API，不写 Product Fact、实验台账或素材状态</span></div>
      <header className="prototype-hero"><div><p className="prototype-kicker">Momcozy creative intelligence</p><h1>证据驱动内容决策工作台</h1><p className="lede">把平台信号、商品事实、可复现实验、Storyboard 与素材 QA 组织成一条可解释的决策链。</p></div><div className="prototype-scope"><span className="prototype-chip"><strong>Brand</strong> Momcozy</span><span className="prototype-chip"><strong>Market</strong> Germany</span><span className="prototype-chip"><strong>Window</strong> 2026-08-21—08-27</span><span className="prototype-chip"><strong>Ship gate</strong> blocked</span></div></header>
      {variant === "A" && <VariantA state={visibleState} setState={setState} />}
      {variant === "B" && <VariantB state={visibleState} setState={setState} />}
      {variant === "C" && <VariantC state={visibleState} setState={setState} />}
      <PrototypeStateInspector state={visibleState} />
      <PrototypeSwitcher current={variant} />
    </div>
  );
}
