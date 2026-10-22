"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/features/auth/use-auth";
import {
  accountProfileQueryKey,
  getAccountProfile,
  updateAccountProfile,
  type AccountProfile,
} from "@/lib/api/profile";

export function useAccountProfile() {
  const { user, loading: authLoading } = useAuth();
  const userId = user?.id ?? null;
  const query = useQuery({
    queryKey: accountProfileQueryKey(userId),
    queryFn: ({ signal }) => getAccountProfile(signal),
    enabled: !authLoading && userId !== null,
    staleTime: 30_000,
    retry: false,
  });

  return { ...query, authLoading, userId };
}

export function useSaveAccountProfile(userId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (profile: AccountProfile) => updateAccountProfile(profile),
    onSuccess: async (savedProfile) => {
      // A profile read started before the save must not overwrite the saved facts.
      await queryClient.cancelQueries({ queryKey: accountProfileQueryKey(userId), exact: true });
      queryClient.setQueryData(accountProfileQueryKey(userId), savedProfile);
      // ProfileGuard keys result screens by this data so their local search and
      // draft state is discarded when the supporting student facts change.
    },
  });
}
