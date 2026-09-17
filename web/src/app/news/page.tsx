import { listNews, parseTags } from "@/lib/db";
import { createMetadata } from "@/lib/seo";
import Link from "next/link";

export const dynamic = "force-dynamic";

export const metadata = createMetadata({
  title: "News",
  description: "ข่าวเทคทั่วโลกสำหรับ maker — wearable, robot, open-source, edge AI",
  path: "/news",
});

export default async function NewsPage() {
  const items = await listNews();
  const [hero, ...rest] = items;

  return (
    <section className="section">
      <div className="shell">
        <p className="kicker">Tech radar</p>
        <h2>News</h2>
        <p className="sub">ข่าวโลกที่เกี่ยวกับ wearable · IoT · robot — ไม่ใช่พอร์ทัลข่าวทั่วไป</p>

        {hero ? (
          <a className="card" href={hero.source_url} rel="noreferrer" style={{ display: "block", marginBottom: "1rem" }}>
            <div className="kicker">{hero.source_name}</div>
            <h3 style={{ fontFamily: "var(--font-display)", fontSize: "1.8rem", margin: "0.4rem 0" }}>
              {hero.title}
            </h3>
            <p>{hero.summary}</p>
          </a>
        ) : (
          <p className="notice">ยังไม่มีข่าวในฐานข้อมูล — รัน seed ได้</p>
        )}

        <div className="news-grid">
          {rest.map((item) => (
            <article key={item.id} className="card news-card">
              <div className="kicker">{item.source_name}</div>
              <h3>{item.title}</h3>
              <p>{item.summary}</p>
              <div className="tags">
                {parseTags(item.topics_json).map((t) => (
                  <span key={t} className="tag">
                    {t}
                  </span>
                ))}
              </div>
              <div style={{ display: "flex", gap: "0.5rem", marginTop: "auto" }}>
                <a className="btn btn-ghost" href={item.source_url} rel="noreferrer">
                  แหล่งข่าว
                </a>
                <Link className="btn btn-primary" href={`/lab?prompt=${encodeURIComponent(item.title)}`}>
                  ลองใน Lab
                </Link>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
