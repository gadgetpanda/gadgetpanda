"""Join the craft Wi‑Fi AP from the host OS (macOS / NetworkManager).

Drone control needs the computer on the craft hotspot first. This module wraps
platform tools so CLI can force the association before opening UDP.
"""

from __future__ import annotations

import asyncio
import platform
import re
import shutil
import subprocess
import time
from dataclasses import dataclass


class WifiError(RuntimeError):
    """Raised when the OS cannot change Wi‑Fi association."""


@dataclass(frozen=True)
class WifiStatus:
    device: str
    ssid: str | None
    backend: str
    ipv4: str | None = None

    @property
    def looks_like_drone_lan(self) -> bool:
        if self.ssid and "UFO" in self.ssid.upper():
            return True
        if self.ipv4 and self.ipv4.startswith("192.168.1."):
            return True
        return False


def _run(cmd: list[str], *, timeout: float = 30.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _macos_wifi_device() -> str:
    result = _run(["networksetup", "-listallhardwareports"])
    if result.returncode != 0:
        raise WifiError(result.stderr.strip() or "networksetup listallhardwareports failed")
    device = None
    pending_wifi = False
    for line in result.stdout.splitlines():
        if line.startswith("Hardware Port:"):
            pending_wifi = "wi-fi" in line.lower() or "airport" in line.lower()
        elif pending_wifi and line.startswith("Device:"):
            device = line.split(":", 1)[1].strip()
            break
    if not device:
        raise WifiError("ไม่พบอินเทอร์เฟซ Wi‑Fi (networksetup)")
    return device


def _macos_ipv4(device: str) -> str | None:
    result = _run(["ipconfig", "getifaddr", device], timeout=5)
    addr = (result.stdout or "").strip()
    return addr or None


def _macos_status(device: str | None = None) -> WifiStatus:
    iface = device or _macos_wifi_device()
    result = _run(["networksetup", "-getairportnetwork", iface])
    text = (result.stdout or result.stderr or "").strip()
    ssid = None
    if "not associated" in text.lower():
        ssid = None
    else:
        match = re.search(r"Current Wi-Fi Network:\s*(.+)$", text)
        if match:
            ssid = match.group(1).strip() or None
        elif result.returncode == 0 and text and "error" not in text.lower():
            ssid = text
    return WifiStatus(device=iface, ssid=ssid, backend="networksetup", ipv4=_macos_ipv4(iface))


def _macos_join(ssid: str, password: str | None, device: str | None, timeout: float) -> WifiStatus:
    iface = device or _macos_wifi_device()
    _run(["networksetup", "-setairportpower", iface, "on"], timeout=10)
    cmd = ["networksetup", "-setairportnetwork", iface, ssid]
    if password:
        cmd.append(password)
    result = _run(cmd, timeout=timeout)
    combined = f"{result.stdout}\n{result.stderr}".strip()
    if result.returncode != 0 or "error" in combined.lower() or "failed" in combined.lower():
        raise WifiError(combined or f"join failed for {ssid!r}")
    # DHCP / association settle — SSID may stay blank on some macOS builds; accept drone LAN IP.
    deadline = time.monotonic() + min(timeout, 12.0)
    last = _macos_status(iface)
    while time.monotonic() < deadline:
        last = _macos_status(iface)
        if last.ssid == ssid or last.looks_like_drone_lan:
            return last
        time.sleep(0.4)
    if last.ssid != ssid and not last.looks_like_drone_lan:
        raise WifiError(
            f"join issued but still on ssid={last.ssid!r} ipv4={last.ipv4!r} (want {ssid!r})"
        )
    return last


def _macos_preferred(device: str | None = None) -> list[str]:
    iface = device or _macos_wifi_device()
    result = _run(["networksetup", "-listpreferredwirelessnetworks", iface])
    if result.returncode != 0:
        return []
    names: list[str] = []
    for line in result.stdout.splitlines():
        if line.startswith("Preferred networks"):
            continue
        name = line.strip().lstrip("\t ")
        if name:
            names.append(name)
    return names


def _nmcli_available() -> bool:
    return shutil.which("nmcli") is not None


def _linux_status() -> WifiStatus:
    result = _run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"])
    if result.returncode != 0:
        raise WifiError(result.stderr.strip() or "nmcli device failed")
    device = "wlan0"
    ssid = None
    for line in result.stdout.splitlines():
        parts = line.split(":")
        if len(parts) >= 4 and parts[1] == "wifi" and parts[2] == "connected":
            device = parts[0]
            ssid = parts[3] or None
            break
    ipv4 = None
    addr = _run(["nmcli", "-t", "-f", "IP4.ADDRESS", "device", "show", device])
    if addr.returncode == 0 and addr.stdout.strip():
        ipv4 = addr.stdout.strip().split("/", 1)[0]
    return WifiStatus(device=device, ssid=ssid, backend="nmcli", ipv4=ipv4)


def _linux_join(ssid: str, password: str | None, timeout: float) -> WifiStatus:
    cmd = ["nmcli", "device", "wifi", "connect", ssid]
    if password:
        cmd.extend(["password", password])
    result = _run(cmd, timeout=timeout)
    if result.returncode != 0:
        raise WifiError((result.stderr or result.stdout or "nmcli connect failed").strip())
    time.sleep(1.0)
    status = _linux_status()
    if status.ssid != ssid:
        raise WifiError(f"join issued but still on {status.ssid!r} (want {ssid!r})")
    return status


def _linux_scan() -> list[str]:
    result = _run(["nmcli", "-t", "-f", "SSID", "device", "wifi", "list"])
    if result.returncode != 0:
        return []
    seen: set[str] = set()
    names: list[str] = []
    for line in result.stdout.splitlines():
        name = line.strip()
        if name and name not in seen:
            seen.add(name)
            names.append(name)
    return names


def wifi_backend() -> str:
    system = platform.system()
    if system == "Darwin":
        return "networksetup"
    if system == "Linux" and _nmcli_available():
        return "nmcli"
    raise WifiError(
        f"บังคับ join Wi‑Fi ยังไม่รองรับบน {system} "
        "(macOS ใช้ networksetup, Linux ใช้ nmcli)"
    )


def status(device: str | None = None) -> WifiStatus:
    backend = wifi_backend()
    if backend == "networksetup":
        return _macos_status(device)
    return _linux_status()


def list_networks(device: str | None = None) -> list[str]:
    backend = wifi_backend()
    if backend == "networksetup":
        return _macos_preferred(device)
    return _linux_scan()


def join(
    ssid: str,
    password: str | None = None,
    *,
    device: str | None = None,
    timeout: float = 25.0,
) -> WifiStatus:
    from gadgetpanda.license import require as require_license

    require_license("drone.wifi")
    ssid = ssid.strip()
    if not ssid:
        raise WifiError("ต้องใส่ SSID")
    backend = wifi_backend()
    if backend == "networksetup":
        return _macos_join(ssid, password, device, timeout)
    return _linux_join(ssid, password, timeout)


async def ensure_joined(
    ssid: str,
    password: str | None = None,
    *,
    device: str | None = None,
    timeout: float = 25.0,
    settle: float = 2.0,
) -> WifiStatus:
    """Join AP off the event loop thread, then wait briefly for DHCP."""
    status_now = await asyncio.to_thread(status, device)
    if status_now.ssid == ssid:
        return status_now
    joined = await asyncio.to_thread(join, ssid, password, device=device, timeout=timeout)
    if settle > 0:
        await asyncio.sleep(settle)
    return joined
