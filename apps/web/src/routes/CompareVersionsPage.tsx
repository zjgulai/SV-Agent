import { useQuery } from "@tanstack/react-query";
import { useParams, useSearchParams } from "react-router-dom";

import { ApiProblem, api } from "../api/client";

export function CompareVersionsPage() {
  const { id = "" } = useParams();
  const [params] = useSearchParams();
  const left = params.get("left") ?? "";
  const right = params.get("right") ?? "";
  const comparison = useQuery({ queryKey: ["script-diff", id, left, right], queryFn: () => api.compareVersions(id, left, right), enabled: Boolean(id && left && right) });
  const error = comparison.error as ApiProblem | null;
  return (
    <section className="page page-wide">
      <p className="eyebrow">FIELD-LEVEL DIFF</p><h1>版本差异</h1><p className="lede">忽略数据库 ID 与创建时间，只显示脚本合同字段变化。</p>
      {comparison.isPending && <div className="state-card">正在比较版本…</div>}
      {error && <div className="inline-error" role="alert">{error.message}<button type="button" onClick={() => comparison.refetch()}>重试</button></div>}
      {comparison.data && <div className="diff-grid">{(["changed", "added", "removed"] as const).map((kind) => <section key={kind}><h2>{kind.toUpperCase()} · {comparison.data[kind].length}</h2>{comparison.data[kind].map((item) => <article className={`diff-item diff-${kind}`} key={item.path}><code>{item.path}</code>{"left" in item && <><del>{String(item.left)}</del><ins>{String(item.right)}</ins></>}{"value" in item && <p>{String(item.value)}</p>}</article>)}</section>)}</div>}
    </section>
  );
}
