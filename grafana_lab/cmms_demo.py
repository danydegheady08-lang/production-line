"""Exercise 6.3: a CMMS work order puts the line into Scheduled Downtime.
Runs offline (no InfluxDB) so the logic can be checked on its own."""
import random

STATES = ["Productive", "Standby", "Unscheduled Downtime"]
WEIGHTS = [0.85, 0.10, 0.05]
PM_EVERY = 120      # seconds: the CMMS issues a preventive work order
PM_LENGTH = 15      # seconds the maintenance window lasts


def machine_state(t, rng):
    """Scheduled window first, because a work order beats random behaviour."""
    if t % PM_EVERY >= PM_EVERY - PM_LENGTH:
        return "Scheduled Downtime"
    return rng.choices(STATES, weights=WEIGHTS)[0]


def oee_view(counts, total):
    scheduled = counts.get("Scheduled Downtime", 0)
    productive = counts.get("Productive", 0)
    planned = total - scheduled                 # planned production time
    return {
        "naive availability (scheduled counted as loss)": productive / total,
        "availability (scheduled excluded)": productive / planned,
        "share of time lost to scheduled downtime": scheduled / total,
    }


if __name__ == "__main__":
    rng = random.Random(42)
    total = 600
    counts = {}
    for t in range(total):
        s = machine_state(t, rng)
        counts[s] = counts.get(s, 0) + 1
    print("seconds per state over", total, "s:")
    for k, v in sorted(counts.items()):
        print(f"  {k:<22} {v:4d}  {v / total:6.1%}")
    for k, v in oee_view(counts, total).items():
        print(f"{k}: {v:.1%}")
