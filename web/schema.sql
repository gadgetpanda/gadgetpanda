-- Web platform tables on shared D1: gadgetpanda-license
-- Keeps existing users / sessions / license_keys intact.

CREATE TABLE IF NOT EXISTS community_projects (
  id TEXT PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  summary TEXT NOT NULL DEFAULT '',
  device TEXT NOT NULL CHECK (device IN ('ring', 'dog', 'drone', 'multi')),
  tags_json TEXT NOT NULL DEFAULT '[]',
  code TEXT NOT NULL DEFAULT '',
  cover_url TEXT NOT NULL DEFAULT '',
  author_name TEXT NOT NULL DEFAULT 'Gadget Panda',
  author_user_id TEXT,
  likes INTEGER NOT NULL DEFAULT 0,
  featured INTEGER NOT NULL DEFAULT 0,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_projects_device ON community_projects(device);
CREATE INDEX IF NOT EXISTS idx_projects_featured ON community_projects(featured, created_at DESC);

CREATE TABLE IF NOT EXISTS news_items (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  summary TEXT NOT NULL DEFAULT '',
  source_name TEXT NOT NULL DEFAULT '',
  source_url TEXT NOT NULL,
  image_url TEXT NOT NULL DEFAULT '',
  topics_json TEXT NOT NULL DEFAULT '[]',
  published_at INTEGER NOT NULL,
  created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_news_published ON news_items(published_at DESC);

CREATE TABLE IF NOT EXISTS store_leads (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL DEFAULT '',
  email TEXT NOT NULL DEFAULT '',
  phone TEXT NOT NULL DEFAULT '',
  product TEXT NOT NULL DEFAULT 'ring',
  qty INTEGER NOT NULL DEFAULT 1,
  note TEXT NOT NULL DEFAULT '',
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS lab_runs (
  id TEXT PRIMARY KEY,
  device TEXT NOT NULL DEFAULT 'ring',
  prompt TEXT NOT NULL,
  code TEXT NOT NULL DEFAULT '',
  created_at INTEGER NOT NULL
);
