"""producer.py : Python -> InfluxDB, one row per second (lecture code).

Run:   python producer.py
Test without a database:   python producer.py --dry-run

Exercise 5.2 : change WEIGHTS to [0.50, 0.20, 0.30] and run it again.
Exercise 5.2 : set COUPLE_TEMPERATURE = True to let a stopped machine cool down.
"""
import sys
import time, math, random
from datetime import datetime, timezone

DRY_RUN = "--dry-run" in sys.argv

URL    = "http://localhost:8086"
TOKEN  = "my-super-secret-token"
ORG    = "lecture"
BUCKET = "factory"

LINE = "B"
WEIGHTS = [0.85, 0.10, 0.05]          # Productive, Standby, Unscheduled Downtime
COUPLE_TEMPERATURE = False            # lecture code: temperature ignores the state

if not DRY_RUN:
    from influxdb_client import InfluxDBClient, Point
    from influxdb_client.client.write_api import SYNCHRONOUS
    client = InfluxDBClient(url=URL, token=TOKEN, org=ORG)
    write = client.write_api(write_options=SYNCHRONOUS)

print("Sending data to InfluxDB. Ctrl+C to stop." if not DRY_RUN else "Dry run, nothing is written.")
t = 0
parts_total = 0
states = ["Productive", "Standby", "Unscheduled Downtime"]
temperature = 60.0
max_seconds = 20 if DRY_RUN else None

try:
    while max_seconds is None or t < max_seconds:
        state = random.choices(states, weights=WEIGHTS)[0]

        if COUPLE_TEMPERATURE:
            # a running machine heats towards its working point, a stopped one cools
            target = 60 + 5 * math.sin(t / 10) if state == "Productive" else 35
            temperature += (target - temperature) * 0.08 + random.uniform(-0.3, 0.3)
        else:
            temperature = 60 + 5 * math.sin(t / 10) + random.uniform(-0.3, 0.3)

        if random.random() < 0.4:
            parts_total += 1

        if not DRY_RUN:
            point = (
                Point("machine")
                .tag("line", LINE)
                .field("temperature", temperature)
                .field("parts_total", parts_total)
                .field("state", state)
                .time(datetime.now(timezone.utc))
            )
            write.write(bucket=BUCKET, record=point)
        print(f"t={t:4d}   T={temperature:5.2f}   parts={parts_total}   state={state}")
        t += 1
        time.sleep(0.05 if DRY_RUN else 1)
except KeyboardInterrupt:
    print("Stopped.")
finally:
    if not DRY_RUN:
        client.close()
