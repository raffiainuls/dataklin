"""Timeliness/Freshness Check (backlog #5): deteksi apakah dataset yang dipantau
terjadwal (F10) benar-benar diperbarui sesuai jadwalnya. Hanya relevan untuk dataset
dengan monitoring aktif DAN sudah punya run sebelumnya untuk dibandingkan — dataset
upload biasa (tanpa jadwal) atau run pertama tidak punya dimensi ini sama sekali,
konsisten dengan dimensi lain yang juga hanya muncul bila datanya tersedia.
"""
from __future__ import annotations

from datetime import datetime

# keterlambatan dianggap mulai bermakna setelah melewati interval x faktor ini
LATE_FACTOR = 2.0


def compute_timeliness(monitoring_enabled: bool, interval_minutes: int,
                       previous_run_at: datetime | None, now: datetime) -> dict | None:
    """Kembalikan {score(0..1), minutes_since_previous, expected_minutes, on_time}
    atau None bila tidak relevan dihitung."""
    if not monitoring_enabled or previous_run_at is None or interval_minutes <= 0:
        return None
    elapsed_minutes = (now - previous_run_at).total_seconds() / 60
    threshold = interval_minutes * LATE_FACTOR
    on_time = elapsed_minutes <= threshold
    score = 1.0 if on_time else max(0.0, 1 - (elapsed_minutes - threshold) / threshold)
    return {
        "score": round(score, 4),
        "minutes_since_previous": round(elapsed_minutes, 1),
        "expected_minutes": interval_minutes,
        "on_time": on_time,
    }
