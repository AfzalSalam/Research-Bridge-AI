"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/features/theme/theme-provider";
import { Button } from "@/components/ui/button";

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  return (
    <Button
      aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      onClick={toggleTheme}
      size="icon"
      variant="ghost"
      className="transition-colors motion-reduce:transition-none"
    >
      {theme === "dark" ? (
        <Sun aria-hidden="true" className="size-5" strokeWidth={1.8} />
      ) : (
        <Moon aria-hidden="true" className="size-5" strokeWidth={1.8} />
      )}
    </Button>
  );
}
