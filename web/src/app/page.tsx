import Link from "next/link";
import { createMetadata } from "@/lib/seo";

export const metadata = createMetadata({
  title: undefined,
  description:
    "One Python host. Three toys. Buy RING503PANDA, SoftDog, FLOW-UFO — code in Lab, share on PandaWorld.",
  path: "/",
});

const devices = [
  {
    href: "/ring",
    name: "RING503PANDA",
    link: "Bluetooth LE",
    blurb: "PPG · IMU · HR/HRV · temp · SpO₂ · battery",
  },
  {
    href: "/dog",
    name: "SoftDog (X1)",
    link: "Bluetooth LE",
    blurb: "Actions · move/hold · program queue · web remote",
  },
  {
    href: "/drone",
    name: "FLOW-UFO",
    link: "Wi‑Fi UDP + RTSP",
    blurb: "Stick loop · takeoff/land · FPV remote",
  },
];

export default function HomePage() {
  return (
    <>
      <section className="hero">
        <div className="shell">
          <p className="kicker">Maker platform</p>
          <h1>Gadget Panda</h1>
          <p className="lead">
            One Python host. Three toys. Infinite maker projects — เหมือนระบบนิเวศ Bambu Lab
            แต่สำหรับแหวน · หุ่นยนต์ · โดรน
          </p>
          <div className="hero-actions">
            <Link href="/store" className="btn btn-primary">
              สั่งซื้อ
            </Link>
            <Link href="/lab" className="btn btn-ghost">
              สร้างโค้ดใน Lab
            </Link>
            <Link href="/world" className="btn btn-ghost">
              PandaWorld
            </Link>
          </div>
          <p className="mono" style={{ maxWidth: 520 }}>
            pip install &apos;gadgetpanda[ui]&apos;
          </p>
        </div>
      </section>

      <section className="section">
        <div className="shell">
          <h2>Products</h2>
          <p className="sub">เลือกอุปกรณ์ แล้วเปิดโปรเจกต์หรือสั่งของได้ทันที</p>
          <div className="grid-3">
            {devices.map((d) => (
              <Link key={d.href} href={d.href} className="card device-card">
                <h3>{d.name}</h3>
                <p>{d.blurb}</p>
                <div className="meta">{d.link}</div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="section" style={{ paddingTop: 0 }}>
        <div className="shell grid-2">
          <div className="card">
            <h3>Panda Lab</h3>
            <p>Gemini สร้างโค้ด Python ที่ผูก API จริงของ gadgetpanda — แล้ว publish ขึ้นชุมชนได้</p>
            <p style={{ marginTop: "1rem" }}>
              <Link href="/lab" className="btn btn-primary">
                เปิด Lab
              </Link>
            </p>
          </div>
          <div className="card">
            <h3>News</h3>
            <p>ข่าวเทคทั่วโลก โฟกัส wearable · robot · open-source — จุดประกายไอเดียแล้วลองใน Lab</p>
            <p style={{ marginTop: "1rem" }}>
              <Link href="/news" className="btn btn-ghost">
                อ่านข่าว
              </Link>
            </p>
          </div>
        </div>
      </section>
    </>
  );
}
