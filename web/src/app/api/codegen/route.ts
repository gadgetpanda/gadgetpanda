import { getCloudflareContext } from "@opennextjs/cloudflare";
import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const GROUNDING = `
You are Gadget Panda Lab. Write Python 3.11+ using ONLY the gadgetpanda package APIs below.
Never invent APIs. Prefer short runnable scripts. Reply in JSON: {"explain":"...thai short...","code":"..."}

Ring:
  from gadgetpanda import Ring
  ring = await Ring.find()
  ring.on("heart_rate", lambda s: print(s.bpm))
  ring.on("ppg", handler) / ring.on("imu", handler)
  async with ring:
      await ring.set_raw_enabled(True)

Dog:
  from gadgetpanda.dog import Dog, Action, Move
  async with Dog(address) as dog:
      await dog.action(Action.SIT_DOWN)
      await dog.hold_move(Move.FORWARD, seconds=1.0)

Drone:
  from gadgetpanda.drone import Drone
  async with Drone("192.168.1.1", model="flow") as drone:
      await drone.command("takeoff")
      await drone.hold_stick("forward", seconds=1.5)
      await drone.command("land")
`.trim();

const FALLBACK: Record<string, { explain: string; code: string }> = {
  ring: {
    explain: "ตัวอย่างสตรีม heart rate (โหมด fallback เมื่อยังไม่มี Gemini key)",
    code: `import asyncio
from gadgetpanda import Ring

async def main():
    ring = await Ring.find()
    ring.on("heart_rate", lambda s: print("HR", s.bpm))
    async with ring:
        await asyncio.Event().wait()

asyncio.run(main())`,
  },
  dog: {
    explain: "ตัวอย่างสั่ง SoftDog นั่ง",
    code: `import asyncio
from gadgetpanda.dog import Dog, Action

async def main():
    async with Dog("AA:BB:CC:DD:EE:FF") as dog:
        await dog.action(Action.SIT_DOWN)

asyncio.run(main())`,
  },
  drone: {
    explain: "ตัวอย่าง takeoff / land",
    code: `import asyncio
from gadgetpanda.drone import Drone

async def main():
    async with Drone("192.168.1.1", model="flow") as drone:
        await drone.command("takeoff")
        await asyncio.sleep(2)
        await drone.command("land")

asyncio.run(main())`,
  },
};

export async function POST(req: NextRequest) {
  const body = (await req.json()) as { device?: string; prompt?: string };
  const device = (body.device || "ring").toLowerCase();
  const prompt = (body.prompt || "").trim();
  if (!prompt) {
    return NextResponse.json({ error: "พิมพ์งานที่อยากทำก่อน" }, { status: 400 });
  }

  let env: CloudflareEnv | null = null;
  try {
    const ctx = await getCloudflareContext({ async: true });
    env = ctx.env as CloudflareEnv;
  } catch {
    env = null;
  }

  const apiKey = env?.GEMINI_API_KEY;
  if (!apiKey) {
    const fb = FALLBACK[device] || FALLBACK.ring;
    return NextResponse.json({ ...fb, mode: "fallback" });
  }

  const geminiRes = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${apiKey}`,
    {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        contents: [
          {
            role: "user",
            parts: [
              {
                text: `${GROUNDING}\n\nDevice: ${device}\nUser task: ${prompt}\nReturn JSON only.`,
              },
            ],
          },
        ],
        generationConfig: { temperature: 0.4 },
      }),
    },
  );

  if (!geminiRes.ok) {
    const text = await geminiRes.text();
    return NextResponse.json({ error: `Gemini error: ${text.slice(0, 200)}` }, { status: 502 });
  }

  const payload = (await geminiRes.json()) as {
    candidates?: Array<{ content?: { parts?: Array<{ text?: string }> } }>;
  };
  const raw = payload.candidates?.[0]?.content?.parts?.map((p) => p.text || "").join("\n") || "";
  const jsonMatch = raw.match(/\{[\s\S]*\}/);
  let explain = "สร้างจาก Gemini";
  let code = raw;
  if (jsonMatch) {
    try {
      const parsed = JSON.parse(jsonMatch[0]) as { explain?: string; code?: string };
      explain = parsed.explain || explain;
      code = parsed.code || code;
    } catch {
      /* keep raw */
    }
  }

  if (env?.DB) {
    await env.DB.prepare(
      `INSERT INTO lab_runs (id, device, prompt, code, created_at) VALUES (?, ?, ?, ?, ?)`,
    )
      .bind(crypto.randomUUID(), device, prompt, code, Math.floor(Date.now() / 1000))
      .run()
      .catch(() => undefined);
  }

  return NextResponse.json({ explain, code, mode: "gemini" });
}
