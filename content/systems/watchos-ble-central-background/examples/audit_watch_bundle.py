#!/usr/bin/env python3
"""Read-only audit of a built watch app. Passing is not a runtime guarantee."""
from __future__ import annotations

import argparse
import json
import plistlib
import subprocess
from pathlib import Path

EXTENDED_MODES = {"self-care", "mindfulness", "physical-therapy", "alarm"}


def audit(info: dict, entitlements: dict, mode: str = "workout") -> dict:
    checks = []
    def add(name, passed, detail):
        checks.append({"check": name, "passed": bool(passed), "detail": detail})
    purpose = lambda key: isinstance(info.get(key), str) and bool(info[key].strip())
    ui_modes = set(info.get("UIBackgroundModes", []))
    wk_modes = set(info.get("WKBackgroundModes", []))
    add("watch_bundle", "WatchOS" in info.get("CFBundleSupportedPlatforms", []), "Inspect the executable WatchOS bundle, not its iOS container or a framework.")
    add("bluetooth_purpose", purpose("NSBluetoothAlwaysUsageDescription"), "Bluetooth permission text must be present in the built bundle.")
    add("ble_background_declared", "bluetooth-central" in ui_modes, "Declares background BLE events; this alone does not provide continuous CPU runtime.")
    add("single_extended_type", len(wk_modes & EXTENDED_MODES) <= 1, "At most one extended runtime type may be declared alongside workout-processing.")
    if mode == "workout":
        add("workout_mode", "workout-processing" in wk_modes, "A real user-initiated workout is still required.")
        add("healthkit_entitlement", entitlements.get("com.apple.developer.healthkit") is True, "This checks signed capability, not user permission.")
        for key in ["NSHealthShareUsageDescription", "NSHealthUpdateUsageDescription"]:
            add(key, purpose(key), "This example workout path reads and writes HealthKit data.")
    else:
        add("extended_mode", mode in wk_modes, "The selected mode must match the app's real purpose and start while active.")
    notes = ["Static configuration only: runtime, user grants, sampling continuity and delivery remain unverified."]
    if not info.get("NSMotionUsageDescription"):
        notes.append("Motion purpose text is absent; check the exact Core Motion APIs and SDK requirements.")
    if "audio" in ui_modes:
        notes.append("Audio mode needs a real supported audio/haptic use case; it is not a BLE keep-alive flag.")
    if entitlements.get("com.apple.developer.healthkit.background-delivery"):
        notes.append("HealthKit background delivery is for observer queries, not unlimited app runtime.")
    return {"static_checks_passed": all(item["passed"] for item in checks),
            "runtime_verified": False, "checks": checks, "notes": notes}


def signed_entitlements(app: Path) -> dict:
    result = subprocess.run(["codesign", "-d", "--entitlements", ":-", str(app)], capture_output=True)
    raw = result.stdout + result.stderr
    start, end = raw.find(b"<?xml"), raw.find(b"</plist>")
    if result.returncode:
        raise ValueError("Cannot read signed entitlements; no capability conclusion can be made.")
    if start < 0:
        return {}  # A signed app may legitimately have no entitlement blob.
    if end < start:
        raise ValueError("Malformed signed XML entitlements.")
    return plistlib.loads(raw[start:end + len(b"</plist>")])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", type=Path, help="Path to the built WatchApp.app")
    parser.add_argument("--mode", choices=["workout", *sorted(EXTENDED_MODES)], default="workout")
    args = parser.parse_args()
    try:
        with (args.app / "Info.plist").open("rb") as stream:
            info = plistlib.load(stream)
        report = audit(info, signed_entitlements(args.app), args.mode)
    except (OSError, ValueError, plistlib.InvalidFileException):
        print(json.dumps({"static_checks_passed": False, "runtime_verified": False,
                          "error": "Built Info.plist or signed entitlements could not be read."}))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["static_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
