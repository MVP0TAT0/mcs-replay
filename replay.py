import json
import time

from pathlib import Path
from dataclasses import dataclass
from typing import List
from datetime import datetime, timezone

import paho.mqtt.client as mqtt


CONFIG_FILE = "config.json"


@dataclass(order=True)
class ReplayEvent:
    timestamp: float
    topic: str
    payload: str

class MQTTReplayApp:
    def __init__(self, config_path: str):
        self.config = self.load_config(config_path)
        self.mqtt_host = self.config["mqtt"]["host"]
        self.mqtt_port = self.config["mqtt"]["port"]
        self.messages_root = Path(self.config["messages_root"])
        self.speed = self.config.get("speed", 1.0)
        self.events: List[ReplayEvent] = []
        self.client = mqtt.Client()

    def load_config(self, path: str) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def parse_timestamp_from_filename(self, file_path: Path) -> float:
        timestamp_str = file_path.stem
        dt = datetime.strptime(
            timestamp_str,
            "%Y%m%dT%H%M%S.%fZ"
        )
        dt = dt.replace(tzinfo=timezone.utc)

        return dt.timestamp()

    def connect_mqtt(self):
        print(f"Connecting to MQTT broker {self.mqtt_host}:{self.mqtt_port}...")
        self.client.connect(self.mqtt_host, self.mqtt_port)
        self.client.loop_start()
        print("Connected.")

    def scan_messages(self):
        print(f"Scanning messages from: {self.messages_root}")
        if not self.messages_root.exists():
            raise FileNotFoundError(
                f"Messages root folder does not exist: {self.messages_root}"
            )
        files = sorted(self.messages_root.rglob("*"))
        for file_path in files:
            if not file_path.is_file():
                continue

            relative_parent = file_path.parent.relative_to(self.messages_root)
            topic = str(relative_parent).replace("\\", "/")

            try:
                timestamp = self.parse_timestamp_from_filename(file_path)
            except Exception:
                print(
                    f"Skipping file with invalid timestamp format: "
                    f"{file_path.name}"
                )
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    payload = f.read()
            except Exception as e:
                print(f"Failed to read file {file_path}: {e}")
                continue

            event = ReplayEvent(
                timestamp=timestamp,
                topic=topic,
                payload=payload,
            )

            self.events.append(event)

        self.events.sort()
        print(f"Loaded {len(self.events)} events.")

    def replay(self):
        if not self.events:
            print("No events to replay.")
            return

        first_timestamp = self.events[0].timestamp
        replay_start = time.monotonic()
        print("Starting replay...")

        for idx, event in enumerate(self.events):
            relative_offset = (
                (event.timestamp - first_timestamp)
                / self.speed
            )
            target_time = replay_start + relative_offset
            now = time.monotonic()
            sleep_time = target_time - now
            
            if sleep_time > 0:
                time.sleep(sleep_time)

            result = self.client.publish(
                event.topic,
                event.payload
            )

            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                print(
                    f"[{idx}] Failed to publish -> "
                    f"{event.topic}"
                )

        print("Replay finished.")

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()


def main():
    app = MQTTReplayApp(CONFIG_FILE)

    try:
        app.connect_mqtt()
        app.scan_messages()
        app.replay()

    except KeyboardInterrupt:
        print("\nInterrupted by user.")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        app.stop()


if __name__ == "__main__":
    main()