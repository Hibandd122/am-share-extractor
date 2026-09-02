"""
Lyric Aligner & Parser Engine
Supports Raw Text, LRC format ([mm:ss.xx]), and SRT subtitles.
"""

import re
from typing import List, Dict, Any, Optional


def parse_lrc_timestamp(ts_str: str) -> Optional[int]:
    """Converts [mm:ss.xx] or [mm:ss.xxx] to milliseconds."""
    m = re.match(r"\[?(\d{1,2}):(\d{2})(?:\.(\d{1,3}))?\]?", ts_str.strip())
    if not m:
        return None
    mins = int(m.group(1))
    secs = int(m.group(2))
    frac_str = m.group(3) or "0"
    # Normalize fraction to milliseconds
    if len(frac_str) == 1:
        ms = int(frac_str) * 100
    elif len(frac_str) == 2:
        ms = int(frac_str) * 10
    else:
        ms = int(frac_str[:3])
    return (mins * 60 + secs) * 1000 + ms


def parse_srt_timestamp(ts_str: str) -> Optional[int]:
    """Converts hh:mm:ss,ms to milliseconds."""
    m = re.match(r"(\d{1,2}):(\d{2}):(\d{2})[,\.](\d{1,3})", ts_str.strip())
    if not m:
        return None
    hrs = int(m.group(1))
    mins = int(m.group(2))
    secs = int(m.group(3))
    ms = int((m.group(4) + "00")[:3])
    return (hrs * 3600 + mins * 60 + secs) * 1000 + ms


def parse_raw_lyrics(raw_content: str) -> List[Dict[str, Any]]:
    """
    Auto-detects format (LRC, SRT, or plain lines) and parses into lyric segments.
    """
    if not raw_content or not raw_content.strip():
        return []

    # Handle literal escaped newlines from CLI input
    normalized = raw_content.replace("\\n", "\n")
    lines = [line.strip() for line in normalized.strip().splitlines() if line.strip()]
    if not lines:
        return []

    # Check if LRC format
    lrc_entries = []
    lrc_pattern = re.compile(r"\[(\d{1,2}:\d{2}(?:\.\d{1,3})?)\](.*)")
    is_lrc = False

    for line in lines:
        matches = lrc_pattern.findall(line)
        if matches:
            is_lrc = True
            for ts, text in matches:
                ms = parse_lrc_timestamp(ts)
                clean_txt = text.strip()
                if ms is not None and clean_txt:
                    lrc_entries.append({"start_ms": ms, "text": clean_txt})

    if is_lrc and lrc_entries:
        lrc_entries.sort(key=lambda x: x["start_ms"])
        # Calculate end times
        for i in range(len(lrc_entries)):
            current = lrc_entries[i]
            if i < len(lrc_entries) - 1:
                next_start = lrc_entries[i + 1]["start_ms"]
                current["end_ms"] = min(next_start - 1, current["start_ms"] + 4500)
            else:
                current["end_ms"] = current["start_ms"] + 3000
            current["id"] = i + 1
        return lrc_entries

    # Check if SRT format
    srt_entries = []
    srt_block_pattern = re.compile(
        r"(\d+)\s*\n(\d{1,2}:\d{2}:\d{2}[,\.]\d{1,3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,\.]\d{1,3})\s*\n([\s\S]*?)(?=\n\n|\Z)"
    )
    srt_matches = srt_block_pattern.findall(raw_content)
    if srt_matches:
        for idx, start_ts, end_ts, text in srt_matches:
            s_ms = parse_srt_timestamp(start_ts)
            e_ms = parse_srt_timestamp(end_ts)
            clean_text = " ".join(text.strip().split())
            if s_ms is not None and e_ms is not None and clean_text:
                srt_entries.append({
                    "id": len(srt_entries) + 1,
                    "start_ms": s_ms,
                    "end_ms": e_ms,
                    "text": clean_text
                })
        if srt_entries:
            return srt_entries

    # Plain text format (no timestamps)
    plain_entries = []
    for idx, line in enumerate(lines):
        # Ignore chords or section headers like [Verse 1], [Chorus]
        if line.startswith("[") and line.endswith("]"):
            continue
        plain_entries.append({
            "id": idx + 1,
            "text": line,
            "start_ms": 0,
            "end_ms": 0
        })
    return plain_entries


def align_lyrics_to_beats(
    lyrics: List[Dict[str, Any]],
    beat_timestamps_ms: List[int],
    total_duration_ms: int = 30000
) -> List[Dict[str, Any]]:
    """
    Distributes plain text lyrics across detected beats and total song duration.
    """
    if not lyrics:
        return []

    num_lines = len(lyrics)

    # If lyrics already have explicit timestamps from LRC/SRT, preserve them
    has_timestamps = any(item.get("end_ms", 0) > 0 for item in lyrics)
    if has_timestamps:
        return lyrics

    # Distribute lines across beats if available
    if beat_timestamps_ms and len(beat_timestamps_ms) >= num_lines:
        # Group beats into chunks per line
        beats_per_line = len(beat_timestamps_ms) // num_lines
        for i, item in enumerate(lyrics):
            start_beat_idx = i * beats_per_line
            end_beat_idx = min(len(beat_timestamps_ms) - 1, (i + 1) * beats_per_line - 1)
            
            s_ms = beat_timestamps_ms[start_beat_idx]
            e_ms = beat_timestamps_ms[end_beat_idx] if end_beat_idx > start_beat_idx else s_ms + 2500
            
            item["start_ms"] = max(0, s_ms - 100)
            item["end_ms"] = max(item["start_ms"] + 1200, e_ms)
    else:
        # Uniform distribution across song duration with lead-in offset
        lead_in = 1000
        usable_duration = max(5000, total_duration_ms - lead_in - 2000)
        time_per_line = usable_duration / num_lines

        for i, item in enumerate(lyrics):
            s_ms = int(lead_in + i * time_per_line)
            e_ms = int(s_ms + time_per_line * 0.92)
            item["start_ms"] = s_ms
            item["end_ms"] = e_ms

    return lyrics
