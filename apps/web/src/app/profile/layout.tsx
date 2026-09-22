import { ProfileGuard } from "@/features/profile/profile-guard";

export default function ProfileLayout({ children }: { children: React.ReactNode }) {
  return <ProfileGuard>{children}</ProfileGuard>;
}
