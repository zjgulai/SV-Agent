import type { ScriptShot } from "../../api/client";

export function ScriptTimeline({ shots }: { shots: ScriptShot[] }) {
  return (
    <div className="timeline">
      {shots.map((shot, index) => (
        <article className="shot" key={`${shot.start_seconds}-${shot.end_seconds}`}>
          <div className="shot-time"><strong>{shot.start_seconds.toFixed(1)}s</strong><span>→ {shot.end_seconds.toFixed(1)}s</span></div>
          <div className="shot-body">
            <span className="phase-label">{shot.phase_key}</span>
            <h3 id={`shot-${index}-voiceover`}>{shot.voiceover}</h3>
            <dl>
              <div><dt>画面</dt><dd id={`shot-${index}-visual`}>{shot.visual}</dd></div>
              <div><dt>动作</dt><dd id={`shot-${index}-action`}>{shot.action}</dd></div>
              <div><dt>字幕</dt><dd id={`shot-${index}-caption`}>{shot.caption || "—"}</dd></div>
              <div><dt>验收镜头</dt><dd id={`shot-${index}-acceptance_shot`}>{shot.acceptance_shot}</dd></div>
            </dl>
            <div className="fact-chips">{shot.supported_fact_ids.map((id) => <code key={id}>fact:{id.slice(0, 8)}</code>)}</div>
          </div>
        </article>
      ))}
    </div>
  );
}
