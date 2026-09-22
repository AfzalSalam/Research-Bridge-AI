import { ProfileGuard } from "@/features/profile/profile-guard";

export default function MentorsLayout({ children }: { children: React.ReactNode }) {
  return <ProfileGuard>{children}</ProfileGuard>;
}
