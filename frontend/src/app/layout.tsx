import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans, IBM_Plex_Serif, Noto_Sans_Bengali } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";

import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { SITE } from "@/config/site";
import { clerkAppearance } from "@/config/clerk";
import "./globals.css";

const plexSans = IBM_Plex_Sans({ variable: "--font-plex-sans", subsets: ["latin"], weight: ["400", "500", "600"] });
const plexSerif = IBM_Plex_Serif({ variable: "--font-plex-serif", subsets: ["latin"], weight: ["500", "600"] });
const plexMono = IBM_Plex_Mono({ variable: "--font-plex-mono", subsets: ["latin"], weight: ["400", "500"] });
const bengali = Noto_Sans_Bengali({ variable: "--font-bengali", subsets: ["bengali"], weight: ["400", "500"] });

export const metadata: Metadata = {
  title: { default: `${SITE.name} | Check a traffic fine`, template: `%s | ${SITE.name}` },
  description: SITE.description,
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <ClerkProvider appearance={clerkAppearance}>
      <html lang="en" className={`${plexSans.variable} ${plexSerif.variable} ${plexMono.variable} ${bengali.variable}`}>
        <body className="flex min-h-screen flex-col">
          <TooltipProvider>{children}</TooltipProvider>
          <Toaster position="bottom-center" />
        </body>
      </html>
    </ClerkProvider>
  );
}
