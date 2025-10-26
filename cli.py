#!/usr/bin/env python3
"""
DynamicKey — Privacy-First Keystroke Dynamics CLI

This tool measures keystroke dynamics — the time intervals between key presses —
to generate local JSON and HTML reports. It’s ethical, privacy-respecting,
and does not require any backend server.

Features:
- Capture keystroke timing data for a prompted phrase (multiple rounds)
- Store only anonymized key identifiers (SHA256 with ephemeral salt)
- Compute per-round and aggregate statistics (inter-key intervals, key hold times)
- Export detailed JSON and HTML reports
- Optionally send summarized results to a Discord webhook (no raw key data)

Usage Example:
  python cli.py --phrase "the quick brown fox" --rounds 5
"""

import argparse
import datetime
import hashlib
import json
import sys
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, asdict
from statistics import mean, pstdev

try:
    from pynput import keyboard
except ImportError:
    print("pynput is required. Install it via: pip install pynput")
    sys.exit(1)

try:
    import requests
except ImportError:
    requests = None


@dataclass
class KeyEvent:
    event: str  # 'down' or 'up'
    key_hash: str
    timestamp: float


@dataclass
class RoundResult:
    round_index: int
    phrase: str
    start_time: float
    end_time: float
    duration: float
    inter_key_intervals: list
    key_hold_times: dict


class KeystrokeCapture:
    def __init__(self, anonymize=True):
        self.salt = uuid.uuid4().hex if anonymize else ""
        self.anonymize = anonymize
        self.events = []
        self._down_timestamps = {}

    def _hash_key(self, key_name: str) -> str:
        if not self.anonymize:
            return key_name
        h = hashlib.sha256()
        h.update((self.salt + "::" + key_name).encode("utf-8"))
        return h.hexdigest()

    def on_press(self, key):
        name = getattr(key, "char", None) or str(key)
        key_h = self._hash_key(name)
        ts = time.perf_counter()
        self.events.append(KeyEvent("down", key_h, ts))
        self._down_timestamps[key_h] = ts

    def on_release(self, key):
        name = getattr(key, "char", None) or str(key)
        key_h = self._hash_key(name)
        ts = time.perf_counter()
        self.events.append(KeyEvent("up", key_h, ts))
        if key_h in self._down_timestamps:
            del self._down_timestamps[key_h]

    def clear(self):
        self.events.clear()
        self._down_timestamps.clear()


def compute_round_features(events: list):
    key_hold_times = defaultdict(list)
    inter_key_intervals = []
    last_down_ts = None
    down_map = {}

    for ev in events:
        if ev.event == "down":
            if last_down_ts is not None:
                inter_key_intervals.append(ev.timestamp - last_down_ts)
            last_down_ts = ev.timestamp
            down_map[ev.key_hash] = ev.timestamp
        elif ev.event == "up" and ev.key_hash in down_map:
            hold = ev.timestamp - down_map[ev.key_hash]
            if hold >= 0:
                key_hold_times[ev.key_hash].append(hold)
            del down_map[ev.key_hash]

    return inter_key_intervals, dict(key_hold_times)


def make_json_report(all_rounds, metadata):
    out = {"metadata": metadata, "rounds": []}
    all_intervals = []
    aggregate_key_holds = defaultdict(list)

    for r in all_rounds:
        out["rounds"].append(asdict(r))
        all_intervals.extend(r.inter_key_intervals)
        for k, holds in r.key_hold_times.items():
            aggregate_key_holds[k].extend(holds)

    def summarize_list(lst):
        if not lst:
            return {"count": 0}
        return {
            "count": len(lst),
            "mean": mean(lst),
            "stdev": pstdev(lst) if len(lst) > 1 else 0.0,
            "min": min(lst),
            "max": max(lst),
        }

    out["aggregate"] = {
        "inter_key_intervals": summarize_list(all_intervals),
        "key_hold_times": {k: summarize_list(v) for k, v in aggregate_key_holds.items()},
    }
    return out


HTML_TEMPLATE = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>DynamicKey Report</title>
  <style>
    body{{font-family:Arial,sans-serif;padding:20px}}
    table{{border-collapse:collapse;width:100%;margin-bottom:20px}}
    th,td{{border:1px solid #ddd;padding:8px}}
    th{{background:#f4f4f4}}
    .stat{{font-family:monospace}}
  </style>
</head>
<body>
<h1>DynamicKey — Keystroke Dynamics Report</h1>
<p><strong>Session:</strong> {session_id}</p>
<p><strong>Captured:</strong> {captured_on}</p>

<h2>Rounds</h2>
{rounds_table}

<h2>Aggregate Statistics</h2>
{aggregate_section}
</body></html>
"""


def rounds_table_html(rounds):
    rows = [
        f"<tr><td>{r.round_index}</td><td class='stat'>{r.duration:.4f}s</td><td>{len(r.inter_key_intervals)}</td><td>{len(r.key_hold_times)}</td></tr>"
        for r in rounds
    ]
    return f"<table><thead><tr><th>Round</th><th>Duration</th><th>Intervals</th><th>Distinct Keys</th></tr></thead><tbody>{''.join(rows)}</tbody></table>"


def aggregate_section_html(aggregate):
    ik = aggregate.get("inter_key_intervals", {})
    ik_html = (
        f"<p>Inter-key intervals: mean={ik.get('mean', 0):.4f}s "
        f"stdev={ik.get('stdev', 0):.4f}s (n={ik.get('count', 0)})</p>"
    )
    keys_html = "<ul>" + "".join(
        f"<li>{k[:8]}... — mean={v.get('mean', 0):.4f}s</li>"
        for k, v in aggregate.get("key_hold_times", {}).items()
    ) + "</ul>"
    return ik_html + keys_html


def send_discord_summary(webhook_url, report):
    import requests, datetime, random

    meta = report["metadata"]
    agg = report["aggregate"]["inter_key_intervals"]

    rounds = len(report["rounds"])
    mean_interval = agg["mean"]
    total_keys = sum(len(r["inter_key_intervals"]) for r in report["rounds"])
    duration = sum(r["duration"] for r in report["rounds"])

    colors = [0x00BFFF, 0x7289DA, 0x2ECC71, 0xF1C40F, 0xE67E22]
    color = random.choice(colors)

    embed = {
        "title": "🎹 DynamicKey — Session Summary",
        "description": "Keystroke dynamics analysis complete.",
        "color": color,
        "fields": [
            {"name": "🆔 Session", "value": f"`{meta['session_id']}`", "inline": False},
            {"name": "📦 Rounds", "value": str(rounds), "inline": True},
            {"name": "⌨️ Total Keys", "value": str(total_keys), "inline": True},
            {"name": "⏱️ Total Duration (s)", "value": f"{duration:.2f}", "inline": True},
            {"name": "⚙️ Mean Interval (s)", "value": f"{mean_interval:.4f}", "inline": True},
        ],
        "footer": {"text": "DynamicKey • Privacy Preserved"},
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
    }

    data = {"embeds": [embed]}
    response = requests.post(webhook_url, json=data)
    if response.status_code != 204 and response.status_code != 200:
        print(f"[!] Discord webhook failed: {response.status_code} - {response.text}")
    else:
        print("✅ Summary sent to Discord successfully.")

def main():
    parser = argparse.ArgumentParser(description="DynamicKey — Privacy-First Keystroke Dynamics CLI")
    parser.add_argument("--phrase", default="the quick brown fox", help="Phrase to type")
    parser.add_argument("--rounds", type=int, default=3, help="Number of rounds")
    parser.add_argument("--out-json", default="keystroke_report.json")
    parser.add_argument("--out-html", default="keystroke_report.html")
    parser.add_argument("--discord-webhook", default=None)
    parser.add_argument("--store-chars", action="store_true")
    args = parser.parse_args()

    anonymize = not args.store_chars
    if not anonymize:
        confirm = input("Type 'I CONSENT' to confirm you have permission to store raw characters: ")
        if confirm.strip() != "I CONSENT":
            print("Consent not given. Exiting.")
            return

    cap = KeystrokeCapture(anonymize=anonymize)
    listener = keyboard.Listener(on_press=cap.on_press, on_release=cap.on_release)
    listener.start()

    all_rounds = []
    session_id = uuid.uuid4().hex
    metadata = {
        "session_id": session_id,
        "phrase": args.phrase,
        "rounds_requested": args.rounds,
        "anonymized_keys": anonymize,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    print(f"Phrase: {args.phrase}")
    print(f"Rounds: {args.rounds}")
    print("Press ENTER to start a round, type the phrase, and press ENTER again to finish.\n")

    try:
        for round_idx in range(1, args.rounds + 1):
            input(f"Round {round_idx}: Press ENTER to start...")
            cap.clear()
            print(f"Type the phrase now: '{args.phrase}'")
            start_time = time.perf_counter()
            input()  # Wait for user to finish typing and press ENTER
            end_time = time.perf_counter()

            round_events = cap.events.copy()
            duration = end_time - start_time
            inter_key_intervals, key_hold_times = compute_round_features(round_events)

            round_result = RoundResult(
                round_index=round_idx,
                phrase=args.phrase,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                inter_key_intervals=inter_key_intervals,
                key_hold_times=key_hold_times,
            )
            all_rounds.append(round_result)
            print(f"Round {round_idx} completed in {duration:.4f} seconds.\n")
    except KeyboardInterrupt:
        print("\nInterrupted. Saving what was captured.")
    finally:
        listener.stop()

    # Write JSON report
    report = make_json_report(all_rounds, metadata)
    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nJSON saved to {args.out_json}")

    # Write HTML report
    html = HTML_TEMPLATE.format(
        session_id=session_id,
        captured_on=metadata["created_at"],
        rounds_table=rounds_table_html(all_rounds),
        aggregate_section=aggregate_section_html(report["aggregate"]),
    )
    with open(args.out_html, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML saved to {args.out_html}")

    # Send to Discord if webhook provided
    if args.discord_webhook:
        send_discord_summary(args.discord_webhook, report)
        print("Summary sent to Discord.")

    print("\n✅ Done — data stored locally. Keep it private.")


if __name__ == "__main__":
    main()
