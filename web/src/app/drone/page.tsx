import Link from "next/link";
import { createMetadata } from "@/lib/seo";

export const metadata = createMetadata({
  title: "FLOW-UFO",
  description: "FLOW-UFO mini drone — Wi-Fi stick loop, takeoff/land, FPV remote",
  path: "/drone",
});

export default function DronePage() {
  return (
    <section className="section">
      <div className="shell">
        <p className="kicker">Product</p>
        <h2>FLOW-UFO</h2>
        <p className="sub">Wi‑Fi craft · stick · FPV</p>
        <pre className="mono">{`gadgetpanda drone ui --demo`}</pre>
        <p style={{ marginTop: "1.2rem", display: "flex", gap: "0.6rem" }}>
          <Link className="btn btn-primary" href="/store">
            สอบถามราคา
          </Link>
          <Link className="btn btn-ghost" href="/lab?device=drone">
            สร้างโค้ด
          </Link>
        </p>
      </div>
    </section>
  );
}
