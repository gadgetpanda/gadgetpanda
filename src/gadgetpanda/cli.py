from __future__ import annotations

import argparse
import asyncio
import json
import sys
import traceback

from gadgetpanda.dog import Action, Dog, Move, OpcodeUnknown, UnsupportedCapability, all_profiles, by_id
from gadgetpanda.drone import (
    Drone,
    UnsupportedCapability as DroneUnsupported,
    WifiError,
    all_profiles as drone_all_profiles,
    by_id as drone_by_id,
    ensure_joined,
    list_networks,
    wifi_status,
)
from gadgetpanda.license import FeatureDenied, LicenseError, get_license, init as license_init
from gadgetpanda.models import brand_display, brand_display_value
from gadgetpanda.ring import Ring
from gadgetpanda.stream import DEFAULT_MODE, MODES


def _print(*args, sep: str = " ", end: str = "\n", file=None, flush: bool = False) -> None:
    """Every CLI line goes through brand_display so OEM marks never reach the user."""
    print(brand_display(sep.join(str(item) for item in args)), end=end, file=file, flush=flush)


class _Parser(argparse.ArgumentParser):
    def _print_message(self, message: str, file=None) -> None:
        if message:
            _print(message, end="", file=file or sys.stderr)


def parse_sex(value: str) -> int:
    key = str(value).strip().lower()
    mapping = {
        "0": 0,
        "หญิง": 0,
        "female": 0,
        "f": 0,
        "1": 1,
        "ชาย": 1,
        "male": 1,
        "m": 1,
    }
    if key not in mapping:
        raise argparse.ArgumentTypeError("เพศใช้ 0/หญิง/female หรือ 1/ชาย/male")
    return mapping[key]


class _SexAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if values is None:
            parser.error("ต้องใส่ค่าหลัง --sex เช่น --sex 1 หรือ --sex ชาย — ถ้าไม่เปลี่ยนเพศไม่ต้องใส่ --sex")
        setattr(namespace, self.dest, parse_sex(values))


async def cmd_scan(timeout: float) -> None:
    devices = await Ring.scan(timeout=timeout)
    if not devices:
        _print("ไม่พบแหวน — เปิด BLE ของเครื่องและสวมแหวนให้ใกล้ ๆ")
        return
    for device in devices:
        _print(f"{device.address}  {device.rssi or '':>4}  {device.display_name}")
    _print()
    _print("ต่อเครื่อง:")
    _print("  gadgetpanda ring live")
    _print(f"  gadgetpanda ring connect {devices[0].address}")


def _print_ppg(samples) -> None:
    if not samples:
        return
    values = " ".join(str(sample.value) for sample in samples)
    _print(f"ppg flag={samples[0].flag} n={len(samples)} {values}")


def _print_imu(samples) -> None:
    if not samples:
        return
    first = samples[0]
    peak = max(samples, key=lambda item: item.gyro_mag2)
    gyros = " ".join(f"({item.gyro_x},{item.gyro_y},{item.gyro_z})" for item in samples)
    _print(
        f"imu n={len(samples)} "
        f"acc=({first.acc_x},{first.acc_y},{first.acc_z}) "
        f"gyro=({peak.gyro_x},{peak.gyro_y},{peak.gyro_z}) "
        f"gyros={gyros}"
    )


def _listen_all(ring: Ring) -> None:
    ring.on("info", lambda info: _print("info", json.dumps(brand_display_value(info), ensure_ascii=False)))
    ring.on("battery", lambda level: _print("battery", f"{level}%"))
    ring.on("heart_rate", lambda sample: _print("hr", sample.bpm, "bpm", f"rr={sample.rr_intervals}"))
    ring.on("hrv", lambda hrv: _print("hrv", f"sdnn={hrv.sdnn:.2f} sdnn_ms={hrv.sdnn_ms:.2f} n={hrv.samples}"))
    ring.on("sport", lambda sport: _print("sport", sport))
    ring.on("health", lambda health: _print("health", health))
    ring.on("temperature", lambda temp: _print("temp", temp))
    ring.on("spo2", lambda spo2: _print("spo2", spo2))
    ring.on("imu", _print_imu)
    ring.on("ppg", _print_ppg)
    ring.on("error", lambda exc, packet=None: _print("error", exc, file=sys.stderr))


async def _session(ring: Ring, connect_timeout: float = 20.0, *, ppg_only: bool = False) -> None:
    if ppg_only:
        ring.on("info", lambda info: _print("info", json.dumps(brand_display_value(info), ensure_ascii=False)))
        ring.on("battery", lambda level: _print("battery", f"{level}%"))
        ring.on("heart_rate", lambda sample: _print("hr", sample.bpm, "bpm"))
        ring.on("ppg", _print_ppg)
        ring.on("error", lambda exc, packet=None: _print("error", exc, file=sys.stderr))
    else:
        _listen_all(ring)
    await ring.connect(timeout=connect_timeout)
    try:
        _print(f"connected {ring.name} {ring.address} battery={ring.battery}")
        if ppg_only:
            await ring.start_ppg()
            _print("ppg streaming — สวมแหวนไว้ แล้ว Ctrl+C เพื่อหยุด")
        else:
            await ring.start_realtime()
            _print("realtime — hr sport health temp spo2 imu ppg — Ctrl+C เพื่อหยุด")
        await asyncio.Event().wait()
    finally:
        try:
            await ring.stop_realtime()
        except Exception:
            pass
        await ring.disconnect()


async def cmd_connect(address: str, timeout: float) -> None:
    _print(f"connecting {address} …")
    await _session(Ring(address, name="RING503PANDA"), timeout)


async def cmd_live(timeout: float) -> None:
    ring = await Ring.find(timeout=timeout)
    await _session(ring)


async def cmd_ppg(address: str | None, timeout: float) -> None:
    if address:
        _print(f"connecting {address} …")
        ring = Ring(address, name="RING503PANDA")
    else:
        ring = await Ring.find(timeout=timeout)
    await _session(ring, timeout, ppg_only=True)


async def cmd_user(address: str | None, timeout: float, age: int, weight_kg: int, height_cm: int, sex: int | None) -> None:
    if address:
        _print(f"connecting {address} …")
        ring = Ring(address, name="RING503PANDA")
    else:
        ring = await Ring.find(timeout=timeout)
    async with ring:
        await ring.get_user()
        await ring.set_user(age, sex, weight_kg, height_cm)
        await ring.get_user()
        user = ring.user
        if user is None:
            _print("ตั้งค่าแล้ว แต่แหวนยังไม่ส่งโปรไฟล์กลับ")
            return
        _print(f"user age={user.age} weight={user.weight_kg}kg height={user.height_cm}cm sex={user.sex}")


async def cmd_dog_scan(timeout: float, loose: bool) -> None:
    devices = await Dog.scan(timeout=timeout, loose=loose)
    if not devices:
        _print("ไม่พบสุนัข — เปิด BLE และเปิดเครื่องให้ใกล้ ๆ (หรือลอง --loose)")
        return
    for device in devices:
        _print(f"{device.address}  {device.rssi or '':>4}  {device.display_name}")
    _print()
    _print("ต่อเครื่อง:")
    _print(f"  gadgetpanda dog connect {devices[0].address}")
    _print(f"  gadgetpanda dog raw {devices[0].address} <hex>")


async def _dog_shell(dog: Dog) -> None:
    """Interactive session for remote + program control."""
    loop = asyncio.get_running_loop()
    _print(
        "shell: raw | action | move | hold <dir> [sec] | stop | "
        "program <enter|exit|clear|play|add|run> | help | quit"
    )
    while dog.connected:
        try:
            line = await loop.run_in_executor(None, sys.stdin.readline)
        except Exception:
            break
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        cmd = parts[0].lower()
        arg = " ".join(parts[1:]) if len(parts) > 1 else ""
        try:
            if cmd in {"q", "quit", "exit"}:
                await dog.stop_hold()
                return
            if cmd in {"h", "help", "?"}:
                _print("raw b10100")
                _print("action jump | sit_down | dance | voice | …")
                _print("move forward | backward | turn_left | turn_right | stop")
                _print("hold forward 2     # ซ้ำทุก 50ms แล้ว stop")
                _print("hold forward      # กดค้างจน stop")
                _print("stop              # หยุด hold + ส่ง move stop")
                _print("program enter | exit | clear | play")
                _print("program add jump")
                _print("program run jump,sit_down,dance")
                continue
            if cmd == "raw":
                if not arg:
                    _print("ใส่ hex เช่น: raw b10100")
                    continue
                await dog.raw_write(arg)
                _print("tx", arg.replace(" ", ""))
                continue
            if cmd in {"action", "a"}:
                if not arg:
                    _print("ใส่ชื่อ เช่น: action jump")
                    continue
                await dog.action(arg)
                _print("sent action", arg)
                continue
            if cmd in {"move", "m"}:
                if not arg:
                    _print("ใส่ชื่อ เช่น: move forward")
                    continue
                await dog.move(arg)
                _print("sent move", arg)
                continue
            if cmd == "hold":
                if not arg:
                    _print("เช่น: hold forward 2")
                    continue
                hold_parts = arg.split()
                name = hold_parts[0]
                seconds = float(hold_parts[1]) if len(hold_parts) > 1 else None
                await dog.hold_move(name, seconds=seconds)
                _print("holding" if seconds is None else f"held {seconds}s", name)
                continue
            if cmd == "stop":
                await dog.move(Move.STOP)
                _print("sent move stop")
                continue
            if cmd in {"program", "prog", "p"}:
                if not arg:
                    _print("program enter|exit|clear|play|add <verb>|run a,b,c")
                    continue
                sub_parts = arg.split(maxsplit=1)
                sub = sub_parts[0].lower()
                rest = sub_parts[1].strip() if len(sub_parts) > 1 else ""
                if sub == "enter":
                    await dog.enter_program_mode()
                    _print("tx program enter b2ffff")
                elif sub == "exit":
                    await dog.enter_remote_mode()
                    _print("tx program exit b2fffe")
                elif sub == "clear":
                    await dog.program_clear()
                    _print("tx program clear b2fff2")
                elif sub == "play":
                    await dog.program_play()
                    _print("tx program play b2fff1")
                elif sub == "add":
                    if not rest:
                        _print("เช่น: program add jump")
                        continue
                    await dog.program_add(rest)
                    _print("queued", rest)
                elif sub == "run":
                    if not rest:
                        _print("เช่น: program run jump,sit_down,dance")
                        continue
                    verbs = [v.strip() for v in rest.replace(" ", ",").split(",") if v.strip()]
                    await dog.run_program(verbs)
                    _print("ran program", ", ".join(verbs))
                else:
                    _print("program enter|exit|clear|play|add|run")
                continue
            # bare hex shortcut
            if all(ch in "0123456789abcdefABCDEF :-" for ch in line) and any(c.isalnum() for c in line):
                await dog.raw_write(line)
                _print("tx", line.replace(" ", "").replace(":", "").replace("-", ""))
                continue
            _print("ไม่รู้จักคำสั่ง — พิมพ์ help")
        except (OpcodeUnknown, UnsupportedCapability, ValueError, RuntimeError) as exc:
            if isinstance(exc, OpcodeUnknown):
                _print(f"ยังไม่มี opcode สำหรับ {exc.verb!r}")
            else:
                _print(exc)


async def cmd_dog_connect(address: str, timeout: float, model: str, shell: bool) -> None:
    _print(f"connecting dog {address} model={model} …")
    dog = Dog(address, model=model)
    dog.on("rx", lambda data: _print("rx", data.hex()))
    dog.on("error", lambda exc: _print("error", exc, file=sys.stderr))
    await dog.connect(timeout=timeout)
    try:
        _print(f"connected {dog.name}  addr={dog.address}  profile={dog.profile.id}")
        for line in dog.services:
            _print("gatt", line)
        if shell:
            await _dog_shell(dog)
        else:
            _print("listening notify — Ctrl+C เพื่อหยุด (หรือใช้ --shell เพื่อส่ง raw/action)")
            await asyncio.Event().wait()
    finally:
        await dog.disconnect()


async def cmd_dog_raw(address: str, hex_payload: str, timeout: float, model: str) -> None:
    dog = Dog(address, model=model)
    async with dog:
        await dog.raw_write(hex_payload)
        _print(f"tx {hex_payload}  → {dog.name}")


async def cmd_dog_action(address: str, name: str, timeout: float, model: str, kind: str) -> None:
    dog = Dog(address, model=model)
    async with dog:
        try:
            if kind == "move":
                await dog.move(Move(name))
            else:
                await dog.action(name)
        except (OpcodeUnknown, UnsupportedCapability, ValueError) as exc:
            _print(exc)
            raise SystemExit(2) from None
        _print(f"sent {kind} {name}  → {dog.name}")


def cmd_dog_caps(model: str | None) -> None:
    profiles = (by_id(model),) if model else all_profiles()
    for profile in profiles:
        caps = ", ".join(sorted(cap.name for cap in profile.capabilities))
        filled = sum(1 for _ in profile.opcodes)
        _print(f"{profile.id}  {profile.display_name}  opcodes={filled}")
        _print(f"  {caps}")


async def cmd_dog_ui(
    address: str | None,
    timeout: float,
    host: str,
    port: int,
    demo: bool,
    open_browser: bool,
    model: str,
) -> None:
    try:
        from gadgetpanda.dog.ui import serve
    except ImportError:
        _print('ติดตั้ง UI ด้วย: pip install -e ".[ui]"')
        raise SystemExit(1) from None
    url = f"http://{host}:{port}"
    if demo:
        _print(f"dog ui {url}  (demo — ไม่ต่อ BLE จริง)  model={model}", flush=True)
    elif address:
        _print(f"dog ui {url}  → {address}  model={model}", flush=True)
    else:
        _print(f"dog ui {url}  → สแกนหาสุนัขตัวแรก  model={model}", flush=True)
    if open_browser:
        import webbrowser

        asyncio.get_running_loop().call_later(0.8, webbrowser.open, url)
    await serve(host, port, address, timeout, demo=demo, model=model)


async def cmd_ui(
    address: str | None,
    timeout: float,
    host: str,
    port: int,
    demo: bool,
    open_browser: bool,
    mode: str = DEFAULT_MODE,
) -> None:
    try:
        from gadgetpanda.dashboard.server import serve
    except ImportError:
        _print('ติดตั้ง UI ด้วย: pip install -e ".[ui]"')
        raise SystemExit(1) from None
    url = f"http://{host}:{port}"
    if demo:
        _print(f"dashboard {url}  (โหมดสาธิต ไม่ต่อแหวนจริง)  stream={mode}", flush=True)
    elif address:
        _print(f"dashboard {url}  → {address}  stream={mode}", flush=True)
    else:
        _print(f"dashboard {url}  → สแกนหาแหวนวงแรก  stream={mode}", flush=True)
    if open_browser:
        import webbrowser

        asyncio.get_running_loop().call_later(0.8, webbrowser.open, url)
    await serve(host, port, address, timeout, demo, mode)


def _add_ring_parsers(ring_sub) -> None:
    scan_p = ring_sub.add_parser("scan", help="สแกนหาแหวน RING503PANDA / RING503nPANDA")
    scan_p.add_argument("--timeout", type=float, default=8.0)

    connect_p = ring_sub.add_parser("connect", help="ต่อแหวนด้วยที่อยู่จาก scan แล้วสตรีมทุกค่า")
    connect_p.add_argument("address", help="เช่น EA1D0BD7-5438-F5F9-E624-9E8E750CCD38")
    connect_p.add_argument("--timeout", type=float, default=20.0)

    live_p = ring_sub.add_parser("live", help="สแกนแล้วสตรีมทุกค่าแบบ realtime")
    live_p.add_argument("--timeout", type=float, default=8.0)

    ppg_p = ring_sub.add_parser("ppg", help="สตรีมเฉพาะ PPG realtime")
    ppg_p.add_argument("address", nargs="?", help="ที่อยู่จาก scan ถ้าไม่ใส่จะหาวงแรก")
    ppg_p.add_argument("--timeout", type=float, default=20.0)

    ui_p = ring_sub.add_parser("ui", help="แดชบอร์ด realtime พร้อมกราฟแนวโน้มทุกค่า")
    ui_p.add_argument("address", nargs="?", help="ที่อยู่จาก scan ถ้าไม่ใส่จะหาวงแรก")
    ui_p.add_argument("--timeout", type=float, default=20.0)
    ui_p.add_argument("--host", default="127.0.0.1")
    ui_p.add_argument("--port", type=int, default=8765)
    ui_p.add_argument("--demo", action="store_true", help="จำลองข้อมูลโดยไม่ต่อแหวน")
    ui_p.add_argument("--no-open", action="store_true", help="ไม่เปิดเบราว์เซอร์อัตโนมัติ")
    ui_p.add_argument("--mode", default=DEFAULT_MODE, choices=sorted(MODES), help="โหมดสตรีมเริ่มต้น")

    user_p = ring_sub.add_parser("user", help="ตั้งอายุ น้ำหนัก ส่วนสูง ลงแหวน")
    user_p.add_argument("address", nargs="?", help="ที่อยู่จาก scan ถ้าไม่ใส่จะหาวงแรก")
    user_p.add_argument("--timeout", type=float, default=20.0)
    user_p.add_argument("--age", type=int, required=True)
    user_p.add_argument("--weight", type=int, required=True, dest="weight_kg")
    user_p.add_argument("--height", type=int, required=True, dest="height_cm")
    user_p.add_argument(
        "--sex",
        nargs="?",
        action=_SexAction,
        default=None,
        metavar="เพศ",
        help="1/ชาย/male หรือ 0/หญิง/female — ไม่ใส่ถ้าไม่เปลี่ยน",
    )
    user_p.add_argument("--male", dest="sex", action="store_const", const=1, help="เพศชาย")
    user_p.add_argument("--female", dest="sex", action="store_const", const=0, help="เพศหญิง")


def _dispatch_ring(args) -> None:
    ring_cmd = getattr(args, "ring_command", None)
    if ring_cmd == "connect":
        asyncio.run(cmd_connect(args.address, args.timeout))
    elif ring_cmd == "live":
        asyncio.run(cmd_live(args.timeout))
    elif ring_cmd == "ppg":
        asyncio.run(cmd_ppg(getattr(args, "address", None), args.timeout))
    elif ring_cmd == "user":
        asyncio.run(
            cmd_user(
                getattr(args, "address", None),
                args.timeout,
                args.age,
                args.weight_kg,
                args.height_cm,
                args.sex,
            )
        )
    elif ring_cmd == "ui":
        asyncio.run(
            cmd_ui(
                getattr(args, "address", None),
                args.timeout,
                args.host,
                args.port,
                args.demo,
                not args.no_open,
                args.mode,
            )
        )
    else:
        asyncio.run(cmd_scan(getattr(args, "timeout", 8.0)))


async def _drone_maybe_join_wifi(
    ssid: str | None,
    password: str | None,
    *,
    device: str | None = None,
    settle: float = 2.0,
) -> None:
    if not ssid:
        return
    _print(f"wifi join {ssid!r} …", flush=True)
    try:
        status = await ensure_joined(ssid, password, device=device, settle=settle)
    except WifiError as exc:
        _print(f"wifi error: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
    _print(f"wifi ok  device={status.device}  ssid={status.ssid}  via={status.backend}")


async def cmd_drone_wifi(action: str, ssid: str | None, password: str | None, device: str | None) -> None:
    try:
        if action == "status":
            status = wifi_status(device)
            lan = "drone-lan" if status.looks_like_drone_lan else "not-drone-lan"
            _print(
                f"backend={status.backend}  device={status.device}  "
                f"ssid={status.ssid or '(none)'}  ipv4={status.ipv4 or '(none)'}  [{lan}]"
            )
            return
        if action == "list":
            names = list_networks(device)
            if not names:
                _print("ไม่พบรายการเครือข่าย (macOS แสดง preferred; Linux แสดง scan)")
                return
            for name in names:
                _print(name)
            return
        if action == "join":
            if not ssid:
                _print("ใส่ SSID เช่น: gadgetpanda drone wifi join KY_UFO_xxxx")
                raise SystemExit(2)
            status = await ensure_joined(ssid, password, device=device)
            _print(
                f"joined {status.ssid or ssid} on {status.device}  ipv4={status.ipv4 or '(pending)'}"
            )
            return
        _print(f"unknown wifi action {action}")
        raise SystemExit(2)
    except WifiError as exc:
        _print(f"wifi error: {exc}", file=sys.stderr)
        raise SystemExit(2) from None


async def cmd_drone_scan(timeout: float, model: str) -> None:
    try:
        wifi = wifi_status()
        _print(f"wifi now: {wifi.ssid or '(none)'}  ipv4={wifi.ipv4 or '(none)'} on {wifi.device}")
        if not wifi.looks_like_drone_lan:
            _print("คำเตือน: ยังไม่ได้อยู่บน hotspot โดรน — join ก่อน เช่น")
            _print('  gadgetpanda drone wifi join "FLOW-UFO-xxxx"')
            _print("หมายเหตุ: โดรนไม่มีอินเทอร์เน็ตเป็นปกติ ใช้แค่ LAN 192.168.1.x")
    except WifiError as exc:
        _print(f"wifi status: {exc}")
    devices = await Drone.scan(timeout=timeout, model=model)
    up = [d for d in devices if d.reachable]
    if not up:
        _print("ไม่พบโดรนที่ตอบ TCP/ICMP — join Wi‑Fi โดรนแล้วรอ DHCP แล้วลองใหม่")
        for device in devices:
            _print(f"  {device.display_name}")
        return
    for device in devices:
        _print(device.display_name)
    _print()
    best = up[0]
    _print("ต่อเครื่อง (ออฟไลน์บน LAN โดรนได้เลย ไม่ต้องมีเน็ต):")
    _print(f"  gadgetpanda drone connect {best.host} --model flow")
    _print(f"  gadgetpanda drone ui {best.host} --model flow")


async def _drone_shell(drone: Drone) -> None:
    loop = asyncio.get_running_loop()
    _print("shell: stick | hold <dir> [sec] | cmd | raw | axes | help | quit")
    while drone.connected:
        try:
            line = await loop.run_in_executor(None, sys.stdin.readline)
        except Exception:
            break
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        cmd = parts[0].lower()
        arg = " ".join(parts[1:]) if len(parts) > 1 else ""
        try:
            if cmd in {"q", "quit", "exit"}:
                return
            if cmd in {"h", "help", "?"}:
                _print("stick forward|backward|left|right|up|down|yaw_left|yaw_right|hover")
                _print("hold forward 2")
                _print("cmd takeoff|land|stop|emergency|calibrate|headless_on|light_on")
                _print("axes roll pitch throttle yaw   # 1-255, center 128")
                _print("raw 0306808080800099")
                continue
            if cmd == "raw":
                if not arg:
                    _print("ใส่ hex เช่น: raw 0101")
                    continue
                await drone.raw_write(arg)
                _print("tx", arg.replace(" ", ""))
                continue
            if cmd in {"stick", "s"}:
                if not arg:
                    _print("เช่น: stick forward")
                    continue
                await drone.stick(arg)
                _print("stick", arg)
                continue
            if cmd == "hold":
                if not arg:
                    _print("เช่น: hold forward 2")
                    continue
                hold_parts = arg.split()
                name = hold_parts[0]
                seconds = float(hold_parts[1]) if len(hold_parts) > 1 else None
                await drone.hold_stick(name, seconds=seconds)
                _print("holding" if seconds is None else f"held {seconds}s", name)
                continue
            if cmd in {"cmd", "command", "c"}:
                if not arg:
                    _print("เช่น: cmd takeoff")
                    continue
                await drone.command(arg)
                _print("cmd", arg)
                continue
            if cmd == "axes":
                nums = [int(x) for x in arg.split()]
                if len(nums) != 4:
                    _print("axes roll pitch throttle yaw")
                    continue
                drone.set_axes(roll=nums[0], pitch=nums[1], throttle=nums[2], yaw=nums[3])
                _print("axes", nums)
                continue
            _print("unknown — พิมพ์ help")
        except (DroneUnsupported, ValueError) as exc:
            _print("error", exc)
        except Exception:
            _print(traceback.format_exc(), end="", file=sys.stderr)


async def cmd_drone_connect(
    host: str | None,
    timeout: float,
    model: str,
    shell: bool,
    demo: bool,
    wifi_ssid: str | None = None,
    wifi_password: str | None = None,
    wifi_device: str | None = None,
) -> None:
    if not demo:
        await _drone_maybe_join_wifi(wifi_ssid, wifi_password, device=wifi_device)
    drone = Drone(host, model=model, demo=demo)
    drone.on("tx", lambda data: None)
    drone.on("error", lambda exc: _print("error", exc, file=sys.stderr))
    _print(f"connecting {drone.address} model={model}" + (" (demo)" if demo else "") + " …")
    await drone.connect(timeout=timeout)
    try:
        _print(f"connected {drone.name} {drone.address}")
        _print("เตือน: โดรนบินได้จริง — มีพื้นที่โล่ง และ emergency พร้อม")
        if shell:
            await _drone_shell(drone)
        else:
            await asyncio.Event().wait()
    finally:
        await drone.disconnect()


async def cmd_drone_raw(host: str | None, hex_payload: str, timeout: float, model: str, demo: bool) -> None:
    async with Drone(host, model=model, demo=demo) as drone:
        await drone.raw_write(hex_payload)
        _print("tx", hex_payload.replace(" ", ""))
        await asyncio.sleep(0.2)


async def cmd_drone_stick(host: str | None, name: str, timeout: float, model: str, seconds: float, demo: bool) -> None:
    async with Drone(host, model=model, demo=demo) as drone:
        await drone.hold_stick(name, seconds=seconds)
        _print("stick", name, f"{seconds}s")


async def cmd_drone_command(host: str | None, name: str, timeout: float, model: str, demo: bool) -> None:
    async with Drone(host, model=model, demo=demo) as drone:
        await drone.command(name)
        _print("cmd", name)


def cmd_drone_caps(model: str | None) -> None:
    profiles = [drone_by_id(model)] if model else drone_all_profiles()
    for profile in profiles:
        caps = ", ".join(sorted(c.value for c in profile.capabilities)) or "(none)"
        _print(f"{profile.id}  {profile.display_name}")
        _print(f"  frame={profile.frame_variant}  {profile.endpoints.host}:{profile.endpoints.udp_port}")
        _print(f"  caps: {caps}")


async def cmd_drone_ui(
    drone_host: str | None,
    timeout: float,
    host: str,
    port: int,
    demo: bool,
    open_browser: bool,
    model: str,
    wifi_ssid: str | None = None,
    wifi_password: str | None = None,
    wifi_device: str | None = None,
) -> None:
    try:
        from gadgetpanda.drone.ui import serve
    except ImportError:
        _print('ติดตั้ง UI ด้วย: pip install -e ".[ui]"')
        raise SystemExit(1) from None
    if not demo:
        await _drone_maybe_join_wifi(wifi_ssid, wifi_password, device=wifi_device)
    url = f"http://{host}:{port}"
    if demo:
        _print(f"drone remote {url}  (demo)", flush=True)
    else:
        _print(f"drone remote {url}  → {drone_host or '192.168.1.1'}  model={model}", flush=True)
    if open_browser:
        import webbrowser

        asyncio.get_running_loop().call_later(0.8, webbrowser.open, url)
    await serve(host, port, drone_host, timeout, demo, model)


def cmd_license_status() -> None:
    lic = license_init()
    _print(json.dumps(lic.status(), ensure_ascii=False, indent=2))


def cmd_license_activate(api_key: str, server: str | None) -> None:
    lic = get_license()
    status = lic.activate(api_key, server_url=server)
    _print("activated")
    _print(json.dumps(status, ensure_ascii=False, indent=2))


def cmd_license_refresh() -> None:
    lic = license_init()
    if not lic.api_key:
        raise LicenseError("no license key — run: gadgetpanda license activate <key>")
    status = lic.refresh()
    _print(json.dumps(status, ensure_ascii=False, indent=2))


def cmd_license_logout() -> None:
    lic = license_init()
    lic.logout(online=True)
    _print("logged out — device slot freed")


def cmd_license_features() -> None:
    from gadgetpanda.license import FEATURES, PRESETS

    for feature in FEATURES:
        _print(f"{feature.id:16}  {feature.group:6}  {feature.label}")
    _print()
    for name, ids in PRESETS.items():
        _print(f"preset {name}: {', '.join(sorted(ids))}")


def main(argv: list[str] | None = None) -> None:
    parser = _Parser(prog="gadgetpanda", description="Gadget Panda CLI — ring · dog · drone · license")
    sub = parser.add_subparsers(dest="command", parser_class=_Parser)

    ring_p = sub.add_parser("ring", help="แหวน RING503PANDA — สแกน / สตรีม / แดชบอร์ด")
    ring_sub = ring_p.add_subparsers(dest="ring_command", parser_class=_Parser)
    _add_ring_parsers(ring_sub)

    dog_p = sub.add_parser("dog", help="หุ่นสุนัขสนุก (X1) — คนละโปรโตคอลกับแหวน")
    dog_sub = dog_p.add_subparsers(dest="dog_command", parser_class=_Parser)

    dog_scan = dog_sub.add_parser("scan", help="สแกนหาสุนัข BLE")
    dog_scan.add_argument("--timeout", type=float, default=8.0)
    dog_scan.add_argument("--loose", action="store_true", help="แสดงทุกอุปกรณ์ที่เห็น (เรียนรู้ชื่อ)")

    dog_connect = dog_sub.add_parser("connect", help="ต่อ GATT แล้วฟัง notify / เปิด shell")
    dog_connect.add_argument("address")
    dog_connect.add_argument("--timeout", type=float, default=20.0)
    dog_connect.add_argument("--model", default="x1", help="x1 หรือ generic")
    dog_connect.add_argument(
        "--shell",
        action="store_true",
        default=True,
        help="เปิด interactive shell สำหรับ raw/action/move (ค่าเริ่มต้นเปิด)",
    )
    dog_connect.add_argument("--no-shell", action="store_false", dest="shell", help="แค่ฟัง notify")

    dog_raw = dog_sub.add_parser("raw", help="ส่งไบต์ดิบไป FFE9")
    dog_raw.add_argument("address")
    dog_raw.add_argument("hex", help="เช่น b10100 หรือ b1 01 00")
    dog_raw.add_argument("--timeout", type=float, default=20.0)
    dog_raw.add_argument("--model", default="x1")

    dog_action = dog_sub.add_parser("action", help="ส่งท่า (เช่น jump / sit_down / voice)")
    dog_action.add_argument("address")
    dog_action.add_argument("name", help="เช่น sit_down / voice / jump")
    dog_action.add_argument("--timeout", type=float, default=20.0)
    dog_action.add_argument("--model", default="x1")

    dog_move = dog_sub.add_parser("move", help="ส่งคำสั่งเคลื่อนที่ (เช่น forward / stop)")
    dog_move.add_argument("address")
    dog_move.add_argument("name", help="เช่น forward / stop / turn_left")
    dog_move.add_argument("--timeout", type=float, default=20.0)
    dog_move.add_argument("--model", default="x1")

    dog_caps = dog_sub.add_parser("caps", help="แสดง capability ของรุ่น")
    dog_caps.add_argument("--model", default=None, help="ระบุรุ่น หรือไม่ใส่เพื่อแสดงทั้งหมด")

    dog_ui = dog_sub.add_parser("ui", help="รีโมทเว็บ (D-pad / ท่า / program)")
    dog_ui.add_argument("address", nargs="?", help="ที่อยู่จาก scan ถ้าไม่ใส่จะหาตัวแรก")
    dog_ui.add_argument("--timeout", type=float, default=20.0)
    dog_ui.add_argument("--host", default="127.0.0.1")
    dog_ui.add_argument("--port", type=int, default=8766)
    dog_ui.add_argument("--model", default="x1")
    dog_ui.add_argument("--demo", action="store_true", help="จำลองโดยไม่ต่อ BLE")
    dog_ui.add_argument("--no-open", action="store_true", help="ไม่เปิดเบราว์เซอร์อัตโนมัติ")

    drone_p = sub.add_parser("drone", help="โดรน Wi‑Fi V66 / KY UFO stack — คนละโปรโตคอลกับแหวน/หมา")
    drone_sub = drone_p.add_subparsers(dest="drone_command", parser_class=_Parser)

    drone_scan = drone_sub.add_parser("scan", help="probe IP เกตเวย์โดรน (ต้อง join Wi‑Fi แล้ว)")
    drone_scan.add_argument("--timeout", type=float, default=1.5)
    drone_scan.add_argument("--model", default="v66")

    drone_connect = drone_sub.add_parser("connect", help="เปิด UDP stick loop + shell")
    drone_connect.add_argument("host", nargs="?", default=None, help="เช่น 192.168.1.1")
    drone_connect.add_argument("--timeout", type=float, default=3.0)
    drone_connect.add_argument("--model", default="v66")
    drone_connect.add_argument("--demo", action="store_true")
    drone_connect.add_argument("--shell", action="store_true", default=True)
    drone_connect.add_argument("--no-shell", action="store_false", dest="shell")
    drone_connect.add_argument("--wifi", dest="wifi_ssid", default=None, help="บังคับ join SSID ก่อนต่อ UDP")
    drone_connect.add_argument("--wifi-password", default=None, help="รหัส Wi‑Fi (ถ้าว่างไม่ใส่)")
    drone_connect.add_argument("--wifi-device", default=None, help="เช่น en0 บน macOS")

    drone_wifi = drone_sub.add_parser("wifi", help="สถานะ / join Wi‑Fi ของโดรนจากเครื่องนี้")
    drone_wifi_sub = drone_wifi.add_subparsers(dest="wifi_action", parser_class=_Parser)
    drone_wifi_status = drone_wifi_sub.add_parser("status", help="SSID ที่ต่ออยู่ตอนนี้")
    drone_wifi_status.add_argument("--device", default=None)
    drone_wifi_list = drone_wifi_sub.add_parser("list", help="รายการเครือข่าย (preferred/scan)")
    drone_wifi_list.add_argument("--device", default=None)
    drone_wifi_join = drone_wifi_sub.add_parser("join", help="บังคับ join hotspot")
    drone_wifi_join.add_argument("ssid", help="เช่น KY_UFO_xxxx")
    drone_wifi_join.add_argument("--password", default=None)
    drone_wifi_join.add_argument("--device", default=None)

    drone_raw = drone_sub.add_parser("raw", help="ส่งไบต์ดิบทาง UDP")
    drone_raw.add_argument("hex", help="เช่น 0101 หรือ 0306808080800099")
    drone_raw.add_argument("--host", default=None, help="IP โดรน ค่าเริ่มต้นตามรุ่น")
    drone_raw.add_argument("--timeout", type=float, default=3.0)
    drone_raw.add_argument("--model", default="v66")
    drone_raw.add_argument("--demo", action="store_true")

    drone_stick = drone_sub.add_parser("stick", help="ตั้งทิศสติ๊กชั่วคราว")
    drone_stick.add_argument("name", help="forward / up / yaw_left / …")
    drone_stick.add_argument("--host", default=None)
    drone_stick.add_argument("--seconds", type=float, default=1.0)
    drone_stick.add_argument("--timeout", type=float, default=3.0)
    drone_stick.add_argument("--model", default="v66")
    drone_stick.add_argument("--demo", action="store_true")

    drone_cmd = drone_sub.add_parser("cmd", help="takeoff / land / emergency / …")
    drone_cmd.add_argument("name", help="takeoff | land | stop | emergency | …")
    drone_cmd.add_argument("--host", default=None)
    drone_cmd.add_argument("--timeout", type=float, default=3.0)
    drone_cmd.add_argument("--model", default="v66")
    drone_cmd.add_argument("--demo", action="store_true")

    drone_caps = drone_sub.add_parser("caps", help="แสดง capability ของรุ่น")
    drone_caps.add_argument("--model", default=None)

    drone_ui = drone_sub.add_parser("ui", help="รีโมทเว็บ (D-pad / คำสั่งบิน)")
    drone_ui.add_argument("drone_host", nargs="?", default=None, help="IP โดรน เช่น 192.168.1.1")
    drone_ui.add_argument("--timeout", type=float, default=3.0)
    drone_ui.add_argument("--host", default="127.0.0.1")
    drone_ui.add_argument("--port", type=int, default=8767)
    drone_ui.add_argument("--model", default="v66")
    drone_ui.add_argument("--demo", action="store_true")
    drone_ui.add_argument("--no-open", action="store_true")
    drone_ui.add_argument("--wifi", dest="wifi_ssid", default=None, help="บังคับ join SSID ก่อนเปิดรีโมท")
    drone_ui.add_argument("--wifi-password", default=None)
    drone_ui.add_argument("--wifi-device", default=None)

    lic_p = sub.add_parser("license", help="soft license — activate / status / logout")
    lic_sub = lic_p.add_subparsers(dest="license_command", parser_class=_Parser)
    lic_sub.add_parser("status", help="สถานะ key / features / device")
    lic_act = lic_sub.add_parser("activate", help="ผูก key กับเครื่องนี้")
    lic_act.add_argument("api_key")
    lic_act.add_argument("--server", default=None, help="เช่น http://127.0.0.1:8787")
    lic_sub.add_parser("refresh", help="ต่ออายุ token จากเซิร์ฟเวอร์หรือแคช")
    lic_sub.add_parser("logout", help="ปลดผูกเครื่อง (ย้ายไปเครื่องอื่นได้)")
    lic_sub.add_parser("features", help="รายการ feature ids")

    parser.set_defaults(command="ring", ring_command="scan", timeout=8.0)
    args = parser.parse_args(argv)
    try:
        if args.command == "license":
            lic_cmd = getattr(args, "license_command", None) or "status"
            if lic_cmd == "activate":
                cmd_license_activate(args.api_key, getattr(args, "server", None))
            elif lic_cmd == "refresh":
                cmd_license_refresh()
            elif lic_cmd == "logout":
                cmd_license_logout()
            elif lic_cmd == "features":
                cmd_license_features()
            else:
                cmd_license_status()
        elif args.command == "dog":
            dog_cmd = getattr(args, "dog_command", None)
            if dog_cmd == "connect":
                asyncio.run(cmd_dog_connect(args.address, args.timeout, args.model, getattr(args, "shell", True)))
            elif dog_cmd == "raw":
                asyncio.run(cmd_dog_raw(args.address, args.hex, args.timeout, args.model))
            elif dog_cmd == "action":
                asyncio.run(cmd_dog_action(args.address, args.name, args.timeout, args.model, "action"))
            elif dog_cmd == "move":
                asyncio.run(cmd_dog_action(args.address, args.name, args.timeout, args.model, "move"))
            elif dog_cmd == "caps":
                cmd_dog_caps(getattr(args, "model", None))
            elif dog_cmd == "ui":
                asyncio.run(
                    cmd_dog_ui(
                        getattr(args, "address", None),
                        args.timeout,
                        args.host,
                        args.port,
                        getattr(args, "demo", False),
                        not getattr(args, "no_open", False),
                        getattr(args, "model", "x1"),
                    )
                )
            else:
                asyncio.run(cmd_dog_scan(getattr(args, "timeout", 8.0), getattr(args, "loose", False)))
        elif args.command == "drone":
            drone_cmd = getattr(args, "drone_command", None)
            if drone_cmd == "wifi":
                action = getattr(args, "wifi_action", None) or "status"
                asyncio.run(
                    cmd_drone_wifi(
                        action,
                        getattr(args, "ssid", None),
                        getattr(args, "password", None),
                        getattr(args, "device", None),
                    )
                )
            elif drone_cmd == "connect":
                asyncio.run(
                    cmd_drone_connect(
                        getattr(args, "host", None),
                        args.timeout,
                        args.model,
                        getattr(args, "shell", True),
                        getattr(args, "demo", False),
                        getattr(args, "wifi_ssid", None),
                        getattr(args, "wifi_password", None),
                        getattr(args, "wifi_device", None),
                    )
                )
            elif drone_cmd == "raw":
                asyncio.run(
                    cmd_drone_raw(
                        getattr(args, "host", None),
                        args.hex,
                        args.timeout,
                        args.model,
                        getattr(args, "demo", False),
                    )
                )
            elif drone_cmd == "stick":
                asyncio.run(
                    cmd_drone_stick(
                        getattr(args, "host", None),
                        args.name,
                        args.timeout,
                        args.model,
                        args.seconds,
                        getattr(args, "demo", False),
                    )
                )
            elif drone_cmd == "cmd":
                asyncio.run(
                    cmd_drone_command(
                        getattr(args, "host", None),
                        args.name,
                        args.timeout,
                        args.model,
                        getattr(args, "demo", False),
                    )
                )
            elif drone_cmd == "caps":
                cmd_drone_caps(getattr(args, "model", None))
            elif drone_cmd == "ui":
                asyncio.run(
                    cmd_drone_ui(
                        getattr(args, "drone_host", None),
                        args.timeout,
                        args.host,
                        args.port,
                        getattr(args, "demo", False),
                        not getattr(args, "no_open", False),
                        getattr(args, "model", "v66"),
                        getattr(args, "wifi_ssid", None),
                        getattr(args, "wifi_password", None),
                        getattr(args, "wifi_device", None),
                    )
                )
            else:
                asyncio.run(cmd_drone_scan(getattr(args, "timeout", 1.5), getattr(args, "model", "v66")))
        else:
            _dispatch_ring(args)
    except (LicenseError, FeatureDenied) as exc:
        _print(str(exc), file=sys.stderr)
        raise SystemExit(2) from None
    except KeyboardInterrupt:
        _print("\nbye")
    except Exception:
        _print(traceback.format_exc(), end="", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
