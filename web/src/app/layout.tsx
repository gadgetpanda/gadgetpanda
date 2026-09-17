import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans, Syne } from "next/font/google";
import { SiteFooter, SiteHeader } from "@/components/SiteChrome";
import { createMetadata, siteConfig } from "@/lib/seo";
import "./globals.css";

const display = Syne({
  variable: "--font-display",
  subsets: ["latin"],
  weight: ["600", "700", "800"],
});

const body = IBM_Plex_Sans({
  variable: "--font-body",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

const mono = IBM_Plex_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  ...createMetadata({}),
  applicationName: siteConfig.name,
  keywords: [
    "Gadget Panda",
    "smart ring",
    "RING503PANDA",
    "SoftDog",
    "FLOW-UFO",
    "BLE",
    "maker",
    "Python SDK",
  ],
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="th">
      <body className={`${display.variable} ${body.variable} ${mono.variable}`}>
        <SiteHeader />
        <main>{children}</main>
        <SiteFooter />
      </body>
    </html>
  );
}
