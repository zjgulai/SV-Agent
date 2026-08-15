import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "../../api/client";

const TERMINAL = new Set(["succeeded", "failed", "validation_failed"]);
const MAX_BACKOFF_MS = 30_000;

export function useDocumentHidden() {
  const [hidden, setHidden] = useState(() => globalThis.document?.hidden ?? false);
  useEffect(() => {
    const update = () => setHidden(globalThis.document.hidden);
    globalThis.document?.addEventListener("visibilitychange", update);
    return () => globalThis.document?.removeEventListener("visibilitychange", update);
  }, []);
  return hidden;
}

export function jobPollingInterval({
  pause,
  hidden,
  state,
  failureCount,
}: {
  pause: boolean;
  hidden: boolean;
  state: string | undefined;
  failureCount: number;
}): number | false {
  if (pause || hidden || (state && TERMINAL.has(state))) return false;
  return Math.min(1_000 * 2 ** failureCount, MAX_BACKOFF_MS);
}

export function useJobPolling(jobId: string, pause = false) {
  const hidden = useDocumentHidden();
  return useQuery({
    queryKey: ["job", jobId],
    queryFn: () => api.getJob(jobId),
    enabled: Boolean(jobId) && !hidden && !pause,
    refetchInterval: (query) => {
      return jobPollingInterval({
        pause,
        hidden,
        state: query.state.data?.state,
        failureCount: query.state.fetchFailureCount,
      });
    },
  });
}
