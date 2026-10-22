"use client";

import { Fragment, useEffect, type ReactNode } from "react";
import { useRouter, usePathname } from "next/navigation";

import { DataState } from "@/components/states/data-state";
import { Button } from "@/components/ui/button";
import { useAccountProfile } from "@/features/profile/use-account-profile";
import { profileErrorMessage } from "@/lib/api/profile";

export function ProfileGuard({ children }: { children: ReactNode }) {
  const profile = useAccountProfile();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (profile.authLoading) return;
    if (!profile.userId) {
      router.replace("/login");
    } else if (profile.isSuccess && profile.data === null && pathname !== "/onboarding") {
      router.replace("/onboarding");
    }
  }, [profile.authLoading, profile.userId, profile.isSuccess, profile.data, pathname, router]);

  if (profile.authLoading || !profile.userId || profile.isPending) {
    return <DataState kind="loading" title="Loading your profile" description="Checking your account and saved research background." />;
  }
  if (profile.isError) {
    return <DataState kind="error" title="Your profile is unavailable" description={profileErrorMessage(profile.error)} action={<Button onClick={() => void profile.refetch()}>Retry profile</Button>} />;
  }
  if (!profile.data && pathname !== "/onboarding") return null;

  // Restart result/draft state when profile evidence changes, keeping the editor
  // mounted during saves so its success feedback and focus are preserved.
  const evidenceKey = pathname === "/profile" || pathname === "/onboarding"
    ? profile.userId
    : `${profile.userId}:${JSON.stringify(profile.data)}`;
  return <Fragment key={evidenceKey}>{children}</Fragment>;
}
