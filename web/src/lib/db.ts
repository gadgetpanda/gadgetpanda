import { getCloudflareContext } from "@opennextjs/cloudflare";

export type Project = {
  id: string;
  slug: string;
  title: string;
  summary: string;
  device: string;
  tags_json: string;
  code: string;
  cover_url: string;
  author_name: string;
  likes: number;
  featured: number;
  created_at: number;
};

export type NewsItem = {
  id: string;
  title: string;
  summary: string;
  source_name: string;
  source_url: string;
  image_url: string;
  topics_json: string;
  published_at: number;
};

export async function getDb(): Promise<D1Database | null> {
  try {
    const { env } = await getCloudflareContext({ async: true });
    return (env as CloudflareEnv).DB ?? null;
  } catch {
    return null;
  }
}

export async function listProjects(limit = 24): Promise<Project[]> {
  const db = await getDb();
  if (!db) return [];
  const { results } = await db
    .prepare(
      `SELECT * FROM community_projects ORDER BY featured DESC, likes DESC, created_at DESC LIMIT ?`,
    )
    .bind(limit)
    .all<Project>();
  return results ?? [];
}

export async function listNews(limit = 20): Promise<NewsItem[]> {
  const db = await getDb();
  if (!db) return [];
  const { results } = await db
    .prepare(`SELECT * FROM news_items ORDER BY published_at DESC LIMIT ?`)
    .bind(limit)
    .all<NewsItem>();
  return results ?? [];
}

export function parseTags(raw: string): string[] {
  try {
    const value = JSON.parse(raw) as unknown;
    return Array.isArray(value) ? value.map(String) : [];
  } catch {
    return [];
  }
}
