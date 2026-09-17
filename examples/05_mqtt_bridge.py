"""Forward heart rate and IMU magnitude to MQTT.

  pip install 'gadgetpanda[mqtt]'
  mosquitto_sub -t 'panda/#' -v
"""

from __future__ import annotations

import asyncio
import json
import math
import os

from gadgetpanda import Ring

try:
    import paho.mqtt.client as mqtt
except ImportError as exc:
    raise SystemExit("pip install 'gadgetpanda[mqtt]'") from exc


HOST = os.environ.get("PANDA_MQTT_HOST", "localhost")
PORT = int(os.environ.get("PANDA_MQTT_PORT", "1883"))
TOPIC = os.environ.get("PANDA_MQTT_TOPIC", "panda")


async def main() -> None:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(HOST, PORT)
    client.loop_start()

    ring = await Ring.find()

    def publish(kind: str, payload: dict) -> None:
        client.publish(f"{TOPIC}/{kind}", json.dumps(payload))

    ring.on("heart_rate", lambda sample: publish("heart_rate", {"bpm": sample.bpm}))
    ring.on("sport", lambda sport: publish("sport", {"steps": sport.steps, "kcal": sport.calories_kcal}))
    ring.on("health", lambda health: publish("health", {"stress": health.stress, "vo2max": health.vo2max}))
    ring.on("temperature", lambda temp: publish("temperature", {"body_c": temp.body_c}))
    ring.on("spo2", lambda spo2: publish("spo2", {"spo2": spo2.spo2, "on_wrist": spo2.on_wrist}))
    ring.on("ppg", lambda samples: publish("ppg", {"values": [item.value for item in samples]}))
    ring.on(
        "raw",
        lambda frame: publish(
            "imu",
            {
                "count": len(frame.imu),
                "mag": [
                    math.sqrt(s.acc_x**2 + s.acc_y**2 + s.acc_z**2)
                    for s in frame.imu[:4]
                ],
            },
        ),
    )

    async with ring:
        await ring.start_realtime()
        print(f"mqtt {HOST}:{PORT}  topic {TOPIC}/#")
        await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nbye")
