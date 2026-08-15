import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { api } from "../api/client";
import { recordJobObservation } from "../features/operationRecovery";
import { useDocumentHidden, useJobPolling } from "../features/generations/useJobPolling";

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

const EVENT_LABELS: Record<string, string> = {
  dispatch_dead_lettered: "投递暂停",
  dispatch_manual_retry_scheduled: "已安排运维重试",
};

export function JobPage() {
  const { id = "" } = useParams();
  const hidden = useDocumentHidden();
  const events = useQuery({
    queryKey: ["job-events", id],
    queryFn: () => api.getJobEvents(id),
    enabled: Boolean(id) && !hidden,
    refetchInterval: (query) =>
      hidden || query.state.data?.at(-1)?.event_type === "dispatch_dead_lettered" ? false : 1_000,
  });
  const deliveryDead = events.data?.at(-1)?.event_type === "dispatch_dead_lettered";
  const job = useJobPolling(id, deliveryDead);
  useEffect(() => {
    if (job.data) recordJobObservation(`/jobs/${id}`, job.data.state);
  }, [id, job.data]);
  const terminal = job.data ? ["succeeded", "failed", "validation_failed"].includes(job.data.state) : false;
  if (job.isPending) return <section className="page"><div className="state-card">正在恢复任务…</div></section>;
  if (job.isError) return <section className="page"><div className="state-card state-error"><p>任务读取失败。任务没有被重新提交。</p><button className="button button-secondary" type="button" disabled={job.isFetching} onClick={() => void job.refetch()}>重新连接</button></div></section>;
  const data = job.data;
  const destination = data.job_type === "script_generation" ? `/scripts/${data.result_id}` : `/products/${data.result_id}`;
  const statusLabel = deliveryDead
    ? "投递暂停"
    : data.state === "queued" && data.job_type === "product_import"
      ? "等待安全导入"
      : LABELS[data.state];
  return (
    <section className="page job-page">
      <p className="eyebrow">DURABLE JOB · {data.id.slice(0, 8)}</p>
      <div className={`job-orbit ${terminal ? "terminal" : ""}`}><span /><span /><strong>{data.attempt_count}</strong></div>
      <h1 role="status">{statusLabel}</h1>
      {deliveryDead ? (
        <div className="state-card state-error">
          <strong>需要运维恢复</strong>
          <p>任务尚未开始执行。消息投递已停止，部署运维可在受控环境恢复同一任务。</p>
        </div>
      ) : !terminal && <p className="lede">任务状态来自 PostgreSQL。关闭页面后再次打开，也能从这里恢复。</p>}
      {data.error_detail && <div className="state-card state-error">{data.error_detail}</div>}
      {events.data && <ol className="job-timeline" aria-label="任务实际阶段">
        {events.data.map((event) => (
          <li key={event.id}>
            <strong>{EVENT_LABELS[event.event_type] ?? LABELS[event.to_state] ?? event.to_state}</strong>
            <span>{event.event_type.replaceAll("_", " · ")}</span>
            <time dateTime={event.created_at}>{new Date(event.created_at).toLocaleTimeString()}</time>
          </li>
        ))}
      </ol>}
      {terminal && data.result_id && data.state !== "failed" && <Link className="button button-primary job-result" to={destination}>{data.job_type === "script_generation" ? "查看脚本" : "查看商品"}</Link>}
    </section>
  );
}
