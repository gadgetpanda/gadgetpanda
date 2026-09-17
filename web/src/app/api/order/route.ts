import { getCloudflareContext } from "@opennextjs/cloudflare";
import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  const body = (await req.json()) as {
    name?: string;
    email?: string;
    phone?: string;
    product?: string;
    qty?: string | number;
    note?: string;
  };

  if (!body.name?.trim() || !body.email?.trim()) {
    return NextResponse.json({ error: "กรอกชื่อและอีเมล" }, { status: 400 });
  }

  try {
    const { env } = await getCloudflareContext({ async: true });
    const db = (env as CloudflareEnv).DB;
    const id = crypto.randomUUID();
    await db
      .prepare(
        `INSERT INTO store_leads (id, name, email, phone, product, qty, note, created_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
      )
      .bind(
        id,
        body.name.trim(),
        body.email.trim(),
        (body.phone || "").trim(),
        body.product || "ring",
        Number(body.qty) || 1,
        (body.note || "").trim(),
        Math.floor(Date.now() / 1000),
      )
      .run();
    return NextResponse.json({ ok: true, id });
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "บันทึกไม่สำเร็จ" },
      { status: 500 },
    );
  }
}
