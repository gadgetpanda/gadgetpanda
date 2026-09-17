import Link from "next/link";
import { createMetadata } from "@/lib/seo";

export const metadata = createMetadata({
  title: "SoftDog",
  description: "SoftDog X1 — BLE actions, move hold, program queue, web remote",
  path: "/dog",
});

export default function DogPage() {
  return (
    <section className="section">
      <div className="shell">
        <p className="kicker">Product</p>
        <h2>SoftDog (X1)</h2>
        <p className="sub">เล่น · โปรแกรม · รีโมตเว็บ</p>
        <pre className="mono">{`gadgetpanda dog ui --demo`}</pre>
        <p style={{ marginTop: "1.2rem", display: "flex", gap: "0.6rem" }}>
          <Link className="btn btn-primary" href="/store">
            สอบถามราคา
          </Link>
          <Link className="btn btn-ghost" href="/lab?device=dog">
            สร้างโค้ด
          </Link>
        </p>
      </div>
    </section>
  );
}
