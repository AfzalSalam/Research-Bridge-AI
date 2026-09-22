import { ProfileGuard } from "@/features/profile/profile-guard";

export default function OpportunitiesLayout({ children }: { children: React.ReactNode }) {
  return <ProfileGuard>{children}</ProfileGuard>;
}
