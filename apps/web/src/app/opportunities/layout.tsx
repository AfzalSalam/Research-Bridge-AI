import { AuthGuard } from "@/features/auth/auth-guard";

export default function OpportunitiesLayout({ children }: { children: React.ReactNode }) {
  return <AuthGuard>{children}</AuthGuard>;
}
