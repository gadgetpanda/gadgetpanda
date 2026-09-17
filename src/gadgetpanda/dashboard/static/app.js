const HISTORY = 96;
const PPG_HISTORY = 220;

const GROUPS = {
  "vitals-grid": [
    { key: "hr", label: "ชีพจร", en: "Heart rate", unit: "bpm", color: "#e11d2e", large: true },
    { key: "hrv", label: "HRV", en: "SDNN", unit: "ms", color: "#b8a3c7" },
    { key: "spo2", label: "ออกซิเจน", en: "SpO₂", unit: "%", color: "#5ec8c0" },
    { key: "battery", label: "แบตเตอรี่", en: "Battery", unit: "%", color: "#c9a227" },
  ],
  "temp-grid": [
    { key: "body", label: "อุณหภูมิกาย", en: "Body", unit: "°C", color: "#e11d2e" },
    { key: "wrist", label: "ข้อมือ", en: "Wrist", unit: "°C", color: "#c9a227" },
    { key: "ambient", label: "อากาศ", en: "Ambient", unit: "°C", color: "#5ec8c0" },
  ],
  "activity-grid": [
    { key: "steps", label: "ก้าว", en: "Steps", unit: "", color: "#3dd68c" },
    { key: "distance", label: "ระยะทาง", en: "Distance", unit: "m", color: "#5ec8c0" },
    { key: "calories", label: "แคลอรี่", en: "Calories", unit: "kcal", color: "#c9a227" },
  ],
  "wellness-grid": [
    { key: "stress", label: "ความเครียด", en: "Stress", unit: "", color: "#e11d2e" },
    { key: "vo2", label: "VO₂ max", en: "Aerobic", unit: "", color: "#5ec8c0" },
    { key: "breath", label: "หายใจ", en: "Breath", unit: "/min", color: "#b8a3c7" },
    { key: "emotion", label: "อารมณ์", en: "Emotion", unit: "", color: "#c9a227" },
    { key: "stamina", label: "ความทน", en: "Stamina", unit: "", color: "#3dd68c" },
  ],
};

const series = {};
const cards = {};
const state = { hints: {}, mode: "all", socket: null, lastSpo2: null };

function makeCard(spec) {
  const article = document.createElement("article");
  article.className = spec.large ? "card large" : "card";
  article.innerHTML = `
    <div class="label"><b>${spec.label}</b><span>${spec.en}</span></div>
    <div class="value" id="val-${spec.key}">—<small>${spec.unit}</small></div>
    <div class="hint" id="hint-${spec.key}"></div>
    <canvas id="chart-${spec.key}" height="64"></canvas>
  `;
  series[spec.key] = { values: [], color: spec.color, canvas: null };
  return article;
}

for (const [id, specs] of Object.entries(GROUPS)) {
  const root = document.getElementById(id);
  for (const spec of specs) {
    const card = makeCard(spec);
    root.appendChild(card);
    series[spec.key].canvas = card.querySelector("canvas");
    cards[spec.key] = spec;
  }
}

class Trend {
  constructor(canvas, colors, limit = HISTORY) {
    this.canvas = canvas;
    this.colors = Array.isArray(colors) ? colors : [colors];
    this.limit = limit;
    this.lanes = this.colors.map(() => []);
  }

  push(values) {
    const next = Array.isArray(values) ? values : [values];
    next.forEach((value, index) => {
      if (value == null || Number.isNaN(value)) return;
      this.lanes[index] = this.lanes[index] || [];
      this.lanes[index].push(Number(value));
      if (this.lanes[index].length > this.limit) this.lanes[index].shift();
    });
    this.draw();
  }

  draw() {
    if (!this.canvas) return;
    const ctx = this.canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    const width = Math.max(this.canvas.clientWidth || this.canvas.width || 320, 32);
    const height = Math.max(this.canvas.clientHeight || this.canvas.height || 120, 32);
    this.canvas.width = Math.floor(width * dpr);
    this.canvas.height = Math.floor(height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);
    const all = this.lanes.flat();
    if (!all.length) return;
    const min = Math.min(...all);
    const max = Math.max(...all);
    const pad = max === min ? Math.abs(max) * 0.08 || 1 : (max - min) * 0.18;
    const lo = min - pad;
    const hi = max + pad;
    this.lanes.forEach((lane, index) => this._stroke(ctx, lane, this.colors[index] || this.colors[0], width, height, lo, hi, index === 0));
  }

  _stroke(ctx, lane, color, width, height, lo, hi, fill) {
    if (lane.length < 2) return;
    ctx.beginPath();
    lane.forEach((value, index) => {
      const x = (index / (this.limit - 1)) * (width - 2) + 1;
      const y = height - 4 - ((value - lo) / (hi - lo)) * (height - 8);
      if (index === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.6;
    ctx.lineJoin = "round";
    ctx.stroke();
    if (fill) {
      const lastX = ((lane.length - 1) / (this.limit - 1)) * (width - 2) + 1;
      ctx.lineTo(lastX, height);
      ctx.lineTo(1, height);
      ctx.closePath();
      const gradient = ctx.createLinearGradient(0, 0, 0, height);
      gradient.addColorStop(0, color + "55");
      gradient.addColorStop(1, color + "00");
      ctx.fillStyle = gradient;
      ctx.fill();
    }
  }
}

const charts = {};
for (const [key, item] of Object.entries(series)) {
  charts[key] = new Trend(item.canvas, item.color);
}
const accChart = new Trend(document.getElementById("acc-chart"), ["#e11d2e", "#c9a227", "#5ec8c0"]);
const gyroChart = new Trend(document.getElementById("gyro-chart"), ["#e11d2e", "#c9a227", "#5ec8c0"]);
const ppgChart = new Trend(document.getElementById("ppg-chart"), "#c8102e", PPG_HISTORY);

function setValue(key, value, digits = 0) {
  const node = document.getElementById(`val-${key}`);
  if (!node || value == null) return;
  const shown = typeof value === "number" ? (digits ? value.toFixed(digits) : Math.round(value).toString()) : value;
  node.innerHTML = `${shown}<small>${cards[key]?.unit || ""}</small>`;
}

function setHint(key, text) {
  const node = document.getElementById(`hint-${key}`);
  if (node) node.textContent = text || "";
}

function pushMetric(key, value, digits = 0) {
  if (value == null) return;
  if (key === "spo2") state.lastSpo2 = value;
  setValue(key, value, digits);
  charts[key]?.push(value);
}

function setStatus(payload) {
  const pill = document.getElementById("status-pill");
  const label = document.getElementById("status-label");
  const stateName = payload.state || "idle";
  pill.dataset.state = stateName;
  const labels = {
    idle: "รอเชื่อมต่อ",
    connecting: "กำลังต่อแหวน",
    live: "เชื่อมต่อแล้ว",
    demo: "โหมดสาธิต",
    error: payload.error || "เชื่อมต่อไม่ได้",
    disconnected: "หลุดการเชื่อมต่อ",
  };
  label.textContent = labels[stateName] || stateName;
  if (payload.name) document.getElementById("ring-name").textContent = payload.name;
  if (payload.address) document.getElementById("ring-addr").textContent = payload.address;
}

function renderFacts(info, user) {
  const facts = [];
  const source = info || {};
  const labels = {
    model: "รุ่น",
    firmware: "เฟิร์มแวร์",
    hardware: "ฮาร์ดแวร์",
    software: "ซอฟต์แวร์",
    vendor: "ผู้ผลิต",
    serial: "ซีเรียล",
  };
  for (const [key, label] of Object.entries(labels)) {
    if (source[key]) facts.push([label, source[key]]);
  }
  if (user) {
    facts.push(["อายุ", `${user.age}`], ["น้ำหนัก", `${user.weight_kg} kg`], ["ส่วนสูง", `${user.height_cm} cm`]);
    fillUserForm(user);
  }
  document.getElementById("facts").innerHTML = facts
    .map(([label, value]) => `<div><dt>${label}</dt><dd>${value}</dd></div>`)
    .join("");
}

function fillUserForm(user) {
  const age = document.getElementById("user-age");
  const weight = document.getElementById("user-weight");
  const height = document.getElementById("user-height");
  const sex = document.getElementById("user-sex");
  if (age && user.age != null) age.value = user.age;
  if (weight && user.weight_kg != null) weight.value = user.weight_kg;
  if (height && user.height_cm != null) height.value = user.height_cm;
  if (sex && (user.sex === 0 || user.sex === 1)) sex.value = String(user.sex);
}

function setUserStatus(ok, text) {
  const node = document.getElementById("user-status");
  if (!node) return;
  node.textContent = text || "";
  node.classList.toggle("is-ok", ok === true);
  node.classList.toggle("is-bad", ok === false);
}

let latestInfo = {};
let latestUser = null;

function listHtml(items) {
  if (!items?.length) return "<li>—</li>";
  return items.map((item) => `<li>${item}</li>`).join("");
}

function flagHtml(flags = {}) {
  const rows = [
    ["PPG/IMU raw", !!flags.raw],
    ["SpO₂", !!flags.spo2],
    ["โพลกีฬา/สุขภาพ", !!flags.poll],
    [`ชีพจร: ${flags.hr || "off"}`, flags.hr && flags.hr !== "off"],
  ];
  return rows
    .map(
      ([label, on]) =>
        `<span class="mode-flag ${on ? "on" : "off"}">${label}${on ? "" : " · ปิด"}</span>`
    )
    .join("");
}

function renderModeBoard(modes, activeId) {
  const board = document.getElementById("mode-board");
  if (!board) return;
  // Prefer highlighting static cards already in HTML so text always shows.
  const cards = board.querySelectorAll(".mode-card[data-mode]");
  if (cards.length) {
    cards.forEach((card) => {
      const on = card.dataset.mode === activeId;
      card.classList.toggle("is-on", on);
      const stateNode = card.querySelector(".mode-card-state");
      if (stateNode) stateNode.textContent = on ? "กำลังใช้" : "เลือก";
    });
    return;
  }
  if (!modes?.length) {
    board.innerHTML = "";
    return;
  }
  board.innerHTML = modes
    .map((item) => {
      const on = item.id === activeId ? " is-on" : "";
      return `<article class="mode-card${on}" data-mode="${item.id}" role="button" tabindex="0">
        <header>
          <div>
            <strong>${item.label}</strong>
            <small>${item.en}</small>
          </div>
          <span class="mode-card-state">${on ? "กำลังใช้" : "เลือก"}</span>
        </header>
        <p class="mode-card-hint">${item.hint || ""}</p>
        <div class="mode-card-cols">
          <div>
            <h4>ดึงได้</h4>
            <ul>${listHtml(item.gets)}</ul>
          </div>
          <div>
            <h4>เงื่อนไข</h4>
            <ul>${listHtml(item.needs)}</ul>
          </div>
          <div class="skip">
            <h4>ไม่ได้</h4>
            <ul>${listHtml(item.skips)}</ul>
          </div>
        </div>
        <div class="mode-flags">${flagHtml(item.flags)}</div>
      </article>`;
    })
    .join("");
}

function renderModeGuide(payload) {
  const name = document.getElementById("mode-guide-name");
  const hint = document.getElementById("mode-hint");
  const gets = document.getElementById("mode-gets");
  const needs = document.getElementById("mode-needs");
  const skips = document.getElementById("mode-skips");
  const flags = document.getElementById("mode-flags");
  if (name) name.textContent = `${payload.label || "—"} · ${payload.en || ""}`;
  if (hint) hint.textContent = payload.hint || "";
  if (gets) gets.innerHTML = listHtml(payload.gets);
  if (needs) needs.innerHTML = listHtml(payload.needs);
  if (skips) skips.innerHTML = listHtml(payload.skips);
  if (flags) flags.innerHTML = flagHtml(payload.flags);
  renderModeBoard(payload.modes || [], payload.mode);
}

function renderModes(payload) {
  const root = document.getElementById("mode-chips");
  state.mode = payload.mode || "all";
  renderModeGuide(payload);
  if (payload.modes?.length) {
    root.innerHTML = payload.modes
      .map(
        (item) =>
          `<button type="button" class="chip${item.id === state.mode ? " is-on" : ""}" data-mode="${item.id}" title="${item.hint || ""}">
            ${item.label}<small>${item.en}</small>
          </button>`
      )
      .join("");
  } else {
    root.querySelectorAll(".chip").forEach((chip) => chip.classList.toggle("is-on", chip.dataset.mode === state.mode));
  }
  const open = new Set(payload.sections || []);
  document.querySelectorAll("[data-section]").forEach((section) => {
    section.classList.toggle("is-off", open.size > 0 && !open.has(section.dataset.section));
  });
  if (state.mode === "all" || state.mode === "ppg" || state.mode === "motion") {
    state.lastSpo2 = null;
    setValue("spo2", "—");
    setHint("spo2", "ใช้โหมดสัญญาณชีพเพื่อวัด SpO₂");
  }
  if (state.mode === "vitals") {
    setHint("spo2", "สวมแน่น นิ่งๆ จนขึ้น %");
  }
  if (state.mode === "hr") {
    setHint("hr", "จาก BLE Heart Rate Service");
  }
  if (state.mode === "ppg") {
    setHint("hr", "ประมาณจากคลื่น PPG");
  }
}

function chooseMode(mode) {
  if (!mode || !state.socket || state.socket.readyState !== WebSocket.OPEN) return;
  state.socket.send(JSON.stringify({ type: "set_mode", mode }));
}

function handle(message) {
  switch (message.type) {
    case "mode":
      renderModes(message);
      break;
    case "status":
    case "connected":
      setStatus(message.type === "connected" ? { state: "live", ...message } : message);
      if (message.name) document.getElementById("ring-name").textContent = message.name;
      if (message.address) document.getElementById("ring-addr").textContent = message.address;
      break;
    case "disconnected":
      setStatus({ state: "disconnected" });
      break;
    case "info":
      latestInfo = message.info || {};
      renderFacts(latestInfo, latestUser);
      break;
    case "user":
      latestUser = message;
      renderFacts(latestInfo, latestUser);
      break;
    case "user_status":
      setUserStatus(message.ok, message.ok ? "บันทึกลงแหวนแล้ว" : (message.error || "บันทึกไม่สำเร็จ"));
      break;
    case "battery":
      pushMetric("battery", message.value);
      break;
    case "heart_rate":
      pushMetric("hr", message.bpm);
      if (message.source === "ppg") {
        setHint("hr", "ประมาณจากคลื่น PPG");
      } else {
        setHint("hr", message.rr?.length ? `RR ${message.rr.join(" · ")}` : "จากเซ็นเซอร์ชีพจร");
      }
      break;
    case "hrv":
      pushMetric("hrv", message.sdnn_ms, 1);
      setHint("hrv", `${message.samples} samples`);
      break;
    case "spo2":
      if (message.enabled && !(message.spo2 > 0)) {
        setValue("spo2", "…");
        setHint("spo2", message.on_wrist ? "กำลังวัด… สวมแน่น นิ่งๆ" : "สวมแหวนให้แน่นแล้วรอ");
      } else if (message.spo2 > 0) {
        pushMetric("spo2", message.spo2);
        setHint(
          "spo2",
          message.enabled
            ? (message.on_wrist ? "บนนิ้วแล้ว" : "ยังไม่ตรวจบนนิ้ว")
            : "ค้างล่าสุด · กำลังดึงชีพจร"
        );
      }
      break;
    case "optical_contact":
      if (!(state.lastSpo2 > 0)) {
        setValue("spo2", "…");
        setHint("spo2", message.on_wrist ? "ตรวจจับนิ้วแล้ว กำลังคำนวณ…" : "สวมแหวนให้แน่นแล้วรอ");
      }
      break;
    case "temperature":
      pushMetric("body", message.body_c, 1);
      pushMetric("wrist", message.wrist_c, 1);
      pushMetric("ambient", message.ambient_c, 1);
      break;
    case "sport":
      pushMetric("steps", message.steps);
      pushMetric("distance", message.distance_m, 1);
      pushMetric("calories", message.calories_kcal, 1);
      break;
    case "health":
      pushMetric("vo2", message.vo2max);
      pushMetric("breath", message.breath_rate);
      pushMetric("emotion", message.emotion);
      pushMetric("stress", message.stress);
      pushMetric("stamina", message.stamina);
      break;
    case "imu":
      accChart.push(message.acc);
      gyroChart.push(message.gyro);
      document.getElementById("acc-readout").textContent =
        `X ${message.acc[0]}   Y ${message.acc[1]}   Z ${message.acc[2]}`;
      document.getElementById("gyro-readout").textContent =
        `X ${message.gyro[0]}   Y ${message.gyro[1]}   Z ${message.gyro[2]}`;
      break;
    case "ppg":
      for (const value of message.values || []) ppgChart.push(value);
      if (message.values?.length) {
        document.getElementById("ppg-value").textContent = message.values.at(-1);
      }
      document.getElementById("ppg-flag").textContent = message.flag != null ? `flag ${message.flag}` : "";
      break;
    default:
      break;
  }
}

function connect() {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${location.host}/ws`);
  state.socket = socket;
  socket.onmessage = (event) => handle(JSON.parse(event.data));
  socket.onclose = () => setTimeout(connect, 1200);
}

document.getElementById("mode-chips")?.addEventListener("click", (event) => {
  const chip = event.target.closest("[data-mode]");
  if (chip) chooseMode(chip.dataset.mode);
});

document.getElementById("mode-board")?.addEventListener("click", (event) => {
  const card = event.target.closest(".mode-card[data-mode]");
  if (card) chooseMode(card.dataset.mode);
});

document.getElementById("mode-board")?.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" && event.key !== " ") return;
  const card = event.target.closest(".mode-card[data-mode]");
  if (!card) return;
  event.preventDefault();
  chooseMode(card.dataset.mode);
});

document.getElementById("user-form").addEventListener("submit", (event) => {
  event.preventDefault();
  if (!state.socket || state.socket.readyState !== WebSocket.OPEN) {
    setUserStatus(false, "ยังไม่ต่อแดชบอร์ด");
    return;
  }
  const sex = document.getElementById("user-sex").value;
  state.socket.send(JSON.stringify({
    type: "set_user",
    age: Number(document.getElementById("user-age").value),
    weight_kg: Number(document.getElementById("user-weight").value),
    height_cm: Number(document.getElementById("user-height").value),
    sex: sex === "" ? null : Number(sex),
  }));
  setUserStatus(null, "กำลังบันทึก…");
});

function tickClock() {
  const now = new Date();
  document.getElementById("clock").textContent = now.toLocaleTimeString("th-TH", { hour12: false });
}

tickClock();
setInterval(tickClock, 1000);
connect();
window.addEventListener("resize", () => {
  Object.values(charts).forEach((chart) => chart.draw());
  accChart.draw();
  gyroChart.draw();
  ppgChart.draw();
});
