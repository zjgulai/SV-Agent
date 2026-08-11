import { useQuery } from "@tanstack/react-query";

import { api } from "../../api/client";

const TERMINAL = new Set(["succeeded", "failed", "validation_failed"]);

export function useJobPolling(jobId: string) {
  return useQuery({
    queryKey: ["job", jobId],
    queryFn: () => api.getJob(jobId),
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const state = query.state.data?.state;
      return state && TERMINAL.has(state) ? false : 1_000;
    },
  });
}
