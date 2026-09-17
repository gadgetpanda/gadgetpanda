import type { Metadata } from "next";

export const siteConfig = {
  name: "Gadget Panda",
  url: "https://gadgetpanda.app",
  description:
    "Maker host for RING503PANDA, SoftDog, and FLOW-UFO — buy hardware, generate code in Lab, share on PandaWorld.",
  locale: "th_TH",
};

export function createMetadata({
  title,
  description,
  path = "/",
}: {
  title?: string;
  description?: string;
  path?: string;
}): Metadata {
  const fullTitle = title ? `${title} · ${siteConfig.name}` : siteConfig.name;
  const desc = description ?? siteConfig.description;
  const url = `${siteConfig.url}${path}`;

  return {
    metadataBase: new URL(siteConfig.url),
    title: fullTitle,
    description: desc,
    alternates: { canonical: path },
    openGraph: {
      type: "website",
      locale: siteConfig.locale,
      url,
      siteName: siteConfig.name,
      title: fullTitle,
      description: desc,
      images: [{ url: "/logo.jpg", width: 512, height: 512, alt: "Gadget Panda" }],
    },
    twitter: {
      card: "summary",
      title: fullTitle,
      description: desc,
      images: ["/logo.jpg"],
    },
    robots: { index: true, follow: true },
  };
}
