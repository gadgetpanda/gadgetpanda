# V66 / KY UFO Wi‑Fi drone

ชั้น `gadgetpanda.drone` สำหรับโดรนมินิสาย **V66** (แอป KY UFO)  
คนละโปรโตคอลกับแหวน (BLE) และ SoftDog (BLE)

## แนวคิด

1. ต่อ Wi‑Fi hotspot ของโดรนด้วยมือ (เช่น `KY_UFO_…`)
2. โฮสต์คุย UDP ไป `192.168.1.1:7099`
3. ส่งเฟรมสติ๊กซ้ำ ~ทุก 50 ms + heartbeat `01 01`

## สิบนาทีแรก

```bash
pip install -e ".[ui]"
# บังคับ join hotspot จาก CLI (macOS networksetup / Linux nmcli)
gadgetpanda drone wifi status
gadgetpanda drone wifi join KY_UFO_xxxx            # เปิดมักไม่มีรหัส
gadgetpanda drone wifi join KY_UFO_xxxx --password secret

gadgetpanda drone connect --wifi KY_UFO_xxxx
gadgetpanda drone ui --wifi KY_UFO_xxxx
# หรือ demo โดยไม่ต่อ Wi‑Fi จริง:
gadgetpanda drone connect --demo
gadgetpanda drone ui --demo
```

รีโมท FPV (`http://127.0.0.1:8767`) แสดง RTSP เป็นพื้นหลัง  
`pip install 'gadgetpanda[ui]'` จะได้ `imageio-ffmpeg` (binary ใน wheel) อัตโนมัติ  
ถ้าเครื่องมี `ffmpeg` ใน PATH อยู่แล้ว จะใช้ตัวนั้นก่อน

```bash
pip install -e ".[ui]"
gadgetpanda drone ui 192.168.1.1 --model flow
```

## สาเหตุที่สั่งแล้วไม่ขยับ (พบบ่อย)

1. **Mac ยังไม่ได้อยู่บน Wi‑Fi โดรน** — ต้องเป็น `FLOW-UFO-…` ไม่ใช่ Wi‑Fi บ้าน/ออฟฟิศ  
   ถ้า tick พังด้วย `Errno 49 Can't assign requested address` = ยังไม่ on-link กับ `192.168.1.1`  
   ตรวจ: `gadgetpanda drone wifi status` ต้องเห็น SSID โดรน และ `tcp:7070` เปิดได้
2. **รุ่น FLOW ใช้เฟรม GL** — ใช้ `--model flow` พร้อม **fixed-height** เปิดอัตโนมัติ
3. **ไม่มีภาพกล้อง** — สาเหตุเดียวกัน (RTSP `:7070` อยู่บน AP โดรนเท่านั้น) + ต้องมี ffmpeg (`pip install 'gadgetpanda[ui]'`)

```bash
# 1) join hotspot
gadgetpanda drone wifi join "FLOW-UFO-xxxx"
gadgetpanda drone wifi status   # ต้องขึ้น FLOW-UFO-…

# 2) ตรวจว่าเกตเวย์ตอบ
gadgetpanda drone scan          # ต้องมี 192.168.1.1 [up]

# 3) ควบคุม
gadgetpanda drone connect --wifi "FLOW-UFO-xxxx" --model flow
gadgetpanda drone ui --wifi "FLOW-UFO-xxxx" --model flow
```
