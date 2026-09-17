"use client";

import { FormEvent, useState } from "react";

export function OrderForm() {
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setStatus("");
    const form = new FormData(event.currentTarget);
    const payload = Object.fromEntries(form.entries());
    try {
      const res = await fetch("/api/order", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = (await res.json()) as { ok?: boolean; error?: string };
      if (!res.ok) throw new Error(data.error || "ส่งไม่สำเร็จ");
      setStatus("รับออเดอร์แล้ว — ทีมจะติดต่อกลับเร็วๆ นี้");
      event.currentTarget.reset();
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "ส่งไม่สำเร็จ");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="stack card" onSubmit={onSubmit}>
      <label>
        ชื่อ
        <input name="name" required placeholder="ชื่อ-นามสกุล" />
      </label>
      <label>
        อีเมล
        <input name="email" type="email" required placeholder="you@email.com" />
      </label>
      <label>
        โทร
        <input name="phone" placeholder="08x-xxx-xxxx" />
      </label>
      <label>
        สินค้า
        <select name="product" defaultValue="ring">
          <option value="ring">RING503PANDA</option>
          <option value="dog">SoftDog</option>
          <option value="drone">FLOW-UFO</option>
          <option value="lab10">Lab pack 10 วง</option>
        </select>
      </label>
      <label>
        จำนวน
        <input name="qty" type="number" min={1} defaultValue={1} />
      </label>
      <label>
        หมายเหตุ
        <textarea name="note" placeholder="ที่อยู่จัดส่ง / ต้องการใบกำกับภาษี" />
      </label>
      <button className="btn btn-primary" disabled={busy} type="submit">
        {busy ? "กำลังส่ง…" : "ส่งคำสั่งซื้อ"}
      </button>
      {status ? <p className="notice">{status}</p> : null}
    </form>
  );
}
