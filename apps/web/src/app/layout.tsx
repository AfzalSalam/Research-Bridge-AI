import type { Metadata } from "next";

import "@fontsource-variable/manrope";
import "@fontsource-variable/source-serif-4";
import "@fontsource-variable/fraunces";
import "@fontsource-variable/hanken-grotesk";
import "./globals.css";

import { AppProviders } from "@/app/app-providers";
import { SiteHeader } from "@/components/navigation/site-header";

export const metadata: Metadata = {
  title: {
    default: "Research Bridge AI",
    template: "%s | Research Bridge AI",
  },
  description: "Evidence-first academic discovery and outreach.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <a className="skip-link" href="#main-content">
          Skip to main content
        </a>
        <AppProviders>
          <SiteHeader />
          {children}
        </AppProviders>
      </body>
    </html>
  );
}
