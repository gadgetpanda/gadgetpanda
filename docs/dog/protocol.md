# Fun Dog · Host Protocol

มุมโฮสต์ Python สำหรับ SmartDog / X1

## 1. Overview

- API: `Dog.scan` → `connect` → `raw_write` / `action` / `move` / `hold_move` / `run_program`
- รุ่น: `DogProfile` (`x1`, `generic`, …)
- ตารางไบต์: `gadgetpanda.dog.protocol`

## 2. GATT

| Role | UUID |
|---|---|
| Service | `0000FFE5-0000-1000-8000-00805F9B34FB` |
| Notify | `0000FFE8-0000-1000-8000-00805F9B34FB` |
| Write | `0000FFE9-0000-1000-8000-00805F9B34FB` |

gadgetpanda เขียนไบต์ดิบไป FFE9

## 3. Frame format

### 3.1 Remote — prefix `0xB1`

`[0xB1, operation, action]`

| Verb | Hex |
|---|---|
| Forward / Backward / Turn L / Turn R | `b10100` / `b10200` / `b10300` / `b10400` |
| Stop | `b10500` |
| Greet … Swim (action 1…17) | `b10001` … `b10011` |

Hold-to-move: ซ้ำทุก 50 ms → `Dog.hold_move(..., interval=0.05)`

### 3.2 Program — prefix `0xB2`

รหัส `(op, action)` ชุดเดียวกับ remote

| Command | Hex | API |
|---|---|---|
| Enter program mode | `b2ffff` | `enter_program_mode()` |
| Exit → remote | `b2fffe` | `enter_remote_mode()` |
| Play queue | `b2fff1` | `program_play()` |
| Clear queue | `b2fff2` | `program_clear()` |
| Enqueue step | `b2` + op/action | `program_add(verb)` |

Program palette (ไม่มี Learn / Song / Voice / Stop):  
Forward, Backward, Turn_Left/Right, Greet, Bless, Pee, Kung_Fu, Turn_Over, Sit_Down, Act_Cute, Lie_Down, Push_Ups, Hand_stand, Swim, Dance, Hand_shake, Jump

### 3.3 Scan marker

โฆษณาบางรุ่นขึ้นต้น `a1 b1` (`is_scan_marker`) — ไม่ใช่คำสั่งเขียน

## 4. CLI / UI

```bash
# รีโมทเว็บ (พอร์ต 8766)
pip install -e ".[ui]"
gadgetpanda dog ui --demo
gadgetpanda dog ui <addr>

# shell
gadgetpanda dog connect <addr>
# move forward | hold forward 2 | action jump | program run jump,sit_down,dance
```

## 5. Capability gate

1. ไม่มี capability → `UnsupportedCapability`
2. ไม่มี opcode / ไม่อยู่ใน program palette → `OpcodeUnknown`
3. เขียน FFE9

## 6. Out of scope

- อัปโหลดใบหน้า / สตรีมเสียง / กล้อง
- โปรโตคอลแหวน RING503PANDA
