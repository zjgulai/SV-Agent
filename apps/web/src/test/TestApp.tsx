import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

import { AppRoutes } from "../App";

export function TestApp({ initialEntries }: { initialEntries: string[] }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } },
  });
  return (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>
        <AppRoutes />
      </MemoryRouter>
    </QueryClientProvider>
  );
}
