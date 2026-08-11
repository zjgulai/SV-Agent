import { Link, useParams } from "react-router-dom";

import { useJobPolling } from "../features/generations/useJobPolling";

const LABELS: Record<string, string> = {
  queued: "正在生成",
  fetching: "正在读取公开来源",
  parsing: "正在提取商品事实",
  generating: "正在生成",
  validating: "正在校验",
  succeeded: "任务完成",
  failed: "任务失败",
  validation_failed: "校验未通过",
};

export function JobPage() {
  const { id = "" } = useParams();
  const job = useJobPolling(id);
  if (job.isPending) return <section className="page"><div className="state-card">正在恢复任务…</div></section>;
  if (job.isError) return <section className="page"><div className="state-card state-error">任务读取失败。</div></section>;
  const data = job.data;
  const terminal = ["succeeded", "failed", "validation_failed"].includes(data.state);
  const destination = data.job_type === "script_generation" ? `/scripts/${data.result_id}` : `/products/${data.result_id}`;
  const statusLabel = data.state === "queued" && data.job_type === "product_import" ? "等待安全导入" : LABELS[data.state];
  return (
    <section className="page job-page">
      <p className="eyebrow">DURABLE JOB · {data.id.slice(0, 8)}</p>
      <div className={`job-orbit ${terminal ? "terminal" : ""}`}><span /><span /><strong>{data.attempt_count}</strong></div>
      <h1 role="status">{statusLabel}</h1>
      {!terminal && <p className="lede">任务状态来自 PostgreSQL。关闭页面后再次打开，也能从这里恢复。</p>}
      {data.error_detail && <div className="state-card state-error">{data.error_detail}</div>}
      {terminal && data.result_id && data.state !== "failed" && <Link className="button button-primary job-result" to={destination}>{data.job_type === "script_generation" ? "查看脚本" : "查看商品"}</Link>}
    </section>
  );
}
