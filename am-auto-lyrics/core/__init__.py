"""
AM Auto Lyrics Core Package
"""

from .presets import PRESETS, AVAILABLE_FONTS
from .lyric_aligner import parse_raw_lyrics, align_lyrics_to_beats
from .audio_analyzer import generate_beats_from_bpm, estimate_bpm_from_peaks
from .xml_generator import generate_alight_motion_xml

__all__ = [
    "PRESETS",
    "AVAILABLE_FONTS",
    "parse_raw_lyrics",
    "align_lyrics_to_beats",
    "generate_beats_from_bpm",
    "estimate_bpm_from_peaks",
    "generate_alight_motion_xml",
]
