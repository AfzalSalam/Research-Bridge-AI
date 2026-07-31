import * as React from "react";

import { cn } from "@/lib/utils";

export function NativeSelect({
  className,
  ...props
}: React.ComponentProps<"select">) {
  return (
    <select
      className={cn(
        "h-11 w-full rounded-md border border-input bg-surface px-3.5 text-base text-foreground outline-none transition-[border-color,box-shadow] focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/20 disabled:cursor-not-allowed disabled:bg-muted disabled:opacity-60 aria-invalid:border-destructive motion-reduce:transition-none",
        className,
      )}
      {...props}
    />
  );
}
