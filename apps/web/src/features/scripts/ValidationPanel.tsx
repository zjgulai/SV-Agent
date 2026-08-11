import type { ValidationFinding } from "../../api/client";

function target(path: string) {
  const match = path.match(/^shots\[(\d+)]\.(.+)$/);
  return match ? `#shot-${match[1]}-${match[2]}` : undefined;
}

export function ValidationPanel({ acceptable, findings }: { acceptable: boolean; findings: ValidationFinding[] }) {
  const blocking = findings.filter((finding) => finding.severity === "blocking");
  return (
    <section className={`validation-panel ${acceptable ? "validation-ok" : "validation-blocked"}`}>
      <div className="validation-title">
        <div><p className="eyebrow">VALIDATION GATE</p><h2>{acceptable ? "校验通过" : "校验未通过"}</h2></div>
        <strong>{blocking.length} BLOCKING</strong>
      </div>
      {blocking.map((finding) => (
        <a className="finding" href={target(finding.path)} key={`${finding.path}-${finding.rule_id}`}>
          <span>{finding.rule_id}</span>
          <div><strong>{finding.path}</strong><p>{finding.message}</p></div>
          <span>定位 →</span>
        </a>
      ))}
    </section>
  );
}
