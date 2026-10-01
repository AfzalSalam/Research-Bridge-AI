"use client";

import { Menu } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { Brand } from "@/components/brand/brand";
import { Container } from "@/components/layout/container";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/features/auth/use-auth";
import { ThemeToggle } from "@/features/theme/theme-toggle";
import {
  Sheet,
  SheetClose,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import {
  primaryNavigation,
  profileNavigation,
  type NavigationItem,
} from "@/config/navigation";
import { cn } from "@/lib/utils";

function isCurrentRoute(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

function NavigationLink({
  item,
  pathname,
}: {
  item: NavigationItem;
  pathname: string;
}) {
  const isCurrent = isCurrentRoute(pathname, item.href);

  return (
    <Link
      aria-current={isCurrent ? "page" : undefined}
      className={cn(
        "rounded-sm text-sm font-semibold text-muted-foreground transition-colors hover:text-foreground motion-reduce:transition-none",
        "aria-[current=page]:text-brand-teal",
      )}
      href={item.href}
    >
      {item.label}
    </Link>
  );
}

export function SiteHeader() {
  const pathname = usePathname();
  const { user } = useAuth();
  
  const mobileNavigation = [...primaryNavigation];
  if (user) {
    mobileNavigation.push(profileNavigation);
  }

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/95 supports-[backdrop-filter]:bg-background/90 supports-[backdrop-filter]:backdrop-blur-sm">
      <Container className="flex min-h-18 items-center justify-between gap-5">
        <Brand />

        <nav aria-label="Primary" className="hidden items-center gap-7 lg:flex">
          {primaryNavigation.map((item) => (
            <NavigationLink item={item} key={item.href} pathname={pathname} />
          ))}
        </nav>

        <div className="hidden items-center gap-2 lg:flex">
          <ThemeToggle />
          {user ? (
            <Button asChild size="default" variant="outline">
              <Link
                aria-current={
                  isCurrentRoute(pathname, profileNavigation.href)
                    ? "page"
                    : undefined
                }
                href={profileNavigation.href}
              >
                Profile
              </Link>
            </Button>
          ) : (
            <Button asChild size="default" variant="default">
              <Link href="/login">Sign In</Link>
            </Button>
          )}
        </div>

        <div className="lg:hidden">
          <Sheet>
            <SheetTrigger asChild>
              <Button aria-label="Open navigation" size="icon" variant="outline">
                <Menu aria-hidden="true" className="size-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="right">
              <SheetHeader className="border-b border-border">
                <SheetTitle>Navigate Research Bridge</SheetTitle>
                <SheetDescription>
                  Move through the placement-release workflow.
                </SheetDescription>
              </SheetHeader>
              <nav aria-label="Mobile" className="px-6">
                {mobileNavigation.map((item) => {
                  const Icon = item.icon;
                  const isCurrent = isCurrentRoute(pathname, item.href);

                  return (
                    <SheetClose asChild key={item.href}>
                      <Link
                        aria-current={isCurrent ? "page" : undefined}
                        className={cn(
                          "grid min-h-16 grid-cols-[2.75rem_minmax(0,1fr)] items-center gap-3 border-b border-border py-3 text-foreground outline-none transition-colors hover:text-brand-teal focus-visible:text-brand-teal motion-reduce:transition-none",
                          isCurrent && "text-brand-teal",
                        )}
                        href={item.href}
                      >
                        <span className="grid size-10 place-items-center rounded-full bg-muted text-brand-indigo">
                          <Icon
                            aria-hidden="true"
                            className="size-5"
                            strokeWidth={1.8}
                          />
                        </span>
                        <span>
                          <span className="block text-sm font-semibold">
                            {item.label}
                          </span>
                          <span className="mt-0.5 block text-xs leading-5 font-normal text-muted-foreground">
                            {item.description}
                          </span>
                        </span>
                      </Link>
                    </SheetClose>
                  );
                })}
              </nav>
              <p className="mt-auto border-t border-border p-6 text-xs leading-5 text-muted-foreground">
                Evidence before generation. Unknown facts stay unknown.
              </p>
            </SheetContent>
          </Sheet>
        </div>
      </Container>
    </header>
  );
}
