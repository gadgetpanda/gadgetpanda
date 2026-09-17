"use client";

import { FormEvent, useState } from "react";

export function LabClient({
  initialDevice,
  initialPrompt,
}: {
  initialDevice: string;
  initialPrompt: string;
}) {
  const [device, setDevice] = useState(initialDevice);
  const [prompt, setPrompt] = useState(
    initialPrompt || "อ่าน heart rate จาก RING503PANDA แล้วพิมพ์ทุกครั้งที่เปลี่ยน",
  );
  const [code, setCode] = useState("");
  const [explain, setExplain] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const res = await fetch("/api/codegen", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ device, prompt }),
      });
      const data = (await res.json()) as { code?: string; explain?: string; error?: string };
      if (!res.ok) throw new Error(data.error || "สร้างโค้ดไม่สำเร็จ");
      setCode(data.code || "");
      setExplain(data.explain || "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "สร้างโค้ดไม่สำเร็จ");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid-2">
      <form className="stack card" onSubmit={onSubmit}>
        <label>
          Device profile
          <select value={device} onChange={(e) => setDevice(e.target.value)}>
            <option value="ring">RING503PANDA</option>
            <option value="dog">SoftDog</option>
            <option value="drone">FLOW-UFO</option>
          </select>
        </label>
        <label>
          งานที่อยากทำ
          <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} required />
        </label>
        <button className="btn btn-primary" disabled={busy} type="submit">
          {busy ? "กำลังสร้าง…" : "Generate with Gemini"}
        </button>
        {error ? <p className="notice">{error}</p> : null}
      </form>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>ผลลัพธ์</h3>
        {explain ? <p style={{ color: "var(--mute)" }}>{explain}</p> : null}
        <pre className="mono">{code || "# โค้ดจะโชว์ที่นี่"}</pre>
        <p className="notice" style={{ marginTop: "0.8rem" }}>
          รันด้วย: pip install &apos;gadgetpanda[ui]&apos;
        </p>
      </div>
    </div>
  );
}
