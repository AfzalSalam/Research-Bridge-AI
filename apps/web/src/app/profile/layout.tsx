import { AuthGuard } from "@/features/auth/auth-guard";

export default function ProfileLayout({ children }: { children: React.ReactNode }) {
  return <AuthGuard>{children}</AuthGuard>;
}
