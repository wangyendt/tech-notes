"""Synthetic-only quality example. Not a Bluetooth parser or medical validator."""
from collections import Counter
from statistics import median


def summarize(records):
    """records: iterable of (device_record_ms, raw_bpm); zeros/duplicates retained."""
    rows = sorted(records, key=lambda row: row[0])
    if any(t < 0 or bpm < 0 for t, bpm in rows):
        raise ValueError("negative timestamp or raw value")
    intervals = [b[0] - a[0] for a, b in zip(rows, rows[1:])]
    positive = [dt for dt in intervals if dt > 0]
    step = median(positive) if positive else None
    threshold = max(3000, 3 * step) if step is not None else 3000
    return {
        "source": "SYNTHETIC_EXAMPLE_NOT_REAL_HEART_RATE",
        "records": len(rows),
        "raw_zero_records": sum(bpm == 0 for _, bpm in rows),
        "duplicate_timestamp_extras": sum(n - 1 for n in Counter(t for t, _ in rows).values()),
        "median_positive_interval_ms": step,
        "max_interval_ms": max(positive, default=None),
        "gap_threshold_ms": threshold,
        "long_gaps": sum(dt > threshold for dt in intervals),
        "packet_loss_proven": False,
    }


if __name__ == "__main__":
    import json
    synthetic = [(0, 0), (1000, 0), (2000, 82), (3000, 83), (3000, 83), (8000, 84)]
    print(json.dumps(summarize(synthetic), indent=2, ensure_ascii=False))
