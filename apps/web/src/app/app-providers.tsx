"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

import { ResearchSessionProvider } from "@/features/discovery/research-session";
import { DemoProvider } from "@/features/demo/demo-store";
import { ThemeProvider } from "@/features/theme/theme-provider";
import { configureApiClient } from "@/lib/api/setup";
import { useAuth } from "@/features/auth/use-auth";

if (typeof window !== "undefined") {
  configureApiClient();
}

function AccountQueryProvider({ children, identity }: { children: ReactNode; identity: string }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      <ResearchSessionProvider identity={identity}><DemoProvider>{children}</DemoProvider></ResearchSessionProvider>
    </QueryClientProvider>
  );
}

export function AppProviders({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  // A new identity gets a new cache and fresh local component state. Account A's
  // private results must never appear while account B's requests are loading.
  const identity = loading ? "loading" : user?.id ?? "anonymous";
  return (
    <ThemeProvider>
      <AccountQueryProvider key={identity} identity={identity}>{children}</AccountQueryProvider>
    </ThemeProvider>
  );
}

