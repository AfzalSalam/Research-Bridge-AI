import type { ReactNode } from "react";
import { ProfileGuard } from "@/features/profile/profile-guard";
export default function Layout({children}:{children:ReactNode}){return <ProfileGuard>{children}</ProfileGuard>;}
