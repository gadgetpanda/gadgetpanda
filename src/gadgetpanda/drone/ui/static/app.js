const CENTER = 128;
const DEFLECTION = 70;

const state = {
  socket: null,
  axes: { roll: CENTER, pitch: CENTER, throttle: CENTER, yaw: CENTER },
  left: { x: 0, y: 0 },
  right: { x: 0, y: 0 },
  sending: false,
};

const el = {
  video: document.getElementById("video"),
  fallback: document.getElementById("video-fallback"),
  hint: document.getElementById("video-hint"),
  conn: document.getElementById("conn"),
  connLabel: document.getElementById("conn-label"),
  name: document.getElementById("drone-name"),
  addr: document.getElementById("drone-addr"),
  rtsp: document.getElementById("rtsp-url"),
  speed: document.getElementById("speed"),
};

function send(message) {
  if (!state.socket || state.socket.readyState !== WebSocket.OPEN) return;
  state.socket.send(JSON.stringify(message));
}

function clamp(v, min, max) {
  return Math.max(min, Math.min(max, v));
}

function axisFromNorm(v) {
  return Math.round(clamp(CENTER + v * DEFLECTION, 1, 255));
}

let axesTimer = null;
function pushAxes() {
  state.axes = {
    throttle: axisFromNorm(-state.left.y),
    yaw: axisFromNorm(state.left.x),
    pitch: axisFromNorm(-state.right.y),
    roll: axisFromNorm(state.right.x),
  };
  el.speed.textContent = `${Math.round(((state.axes.throttle - 1) / 254) * 100)}%`;
  if (axesTimer) return;
  axesTimer = setTimeout(() => {
    axesTimer = null;
    send({ type: "axes", ...state.axes });
  }, 40);
}

function bindStick(rootId, knobId, side) {
  const root = document.getElementById(rootId);
  const knob = document.getElementById(knobId);
  const ring = root.querySelector(".stick-ring");
  let active = false;

  function setFromEvent(ev) {
    const rect = ring.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const max = rect.width * 0.34;
    let x = (ev.clientX - cx) / max;
    let y = (ev.clientY - cy) / max;
    const mag = Math.hypot(x, y);
    if (mag > 1) {
      x /= mag;
      y /= mag;
    }
    state[side] = { x, y };
    knob.style.transform = `translate(calc(-50% + ${x * max}px), calc(-50% + ${y * max}px))`;
    pushAxes();
  }

  function reset() {
    active = false;
    state[side] = { x: 0, y: 0 };
    knob.style.transform = "translate(-50%, -50%)";
    pushAxes();
  }

  ring.addEventListener("pointerdown", (ev) => {
    active = true;
    ring.setPointerCapture(ev.pointerId);
    setFromEvent(ev);
  });
  ring.addEventListener("pointermove", (ev) => {
    if (!active) return;
    setFromEvent(ev);
  });
  ring.addEventListener("pointerup", reset);
  ring.addEventListener("pointercancel", reset);
  ring.addEventListener("pointerleave", (ev) => {
    if (active && ev.buttons === 0) reset();
  });
}

function setStatus(payload) {
  const connected = payload.state === "connected";
  el.conn.classList.toggle("on", connected);
  el.conn.classList.toggle("bad", payload.state === "error");
  const labels = {
    idle: "รอเชื่อมต่อ",
    connecting: "กำลังต่อ",
    connected: payload.demo ? "DEMO" : "เชื่อมต่อแล้ว",
    error: payload.error || "ผิดพลาด",
  };
  el.connLabel.textContent = labels[payload.state] || payload.state;
  if (payload.name) el.name.textContent = payload.name;
  if (payload.address) el.addr.textContent = payload.address;
  if (payload.rtsp) el.rtsp.textContent = payload.rtsp;
  if (payload.stream && !payload.demo) startVideo(payload.stream);
  if (payload.stream_error) {
    el.hint.textContent = payload.stream_error;
  }
  if (payload.demo) {
    el.hint.textContent = "โหมด demo — ไม่มี RTSP จริง";
  }
}

function startVideo(path) {
  const url = `${path}?t=${Date.now()}`;
  el.video.onload = () => {
    el.video.classList.add("is-live");
    el.fallback.classList.add("is-hidden");
  };
  el.video.onerror = () => {
    el.video.classList.remove("is-live");
    el.fallback.classList.remove("is-hidden");
    el.hint.textContent = "สตรีม RTSP ยังไม่ขึ้น — เช็ก ffmpeg / ต่อ Wi‑Fi โดรน";
  };
  el.video.src = url;
}

function connectWs() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${proto}://${location.host}/ws`);
  state.socket = socket;
  socket.addEventListener("open", () => {
    el.hint.textContent = "ws open · รอวิดีโอ";
  });
  socket.addEventListener("close", () => setTimeout(connectWs, 1200));
  socket.addEventListener("message", (ev) => {
    let message;
    try { message = JSON.parse(ev.data); } catch { return; }
    if (message.type === "status") setStatus(message);
    if (message.type === "catalog" && message.rtsp) el.rtsp.textContent = message.rtsp;
  });
}

document.querySelectorAll("[data-cmd]").forEach((btn) => {
  btn.addEventListener("click", () => send({ type: "command", name: btn.dataset.cmd }));
});
document.getElementById("btn-stop").addEventListener("click", () => send({ type: "stop" }));
document.getElementById("btn-back").addEventListener("click", () => {
  send({ type: "hover" });
});
document.getElementById("btn-rev").addEventListener("click", () => {
  // camera switch short UDP command
  send({ type: "raw", hex: "0602" });
});

bindStick("stick-left", "knob-left", "left");
bindStick("stick-right", "knob-right", "right");
connectWs();

// Prefer stream endpoint even before status arrives.
fetch("/api/stream-info")
  .then((r) => r.json())
  .then((info) => {
    if (info.rtsp) el.rtsp.textContent = info.rtsp;
    if (info.demo) {
      el.hint.textContent = "โหมด demo — ไม่มี RTSP จริง";
      return;
    }
    if (!info.ffmpeg) {
      el.hint.textContent = "ติดตั้ง UI extra: pip install 'gadgetpanda[ui]' (มี ffmpeg ใน wheel)";
      return;
    }
    if (info.stream_error) el.hint.textContent = info.stream_error;
    startVideo(info.stream || "/stream.mjpeg");
  })
  .catch(() => {});
