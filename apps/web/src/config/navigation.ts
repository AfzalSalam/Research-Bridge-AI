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
    label: "Mentors",
    href: "/mentors",
    description: "Review plausible mentors and the papers behind each match.",
    icon: UsersRound,
  },
  {
    label: "Opportunities",
    href: "/opportunities",
    description: "Find research opportunities with visible source evidence.",
    icon: BriefcaseBusiness,
  },
  {
    label: "Applications",
    href: "/applications",
    description: "Keep saved opportunities and follow-ups organized.",
    icon: ClipboardList,
  },
] as const;

export const profileNavigation: NavigationItem = {
  label: "Profile",
  href: "/profile",
  description: "Manage the student facts used for matching and outreach.",
  icon: UserRound,
};
