"use client";

import type { ReactNode } from "react";

import { DataState } from "@/components/states/data-state";
import { Button } from "@/components/ui/button";
import { useDemoStore } from "@/features/demo/demo-store";

export function DemoDataBoundary({
  children,
  loadingDescription,
  loadingTitle,
}: {
  children: ReactNode;
  loadingDescription: string;
  loadingTitle: string;
}) {
  const {
    bootstrapError,
    bootstrapStatus,
    hydrated,
    retryBootstrap,
  } = useDemoStore();

  if (bootstrapStatus === "error") {
    const requestReference = bootstrapError?.requestId
      ? ` Request reference: ${bootstrapError.requestId}.`
      : "";
    return (
      <DataState
        action={
          <Button onClick={retryBootstrap} variant="outline">
            Retry demo API
          </Button>
        }
        description={`${bootstrapError?.message ?? "The fictional catalog could not be loaded."}${requestReference}`}
        kind="error"
        title="Demo API unavailable"
      />
    );
  }

  if (!hydrated) {
    return (
      <DataState
        description={loadingDescription}
        kind="loading"
        title={loadingTitle}
      />
    );
  }

  return children;
}
