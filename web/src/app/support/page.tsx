import { createMetadata } from "@/lib/seo";

export const metadata = createMetadata({
  title: "Support",
  description: "FAQ จาก Inbox จริง — ราคา สั่งซื้อ SDK กันน้ำ OS",
  path: "/support",
});

const faqs = [
  {
    q: "PANDA RING ราคาเท่าไหร่?",
    a: "Developer Edition 4,490 บาท · Lab/มหาวิทยาลัย 10 วงขึ้นไป 3,490 บาท/วง",
  },
  {
    q: "ต้องจ่ายรายเดือนไหม?",
    a: "ไม่ต้อง — ซื้อครั้งเดียว ใช้ SDK โอเพนซอร์สได้",
  },
  {
    q: "สั่งซื้อได้ที่ไหน?",
    a: "สั่งผ่านหน้า Store บน gadgetpanda.app หรือ Inbox เพจ Gadget Panda",
  },
  {
    q: "เขียนโค้ดด้วยภาษาอะไร?",
    a: "Python 3.11+ ผ่าน pip install gadgetpanda — มี UI และตัวอย่างบน GitHub",
  },
  {
    q: "รองรับระบบปฏิบัติการอะไร?",
    a: "Mac · Linux · Windows · Raspberry Pi (BLE/Wi‑Fi จริง บนเครื่อง)",
  },
  {
    q: "มีไมค์หรือลำโพงไหม?",
    a: "แหวนไม่มีไมค์/ลำโพง — โฟกัสเซ็นเซอร์และสตรีมข้อมูล",
  },
];

export default function SupportPage() {
  return (
    <section className="section">
      <div className="shell">
        <p className="kicker">Support</p>
        <h2>ช่วยเหลือ</h2>
        <p className="sub">คำถามที่ลูกค้าทักเพจบ่อยที่สุด</p>
        <div className="faq">
          {faqs.map((item) => (
            <details key={item.q}>
              <summary>{item.q}</summary>
              <p>{item.a}</p>
            </details>
          ))}
        </div>
        <p className="notice" style={{ marginTop: "1.5rem" }}>
          เอกสาร:{" "}
          <a href="https://github.com/gadgetpanda/gadgetpanda" rel="noreferrer">
            GitHub
          </a>{" "}
          · License:{" "}
          <a href="https://lib.gadgetpanda.app" rel="noreferrer">
            lib.gadgetpanda.app
          </a>
        </p>
      </div>
    </section>
  );
}
