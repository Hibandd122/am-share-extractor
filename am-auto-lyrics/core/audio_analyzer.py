"""
Audio Analyzer & Beat Detection Utility
Calculates BPM and generates beat timestamps for audio synchronization.
"""

from typing import List, Dict, Any


def generate_beats_from_bpm(
    bpm: float,
    duration_ms: int,
    offset_ms: int = 0
) -> List[int]:
    """
    Generates rhythmic beat timestamps (in milliseconds) for a given BPM and duration.
    """
    if bpm <= 0:
        bpm = 120.0

    beat_interval_ms = (60.0 / bpm) * 1000.0
    beats = []
    
    current_ms = float(offset_ms)
    while current_ms < duration_ms:
        beats.append(int(round(current_ms)))
        current_ms += beat_interval_ms

    return beats


def estimate_bpm_from_peaks(peak_timestamps_ms: List[int]) -> float:
    """
    Estimates BPM from a list of detected audio onset peak timestamps.
    """
    if len(peak_timestamps_ms) < 2:
        return 120.0

    intervals = []
    for i in range(1, len(peak_timestamps_ms)):
        diff = peak_timestamps_ms[i] - peak_timestamps_ms[i - 1]
        # Filter intervals within human musical range (40 BPM to 220 BPM -> 270ms to 1500ms)
        if 270 <= diff <= 1500:
            intervals.append(diff)

    if not intervals:
        return 120.0

    # Median interval for robustness against outlier noise
    intervals.sort()
    median_interval = intervals[len(intervals) // 2]
    
    bpm = (60.0 * 1000.0) / median_interval
    return round(bpm, 1)
