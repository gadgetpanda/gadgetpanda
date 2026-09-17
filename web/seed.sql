-- Seed demo content for PandaWorld + News (idempotent-ish via INSERT OR IGNORE)

INSERT OR IGNORE INTO community_projects (
  id, slug, title, summary, device, tags_json, code, author_name, likes, featured, created_at, updated_at
) VALUES
(
  'proj_hr',
  'live-heart-rate',
  'Live Heart Rate',
  'เชื่อม RING503PANDA แล้วพิมพ์ BPM แบบ realtime',
  'ring',
  '["ppg","hr","beginner"]',
  'import asyncio
from gadgetpanda import Ring

async def main():
    ring = await Ring.find()
    ring.on("heart_rate", lambda s: print("HR", s.bpm))
    async with ring:
        await asyncio.Event().wait()

asyncio.run(main())',
  'Gadget Panda',
  42,
  1,
  1726500000,
  1726500000
),
(
  'proj_ppg',
  'raw-ppg-csv',
  'Raw PPG → CSV',
  'สตรีม PPG ดิบและบันทึกเป็นไฟล์สำหรับงานวิจัย',
  'ring',
  '["ppg","research","csv"]',
  'import asyncio, csv, time
from gadgetpanda import Ring

async def main():
    ring = await Ring.find()
    rows = []
    ring.on("ppg", lambda samples: rows.extend((time.time(), s) for s in samples))
    async with ring:
        await ring.set_raw_enabled(True)
        await asyncio.sleep(10)
    with open("ppg.csv", "w", newline="") as f:
        csv.writer(f).writerows(rows)
    print("wrote", len(rows), "samples")

asyncio.run(main())',
  'Gadget Panda',
  28,
  1,
  1726500100,
  1726500100
),
(
  'proj_dog',
  'sit-on-command',
  'SoftDog Sit',
  'สั่ง SoftDog นั่งผ่าน BLE action',
  'dog',
  '["softdog","action"]',
  'import asyncio
from gadgetpanda.dog import Dog, Action

async def main():
    async with Dog("AA:BB:CC:DD:EE:FF") as dog:
        await dog.action(Action.SIT_DOWN)

asyncio.run(main())',
  'Gadget Panda',
  19,
  0,
  1726500200,
  1726500200
),
(
  'proj_drone',
  'hover-demo',
  'FLOW-UFO Hover',
  'Takeoff · hover · land บน Wi‑Fi craft',
  'drone',
  '["drone","fpv"]',
  'import asyncio
from gadgetpanda.drone import Drone

async def main():
    async with Drone("192.168.1.1", model="flow") as drone:
        await drone.command("takeoff")
        await asyncio.sleep(2)
        await drone.command("land")

asyncio.run(main())',
  'Gadget Panda',
  15,
  0,
  1726500300,
  1726500300
);

INSERT OR IGNORE INTO news_items (
  id, title, summary, source_name, source_url, topics_json, published_at, created_at
) VALUES
(
  'news_1',
  'Open-source wearables push raw PPG into maker hands',
  'นักพัฒนากำลังเปิดสเปกเซ็นเซอร์แทนแอปสุขภาพปิดตาย — ตรงกับแนวทาง Gadget Panda',
  'Hackaday',
  'https://hackaday.com/',
  '["wearable","ppg","open-source"]',
  1726500400,
  1726500400
),
(
  'news_2',
  'Edge AI on tiny robots: why on-device still matters',
  'หุ่นยนต์ขนาดเล็กใช้โมเดลบนอุปกรณ์มากขึ้นสำหรับ latency และการควบคุม',
  'IEEE Spectrum',
  'https://spectrum.ieee.org/',
  '["robot","edge-ai"]',
  1726500500,
  1726500500
),
(
  'news_3',
  'BLE + Python remains the fastest path from idea to prototype',
  'Host-side Python ยังเป็นทางลัดของ Lab และ senior project',
  'Adafruit Blog',
  'https://blog.adafruit.com/',
  '["ble","python","maker"]',
  1726500600,
  1726500600
);
