"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

import { DemoProvider } from "@/features/demo/demo-store";
import { ThemeProvider } from "@/features/theme/theme-provider";
import { configureApiClient } from "@/lib/api/setup";

if (typeof window !== "undefined") {
  configureApiClient();
}

export function AppProviders({ children }: { children: ReactNode }) {
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
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <DemoProvider>{children}</DemoProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}

