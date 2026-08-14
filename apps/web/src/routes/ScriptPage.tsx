import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { ApiProblem, api } from "../api/client";
import { ScriptTimeline } from "../features/scripts/ScriptTimeline";
import { ValidationPanel } from "../features/scripts/ValidationPanel";

export function ScriptPage() {
  const { id = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const queryClient = useQueryClient();
  const script = useQuery({ queryKey: ["script", id], queryFn: () => api.getScript(id), enabled: Boolean(id) });
  const selectedId = params.get("version") ?? script.data?.versions.at(-1)?.id;
  const version = script.data?.versions.find((item) => item.id === selectedId) ?? script.data?.versions.at(-1);
  const derive = useMutation({
    mutationFn: () => {
      if (!version) throw new Error("脚本尚无可派生版本");
      return api.deriveVersion(id, version.id, `${version.draft.titles[0]} · Version 2`);
    },
    onSuccess: async (created) => {
      await queryClient.invalidateQueries({ queryKey: ["script", id] });
      setParams({ version: created.id });
    },
  });
  if (script.isPending) return <section className="page"><div className="state-card">正在读取脚本版本…</div></section>;
  if (script.isError || !version) return <section className="page"><div className="state-card state-error">脚本尚无可查看版本。</div></section>;
  const exportBase = `/api/v1/scripts/${id}/versions/${version.id}/export`;
  const deriveError = derive.error as ApiProblem | null;
  return (
    <section className="page page-wide script-page">
      <div className="page-heading"><div><p className="eyebrow">SCRIPT · {id.slice(0, 8)}</p><h1>结构化脚本</h1><p>{script.data.generation.pattern_key}@{script.data.generation.pattern_version} · {version.draft.target_duration_seconds}s · {version.draft.audience}</p></div><div className="export-actions"><a className="button" href={`${exportBase}?format=json`}>导出 JSON</a><a className="button button-primary" href={`${exportBase}?format=markdown`}>导出 Markdown</a></div></div>
      <div className="version-bar"><label>脚本版本<select value={version.id} onChange={(event) => setParams({ version: event.target.value })}>{script.data.versions.map((item, index) => <option key={item.id} value={item.id}>Version {index + 1}</option>)}</select></label><div className="version-actions"><button type="button" onClick={() => derive.mutate()} disabled={derive.isPending}>创建版本二</button>{script.data.versions.length > 1 && <Link to={`/scripts/${id}/compare?left=${script.data.versions[0].id}&right=${version.id}`}>比较版本 →</Link>}</div></div>
      {deriveError && <div className="inline-error" role="alert">{deriveError.message}</div>}
      <div className="frozen-fact-contract"><span>冻结事实合同</span><strong>纳入 {script.data.generation.selected_fact_ids.length} · 排除 {script.data.generation.excluded_fact_ids.length}</strong><small>分镜预检会重读并验证这份合同，不会自行补充商品主张。</small><Link to={"/scripts/" + id + "/versions/" + version.id + "/storyboard-preflight"}>分镜预检 →</Link></div>
      <ValidationPanel acceptable={version.validation_report.acceptable} findings={version.validation_report.findings} />
      <div className="script-columns"><section><p className="eyebrow">TIMELINE</p><ScriptTimeline shots={version.draft.shots} /></section><aside><p className="eyebrow">DELIVERY PACK</p><h2>标题</h2><ul>{version.draft.titles.map((item) => <li key={item}>{item}</li>)}</ul><h2>标签</h2><div className="tag-list">{version.draft.tags.map((item) => <span key={item}>#{item}</span>)}</div><h2>拍摄清单</h2><ol>{version.draft.shooting_list.map((item) => <li key={item}>{item}</li>)}</ol></aside></div>
    </section>
  );
}
