import Link from "next/link";
import { listProjects, parseTags } from "@/lib/db";
import { createMetadata } from "@/lib/seo";

export const dynamic = "force-dynamic";

export const metadata = createMetadata({
  title: "PandaWorld",
  description: "ชุมชนโปรเจกต์ Gadget Panda — แชร์ ดาวน์โหลด Remix ใน Lab",
  path: "/world",
});

export default async function WorldPage() {
  const projects = await listProjects();

  return (
    <section className="section">
      <div className="shell">
        <p className="kicker">Community · MakerWorld-style</p>
        <h2>PandaWorld</h2>
        <p className="sub">โปรเจกต์จาก maker — เปิดใน Lab เพื่อ remix ด้วย Gemini</p>

        {projects.length === 0 ? (
          <p className="notice">ยังไม่มีโปรเจกต์ในฐานข้อมูล — รัน seed หรือสร้างจาก Lab</p>
        ) : (
          <div className="project-grid">
            {projects.map((p) => (
              <article key={p.id} className="card project-card">
                <div className="device">{p.device}</div>
                <h3>{p.title}</h3>
                <p>{p.summary}</p>
                <div className="tags">
                  {parseTags(p.tags_json).map((tag) => (
                    <span key={tag} className="tag">
                      {tag}
                    </span>
                  ))}
                </div>
                <p style={{ color: "var(--mute)", fontSize: "0.85rem" }}>
                  {p.author_name} · ♥ {p.likes}
                </p>
                <Link
                  className="btn btn-ghost"
                  href={`/lab?device=${encodeURIComponent(p.device)}&prompt=${encodeURIComponent(
                    `Remix โปรเจกต์นี้: ${p.title}. ${p.summary}`,
                  )}`}
                >
                  Open in Lab
                </Link>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
