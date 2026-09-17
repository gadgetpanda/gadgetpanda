import { createMetadata } from "@/lib/seo";
import { OrderForm } from "./OrderForm";

export const metadata = createMetadata({
  title: "Store",
  description: "ราคา RING503PANDA Developer Edition และแพ็ก Lab — สั่งซื้อในไทย",
  path: "/store",
});

export default function StorePage() {
  return (
    <section className="section">
      <div className="shell">
        <p className="kicker">Store</p>
        <h2>สั่งซื้อ PANDA RING</h2>
        <p className="sub">ราคาชัดเจน · ไม่มีรายเดือน · SDK โอเพนซอร์สฟรี</p>

        <div className="grid-2">
          <div className="price-box">
            <div className="kicker">Developer Edition</div>
            <p className="amount">฿4,490</p>
            <p>แหวน 1 วง + pip SDK + เข้า Lab / PandaWorld</p>
          </div>
          <div className="card">
            <div className="kicker">University / Lab</div>
            <p className="amount" style={{ fontSize: "2rem", margin: "0.3rem 0" }}>
              ฿3,490<span style={{ fontSize: "1rem" }}>/วง</span>
            </p>
            <p>สั่ง 10 วงขึ้นไป — เหมาะ senior project และ research lab</p>
          </div>
        </div>

        <div style={{ marginTop: "2rem" }}>
          <h3 style={{ fontFamily: "var(--font-display)" }}>ฟอร์มสั่งซื้อ</h3>
          <p className="sub">ทีมจะตอบยืนยันสต็อกและช่องทางชำระ (โอน / COD)</p>
          <OrderForm />
        </div>
      </div>
    </section>
  );
}
