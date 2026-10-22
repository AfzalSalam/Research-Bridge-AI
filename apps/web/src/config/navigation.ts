import type { LucideIcon } from "lucide-react";
import {
  BriefcaseBusiness,
  ClipboardList,
  Compass,
  UserRound,
  UsersRound,
} from "lucide-react";

export interface NavigationItem {
  description: string;
  href: string;
  icon: LucideIcon;
  label: string;
}

export const primaryNavigation: readonly NavigationItem[] = [
  {
    label: "Discover",
    href: "/discover",
    description: "Turn a topic or paper into an evidence-led research path.",
    icon: Compass,
  },
  {
    label: "My Research",
    href: "/research",
    description: "Keep papers, reading notes, and researcher shortlists together.",
    icon: UsersRound,
  },
  {
    label: "Conversations",
    href: "/conversations",
    description: "Continue saved outreach drafts with their paper evidence.",
    icon: ClipboardList,
  },
  {
    label: "Opportunities",
    href: "/opportunities",
    description: "Find research opportunities with visible source evidence.",
    icon: BriefcaseBusiness,
  },
] as const;

export const profileNavigation: NavigationItem = {
  label: "Profile & Settings",
  href: "/profile",
  description: "Manage the student facts used for matching and outreach.",
  icon: UserRound,
};
