import { ProfileGuard } from "@/features/profile/profile-guard";

export default function DiscoverLayout({ children }: { children: React.ReactNode }) {
  return <ProfileGuard>{children}</ProfileGuard>;
}
