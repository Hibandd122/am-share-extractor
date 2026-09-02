#!/usr/bin/env python3
"""
AM Auto Lyrics - Command Line Interface (CLI)
Generate Alight Motion XML Lyric Projects directly from terminal.
"""

import argparse
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from core.xml_generator import generate_alight_motion_xml
from core.lyric_aligner import parse_raw_lyrics, align_lyrics_to_beats
from core.audio_analyzer import generate_beats_from_bpm
from core.presets import PRESETS


def main():
    parser = argparse.ArgumentParser(
        description="Auto Create Lyric Projects for Alight Motion (BPM / Beat Sync to XML)"
    )
    parser.add_argument(
        "--lyrics", "-l", required=True,
        help="Path to lyrics file (.txt, .lrc, .srt) or raw lyrics string",
    )
    parser.add_argument(
        "--bpm", "-b", type=float, default=120.0,
        help="Audio BPM for automated beat detection (default: 120.0)",
    )
    parser.add_argument(
        "--duration", "-d", type=int, default=30,
        help="Total duration in seconds (default: 30s)",
    )
    parser.add_argument(
        "--preset", "-p", choices=list(PRESETS.keys()), default="typewriter",
        help="Animation preset (typewriter, kinetic_pop, neon_glow, minimal_clean)",
    )
    parser.add_argument(
        "--title", "-t", default="AM Auto Lyrics",
        help="Project title for Alight Motion",
    )
    parser.add_argument(
        "--resolution", "-r", default="1080x1920",
        help="Resolution WxH (default: 1080x1920 for Portrait)",
    )
    parser.add_argument(
        "--output", "-o", default=None,
        help="Path to output .xml file (default: <title>.xml)",
    )

    args = parser.parse_args()

    # Load lyrics content
    if os.path.isfile(args.lyrics):
        with open(args.lyrics, "r", encoding="utf-8") as f:
            raw_content = f.read()
    else:
        raw_content = args.lyrics

    parsed_lyrics = parse_raw_lyrics(raw_content)
    if not parsed_lyrics:
        print("[!] No valid lyrics lines found.", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Loaded {len(parsed_lyrics)} lyric lines.")

    # Generate beats from BPM
    total_ms = args.duration * 1000
    beats = generate_beats_from_bpm(args.bpm, total_ms)
    print(f"[*] Generated {len(beats)} beat marks at {args.bpm} BPM.")

    # Align lyrics to beats
    aligned_lyrics = align_lyrics_to_beats(parsed_lyrics, beats, total_ms)

    # Resolution
    try:
        w, h = map(int, args.resolution.lower().split("x"))
    except ValueError:
        w, h = 1080, 1920

    # Generate XML
    xml_data = generate_alight_motion_xml(
        lyrics=aligned_lyrics,
        bookmarks_ms=beats,
        title=args.title,
        width=w,
        height=h,
        fps=60,
        total_time_ms=total_ms,
        preset_id=args.preset,
    )

    out_file = args.output or f"{args.title.replace(' ', '_')}.xml"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(xml_data)

    print(f"[+] Successfully generated Alight Motion XML: {out_file} ({len(xml_data):,} bytes)")


if __name__ == "__main__":
    main()
