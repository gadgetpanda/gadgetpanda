import { createMetadata } from "@/lib/seo";
import { LabClient } from "./LabClient";

export const metadata = createMetadata({
  title: "Lab",
  description: "Panda Lab — Gemini สร้างโค้ด gadgetpanda สำหรับ Ring SoftDog FLOW-UFO",
  path: "/lab",
});

export default async function LabPage({
  searchParams,
}: {
  searchParams: Promise<{ prompt?: string; device?: string }>;
}) {
  const params = await searchParams;
  return (
    <section className="section">
      <div className="shell">
        <p className="kicker">Bambu Studio → Panda Lab</p>
        <h2>Lab</h2>
        <p className="sub">
          พิมพ์งานที่อยากทำ — ได้โค้ด Python ที่ใช้แพ็กเกจ gadgetpanda จริง (ต้องตั้ง GEMINI_API_KEY)
        </p>
        <LabClient initialDevice={params.device || "ring"} initialPrompt={params.prompt || ""} />
      </div>
    </section>
  );
}
