# RING503PANDA / Gadget Panda Ring Protocol

เอกสารนี้อธิบายโปรโตคอล BLE ที่โฮสต์ Gadget Panda ใช้คุยกับแหวน RING503PANDA

อ้างอิงการทำงานจากเฟรมบนสาย BLE และมาตรฐาน Bluetooth SIG

ค่าในช่องคำสั่งของแหวนเป็น **big-endian** ยกเว้น Heart Rate มาตรฐาน (`0x2A37`) ที่เป็น little-endian ตามสเปก SIG។

---

## 1. Overview

ชั้นสื่อสารมี 2 กลุ่ม

1. **Bluetooth SIG** — Heart Rate, Battery, Device Information
2. **Fitness command channel** — ช่องคำสั่งของโมดูล แอปเขียน TX แหวนตอบ/สตรีมทาง RX

```text
App  --write-->  TX  AAE28F02
App  <--notify-- RX  AAE28F01
App  <--notify-- Heart Rate  2A37
App  <--notify-- Battery     2A19
```

ชื่อสินค้าคือ `RING503PANDA` / `RING503nPANDA` ตัวโฮสต์กรองด้วยชื่อนี้ และยังจับชื่อโฆษณา BLE ของโมดูลอยู่

---

## 2. GATT map

### 2.1 Required

เครื่องที่ไม่ครบ Heart Rate + Fitness service โฮสต์ควรถือว่าไม่รองรับ

| Service | UUID | Characteristic | UUID | Properties |
|---|---|---|---|---|
| Heart Rate | `0000180D-0000-1000-8000-00805f9b34fb` | Heart Rate Measurement | `00002A37-0000-1000-8000-00805f9b34fb` | Notify |
| Fitness | `AAE28F00-71B5-42A1-8C3C-F9CF6AC969D0` | RX | `AAE28F01-71B5-42A1-8C3C-F9CF6AC969D0` | Notify |
| | | TX | `AAE28F02-71B5-42A1-8C3C-F9CF6AC969D0` | Write / Write Command |

TX: ถ้ามี property Write (`0x08`) ใช้ Write Request  
ถ้ามีแค่ Write Command (`0x04`) ก็ใช้ได้เช่นกัน

### 2.2 Optional

| Service | UUID | Characteristic | UUID | ใช้ทำอะไร |
|---|---|---|---|---|
| Battery | `0000180F-0000-1000-8000-00805f9b34fb` | Battery Level | `00002A19-0000-1000-8000-00805f9b34fb` | Read + Notify, หน่วย % |
| Device Information | `0000180A-0000-1000-8000-00805f9b34fb` | System ID | `00002A23-…` | Read |
| | | Model Number | `00002A24-…` | Read |
| | | Serial Number | `00002A25-…` | Read |
| | | Firmware Revision | `00002A26-…` | Read |
| | | Hardware Revision | `00002A27-…` | Read |
| | | Software Revision | `00002A28-…` | Read |
| | | Manufacturer | `00002A29-…` | Read |

หลังเชื่อมต่อ โฮสต์อ่าน DIS ทั้งชุด แล้วเปิด Battery notify

---

## 3. Connection sequence

```text
1. Scan BLE (ไม่กรอง UUID, กรองชื่อภายหลัง)
2. Connect (autoConnect = false)
3. Discover services
4. Read Device Information + Battery
5. Enable Battery notify
6. Request MTU 517
7. Enable Heart Rate notify (2A37)
8. Enable Fitness RX notify
9. Device ready → ส่งตั้งเวลา UTC (CMD 0x08) ทันที
10. ค่อยยิงคำสั่งอื่น
```

ประวัติสุขภาพ / หัวใจ / PPG เป็นสตรีมหลายแพ็กเก็ต ต้องเคลียร์บัฟเฟอร์ฝั่งโฮสต์ก่อนยิงคำสั่งใหม่.

---

## 4. Gadget Panda frame

TX และ RX ใช้โครงเดียวกัน.

```text
Offset  Size  Name     Description
0       1     SOF      เสมอ 0xFF
1       1     LEN      ความยาวทั้งแพ็กเก็ต รวม checksum
2       1     CMD      opcode
3       N     PAYLOAD  อาจว่าง
LEN-1   1     CHK      checksum
```

ความยาวขั้นต่ำคือ 4 ไบต์ (`FF LEN CMD CHK`).

ตรวจความถูกต้องฝั่งรับ: `value[1] == packet.length`. ไม่ตรงให้ทิ้งแพ็กเก็ต.

### 4.1 Checksum

คำนวณจากทุกไบต์ **ยกเว้นตัว CHK**.

```text
sum = ผลบวกแบบ signed int8 (เทียบเท่า Java `byte`)
CHK = ((-sum) XOR 0x3A) & 0xFF
```

ตัวอย่าง Python

```python
def checksum(data: bytes) -> int:
    total = 0
    for b in data:
        total += b - 256 if b > 127 else b
    return ((-total) ^ 0x3A) & 0xFF


def pack(cmd: int, payload: bytes = b"") -> bytes:
    body = bytes([0xFF, 4 + len(payload), cmd & 0xFF]) + payload
    return body + bytes([checksum(body)])
```

ตัวอย่างแพ็กเก็ตถามก้าว (payload ว่าง)

```text
FF 04 15 CHK
```

คำสั่ง DFU สร้างแพ็กเก็ต 4 ไบต์ แล้วใส่ checksum ทับไบต์สุดท้ายในขณะที่ไบต์นั้นยังเป็น `0x00` ดังนั้นผลรวมรวม `0x00` นั้นด้วย

### 4.2 Integer formats

| รูปแบบ | Endian | ความหมาย |
|---|---|---|
| unsigned ในเฟรม fitness | BE | ค่าทั่วไป / timestamp 4 ไบต์ |
| IMU raw | BE signed 16-bit | acc / gyro |
| Heart Rate `2A37` | LE | ตาม Bluetooth SIG |

---

## 5. Time

แหวนเก็บเวลาเป็น **วินาที** แบบ zone-adjusted

โฮสต์แปลงก่อนส่งและหลังรับด้วย timezone ของเครื่อง

```text
getZoneUTC()
  now_ms + zoneOffset + dstOffset
  → หาร 1000 ได้วินาที

restoreZoneUTC(stamp_sec)
  stamp_sec * 1000 − zoneOffset − dstOffset
  → millisecond epoch ของเครื่อง
```

โฮสต์อื่นต้องแปลงให้สอดคล้องกับโซนเวลาของผู้ใช้ ไม่เช่นนั้นประวัติจะเลื่อนชั่วโมง

แท็กจบสตรีมประวัติหลายชนิดคือ `0xFFFFFFFF` ที่ offset 3.

---

## 6. TX commands

ไบต์ติดลบใน Java แสดงเป็น unsigned ด้วย.

| CMD | Hex | Java | Payload | API | ความหมาย |
|---|---|---|---|---|---|
| 3 | `0x03` | 3 | `00` | `getUserInfo()` | อ่านโปรไฟล์ |
| 4 | `0x04` | 4 | 9 bytes | `setUserInfo(...)` | ตั้งโปรไฟล์ |
| 5 | `0x05` | 5 | `02` | `getHistoryOfSleep()` | ประวัติการนอน |
| 8 | `0x08` | 8 | UTC `u32` | `setUTCTime()` | ตั้งนาฬิกา |
| 13 | `0x0D` | 13 | `04` | `setSportModeEnabled(true)` | เปิด Sport mode |
| 19 | `0x13` | 19 | ว่าง | `getHealthData()` | อ่านสุขภาพ |
| 21 | `0x15` | 21 | ว่าง | `getSportData()` | อ่านก้าว / ระยะ / แคล |
| 22 | `0x16` | 22 | `00` | `getHistoryOfSport()` | ประวัติกีฬา ~7 วัน |
| 39 | `0x27` | 39 | ไม่มี (แพ็กเก็ต 4B) | `dfuMode()` | เข้าโหมด DFU |
| 55 | `0x37` | 55 | `en 00` | `setBloodOxygen(en)` | เปิด/ปิด SpO2 |
| 56 | `0x38` | 56 | ว่าง | `getTemperatureData()` | อ่านอุณหภูมิ |
| 116 | `0x74` | 116 | `00 0C` | `setSportModeEnabled(false)` | ปิด Sport mode |
| 145 | `0x91` | -111 | UTC `u32` | `getHistoryOfHealthData(begin)` | ประวัติสุขภาพตั้งแต่เวลา |
| 146 | `0x92` | -110 | UTC `u32` | `getHeartRateHistoryData(begin)` | ประวัติหัวใจตั้งแต่เวลา |
| 148 | `0x94` | -108 | UTC `u32` | `getPPGHistoryData(begin)` | ประวัติ PPG ตั้งแต่เวลา |
| 150 | `0x96` | -106 | ปี `u16` + เดือน + วัน | `setUserBirthday(...)` | ตั้งวันเกิด |
| 151 | `0x97` | -105 | `00` | `getUserBirthday()` | อ่านวันเกิด |
| 152 | `0x98` | -104 | ดูด้านล่าง | raw 6D/PPG | ถามสถานะ / เปิดสตรีม |
| 243 | `0xF3` | -13 | ว่าง | `restoration()` | Factory restore |

### 6.1 Payload รายคำสั่ง

**ตั้งโปรไฟล์ `0x04`**

```text
age:u8
sex:u8          0 = หญิง, 1 = ชาย
weight:u8       กิโลกรัม
height:u8       เซนติเมตร
userId:u40      big-endian, 5 ไบต์ (เช่นเบอร์โทร)
```

**วันเกิด `0x96`**

```text
year:u16 BE
month:u8
day:u8
```

**Sport mode**

```text
เปิด:  CMD 0x0D   payload 04
ปิด:   CMD 0x74   payload 00 0C
```

**SpO2 `0x37`**

```text
enabled:u8      1 = เปิด, 0 = ปิด
reserved:u8     0
```

**Raw 6D/PPG `0x98`**

```text
ถามสถานะ:   payload 00
ตั้งค่า:      payload 01  <enabled>
  enabled 1 = เปิดสตรีม, 0 = ปิด
```

**ประวัติที่ต้องส่งเวลาเริ่ม**

`0x91` / `0x92` / `0x94` ส่ง `utc2Bytes(getZoneUTC(beginMs))` เป็น `u32` BE.

---

## 7. RX modes

ไบต์ที่ offset 2 ของเฟรมคือ mode. ส่วนใหญ่สะท้อน CMD ที่ส่งไป.  
Offset ในตารางนับจากต้นแพ็กเก็ต รวม `FF LEN CMD`.

| Mode | Hex | ความหมาย | หมายเหตุ |
|---|---|---|---|
| 3 | `0x03` | โปรไฟล์ผู้ใช้ | |
| 5 | `0x05` | ประวัติการนอน | ย่อยที่ offset 3 |
| 19 | `0x13` | สุขภาพ realtime | |
| 21 | `0x15` | กีฬา realtime | |
| 22 | `0x16` | ประวัติกีฬา | SDK reverse รายการก่อนส่งต่อ |
| 33 | `0x21` | รายการ stamp หัวใจแบบเก่า | สะสมจนเจอ `FFFFFFFF` |
| 34 | `0x22` | ข้อมูล HR ต่อเนื่องแบบเก่า | |
| 35 | `0x23` | จบชุด HR แบบเก่า | |
| 55 | `0x37` | SpO2 realtime | ยาวอย่างน้อย 8 ไบต์ |
| 56 | `0x38` | อุณหภูมิ realtime | |
| 57 | `0x39` | ประวัติ SpO2 | มี parser, ไม่มี API เรียกใน 1.0.4 |
| 58 | `0x3A` | ประวัติอุณหภูมิ | มี parser, ไม่มี API เรียกใน 1.0.4 |
| 145 | `0x91` | ประวัติสุขภาพ | เรคคอร์ด 18B, จบที่ `FFFFFFFF` |
| 146 | `0x92` | ประวัติหัวใจ | progress / total |
| 148 | `0x94` | ประวัติ PPG | เรคคอร์ด 62B |
| 151 | `0x97` | วันเกิด | |
| 152 | `0x98` | สถานะ raw | |
| 153 | `0x99` | สตรีม 6D + PPG | แหวนยิงเองหลังเปิด `0x98` |

โหมด 33 / 34 / 35 เป็นสเต็กเก่า. API สาธารณะของ 1.0.4 ใช้ `0x92` แทน.

---

## 8. RX payload layouts

### 8.1 User info — mode `0x03`

```text
[5]      age:u8
[6]      sex:u8
[7]      weight:u8
[8]      height:u8
[9..13]  userId:u40 BE
```

### 8.2 Birthday — mode `0x97`

```text
[3..4]  year:u16 BE
[5]     month:u8
[6]     day:u8
```

### 8.3 Sport realtime — mode `0x15`

```text
[3..5]   step:u24
[6..8]   distance:u24     เมตร = ค่า / 100
[9..11]  calorie:u24      kcal = ค่า / 10
```

ตัวอย่างในแอป: `distance / 100f` เมตร, `calorie / 10f` kcal.

### 8.4 Sport history — mode `0x16`

ตัดหัว `FF LEN CMD` และไบต์ checksum ออก แล้วหั่นทีละ 10 ไบต์.

```text
utc:u32 BE
step:u24 BE
calorie:u24 BE
```

ไม่มีระยะในประวัติ. SDK กลับลำดับรายการก่อน callback.

### 8.5 Health realtime — mode `0x13`

```text
[3] vo2max:u8
[4] breathRate:u8
[5] emotion:u8
[6] stress:u8
[7] stamina:u8
```

### 8.6 Temperature realtime — mode `0x38`

```text
[3..4]  ambient:u16 / 10.0   °C
[5..6]  wrist:u16 / 10.0     °C
[7..8]  body:u16 / 10.0      °C
```

### 8.7 SpO2 realtime — mode `0x37`

ถ้า `LEN < 8` ทิ้งแพ็กเก็ต.

```text
[3] enabled:u8     1 = กำลังวัด
[4] spo2:u8        เปอร์เซ็นต์
[7] onWrist:u8     0 = ถอด, 1 = สวม
```

### 8.8 Sleep history — mode `0x05`

ไบต์ที่ offset 3 เป็นคำสั่งย่อย.

| Sub | ความหมาย |
|---|---|
| `0x03` | บล็อกข้อมูล |
| `0xFF` | จบชุด แล้วส่งรายการสะสม |

บล็อกข้อมูลเดินทีละเรคคอร์ด

```text
count:u8
utc:u32 BE
actions[count]:u8
```

แต่ละ `action` เท่ากับช่วง **5 นาที** (`utc + index * 300_000` ms ในแอปตัวอย่าง).

การตีความใน sample:

- `action > 20` → ตื่น
- ค่าต่ำ / `0` → หลับ (ตื้น / ลึก แยกต่อในแอป)

### 8.9 Health history — mode `0x91`

ถ้า offset 3 เป็น `0xFFFFFFFF` ถือว่าจบชุด.

มิฉะนั้นตัดหัว 3 ไบต์และ checksum แล้วหั่นทีละ **18 ไบต์**.

```text
Offset  Size  Field
0       4     start:u32
4       4     stamp:u32          แปลงด้วย restoreZoneUTC
8       1     type
9       1     stressLevel
10      1     breathRate
11      1     vo2max
12      1     emotionLevel
13      1     stamina
14      1     heartRate
15      1     bloodOxygen
16      2     temperature:u16 / 10.0
```

ส่ง callback ทีละเรคคอร์ด พร้อมเลขลำดับที่โฮสต์นับเอง.

### 8.10 Heart rate history — mode `0x92`

```text
[3..4]  total:u16
[5..6]  progress:u16
จาก offset 7 ถึงก่อน checksum: เรคคอร์ดละ 5 ไบต์
  stamp:u32
  heartRate:u8
```

`progress == total` คือจบ. แต่ละแพ็กเก็ตส่งรายการย่อยพร้อมความคืบหน้า.

### 8.11 PPG history — mode `0x94`

ถ้า offset 3 เป็น `0xFFFFFFFF` ถือว่าจบ.

มิฉะนั้น

```text
[3..4]  total:u16
[5..6]  progress:u16
จาก offset 7: เรคคอร์ดละ 62 ไบต์
```

เรคคอร์ด 62 ไบต์

```text
stamp:u32
isWear:u8          1 = สวม
แล้ว 57 ไบต์ = สูงสุด 3 สล็อต × 19 ไบต์
```

สล็อต 19 ไบต์

```text
minCurrent:u8
maxCurrent:u8
minPd0:u32
minPd1:u32
maxPd0:u32
maxPd1:u32
tiaGain:u8
```

### 8.12 SpO2 history — mode `0x39` (parser อย่างเดียว)

| Sub at offset 3 | ความหมาย |
|---|---|
| `0x01` | ข้อมูล เรคคอร์ดละ 6 ไบต์: `utc:u32 + spo2:u8 + onWrist:u8` |
| `0xFF` | จบชุด |

### 8.13 Temperature history — mode `0x3A` (parser อย่างเดียว)

| Sub at offset 3 | ความหมาย |
|---|---|
| `0x01` | บล็อก: `utc:u32 + count:u8 + count × (temp:u16 / 10.0)` |
| `0xFF` | จบชุด |

### 8.14 Legacy HR stamps — mode `0x21`

สะสมแพ็กเก็ตที่ offset 3 ไม่ใช่ `0xFFFFFFFF`.  
เมื่อเจอแท็กจบ หั่น payload เป็น `u32` ทีละตัวเป็น stamp.

### 8.15 Legacy HR values — mode `0x22` / `0x23`

- `0x22`: แพ็กเก็ตแรกเก็บ stamp ที่ offset 3 แล้วสะสมไบต์ HR
- `0x23`: ไล่ค่า HR จากไบต์ที่ 4 ของแต่ละชิ้น เพิ่มเวลาทีละ `mInterval` วินาที (ค่าเริ่ม 600)

API ใหม่ไม่ใช้คู่โหมดนี้.

### 8.16 Raw status — mode `0x98`

```text
[4] enabled:u8     1 = กำลังสตรีม
```

### 8.17 Raw 6D + PPG stream — mode `0x99`

```text
[3]           frame:u8
[4..7]        stamp:u32
[8]           n6d:u8                 จำนวนไบต์ของก้อน 6D
[9 .. 9+n6d)  raw6d
[9+n6d]       nppg:u8                จำนวนไบต์ของก้อน PPG
[10+n6d]      flag:u8
[11+n6d ..)   ppg                   ความยาวนับตาม nppg
```

ถ้า `n6d == 0` และ `nppg == 0` ส่งรายการว่าง.

**6D** ตัวอย่างละ 12 ไบต์ ค่า `int16` big-endian

```text
accX  accY  accZ  gyroX  gyroY  gyroZ
```

**PPG** ตัวอย่างละ 3 ไบต์ big-endian เป็นค่าหนึ่งตัว ใช้ `flag` ร่วมทั้งก้อน.

โหมดนี้เป็นจุดที่ Maker ใช้ทำ gesture / interactive. ไม่มี opcode ท่าทางสำเร็จรูป.

---

## 9. Bluetooth SIG: Heart Rate

Characteristic `0x2A37` ตาม Heart Rate Service.

```text
flags:u8
  bit0     0 = HR uint8, 1 = HR uint16
  bit1-2   sensor contact
  bit3     energy expanded present
  bit4     RR intervals present
heartRate
[energyExpanded:u16]
[RR:u16...]            หน่วย 1/1024 วินาที, little-endian
```

SDK คำนวณ HRV ฝั่งโฮสต์ ไม่ได้มาจาก opcode Gadget Panda.

- สะสม RR ที่ผ่านตัวกรอง `500 … 1200`
- ครบ 30 ค่า → HRV = ส่วนเบี่ยงเบนมาตรฐาน (แบบ SDNN) ของ 29 ค่าล่าสุด
- ไม่มี RR ติดต่อกันเกิน 60 ครั้ง → ส่ง HRV `0` และล้างบัฟเฟอร์

---

## 10. DFU

```text
TX: FF 04 27 CHK
```

หลังเข้าโหมดอัปเกรด อุปกรณ์ DFU ใช้ที่อยู่ MAC เดิมแต่ **ไบต์สุดท้าย + 1**.

```text
AA:BB:CC:DD:EE:10  →  AA:BB:CC:DD:EE:11
```

ชื่อโฆษณามักเป็น `DFU_<ชื่อเดิม>` หรือลงท้ายด้วย `U`.  
การอัปโหลด firmware ใช้ Nordic DFU (`no.nordicsemi.android:dfu`) คนละชั้นกับเฟรม Gadget Panda.

---

## 11. Host buffer types

ก่อนดึงประวัติ SDK เรียก `clearType(type)`.

| Type | ค่า | ใช้กับ |
|---|---|---|
| `TYPE_SPORT` | 2 | ประวัติกีฬา |
| `TYPE_HEART` | 4 | legacy HR stamps |
| `TYPE_HEARTS` | 6 | legacy HR values |
| `TYPE_SLEEP` | 8 | การนอน |
| `TYPE_HEALTH` | 16 | ประวัติสุขภาพ |
| `TYPE_HEART_RATE` | 18 | ประวัติหัวใจ `0x92` |
| `TYPE_PPG` | 20 | ประวัติ PPG |

---

## 12. What this protocol does not include

- ไม่มีคำสั่ง gesture สำเร็จรูป ต้องตีความ 6D เอง
- ไม่มีเมธอดสาธารณะสำหรับขอประวัติ SpO2 / อุณหภูมิ แม้ RX parser จะรองรับ mode `0x39` / `0x3A`

---

## 13. Suggested implementation order

1. สแกน + เชื่อม + อ่าน Battery / DIS
2. เปิด Heart Rate notify
3. ส่ง UTC `0x08`
4. ทดลอง `0x15` ก้าว และ `0x38` อุณหภูมิ
5. เปิด raw `0x98` แล้ว parse `0x99`
6. ค่อยทำประวัติ `0x16` / `0x05` / `0x91` / `0x92` / `0x94`

