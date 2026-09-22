import { AuthGuard } from "@/features/auth/auth-guard";

export default function OnboardingLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <main className="container mx-auto py-12 md:py-24">{children}</main>
    </AuthGuard>
  );
}
