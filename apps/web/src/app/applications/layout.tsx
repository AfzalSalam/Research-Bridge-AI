import { AuthGuard } from "@/features/auth/auth-guard";

export default function ApplicationsLayout({ children }: { children: React.ReactNode }) {
  return <AuthGuard>{children}</AuthGuard>;
}
