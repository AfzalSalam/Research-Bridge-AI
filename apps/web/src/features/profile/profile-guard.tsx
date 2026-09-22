"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { getAccountProfile } from "@/lib/api/profile";
import { useAuth } from "@/features/auth/use-auth";

export function ProfileGuard({ children }: { children: React.ReactNode }) {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  const profileQuery = useQuery({
    queryKey: ["profile"],
    queryFn: ({ signal }) => getAccountProfile(signal),
    enabled: !!user,
  });

  useEffect(() => {
    if (authLoading || profileQuery.isLoading) return;

    if (!user) {
      router.push("/login");
      return;
    }

    if (!profileQuery.data && pathname !== "/onboarding") {
      router.push("/onboarding");
    }
  }, [user, authLoading, profileQuery.isLoading, profileQuery.data, pathname, router]);

  if (authLoading || profileQuery.isLoading) {
    return (
      <div className="flex h-screen w-full items-center justify-center">
        <p className="text-muted-foreground animate-pulse">Loading profile...</p>
      </div>
    );
  }

  // Prevent flashing content if user is logged out or profile is missing (and they aren't on onboarding)
  if (!user || (!profileQuery.data && pathname !== "/onboarding")) {
    return null;
  }

  return <>{children}</>;
}
