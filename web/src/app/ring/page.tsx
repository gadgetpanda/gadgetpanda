import Link from "next/link";
import { createMetadata } from "@/lib/seo";

export const metadata = createMetadata({
  title: "RING503PANDA",
  description: "Smart ring สำหรับ maker — PPG IMU HR SpO2 ผ่าน Python SDK",
  path: "/ring",
});

export default function RingPage() {
  return (
    <section className="section">
      <div className="shell">
        <p className="kicker">Product</p>
        <h2>RING503PANDA</h2>
        <p className="sub">Bluetooth LE · raw sensors · host-side Python</p>
        <div className="grid-2">
          <div className="card">
            <h3>เซ็นเซอร์</h3>
            <p>PPG · 6-axis IMU · heart rate / HRV · temperature · SpO₂ · battery</p>
          </div>
          <div className="card">
            <h3>เริ่มใช้</h3>
            <pre className="mono">{`pip install 'gadgetpanda[ui]'
gadgetpanda ring ui --demo`}</pre>
          </div>
        </div>
        <p style={{ marginTop: "1.2rem", display: "flex", gap: "0.6rem" }}>
          <Link className="btn btn-primary" href="/store">
            ซื้อ
          </Link>
          <Link className="btn btn-ghost" href="/lab?device=ring">
            สร้างโค้ด
          </Link>
          <Link className="btn btn-ghost" href="/world">
            ดูโปรเจกต์
          </Link>
        </p>
      </div>
    </section>
  );
}
