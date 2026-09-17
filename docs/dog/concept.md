# Fun Dog · Maker Concept

**สุนัขเป็นของเล่น — คำสั่งเป็นของคุณ**

ชั้นโฮสต์ BLE สำหรับหุ่นสุนัขสนุกหลายรุ่น (เริ่มจาก X1)  
คู่ขนานกับแหวน RING503PANDA — **คนละโปรโตคอล**

```text
โปรเจกต์ของ Maker
  ท่าทาง / เกม / MQTT / โปรแกรมลำดับ
        ▲
gadgetpanda.dog  (MIT, Python)
  scan · connect · action · move · hold_move · run_program · raw_write
        ▲
X1 / รุ่นอื่น ๆ
  BLE GATT (FFE5/FFE8/FFE9) · remote `0xB1` · program `0xB2`
```

## เป็น / ไม่เป็น

| เป็น | ไม่เป็น |
|---|---|
| host สั่งท่าผ่าน BLE | โคลนแอปมือถือสำเร็จรูป |
| capability ต่อรุ่น | สมมติว่ารุ่นเดียวทำได้ครบ |
| โปรโตคอลโฮสต์เปิดใน docs | ล็อกไว้ในแอปปิด |
| program queue + hold-move | สตรีมเสียง / อัปโหลดใบหน้า |

## หลายรุ่น

รุ่นใหม่ = เพิ่ม `DogProfile` + `capabilities` + `opcodes`  
รุ่นที่ทำได้น้อยกว่าจะได้ `UnsupportedCapability` ชัดเจน

รีโมทเว็บ: `gadgetpanda dog ui` (ต้อง `pip install -e ".[ui]"`)

ดูรายละเอียดใน [protocol.md](protocol.md)
