"""
TrafficIntelli ingestion test harness (no hardware required).

Posts Arduino-format CYCLE packets to POST /traffic/cycle with
source=SIMULATED, then checks the HTTP response AND the resulting
PostgreSQL state. Rows it creates are labelled SIMULATED, never REAL.

Usage (backend must be running):
    python test_cycle_ingest.py [base_url]
    python test_cycle_ingest.py http://127.0.0.1:8000
"""

import sys
import json
import random
import urllib.request
import urllib.error

from sqlalchemy import text

from database import engine


BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
URL = f"{BASE_URL}/traffic/cycle?source=SIMULATED"


def build_packet(cycle_number, counts, cleared, remaining):
    """Builds a packet exactly as sendCycleData() in sketch_apr6a.ino does."""
    total = sum(counts)
    extra = [(c * 30) // total if total else 0 for c in counts]
    green = [30 + e for e in extra]
    density = ["LOW" if c <= 10 else "MEDIUM" if c <= 20 else "HIGH" for c in counts]
    fields = (
        ["CYCLE", cycle_number, sum(green)]
        + counts + density + green + extra + cleared + remaining
        + [0, 0, 0]
    )
    return "|".join(str(f) for f in fields)


def post(body):
    req = urllib.request.Request(URL, data=body.encode(), method="POST",
                                 headers={"Content-Type": "text/plain"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def db_row(cycle_id):
    with engine.connect() as c:
        return c.execute(
            text("SELECT cycle_id, cycle_number, total_count, data_source "
                 "FROM traffic_cycles WHERE cycle_id = :id"), {"id": cycle_id}
        ).fetchone()


def check(name, ok):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    return ok


def main():
    results = []
    # Random counts make each run's packet unique, so reruns are not duplicates.
    counts = [random.randint(0, 25) for _ in range(4)]
    packet = build_packet(1, counts, [1, 0, 2, 0], counts)
    print("Packet:", packet, f"({len(packet.split('|'))} fields)")

    code, body = post(packet)
    print("  ->", code, body)
    inserted = code == 201 and body.get("status") == "inserted"
    results.append(check("valid packet inserted (HTTP 201)", inserted))
    if inserted:
        row = db_row(body["cycle_id"])
        print("  DB:", row)
        results.append(check("row exists in PostgreSQL as SIMULATED",
                             row is not None and row.data_source == "SIMULATED"
                             and row.total_count == sum(counts)))

    code, body = post(packet)
    print("  ->", code, body)
    results.append(check("identical retransmission -> duplicate (HTTP 200, inserted=false)",
                         code == 200 and body.get("status") == "duplicate"
                         and body.get("inserted") is False))

    # Same cycle number, different traffic: what an Arduino reset produces.
    counts2 = [c + 1 for c in counts]
    code, body = post(build_packet(1, counts2, [0, 0, 0, 0], counts2))
    print("  ->", code, body)
    results.append(check("same cycle_number, new data (Arduino reset) -> inserted",
                         code == 201 and body.get("status") == "inserted"))

    code, body = post(packet.rsplit("|", 1)[0])
    print("  ->", code, body)
    results.append(check("29-field packet -> HTTP 400", code == 400))

    bad = packet.split("|")
    bad[3] = ""
    code, body = post("|".join(bad))
    print("  ->", code, body)
    results.append(check("empty field -> HTTP 400", code == 400))

    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
