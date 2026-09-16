"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "./use-auth";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    const isDemo = typeof window !== "undefined" && localStorage.getItem("demo_mode") === "true";
    if (!loading && !user && !isDemo) {
      router.push("/login");
    }
  }, [user, loading, router]);

  const isDemo = typeof window !== "undefined" && localStorage.getItem("demo_mode") === "true";

  if (!isDemo && (loading || !user)) {
    return (
      <div className="flex h-screen w-full items-center justify-center">
        <p className="text-muted-foreground animate-pulse">Loading...</p>
      </div>
    );
  }

  return <>{children}</>;
}
