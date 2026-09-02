"""
Alight Motion Text Animation Presets Catalog
Contains authentic effect IDs, property configurations, and cubicBezier curves.
"""

from typing import Dict, Any, List

PRESETS: Dict[str, Dict[str, Any]] = {
    "typewriter": {
        "id": "typewriter",
        "name": "Typewriter Smooth Reveal (AM Official Style)",
        "description": "Smooth character-by-character kinetic reveal with cubicBezier easing and fade.",
        "font_default": "googlefonts?name=Patrick Hand&weight=400",
        "font_size_default": 24.0,
        "effects": [
            {
                "id": "com.alightcreative.effects.texttransform",
                "locallyApplied": "true",
                "properties": [
                    {"name": "alpha", "type": "float", "value": "1.000000"},
                    {"name": "component", "type": "int", "value": "2"},
                    {"name": "easeIn", "type": "float", "value": "-1.000000"},
                    {"name": "easeOut", "type": "float", "value": "1.000000"},
                    {
                        "name": "end",
                        "type": "float",
                        "keyframes": [
                            {"t": 0.000000, "v": 0.000000},
                            {"t": 0.996155, "v": 1.000000, "e": "cubicBezier 0.0 0.0 0.56084657 1.0"}
                        ]
                    },
                    {"name": "offset", "type": "vec2", "value": "-10.000000,-8.000000"}
                ]
            },
            {
                "id": "com.alightcreative.effects.fade",
                "locallyApplied": "true",
                "properties": []
            }
        ]
    },
    "kinetic_pop": {
        "id": "kinetic_pop",
        "name": "Kinetic Beat Pop (Scale Pulse & Bounce)",
        "description": "Energetic scale bounce that pops in aggressively on the bass drop / beat onset.",
        "font_default": "googlefonts?name=Montserrat&weight=700",
        "font_size_default": 28.0,
        "effects": [
            {
                "id": "com.alightcreative.effects.texttransform",
                "locallyApplied": "true",
                "properties": [
                    {"name": "component", "type": "int", "value": "1"},
                    {"name": "scale", "type": "float", "value": "1.350000"},
                    {
                        "name": "progress",
                        "type": "float",
                        "keyframes": [
                            {"t": 0.000000, "v": 0.000000},
                            {"t": 0.350000, "v": 1.000000, "e": "cubicBezier 0.17 0.89 0.32 1.28"}
                        ]
                    }
                ]
            },
            {
                "id": "com.alightcreative.effects.fade",
                "locallyApplied": "true",
                "properties": []
            }
        ]
    },
    "neon_glow": {
        "id": "neon_glow",
        "name": "Neon Cyber Glow (Glow + Slide Up)",
        "description": "Cyberpunk glowing text with smooth upwards vertical glide.",
        "font_default": "googlefonts?name=Outfit&weight=600",
        "font_size_default": 26.0,
        "effects": [
            {
                "id": "com.alightcreative.effects.glow",
                "locallyApplied": "true",
                "properties": [
                    {"name": "radius", "type": "float", "value": "35.000000"},
                    {"name": "alpha", "type": "float", "value": "0.750000"},
                    {"name": "color", "type": "color", "value": "#FF38BDF8"}
                ]
            },
            {
                "id": "com.alightcreative.effects.fade",
                "locallyApplied": "true",
                "properties": []
            }
        ]
    },
    "minimal_clean": {
        "id": "minimal_clean",
        "name": "Minimal Fade & Letter Spacing",
        "description": "Elegant clean aesthetic with tracking/kerning expand on reveal.",
        "font_default": "googlefonts?name=Inter&weight=500",
        "font_size_default": 22.0,
        "effects": [
            {
                "id": "com.alightcreative.effects.fade",
                "locallyApplied": "true",
                "properties": [
                    {"name": "inTime", "type": "float", "value": "0.200000"},
                    {"name": "outTime", "type": "float", "value": "0.200000"}
                ]
            }
        ]
    }
}

AVAILABLE_FONTS = [
    {"name": "Patrick Hand", "weight": 400, "tag": "googlefonts?name=Patrick Hand&weight=400", "label": "Patrick Hand (Handwritten/Lyric)"},
    {"name": "Montserrat", "weight": 700, "tag": "googlefonts?name=Montserrat&weight=700", "label": "Montserrat Bold (Modern Punchy)"},
    {"name": "Outfit", "weight": 600, "tag": "googlefonts?name=Outfit&weight=600", "label": "Outfit SemiBold (Cyber / Clean)"},
    {"name": "Be Vietnam Pro", "weight": 600, "tag": "googlefonts?name=Be Vietnam Pro&weight=600", "label": "Be Vietnam Pro (Vietnamese Native)"},
    {"name": "Quicksand", "weight": 600, "tag": "googlefonts?name=Quicksand&weight=600", "label": "Quicksand (Soft / Aesthetic)"},
    {"name": "Inter", "weight": 500, "tag": "googlefonts?name=Inter&weight=500", "label": "Inter (Minimalist Clean)"},
    {"name": "Caveat", "weight": 700, "tag": "googlefonts?name=Caveat&weight=700", "label": "Caveat Brush (Artistic Script)"},
]
