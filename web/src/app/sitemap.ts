import type { MetadataRoute } from "next";
import { siteConfig } from "@/lib/seo";

export default function sitemap(): MetadataRoute.Sitemap {
  const paths = ["", "/store", "/world", "/lab", "/news", "/support", "/ring", "/dog", "/drone"];
  const now = new Date();
  return paths.map((path) => ({
    url: `${siteConfig.url}${path || "/"}`,
    lastModified: now,
    changeFrequency: path === "/news" ? "hourly" : "weekly",
    priority: path === "" ? 1 : 0.7,
  }));
}
