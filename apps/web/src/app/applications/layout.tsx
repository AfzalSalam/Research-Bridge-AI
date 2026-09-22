import { ProfileGuard } from "@/features/profile/profile-guard";

export default function ApplicationsLayout({ children }: { children: React.ReactNode }) {
  return <ProfileGuard>{children}</ProfileGuard>;
}
